import glob
import logging
import os
from datetime import datetime
from threading import Condition
import time
import cv2
import rx
from PySide2 import QtCore, QtWidgets
from genicam2.gentl import TimeoutException
from harvesters.core import Buffer
from numpy import random
from rx import operators, disposable, subject, scheduler
from rx.scheduler import ThreadPoolScheduler

import services.service_provider
from data_class.subject_data import AcquiredImage
from services import config
from services.subjects import Subjects
from utils.QtScheduler import QtScheduler
from utils.observer import ErrorToConsoleObserver


class ImageSource(object):
    """
    Image source should decide whether the downstream should backpressure/block itself by using observe_on or not
    """

    def __init__(self):
        super().__init__()
        self.subject_provider = services.service_provider.SubjectProvider()
        self.subjects: Subjects = self.subject_provider.get_or_create_instance(None)

    def start(self):
        self.subjects.image_source_connected.on_next(True)

    def stop(self):
        self.subjects.image_source_connected.on_next(False)

    def is_running(self):
        return self.subjects.image_source_connected.value

    def next_image(self, img: AcquiredImage):
        self.subjects.image_producer.on_next(img)

    def get_name(self):
        raise NotImplementedError()


class MockImageSource(ImageSource):
    config_prefix = "Test_Images"

    def __init__(self):
        super().__init__()
        self.config = config.SettingAccessor(self.config_prefix)
        self.fps = self.config["fps"]
        self.images = self._source_images()
        self._stop = subject.Subject()
        self.running = False
        self.feed_scheduler = ThreadPoolScheduler()

    def get_name(self):
        return "test"

    @staticmethod
    @config.DefaultSettingRegistration(config_prefix)
    def default_settings(config_prefix):
        config.default_settings(config_prefix, [
            config.SettingRegistry("fps", 5, type="int"),
        ])

    @staticmethod
    def _source_images():
        image_path = glob.glob("TestImages/*.png")

        images = []
        for image in image_path:
            image_array = cv2.imread(image, 0)
            images.append(image_array)

        return images

    def generate_image(self):
        idx = random.choice(len(self.images), 1)[0]
        img = self.images[idx]
        return img

    def start(self):
        self.fps = self.config["fps"]
        rx.interval(1 / self.fps).pipe(
            operators.map(lambda x: self.generate_image()),
            operators.map(lambda arr: AcquiredImage(arr, datetime.now().timestamp())),
            operators.take_until(self._stop),
        ).subscribe(ErrorToConsoleObserver(self.next_image))
        self.running = True
        super().start()

    def is_running(self):
        return self.running

    def stop(self):
        self._stop.on_next(None)
        self.running = False
        super().stop()


class HarvestersSource(ImageSource):
    """
    This source disregard analyzer back pressure. User has to control the frame rate.
    """
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

    def get_name(self):
        return "haravesters"

    def is_running(self):
        return self.running

    @staticmethod
    @config.DefaultSettingRegistration(config_prefix)
    def defaultSettings(config_prefix):
        config.default_settings(config_prefix, [
            config.SettingRegistry("cti_path", "/tmp/TL.cti", type="str", title="Path to .cti file"),
            config.SettingRegistry("gain", 0, type="float"),
            config.SettingRegistry("invert_polarity", False, type="bool", title="Invert polarity"),
            config.SettingRegistry("id", "", type="str", title="Camera Id (use camera_id.py)"),
            config.SettingRegistry("fps", 5, type="float", title="frame per second")
        ])

    def _read_buffer(self):
        try:
            buffer: Buffer = self.acquirer.fetch_buffer(timeout=0.1)
            payload = buffer.payload
            component = payload.components[0]
            width = component.width
            height = component.height
            content = component.data.reshape(height, width)
            self.next_image(AcquiredImage(content.copy(), time.time(), f"{time}.jpg"))
            buffer.queue()
        except TimeoutException as ex:
            pass
        except Exception as ex:
            self.logger.error(ex)

    def reload_camera_driver(self):
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

        self.reload_camera_driver()

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


