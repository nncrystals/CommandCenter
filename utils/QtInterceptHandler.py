import logging
from rx.subject import Subject
from logging import StreamHandler


class QtInterceptHandler(StreamHandler):
    # (LOGGING.level, message)
    loggingRequested = Subject()

    def __init__(self):
        super(QtInterceptHandler, self).__init__()

    def emit(self, record, **kwargs):
        level = record.levelno
        message = record.getMessage()
        self.loggingRequested.on_next((level, message))
        super().emit(record)
