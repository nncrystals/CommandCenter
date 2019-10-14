import rx
from rx import operators
from rx import subject


def buffer_until_complete():
    def _buffer_until_complete(source: rx.Observable):
        def do_boundary():
            boundary.on_next(0)
            boundary.on_completed()
        boundary = subject.Subject()
        source.subscribe(on_completed=do_boundary)
        return operators.buffer(boundary)(source)
    return _buffer_until_complete
