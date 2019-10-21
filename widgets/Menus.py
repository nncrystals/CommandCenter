import functools
import logging
import os
import traceback

import PySide2
from PySide2 import QtWidgets, QtCore
from setuptools import glob
from services import config
from services import service_provider
from services.analyzers import Analyzer
from services.camera_peripheral_control import CameraPeripheralControl
from services.image_sources import ImageSource
from services.service_provider import ImageSourceProvider, AnalyzerProvider
from services.simex_io import SimexIO
from utils.QtScheduler import QtScheduler
from widgets import SignalMappingDialog
from widgets.CameraPeripheralDialog import CameraPeripheralDialog


class LayoutMenu(QtWidgets.QMenu):

    def __init__(self, layout_directory, parent=None):
        super().__init__("&Layout", parent)
        self.layout_directory = layout_directory
        self.layout_path = os.path.join(layout_directory, "layout.settings")
        self.layout_list_menu = QtWidgets.QMenu("Load L&ayout", self)
        self.layout_list_menu.aboutToShow.connect(self.refresh_saved_layouts)
        self.logger = logging.getLogger("console")

        self.addAction("&Default").triggered.connect(self.parent().applyDefaultLayout)
        self.addAction("&Save layout").triggered.connect(self.save_layout)
        self.addMenu(self.layout_list_menu)

    def load_layout(self, state):
        self.parent().restoreState(state, 0)

    @QtCore.Slot()
    def refresh_saved_layouts(self):
        self.layout_list_menu.clear()
        layout_path = self.layout_path
        if not layout_path:
            self.layout_list_menu.addAction("No available layout").setDisabled(True)
        else:
            settings = QtCore.QSettings(layout_path, QtCore.QSettings.IniFormat)
            for name in settings.childGroups():
                self.layout_list_menu.addAction(name).triggered.connect(
                    functools.partial(self.load_layout, settings.value(f"{name}/state")))

    @QtCore.Slot()
    def save_layout(self):
        name, ok = QtWidgets.QInputDialog.getText(self, "Save layout as", "layout name")
        if not ok:
            return
        panel: QtWidgets.QDockWidget
        setting_path = self.layout_path
        settings = QtCore.QSettings(setting_path,
                                    QtCore.QSettings.IniFormat)
        state = self.parent().saveState(0)
        settings.setValue(f"{name}/state", state)
        settings.sync()
        self.logger.info(f"Layout successfully saved to {setting_path}")


class ImageSourceMenu(QtWidgets.QMenu):
    config_prefix = "ImageSource"

    def __init__(self, parent=None):
        super().__init__("&Image source", parent)
        self.config = config.SettingAccessor(self.config_prefix)
        self.image_source_provider = ImageSourceProvider()
        self.logger = logging.getLogger("console")
        self.image_source_list_menu = QtWidgets.QMenu("&Image source", self)
        self.addMenu(self.image_source_list_menu)

        # lazy initialization because the external signal should be connected first. Otherwise the image may not display
        QtScheduler(QtCore).schedule(lambda sc, state: self.initMenu())

    @staticmethod
    @config.DefaultSettingRegistration(config_prefix)
    def default_settings(config_prefix):
        config.default_settings(config_prefix, [
            config.SettingRegistry("source", "")
        ])

    @QtCore.Slot()
    def initMenu(self):
        self.makeImageSourceMenu()
        self.addAction("C&onnect").triggered.connect(self.connectImageSource)
        self.addAction("&Disconnect").triggered.connect(self.disconnectImageSource)

    @QtCore.Slot()
    def connectImageSource(self):
        try:
            image_source: ImageSource = self.image_source_provider.get_instance()
        except:
            self.logger.error("Image source is not selected. Cannot connect.")
            return

        image_source.start()
        self.logger.info("Image source connected")

    @QtCore.Slot()
    def disconnectImageSource(self):
        try:
            image_source: ImageSource = self.image_source_provider.get_instance()
        except:
            self.logger.error("Image source is not selected. Cannot disconnect")
            return

        image_source.stop()
        self.logger.info("Image source disconnected")

    @QtCore.Slot(QtWidgets.QAction)
    def agCallback(self, action: QtWidgets.QAction):
        try:
            text = action.text()
            try:
                self.image_source_provider.replace_instance_with(text)
            except Exception as ex:
                self.logger.error("Failed to switch image source. Try stop the current image source first")
                self.logger.debug(ex)
                return
            self.config["source"] = text
            self.logger.info(f"Image source is switched to {text}")
        except Exception as ex:
            self.logger.error(ex)

    def makeImageSourceMenu(self):
        self.image_source_list_menu.clear()
        ag = QtWidgets.QActionGroup(self.image_source_list_menu)
        ag.setExclusive(True)
        ag.triggered.connect(self.agCallback)
        for name in self.image_source_provider.name_mapping.keys():
            a = QtWidgets.QAction(name)
            a.setCheckable(True)
            ag.addAction(a)
            if name == self.config["source"]:
                a.trigger()
            self.image_source_list_menu.addAction(a)


