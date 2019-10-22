"""
Process the raw masks from analyzer.
- remove edge touching objects
- analyze area and ellipse fit
- report number of object
"""
from typing import List
from pycocotools import mask as mask_util
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
            config.SettingRegistry("calibration_ratio", 0, type="float", title="Length (micrometer) per pixel"),
            config.SettingRegistry("conf_threshold", 0.8, type="float", title="Confidence threshold"),
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

    def filter_unwanted(self, detections):
        crop_threshold = self.config["crop_threshold"]
        conf_threshold = self.config["conf_threshold"]

        filtered = []
        detection: DetectedObject
        if conf_threshold != 0:
            for detection in detections:
                if detection.score > conf_threshold:
                    filtered.append(detection)
        ret = []
        if crop_threshold != 0:
            for detection in filtered:
                xlt, ylt, xrb, yrb = detection.bbox
                image_height, image_width = detection.maskRLE["size"]
                if xlt <= float(
                        crop_threshold) or ylt <= crop_threshold or image_width - xrb <= crop_threshold or image_height - yrb <= crop_threshold:
                    continue
                else:
                    ret.append(detection)
        return ret

    def render_sample_image(self, data: SampleImageData):
        detections = self.filter_unwanted(data.labels)
        rendered = render_inference(data.image, detections)
        self.subjects.rendered_sample_image_producer.on_next(rendered)

    def process_distribution_data(self, data: List[DetectionsInImage]):
        areas = []
        minors = []
        majors = []
        for d in data:
            detections_per_image = self.filter_unwanted(d.objs)
            for detections in detections_per_image:
                mask = mask_util.decode(detections.maskRLE)
                areas.append(mask.sum())
                mask.dtype = np.uint8
                contours, _ = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
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
        areas = np.asarray(areas).T
        minors = np.asarray(minors).T
        majors = np.asarray(majors).T

        calibration_ratio = self.config["calibration_ratio"]
        if calibration_ratio == 0:
            area_dist = AreaDistribution(areas)
            ellipse_dist = EllipseDistribution(majors, minors)
        else:
            areas = areas * calibration_ratio
            area_dist = AreaDistribution(areas, "<math>&mu;m<sup>2</sup></math>")
            majors = majors * calibration_ratio
            minors = minors * calibration_ratio
            ellipse_dist = EllipseDistribution(majors, minors,
                                               "<math>&mu;m</math>")

        self.subjects.processed_distributions.on_next(
            ProcessedDistributions({"areas": area_dist, "ellipses": ellipse_dist}))
        self.subjects.add_to_timeline.on_next(
            TimelineDataPoint("Particles per frame", "class 1").add_new_point(len(areas) / len(data)))

        self.subjects.add_to_timeline.on_next(
            TimelineDataPoint("Ellipse average size", "minor").add_new_point(float(minors.mean())))
        self.subjects.add_to_timeline.on_next(
            TimelineDataPoint("Ellipse average size", "major").add_new_point(float(majors.mean())))
        self.subjects.add_to_timeline.on_next(
            TimelineDataPoint("Area average size", "area").add_new_point(float(areas.mean())))
    def finalize(self):
        self._stop.on_next(True)
