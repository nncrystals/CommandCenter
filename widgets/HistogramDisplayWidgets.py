from typing import List

import numpy as np
import pyqtgraph as pg

import services.config as config_provider
from data_class.distribution import EllipseDistribution, AreaDistribution


class PlotWidget(pg.PlotWidget):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)


class HistogramSeriesConfiguration(object):
    def __init__(self, name: str, brush=(0, 0, 255, 150)):
        self.name = name
        self.brush = brush


class HistogramWidget(PlotWidget):
    def __init__(self, confs: List[HistogramSeriesConfiguration], **kwargs):
        super().__init__(**kwargs)
        self.plots = {}
        self.plotItem.setLabel("left", "Counts")
        self.plotItem.addLegend()

        for conf in confs:
            self.plots[conf.name] = self.plotItem.plot([0, 0], [0] ,brush=conf.brush, stepMode=True, fillLevel=0, name=conf.name)


class AreaDisplayWidget(HistogramWidget):
    config_prefix = "Area_Distribution"

    def __init__(self, parent=None):
        super().__init__([HistogramSeriesConfiguration("area", (0, 0, 255, 150))], parent=parent)

        self.config = config_provider.SettingAccessor(self.config_prefix)

    @staticmethod
    @config_provider.DefaultSettingRegistration(config_prefix)
    def default_settings(config_prefix):
        config_provider.default_settings(config_prefix, [
            config_provider.SettingRegistry("bins", 30, type="int", title="Bins")
        ])

    def update_histogram(self, dist: AreaDistribution):
        if dist.area_dist.size == 0:
            return
        y, x = np.histogram(dist.area_dist, self.config["bins"])
        self.plots["area"].setData(x, y)
        label = f"Area distribution {dist.unit}"
        if self.plotItem.getLabel('bottom') != label:
            self.plotItem.setLabel('bottom', label)


class EllipsesDisplayWidget(HistogramWidget):
    config_prefix = "Ellipse_Distribution"

    def __init__(self, parent=None):
        super().__init__([
            HistogramSeriesConfiguration("minor axis", (0, 0, 255, 150)),
            HistogramSeriesConfiguration("major axis", (255, 0, 0, 150)),
        ], parent=parent)
        self.config = config_provider.SettingAccessor(self.config_prefix)

    @staticmethod
    @config_provider.DefaultSettingRegistration(config_prefix)
    def default_settings(config_prefix):
        config_provider.default_settings(config_prefix, [
            config_provider.SettingRegistry("bins", 30, type="int", title="Bins")
        ])

    def update_histogram(self, dist: EllipseDistribution):
        if dist.major_dist.size == 0:
            return
        major, minor = dist.major_dist, dist.minor_dist
        y_maj, x_maj = np.histogram(major, self.config["bins"])
        y_min, x_min = np.histogram(minor, self.config["bins"])

        self.plots["major axis"].setData(x_maj, y_maj)
        self.plots["minor axis"].setData(x_min, y_min)

        label = f"Ellipses distribution {dist.unit}"
        if self.plotItem.getLabel('bottom') != label:
            self.plotItem.setLabel('bottom', label)
