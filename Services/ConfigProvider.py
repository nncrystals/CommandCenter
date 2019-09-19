import os
import typing
from pydoc import locate

from PyQt5 import QtWidgets, QtGui, QtCore

class SettingRegistry(object):
    def __init__(self, key, value, type="str", title=None):
        self.value = value
        self.title = title
        self.type = type
        self.key = key


class SettingAccessor(object):
    def __init__(self, section):
        self.section = section

    def __getitem__(self, item):
        type = globalSettings.value(f"{self.section}/{item}/type", defaultValue="str")
        return globalSettings.value(f"{self.section}/{item}", type=locate(type))

    def __setitem__(self, key, value):
        globalSettings.setValue(f"{self.section}/{key}", value)

class defaultSettingRegistration(object):
    def __init__(self, section):
        self.section = section

    def __call__(self, func):
        func(self.section)

settingPath = os.path.abspath(os.path.join("Configs", "settings.ini"))
globalSettings = QtCore.QSettings(settingPath, QtCore.QSettings.IniFormat)


def defaultSettings(defaults: dict):
    """

    :param defaults:
    :return:
    """
    defaultSettings("", defaults)


def defaultSettings(section: str, defaults: dict):
    """

    :param section:
    :param defaults:
    """
    for k, v in defaults.items():
        key = section + "/" + k
        if globalSettings.contains(key):
            continue
        globalSettings.setValue(key, v)
    globalSettings.sync()


def defaultSettings(section: str, defaults: typing.Iterable[SettingRegistry]):
    """

    :param section:
    :param defaults:
    """
    for d in defaults:
        key = section + "/" + d.key
        if globalSettings.contains(key):
            continue
        globalSettings.setValue(key, d.value)
        if d.type != "str":
            globalSettings.setValue(f"{key}/type", d.type)
        if d.title is not None:
            globalSettings.setValue(f"{key}/title", d.title)
    globalSettings.sync()




