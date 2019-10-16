from threading import Lock
from typing import Optional

import rx
from rx import subject, operators
from rx.core import typing
from rxpy_backpressure import BackPressure


class BackPressureItem(object):
    def __init__(self, back_pressure_token):
        self.back_pressure_token = back_pressure_token


class BackPressureObservable(rx.Observable):

    def __init__(self, subscribe: Optional[typing.Subscription] = None) -> None:
        super().__init__(subscribe)

        # let the down stream notify this observable.
        self.back_pressure_token = subject.BehaviorSubject(False)


def flow_control(should_stop: subject.BehaviorSubject) -> rx.Observable:
    """
    Flow control operator. Buffer the previous items and emit them gracefully (respecting the given should_stop/back pressure)
    :param should_stop:
    :return:
    """
    buffer = []
    _stop = subject.Subject()
    _upstream_completed = False

    def on_error(ex):
        _stop.on_next(0)
        raise ex

    def on_upstream_completed():
        _upstream_completed = True

    def upstream(source: rx.Observable):
        source.pipe(operators.take_until(_stop)).subscribe(
            lambda x: buffer.append(x),
            on_error,
            on_upstream_completed
        )

    def downstream_subscribe(observer: rx.core.Observer, sch: rx.typing.Scheduler = None):
        def emit_next():
            if len(buffer):
                observer.on_next(buffer.pop(0))
            else:
                if _upstream_completed:
                    observer.on_completed()

        def schedule_emit_next_until(until: subject.Subject):
            stop_emitting = False

            def _action(sch: rx.typing.Scheduler, state=None):
                emit_next()

            def until_on_next(v):
                nonlocal stop_emitting
                stop_emitting = True

            until.pipe(operators.take_until(_stop)).subscribe(until_on_next, scheduler=sch)

            if not stop_emitting:
                sch.schedule(_action)

        def should_stop_updated(val: bool):
            if val:
                # should stop, do nothing until next message
                pass
            else:
                # normal operation
                # Cannot guarantee that the should_stop will emit every time the value is received.
                schedule_emit_next_until(should_stop)

        should_stop.pipe(operators.take_until(_stop)).subscribe(should_stop_updated)

    return rx.create(downstream_subscribe)


class RequestNextObservable(rx.Observable):
    def __init__(self, request: subject.BehaviorSubject):
        """

        :param request: emit true to request next value.
        """
        super().__init__()
        self.request = request


class BackPressureAwareObservable(rx.Observable):
    """
    The *direct* down stream back pressure is monitored
    The user should handle when the observable should be stopped.
    """

    def __init__(self):
        super().__init__()
        self.back_pressure = subject.BehaviorSubject(False)


def bp_operator(strategy, *args):
    def upstream(source: rx.Observable):
        def subscribe(observer: rx.core.Observer, sche=None):
            return source.subscribe(strategy(observer, *args), sche)

        return rx.create(subscribe)

    return upstream


def bp_drop_operator_attach_size(cache_size=10):
    """
    Create back pressure drop operator and attach the current buffer size as a tuple.
    :param cache_size:
    :return:
    """

    def upstream(source: rx.Observable):
        def subscribe(observer: rx.core.Observer, sche=None):
            op = BackPressure.DROP(observer, cache_size)
            _on_next = op.wrapped_observer.on_next

            def inject_on_next(value):
                _on_next((value, len(op._DropBackPressureStrategy__message_cache)))

            op.wrapped_observer.on_next = inject_on_next
            return source.subscribe(op, sche)

        return rx.create(subscribe)

    return upstream


def bp_drop_report_full(report_stream: rx.core.Observer, cache_size=10, threshold=None):
    if threshold is None:
        threshold = cache_size

    def upstream(source: rx.Observable):
        def subscribe(observer: rx.core.Observer, sche=None):
            op = BackPressure.DROP(observer, cache_size)

            def update_stream(*args):
                size = len(op._DropBackPressureStrategy__message_cache)
                if size >= threshold:
                    report_stream.on_next(True)
                else:
                    report_stream.on_next(False)

            _on_next = op.wrapped_observer.on_next

            def inject_on_next(value):
                _on_next(value)
                update_stream()

            op.wrapped_observer.on_next = inject_on_next
            return source.pipe(operators.do_action(update_stream)).subscribe(op, sche)

        return rx.create(subscribe)

    return upstream
