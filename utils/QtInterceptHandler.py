from PyQt5 import QtCore
from logging import StreamHandler
import logging


class QtInterceptHandler(QtCore.QObject, StreamHandler):
    # (LOGGING.level, message)
    loggingRequested = QtCore.pyqtSignal(int, str)

    def __init__(self):
        super().__init__()

    def emit(self, record):
        level = record.levelno
        message = record.getMessage()
        self.loggingRequested.emit(level, message)
        super().emit(record)
