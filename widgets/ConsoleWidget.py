import datetime
import logging
import pyqtgraph.console as pgc
from PySide2 import QtWidgets, QtCore
from rx import operators
from utils.QtScheduler import QtScheduler

from utils.QtInterceptHandler import QtInterceptHandler


class Console(pgc.ConsoleWidget):
    def __init__(self, parent=None, namespace=None, historyFile=None, text=None, editor=None):
        super().__init__(parent, namespace, historyFile, text, editor)

        self.handler = QtInterceptHandler()
        self.interceptLogger = logging.getLogger("console")

        self.handler.loggingRequested.pipe(operators.observe_on(QtScheduler(QtCore))).subscribe(self.printLog)
        self.interceptLogger.setLevel(logging.DEBUG)
        self.interceptLogger.handlers.clear()
        self.interceptLogger.addHandler(self.handler)

        self.addClearUtility()

    def openMenu(self, position):
        menu = self.output.createStandardContextMenu()
        a = QtWidgets.QAction("C&lear")
        a.triggered.connect(lambda: self.output.clear())
        menu.addAction(a)
        menu.exec_(self.output.viewport().mapToGlobal(position))

    def addClearUtility(self):
        self.output.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.output.customContextMenuRequested.connect(self.openMenu)

    def printLog(self, x):
        level, message = x
        levelText = logging.getLevelName(level)
        timestamp = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        if level <= logging.INFO:
            background = "#fff"
            foreground = "#000"
        elif level <= logging.WARNING:
            background = "#fce803"
            foreground = "#000"
        elif level <= logging.ERROR:
            background = "#f00"
            foreground = "#fff"
        else:
            background = "#fff"
            foreground = "#000"

        self.write(
            f"<div style='background-color: {background}; color: {foreground}'>[{levelText}] @{timestamp}: {message}</div><br>",
            True)
