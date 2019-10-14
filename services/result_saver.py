import os

import msgpack
from rx import operators, subject

from data_class.subject_data import TimelineDataPoint, DetectionsInImage, AcquiredImage
from services import config
import services.service_provider
from services.subjects import Subjects
from utils.observer import ErrorToConsoleObserver


class ResultSaver(object):
    config_prefix = "ResultSaver"

    def __init__(self):
        super(ResultSaver, self).__init__()

        self._stop = subject.Subject()
        self.config = config.SettingAccessor(self.config_prefix)
        self.subjects: Subjects = services.service_provider.SubjectProvider().get_or_create_instance(None)
        self.subjects.image_producer.pipe(
            operators.filter(self.config_enabled_filter("save_images")),
            operators.take_until(self._stop),
        ).subscribe(ErrorToConsoleObserver(self.save_image))
        self.subjects.detection_result.pipe(
            operators.filter(self.config_enabled_filter("save_labels")),
            operators.take_until(self._stop),
        ).subscribe(ErrorToConsoleObserver(self.save_labels))
        self.subjects.add_to_timeline.pipe(
            operators.filter(self.config_enabled_filter("save_events")),
            operators.take_until(self._stop),
        ).subscribe(ErrorToConsoleObserver(self.save_timeline_events))

        config.setting_updated_channel.pipe(
            operators.filter(self._directory_filter),
            operators.take_until(self._stop),
        ).subscribe(ErrorToConsoleObserver(lambda x: self.initialize_saving_directory()))

        self.initialize_saving_directory()

    @staticmethod
    @config.DefaultSettingRegistration(config_prefix)
    def default_settings(configPrefix):
        config.default_settings(configPrefix, [
            config.SettingRegistry("enabled", False, type="bool", title="Enable data saving"),
            config.SettingRegistry("save_images", True, type="bool", title="Save image"),
            config.SettingRegistry("save_labels", True, type="bool", title="Save labels"),
            config.SettingRegistry("save_events", True, type="bool", title="Save events"),
            config.SettingRegistry("directory", "/tmp", type="str", title="Save directory")
        ])

    def _enable_filter(self, data):
        key = data[0]
        return key == f"{ResultSaver.config_prefix}/enabled"

    def _directory_filter(self, data):
        key = data[0]
        return key == f"{ResultSaver.config_prefix}/directory"

    def initialize_saving_directory(self):
        path = self.config["directory"]

        os.makedirs(path, exist_ok=True)

    def save_image(self, data: AcquiredImage):
        path = os.path.join(self.config["directory"], "images.bin")
        with open(path, "a+b") as f:
            f.write(msgpack.packb({
                "name": data.name,
                "data": data.encoded_buffer,
                "ts": data.time})
            )

    def save_labels(self, data: DetectionsInImage):
        path = os.path.join(self.config["directory"], "labels.bin")
        _detects = []
        for detect in data.objs:
            detect: dict = detect.__dict__.copy()
            detect.pop("mask")
            _detects.append(detect)
        with open(path, "a+b") as f:
            f.write(msgpack.packb({"name": data.image_id, "labels": _detects}))

    def save_timeline_events(self, dp: TimelineDataPoint):
        path = os.path.join(self.config["directory"], "events.bin")
        with open(path, "a+b") as f:
            f.write(msgpack.packb({"time": dp.time, "plot": dp.plot_name, "series": dp.series_name, "value": dp.value}))

    def config_enabled_filter(self, key):
        def f(x=None):
            return self.config["enabled"] and self.config[key]

        return f

    def finalize(self):
        self._stop.on_next(True)