class AnalyzerMenu(QtWidgets.QMenu):
    configPrefix = "Analyzers"

    def __init__(self, parent=None):
        super().__init__("Ana&lyzers", parent)
        self.config = config.SettingAccessor(self.configPrefix)
        self.logger = logging.getLogger("console")
        self.analyzer_provider = AnalyzerProvider()
        self.analyzer_choice_menu = QtWidgets.QMenu("Ana&lyzers", self)
        self.addMenu(self.analyzer_choice_menu)
        self.makeAnalyzerMenu()
        self.addAction("&Connect").triggered.connect(self.connectAnalyzer)
        self.addAction("&Disconnect").triggered.connect(self.disconnectAnalyzer)

    @staticmethod
    @config.DefaultSettingRegistration(configPrefix)
    def defaultSettings(configPrefix):
        config.default_settings(configPrefix, [
            config.SettingRegistry("analyzer", "")
        ])

    @QtCore.Slot(QtWidgets.QAction)
    def agCallback(self, action: QtWidgets.QAction):
        try:
            text = action.text()
            try:
                self.analyzer_provider.replace_instance_with(text)
            except Exception as ex:
                self.logger.error("Failed to switch analyzer. Try stop the current analyzer first.")
                traceback.print_exc()
                return
            self.config["analyzer"] = text
            self.logger.info(f"Analyzer is switched to {text}")
        except Exception as ex:
            self.logger.error(ex)

    def makeAnalyzerMenu(self):
        self.analyzer_choice_menu.clear()
        ag = QtWidgets.QActionGroup(self)
        ag.setExclusive(True)
        ag.triggered.connect(self.agCallback)
        for name in self.analyzer_provider.name_mapping.keys():
            a = QtWidgets.QAction(name)
            a.setCheckable(True)
            ag.addAction(a)
            if name == self.config["analyzer"]:
                a.trigger()
            self.analyzer_choice_menu.addAction(a)

    @QtCore.Slot()
    def connectAnalyzer(self):
        try:
            analyzer: Analyzer = self.analyzer_provider.get_instance()
        except:
            self.logger.error("Analyzer is not selected. Cannot connect.")
            traceback.print_exc()
            return

        analyzer.start()
        self.logger.info("Analyzer connected")

    @QtCore.Slot()
    def disconnectAnalyzer(self):
        try:
            analyzer: Analyzer = self.analyzer_provider.get_instance()
        except:
            self.logger.error("Analyzer is not selected. Cannot disconnect.")
            traceback.print_exc()
            return

        analyzer.stop()
        self.logger.info("Analyzer disconnected")


class SimexMenu(QtWidgets.QMenu):
    def __init__(self, parent=None):
        super().__init__("Simex", parent)
        self.simex_io_instance: SimexIO = service_provider.SimexIOProvider().get_or_create_instance(None)

        connect_action = self.addAction("&Connect")
        connect_action.triggered.connect(lambda: self.simex_io_instance.connect().subscribe())
        disconnect_action = self.addAction("&Disconnect")
        disconnect_action.triggered.connect(lambda: self.simex_io_instance.disconnect())


class HardwareControlMenu(QtWidgets.QMenu):
    def __init__(self, parent=None):
        super().__init__("&Hardware", parent)
        self.camera_peripheral_control: CameraPeripheralControl = service_provider.CameraPeripheralControlService().get_or_create_instance(
            None)
        self.camera_peripheral_control_menu = QtWidgets.QMenu("Camera &Peripheral", self)
        self.camera_peripheral_control_menu.addAction("&Connect").triggered.connect(
            self.camera_peripheral_control.start)
        self.camera_peripheral_control_menu.addAction("&Disconnect").triggered.connect(
            self.camera_peripheral_control.stop)
        self.camera_peripheral_control_menu.addSeparator()

        allow_control_action = QtWidgets.QWidgetAction(self.camera_peripheral_control_menu)
        checkbox = QtWidgets.QCheckBox("Allow Simex Control")
        checkbox.stateChanged.connect(self.simex_control_updated)
        allow_control_action.setDefaultWidget(checkbox)
        self.camera_peripheral_control_menu.addAction(allow_control_action)

        self.manual_control = self.camera_peripheral_control_menu.addAction("Manual &control")
        self.manual_control.triggered.connect(self.manual_control_requested)

        self.addMenu(self.camera_peripheral_control_menu)

    def simex_control_updated(self, ev):
        if ev == QtCore.Qt.Checked:
            self.manual_control.setDisabled(True)
        else:
            self.manual_control.setEnabled(True)

    def manual_control_requested(self):
        CameraPeripheralDialog(self).show()


class SignalMappingMenu(QtWidgets.QAction):
    def __init__(self, parent=None):
        super().__init__("Signal &Mapping", parent)
        self.triggered.connect(self.show_signal_mapping_dialog)

    def show_signal_mapping_dialog(self):
        dlg = SignalMappingDialog.SignalMappingDialog()
        dlg.exec_()


class QuickConnectMenu(QtWidgets.QMenu):
    def __init__(self, parent=None):
        super().__init__("&Quick Connect", parent)
        self.logger = logging.getLogger("console")
        self.addAction("Connect all").triggered.connect(self.connect_all)
        self.addAction("Disconnect all").triggered.connect(self.disconnect_all)

    def connect_all(self):
        self.logger.info("Quick connect all elements")
        try:
            image_source: ImageSource = service_provider.ImageSourceProvider().get_instance()
        except Exception as ex:
            self.logger.error(ex)
            return
        try:
            if image_source.is_running():
                self.logger.info("Image source is already connected. Skip.")
            else:
                self.logger.info(f"Connecting image source: {image_source.get_name()}")
                image_source.start()
        except Exception as ex:
            self.logger.error(f"Failed to connect to image source: {image_source.get_name()}")
            return

        try:
            analyzer_source: Analyzer = service_provider.AnalyzerProvider().get_instance()
        except Exception as ex:
            self.logger.error(ex)
            return
        try:
            if analyzer_source.is_running():
                self.logger.info("Analyzer is already connected. Skip.")
            else:
                self.logger.info(f"Connecting to analyzer: {analyzer_source.get_name()}")
                analyzer_source.start()
        except Exception as ex:
            self.logger.error(f"Failed to connect to analyzer: {analyzer_source.get_name()}")

    def disconnect_all(self):
        pass