import io
import sys
import time
import numpy as np
from typing import Optional, Any

from PIL import Image

from PyQt5 import QtWidgets, QtCore, QtGui, QtNetwork
import pyqtgraph as pg


class SimpleDisplayWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        self.imageItem = pg.ImageItem()
        self.imageItem.setOpts(axisOrder='row-major')
        self.imageWidget = pg.GraphicsView()
        self.view = pg.ViewBox(lockAspect=True, invertY=True)
        self.imageWidget.setCentralItem(self.view)
        self.view.addItem(self.imageItem)
        layout.addWidget(self.imageWidget)

    def updateImage(self, image: np.ndarray):
        self.imageItem.setImage(image, False)


class ImageDisplayWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        self.imageItem = pg.ImageItem()
        self.imageItem.setOpts(axisOrder='row-major')
        self.imageWidget = pg.ImageView(self, imageItem=self.imageItem)
        self.imageWidget.ui.menuBtn.hide()
        self.imageWidget.ui.roiBtn.hide()
        layout.addWidget(self.imageWidget)

    def updateImage(self, image: np.ndarray):
        self.imageItem.setImage(image)


if __name__ == '__main__':
    import requests


    class ImageRequestWorker(QtCore.QThread):
        imageReady = QtCore.pyqtSignal(np.ndarray)

        def __init__(self):
            super().__init__()

        def run(self) -> None:
            while True:
                response = requests.get("https://picsum.photos/800/600")
                if response.status_code == 200:
                    try:
                        img = Image.open(io.BytesIO(response.content))
                        img = np.asarray(img)
                        self.imageReady.emit(img.transpose([1, 0, 2]))
                    except:
                        pass
                time.sleep(1)


    app = QtWidgets.QApplication(sys.argv)
    worker = ImageRequestWorker()

    window = ImageDisplayWidget()
    window.setGeometry(0, 0, 800, 800)
    window.show()

    worker.imageReady.connect(window.updateImage)
    worker.start()
    app.exec_()
