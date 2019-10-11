import logging
import time
import typing

import numpy as np
import turbojpeg as tj
from rx import operators
from rx import scheduler
from rx import subject

import inference_service_proto.inference_service_pb2 as grpc_def
import services.service_provider
from services import config
from services.inference_comm import InferenceComm
from services.subjects import Subjects


class Analyzer(object):
    def __init__(self, *args, **kwargs):
        super().__init__()

    def is_running(self):
        pass

    def start(self):
        pass

    def stop(self):
        pass


class RemoteAnalyzer(Analyzer):
    config_prefix = "Remote_Analyzer"

    def __init__(self, *args, **kwargs):
        super().__init__()

        self.config = config.SettingAccessor(self.config_prefix)
        self.logger = logging.getLogger("console")
        self.encoder = tj.TurboJPEG(self.config["turbo_jpeg_library"])
        self.batch_size = self.config["batch_size"]
        self.inference_comm = InferenceComm()
        self._stop = subject.Subject()
        self.feed_scheduler = scheduler.NewThreadScheduler()
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
            config.SettingRegistry("turbo_jpeg_library", "/usr/lib/x86_64-linux-gnu/libturbojpeg.so.0",
                                   type="str", title="Path to TurboJPEG library"),
        ])

    def configure_subscriptions(self, connected):
        if connected:
            self.subjects.image_producer \
                .pipe(operators.filter(self.inference_comm.back_pressure_detection)) \
                .pipe(operators.buffer_with_count(self.batch_size)) \
                .pipe(operators.subscribe_on(self.feed_scheduler)) \
                .pipe(operators.take_until(self._stop)) \
                .subscribe(self.feed_image)

            self.subjects.image_producer \
                .pipe(operators.filter(lambda x: not self.inference_comm.back_pressure_detection(x))) \
                .pipe(operators.throttle_first(1)) \
                .pipe(operators.take_until(self._stop)) \
                .subscribe(lambda x: self.logger.warning(
                    "Back pressure detected. Some frames were dropped. Please reduce the image acquisition fps."
                ))

            self.inference_comm.result_chan \
                .pipe(operators.subscribe_on(self.process_scheduler), operators.take_until(self._stop)) \
                .subscribe(self.result_processing)

            self.inference_comm.error_chan.pipe(operators.take_until(self._stop)).subscribe(
                lambda err: self.logger.error(err))
            self.inference_comm.connection_chan.pipe(operators.take_until(self._stop)).subscribe(
                lambda connected: self.logger.info(
                    "GRPC Remote analyzer connected" if connected else "GRPC Remote analyzer disconnected"
                ))
            self.inference_comm.stats_chan.take_until(self._stop).subscribe(
                lambda x: self.logger.info(f"Processed {x.frame} frames. Average {x.processTime / x.frame} secs"))

    def is_running(self):
        return self.inference_comm.connection_chan.value

    def start(self):
        if self.is_running():
            self.logger.warning("GRPC remote inference server is already connected.")
            return
        self.inference_comm.connection_chan.pipe(operators.take_until(self._stop)).subscribe(
            self.configure_subscriptions)
        self.inference_comm.connect_to_grpc_server(self.config["ip"], self.config["port"])

    def clean(self):
        self.inference_comm.stop()

    def stop(self):
        self.clean()
        self._stop.on_next(True)
        self._stop.on_completed()
        super().stop()

    def feed_image(self, images: typing.Iterable[np.ndarray]):
        try:
            images = [image[:, :, np.newaxis] for image in images if len(image.shape) == 2]
            images = [(self.encoder.encode(image, quality=90, jpeg_subsample=tj.TJSAMP_GRAY), f"{time.time_ns()}.jpg")
                      for image in images]

            for im, name in images:
                self.subjects.images_to_save.on_next({"data": im, "name": name})

            self.inference_comm.feed_images(images)
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
            self.subjects.detection_result.on_next((results, image_id))
            if image_id in sample_image_ids:
                results_to_render[image_id] = results

        for image_id, detections in results_to_render.items():
            img = image_data_to_render[image_id]
            self.subjects.sample_image_data.on_next((img, detections))
