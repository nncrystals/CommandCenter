import logging
import math
import struct
import queue
import time
import traceback

from pymodbus.client.sync import ModbusSerialClient
from rx import scheduler, subject, operators

import services
from services import config
from services.subjects import Subjects


class PumpControl(object):
    def start(self):
        pass

    def stop(self):
        pass

    def is_running(self) -> bool:
        pass

    def set_speed(self, slurry_speed, clear_speed):
        pass

    def get_state(self):
        pass


class ModBusPumpControl(PumpControl):
    tq: subject.Subject
    client: ModbusSerialClient
    config_prefix = "PumpControl"

    def __init__(self):
        self._stop = None
        self.config = config.SettingAccessor(self.config_prefix)
        self.client = None
        self.tq = None
        self.running = False
        self.state = [0.0, 0.0]
        self.logger = logging.getLogger("console")
        self.scheduler = scheduler.ThreadPoolScheduler(1)

    def get_state(self):
        return self.state

    @staticmethod
    @config.DefaultSettingRegistration(config_prefix)
    def default_settings(config_prefix):
        config.default_settings(config_prefix, [
            config.SettingRegistry("serial_port", "", type="str", title="Serial port"),
            config.SettingRegistry("baud", 9600, type="int", title="Baud rate"),
            config.SettingRegistry("slurry_pump_addr", 192, type="int", title="Slurry pump address"),
            config.SettingRegistry("clear_pump_addr", 200, type="int", title="Clear pump address"),
            config.SettingRegistry("ctrl_delay", 0.5, type="float", title="Control delay (s)"),
            config.SettingRegistry("timeout", 1.0, type="float", title="timeout (s)"),
        ])

    def start(self):
        if self.is_running():
            self.logger.warning("Pump control is already running.")
            return
        self._stop = subject.Subject()
        self.tq = subject.Subject()

        def on_next(job):
            try:
                job()
            except Exception as ex:
                self.logger.error(ex)

        self.tq.pipe(operators.observe_on(self.scheduler)).subscribe(
            on_next,
            lambda ex: self.logger.error(ex),
            lambda: self.client.close()
        )
        self.client = ModbusSerialClient(method='rtu', port=self.config["serial_port"], timeout=self.config["timeout"],
                                         baudrate=self.config["baud"])
        self.client.connect()
        self.enable_remote_control()

        # todo switch
        self.subjects: Subjects = services.service_provider.SubjectProvider().get_or_create_instance(None)
        self.subjects.pump_control.pipe(
            operators.debounce(1.0),
            operators.take_until(self._stop),
        ).subscribe(lambda x: self.set_speed(*x))


        self.running = True
        self.logger.info("Pump control started.")
        super().start()

    def stop(self):
        self.tq.on_next(lambda: self.tq.on_completed())
        self.running = False
        self.logger.info("Pump control stopped.")
        super().stop()

    def is_running(self) -> bool:
        if self.tq is None:
            return False
        elif self.tq.is_stopped:
            return False
        else:
            return True

    def set_speed(self, slurry_speed, clear_speed):
        if not self.is_running():
            raise RuntimeError("Pump control is not connected")
        if slurry_speed is not None and slurry_speed != self.state[0]:
            self.ctrl_pump(self.config["slurry_pump_addr"], slurry_speed)
            self.logger.info(f"Slurry pump speed updated: {slurry_speed}")
            self.state[0] = slurry_speed
        if clear_speed is not None and clear_speed != self.state[1]:
            self.ctrl_pump(self.config["clear_pump_addr"], clear_speed)
            self.logger.info(f"Clear pump speed updated: {clear_speed}")
            self.state[1] = clear_speed

    def enable_remote_control(self, enable=True):
        def _enable_remote_control(unit, enable=True):
            self.tq.on_next(lambda: self.client.write_coil(0x1004, 1 if enable else 0, unit=unit))
            self.tq.on_next(lambda: time.sleep(self.config["ctrl_delay"]))

        _enable_remote_control(self.config["slurry_pump_addr"], enable)
        _enable_remote_control(self.config["clear_pump_addr"], enable)

    def ctrl_pump(self, unit, speed):
        def start_pump(unit, enable=True):
            self.tq.on_next(lambda: self.client.write_coil(0x1001, 1 if enable else 0, unit=unit))
            self.tq.on_next(lambda: time.sleep(self.config["ctrl_delay"]))

        def direction(unit, direction=True):
            self.tq.on_next(lambda: self.client.write_coil(0x1003, 65280 if direction else 0, unit=unit))
            self.tq.on_next(lambda: time.sleep(self.config["ctrl_delay"]))

        def rate(unit, speed):
            buffer = struct.pack("f", math.fabs(speed))
            lb = struct.unpack("<H", buffer[0:2])[0]
            hb = struct.unpack("<H", buffer[2:4])[0]
            self.tq.on_next(lambda: self.client.write_registers(0x3001, [hb, lb], unit=unit))
            self.tq.on_next(lambda: time.sleep(self.config["ctrl_delay"]))

        # stop pump first otherwise cannot adjust direction
        start_pump(unit, False)

        rate(unit, speed)
        if speed == 0:
            return
        direction(unit, speed > 0)
        start_pump(unit, True)

if __name__ == '__main__':
    ctrl = ModBusPumpControl()
    ctrl.start()
    time.sleep(3)
    ctrl.set_speed(10.0, 20.0)
    time.sleep(3)
    ctrl.set_speed(-10.0, -20.0)
    time.sleep(3)
    ctrl.set_speed(0., 0.)
    time.sleep(3)
    ctrl.stop()
    time.sleep(100)
