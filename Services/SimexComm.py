import asyncio

import msgpack
import numpy as np
from PyQt5 import QtCore


class SimexComm(QtCore.QThread):
    imageReceived = QtCore.pyqtSignal(np.ndarray)
    connected = QtCore.pyqtSignal()
    disconnected = QtCore.pyqtSignal()
    errorOccured = QtCore.pyqtSignal(str)

    def __init__(self, bufferSize, parent=None):
        super().__init__(parent)

        self.bufferSize = bufferSize
        self.unpacker = msgpack.Unpacker()
        self.asyncLoop = asyncio.new_event_loop()
        self.isConnected = False
        self.socketReader: asyncio.StreamReader = None
        self.socketWriter: asyncio.StreamWriter = None
        self.start()

    def run(self) -> None:
        self.asyncLoop.run_forever()

    def stop(self):
        self.socketWriter.close()
        if self.asyncLoop.is_running():
            self.asyncLoop.stop()
        self.disconnected.emit()
        self.isConnected = False


    def connectToServer(self, addr: str, port: int):
        asyncio.run_coroutine_threadsafe(self.connectAsync(addr, port), self.asyncLoop)

    async def connectAsync(self, addr: str, port: int):
        try:
            self.socketReader, self.socketWriter = await asyncio.open_connection(addr, port)
            self.connected.emit()
            asyncio.run_coroutine_threadsafe(self.recv(), self.asyncLoop)
            self.isConnected = True
        except Exception as e:
            self.errorOccured.emit(f"Failed to connect to tcp://{addr}:{port}")

    async def recv(self):
        while True:
            buf = await self.socketReader.read(self.bufferSize)
            if not buf:
                self.disconnected.emit()
                self.isConnected = False
                return
            asyncio.run_coroutine_threadsafe(self.processMessage(buf), self.asyncLoop)

    async def processMessage(self, buf):
        self.unpacker.feed(buf)
        for value in self.unpacker:
            try:
                type = value[b"t"]
                if type == 3:
                    self.errorOccured.emit(f"Simex error: {value[b'd']}")
                elif type == 2:
                    d = value[b"d"][0]
                    data = d[b"dataRef"]
                    typeId = d[b"typeId"]
                    dims = d[b"dims"]

                    arr: np.ndarray = np.frombuffer(data, dtype=self.typeIdToNumpyType(typeId))
                    # Note: matlab use column major order, this reshape should be adapted accordingly
                    arr = arr.reshape(dims, order='F')

                    self.imageReceived.emit(arr)
            except Exception as e:
                self.errorOccured.emit(f"Error while processing Simex data: {e}")
    @staticmethod
    def typeIdToNumpyType(typeId):
        if typeId == 0:
            return np.float64
        elif typeId == 1:
            return np.float32
        elif typeId == 2:
            return np.int8
        elif typeId == 3:
            return np.uint8
        elif typeId == 4:
            return np.int16
        elif typeId == 5:
            return np.uint16
        elif typeId == 6:
            return np.int32
        elif typeId == 7:
            return np.uint32
        elif typeId == 8:
            return np.bool
