import logging

from services import config
import serial


class CameraPeripheralControlParams(object):
    def __init__(self, pulse_width_tick: int, digital_filter: int, start_delay: int):
        self.digital_filter = digital_filter
        self.pulse_width_tick = pulse_width_tick
        self.start_delay = start_delay


class CameraPeripheralControl(object):
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


class SerialCameraPeripheralControl(CameraPeripheralControl):
    serial: serial.Serial
    config_prefix = "SerialCameraPeripheralControl"

    def __init__(self):
        super(SerialCameraPeripheralControl, self).__init__()
        self.config = config.SettingAccessor(self.config_prefix)
        self.serial = None
        self.logger = logging.getLogger("console")
        self.stored_parameters = None

    @staticmethod
    @config.DefaultSettingRegistration(config_prefix)
    def default_settings(config_prefix):
        config.default_settings(config_prefix, [
            config.SettingRegistry("serial_port", "", type="str", title="Serial port"),
            config.SettingRegistry("baud", 115200, type="int", title="Baud rate"),
        ])

    def start(self):
        self.serial = serial.Serial(self.config["serial_port"], baudrate=self.config["baud"])
        try:
            self.serial.open()
        except Exception as ex:
            self.logger.error(f"Failed to open {self.config['serial_port']}.")
            self.logger.debug(ex)
            return

        super().start()

    def stop(self):
        if self.serial:
            self.serial.close()
        super().stop()

    def set_power(self, enabled: bool):
        self.guard_serial_open()

        val = 1 if enabled else 0
        self.serial.write(f"s_power {val}\n")

    def is_running(self) -> bool:
        if not self.serial:
            return False

        return self.serial.isOpen()

    def set_params(self, param: CameraPeripheralControlParams):
        self.guard_serial_open()

        if self.stored_parameters is None:
            self.stored_parameters = CameraPeripheralControlParams(None, None, None)

        if param.digital_filter != self.stored_parameters.digital_filter:
            self.stored_parameters.digital_filter = param.digital_filter
            self.serial.write(f"s_filter {param.digital_filter}\ncommit\n")
            self.logger.debug(f"digital filter updated to {param.digital_filter}")
        if param.pulse_width_tick != self.stored_parameters.pulse_width_tick:
            self.stored_parameters.pulse_width_tick = param.pulse_width_tick
            self.serial.write(f"s_exposure {param.pulse_width_tick}\ncommit\n")
            self.logger.debug(f"Pulse width updated to {param.pulse_width_tick}")
        if param.start_delay != self.stored_parameters.start_delay:
            self.stored_parameters.start_delay = param.start_delay
            self.serial.write(f"s_delay {param.start_delay}\ncommit\n")
            self.logger.debug(f"Start delay updated to {param.start_delay}")

    def set_trigger(self, enabled: bool):
        if enabled:
            self.serial.write("arm_trigger\n")
        else:
            self.serial.write("disarm_trigger\n")
        super().set_trigger(enabled)

    def guard_serial_open(self):
        if not self.serial and not self.serial.isOpen():
            raise RuntimeError("Serial port not opened.")