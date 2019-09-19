import cv2
from PyQt5 import QtWidgets, QtGui, QtCore
from pycocotools import mask as mask_util
from inference_service_proto import inference_service_pb2_grpc as grpc_service
from inference_service_proto import inference_service_pb2 as grpc_def

class DetectionParseTask(QtCore.QRunnable):
    detections: grpc_def.ResultPerImage

    def __init__(self, detections, areaSignal, ellipseSignal):
        super().__init__()
        self.ellipseSignal = ellipseSignal
        self.areaSignal = areaSignal
        self.detections = detections

    def run(self) -> None:
        areas = []
        ellipses = []

        for detection in self.detections.detections:
            rle = {
                "counts": detection.rle.counts,
                "size": detection.rle.size,
            }
            m = mask_util.decode(rle)
            areas.append(m.sum())

            contours, _ = cv2.findContours(m, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            maxArea = 0
            biggestContour = None
            for c in contours:
                area = cv2.contourArea(c)
                if area > maxArea:
                    biggestContour = c
                    maxArea = area
            if len(biggestContour) > 5:
                ellipse = cv2.fitEllipse(biggestContour)
                ellipses.append(ellipse)

        self.ellipseSignal.emit(ellipses)
        self.areaSignal.emit(areas)


class DetectionParser(QtCore.QObject):
    areasPerImageReady = QtCore.pyqtSignal(object)
    ellipsesPerImageReady = QtCore.pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.threadPool = QtCore.QThreadPool(self)

    @QtCore.pyqtSlot(object)
    def parseDetectionsPerImage(self, detections):
        task = DetectionParseTask(detections, self.areasPerImageReady, self.ellipsesPerImageReady)
        self.threadPool.start(task)
