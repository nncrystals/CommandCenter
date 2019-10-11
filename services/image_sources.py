import glob
import glob
import logging

import numpy as np
import rx
from PIL import Image
from genicam2.gentl import TimeoutException
from numpy import random
from rx import operators, disposable, scheduler
from rx import subject

import services.service_provider
from services import config
from services.subjects import Subjects


class ImageSource(object):

    def __init__(self):
        super().__init__()
        self.subject_provider = services.service_provider.SubjectProvider()
        self.subjects: Subjects = self.subject_provider.get_or_create_instance(None)


    def start(self):
        self.subjects.image_source_connected.on_next(True)

    def stop(self):
        self.subjects.image_source_connected.on_next(False)

    def is_running(self):
        pass

    def next_image(self, arr):
        self.subjects.image_producer.on_next(arr)


class MockImageSource(ImageSource):
    config_prefix = "Test_Images"
    def __init__(self):
        super().__init__()
        self.config = config.SettingAccessor(self.config_prefix)
        self.fps = self.config["fps"]
        self.images = self._sourceImages()
        self._stop = subject.Subject()
        self.running = False

    @staticmethod
    @config.DefaultSettingRegistration(config_prefix)
    def defaultSettings(configPrefix):
        config.default_settings(configPrefix, [
            config.SettingRegistry("fps", 5, type="int"),
        ])

    @staticmethod
    def _sourceImages():
        image_path = glob.glob("TestImages/*.png")
        images = [(np.asarray(Image.open(image))[:, :, 1]) for image in image_path]
        return images

    def generate_image(self):
        idx = random.choice(len(self.images), 1)[0]
        img = self.images[idx]
        return img

    def start(self):
        self.fps = self.config["fps"]
        rx.interval(1 / self.fps).pipe(
            operators.map(lambda x: self.generate_image()),
            operators.take_until(self._stop),
        ).subscribe(self.next_image)
        self.running = True

    def is_running(self):
        return self.running

    def stop(self):
        self._stop.on_next(None)
        self.running = False


class HarvestersSource(ImageSource):
    config_prefix = "Harvesters_Source"

    def __init__(self):
        from harvesters.core import Harvester

        super().__init__()
        self.config = config.SettingAccessor(self.config_prefix)
        self.logger = logging.getLogger("console")
        self._stop = subject.Subject()
        self.driver = Harvester()
        self.driver.add_cti_file(self.config["cti_path"])
        self.acquirer = None
        self.simex_instance = None
        self.running = False
        self.scheduler = scheduler.NewThreadScheduler()
        self.scheduler.schedule(lambda sc, state: self.driver.update_device_info_list())

    def is_running(self):
        return self.running

    @staticmethod
    @config.DefaultSettingRegistration(config_prefix)
    def defaultSettings(configPrefix):
        config.default_settings(configPrefix, [
            config.SettingRegistry("cti_path", "/tmp/TL.cti", type="str", title="Path to .cti file"),
            config.SettingRegistry("gain", 0, type="float"),
            config.SettingRegistry("invert_polarity", False, type="bool", title="Invert polarity"),
            config.SettingRegistry("id", "", type="str", title="Camera Id (use camera_id.py)"),
            config.SettingRegistry("fps", 5, type="float", title="frame per second")
        ])

    def _read_buffer(self):
        try:
            buffer = self.acquirer.fetch_buffer(timeout=0.1)
            payload = buffer.payload
            component = payload.components[0]
            width = component.width
            height = component.height
            content = component.data.reshape(height, width)
            self.next_image(content.copy())
            buffer.queue()
        except TimeoutException as ex:
            pass
        except Exception as ex:
            self.logger.error(ex)

    def reloadCameraDriver(self):
        id_ = self.config["id"]
        if not id_:
            self.acquirer = self.driver.create_image_acquirer(list_index=0)
        else:
            self.acquirer = self.driver.create_image_acquirer(id_=id)

        self.acquirer.on_new_buffer_arrival = self._read_buffer
        node = self.acquirer.device.node_map
        node.LineSelector.value = 'Line1'
        node.LineMode.value = 'Output'
        node.LineInverter.value = True
        node.LineSource.value = "ExposureActive"
        node.ExposureTime.value = 45.0
        node.AcquisitionFrameRateMode.value = "Basic"
        node.AcquisitionFrameRate.value = self.config["fps"]

    def start(self):
        super().start()

        self.reloadCameraDriver()

        if self.acquirer:
            self.acquirer.start_image_acquisition()

        self.running = True

    def stop(self):
        if self.acquirer:
            self.acquirer.stop_image_acquisition()
            self.acquirer.destroy()
        self._stop.on_next(True)
        self.running = False
        super().stop()
