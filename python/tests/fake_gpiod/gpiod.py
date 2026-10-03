"""
A stand-in for the libgpiod v2 bindings that works across processes (`tests/test_supervisor.py`).

Every `set_value` writes the line values to the JSON file named by `FAKE_GPIOD_STATE`
(``{"<chip>:<offset>": 0 | 1}``), so a test can watch what a supervisor process does to the
lines. The chips and their line names come from `FAKE_GPIOD_LINES` (``{"<chip>": [names]}``).
"""

import json
import os
from enum import Enum
from types import SimpleNamespace


class Direction(Enum):
    INPUT = 1
    OUTPUT = 2


class Value(Enum):
    INACTIVE = 0
    ACTIVE = 1


line = SimpleNamespace(Direction=Direction, Value=Value)


def _state_path():
    return os.environ["FAKE_GPIOD_STATE"]


def _write(key, value):
    path = _state_path()
    try:
        with open(path, encoding="utf-8") as handle:
            state = json.load(handle)
    except (FileNotFoundError, ValueError):
        state = {}
    state[key] = value
    temporary = f"{path}.{os.getpid()}"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(state, handle)
    os.replace(temporary, path)


class Chip:
    def __init__(self, path):
        self.path = path
        self.names = json.loads(os.environ["FAKE_GPIOD_LINES"]).get(path)
        if self.names is None:
            raise OSError(2, "No such chip")

    def line_offset_from_id(self, name):
        if name not in self.names:
            raise OSError(2, "No such line")
        return self.names.index(name)

    def close(self):
        pass


def LineSettings(direction, output_value):  # noqa: N802 - mirrors gpiod.LineSettings
    return {"direction": direction, "output_value": output_value}


class _Request:
    def __init__(self, path, offsets):
        self.path, self.offsets = path, offsets
        for offset in offsets:
            _write(f"{path}:{offset}", 0)

    def set_value(self, offset, value):
        assert offset in self.offsets
        _write(f"{self.path}:{offset}", value.value)

    def get_value(self, offset):
        with open(_state_path(), encoding="utf-8") as handle:
            return Value(json.load(handle)[f"{self.path}:{offset}"])

    def release(self):
        pass


def request_lines(path, consumer, config):
    if path not in json.loads(os.environ["FAKE_GPIOD_LINES"]):
        raise OSError(2, "No such chip")
    (offsets,) = config
    return _Request(path, offsets)
