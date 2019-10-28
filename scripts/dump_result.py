import argparse
import os
import zipfile

from data_class.subject_data import AcquiredImage
from services.result_parser import ImageResultParser

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("dir", help="path to storage dir")
    parser.add_argument("out", help="output zip")

    args = parser.parse_args()

    root = args.dir
    parser = ImageResultParser()
    parser.load_file(os.path.join(root, "images.bin"))
    with zipfile.ZipFile(args.out, "w") as z:
        value: AcquiredImage
        for value in parser.generator:
            z.writestr(value.name.decode(), value.image)

