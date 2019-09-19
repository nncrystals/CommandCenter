import os
from PyQt5 import QtWidgets, QtGui, QtCore

settingPath = os.path.abspath(os.path.join("Configs", "settings.ini"))
globalSettings = QtCore.QSettings(settingPath, QtCore.QSettings.IniFormat)


def initializeSettingSection(defaults: dict):
    for k, v in defaults.items():
        if globalSettings.contains(k):
            continue
        globalSettings.setValue(k, v)
    globalSettings.sync()
