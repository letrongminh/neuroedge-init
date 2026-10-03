"""
TSK-I2a-03 — read-only I2C for agents (RFC-0007 §3b, §3e).

The policy runs against a fake bus that records every transaction, so "no transaction"
is asserted here and not only on `i2c-stub`; the transport against a fake `ioctl`; the
HALs and an `@action` end to end. The same code against a real kernel adapter
(`i2c-stub`) is `tests_linux/test_i2c_read.py`, run by the `linux-hal` CI job.
"""

from __future__ import annotations

import ctypes
import errno
import inspect

import pytest

import neuroedge.hal.i2c_bus as i2c_bus
import neuroedge.hal.linux as linux
from neuroedge import action
from neuroedge.actions import Conversation
from neuroedge.engine import ActionContractEngine, EventLog, resolve_gate_document
from neuroedge.engine.compiler import check_actions, check_capabilities, load_agent_manifest
from neuroedge.errors import (
    ActionContractViolation,
    AgentManifestError,
    BoardCapabilityError,
    PerceptionUnavailableError,
)
from neuroedge.hal import HardwareAbstractionLayer, i2c
from neuroedge.hal.board import load_board_by_id
from neuroedge.hal.i2c_bus import (
    I2CProbe,
    I2CReader,
    LinuxI2CBus,
    ReadFault,
    parse_buses,
)
from neuroedge.hal.linux import LinuxHAL
from neuroedge.hal.sim import SimHAL
from neuroedge.trace import validate_trace

from .test_hal_linux import LINES, FakeGpiod

BOARD = load_board_by_id("linux-rpi5")  # ina219 @0x40 regs 1..4, ads7828 @0x4a: receive-byte only


@pytest.fixture(autouse=True)
def no_machine_wiring(monkeypatch):
    monkeypatch.delenv(linux.I2C_ENV, raising=False)


class RecordingBus:
    """
    A bus that answers from a table and records every transaction it is sent.
    `present` addresses answer a receive byte; `registers` maps (address, register) to a
    list of outcomes consumed in order — an int is an answer, an OSError is raised.
    """

    def __init__(self, present=(), registers=None):
        self.present = set(present)
        self.registers = {key: list(value) for key, value in (registers or {}).items()}
        self.transactions: list[tuple] = []
        self.closed = False

    def receive_byte(self, address):
        self.transactions.append(("receive_byte", address))
        if address not in self.present:
            raise OSError(errno.ENXIO, "No such device or address")
        return 0

    def read_register(self, address, register, width):
        self.transactions.append(("read_register", address, register, width))
        outcomes = self.registers.get((address, register))
        if not outcomes:
            raise OSError(errno.ENXIO, "No such device or address")
        outcome = outcomes.pop(0)
        if isinstance(outcome, OSError):
            raise outcome
        return outcome

    def check(self):
        return None

    def close(self):
        self.closed = True


def reader_on(bus, board=BOARD):
    events = []
    opened: list[str] = []

    def open_bus(name, where):
        opened.append(name)
        return bus

    reader = I2CReader(board, open_bus, lambda type, data: events.append((type, data)))
    return reader, events, opened


# --- the allow-list: refused before any transaction -------------------------------------


def test_a_declared_register_is_one_pointer_write_then_a_repeated_start_read():
    bus = RecordingBus(registers={(0x40, 0x02): [0x0C80]})
    reader, events, _ = reader_on(bus)
    assert reader.read("i2c1", "ina219", 0x02, width=2, called_from="test") == 0x0C80
    assert bus.transactions == [("read_register", 0x40, 0x02, 2)]
    assert events == [
        (
            "i2c_read",
            {"bus": "i2c1", "device": "ina219", "address": 0x40, "register": 2, "value": 0x0C80},
        )
    ]


def test_a_device_with_no_readable_registers_is_receive_byte_only():
    bus = RecordingBus(present={0x4A})
    reader, events, _ = reader_on(bus)
    assert reader.read("i2c1", "ads7828") == 0
    assert bus.transactions == [("receive_byte", 0x4A)]
    # No `register` key on a receive byte (docs/spec/simulation_coverage.md).
    assert events == [
        ("i2c_read", {"bus": "i2c1", "device": "ads7828", "address": 0x4A, "value": 0})
    ]
    with pytest.raises(BoardCapabilityError, match="receive-byte only"):
        reader.read("i2c1", "ads7828", 0x00)
    assert bus.transactions == [("receive_byte", 0x4A)], "the refused read sent nothing"


