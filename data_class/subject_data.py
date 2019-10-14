"""
Types for data exchange for the subjects
"""
import datetime
from typing import List, Dict

import numpy as np

from data_class.detected_objects import DetectedObject
from data_class.distribution import Distribution
from services import service_provider
from services.image_encoder import ImageEncoder


class TimelineDataPoint(object):
    def __init__(self, plot_name: str, series_name: str):
        super().__init__()
        self.series_name = series_name
        self.plot_name = plot_name
        self.value = None
        self.time = None

    def add_new_point(self, value: float, time=None):
        if time is None:
            time = datetime.datetime.now().timestamp()
        self._append = True
        self.value = value
        self.time = time
        return self


class AcquiredImage(object):
    def __init__(self, image: np.ndarray, time: float, name: str = None):
        super(AcquiredImage, self).__init__()

        self.time = time
        self.image = image
        self.name = name or f"{time * 1000:.0f}.jpg"
        self._encoded_buffer = None

    @property
    def encoded_buffer(self):
        if self._encoded_buffer is None:
            self.encode()
        return self._encoded_buffer

    def encode(self):
        encoder:ImageEncoder = service_provider.ImageEncoderProvider().get_or_create_instance(None)
        self._encoded_buffer = encoder.encode(self.image)
        return self._encoded_buffer


class SampleImageData(object):
    def __init__(self, image: bytes, labels: List[DetectedObject], time=None):
        self.image = image
        self.labels = labels
        self.time = time or datetime.datetime.now().timestamp()


class ProcessedDistributions(object):
    def __init__(self, dists: Dict[str, Distribution]):
        self.dists = dists


class DetectionsInImage(object):
    def __init__(self, image_id: str, objs: List[DetectedObject]):
        self.objs = objs
        self.image_id = image_id
