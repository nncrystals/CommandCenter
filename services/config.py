import os
import typing
from pydoc import locate

from rx import subject

from PySide2 import QtCore

setting_updated_channel = subject.Subject()


class SettingRegistry(object):
    def __init__(self, key, value, type="str", title=None):
        self.value = value
        self.title = title
        self.type = type
        self.key = key


class SettingAccessor(object):
    def __init__(self, section=None):
        self.section = f"{section}/" if section else ""

    def __getitem__(self, item):
        item = self.section + item
        t = global_settings.value(f"{item}/type", defaultValue="str")
        default = global_settings.value(f"{item}/default", defaultValue=None)

        # https://bugreports.qt.io/browse/PYSIDE-820
        if t == "bool":
            value = global_settings.value(item, defaultValue=default)
            value = bool(value)
        else:
            value = global_settings.value(item, defaultValue=default, type=locate(t))

        return value
    def __setitem__(self, key, value):
        k = f"{self.section}{key}"
        global_settings.setValue(k, value)
        setting_updated_channel.on_next((k, value))


class DefaultSettingRegistration(object):
    def __init__(self, section):
        self.section = section

    def __call__(self, func):
        func(self.section)


setting_path = os.path.abspath(os.path.join("Configs", "settings.ini"))
global_settings = QtCore.QSettings(setting_path, QtCore.QSettings.IniFormat)


def default_settings(section: str, defaults: typing.Iterable[SettingRegistry]):
    """

    :param section:
    :param defaults:
    """
    for d in defaults:
        key = section + "/" + d.key
        if global_settings.contains(key):
            continue
        global_settings.setValue(key, d.value)
        if d.type != "str":
            global_settings.setValue(f"{key}/type", d.type)
        if d.title is not None:
            global_settings.setValue(f"{key}/title", d.title)
    global_settings.sync()
