import io
import math
import random
import sys
import typing
from typing import Optional, Any
import cv2

import numpy as np
from PyQt5 import QtWidgets, QtGui, QtCore
from inference_service_proto import inference_service_pb2_grpc as grpc_service
from inference_service_proto import inference_service_pb2 as grpc_def
from pycocotools import mask as mask_util


# TODO this class should receive detection from detection parser. reduce redundancy.
class ImageRenderTask(QtCore.QRunnable, QtCore.QObject):
    def __init__(self, image: bytes, detections, imageReadySignal=None, alpha=0.4):
        super().__init__()
        self.imageReadySignal = imageReadySignal
        self.detections = detections
        self.image = image
        self.alpha = alpha

    def run(self) -> None:
        img_buf = np.asarray(bytearray(self.image), dtype="uint8")
        im = cv2.imdecode(img_buf, cv2.IMREAD_COLOR)
        masks = []
        labels = []
        bboxes = []
        scores = []
        for detection in self.detections:
            rle = {
                "counts": detection.rle.counts,
                "size": detection.rle.size,
            }
            masks.append(mask_util.decode(rle))
            labels.append(detection.category)

            bbox = detection.bbox
            bboxes.append((bbox.xlt, bbox.ylt, bbox.xrb, bbox.yrb))
            scores.append(detection.confidence)

        mask_channel = np.zeros([im.shape[0], im.shape[1]], dtype=bool)
        overlay = np.zeros_like(im)
        for m in masks:
            m.dtype = bool
            mask_channel[m] = True
            overlay[m] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

        # apply overlay
        im[mask_channel] = im[mask_channel] * (1 - self.alpha) + overlay[mask_channel] * self.alpha

        for b, l, s in zip(bboxes, labels, scores):
            b = [math.ceil(coor) for coor in b]
            pt1 = (b[0], b[1])
            pt2 = (b[2], b[3])

            cv2.rectangle(im, pt1, pt2, (255, 0, 0), thickness=1)
            cv2.putText(im, f"{l} {s:.2f}", pt1, cv2.FONT_HERSHEY_PLAIN, 1, (255, 0, 0))
        image = QtGui.QImage(im, im.shape[1], im.shape[0], im.strides[0], QtGui.QImage.Format_RGB888)
        pixmap = QtGui.QPixmap(image)

        if self.imageReadySignal:
            self.imageReadySignal.emit(pixmap)

# async inference image renderer
class InferenceResultRenderer(QtCore.QObject):
    renderedImageReady = QtCore.pyqtSignal(np.ndarray)

    def __init__(self, parent):
        super().__init__(parent)
        self.threadPool = QtCore.QThreadPool(self)

    @QtCore.pyqtSlot(np.ndarray, object)
    def renderImageAsync(self, image, detections: grpc_def.ResultPerImage):
        task = ImageRenderTask(image, detections, self.renderedImageReady)
        self.threadPool.start(task)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)

    import pickle

    with open("TestImages/sample_response.pkl", "rb") as f:
        sampleResponse: grpc_def.InferenceResult = pickle.load(f)


    def imageReadyCallback(pixmap: QtGui.QPixmap):
        print(pixmap.size())
        app.exit(0)


    render = InferenceResultRenderer(None)
    render.renderedImageReady.connect(imageReadyCallback)
    label = [x for x in sampleResponse.result if x.image_id == sampleResponse.returned_images[0].name][0]
    render.renderImageAsync(sampleResponse.returned_images[0].images_data, label)

    app.exec_()