@pytest.mark.parametrize("register", [0x00, 0x05, 0xFF, 0x100, -1, True, "1"])
def test_an_undeclared_register_is_refused_with_no_transaction(register):
    bus = RecordingBus(registers={(0x40, 0x05): [1]})
    reader, events, opened = reader_on(bus)
    with pytest.raises(BoardCapabilityError, match="readable_registers"):
        reader.read("i2c1", "ina219", register, called_from="actions/power.py:7")
    assert bus.transactions == [] and events == []
    assert opened == [], "the board decided before a bus was even opened"


@pytest.mark.parametrize(
    ("bus_id", "device"),
    [
        ("i2c1", "lm75"),  # a device the board does not list
        ("i2c1", 0x48),  # an address outside the allow-list, however it is written
        ("i2c1", 0x7F),
        ("i2c9", "ina219"),  # a bus the board does not declare
        ("i2c1", True),
        ("i2c1", 4.0),
        ("i2c1", None),
    ],
)
def test_a_read_outside_the_allow_list_is_refused_with_no_transaction(bus_id, device):
    bus = RecordingBus(present={0x48, 0x40}, registers={(0x48, 0): [1]})
    reader, events, opened = reader_on(bus)
    with pytest.raises(BoardCapabilityError):
        reader.read(bus_id, device)
    with pytest.raises(BoardCapabilityError):
        reader.read(bus_id, device, 0x01)
    assert bus.transactions == [] and events == [] and opened == []


def test_an_allow_listed_address_may_be_named_by_number():
    bus = RecordingBus(registers={(0x40, 0x01): [7]})
    reader, events, _ = reader_on(bus)
    assert reader.read("i2c1", 0x40, 0x01) == 7
    assert events[0][1]["device"] == "ina219"


@pytest.mark.parametrize(
    ("register", "width"), [(0x01, 0), (0x01, 3), (0x01, True), (None, 2), (0x01, "1")]
)
def test_a_width_other_than_one_byte_or_one_register_is_refused(register, width):
    bus = RecordingBus(present={0x40}, registers={(0x40, 0x01): [1]})
    reader, _, _ = reader_on(bus)
    with pytest.raises(BoardCapabilityError):
        reader.read("i2c1", "ina219", register, width=width)
    assert bus.transactions == []


def test_a_board_without_i2c_refuses_every_read():
    reader, _, opened = reader_on(
        RecordingBus(present={0x40}), board=load_board_by_id("sim-default")
    )
    with pytest.raises(BoardCapabilityError, match="declares no I2C bus"):
        reader.read("i2c1", "ina219")
    assert opened == []


# --- a scan is read-byte probes only ----------------------------------------------------


def test_a_scan_lists_addresses_outside_the_allow_list_with_read_byte_probes_only():
    bus = RecordingBus(present={0x40, 0x48, 0x4A})
    reader, events, _ = reader_on(bus)
    found = reader.scan("i2c1", called_from="test")
    assert found == [I2CProbe(0x40, "ina219"), I2CProbe(0x48, None), I2CProbe(0x4A, "ads7828")]
    # Every transaction is a receive byte; the whole 0x03..0x77 range is probed once.
    assert {kind for kind, *_ in bus.transactions} == {"receive_byte"}
    assert [address for _, address in bus.transactions] == list(range(0x03, 0x78))
    assert events == [], "a scan reads nothing the agent sees"


def test_an_address_the_scan_found_is_still_refused_to_a_read():
    bus = RecordingBus(present={0x48}, registers={(0x48, 0x00): [25]})
    reader, _, _ = reader_on(bus)
    assert [p.address for p in reader.scan("i2c1")] == [0x48]
    sent = list(bus.transactions)
    with pytest.raises(BoardCapabilityError, match="reported by a scan and never read"):
        reader.read("i2c1", 0x48)
    with pytest.raises(BoardCapabilityError):
        reader.read("i2c1", 0x48, 0x00)
    assert bus.transactions == sent


def test_a_scan_does_not_report_a_broken_bus_as_an_empty_one():
    class Broken(RecordingBus):
        def receive_byte(self, address):
            raise OSError(errno.EIO, "Input/output error")

    reader, _, _ = reader_on(Broken())
    with pytest.raises(PerceptionUnavailableError, match="EIO"):
        reader.scan("i2c1")


def test_a_scan_of_an_undeclared_bus_is_refused_before_a_probe():
    bus = RecordingBus(present={0x40})
    reader, _, opened = reader_on(bus)
    with pytest.raises(BoardCapabilityError):
        reader.scan("i2c9")
    assert bus.transactions == [] and opened == []


