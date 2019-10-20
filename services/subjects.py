from typing import List

import numpy as np
from rx import subject
from rx import typing

from data_class.detected_objects import DetectedObject

from data_class.subject_data import ProcessedDistributions, AcquiredImage, SampleImageData, TimelineDataPoint, \
    DetectionsInImage


class Subjects(object):
    """
    Internal message channel multiplexier
    """
    image_producer: typing.Subject[AcquiredImage, AcquiredImage] = subject.Subject()
    image_source_connected: subject.BehaviorSubject = subject.BehaviorSubject(False)

    sample_image_data: typing.Subject[SampleImageData, SampleImageData] = subject.Subject()
    detection_result: typing.Subject[DetectionsInImage, DetectionsInImage] = subject.Subject()
    analyzer_back_pressure_detected: subject.BehaviorSubject = subject.BehaviorSubject(False)
    rendered_sample_image_producer: typing.Subject[np.ndarray, np.ndarray] = subject.Subject()

    analyzer_connected: subject.BehaviorSubject = subject.BehaviorSubject(False)

    processed_distributions: typing.Subject[ProcessedDistributions, ProcessedDistributions] = subject.Subject()
    add_to_timeline: typing.Subject[TimelineDataPoint, TimelineDataPoint] = subject.Subject()