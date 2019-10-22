import enum
import logging
import time
from typing import List

import numpy as np
import rx
import simex
from rx import operators, subject, scheduler
from rx.disposable import Disposable
from simex import SimexPort

from services import config
import services.service_provider
from services.camera_peripheral_control import CameraPeripheralControlParams
from services.subjects import Subjects
from utils.observer import ErrorToConsoleObserver


class OutputPorts(enum.Enum):
    BRIGHTNESS = 0


class InputPorts(enum.Enum):
    EXPOSURE = 0
    POWER = 1
    TRIGGER = 2
    SLURRY_PUMP = 3
    CLEAR_PUMP = 4


class SimexIO(object):
    config_prefix = "SimexIO"
    image_feed_chan_in = subject.Subject()
    camera_temperature_chan_in = subject.Subject()

    def __init__(self):
        self.logger = logging.getLogger("console")
        self.config = config.SettingAccessor(self.config_prefix)
        self.logger.debug(f"Simex address = {self.config['ip']}:{self.config['port']}")
        self.instance = simex.SimexRemote(self.config['ip'], self.config['port'])
        self.connected = subject.BehaviorSubject(False)
        self.execution_thread = scheduler.NewThreadScheduler()
        self.subjects: Subjects = services.service_provider.SubjectProvider().get_or_create_instance(None)
        self._stop = subject.Subject()

    @staticmethod
    @config.DefaultSettingRegistration(config_prefix)
    def default_settings(configPrefix):
        config.default_settings(configPrefix, [
            config.SettingRegistry("ip", "127.0.0.1", type="str", title="Block server IP"),
            config.SettingRegistry("port", 12305, type="int", title="Block server port"),
            config.SettingRegistry("buffer_count", 5, type="int", title="Image statistics averaging window size"),
            config.SettingRegistry("temperature_sample_time", 1.0, type="float",
                                   title="Temperature report sample time(sec)"),
        ])

    def connect(self):
        if self.instance.is_connected:
            error_message = "SimexIO is already connected."
            self.logger.warning(error_message)
            return rx.throw(RuntimeError(error_message))

        def subscribe(observer: rx.typing.Observer, scheduler=None):
            try:
                self.logger.debug("connecting to SimexIO")
                self.instance.connect()
            except Exception as ex:
                self.logger.error(f"Failed to connect to SimexIO. Exception: {ex}")
                return

            self._simex_configure_subscription()

            return Disposable(lambda: None)

        return rx.create(subscribe)

    def disconnect(self):
        if not self.instance.is_connected:
            self.logger.warning("SimexIO is not connected. Cannot disconnect.")
            return

        try:
            self.logger.debug("disconnecting SimexIO")
            self.instance.disconnect()
            self._stop.on_next(None)
            self.connected.on_next(False)
        except Exception as ex:
            self.logger.error(f"Failed to disconnect SimexIO. Exception: {ex}")

    def _simex_verify_version_cb(self, x=None):
        if not x:
            raise RuntimeError("Simex server compatibility verification failed")
        else:
            # verify port configuration
            return self.instance.request_info()

    def _simex_connect_error_cb(self, err=None):
        self.logger.error(f"Exception occured in SimexIO validation chain: {err}")

    def _simex_configure_subscription(self, x=None):
        self.subjects.image_producer.pipe(
            operators.observe_on(self.execution_thread),
            operators.map(lambda acquired_image: acquired_image.image),  # pluck the image array
            operators.map(lambda im: np.median(im)),
            operators.buffer_with_count(self.config["buffer_count"]),
            operators.map(lambda medians: np.mean(medians)),
            operators.take_until(self._stop)
        ).subscribe(
            ErrorToConsoleObserver(
                lambda t: self.instance.request_port_update(
                    OutputPorts.BRIGHTNESS.value,
                    np.asarray(t, dtype=np.float64)
                ).subscribe(ErrorToConsoleObserver()))
        )

        self.instance.input_port_updated.pipe(
            operators.observe_on(self.execution_thread),
            operators.take_until(self._stop)
        ).subscribe(ErrorToConsoleObserver(self.input_port_updated))

    def input_port_updated(self, x: List[SimexPort]):
        try:
            self.subjects.simex_camera_peripheral_control.on_next(
                CameraPeripheralControlParams(pulse_width_tick=int(x[0].data), power=int(x[1].data),
                                              trigger=bool(x[2].data)))
            self.subjects.simex_pump_control.on_next(
                [int(x[3].data), int(x[4].data)]
            )
        except:
            pass

if __name__ == '__main__':
    def update(x=None):
        print("update!")
        simio.instance.request_port_update(0, np.array([133], dtype=np.float64)).subscribe(ErrorToConsoleObserver())


    simio = SimexIO()
    simio.connect().subscribe(ErrorToConsoleObserver(update))
    time.sleep(1)
