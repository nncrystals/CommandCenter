import sys
from widgets.MainWidget import MainWidget

from PyQt5 import QtWidgets
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MainWidget()
    window.show()
    app.exec()

