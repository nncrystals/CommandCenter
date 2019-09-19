import argparse
from PyQt5 import QtWidgets
import sys

from Widgets.MainWidget import MainWidget

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--mock", help="running in mocking mode.", action="store_true")
    args = parser.parse_args()

    app = QtWidgets.QApplication(sys.argv)
    window = MainWidget()
    window.show()

    # receiver = DataReceiver("127.0.0.1", 11250)
    # receiver.start()
    #
    # receiver.newImageReceived.connect(window.updateImage)
    app.exec_()


