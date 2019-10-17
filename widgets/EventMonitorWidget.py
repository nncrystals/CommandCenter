import datetime
import sys
import time

from PySide2 import QtWidgets, QtCore, QtGui
import logging

from utils.QtInterceptHandler import QtInterceptHandler


class EventEntry(QtWidgets.QWidget):
    def __init__(self, parent, level, message):
        super().__init__(parent)
        self.message = message
        self.level = level
        now = datetime.datetime.now()
        self.timestr = now.strftime("%Y/%m/%d %H:%M:%S")
        self.hbox = QtWidgets.QHBoxLayout()
        self.setLayout(self.hbox)

        iconName = ""
        self.bgColor = ""
        if level <= logging.INFO:
            iconName = QtWidgets.QStyle.SP_MessageBoxInformation
            self.bgColor = "white"
        elif level <= logging.WARNING:
            iconName = QtWidgets.QStyle.SP_MessageBoxWarning
            self.bgColor = "yellow"
        elif level <= logging.ERROR:
            iconName = QtWidgets.QStyle.SP_MessageBoxCritical
            self.bgColor = "red"
        icon = self.style().standardIcon(iconName)
        iconWidget = QtWidgets.QLabel(self)
        iconWidget.setPixmap(QtGui.QPixmap(icon.pixmap(10, 10)))
        iconWidget.setFixedHeight(10)
        self.hbox.addWidget(iconWidget)
        messageWidget = QtWidgets.QLabel(self)
        messageWidget.setText(f"{self.timestr} {message}")
        self.hbox.addWidget(messageWidget)
        self.hbox.addStretch(1)

    def mouseDoubleClickEvent(self, a0: QtGui.QMouseEvent) -> None:
        dlg = DetailMessageDialog(self, self)
        dlg.show()

    def getSuggestedBackgroundColor(self):
        return self.bgColor


class DetailMessageDialog(QtWidgets.QDialog):
    def __init__(self, parent, evt: EventEntry):
        super().__init__(parent)
        self.evt = evt
        self.setLayout(QtWidgets.QVBoxLayout())
        disp = QtWidgets.QTextEdit(self)
        disp.setReadOnly(True)
        disp.setText(self.evt.message)
        self.layout().addWidget(disp)
        self.setMinimumSize(200, 100)
        self.setWindowTitle(f"{logging.getLevelName(evt.level)} on {evt.timestr}")


class EventMonitorWidget(QtWidgets.QListWidget):
    def __init__(self, parent, loggerName: str = "eventMonitor"):
        super().__init__(parent)
        self.setSelectionMode(self.NoSelection)
        self.loggerName = loggerName
        self.logger = logging.getLogger(self.loggerName)
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers.clear()
        self.handler = QtInterceptHandler()
        self.logger.addHandler(self.handler)
        self.handler.loggingRequested.connect(self.interceptMessage)

    def contextMenuEvent(self, evt: QtGui.QContextMenuEvent) -> None:
        menu = QtWidgets.QMenu(self)
        clear = QtWidgets.QAction("Clear all", self)
        clear.triggered.connect(self.clear)
        menu.addAction(clear)
        menu.exec(evt.globalPos())

    @QtCore.Slot
    def interceptMessage(self, level, message):
        item = QtWidgets.QListWidgetItem(self)
        entry = EventEntry(self, level, message)
        item.setSizeHint(entry.size())
        item.setBackground(QtGui.QColor(entry.getSuggestedBackgroundColor()))
        self.addItem(item)
        self.setItemWidget(item, entry)


if __name__ == '__main__':
    class LoggingThread(QtCore.QThread):
        def __init__(self):
            super().__init__()
            self.logger = logging.getLogger("test")

        def run(self) -> None:
            while True:
                self.logger.error("err")
                self.logger.warning("warn")
                self.logger.info("info")
                time.sleep(1)


    app = QtWidgets.QApplication(sys.argv)
    window = EventMonitorWidget(None, "test")
    window.show()
    worker = LoggingThread()
    worker.start()
    app.exec_()
