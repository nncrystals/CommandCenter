from PySide2 import QtWidgets, QtGui, QtCore

from services.hardware_control import CameraPeripheralControl, CameraPeripheralControlParams
from services.service_provider import CameraPeripheralControlService


class CameraPeripheralDialog(QtWidgets.QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.control: CameraPeripheralControl = CameraPeripheralControlService().get_or_create_instance(None)
        state: CameraPeripheralControlParams = self.control.get_state()

        layout = QtWidgets.QFormLayout()
        self.setLayout(layout)

        self.power_checkbox = QtWidgets.QCheckBox(self)
        self.power_checkbox.setCheckState(QtCore.Qt.Checked if state.power else QtCore.Qt.Unchecked)
        self.power_checkbox.stateChanged.connect(self.power_updated)
        layout.addRow("Power", self.power_checkbox)

        self.trigger_checkbox = QtWidgets.QCheckBox(self)
        self.trigger_checkbox.stateChanged.connect(self.trigger_updated)
        self.trigger_checkbox.setCheckState(QtCore.Qt.Checked if state.trigger else QtCore.Qt.Unchecked)
        layout.addRow("Trigger", self.trigger_checkbox)

        self.exposure_edit = QtWidgets.QSpinBox(self)
        self.exposure_edit.setMinimum(0)
        self.exposure_edit.setSingleStep(20)
        self.exposure_edit.setValue(state.pulse_width_tick or 0)
        self.exposure_edit.valueChanged.connect(self.exposure_updated)
        layout.addRow("Exposure", self.exposure_edit)

        self.setWindowTitle("Camera Peripheral Control")
        self.setMinimumWidth(400)

    def exposure_updated(self, new_val):
        self.control.set_params(CameraPeripheralControlParams(new_val))

    def power_updated(self, ev):
        if ev == QtCore.Qt.Checked:
            self.control.set_power(True)
        else:
            self.control.set_power(False)

    def trigger_updated(self, ev):
        if ev == QtCore.Qt.Checked:
            self.control.set_trigger(True)
        else:
            self.control.set_trigger(False)
