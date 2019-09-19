import numpy as np
import pyqtgraph as pg
from PyQt5 import QtCore

import Services.configProvider as configProvider


class PlotWidget(pg.PlotWidget):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)


class AreaDisplayWidget(PlotWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.configPrefix = "Area_Distribution"
        configProvider.initializeSettingSection({
            self.configPrefix + "/bins": 30,
            self.configPrefix + "/bins/type": "int",
            self.configPrefix + "/bins/title": "Bins",
        })

    @QtCore.pyqtSlot(np.ndarray)
    def updateHistogram(self, arr: np.ndarray):
        y, x = np.histogram(arr, int(configProvider.globalSettings.value(self.configPrefix + "/bins")))
        self.plotItem.clear()
        self.plotItem.plot(x, y, stepMode=True, fillLevel=0, brush=(0, 0, 255, 150))


class EllipsesDisplayWidget(PlotWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.configPrefix = "Ellipse_Distribution"
        configProvider.initializeSettingSection({
            self.configPrefix + "/bins": 30,
            self.configPrefix + "/bins/type": "int",
            self.configPrefix + "/bins/title": "Bins",
        })

    @QtCore.pyqtSlot(np.ndarray, np.ndarray)
    def updateHistograms(self, major: np.ndarray, minor: np.ndarray):
        yMaj, xMaj = np.histogram(major, int(configProvider.globalSettings.value(self.configPrefix + "/bins")))
        yMin, xMin = np.histogram(minor, int(configProvider.globalSettings.value(self.configPrefix + "/bins")))
        self.plotItem.clear()
        self.plotItem.plot(xMaj, yMaj, stepMode=True, fillLevel=0, brush=(0, 0, 255, 150))
        self.plotItem.plot(xMin, yMin, stepMode=True, fillLevel=0, brush=(255, 0, 0, 150))
