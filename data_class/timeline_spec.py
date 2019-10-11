import datetime

import numpy as np


class DataPoint(object):
    def __init__(self, plot_name: str, series_name: str):
        super().__init__()
        self.series_name = series_name
        self.plot_name = plot_name
        self.value = None
        self.time = None

    def add_new_point(self, value: float, time=None):
        if time is None:
            time = datetime.datetime.now().timestamp()
        self._append = True
        self.value = value
        self.time = time
        return self
