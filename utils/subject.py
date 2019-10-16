from typing import Optional, Union

from rx import subject
from rx.core import typing
from rx.scheduler import NewThreadScheduler


class ScheduledSubject(subject.Subject):

    def __init__(self) -> None:
        super().__init__()

    def subscribe(self, observer: Optional[Union[typing.Observer, typing.OnNext]] = None,
                  on_error: Optional[typing.OnError] = None, on_completed: Optional[typing.OnCompleted] = None,
                  on_next: Optional[typing.OnNext] = None, *,
                  scheduler: Optional[typing.Scheduler] = None) -> typing.Disposable:
        scheduler = scheduler or NewThreadScheduler()
        return super().subscribe(observer, on_error, on_completed, on_next, scheduler=scheduler)


class BackPressureSubject(subject.Subject):
    def __init__(self) -> None:
        super().__init__()
