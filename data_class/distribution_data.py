from PyQt5 import QtCore


class DistributionData(QtCore.QObject):
    def __init__(self, unit="um"):
        super().__init__()
        self.unit = unit
        self.x = []