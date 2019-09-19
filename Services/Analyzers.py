import typing
import logging
import numpy as np
from PyQt5 import QtWidgets, QtGui, QtCore

from Services import ConfigProvider
from Services.InferenceComm import InferenceComm
from inference_service_proto.inference_service_pb2 import InferenceResult

import turbojpeg as tj


class BaseAnalyzer(QtCore.QObject):
    resultAnalyzed = QtCore.pyqtSignal(InferenceResult)

    def __init__(self, parent=None):
        super().__init__(parent)

    def isRunning(self):
        pass

    def start(self):
        pass

    def stop(self):
        pass

    def feedImage(self, images: typing.Iterable[np.ndarray]):
        pass


class GRPCRemoteAnalyzer(BaseAnalyzer):
    configPrefix = "GRPCRemoteAnalyzer"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = ConfigProvider.SettingAccessor(self.configPrefix)
        self.logger = logging.getLogger("console")
        self.imageEncoder = tj.TurboJPEG()
        self.inferenceComm = InferenceComm(self.config["batch_size"])
        self.inferenceComm.errorOccurred.connect(lambda e: self.logger.error(e))
        self.inferenceComm.connected.connect(lambda: self.logger.info("GRPC remote analyzer connected"))
        self.inferenceComm.disconnected.connect(lambda: self.logger.info("GRPC remote analyzer disconnected"))
        self.inferenceComm.statsEmitted.connect(
            lambda s: self.logger.info(f"Processed {s.frame} images. Average time: {s.processTime / s.frame}")
        )
        self.inferenceComm.resultReady.connect(lambda r: self.resultAnalyzed.emit(r))

    @staticmethod
    @ConfigProvider.defaultSettingRegistration(configPrefix)
    def defaultSettings(configPrefix):
        ConfigProvider.defaultSettings(configPrefix, [
            ConfigProvider.SettingRegistry("ip", "127.0.0.1"),
            ConfigProvider.SettingRegistry("port", "3034"),
            ConfigProvider.SettingRegistry("batch_size", 5, type=int, title="Inference batch size"),
        ])

    def isRunning(self):
        return self.inferenceComm.isConnected

    def start(self):
        if self.isRunning():
            self.logger.warning("GRPC remote inference server is already connected.")
            return
        self.inferenceComm.connectToGrpcServer(self.config["ip"], self.config["port"])

    def stop(self):
        self.inferenceComm.stop()

    def feedImage(self, images: typing.Iterable[np.ndarray]):
        images = [self.imageEncoder.encode(image, quality=90, pixel_format=tj.TJPF_GRAY) for image in images]
        self.inferenceComm.feedImages(images)
