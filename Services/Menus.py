import functools
import logging
import os
import typing

from PyQt5 import QtWidgets, QtGui, QtCore
from setuptools import glob

from Services import configProvider
from Services.ImageSources import imageSourceList


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
    imageSourceChanged = QtCore.pyqtSignal(type)

    def __init__(self, parent=None):
        super().__init__("&Image source", parent)
        self.configPrefix = "Image_Source"
        configProvider.initializeSettingSection({
            self.configPrefix + "/source": ""
        })
        self.logger = logging.getLogger("console")
        self.makeImageSourceMenu()

    @QtCore.pyqtSlot(QtWidgets.QAction)
    def agCallback(self, action: QtWidgets.QAction):
        self.imageSourceChanged.emit(imageSourceList[action.text()])
        configProvider.globalSettings.setValue(self.configPrefix + "/source", action.text())
        self.logger.info(f"Image source switched to {action.text()}")

    def makeImageSourceMenu(self):
        self.clear()
        ag = QtWidgets.QActionGroup(self)
        ag.setExclusive(True)
        for name, imageSourceType in imageSourceList.items():
            a = QtWidgets.QAction(name)
            a.setCheckable(True)
            if name == configProvider.globalSettings.value(self.configPrefix + "/source"):
                a.setChecked(True)
            ag.addAction(a)
            self.addAction(a)
        ag.triggered.connect(self.agCallback)


class AnalysisMenu(QtWidgets.QMenu):
    def __init__(self, parent=None):
        super().__init__("&Analysis", parent)