# --- NACK, timeout: one retry, then NE5001 ----------------------------------------------


NACK = OSError(errno.ENXIO, "No such device or address")
TIMEOUT = OSError(errno.ETIMEDOUT, "Connection timed out")


def test_a_nack_is_retried_once_and_a_second_answer_is_returned():
    bus = RecordingBus(registers={(0x40, 0x01): [NACK, 0x1234]})
    reader, events, _ = reader_on(bus)
    assert reader.read("i2c1", "ina219", 0x01, width=2) == 0x1234
    assert len(bus.transactions) == 2
    assert [e[0] for e in events] == ["i2c_read"] and events[0][1]["value"] == 0x1234


@pytest.mark.parametrize("fault", [NACK, TIMEOUT], ids=["nack", "timeout"])
def test_a_read_that_fails_twice_is_perception_unavailable_never_a_value(fault):
    bus = RecordingBus(registers={(0x40, 0x01): [fault, fault, 99]})
    reader, events, _ = reader_on(bus)
    with pytest.raises(PerceptionUnavailableError) as raised:
        reader.read("i2c1", "ina219", 0x01, width=2, called_from="actions/power.py:9")
    assert raised.value.code == "NE5001"
    assert "actions/power.py:9" in raised.value.where and "BLOCK" in raised.value.how
    assert len(bus.transactions) == 2, "at most one retry"
    (event,) = events
    assert event[0] == "i2c_read" and "value" not in event[1]
    assert errno.errorcode[fault.errno] in event[1]["reason"]


@pytest.mark.parametrize("garbage", [-1, 256, 3.0, None, True, "x"])
def test_a_value_that_is_not_a_byte_is_a_failed_read(garbage):
    bus = RecordingBus(registers={(0x40, 0x01): [garbage, garbage]})
    reader, events, _ = reader_on(bus)
    with pytest.raises(PerceptionUnavailableError):
        reader.read("i2c1", "ina219", 0x01)
    assert "value" not in events[-1][1]


def test_a_word_wider_than_two_bytes_is_a_failed_read():
    bus = RecordingBus(registers={(0x40, 0x01): [0x10000, 0x10000]})
    reader, _, _ = reader_on(bus)
    with pytest.raises(PerceptionUnavailableError):
        reader.read("i2c1", "ina219", 0x01, width=2)


# --- there is no way to write -----------------------------------------------------------


def test_no_layer_has_a_method_that_sends_data():
    def public(thing):
        return {name for name in dir(thing) if not name.startswith("_")}

    transport = {"receive_byte", "read_register", "check", "close"}
    assert public(LinuxI2CBus) == public(i2c_bus.I2CTransport) == transport
    assert public(I2CReader) == {"read", "scan", "resolve", "device", "check_bus", "close"}
    assert {n for n in dir(HardwareAbstractionLayer) if "i2c" in n} == {"i2c_read", "i2c_scan"}
    assert {n for n in dir(SimHAL) if "i2c" in n} == {
        "i2c_read",
        "i2c_scan",
        "set_i2c",  # scenario setup on sim: what a read will return, not a bus write
        "script_i2c",
    }
    assert {n for n, _ in inspect.getmembers(i2c, inspect.isfunction) if n[0] != "_"} == {"read"}


# --- the Linux transport: SMBus read requests only --------------------------------------


class FakeKernel:
    """
    `os.open`, `os.close` and `fcntl.ioctl` of one i2c-dev node, recording every request.
    Only the `answering` addresses (default: all) acknowledge; `fail` outcomes are raised
    by the next ioctls.
    """

    def __init__(self, monkeypatch, *, byte=0x5A, word=0x1234, fail=(), answering=None):
        self.calls: list[tuple] = []
        self.byte, self.word, self.fail, self.answering = byte, word, list(fail), answering
        self.address = None
        monkeypatch.setattr(i2c_bus.os, "open", self._open)
        monkeypatch.setattr(i2c_bus.os, "close", lambda fd: self.calls.append(("close", fd)))
        monkeypatch.setattr(i2c_bus.fcntl, "ioctl", self._ioctl)

    def _open(self, path, flags):
        self.calls.append(("open", path, flags))
        return 11

    def _ioctl(self, fd, request, arg):
        assert fd == 11
        if self.fail:
            raise self.fail.pop(0)
        if request == i2c_bus.I2C_SLAVE_FORCE:
            self.calls.append(("slave", arg))
            self.address = arg
            return 0
        assert request == i2c_bus.I2C_SMBUS
        self.calls.append(("smbus", arg.read_write, arg.command, arg.size))
        if self.answering is not None and self.address not in self.answering:
            raise OSError(errno.ENXIO, "No such device or address")
        if arg.size == i2c_bus.I2C_SMBUS_WORD_DATA:
            arg.data.contents.word = self.word
        else:
            arg.data.contents.byte = self.byte
        return 0

    def smbus(self):
        return [call for call in self.calls if call[0] == "smbus"]


