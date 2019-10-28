from collections import OrderedDict
from typing import Optional, Any

import msgpack

from data_class.subject_data import AcquiredImage


class Index(object):
    def __init__(self, value, id):
        self.value = value
        self.id = id


class MsgpackFileGenerator(object):
    index: OrderedDict

    def __init__(self, path, index=None):
        self.path = path
        self.index = None
        self.key_list = []
        self.cursor = 0
        if index is not None:
            self.index = index
        else:
            self.build_index()

    def build_index(self):
        index = OrderedDict()
        with open(self.path, "rb") as f:
            unpacker = msgpack.Unpacker(f)
            pos = 0
            for i, value in enumerate(unpacker):
                name = value[b"name"]
                index[name] = Index(pos, i)
                pos = unpacker.tell()

        self.index = index
        self.key_list = list(index.keys())

    def __getitem__(self, item):
        """
        access with [], the cursor does not update
        :param item: str
        :return:
        """
        return self.get(item, False)

    def get(self, item, update_cursor=False):
        with open(self.path, "rb") as f:
            idx: Index = self.index[item]
            f.seek(idx.value)
            unpacker = msgpack.Unpacker(f)
            v = unpacker.unpack()

        if update_cursor:
            self.cursor = idx.id

        return AcquiredImage(v[b"data"], v[b"ts"], v[b"name"])

    def __next__(self):
        try:
            return self.next()
        except (KeyError, IndexError):
            raise StopIteration()

    def __iter__(self):
        return self

    def next(self):
        cursor = self.cursor + 1
        key = self.key_list[cursor]
        value = self.get(key)
        self.cursor = cursor
        return value

    def prev(self):
        cursor = self.cursor - 1
        key = self.key_list[cursor]
        value = self.get(key)
        self.cursor = cursor
        return value


class ImageResultParser(object):
    def __init__(self) -> None:
        super().__init__()
        self.path = None
        self.index = OrderedDict()
        self.generator = None

    def load_file(self, path):
        self.path = path
        self.generator = MsgpackFileGenerator(self.path)
