import logging
import os
import sys

from PySide2 import QtWidgets, QtCore, QtGui
from PySide2.QtWidgets import QDockWidget

from rx import operators, disposable

from services import service_provider
from services.subjects import Subjects
from utils.QtScheduler import QtScheduler
from utils.observer import ErrorToConsoleObserver
from widgets.ConfigDialog import ConfigDialog
from widgets.ConsoleWidget import Console
from widgets.HistogramDisplayWidgets import AreaDisplayWidget, EllipsesDisplayWidget
from widgets.ImageDisplayWidget import SimpleDisplayWidget
from widgets.Menus import ImageSourceMenu, LayoutMenu, AnalyzerMenu, SimexMenu, SignalMappingMenu, HardwareControlMenu, \
    QuickConnectMenu
from widgets.TimelineWidget import TimelineWidget


class MainWidget(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        # declaration
        self.layoutDirectory = os.path.abspath(os.path.join("Configs"))
        self.dockedPanels = None
        self.logger = logging.getLogger("console")
        self.imageSource = None
        self.subscriptions = disposable.CompositeDisposable()
        os.makedirs(self.layoutDirectory, exist_ok=True)
        self.init_background_services()
        self.init_gui()
        self.init_menu()

        self.setWindowTitle("Command Center")
        self.showMaximized()

        self.configure_observers()

    def init_menu(self):
        menu_bar = self.menuBar()
        menu_bar.addMenu(QuickConnectMenu(self))
        image_source_menu = ImageSourceMenu(self)
        menu_bar.addMenu(image_source_menu)
        menu_bar.addMenu(AnalyzerMenu(self))
        menu_bar.addMenu(LayoutMenu(self.layoutDirectory, self))

        configuration_action = menu_bar.addAction("&Configuration")
        configuration_action.triggered.connect(self.showConnectionConfigDialog)

        simex_menu = SimexMenu(self)
        menu_bar.addMenu(simex_menu)

        menu_bar.addAction(SignalMappingMenu(self))
        menu_bar.addMenu(HardwareControlMenu(self))

    @staticmethod
    def init_background_services():
        service_provider.ResultProcessorProvider().get_or_create_instance(None)
        service_provider.ResultSaverProvider().get_or_create_instance(None)

    def init_gui(self):
        # dock
        self.setDockOptions(
            self.AllowNestedDocks | self.AllowTabbedDocks | self.AnimatedDocks | self.GroupedDragging
        )
        self.dockedPanels = {
            "input": QtWidgets.QDockWidget("Input image", self),
            "processed": QtWidgets.QDockWidget("Processed", self),
            "areaDist": QtWidgets.QDockWidget("Area distribution", self),
            "ellipseDist": QtWidgets.QDockWidget("Ellipse distribution", self),
            "timeline": QtWidgets.QDockWidget("Timeline", self),
            "console": QtWidgets.QDockWidget("Console", self),
        }

        # assign object name
        for k, v in self.dockedPanels.items():
            v.setObjectName(k)

        # Create widgets
        self.dockedPanels["input"].setWidget(SimpleDisplayWidget(self))
        self.dockedPanels["processed"].setWidget(SimpleDisplayWidget(self))
        self.dockedPanels["areaDist"].setWidget(AreaDisplayWidget(self))
        self.dockedPanels["ellipseDist"].setWidget(EllipsesDisplayWidget(self))
        self.dockedPanels["timeline"].setWidget(TimelineWidget(self))
        self.dockedPanels["console"].setWidget(Console(self))

        self.applyDefaultLayout()

    def configure_observers(self):
        qt_scheduler = QtScheduler(QtCore)
        subject_provider = service_provider.SubjectProvider()
        subjects: Subjects = subject_provider.get_or_create_instance(None)
        # display raw images
        self.subscriptions.add(
            subjects.image_producer.pipe(
                operators.observe_on(qt_scheduler),
            ).subscribe(ErrorToConsoleObserver(self.dockedPanels["input"].widget().updateImage))
        )

        # display processed images
        self.subscriptions.add(
            subjects.rendered_sample_image_producer.pipe(
                operators.observe_on(qt_scheduler),
            ).subscribe(ErrorToConsoleObserver(self.dockedPanels["processed"].widget().updateImage))
        )

        self.subscriptions.add(
            subjects.processed_distributions.pipe(
                operators.pluck_attr("dists"),
                operators.pluck("areas"),
                operators.observe_on(qt_scheduler),
            ).subscribe(ErrorToConsoleObserver(self.dockedPanels["areaDist"].widget().update_histogram))
        )

        self.subscriptions.add(
            subjects.processed_distributions.pipe(
                operators.pluck_attr("dists"),
                operators.pluck("ellipses"),
                operators.observe_on(qt_scheduler),
            ).subscribe(ErrorToConsoleObserver(self.dockedPanels["ellipseDist"].widget().update_histogram))
        )

        self.subscriptions.add(
            subjects.add_to_timeline.pipe(operators.observe_on(qt_scheduler)).subscribe(
                ErrorToConsoleObserver(self.dockedPanels["timeline"].widget().update_plot))
        )

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        self.subscriptions.dispose()
        super().closeEvent(a0)

    @QtCore.Slot()
    def applyDefaultLayout(self):
        v: QDockWidget
        mainPanel = self.dockedPanels["input"]
        for _, v in self.dockedPanels.items():
            self.addDockWidget(QtCore.Qt.TopDockWidgetArea, v)
            if v != mainPanel:
                self.tabifyDockWidget(mainPanel, v)
        mainPanel.raise_()

    @QtCore.Slot()
    def showConnectionConfigDialog(self):
        dialog = ConfigDialog(self)
        dialog.exec()


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MainWidget()
    window.show()
    app.exec_()
