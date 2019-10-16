from typing import Union, Iterable

import numpy as np


class Distribution(object):
    def __init__(self):
        pass


class AreaDistribution(Distribution):
    def __init__(self, area_dist: Union[Iterable, np.ndarray], unit="<math>px<sup>2</sup></math>"):
        super().__init__()
        self.unit = unit
        self.area_dist: np.ndarray = np.asarray(area_dist)


class EllipseDistribution(Distribution):
    def __init__(self,
                 major_dist: np.ndarray,
                 minor_dist: np.ndarray,
                 unit="<math>px</math>"
                 ):
        super().__init__()
        self.unit = unit
        self.major_dist = major_dist
        self.minor_dist = minor_dist
