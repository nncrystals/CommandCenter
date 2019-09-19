import numpy as np
import pyqtgraph as pg
from PyQt5 import QtCore

import Services.ConfigProvider as configProvider


class PlotWidget(pg.PlotWidget):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)


class AreaDisplayWidget(PlotWidget):
    configPrefix = "Area_Distribution"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = configProvider.SettingAccessor(AreaDisplayWidget.configPrefix)

    @staticmethod
    @configProvider.defaultSettingRegistration(configPrefix)
    def defaultSettings(configPrefix):
        configProvider.defaultSettings(configPrefix, [
            configProvider.SettingRegistry("bins", 30, type="int", title="Bins")
        ])

    @QtCore.pyqtSlot(np.ndarray)
    def updateHistogram(self, arr: np.ndarray):
        y, x = np.histogram(arr, self.config["bins"])
        self.plotItem.clear()
        self.plotItem.plot(x, y, stepMode=True, fillLevel=0, brush=(0, 0, 255, 150))


class EllipsesDisplayWidget(PlotWidget):
    configPrefix = "Ellipse_Distribution"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = configProvider.SettingAccessor(EllipsesDisplayWidget.configPrefix)

    @staticmethod
    @configProvider.defaultSettingRegistration(configPrefix)
    def defaultSettings(configPrefix):
        configProvider.defaultSettings(configPrefix, [
            configProvider.SettingRegistry("bins", 30, type="int", title="Bins")
        ])

    @QtCore.pyqtSlot(np.ndarray, np.ndarray)
    def updateHistograms(self, major: np.ndarray, minor: np.ndarray):
        yMaj, xMaj = np.histogram(major, self.config["bins"])
        yMin, xMin = np.histogram(minor, self.config["bins"])
        self.plotItem.clear()
        self.plotItem.plot(xMaj, yMaj, stepMode=True, fillLevel=0, brush=(0, 0, 255, 150))
        self.plotItem.plot(xMin, yMin, stepMode=True, fillLevel=0, brush=(255, 0, 0, 150))
