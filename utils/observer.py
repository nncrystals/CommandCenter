import logging
import traceback

from rx.core import Observer


class ErrorToConsoleObserver(Observer):
    def __init__(self, on_next=None, on_error=None, on_completed=None, logger=None):
        super().__init__(on_next, on_error or self.on_error_default, on_completed)
        self.logger = logger or logging.getLogger("console")

    def on_error_default(self, ex: Exception):
        self.logger.error(ex)
        self.logger.debug(traceback.format_exc())
