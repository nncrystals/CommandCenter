import os

import msgpack
from rx import operators, subject

from services import config
import services.service_provider
from services.subjects import Subjects


class ResultSaver(object):
    config_prefix = "ResultSaver"

    def __init__(self):
        super(ResultSaver, self).__init__()

        self._stop = subject.Subject()
        self.config = config.SettingAccessor(self.config_prefix)
        self.subjects: Subjects = services.service_provider.SubjectProvider().get_or_create_instance(None)
        self.subjects.images_to_save.pipe(
            operators.filter(self.image_save_enabled_filter),
            operators.take_until(self._stop),
        ).subscribe(self.save_image)
        self.subjects.detection_result.pipe(
            operators.filter(self.label_save_enabled_filter),
            operators.take_until(self._stop),
        ).subscribe(self.save_labels)

        config.setting_updated_channel.pipe(
            operators.filter(self._directory_filter),
            operators.take_until(self._stop),
        ).subscribe(lambda x: self.initialize_saving_directory())

        self.initialize_saving_directory()

    @staticmethod
    @config.DefaultSettingRegistration(config_prefix)
    def default_settings(configPrefix):
        config.default_settings(configPrefix, [
            config.SettingRegistry("enabled", False, type="bool", title="Enable"),
            config.SettingRegistry("save_image", True, type="bool", title="Save image"),
            config.SettingRegistry("save_labels", True, type="bool", title="Save labels"),
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
        imageDir = os.path.join(path, "images")
        labelDir = os.path.join(path, "labels")

        os.makedirs(path, exist_ok=True)
        os.makedirs(imageDir, exist_ok=True)
        os.makedirs(labelDir, exist_ok=True)

    def save_image(self, imageAndName):
        data, name = imageAndName["data"], imageAndName["name"]
        path = os.path.join(self.config["directory"], "images", "images.bin")
        with open(path, "a+b") as f:
            f.write(msgpack.packb({"name": name, "data": data}))

    def save_labels(self, detectsAndName):
        detects, name = detectsAndName
        path = os.path.join(self.config["directory"], "labels", "labels.bin")
        _detects = []
        for detect in detects:
            detect: dict = detect.__dict__.copy()
            detect.pop("mask")
            _detects.append(detect)
        with open(path, "a+b") as f:
            f.write(msgpack.packb({"name": name, "labels": _detects}))

    def image_save_enabled_filter(self, x=None):
        return self.config["enabled"] and self.config["save_image"]

    def label_save_enabled_filter(self, x=None):
        return self.config["enabled"] and self.config["save_labels"]

    def finalize(self):
        self._stop.on_next(True)