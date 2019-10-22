import logging
import traceback
from abc import ABCMeta, abstractmethod

from rx import operators, subject

from services import config
import serial

import services.service_provider
from services.subjects import Subjects


class CameraPeripheralControlParams(object):
    def __init__(self, pulse_width_tick: int = None, digital_filter: int = None, start_delay: int = None,
                 power: int = None, trigger: bool = None):
        self.trigger = trigger
        self.power = power
        self.digital_filter = digital_filter
        self.pulse_width_tick = pulse_width_tick
        self.start_delay = start_delay


class CameraPeripheralControl(object, metaclass=ABCMeta):
    def start(self):
        pass

    def stop(self):
        pass

    def is_running(self) -> bool:
        pass

    def set_power(self, enabled: bool):
        pass

    def set_params(self, param: CameraPeripheralControlParams):
        pass

    def set_trigger(self, enabled: bool):
        pass

    @abstractmethod
    def get_state(self):
        pass


class SerialCameraPeripheralControl(CameraPeripheralControl):
    serial: serial.Serial
    config_prefix = "SerialCameraPeripheralControl"

    def __init__(self):
        super(SerialCameraPeripheralControl, self).__init__()
        self.config = config.SettingAccessor(self.config_prefix)
        self.serial = serial.Serial()
        self.logger = logging.getLogger("console")
        self.stored_parameters = CameraPeripheralControlParams()
        self._stop = subject.Subject()

    @staticmethod
    @config.DefaultSettingRegistration(config_prefix)
    def default_settings(config_prefix):
        config.default_settings(config_prefix, [
            config.SettingRegistry("serial_port", "", type="str", title="Serial port"),
            config.SettingRegistry("baud", 115200, type="int", title="Baud rate"),
        ])

    def start(self):
        self._stop = subject.Subject()

        try:
            self.serial = serial.Serial(self.config["serial_port"], baudrate=self.config["baud"])
        except Exception as ex:
            self.logger.error(f"Failed to open {self.config['serial_port']}.")
            self.logger.debug(ex)
            return

        self.subjects: Subjects = services.service_provider.SubjectProvider().get_or_create_instance(None)
        self.subjects.simex_camera_peripheral_control.pipe(
            operators.take_until(self._stop)
        ).subscribe(self.simex_recv)

        self.logger.info("Successfully connect to camera peripheral control.")
        super().start()

    def stop(self):
        if self.serial:
            self.serial.close()

        self.logger.info("Successfully disconnect from camera peripheral control")
        super().stop()

    def set_power(self, enabled: bool):
        try:
            self.guard_serial_open()

            val = 1 if enabled else 0
            if self.stored_parameters.power != val and val is not None:
                self.stored_parameters.power = val
                self.serial.write(f"s_power {val}\n".encode())
        except Exception as ex:
            self.logger.error(f"Failed to set power: {ex}")
            self.logger.debug(traceback.format_exc())

    def is_running(self) -> bool:
        if not self.serial:
            return False

        return self.serial.isOpen()

    def set_params(self, param: CameraPeripheralControlParams):
        try:
            self.guard_serial_open()

            if self.stored_parameters is None:
                self.stored_parameters = CameraPeripheralControlParams(None, None, None)

            if param.digital_filter != self.stored_parameters.digital_filter and param.digital_filter is not None:
                self.stored_parameters.digital_filter = param.digital_filter
                self.serial.write(f"s_filter {param.digital_filter}\ncommit\n".encode())
                self.logger.debug(f"digital filter updated to {param.digital_filter}")
            if param.pulse_width_tick != self.stored_parameters.pulse_width_tick and param.pulse_width_tick is not None:
                self.stored_parameters.pulse_width_tick = param.pulse_width_tick
                self.serial.write(f"s_exposure {param.pulse_width_tick}\ncommit\n".encode())
                self.logger.debug(f"Pulse width updated to {param.pulse_width_tick}")
            if param.start_delay != self.stored_parameters.start_delay and param.start_delay is not None:
                self.stored_parameters.start_delay = param.start_delay
                self.serial.write(f"s_delay {param.start_delay}\ncommit\n".encode())
                self.logger.debug(f"Start delay updated to {param.start_delay}")
        except Exception as ex:
            self.logger.error(f"Failed to set parameters: {ex}")
            self.logger.debug(traceback.format_exc())

    def set_trigger(self, enabled: bool):
        try:
            self.guard_serial_open()
            if self.stored_parameters.trigger != enabled and enabled is not None:
                if enabled:
                    self.serial.write("arm_trigger\n".encode())
                else:
                    self.serial.write("disarm_trigger\n".encode())
                self.stored_parameters.trigger = enabled
                super().set_trigger(enabled)
        except Exception as ex:
            self.logger.error(f"Failed to set trigger: {ex}")
            self.logger.debug(traceback.format_exc())

    def guard_serial_open(self):
        if not self.serial.isOpen():
            raise RuntimeError("Serial port not opened.")

    def get_state(self):
        return self.stored_parameters

    def simex_recv(self, x: CameraPeripheralControlParams):
        if x.power is not None:
            self.set_power(bool(x.power))
        if x.trigger is not None:
            self.set_trigger(bool(x.trigger))
        if x.pulse_width_tick is not None:
            self.set_params(x)