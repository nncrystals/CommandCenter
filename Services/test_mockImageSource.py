import sys
from unittest import TestCase
from PyQt5 import QtWidgets, QtGui, QtCore
from Services.ImageSources import MockImageSource
import pyqtgraph as pg

class TestMockImageSource(TestCase):
    def test_generate_images(self):
        app = QtWidgets.QApplication(sys.argv)
        window = pg.image()
        source = MockImageSource()
        def show(im):
            window.setImage(im)
        source.imagesReady.connect(show)
        source.start()
        app.exec()