def test_the_linux_bus_issues_only_smbus_reads_of_three_shapes(monkeypatch):
    kernel = FakeKernel(monkeypatch)
    bus = LinuxI2CBus("/dev/i2c-1")
    assert bus.receive_byte(0x4A) == 0x5A
    assert bus.read_register(0x40, 0x02, 1) == 0x5A
    # SMBus words are low byte first; the first byte on the wire is the high byte here.
    assert bus.read_register(0x40, 0x02, 2) == 0x3412
    assert kernel.smbus() == [
        ("smbus", i2c_bus.I2C_SMBUS_READ, 0, i2c_bus.I2C_SMBUS_BYTE),
        ("smbus", i2c_bus.I2C_SMBUS_READ, 0x02, i2c_bus.I2C_SMBUS_BYTE_DATA),
        ("smbus", i2c_bus.I2C_SMBUS_READ, 0x02, i2c_bus.I2C_SMBUS_WORD_DATA),
    ]
    # The direction of every request is a read (1); a write is 0 and is never built.
    assert {call[1] for call in kernel.smbus()} == {1}
    assert i2c_bus.I2C_SMBUS_READ == 1
    # The address is set once per change, with the force request a hwmon-bound chip needs.
    assert [c for c in kernel.calls if c[0] == "slave"] == [("slave", 0x4A), ("slave", 0x40)]
    assert [c for c in kernel.calls if c[0] == "open"] == [
        ("open", "/dev/i2c-1", i2c_bus.os.O_RDWR | i2c_bus.os.O_CLOEXEC)
    ]
    bus.close()
    bus.close()
    assert [c for c in kernel.calls if c[0] == "close"] == [("close", 11)], "close is idempotent"


def test_the_smbus_request_has_the_kernels_layout():
    # struct i2c_smbus_ioctl_data { __u8 read_write; __u8 command; __u32 size; void *data; }
    assert [getattr(i2c_bus._SmbusIoctl, f).offset for f in ("read_write", "command", "size")] == [
        0,
        1,
        4,
    ]
    assert i2c_bus._SmbusIoctl.data.offset % ctypes.sizeof(ctypes.c_void_p) == 0
    # union i2c_smbus_data { __u8 byte; __u16 word; __u8 block[34]; }
    assert ctypes.sizeof(i2c_bus._SmbusData) == 34


def test_a_failed_ioctl_resets_the_address_so_the_next_read_sets_it_again(monkeypatch):
    kernel = FakeKernel(monkeypatch)
    bus = LinuxI2CBus("/dev/i2c-1")
    bus.receive_byte(0x4A)
    kernel.fail.append(OSError(errno.ENXIO, "nack"))
    with pytest.raises(OSError):
        bus.receive_byte(0x4A)
    bus.receive_byte(0x4A)
    assert [c for c in kernel.calls if c[0] == "slave"] == [("slave", 0x4A), ("slave", 0x4A)]


def test_a_missing_node_fails_the_check_and_the_read(monkeypatch):
    def missing(path, flags):
        raise FileNotFoundError(errno.ENOENT, "No such file or directory", path)

    monkeypatch.setattr(i2c_bus.os, "open", missing)
    bus = LinuxI2CBus("/dev/i2c-9")
    with pytest.raises(OSError, match="i2c-9"):
        bus.check()
    reader, _, _ = reader_on(bus)
    with pytest.raises(BoardCapabilityError, match="cannot open the device node.*ENOENT"):
        reader.check_bus("i2c1", "test")
    with pytest.raises(PerceptionUnavailableError, match="ENOENT"):
        reader.read("i2c1", "ads7828")


# --- sim: replays, never scans -----------------------------------------------------------

SIM = load_board_by_id("sim-rpi5")


