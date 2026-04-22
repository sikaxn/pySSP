from __future__ import annotations

import sys
import types

from .shared import *
from .constants import *
from .helpers import *
from .helpers import _equal_power_crossfade_volume
from .widgets import *
from .window import MainWindow

_IMPL_MODULES = [
    "shared",
    "constants",
    "helpers",
    "widgets",
    "timecode",
    "ui_build",
    "settings_archive",
    "tools_library",
    "pages_slots",
    "playback",
    "lyrics_stage",
    "remote_api",
    "actions_input",
    "locking",
    "window",
]


class _MainWindowPackage(types.ModuleType):
    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        package_name = self.__name__
        for module_name in _IMPL_MODULES:
            module = sys.modules.get(f"{package_name}.{module_name}")
            if module is None or module is self:
                continue
            module.__dict__[name] = value

    def __delattr__(self, name):
        super().__delattr__(name)
        package_name = self.__name__
        for module_name in _IMPL_MODULES:
            module = sys.modules.get(f"{package_name}.{module_name}")
            if module is None or module is self:
                continue
            module.__dict__.pop(name, None)


sys.modules[__name__].__class__ = _MainWindowPackage
