from typing import List

from rx import subject


class Subjects(object):
    """
    Internal message channel multiplexier
    """
    image_producer = subject.Subject()
    image_source_connected = subject.BehaviorSubject(False)

    sample_image_data = subject.Subject()
    detection_result = subject.Subject()
    analyzer_back_pressure_detected: subject.BehaviorSubject = subject.BehaviorSubject(False)
    rendered_sample_image_producer  = subject.Subject()

    analyzer_connected = subject.BehaviorSubject(False)

    processed_distributions = subject.Subject()
    add_to_timeline = subject.Subject()

    camera_peripheral_control = subject.Subject()
    pump_control = subject.Subject()