import datetime
import io
import sys
import time
from typing import Union

import numpy as np
import pyqtgraph as pg
from PIL import Image
from PySide2 import QtWidgets, QtCore

from data_class.subject_data import AcquiredImage


class SimpleDisplayWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        self.image_item = pg.ImageItem()
        self.image_item.setOpts(axisOrder='row-major')
        self.text_item = pg.TextItem(color=(255,0,0))
        self.image_widget = pg.GraphicsView()
        self.view = pg.ViewBox(lockAspect=True, invertY=True)
        self.image_widget.setCentralItem(self.view)
        self.view.addItem(self.image_item)
        self.view.addItem(self.text_item)
        layout.addWidget(self.image_widget)

    def updateImage(self, image: Union[AcquiredImage, np.ndarray]):
        if isinstance(image, AcquiredImage):
            self.image_item.setImage(image.image, False)
            self.text_item.setText(f"{datetime.datetime.fromtimestamp(image.time).strftime('%x %X')}")
        else:
            self.image_item.setImage(image, False)
            # self.text_item.setText("")


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

    def updateImage(self, image: AcquiredImage):
        self.imageItem.setImage(image.image, False)


if __name__ == '__main__':
    import requests


    class ImageRequestWorker(QtCore.QThread):
        imageReady = QtCore.Signal(np.ndarray)

        def __init__(self):
            super().__init__()

        def run(self) -> None:
            while True:
                response = requests.get("https://picsum.photos/800/600")
                if response.status_code == 200:
                    try:
                        img = Image.open(io.BytesIO(response.content))
                        img = np.asarray(img)
                        self.imageReady.emit(img.transpose([1, 0, 2]), )
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