def test_sim_replays_what_the_scenario_sets_and_records_each_read():
    events = EventLog()
    hal = SimHAL(SIM, events=events)
    hal.set_i2c("i2c1", "ina219", 0x02, 0x0C80, width=2)
    hal.set_i2c("i2c1", "ads7828", None, 7)
    assert hal.i2c_read("i2c1", "ina219", 0x02, width=2, called_from="test") == 0x0C80
    assert hal.i2c_read("i2c1", "ads7828") == 7
    assert events.of_type("i2c_read") == [
        {"bus": "i2c1", "device": "ina219", "address": 0x40, "register": 2, "value": 0x0C80},
        {"bus": "i2c1", "device": "ads7828", "address": 0x4A, "value": 7},
    ]


def test_sim_never_invents_a_reading():
    events = EventLog()
    hal = SimHAL(SIM, events=events)
    with pytest.raises(PerceptionUnavailableError, match="nothing is scripted"):
        hal.i2c_read("i2c1", "ina219", 0x01)
    (event,) = events.of_type("i2c_read")
    assert "value" not in event and "nothing is scripted" in event["reason"]


def test_sim_has_the_same_allow_list_as_linux():
    hal = SimHAL(SIM)
    hal.set_i2c("i2c1", "ina219", 0x01, 1)
    with pytest.raises(BoardCapabilityError, match="readable_registers"):
        hal.i2c_read("i2c1", "ina219", 0x00)
    with pytest.raises(BoardCapabilityError, match="allow-list"):
        hal.i2c_read("i2c1", 0x48)
    for bad in (("i2c1", "ina219", 0x00, 1), ("i2c1", 0x48, None, 1), ("i2c9", "ina219", None, 1)):
        with pytest.raises(BoardCapabilityError):
            hal.set_i2c(*bad)
    with pytest.raises(BoardCapabilityError, match="not a 1-byte"):
        hal.set_i2c("i2c1", "ina219", 0x01, 256)


def test_sim_does_not_scan():
    with pytest.raises(BoardCapabilityError, match="no bus to scan"):
        SimHAL(SIM).i2c_scan("i2c1")


def test_a_hal_without_i2c_says_so():
    with pytest.raises(BoardCapabilityError, match="not implemented on target"):
        HardwareAbstractionLayer().i2c_read("i2c1", "ina219")


# --- linux: the machine chooses the node ------------------------------------------------


@pytest.fixture
def linux_hal(tmp_path):
    chip = tmp_path / "gpiochip0"
    chip.write_text("")

    def make(**kwargs):
        events = kwargs.pop("events", EventLog(target="linux", board_id="linux-rpi5"))
        return LinuxHAL(
            BOARD,
            chip_glob=str(tmp_path / "gpiochip*"),
            gpiod=FakeGpiod({str(chip): LINES}),
            events=events,
            authorize=lambda *_: None,
            **kwargs,
        )

    return make


def test_linux_reads_through_the_node_the_machine_chose(linux_hal, monkeypatch):
    kernel = FakeKernel(monkeypatch, byte=0x31)
    hal = linux_hal(i2c_nodes={"i2c1": "/dev/i2c-3"})
    assert hal.i2c_read("i2c1", "ads7828", called_from="test") == 0x31
    assert ("open", "/dev/i2c-3", i2c_bus.os.O_RDWR | i2c_bus.os.O_CLOEXEC) in kernel.calls
    assert hal.events.of_type("i2c_read") == [
        {"bus": "i2c1", "device": "ads7828", "address": 0x4A, "value": 0x31}
    ]
    hal.close()
    assert ("close", 11) in kernel.calls, "close releases the node"


def test_the_node_can_come_from_the_environment(linux_hal, monkeypatch):
    kernel = FakeKernel(monkeypatch)
    monkeypatch.setenv(linux.I2C_ENV, " i2c1 = /dev/i2c-5 ; ")
    linux_hal().i2c_read("i2c1", "ads7828")
    assert kernel.calls[0][1] == "/dev/i2c-5"


def test_no_node_is_guessed(linux_hal, monkeypatch):
    kernel = FakeKernel(monkeypatch)
    hal = linux_hal()
    with pytest.raises(BoardCapabilityError, match="refusing to guess") as raised:
        hal.i2c_read("i2c1", "ads7828")
    assert "NEUROEDGE_LINUX_I2C" in raised.value.how
    assert kernel.calls == []
    assert hal.events.of_type("i2c_read") == []


def test_the_allow_list_is_checked_before_the_node_is_looked_up(linux_hal, monkeypatch):
    kernel = FakeKernel(monkeypatch)
    hal = linux_hal()  # no node chosen at all
    with pytest.raises(BoardCapabilityError, match="readable_registers"):
        hal.i2c_read("i2c1", "ina219", 0x00)  # the register, not the node, is what is wrong
    with pytest.raises(BoardCapabilityError, match="allow-list"):
        hal.i2c_read("i2c1", 0x48)
    assert kernel.calls == []


