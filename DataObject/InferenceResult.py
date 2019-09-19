import typing

import numpy as np


class ResultPerImage:
    def __init__(self):
        super().__init__()
        self.imageId: str



class InferenceResult:
    def __init__(self):
        super().__init__()
        self.returnImages: typing.Iterable[np.ndarray]

        self.resultsPerImage: typing.Iterable[ResultPerImage]
