import sys
from pydoc import locate

import pyqtgraph.parametertree as pgp
from Qt import QtWidgets, QtGui, QtCore

from services import config
# parse the config file
from services.config import SettingAccessor


class ConfigDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuration")

        self.config = config.global_settings
        self.pt = pgp.ParameterTree()

        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().addWidget(self.pt)

        self.createForm()
        self.setMinimumHeight(400)
        self.setMinimumWidth(600)

    def keyPressEvent(self, a0: QtGui.QKeyEvent) -> None:
        if a0.key() == QtCore.Qt.Key_Enter or a0.key() == QtCore.Qt.Key_Return:
            return
        super().keyPressEvent(a0)

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        self.config.sync()

    def createForm(self):
        for section in self.config.childGroups():
            p = pgp.Parameter.create(name=section, type="group")
            self.pt.addParameters(p)

            self.config.beginGroup(section)
            for key in self.config.childKeys():
                t = self.config.value(f"{key}/type", "str")
                title = self.config.value(f"{key}/title", key)
                default = self.config.value(f"{key}/default", None)

                # https://bugreports.qt.io/browse/PYSIDE-820
                if t == "bool":
                    value = bool(self.config.value(key, defaultValue=default))
                else:
                    value = self.config.value(key, defaultValue=default, type=locate(t))

                def valueChanged(obj: pgp.Parameter, newVal):
                    accessor = SettingAccessor()
                    accessor[obj.name()] = newVal

                pEntry = pgp.Parameter.create(name=f"{section}/{key}", title=title, value=value,
                                              type=t, default=default)
                pEntry.sigValueChanged.connect(valueChanged)

                p.addChild(pEntry)
            self.config.endGroup()


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = ConfigDialog()
    window.show()

    app.exec_()
