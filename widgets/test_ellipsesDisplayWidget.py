import sys
from unittest import TestCase

import numpy as np
from PyQt5 import QtWidgets, QtGui, QtCore

from widgets.HistogramDisplayWidgets import EllipsesDisplayWidget


class TestEllipsesDisplayWidget(TestCase):
    def updateHistogram(self, widget):
        widget.update_histogram(np.random.standard_normal(500), np.random.standard_normal(500) * 15 + 10)

    def test_ellipseDisplayWidget(self):
        app = QtWidgets.QApplication(sys.argv)
        widget = EllipsesDisplayWidget(None)
        timer = QtCore.QTimer()
        timer.timeout.connect(lambda: self.updateHistogram(widget))
        timer.start(1000)
        widget.show()
        app.exec()
