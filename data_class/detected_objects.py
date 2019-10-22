class DetectedObject:
    def __init__(self):
        super().__init__()
        self.maskRLE = None
        # self.mask = None
        self.bbox = None
        self.label = None
        self.score = None