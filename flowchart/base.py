from pyqtgraph import flowchart

_elements = []
_sources = []
_destination = []


def register_flowchart_element(category):
    def func(cls):
        _elements.append((cls, category))

    return func


def register_flowchart_source(observable, name):
    _sources.append((observable, name))


def register_flowchart_destination(name):
    def func(cls):
        _destination.append((cls, name))
