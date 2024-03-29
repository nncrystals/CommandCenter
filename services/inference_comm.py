import time

import grpc
from pycocotools import mask as mask_util
from rx import subject

from data_class.detected_objects import DetectedObject
from data_class.inference_stats import InferenceStats
from inference_service_proto import inference_service_pb2 as grpc_def
from inference_service_proto import inference_service_pb2_grpc as grpc_service


class InferenceComm(object):
    connection_chan = subject.BehaviorSubject(False)
    result_chan = subject.Subject()
    error_chan = subject.Subject()
    stats_chan = subject.Subject()
    back_pressure_chan = subject.BehaviorSubject(False)

    def __init__(self):
        super().__init__()
        self.channel = None
        self.stub: grpc_service.InferenceStub

        self.start_time_queue = []
        self.stub = None

    def on_connect_state_change(self, state: grpc.ChannelConnectivity):
        if state == grpc.ChannelConnectivity.READY:
            self.connection_chan.on_next(True)
        if state == grpc.ChannelConnectivity.TRANSIENT_FAILURE or state == grpc.ChannelConnectivity.SHUTDOWN:
            if self.connection_chan.value:
                self.connection_chan.on_next(False)

    def connect_to_grpc_server(self, ip, port):
        if self.connection_chan.value:
            return

        if self.channel is not None:
            self.channel.close()

        self.channel = grpc.insecure_channel(f"{ip}:{port}")
        self.channel.subscribe(self.on_connect_state_change, True)

        self.stub = grpc_service.InferenceStub(self.channel)

    def back_pressure_detection(self):
        if len(self.start_time_queue) > 2:
            self.back_pressure_chan.on_next(True)
            return True
        else:
            self.back_pressure_chan.on_next(False)
            return False

    def inference_done(self, future: grpc.Future):
        elapsed_time = time.time() - self.start_time_queue.pop(0)
        try:
            self.back_pressure_detection()
            inference_result: grpc_def.InferenceResult = future.result(None)
            num_processed_images = len(inference_result.result)
            stats = InferenceStats(num_processed_images, elapsed_time)
            self.stats_chan.on_next(stats)

            # notify new detections
            self.result_chan.on_next(inference_result)
        except Exception as ex:
            self.error_chan.on_next(f"Inference error: {ex}")

    def clean(self):
        if self.channel:
            self.channel.close()

    def stop(self):
        if self.connection_chan.value:
            self.clean()
            self.connection_chan.on_next(False)

    def feed_images(self, image_and_name):
        if not self.connection_chan.value:
            self.error_chan.on_next("Server is not connected. Cannot feed image.")
            return

        req = grpc_def.ImageBatchRequest()
        req.opt.num_image_returned = 1

        for image, name in image_and_name:
            req_img = grpc_def.Image()
            req_img.name = name
            req_img.images_data = image
            req.images.append(req_img)

        self.start_time_queue.append(time.time())
        resp: grpc.Future = self.stub.Inference.future(req)
        resp.add_done_callback(self.inference_done)
        self.back_pressure_detection()

    @staticmethod
    def to_detected_object(detection: grpc_def.Detection):
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
