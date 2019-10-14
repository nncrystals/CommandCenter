import logging
import time
import typing

import numpy as np
from rx import operators
from rx import scheduler
from rx import subject

import inference_service_proto.inference_service_pb2 as grpc_def
import services.service_provider
from data_class.detected_objects import DetectedObject
from data_class.subject_data import AcquiredImage, DetectionsInImage, SampleImageData
from services import config
from services.inference_comm import InferenceComm
from services.subjects import Subjects
from utils.observer import ErrorToConsoleObserver


class Analyzer(object):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.subjects: Subjects = services.service_provider.SubjectProvider().get_or_create_instance(None)

    def is_running(self):
        pass

    def start(self):
        pass

    def stop(self):
        pass

    def update_back_pressure_status(self, is_back_pressure: bool):
        self.subjects.analyzer_back_pressure_detected.on_next(is_back_pressure)

    def produce_detected_results(self, detected_objects: DetectionsInImage):
        self.subjects.detection_result.on_next(detected_objects)

    def produce_sample_image_data(self, data: SampleImageData):
        self.subjects.sample_image_data.on_next(data)


class RemoteAnalyzer(Analyzer):
    config_prefix = "Remote_Analyzer"

    def __init__(self, *args, **kwargs):
        super().__init__()

        self.config = config.SettingAccessor(self.config_prefix)
        self.logger = logging.getLogger("console")
        self.batch_size = self.config["batch_size"]
        self.inference_comm = InferenceComm()
        self._stop = subject.Subject()
        self.feed_scheduler = scheduler.ThreadPoolScheduler()
        self.process_scheduler = scheduler.ThreadPoolScheduler()
        self.subject_provider = services.service_provider.SubjectProvider()
        self.subjects: Subjects = self.subject_provider.get_or_create_instance(None)

    @staticmethod
    @config.DefaultSettingRegistration(config_prefix)
    def defaultSettings(configPrefix):
        config.default_settings(configPrefix, [
            config.SettingRegistry("ip", "127.0.0.1"),
            config.SettingRegistry("port", "3034"),
            config.SettingRegistry("batch_size", 5, type="int", title="Inference batch size"),
        ])

    def configure_subscriptions(self, connected):
        if connected:
            self.subjects.image_producer.pipe(
                operators.observe_on(self.feed_scheduler),
                operators.filter(lambda x: not self.subjects.analyzer_back_pressure_detected.value),
                operators.buffer_with_count(self.batch_size),
                operators.take_until(self._stop),
            ).subscribe(ErrorToConsoleObserver(self.feed_image))

            self.inference_comm.back_pressure_chan.pipe(
                operators.subscribe_on(self.process_scheduler),
                operators.take_until(self._stop)
            ).subscribe(ErrorToConsoleObserver(self.update_back_pressure_status))

            # report error when image source is still producing when back pressuring
            self.subjects.analyzer_back_pressure_detected.pipe(
                operators.combine_latest(self.subjects.image_producer),
                operators.map(lambda x: x[0]),
                operators.throttle_with_timeout(1.0),
                operators.take_until(self._stop),
            ).subscribe(ErrorToConsoleObserver(
                lambda x: print("Image is feeding while back-pressure is detected. Please slow down the FPS")))

            self.inference_comm.result_chan.pipe(
                operators.subscribe_on(self.process_scheduler),
                operators.take_until(self._stop)
            ).subscribe(ErrorToConsoleObserver(self.result_processing))

            self.inference_comm.error_chan.pipe(operators.take_until(self._stop)).subscribe(
                ErrorToConsoleObserver(lambda err: self.logger.error(err))
            )
            self.inference_comm.connection_chan.pipe(operators.take_until(self._stop)).subscribe(
                ErrorToConsoleObserver(lambda connected: self.logger.info(
                    "GRPC Remote analyzer connected" if connected else "GRPC Remote analyzer disconnected"
                )))
            self.inference_comm.stats_chan.take_until(self._stop).subscribe(
                ErrorToConsoleObserver(
                    lambda x: self.logger.info(f"Processed {x.frame} frames. Average {x.processTime / x.frame} secs"))
            )

    def is_running(self):
        return self.inference_comm.connection_chan.value

    def start(self):
        if self.is_running():
            self.logger.warning("GRPC remote inference server is already connected.")
            return
        self.inference_comm.connection_chan.pipe(operators.take_until(self._stop)).subscribe(
            ErrorToConsoleObserver(self.configure_subscriptions))
        self.inference_comm.connect_to_grpc_server(self.config["ip"], self.config["port"])

    def clean(self):
        self.inference_comm.stop()

    def stop(self):
        self.clean()
        self._stop.on_next(True)
        self._stop.on_completed()
        super().stop()

    def feed_image(self, acquired_images: typing.Iterable[AcquiredImage]):
        try:
            images_to_feed = []
            for images in acquired_images:
                images_to_feed.append((images.encoded_buffer, images.name))

            self.inference_comm.feed_images(images_to_feed)

        except Exception as e:
            self.logger.error(f"Failed to feed image: {e}")

    def result_processing(self, result: grpc_def.InferenceResult):
        # Emit result objects
        sample_image_ids = []
        results_to_render = {}
        image_data_to_render = {}
        for r in result.returned_images:
            sample_image_ids.append(r.name)
            image_data_to_render[r.name] = r.images_data

        results_per_image: grpc_def.ResultPerImage
        for results_per_image in result.result:
            results = []
            for detection in results_per_image.detections:
                detected_object = InferenceComm.to_detected_object(detection)
                results.append(detected_object)
            image_id = results_per_image.image_id
            self.produce_detected_results(DetectionsInImage(image_id, results))
            if image_id in sample_image_ids:
                results_to_render[image_id] = results

        for image_id, detections in results_to_render.items():
            img = image_data_to_render[image_id]
            self.produce_sample_image_data(SampleImageData(img, detections))


class TestAnalyzer(Analyzer):
    def __init__(self):
        super().__init__()
        self.queue_length = 0
        self.running = False
        self._stop = subject.Subject()

    def is_running(self):
        return self.running

    def start(self):
        self.running = True

        def increment(x):
            self.queue_length += 1
            if self.queue_length > 2:
                self.update_back_pressure_status(True)

        self.subjects.image_producer.pipe(
            operators.filter(lambda x: not self.subjects.analyzer_back_pressure_detected.value),
            operators.buffer_with_count(5),
            operators.do_action(increment),
            operators.delay(1.0),
            operators.take_until(self._stop)
        ).subscribe(ErrorToConsoleObserver(self.produce_fake_analyze_data))

    def stop(self):
        self.running = False
        self._stop.on_next(9)

    def produce_fake_analyze_data(self, x: typing.List[AcquiredImage]):
        from pycocotools import mask as mask_util

        self.queue_length -= 1
        self.update_back_pressure_status(False)
        fake_obj = DetectedObject()
        canvas = np.zeros((600, 800), dtype=np.uint8)
        canvas[10:30, 10:30] = True
        rle = mask_util.encode(np.asfortranarray(canvas))
        fake_obj.maskRLE = rle
        fake_obj.mask = canvas
        fake_obj.bbox = mask_util.toBbox(rle).tolist()
        fake_obj.label = 1
        fake_obj.score = 1

        objs = [fake_obj]
        self.produce_sample_image_data(
            SampleImageData(
                x[0].encoded_buffer,
                objs
            )
        )

        for data in x:
            self.produce_detected_results(DetectionsInImage(data.name, objs))
