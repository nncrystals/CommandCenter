import io
import sys

from PIL import Image
from PyQt5 import QtWidgets, QtGui, QtCore
import pyqtgraph as pg
import msgpack
import numpy as np


class ImageViewer(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image_generator = None
        self.image_pos = []
        self.image_idx = 0
        self.image_path = None

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        self.image_item = pg.ImageItem()
        self.image_item.setOpts(axisOrder='row-major')
        self.image_widget = pg.GraphicsView()
        self.vb = pg.ViewBox()
        self.vb.addItem(self.image_item)
        self.image_widget.setCentralWidget(self.vb)
        layout.addWidget(self.image_widget)

    def keyPressEvent(self, a0: QtGui.QKeyEvent) -> None:
        key = a0.key()
        if key == QtCore.Qt.Key_Right:
            self.next_image()
        elif key == QtCore.Qt.Key_Left:
            self.prev_image()
        super().keyPressEvent(a0)

    def load_image(self, path):
        self.image_path = path

        def image_generator():
            with open(path, "rb") as f:
                unpacker = msgpack.Unpacker(f)
                self.image_pos.append(0)
                for val in unpacker:
                    self.image_pos.append(unpacker.tell())
                    yield val

        self.image_generator = image_generator()

    def load_labels(self, path):
        pass

    def next_image(self):
        if self.image_generator is None:
            return
        self.image_idx += 1
        self.show_image(next(self.image_generator))

    def prev_image(self):
        if self.image_generator is None:
            return
        if self.image_idx == 0:
            return
        self.image_idx -= 1
        pos = self.image_pos[self.image_idx]
        with open(self.image_path, "rb") as f:
            f.seek(pos)
            unpacker = msgpack.Unpacker(f)
            self.show_image(next(unpacker))

    def show_image(self, im):
        name, data, ts = im[b"name"], im[b"data"], im[b"ts"]
        im = Image.open(io.BytesIO(data))
        self.image_item.setImage(np.asarray(im))


class ImageViewerApp(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image_viewer_widget = ImageViewer(self)
        self.setCentralWidget(self.image_viewer_widget)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    image_viewer = ImageViewerApp()
    image_viewer.image_viewer_widget.load_image(sys.argv[1])
    image_viewer.show()
    app.exec()
