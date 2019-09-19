import glob
import sys
import time
import typing
import grpc

from DataObject.InferenceStats import InferenceStats
from inference_service_proto import inference_service_pb2_grpc as grpc_service
from inference_service_proto import inference_service_pb2 as grpc_def

from PyQt5 import QtWidgets, QtGui, QtCore


class InferenceComm(QtCore.QObject):
    resultReady = QtCore.pyqtSignal(grpc_def.InferenceResult)
    connected = QtCore.pyqtSignal()
    disconnected = QtCore.pyqtSignal()
    errorOccurred = QtCore.pyqtSignal(str)
    statsEmitted = QtCore.pyqtSignal()

    def __init__(self, batchSize=5, parent=None):
        super().__init__(parent)
        self.channel = None
        self.stub: grpc_service.InferenceStub
        self.isConnected = False
        self.req = grpc_def.ImageBatchRequest()
        self.req.opt.num_image_returned = 1
        self.startTimeQueue = []

        self.batchSize = batchSize

    def onConnectStateChange(self, state: grpc.ChannelConnectivity):
        if state == grpc.ChannelConnectivity.READY:
            self.connected.emit()
            self.isConnected = True
        if state == grpc.ChannelConnectivity.TRANSIENT_FAILURE or state == grpc.ChannelConnectivity.SHUTDOWN:
            if self.isConnected:
                self.disconnected.emit()
                self.isConnected = False

    def connectToGrpcServer(self, ip, port):
        if self.isConnected:
            return

        if self.channel is not None:
            self.channel.close()

        self.channel = grpc.insecure_channel(f"{ip}:{port}")
        self.channel.subscribe(self.onConnectStateChange, True)

        self.stub = grpc_service.InferenceStub(self.channel)

    def inferenceDoneCallback(self, future: grpc.Future):
        inferenceResult: grpc_def.InferenceResult = future.result(None)
        elapsedTime = time.time() - self.startTimeQueue.pop(0)
        numProcessedImages = len(inferenceResult.result)

        stats = InferenceStats(numProcessedImages, elapsedTime)
        self.statsEmitted.emit(stats)

        # notify new detections
        self.resultReady.emit(inferenceResult)

    def stop(self):
        self.channel.close()
        self.isConnected = False
        self.disconnected.emit()

    @QtCore.pyqtSlot(object)
    def feedImages(self, images: typing.Iterable[bytes]):
        if not self.isConnected:
            self.errorOccurred.emit("Server is not connected. Cannot feed image.")
            return

        if isinstance(images, bytes):
            images = [images]

        for image in images:
            name = time.time_ns()
            req_img = grpc_def.Image()
            req_img.name = f"{name}.jpg"
            req_img.images_data = image
            self.req.images.append(req_img)

        if len(self.req.images) >= self.batchSize:
            self.req.opt.num_image_returned = 1
            self.startTimeQueue.append(time.time())
            resp: grpc.Future = self.stub.Inference.future(self.req)
            resp.add_done_callback(self.inferenceDoneCallback)
            self.req.Clear()


if __name__ == '__main__':
    def imgAndDetectionReadyCallback(img, detection):
        print(img, detection)


    def detectionsReadyCallback(detections):
        print(detections)


    app = QtWidgets.QApplication(sys.argv)

    comm = InferenceComm()
    comm.imageAndDetectionsReady.connect(imgAndDetectionReadyCallback)
    comm.detectionsReady.connect(detectionsReadyCallback)

    comm.connectToGrpcServer("wuyuanyi-pc", "3034")
    while not comm.isConnected:
        time.sleep(1)
    imagePaths = glob.glob("TestImages/*.png")
    images = []
    for x in imagePaths:
        with open(x, "rb") as f:
            images.append(f.read())

    comm.feedImages(images)

    time.sleep(10)

    app.exec_()
