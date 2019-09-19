import sys
from unittest import TestCase

import numpy as np
from PyQt5 import QtWidgets, QtGui, QtCore

from Widgets.HistogramDisplayWidgets import AreaDisplayWidget


class TestAreaDisplayWidget(TestCase):
    def updateHistogram(self, widget):
        widget.updateHistogram(np.random.standard_normal(500))

    def test_updateHistogram(self):
        app = QtWidgets.QApplication(sys.argv)
        widget = AreaDisplayWidget(None)
        timer = QtCore.QTimer()
        timer.timeout.connect(lambda: self.updateHistogram(widget))
        timer.start(1000)
        widget.show()
        app.exec()
