class Signal(object):
    def __init__(self):
        self._output_ports = []
        self._input_ports = []
        self._name = ""

    @property
    def name(self):
        return self._name
    @name.setter
    def name(self,  name):
        self._name = name

    @property
    def input_ports(self):
        return self._input_ports
    
    @property
    def output_ports(self):
        return self._output_ports
    

class Source(Signal):
    pass