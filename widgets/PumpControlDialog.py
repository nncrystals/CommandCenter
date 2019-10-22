from PySide2 import QtWidgets, QtGui, QtCore

from services.pump_control import PumpControl
from services.service_provider import PumpControlService, SubjectProvider
from services.subjects import Subjects


class PumpControlDialog(QtWidgets.QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.control: PumpControl = PumpControlService().get_or_create_instance(None)
        self.subject: Subjects = SubjectProvider().get_or_create_instance(None)
        self.state = self.control.get_state()

        layout = QtWidgets.QFormLayout()
        self.setLayout(layout)

        self.slurry_pump_speed = QtWidgets.QDoubleSpinBox(self)
        self.slurry_pump_speed.setMinimum(-600.0)
        self.slurry_pump_speed.setMaximum(600.0)
        self.slurry_pump_speed.setSingleStep(0.1)
        self.slurry_pump_speed.setValue(self.state[0] or 0)
        self.slurry_pump_speed.valueChanged.connect(lambda x: self.subject.pump_control.on_next((x, None)))
        layout.addRow("Slurry pump", self.slurry_pump_speed)

        self.clear_pump_speed = QtWidgets.QDoubleSpinBox(self)
        self.clear_pump_speed.setMinimum(-600.0)
        self.clear_pump_speed.setMaximum(600.0)
        self.clear_pump_speed.setSingleStep(0.1)
        self.clear_pump_speed.setValue(self.state[1] or 0)
        self.clear_pump_speed.valueChanged.connect(lambda x: self.subject.pump_control.on_next((None, x)))
        layout.addRow("Clear pump", self.clear_pump_speed)

        self.setWindowTitle("Pump control")
        self.setMinimumWidth(400)
