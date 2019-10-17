import functools
import logging
import os
import traceback

from PySide2 import QtWidgets, QtCore
from setuptools import glob
from services import config
from services import service_provider
from services.analyzers import Analyzer
from services.hardware_control import CameraPeripheralControl
from services.image_sources import ImageSource
from services.service_provider import ImageSourceProvider, AnalyzerProvider
from services.simex_io import SimexIO
from utils.QtScheduler import QtScheduler


class LayoutMenu(QtWidgets.QMenu):

    def __init__(self, layoutDirectory, parent=None):
        super().__init__("&Layout", parent)
        self.layout_directory = layoutDirectory
        self.layout_list_menu = QtWidgets.QMenu("Load L&ayout", self)
        self.layout_list_menu.aboutToShow.connect(self.refreshSavedLayouts)
        self.logger = logging.getLogger("console")

        self.addAction("&Default").triggered.connect(self.parent().applyDefaultLayout)
        self.addAction("&Save layout").triggered.connect(self.saveLayout)
        self.addMenu(self.layout_list_menu)

    def loadLayout(self, settings):
        value = settings.value("state")
        self.parent().restoreState(value, 0)

    @QtCore.Slot()
    def refreshSavedLayouts(self):
        self.layout_list_menu.clear()
        layout_paths = glob.glob(os.path.join(self.layout_directory, "*.settings"))
        if not layout_paths:
            self.layout_list_menu.addAction("No available layout").setDisabled(True)
        else:
            for p in layout_paths:
                settings = QtCore.QSettings(p, QtCore.QSettings.IniFormat)
                action = QtWidgets.QAction(settings.value("layoutName"), self)
                action.triggered.connect(functools.partial(self.loadLayout, settings))
                self.layout_list_menu.addAction(action)

    @QtCore.Slot()
    def saveLayout(self):
        name, ok = QtWidgets.QInputDialog.getText(self, "Save layout as", "layout name")
        if not ok:
            return
        panel: QtWidgets.QDockWidget
        settingPath = os.path.join(self.layout_directory, f"{name}.settings")
        settings = QtCore.QSettings(settingPath,
                                    QtCore.QSettings.IniFormat)
        state = self.parent().saveState(0)
        settings.setValue("state", state)
        settings.setValue("layoutName", name)
        settings.sync()
        self.logger.info(f"Layout successfully saved to {settingPath}")


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
        self.camera_peripheral_control: CameraPeripheralControl = service_provider.CameraPeripheralControlService.get_or_create_instance(None)
        self.camera_peripheral_control_menu = QtWidgets.QMenu("Camera &Peripheral", self)
        self.camera_peripheral_control_menu.addAction("&Connect").triggered.connect(self.camera_peripheral_control.start)
        self.camera_peripheral_control_menu.addAction("&Disconnect").triggered.connect(self.camera_peripheral_control.stop)

        self.addMenu(self.camera_peripheral_control_menu)