import os

import PySide2
from PySide2 import QtWidgets, QtGui, QtCore
from pyqtgraph import flowchart

from services.service_provider import SubjectProvider
from flowchart import base as fb
import pyqtgraph.flowchart.library as fclib

from services.subjects import Subjects


class MappingEntry(object):
    fc_file = ""
    name = ""
    input_signal = []
    output_signal = []
    enabled = True


class NewMappingDialog(QtWidgets.QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New mapping")
        self.result = None
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        self.input_signal_list = QtWidgets.QListWidget(self)
        self.input_signal_list.setSelectionMode(QtWidgets.QListWidget.MultiSelection)
        self.output_signal_list = QtWidgets.QListWidget(self)
        self.output_signal_list.setSelectionMode(QtWidgets.QListWidget.MultiSelection)

        # mapping name
        self.name_edit = QtWidgets.QLineEdit(self)
        name_layout = QtWidgets.QFormLayout()
        name_layout.addRow("Name", self.name_edit)
        layout.addLayout(name_layout)

        # signal selection
        subjects: Subjects = SubjectProvider().get_or_create_instance(None)

        for s, _ in subjects.__annotations__.items():
            self.input_signal_list.addItem(s)
            self.output_signal_list.addItem(s)
        selection_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(selection_layout)

        input_group = QtWidgets.QGroupBox("Input Signal")
        input_layout = QtWidgets.QVBoxLayout(input_group)
        input_layout.addWidget(self.input_signal_list)

        output_group = QtWidgets.QGroupBox("Output Signal")
        output_layout = QtWidgets.QVBoxLayout(output_group)
        output_layout.addWidget(self.output_signal_list)

        selection_layout.addWidget(input_group)
        selection_layout.addWidget(output_group)

        # buttons
        self.ok_btn = QtWidgets.QPushButton("&OK", self)
        self.ok_btn.clicked.connect(self.ok)
        self.cancel_btn = QtWidgets.QPushButton("&Cancel", self)
        self.cancel_btn.clicked.connect(self.cancel)

        btn_layout = QtWidgets.QHBoxLayout()
        spacer = QtWidgets.QSpacerItem(1, 1, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        btn_layout.addSpacerItem(spacer)
        layout.addLayout(btn_layout)
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)

    def ok(self):
        result = MappingEntry()
        result.name = self.name_edit.text()
        result.input_signal = [x.text() for x in self.input_signal_list.selectedItems()]
        result.output_signal = [x.text() for x in self.output_signal_list.selectedItems()]
        self.result = result
        self.close()

    def cancel(self):
        self.close()


class MappingListItem(QtWidgets.QListWidgetItem):

    def __init__(self, entry: MappingEntry, parent=None):
        super().__init__(parent)
        self.entry = entry
        self.update()

    def update(self, entry=None):
        if entry is not None:
            self.entry = entry
        self.setText(self.entry.name)
        if not self.entry.enabled:
            self.setTextColor(QtGui.QColor("gray"))
        else:
            self.setTextColor(QtGui.QColor("black"))

    def enable(self):
        self.entry.enabled = True
        self.update()

    def disable(self):
        self.entry.enabled = False
        self.update()

class SignalMappingDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setting_path = os.path.join("Configs", "mapping.setting")
        self.setting = QtCore.QSettings(self.setting_path, QtCore.QSettings.IniFormat)

        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)
        self.mapping_list = QtWidgets.QListWidget(self)
        self.mapping_list.setSelectionMode(QtWidgets.QListWidget.NoSelection)

        self.mapping = []
        self.mapping_settings = QtCore.QSettings("")

        layout.addWidget(self.mapping_list)

        self.refresh()
        self.update_library()
    def refresh(self):
        for name in self.setting.childGroups():
            v = self.setting.value(f"{name}/data")
            self.add_to_list(v)
    def contextMenuEvent(self, ev: QtGui.QContextMenuEvent):
        ctx_menu = QtWidgets.QMenu(self)
        ctx_menu.addAction("&New mapping").triggered.connect(self.new_mapping)
        selected = self.mapping_list.currentItem()
        if selected is not None:
            ctx_menu.addAction("&Delete").triggered.connect(lambda: self.delete_mapping(selected))
            if selected.entry.enabled:
                ctx_menu.addAction("&Disable").triggered.connect(lambda: self.disable_mapping(selected))
            else:
                ctx_menu.addAction("&Enable").triggered.connect(lambda: self.enable_mapping(selected))
            ctx_menu.addAction("&Flowchart").triggered.connect(lambda: self.open_flowchart(selected))

        ctx_menu.exec_(ev.globalPos())
        super().contextMenuEvent(ev)

    def new_mapping(self):
        dialog = NewMappingDialog()
        dialog.exec_()
        if dialog.result is not None:
            self.add_to_list(dialog.result)
            self.setting.setValue(f"{dialog.result.name}/data", dialog.result)
            self.setting.sync()

    def delete_mapping(self, item):
        self.mapping_list.removeItemWidget(item)
        self.setting.remove(f"{item.entry.name}/data")
        self.setting.sync()

    def disable_mapping(self, item):
        item.disable()
        self.setting.setValue(f"{item.entry.name}/data", item.entry)
        self.setting.sync()

    def enable_mapping(self, item):
        item.enable()
        self.setting.setValue(f"{item.entry.name}/data", item.entry)
        self.setting.sync()

    def open_flowchart(self, item):
        pass

    def update_library(self):
        for node in fb._elements:
            fclib.registerNodeType(node[0], node[1])

    def create_flowchart(self):
        fc = flowchart.Flowchart(None)
        fc.library.reload = self.update_library
        return fc

    def add_to_list(self, entry):
        self.mapping.append(entry)

        item = MappingListItem(entry, self.mapping_list)
        self.mapping_list.addItem(item)
