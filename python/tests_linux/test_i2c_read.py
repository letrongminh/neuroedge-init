"""
Read-only I2C on `linux` against a real kernel adapter (TSK-I2a-03, RFC-0007 §3b).

Run by the `linux-hal` CI job after `scripts/setup_i2c_stub.sh`, which loads `i2c-stub`
with three chips: the `ina219` (0x40) and `ads7828` (0x4a) the `linux-rpi5` board
allow-lists, and the `lm75` (0x48) it does not:

    cd python && python -m pytest -q tests_linux

Registers are set with `i2cset` and read back through the HAL, which opens `/dev/i2c-N`
and issues SMBus reads. The policy itself — every refusal sends no transaction — is
proved against a recording fake in `tests/test_hal_i2c.py`; here the same is observed on
the chip: i2c-stub keeps a register pointer that a register read sets, so a refused read
that reached the bus would move it. A missing adapter is a failure, never a skip.
"""

from __future__ import annotations

import copy
import dataclasses
import os
import subprocess

import pytest

from neuroedge.engine.trace_sink import EventLog
from neuroedge.errors import BoardCapabilityError, PerceptionUnavailableError
from neuroedge.hal.board import load_board_by_id
from neuroedge.hal.i2c_bus import I2CProbe
from neuroedge.hal.linux import LinuxHAL

INA219, ADS7828 = "0x40", "0x4a"


def env(name: str) -> str:
    value = os.environ.get(name)
    assert value, f"{name} is not set; run scripts/setup_i2c_stub.sh first"
    return value


def i2cset(address: str, register: int, value: int, mode: str) -> None:
    subprocess.run(
        [
            "i2cset",
            "-f",
            "-y",
            env("NEUROEDGE_I2C_STUB_BUS"),
            address,
            hex(register),
            hex(value),
            mode,
        ],
        check=True,
    )


def i2cget(address: str, register: int | None = None) -> int:
    command = ["i2cget", "-f", "-y", env("NEUROEDGE_I2C_STUB_BUS"), address]
    if register is not None:
        command.append(hex(register))
    return int(subprocess.run(command, check=True, capture_output=True, text=True).stdout, 16)


def make_hal(board=None) -> LinuxHAL:
    node = f"/dev/i2c-{env('NEUROEDGE_I2C_STUB_BUS')}"
    return LinuxHAL(
        board,
        events=EventLog(target="linux", board_id="linux-rpi5"),
        authorize=lambda *_: None,
        i2c_nodes={"i2c1": node},
        display="memory",
    )


@pytest.fixture
def hal():
    hal = make_hal()
    yield hal
    hal.close()


def test_a_declared_register_reads_back_what_the_chip_holds(hal):
    i2cset(INA219, 0x03, 0x7A, "b")
    assert hal.i2c_read("i2c1", "ina219", 0x03, called_from="test") == 0x7A
    # An SMBus word is little-endian; the first byte on the wire is the high byte here.
    i2cset(INA219, 0x02, 0x3412, "w")
    assert hal.i2c_read("i2c1", "ina219", 0x02, width=2, called_from="test") == 0x1234
    assert hal.events.of_type("i2c_read") == [
        {"bus": "i2c1", "device": "ina219", "address": 0x40, "register": 3, "value": 0x7A},
        {"bus": "i2c1", "device": "ina219", "address": 0x40, "register": 2, "value": 0x1234},
    ]


def test_a_device_with_no_declared_registers_answers_a_receive_byte(hal):
    value = hal.i2c_read("i2c1", "ads7828", called_from="test")
    assert 0 <= value <= 0xFF
    assert hal.events.of_type("i2c_read") == [
        {"bus": "i2c1", "device": "ads7828", "address": 0x4A, "value": value}
    ]
    with pytest.raises(BoardCapabilityError, match="receive-byte only"):
        hal.i2c_read("i2c1", "ads7828", 0x00)


def test_an_undeclared_register_sends_nothing_to_the_chip(hal):
    for register, value in ((0x01, 0x11), (0x02, 0x22), (0x03, 0x33)):
        i2cset(INA219, register, value, "b")
    # Control: a declared register read leaves the stub's pointer just after it, so a
    # receive byte next returns the register that follows.
    assert hal.i2c_read("i2c1", "ina219", 0x01) == 0x11
    assert i2cget(INA219) == 0x22, "i2c-stub's pointer did not move as this test relies on"
    assert hal.i2c_read("i2c1", "ina219", 0x01) == 0x11  # pointer is 2 again
    # A refused register would point at 0x00 and move it to 1; it must not even be sent.
    with pytest.raises(BoardCapabilityError, match="readable_registers"):
        hal.i2c_read("i2c1", "ina219", 0x00, called_from="test")
    assert i2cget(INA219) == 0x22, "the refused read reached the chip"


def test_a_scan_lists_the_unlisted_chip_and_a_read_of_it_is_refused(hal):
    assert hal.i2c_scan("i2c1", called_from="test") == [
        I2CProbe(0x40, "ina219"),
        I2CProbe(0x48, None),
        I2CProbe(0x4A, "ads7828"),
    ]
    with pytest.raises(BoardCapabilityError, match="reported by a scan and never read"):
        hal.i2c_read("i2c1", 0x48, called_from="test")
    with pytest.raises(BoardCapabilityError, match="allow-list"):
        hal.i2c_read("i2c1", "lm75", 0x00, called_from="test")
    assert hal.events.of_type("i2c_read") == [], "neither a scan nor a refusal is an agent read"


def test_a_device_that_does_not_answer_is_perception_unavailable_after_one_retry():
    # A board that allow-lists a chip the stub does not have: the bus answers NACK.
    capabilities = copy.deepcopy(load_board_by_id("linux-rpi5").capabilities)
    capabilities["i2c"]["buses"][0]["devices"].append(
        {"name": "ghost", "address": 0x50, "readable_registers": [0x00]}
    )
    board = dataclasses.replace(load_board_by_id("linux-rpi5"), capabilities=capabilities)
    hal = make_hal(board)
    try:
        for args in (("ghost",), ("ghost", 0x00)):
            with pytest.raises(PerceptionUnavailableError) as raised:
                hal.i2c_read("i2c1", *args, called_from="test")
            assert raised.value.code == "NE5001"
        events = hal.events.of_type("i2c_read")
        assert len(events) == 2 and all("value" not in e and e["reason"] for e in events)
    finally:
        hal.close()


def test_a_missing_node_is_perception_unavailable_not_a_default():
    hal = LinuxHAL(
        events=EventLog(target="linux", board_id="linux-rpi5"),
        authorize=lambda *_: None,
        i2c_nodes={"i2c1": "/dev/i2c-250"},
        display="memory",
    )
    try:
        with pytest.raises(BoardCapabilityError, match="i2c-250"):
            hal.preflight(i2c=["i2c1"], where="test")
        with pytest.raises(PerceptionUnavailableError, match="ENOENT"):
            hal.i2c_read("i2c1", "ads7828", called_from="test")
    finally:
        hal.close()
