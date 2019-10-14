import os
from collections import OrderedDict

import msgpack
import rx
from rx import disposable


class ImageLabelIndex(object):
    def __init__(self, name, image_offset, label_offset):
        self.name = name
        self.label_offset = label_offset
        self.image_offset = image_offset

    def __repr__(self) -> str:
        return f"name={self.name}, label_offset={self.label_offset}, image_offset={self.image_offset}"


class FileLoader(object):
    """
    Read data without cache the whole file
    """

    def __init__(self):
        super(FileLoader, self).__init__()

    def load_directory(self, path) -> (rx.Observable, rx.Observable):
        """
        Locate and load the *.bin files. Parse the file and create the index to labels and images rather than loading
        them directly to memory
        :param path: path to directory
        :return: 0:  observable reporting the progress based on file bytes. Will complete when finished.
        """

        def subscribe(observer, scheduler=None):
            subs = disposable.CompositeDisposable()
            image_storage = os.path.join(path, "images.bin")
            label_storage = os.path.join(path, "images.bin")

            if not os.path.exists(image_storage):
                raise FileNotFoundError(f"Image storage is not present in {path}")

            has_label = os.path.exists(label_storage)

            try:
                with open(image_storage, "rb") as f_image:
                    if has_label:
                        with open(label_storage, "rb") as f_label:
                            subs.add(self._index_image(f_image, f_label).subscribe(observer))
                    else:
                        subs.add(self._index_image(f_image, None).subscribe(observer))

            except FileNotFoundError:
                raise FileNotFoundError(f"Image storage is not present in {path}")
            except Exception:
                raise

            return subs

        return rx.create(subscribe)

    def get_data(self, index=None) -> object:
        pass

    def _index_image(self, f_image, f_label) -> rx.Observable:
        def subscribe(observer: rx.typing.Observer, scheduler=None):
            image_unpacker = msgpack.Unpacker(f_image)
            label_unpacker = msgpack.Unpacker(f_label)
            stop = False

            try:
                image_mapping = OrderedDict()
                label_mapping = OrderedDict()
                offset = 0
                for v in image_unpacker:
                    if stop:
                        raise InterruptedError("abort image indexing")
                    image_mapping[v[b"name"]] = offset
                    offset = image_unpacker.tell()

                offset = 0
                for v in label_unpacker:
                    if stop:
                        raise InterruptedError("abort label indexing")
                    label_mapping[v[b"name"]] = offset
                    offset = label_unpacker.tell()

                for name, img_offset in image_mapping.items():
                    if stop:
                        raise InterruptedError("abort assembling index")
                    label_offset = label_mapping[name] if name in label_mapping else None
                    observer.on_next(ImageLabelIndex(name, img_offset, label_offset))

            except InterruptedError:
                # disposed
                raise

            observer.on_completed()

            def dispose():
                stop = True

            return disposable.Disposable(dispose)

        return rx.create(subscribe)
