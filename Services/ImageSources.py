import asyncio
import glob
import io
import logging

import msgpack
from PIL import Image
import numpy as np
from PyQt5 import QtWidgets, QtGui, QtCore
from numpy import random

from Services import ConfigProvider
from Services.SimexComm import SimexComm


class ImageSource(QtCore.QObject):
    imagesReady = QtCore.pyqtSignal(np.ndarray)

    def __init__(self, parent=None):
        super().__init__(parent)

    def start(self):
        pass

    def stop(self):
        pass

    def isRunning(self):
        pass

class MockImageSource(ImageSource):
    def __init__(self, parent=None, fps=5):
        super().__init__(parent)
        self.fps = fps
        self.images = self._sourceImages()
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._backgroundTask)
        self.running = False

    @staticmethod
    def _sourceImages():
        imgPaths = glob.glob("TestImages/*.png")
        images = [np.asarray(Image.open(image))[:,:,0].T for image in imgPaths]
        return images

    @QtCore.pyqtSlot()
    def _backgroundTask(self):
        idx = random.choice(len(self.images), 1)[0]
        img = self.images[idx]
        self.imagesReady.emit(img)

    def start(self):
        self.timer.start(1000 // self.fps)
        self.running = True

    def isRunning(self):
        return self.running

    def stop(self):
        self.timer.stop()
        self.running = False


class SimexImageSource(ImageSource):
    configPrefix = "Simulink_ImageSource"
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = ConfigProvider.SettingAccessor(self.configPrefix)

        self.logger = logging.getLogger("console")
        self.transpose = self.config["transpose"]
        self.simexComm = SimexComm(bufferSize=self.config["buffer_size"])

        self.simexComm.errorOccured.connect(self.logError)
        self.simexComm.imageReceived.connect(self.imageReceivedCallback)
        self.simexComm.connected.connect(self.connectedCallback)
        self.simexComm.disconnected.connect(self.disconnectedCallback)

    @staticmethod
    @ConfigProvider.defaultSettingRegistration(configPrefix)
    def defaultSettings(configPrefix):
        ConfigProvider.defaultSettings(configPrefix, [
            ConfigProvider.SettingRegistry("ip", "127.0.0.1"),
            ConfigProvider.SettingRegistry("port", "11250"),
            ConfigProvider.SettingRegistry("buffer_size", 10240, type="int", title="socket buffer size"),
            ConfigProvider.SettingRegistry("transpose", True, type="bool"),
        ])

    def start(self):
        settings = ConfigProvider.globalSettings
        self.simexComm.connectToServer(self.config["ip"], self.config["port"])

    def stop(self):
        self.simexComm.stop()

    def isRunning(self):
        if self.simexComm:
            return self.simexComm.isConnected
        else:
            return False

    @QtCore.pyqtSlot(str)
    def logError(self, err):
        self.logger.error(err)

    @QtCore.pyqtSlot(np.ndarray)
    def imageReceivedCallback(self, a):
        if self.transpose:
            a = a.T
        self.imagesReady.emit(a)

    @QtCore.pyqtSlot()
    def connectedCallback(self):
        self.logger.info("Simulink image server connected")

    @QtCore.pyqtSlot()
    def disconnectedCallback(self):
        self.logger.info("Simulink image server disconnected")

imageSourceList = {
    "Test": MockImageSource,
    "Simulink": SimexImageSource,
}
