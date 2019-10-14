"""
Process the raw masks from analyzer.
- remove edge touching objects
- analyze area and ellipse fit
- report number of object
"""
from typing import List

import cv2
import numpy as np
from rx import operators
from rx import subject

import services.service_provider
from data_class.detected_objects import DetectedObject
from data_class.distribution import AreaDistribution, EllipseDistribution
from data_class.subject_data import TimelineDataPoint, ProcessedDistributions, SampleImageData, DetectionsInImage
from services import config
from services.inference_result_render import render_inference
from services.subjects import Subjects
from utils.observer import ErrorToConsoleObserver


class ResultProcessor(object):
    config_prefix = "ResultProcess"

    def __init__(self):
        super().__init__()
        self.config = config.SettingAccessor(self.config_prefix)
        config.setting_updated_channel.pipe(
            operators.filter(lambda x: x[0] == f"{ResultProcessor.config_prefix}/group_size")
        ).subscribe(ErrorToConsoleObserver(lambda x: self.configure_subscriptions()))
        self._stop = subject.Subject()
        self.subjects: Subjects = services.service_provider.SubjectProvider().get_or_create_instance(None)
        self.configure_subscriptions()

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
        ).subscribe(ErrorToConsoleObserver(self.process_distribution_data))

        self.subjects.sample_image_data.pipe(
            operators.take_until(self._stop),
        ).subscribe(ErrorToConsoleObserver(self.render_sample_image))

    def filter_cropped(self, detections, threshold):
        if threshold == 0:
            return detections
        ret = []
        detection: DetectedObject
        for detection in detections:
            xlt, ylt, xrb, yrb = detection.bbox
            image_height, image_width = detection.maskRLE["size"]
            if xlt <= float(
                    threshold) or ylt <= threshold or image_width - xrb <= threshold or image_height - yrb <= threshold:
                continue
            else:
                ret.append(detection)
        return ret

    def render_sample_image(self, data: SampleImageData):
        detections = self.filter_cropped(data.labels, self.config["crop_threshold"])
        rendered = render_inference(data.image, detections)
        self.subjects.rendered_sample_image_producer.on_next(rendered)

    def process_distribution_data(self, data: List[DetectionsInImage]):
        areas = []
        minors = []
        majors = []
        for d in data:
            detections_per_image = self.filter_cropped(d.objs, self.config["crop_threshold"])
            for detections in detections_per_image:

                areas.append(detections.mask.sum())
                detections.mask.dtype = np.uint8
                contours, _ = cv2.findContours(detections.mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
                max_area = 0
                biggest_contour = None
                for c in contours:
                    area = cv2.contourArea(c)
                    if area > max_area:
                        biggest_contour = c
                        max_area = area
                if len(biggest_contour) > 5:
                    ellipse = cv2.fitEllipse(biggest_contour)
                    majors.append(ellipse[1][0])
                    minors.append(ellipse[1][1])
        area_dist = AreaDistribution(areas)
        ellipse_dist = EllipseDistribution(majors, minors)
        self.subjects.processed_distributions.on_next(
            ProcessedDistributions({"areas": area_dist, "ellipses": ellipse_dist}))
        self.subjects.add_to_timeline.on_next(
            TimelineDataPoint("Particles per frame", "class 1").add_new_point(len(areas) / len(data)))

    def finalize(self):
        self._stop.on_next(True)