@pytest.mark.parametrize(
    ("value", "why"), [("i2c1", "is not bus=node"), ("=/dev/i2c-1", "is not bus=node")]
)
def test_a_malformed_mapping_fails_before_any_line(monkeypatch, tmp_path, value, why):
    monkeypatch.setenv(linux.I2C_ENV, value)
    chip = tmp_path / "gpiochip0"
    chip.write_text("")
    fake = FakeGpiod({str(chip): LINES})
    with pytest.raises(BoardCapabilityError, match=why):
        LinuxHAL(chip_glob=str(tmp_path / "gpiochip*"), gpiod=fake)
    assert fake.requests == []


def test_a_mapping_for_a_bus_the_board_lacks_is_refused_before_any_line(linux_hal, tmp_path):
    with pytest.raises(BoardCapabilityError, match="declares no I2C bus 'i2c7'"):
        linux_hal(i2c_nodes={"i2c7": "/dev/i2c-7"})


def test_a_nack_on_linux_is_retried_once_then_ne5001(linux_hal, monkeypatch):
    kernel = FakeKernel(monkeypatch, fail=[OSError(errno.ENXIO, "nack")] * 2)
    hal = linux_hal(i2c_nodes={"i2c1": "/dev/i2c-1"})
    with pytest.raises(PerceptionUnavailableError, match="ENXIO"):
        hal.i2c_read("i2c1", "ads7828")
    assert hal.events.of_type("i2c_read")[0]["reason"].startswith("ENXIO")
    # The fault hit the slave-address ioctl each time; nothing was ever sent after it.
    assert kernel.smbus() == []


def test_linux_scans_with_read_byte_probes_only(linux_hal, monkeypatch):
    kernel = FakeKernel(monkeypatch, answering={0x48})
    found = linux_hal(i2c_nodes={"i2c1": "/dev/i2c-1"}).i2c_scan("i2c1")
    assert found == [I2CProbe(0x48, None)]
    probes = kernel.smbus()
    assert len(probes) == 0x78 - 0x03, "every address of 0x03..0x77, once"
    # Every probe is a receive byte read: never a quick-write (size 0), never a register.
    assert {(read_write, command, size) for _, read_write, command, size in probes} == {
        (i2c_bus.I2C_SMBUS_READ, 0, i2c_bus.I2C_SMBUS_BYTE)
    }


def test_parse_buses():
    assert parse_buses("i2c1=/dev/i2c-1; i2c0 = /dev/i2c-3 ;", "env") == {
        "i2c1": "/dev/i2c-1",
        "i2c0": "/dev/i2c-3",
    }


def test_a_preflight_refuses_an_unmapped_bus_before_any_line(tmp_path, monkeypatch):
    kernel = FakeKernel(monkeypatch)
    chip = tmp_path / "gpiochip0"
    chip.write_text("")
    fake = FakeGpiod({str(chip): LINES})
    with pytest.raises(BoardCapabilityError, match="refusing to guess"):
        LinuxHAL(
            BOARD,
            chip_glob=str(tmp_path / "gpiochip*"),
            gpiod=fake,
            needs={"i2c": ["i2c1"], "where": "agent"},
        )
    assert fake.requests == [] and kernel.calls == []
    hal = LinuxHAL(
        BOARD,
        chip_glob=str(tmp_path / "gpiochip*"),
        gpiod=fake,
        i2c_nodes={"i2c1": "/dev/i2c-1"},
        events=EventLog(),
        needs={"i2c": ["i2c1"], "where": "agent"},
    )
    assert fake.requests, "the preflight passed and the lines were requested"
    assert [c[0] for c in kernel.calls] == ["open"], "it opened the node and sent nothing"
    assert hal.events.of_type("i2c_read") == []
    with pytest.raises(BoardCapabilityError, match="declares no I2C bus 'i2c9'"):
        hal.preflight(i2c=["i2c9"], where="agent")


# --- replay: recorded reads, no bus ------------------------------------------------------