class MediaFileSource(ImageSource):
    """
    Supply image from files.
    This source is back-pressure-pausale
    """

    def __init__(self):
        super().__init__()
        self._stop = subject.Subject()
        self.logger = logging.getLogger("console")
        self.back_pressure_lock = Condition()

    def get_name(self):
        return "file"

    def start(self):
        if not self.subjects.analyzer_connected.value:
            if not self.analyzer_not_connected_prompt():
                return

        qt_scheduler = QtScheduler(QtCore)

        # this sequence is auto-back-pressured
        observable = self.request_media_file(qt_scheduler).pipe(
            # list of files
            operators.observe_on(scheduler.NewThreadScheduler()),
            # The following sequence will be run on a new thread.
            operators.flat_map(rx.from_list),
            # observable of files.
            self.load_file_operator(),  # When back pressure, this one will block.
            # observable of frames (AcquiredImage). This operation will be blocked if the downstream is blocked.
            operators.take_until(self._stop),
        ).subscribe(ErrorToConsoleObserver(on_next=self.next_image, on_error=self._catch))

        self.subjects.analyzer_back_pressure_detected.pipe(
            operators.take_until(self._stop),
        ).subscribe(self.notify_back_pressure_changed)
        super().start()

    def stop(self):
        self._stop.on_next(0)
        super().stop()

    def analyzer_not_connected_prompt(self):
        ret = QtWidgets.QMessageBox.question(
            None,
            "Analyzer not running",
            "The analyzer is not running. Some frames may not be processed. Do you want to proceed?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )
        if ret == QtWidgets.QMessageBox.Yes:
            return True
        else:
            return False

    def request_media_file(self, sch) -> rx.Observable:
        def subscribe(observer, subscriber_scheduler: rx.typing.Scheduler = None):
            def _subscribe(*args):
                files = QtWidgets.QFileDialog.getOpenFileNames(None, "Select media file(s)")
                observer.on_next(files[0])
                observer.on_completed()

            sch.schedule(_subscribe)
            return disposable.Disposable(lambda: None)

        return rx.create(subscribe)

    def _catch(self, ex):
        self.logger.error(ex)
        self.logger.info("Error occured. Stopping image source.")
        self.stop()

    def load_file_operator(self):
        def upstream(source):
            def subscribe(observer, sche=None):
                def _subscribe(next_path):
                    # back pressure blocking
                    with self.back_pressure_lock:
                        self.back_pressure_lock.wait_for(
                            lambda: not self.subjects.analyzer_back_pressure_detected.value)
                    _, ext = os.path.splitext(next_path)
                    if ext in (".png", ".jpeg", ".jpg", ".bmp", ".tiff", ".tif"):
                        # is a image file
                        frame = cv2.imread(next_path, cv2.cv2.IMREAD_GRAYSCALE)
                        name = os.path.basename(next_path)
                        t = os.path.getctime(next_path)

                        observer.on_next(AcquiredImage(frame, name=name, time=t))
                    elif ext in (".mov", ".mp4", ".avi"):
                        # is a video file
                        cap = cv2.VideoCapture(next_path)
                        try:
                            stop = False
                            if not cap.isOpened():
                                raise RuntimeError(f"Failed to load video file: {next_path}")

                            while True:
                                if stop:
                                    raise InterruptedError(f"Interrupt processing {next_path}.")
                                ret, frame = cap.read()
                                if frame is None:
                                    observer.on_completed()
                                    break
                                observer.on_next(frame)
                        finally:
                            cap.release()

                return source.subscribe(_subscribe, sche)

            return rx.create(subscribe)

        return upstream

    def notify_back_pressure_changed(self, x):
        if not x:
            with self.back_pressure_lock:
                self.back_pressure_lock.notify_all()