from typing import Union, Iterable

import numpy as np


class Distribution(object):
    def __init__(self):
        pass


class AreaDistribution(Distribution):
    def __init__(self, area_dist: Union[Iterable, np.ndarray]):
        super().__init__()
        self.area_dist: np.ndarray = np.asarray(area_dist)


class EllipseDistribution(Distribution):
    def __init__(self, major_dist: Union[Iterable, np.ndarray], minor_dist: Union[Iterable, np.ndarray]):
        super().__init__()
        self.major_dist = np.asarray(major_dist)
        self.minor_dist = np.asarray(minor_dist)

