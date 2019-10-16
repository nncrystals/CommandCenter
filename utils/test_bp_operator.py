import time
from unittest import TestCase

import rx
from rx import subject, operators
from rx.scheduler import NewThreadScheduler
from rxpy_backpressure import BackPressure

from utils.backpressure import bp_operator, bp_drop_operator_attach_size


class Test_bp_operator(TestCase):
    def setUp(self) -> None:
        # create source stream (fast)
        self.source = rx.interval(0.1)
        # and fast consumer
        self.observer = rx.core.Observer(lambda x: print(f"Received{x}"))
        self._stop = subject.Subject()

    def slow_op(self, val):
        if isinstance(val, tuple):
            val = val[0]

        if val > 5 and val < 10:
            print(f"[slow_op] I am stucked at slow_op: {val}")
            time.sleep(0.5)
            print(f"[slow_op] I am done: {val}")
        else:
            print(f"[slow_op] I am done: {val}")
        return val

    def stop(self, x):
        if x > 15:
            self._stop.on_next(0)

    def test_without_bp(self):
        self.source.pipe(
            operators.do_action(lambda x: print(f"Producing {x}")),
            operators.map(self.slow_op),
            operators.do_action(self.stop),
            operators.take_until(self._stop),
        ).run()

    def test_with_drop(self):
        self.source.pipe(
            operators.do_action(lambda x: print(f"Producing {x}")),
            bp_operator(BackPressure.DROP, 3),
            operators.map(self.slow_op),
            operators.do_action(self.stop),
            operators.take_until(self._stop),
        ).run()

    def test_with_latest(self):
        self.source.pipe(
            operators.do_action(lambda x: print(f"Producing {x}")),
            bp_operator(BackPressure.LATEST),
            operators.map(self.slow_op),
            operators.do_action(self.stop),
            operators.take_until(self._stop),
        ).run()

    def test_with_buffer(self):
        self.source.pipe(
            operators.do_action(lambda x: print(f"Producing {x}")),
            bp_operator(BackPressure.BUFFER),
            operators.map(self.slow_op),
            operators.do_action(self.stop),
            operators.take_until(self._stop),
        ).run()

    def test_with_observe_on(self):
        self.source.pipe(
            operators.do_action(lambda x: print(f"Producing {x}")),
            operators.observe_on(NewThreadScheduler()),
            operators.map(self.slow_op),
            operators.do_action(self.stop),
            operators.take_until(self._stop),
        ).run()

    def test_attach_size(self):
        self.source.pipe(
            operators.do_action(lambda x: print(f"Producing {x}")),
            bp_drop_operator_attach_size(3),
            operators.do_action(print),
            operators.map(self.slow_op),
            operators.do_action(self.stop),
            operators.take_until(self._stop),
        ).run()