def test_replay_feeds_recorded_reads_and_never_opens_a_node(linux_hal, monkeypatch):
    def no_node(*args, **kwargs):
        raise AssertionError("a replay opened a bus")

    monkeypatch.setattr(linux, "open_mapped", no_node)
    monkeypatch.setenv(linux.I2C_ENV, "i2c1=/dev/i2c-1")  # the machine's wiring is not a replay's
    hal = linux_hal(replay=True)
    hal.script_i2c("i2c1", "ina219", 0x01, [10, ReadFault("ETIMEDOUT: Connection timed out"), 12])
    assert hal.i2c_read("i2c1", "ina219", 0x01) == 10
    with pytest.raises(PerceptionUnavailableError, match="ETIMEDOUT"):
        hal.i2c_read("i2c1", "ina219", 0x01)  # the recorded failure, with no retry to consume 12
    assert hal.i2c_read("i2c1", "ina219", 0x01) == 12
    with pytest.raises(PerceptionUnavailableError, match="no further reading"):
        hal.i2c_read("i2c1", "ina219", 0x01)
    with pytest.raises(PerceptionUnavailableError, match="nothing is scripted"):
        hal.i2c_read("i2c1", "ina219", 0x02)
    with pytest.raises(BoardCapabilityError, match="never touches a bus"):
        hal.i2c_scan("i2c1")
    assert [e.get("value", e.get("reason")) for e in hal.events.of_type("i2c_read")][:2] == [
        10,
        "ETIMEDOUT: Connection timed out",
    ]


# --- agents: [requires], the @action API, trace, replay ----------------------------------


@action(name="i2c_current", requires="i2c:i2c1/ina219", gate="i2c_gate")
def current() -> int:
    return i2c.read("i2c1", "ina219", register=0x04, width=2)


@action(name="i2c_other_register", requires="i2c:i2c1/ina219", gate="i2c_gate")
def other_register() -> int:
    return i2c.read("i2c1", "ina219", register=0x00, width=2)


@action(name="i2c_unlisted", requires="i2c:i2c1/ina219", gate="i2c_gate")
def unlisted() -> int:
    return i2c.read("i2c1", 0x48)


def _gate():
    return resolve_gate_document(
        {
            "schema": "neuroedge.gate/v1",
            "name": "i2c_gate",
            "version": "1.0.0",
            "evaluate": {"ok": {"type": "bool", "instructions": "Precondition holds"}},
            "allow_when": {"ok": True},
            "on_block": {"action": "deny"},
            "budget": {"p95_latency_ms": 100},
        }
    )


def conversation(hal, events):
    engine = ActionContractEngine(events=events)
    engine.register("i2c_gate", _gate())
    return Conversation(engine=engine, hal=hal, facts={"ok": True})


async def test_an_action_reads_i2c_through_the_hal_of_its_conversation():
    events = EventLog()
    hal = SimHAL(SIM, events=events)
    hal.set_i2c("i2c1", "ina219", 0x04, 0x0258, width=2)
    result = await conversation(hal, events).do(current)
    assert result.value == 0x0258
    (read,) = events.of_type("i2c_read")
    assert read["register"] == 4 and read["value"] == 0x0258
    validate_trace(events.to_trace())
    assert hal.pins == {}, "reading moves no pin and spends no token on one"


async def test_an_action_cannot_read_what_the_board_does_not_allow():
    events = EventLog()
    hal = SimHAL(SIM, events=events)
    hal.set_i2c("i2c1", "ina219", 0x04, 1, width=2)
    c = conversation(hal, events)
    with pytest.raises(BoardCapabilityError, match="readable_registers"):
        await c.do(other_register)
    with pytest.raises(BoardCapabilityError, match="allow-list"):
        await c.do(unlisted)
    assert events.of_type("i2c_read") == []


async def test_a_failed_read_in_an_action_is_perception_unavailable():
    events = EventLog()
    hal = SimHAL(SIM, events=events)  # nothing scripted: the device is "missing"
    with pytest.raises(PerceptionUnavailableError):
        await conversation(hal, events).do(current)
    assert "reason" in events.of_type("i2c_read")[0]


def test_i2c_read_outside_an_action_is_refused():
    with pytest.raises(ActionContractViolation, match="no HAL is active"):
        i2c.read("i2c1", "ina219", 0x01)


