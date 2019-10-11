import io

import cv2
import numpy as np
from PIL import Image
from rx import operators
from rx import subject

import services.service_provider
from data_class.detected_objects import DetectedObject
from inference_service_proto.inference_service_pb2 import ResultPerImage
from services import config
from services.inference_result_render import render_inference
from services.subjects import Subjects


class ResultProcessor(object):
    config_prefix = "ResultProcess"

    def __init__(self):
        super().__init__()
        self.config = config.SettingAccessor(self.config_prefix)
        config.setting_updated_channel.pipe(
            operators.filter(self.filter_setting)
        ).subscribe(lambda x: self.configure_subscriptions())
        self._stop = subject.Subject()
        self.subjects: Subjects = services.service_provider.SubjectProvider().get_or_create_instance(None)
        self.configure_subscriptions()

    def filter_setting(self, x):
        return x[0] == f"{ResultProcessor.config_prefix}/group_size"

    @staticmethod
    @config.DefaultSettingRegistration(config_prefix)
    def default_settings(configPrefix):
        config.default_settings(configPrefix, [
            config.SettingRegistry("group_size", 10, type="int", title="Group size (images)"),
            config.SettingRegistry("crop_threshold", 0, type="int",
                                   title="Edge cropping object threshold (pixels)")
        ])

    def configure_subscriptions(self):
        self.subjects.detection_result.pipe(
            operators.buffer_with_count(self.config["group_size"]),
            operators.take_until(self._stop),
        ).subscribe(self.process_distribution_data)

        self.subjects.sample_image_data.pipe(
            operators.take_until(self._stop),
        ).subscribe(self.render_sample_image)

    def filter_cropped(self, detections, threshold):
        if threshold == 0:
            return detections
        ret = []
        detection: DetectedObject
        for detection in detections:
            xlt, ylt, xrb, yrb = detection.bbox
            image_height, image_width = detection.maskRLE["size"]
            if xlt <= threshold or ylt <= threshold or image_width - xrb <= threshold or image_height - yrb <= threshold:
                continue
            else:
                ret.append(detection)
        return ret

    def render_sample_image(self, data):
        (img, detections) = data
        detections = self.filter_cropped(detections, self.config["crop_threshold"])
        rendered = render_inference(img, detections)
        self.subjects.sample_image_producer.on_next(rendered)

    def process_distribution_data(self, data):
        areas = []
        ellipses = []

        for detectionsPerImage, name in data:
            detectionsPerImage = self.filter_cropped(detectionsPerImage, self.config["crop_threshold"])
            for detections in detectionsPerImage:

                areas.append(detections.mask.sum())
                detections.mask.dtype=np.uint8
                contours, _ = cv2.findContours(detections.mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
                maxArea = 0
                biggestContour = None
                for c in contours:
                    area = cv2.contourArea(c)
                    if area > maxArea:
                        biggestContour = c
                        maxArea = area
                if len(biggestContour) > 5:
                    ellipse = cv2.fitEllipse(biggestContour)
                    ellipses.append(ellipse[1])
        self.subjects.parsed_result.on_next({"areas": areas, "ellipses": ellipses})

    def finalize(self):
        self._stop.on_next(True)
