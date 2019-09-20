import functools
import logging
import os

from PyQt5 import QtWidgets, QtCore
from setuptools import glob

from Services import ConfigProvider, Analyzers
from Services.Analyzers import analyzers, Analyzer
from Services.ImageSources import imageSources, ImageSource


class LayoutMenu(QtWidgets.QMenu):

    def __init__(self, layoutDirectory, parent=None):
        super().__init__("&Layout", parent)
        self.layoutDirectory = layoutDirectory
        self.loadLayoutMenu = QtWidgets.QMenu("Load L&ayout", self)
        self.loadLayoutMenu.aboutToShow.connect(self.refreshSavedLayouts)
        self.logger = logging.getLogger("console")

        self.addAction("&Default").triggered.connect(self.parent().applyDefaultLayout)
        self.addAction("&Save layout").triggered.connect(self.saveLayout)
        self.addMenu(self.loadLayoutMenu)

    def loadLayout(self, settings):
        value = settings.value("state")
        self.parent().restoreState(value, 0)

    @QtCore.pyqtSlot()
    def refreshSavedLayouts(self):
        self.loadLayoutMenu.clear()
        layoutSettingPaths = glob.glob(os.path.join(self.layoutDirectory, "*.settings"))
        if not layoutSettingPaths:
            self.loadLayoutMenu.addAction("No available layout").setDisabled(True)
        else:
            for p in layoutSettingPaths:
                settings = QtCore.QSettings(p, QtCore.QSettings.IniFormat)
                action = QtWidgets.QAction(settings.value("layoutName"), self)
                action.triggered.connect(functools.partial(self.loadLayout, settings))
                self.loadLayoutMenu.addAction(action)

    @QtCore.pyqtSlot()
    def saveLayout(self):
        name, ok = QtWidgets.QInputDialog.getText(self, "Save layout as", "layout name")
        if not ok:
            return
        panel: QtWidgets.QDockWidget
        settingPath = os.path.join(self.layoutDirectory, f"{name}.settings")
        settings = QtCore.QSettings(settingPath,
                                    QtCore.QSettings.IniFormat)
        state = self.parent().saveState(0)
        settings.setValue("state", state)
        settings.setValue("layoutName", name)
        settings.sync()
        self.logger.info(f"Layout successfully saved to {settingPath}")


class ImageSourceMenu(QtWidgets.QMenu):
    imageSourceChanged = QtCore.pyqtSignal()
    configPrefix = "Image_Source"

    def __init__(self, parent=None):
        super().__init__("&Image source", parent)
        self.config = ConfigProvider.SettingAccessor(self.configPrefix)
        self.logger = logging.getLogger("console")
        self.imageSourceListMenu = QtWidgets.QMenu("&Image source", self)
        self.addMenu(self.imageSourceListMenu)

        # lazy initialization because the external signal should be connected first. Otherwise the image may not display
        th = QtCore.QThread(self)
        th.started.connect(self.initMenu)
        th.start()

    @staticmethod
    @ConfigProvider.defaultSettingRegistration(configPrefix)
    def defaultSettings(configPrefix):
        ConfigProvider.defaultSettings(configPrefix, [
            ConfigProvider.SettingRegistry("source", "")
        ])

    @QtCore.pyqtSlot()
    def initMenu(self):
        self.makeImageSourceMenu()
        self.addAction("C&onnect").triggered.connect(self.connectImageSource)
        self.addAction("&Disconnect").triggered.connect(self.disconnectImageSource)

    @QtCore.pyqtSlot()
    def connectImageSource(self):
        if ImageSource.imageSourceInstance is None:
            self.logger.error("Image source is not selected")
            return

        if ImageSource.imageSourceInstance.isRunning():
            self.logger.warning("Image source is already connected. Ignore connect request.")
            return

        ImageSource.imageSourceInstance.start()

    @QtCore.pyqtSlot()
    def disconnectImageSource(self):
        if ImageSource.imageSourceInstance is None or not ImageSource.imageSourceInstance.isRunning():
            self.logger.warning("Image source is not connected.")
            return
        ImageSource.imageSourceInstance.stop()
        ImageSource.imageSourceInstance = None

    @QtCore.pyqtSlot(QtWidgets.QAction)
    def agCallback(self, action: QtWidgets.QAction):
        if ImageSource.imageSourceInstance is not None and ImageSource.imageSourceInstance.isRunning():
            ImageSource.imageSourceInstance.stop()
        ImageSource.imageSourceInstance = imageSources[action.text()]()
        self.config["source"] = action.text()
        self.logger.info(f"Image source switched to {action.text()}")
        self.imageSourceChanged.emit()

    def makeImageSourceMenu(self):
        self.imageSourceListMenu.clear()
        ag = QtWidgets.QActionGroup(self.imageSourceListMenu)
        ag.setExclusive(True)
        ag.triggered.connect(self.agCallback)
        for name, imageSourceType in imageSources.items():
            a = QtWidgets.QAction(name)
            a.setCheckable(True)
            ag.addAction(a)
            if name == self.config["source"]:
                a.trigger()
            self.imageSourceListMenu.addAction(a)


class AnalyzerMenu(QtWidgets.QMenu):
    analyzerChanged = QtCore.pyqtSignal()
    configPrefix = "Analyzers"

    def __init__(self, parent=None):
        super().__init__("Ana&lyzers", parent)
        self.config = ConfigProvider.SettingAccessor(self.configPrefix)
        self.logger = logging.getLogger("console")
        self.analyzerChoiceMenu = QtWidgets.QMenu("Ana&lyzers", self)
        self.addMenu(self.analyzerChoiceMenu)
        self.makeAnalyzerMenu()
        self.addAction("&Connect").triggered.connect(self.connectAnalyzer)
        self.addAction("&Disconnect").triggered.connect(self.disconnectAnalyzer)

    @staticmethod
    @ConfigProvider.defaultSettingRegistration(configPrefix)
    def defaultSettings(configPrefix):
        ConfigProvider.defaultSettings(configPrefix, [
            ConfigProvider.SettingRegistry("analyzer", "")
        ])

    @QtCore.pyqtSlot(QtWidgets.QAction)
    def agCallback(self, action: QtWidgets.QAction):
        if Analyzer.instance is not None and Analyzer.instance.isRunning():
            Analyzer.instance.stop()
        Analyzer.instance = analyzers[action.text()]()

        self.config["analyzer"] = action.text()
        self.logger.info(f"Analyzer switched to {action.text()}")
        self.analyzerChanged.emit()

    def makeAnalyzerMenu(self):
        self.analyzerChoiceMenu.clear()
        ag = QtWidgets.QActionGroup(self)
        ag.setExclusive(True)
        for name, analyzerType in analyzers.items():
            a = QtWidgets.QAction(name)
            a.setCheckable(True)
            if name == self.config["analyzer"]:
                a.setChecked(True)
            ag.addAction(a)
            self.analyzerChoiceMenu.addAction(a)
        ag.triggered.connect(self.agCallback)

    @QtCore.pyqtSlot()
    def connectAnalyzer(self):
        if Analyzer.instance is None:
            self.logger.error("Analyzer is not selected")
            return

        if Analyzer.instance.isRunning():
            self.logger.warning("Analyzer is already connected. Ignore connect request.")
            return

        Analyzer.instance.start()

    @QtCore.pyqtSlot()
    def disconnectAnalyzer(self):
        if Analyzer.instance is None or not Analyzer.instance.isRunning():
            self.logger.warning("Analyzer is not connected.")
            return
        Analyzer.instance.stop()
        Analyzer.instance = None