@pytest.mark.parametrize("target", ["sim", "linux"])
async def test_a_recorded_session_replays_its_reads_on_either_target(tmp_path, target):
    from neuroedge.testing import TraceRecorder
    from neuroedge.testing.player import _script_i2c

    recorder = TraceRecorder()
    hal = SimHAL(SIM, events=recorder)
    hal.set_i2c("i2c1", "ina219", 0x04, 0x0258, width=2)
    c = conversation(hal, recorder)
    assert (await c.do(current)).value == 0x0258
    hal.script_i2c("i2c1", "ina219", 0x04, [ReadFault("EIO: Input/output error")], width=2)
    with pytest.raises(PerceptionUnavailableError):
        await c.do(current)
    trace = recorder.to_trace()
    kinds = [
        e["data"].get("value", e["data"].get("reason"))
        for e in trace["events"]
        if e["type"] == "i2c_read"
    ]
    assert kinds == [0x0258, "EIO: Input/output error"]

    # The reads are fed back from the trace, never taken from a bus.
    events = EventLog()
    if target == "sim":
        hal2 = SimHAL(SIM, events=events)
    else:
        chip = tmp_path / "gpiochip0"
        chip.write_text("")
        hal2 = LinuxHAL(
            BOARD,
            chip_glob=str(tmp_path / "gpiochip*"),
            gpiod=FakeGpiod({str(chip): LINES}),
            events=events,
            replay=True,
        )
    _script_i2c(hal2, trace)
    c2 = conversation(hal2, events)
    assert (await c2.do(current)).value == 0x0258
    with pytest.raises(PerceptionUnavailableError, match="EIO: Input/output error"):
        await c2.do(current)
    assert events.of_type("i2c_read") == recorder_reads(trace)


def recorder_reads(trace):
    return [e["data"] for e in trace["events"] if e["type"] == "i2c_read"]


def test_a_trace_that_reads_i2c_cannot_replay_on_a_hal_that_cannot_be_fed():
    from neuroedge.errors import ReplayError
    from neuroedge.testing.player import _script_i2c

    trace = {
        "events": [
            {
                "type": "i2c_read",
                "data": {"bus": "i2c1", "device": "ina219", "address": 64, "value": 1},
            }
        ]
    }
    with pytest.raises(ReplayError, match="cannot be fed"):
        _script_i2c(HardwareAbstractionLayer(), trace)


# [requires]: a precise per-bus/device check, never "the board has i2c, so anything goes"


def _manifest(tmp_path, requires, actions=""):
    path = tmp_path / "agent.toml"
    path.write_text(
        f'[agent]\nname = "i2c-agent"\nversion = "0.0.1"\n\n[requires]\n{requires}\n\n'
        '[gates]\ni2c_gate = "neuroedge://gates/unlock_door@1.2.0"\n',
        encoding="utf-8",
    )
    return load_agent_manifest(path)


def test_requires_names_i2c_devices_the_board_allow_lists(tmp_path):
    manifest = _manifest(tmp_path, '"i2c" = { devices = ["i2c1/ina219", "i2c1/ads7828"] }')
    assert check_capabilities(manifest, BOARD) == []
    assert check_capabilities(manifest, SIM) == []


@pytest.mark.parametrize(
    "devices",
    [
        '["i2c1/lm75"]',  # a device the board does not list
        '["i2c0/ina219"]',  # a bus the board does not declare
        '["ina219"]',  # not bus/device
        '"i2c1/ina219"',  # not a list
        "[1]",
    ],
)
def test_an_i2c_device_the_board_does_not_declare_is_a_build_error(tmp_path, devices):
    manifest = _manifest(tmp_path, f'"i2c" = {{ devices = {devices} }}')
    (problem,) = check_capabilities(manifest, BOARD)
    assert isinstance(problem, BoardCapabilityError)
    assert "i2c" in problem.where and "linux-rpi5" in problem.why


def test_a_board_without_i2c_cannot_satisfy_requires_i2c(tmp_path):
    manifest = _manifest(tmp_path, '"i2c" = { devices = ["i2c1/ina219"] }')
    (problem,) = check_capabilities(manifest, load_board_by_id("sim-default"))
    assert "i2c" in problem.where and "declare the i2c primitive" in problem.how


def test_an_action_may_require_only_i2c_devices_the_manifest_declares(tmp_path):
    manifest = _manifest(tmp_path, '"i2c" = { devices = ["i2c1/ads7828"] }')
    problems = check_actions(manifest, [current.__neuroedge_action__])
    assert any(isinstance(p, AgentManifestError) and "i2c:i2c1/ina219" in p.where for p in problems)
    declared = _manifest(tmp_path, '"i2c" = { devices = ["i2c1/ina219"] }')
    assert check_actions(declared, [current.__neuroedge_action__]) == []


def test_an_unknown_extension_in_requires_is_still_refused(tmp_path):
    with pytest.raises(AgentManifestError, match="not HAL primitives"):
        _manifest(tmp_path, '"i2d" = {}')
