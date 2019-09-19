import functools
import glob
import logging
import os
import sys

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QDockWidget

from Services import configProvider
from Services.ImageSources import imageSourceList
from Widgets.ConsoleWidget import Console
from Services.Menus import ImageSourceMenu, LayoutMenu
from Widgets.ConfigDialog import ConfigDialog
from Widgets.HistogramDisplayWidgets import AreaDisplayWidget, EllipsesDisplayWidget
from Widgets.ImageDisplayWidget import ImageDisplayWidget


class MainWidget(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        # declaration
        self.layoutDirectory = os.path.abspath(os.path.join("Configs", "Layouts"))
        self.dockedPanels = None
        self.connectionSubMenu = ImageSourceMenu(self)
        self.logger = logging.getLogger("console")
        self.imageSource = None

        os.makedirs(self.layoutDirectory, exist_ok=True)

        self.initGUI()
        self.initMenu()

        self.setWindowTitle("Inference Block GUI")
        self.showMaximized()

    def initMenu(self):
        menuBar = self.menuBar()
        imageSourceMenu = menuBar.addMenu("&Image source")
        imageSourceMenu.addMenu(self.connectionSubMenu)

        connectionConnectAction = imageSourceMenu.addAction("C&onnect")
        connectionConnectAction.triggered.connect(self.connectImageSource)
        connectionConnectAction = imageSourceMenu.addAction("&Disconnect")
        connectionConnectAction.triggered.connect(self.disconnectImageSource)

        menuBar.addMenu(LayoutMenu(self.layoutDirectory, self))

        configurationAction = menuBar.addAction("&Configuration")
        configurationAction.triggered.connect(self.showConnectionConfigDialog)

    def initGUI(self):
        # dock
        self.setDockOptions(
            self.AllowNestedDocks | self.AllowTabbedDocks | self.AnimatedDocks | self.GroupedDragging
        )
        self.dockedPanels = {
            "input": QtWidgets.QDockWidget("Input image", self),
            "processed": QtWidgets.QDockWidget("Processed", self),
            "areaDist": QtWidgets.QDockWidget("Area distribution", self),
            "ellipseDist": QtWidgets.QDockWidget("Ellipse distribution", self),
            "console": QtWidgets.QDockWidget("Console", self)
        }

        # assign object name
        for k, v in self.dockedPanels.items():
            v.setObjectName(k)

        # Create widgets
        self.dockedPanels["input"].setWidget(ImageDisplayWidget(self))
        self.dockedPanels["processed"].setWidget(ImageDisplayWidget(self))
        self.dockedPanels["areaDist"].setWidget(AreaDisplayWidget(self))
        self.dockedPanels["ellipseDist"].setWidget(EllipsesDisplayWidget(self))
        self.dockedPanels["console"].setWidget(Console(self))

        self.applyDefaultLayout()

    def wireImageSourceSignals(self):
        assert self.imageSource is not None
        self.imageSource.imagesReady.connect(self.dockedPanels["input"].widget().updateImage)

    @QtCore.pyqtSlot()
    def applyDefaultLayout(self):
        v: QDockWidget
        mainPanel = self.dockedPanels["input"]
        for _, v in self.dockedPanels.items():
            self.addDockWidget(QtCore.Qt.TopDockWidgetArea, v)
            if v != mainPanel:
                self.tabifyDockWidget(mainPanel, v)
        mainPanel.raise_()

    @QtCore.pyqtSlot()
    def showConnectionConfigDialog(self):
        dialog = ConfigDialog(self)
        dialog.show()

    @QtCore.pyqtSlot()
    def connectImageSource(self):
        if self.imageSource is None:
            self.imageSource = imageSourceList[configProvider.globalSettings.value("Image_Source/source")]()
            self.wireImageSourceSignals()

        if self.imageSource.isRunning():
            self.logger.warning("Image source is already connected. Ignore connect request.")
            return

        self.imageSource.start()


    @QtCore.pyqtSlot()
    def disconnectImageSource(self):
        if self.imageSource is None or not self.imageSource.isRunning():
            self.logger.warning("Image source is not connected.")
            return
        self.imageSource.stop()
        self.imageSource = None

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MainWidget()
    window.show()
    app.exec_()
