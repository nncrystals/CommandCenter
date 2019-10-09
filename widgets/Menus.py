import functools
import logging
import os
import traceback

from PyQt5 import QtWidgets, QtCore
from setuptools import glob
from services import config
from services import service_provider
from services.analyzers import Analyzer
from services.image_sources import ImageSource
from services.service_provider import ImageSourceProvider, AnalyzerProvider
from services.simex_io import SimexIO


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

    @QtCore.pyqtSlot()
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

    @QtCore.pyqtSlot()
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
    configPrefix = "Image_Source"

    def __init__(self, parent=None):
        super().__init__("&Image source", parent)
        self.config = config.SettingAccessor(self.configPrefix)
        self.image_source_provider = ImageSourceProvider()
        self.logger = logging.getLogger("console")
        self.image_source_list_menu = QtWidgets.QMenu("&Image source", self)
        self.addMenu(self.image_source_list_menu)

        # lazy initialization because the external signal should be connected first. Otherwise the image may not display
        th = QtCore.QThread(self)
        th.started.connect(self.initMenu)
        th.start()

    @staticmethod
    @config.DefaultSettingRegistration(configPrefix)
    def defaultSettings(configPrefix):
        config.default_settings(configPrefix, [
            config.SettingRegistry("source", "")
        ])

    @QtCore.pyqtSlot()
    def initMenu(self):
        self.makeImageSourceMenu()
        self.addAction("C&onnect").triggered.connect(self.connectImageSource)
        self.addAction("&Disconnect").triggered.connect(self.disconnectImageSource)

    @QtCore.pyqtSlot()
    def connectImageSource(self):
        try:
            image_source: ImageSource = self.image_source_provider.get_instance()
        except:
            self.logger.error("Image source is not selected. Cannot connect.")
            return

        image_source.start()
        self.logger.info("Image source connected")

    @QtCore.pyqtSlot()
    def disconnectImageSource(self):
        try:
            image_source: ImageSource = self.image_source_provider.get_instance()
        except:
            self.logger.error("Image source is not selected. Cannot disconnect")
            return

        image_source.stop()
        self.logger.info("Image source disconnected")

    @QtCore.pyqtSlot(QtWidgets.QAction)
    def agCallback(self, action: QtWidgets.QAction):
        try:
            text = action.text()
            try:
                self.image_source_provider.replace_instance_with(text)
            except:
                self.logger.error("Failed to switch image source. Try stop the current image source first")
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

    @QtCore.pyqtSlot(QtWidgets.QAction)
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

    @QtCore.pyqtSlot()
    def connectAnalyzer(self):
        try:
            analyzer: Analyzer = self.analyzer_provider.get_instance()
        except:
            self.logger.error("Analyzer is not selected. Cannot connect.")
            traceback.print_exc()
            return

        analyzer.start()
        self.logger.info("Analyzer connected")

    @QtCore.pyqtSlot()
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

