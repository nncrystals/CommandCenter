from typing import List
from unittest import TestCase

from rx import operators

from storage_viewer.file_loader import FileLoader, ImageLabelIndex
from storage_viewer.operators import buffer_until_complete
from storage_viewer.test.test_observer import TestObserver

DIR_PATH = "/tmp"
class TestFileLoader(TestCase):
    def test_load_directory(self):
        fl = FileLoader()
        observer = TestObserver("load directory", self)
        def report(x: List[ImageLabelIndex]):
            print(f"Indexed {len(x)} objects")
            if len(x):
                print(repr(x[0]))
        observer = TestObserver("load directory", self, on_next=report)

        fl.load_directory(DIR_PATH).pipe(buffer_until_complete()).subscribe(observer)
