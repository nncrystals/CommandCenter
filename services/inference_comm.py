import glob
import sys
import time
import typing
import grpc

from rx import subject
from rx import operators

from DataObject.DetectedObject import DetectedObject
from DataObject.InferenceStats import InferenceStats
from inference_service_proto import inference_service_pb2_grpc as grpc_service
from inference_service_proto import inference_service_pb2 as grpc_def
from pycocotools import mask as mask_util
from PyQt5 import QtWidgets, QtGui, QtCore


class InferenceComm(QtCore.QObject):
    connection_chan = subject.BehaviorSubject(False)
    result_chan = subject.Subject()
    error_chan = subject.Subject()
    stats_chan = subject.Subject()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.channel = None
        self.stub: grpc_service.InferenceStub

        self.start_time_queue = []

    def onConnectStateChange(self, state: grpc.ChannelConnectivity):
        if state == grpc.ChannelConnectivity.READY:
            self.connection_chan.on_next(True)
        if state == grpc.ChannelConnectivity.TRANSIENT_FAILURE or state == grpc.ChannelConnectivity.SHUTDOWN:
            if self.isConnected:
                self.connection_chan.on_next(False)

    def connectToGrpcServer(self, ip, port):
        if self.connection_chan.value:
            return

        if self.channel is not None:
            self.channel.close()

        self.channel = grpc.insecure_channel(f"{ip}:{port}")
        self.channel.subscribe(self.onConnectStateChange, True)

        self.stub = grpc_service.InferenceStub(self.channel)

    def inferenceDoneCallback(self, future: grpc.Future):
        inferenceResult: grpc_def.InferenceResult = future.result(None)
        elapsedTime = time.time() - self.start_time_queue.pop(0)
        numProcessedImages = len(inferenceResult.result)

        stats = InferenceStats(numProcessedImages, elapsedTime)
        self.stats_chan.on_next(stats)

        # notify new detections
        self.result_chan.on_next(inferenceResult)

    def clean(self):
        if self.channel:
            self.channel.close()

    def stop(self):
        if self.connection_chan.value:
            self.clean()
            self.connection_chan.on_next(False)

    def feedImages(self, imagesAndName):
        if not self.connection_chan.value:
            self.error_chan.on_next("Server is not connected. Cannot feed image.")
            return

        req = grpc_def.ImageBatchRequest()
        req.opt.num_image_returned = 1

        for image, name in imagesAndName:
            req_img = grpc_def.Image()
            req_img.name = name
            req_img.images_data = image
            req.images.append(req_img)

        self.start_time_queue.append(time.time())
        resp: grpc.Future = self.stub.Inference.future(req)
        resp.add_done_callback(self.inferenceDoneCallback)

    @staticmethod
    def toDetectedObject(detection: grpc_def.Detection):
        detected_object = DetectedObject()
        rle = {
            "counts": detection.rle.counts,
            "size": list(detection.rle.size),
        }
        bbox = detection.bbox
        detected_object.label = detection.category
        detected_object.maskRLE = rle
        detected_object.mask = mask_util.decode(rle)
        detected_object.bbox = (bbox.xlt, bbox.ylt, bbox.xrb, bbox.yrb)
        detected_object.score = detection.confidence
        return detected_object


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
