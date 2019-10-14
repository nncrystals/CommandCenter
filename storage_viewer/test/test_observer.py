from typing import Any
from unittest import TestCase

import rx
from rx.core import Observer


class TestObserver(Observer):
    def __init__(self, id_ = None, test_case: TestCase = None, on_next=None, on_error=None, on_completed=None):
        super().__init__(
            on_next or self.on_next_handler,
            on_error or self.on_error_handler,
            on_completed or self.on_completed_handler,
        )
        self.id_ = id_
        self.test_case = test_case
        self.prefix = f"{self.id_}: " if self.id_ is not None else ""

    def on_next_handler(self, value: Any) -> None:
        print(f"{self.prefix}{value}")

    def on_error_handler(self, error: Exception) -> None:
        if self.test_case is not None:
            self.test_case.fail(error)
            return
        print(f"{self.prefix}{error}")

    def on_completed_handler(self) -> None:
        print(f"{self.prefix}completed")

