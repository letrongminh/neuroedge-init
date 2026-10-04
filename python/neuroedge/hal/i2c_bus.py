"""
Read-only I2C (TSK-I2a-03, RFC-0007 §3b): the policy every target shares, and the
`/dev/i2c-N` transport of `linux`.

"Read-only" means the API has **no data-write path**. The one write a read makes is
the register pointer, and only to a register in the `readable_registers` of a device in
the board's allow-list, immediately followed by a repeated-start read — which is what
SMBus *read byte/word data* is. A device with no `readable_registers` is receive-byte
only. An address outside the allow-list is never read: it is only *reported*, by a bus
scan made of read-byte probes (never quick-write, which some chips take as a command).

The layers, from the agent down:

* `I2CReader` — the policy. It checks the bus, the device and the register against the
  board **before any transaction**, runs the transaction through a transport with at most
  one retry, records `i2c_read`, and turns a read that still fails into
  `PerceptionUnavailableError` (NE5001).
* a transport (`I2CTransport`) — `receive_byte` and `read_register` and nothing else: a
  transport has no method that sends data, so no caller can. `LinuxI2CBus` talks to the
  kernel's i2c-dev with the `I2C_SMBUS` ioctl (stdlib `fcntl` and `ctypes`, no new
  dependency); `ScriptedI2C` replays values and never touches a bus (`sim`, replay).

The value of a 16-bit register is returned in wire order, first byte on the bus as the
high byte (an LM75 temperature reads 0x1900 for 25 °C), not in SMBus word order.
"""

from __future__ import annotations

import ctypes
import errno
import fcntl
import os
import threading
from collections import deque
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from ..errors import BoardCapabilityError, PerceptionUnavailableError
from .board import BoardProfile

__all__ = [
    "I2CProbe",
    "I2CReader",
    "I2CTransport",
    "LinuxI2CBus",
    "ReadFault",
    "ScriptedI2C",
    "parse_buses",
]

# 7-bit addresses a scan probes (the same range `board.v1` accepts for a device).
SCAN_FIRST, SCAN_LAST = 0x03, 0x77
# At most one retry of a NACK or a timeout (RFC-0007 §3b, TSK-N3-02).
RETRIES = 1
# errno of a probe that found nothing at the address: not a fault of the bus.
EREMOTEIO = getattr(errno, "EREMOTEIO", 121)  # Linux's; the module also imports on macOS
ABSENT = (errno.ENXIO, EREMOTEIO, errno.ENODEV)

# <linux/i2c-dev.h>, <linux/i2c.h>: only the read half of SMBus is ever issued.
I2C_SLAVE_FORCE = 0x0706  # the address even when a kernel driver (hwmon) holds it
I2C_SMBUS = 0x0720
I2C_SMBUS_READ = 1
I2C_SMBUS_BYTE = 1  # receive byte
I2C_SMBUS_BYTE_DATA = 2  # write the register, repeated start, read a byte
I2C_SMBUS_WORD_DATA = 3  # the same, read two bytes


class _SmbusData(ctypes.Union):
    _fields_ = [("byte", ctypes.c_uint8), ("word", ctypes.c_uint16), ("block", ctypes.c_uint8 * 34)]


class _SmbusIoctl(ctypes.Structure):
    _fields_ = [
        ("read_write", ctypes.c_uint8),
        ("command", ctypes.c_uint8),
        ("size", ctypes.c_uint32),
        ("data", ctypes.POINTER(_SmbusData)),
    ]


class I2CTransport(Protocol):
    """What the policy asks of a bus. There is deliberately no way to send data."""

    def receive_byte(self, address: int) -> int: ...

    def read_register(self, address: int, register: int, width: int) -> int: ...

    def check(self) -> None:
        """Fail now if the bus cannot be used; carries no transaction."""

    def close(self) -> None: ...


class LinuxI2CBus:
    """
    One `/dev/i2c-N`, read through the `I2C_SMBUS` ioctl. Every request is built here
    with `I2C_SMBUS_READ` and one of three read sizes; the direction is not a parameter.
    The address is forced (`I2C_SLAVE_FORCE`): a chip the kernel already drives through
    hwmon (an `ads7828`, an `lm75`) would otherwise answer EBUSY. Errors are `OSError`s
    with the kernel's errno (ENXIO / EREMOTEIO for a NACK, ETIMEDOUT, EIO).
    """

    def __init__(self, path: str) -> None:
        self.path = path
        self._fd: int | None = None
        self._address: int | None = None
        self._lock = threading.Lock()

    def check(self) -> None:
        with self._lock:
            self._descriptor()

    def _descriptor(self) -> int:
        if self._fd is None:
            self._fd = os.open(self.path, os.O_RDWR | os.O_CLOEXEC)
            self._address = None
        return self._fd

    def _read(self, address: int, command: int, size: int) -> _SmbusData:
        data = _SmbusData()
        request = _SmbusIoctl(I2C_SMBUS_READ, command, size, ctypes.pointer(data))
        with self._lock:
            fd = self._descriptor()
            try:
                if self._address != address:
                    fcntl.ioctl(fd, I2C_SLAVE_FORCE, address)
                    self._address = address
                fcntl.ioctl(fd, I2C_SMBUS, request)
            except OSError:
                self._address = None  # the next transaction sets it again
                raise
        return data

    def receive_byte(self, address: int) -> int:
        return self._read(address, 0, I2C_SMBUS_BYTE).byte

    def read_register(self, address: int, register: int, width: int) -> int:
        if width == 1:
            return self._read(address, register, I2C_SMBUS_BYTE_DATA).byte
        word = self._read(address, register, I2C_SMBUS_WORD_DATA).word
        return ((word & 0xFF) << 8) | (word >> 8)  # SMBus puts the first byte low

    def close(self) -> None:
        with self._lock:
            fd, self._fd, self._address = self._fd, None, None
        if fd is not None:
            os.close(fd)


class ReadFault(OSError):
    """A recorded failure, fed back by replay; `reason` is what the trace holds, verbatim."""

    def __init__(self, reason: str) -> None:
        super().__init__(errno.EIO, reason)
        self.reason = reason


@dataclass(frozen=True)
class _Fault:
    reason: str


class ScriptedI2C:
    """
    Values in place of a bus: `set` is a scenario's constant (`sim`), `script` the
    readings of a recorded session in order (replay). A read nothing was scripted for
    fails — it is never invented — so an agent that reads more than the trace holds is
    told so by NE5001, not handed a number.
    """

    def __init__(self) -> None:
        self._fixed: dict[tuple[str, int, int | None], int] = {}
        self._queues: dict[tuple[str, int, int | None], deque[int | _Fault]] = {}

    def set(self, bus: str, address: int, register: int | None, value: int) -> None:
        self._fixed[bus, address, register] = value

    def script(
        self, bus: str, address: int, register: int | None, values: Iterable[int | ReadFault]
    ) -> None:
        self._queues[bus, address, register] = deque(
            _Fault(v.reason) if isinstance(v, ReadFault) else v for v in values
        )

    def has_bus(self, bus: str) -> bool:
        return any(key[0] == bus for key in (*self._fixed, *self._queues))

    def transport(self, bus: str) -> I2CTransport:
        return _ScriptedBus(self, bus)

    def _next(self, bus: str, address: int, register: int | None) -> int:
        key = (bus, address, register)
        where = f"{bus} {address:#04x}" + ("" if register is None else f" register {register:#04x}")
        if key in self._queues:
            if not self._queues[key]:
                raise ReadFault(f"the trace holds no further reading of {where}")
            value = self._queues[key].popleft()
            if isinstance(value, _Fault):
                raise ReadFault(value.reason)
            return value
        if key in self._fixed:
            return self._fixed[key]
        raise ReadFault(f"nothing is scripted for {where}")


class _ScriptedBus:
    def __init__(self, script: ScriptedI2C, bus: str) -> None:
        self._script, self._bus = script, bus

    def receive_byte(self, address: int) -> int:
        return self._script._next(self._bus, address, None)

    def read_register(self, address: int, register: int, width: int) -> int:
        return self._script._next(self._bus, address, register)

    def check(self) -> None:
        return None

    def close(self) -> None:
        return None


@dataclass(frozen=True)
class I2CProbe:
    """One address that answered a scan; `device` is its allow-list name, None if outside it."""

    address: int
    device: str | None


def parse_buses(text: str, where: str) -> dict[str, str]:
    """`i2c1=/dev/i2c-1;i2c0=/dev/i2c-3` → a mapping from board bus id to device node."""
    buses: dict[str, str] = {}
    for item in filter(None, (part.strip() for part in text.split(";"))):
        bus, sep, node = item.partition("=")
        if not sep or not bus.strip() or not node.strip():
            raise BoardCapabilityError(
                where=where,
                why=f"{item!r} is not bus=node",
                how="separate entries with ';', e.g. i2c1=/dev/i2c-1",
            )
        buses[bus.strip()] = node.strip()
    return buses


def _reason(exc: OSError) -> str:
    if isinstance(exc, ReadFault):
        return exc.reason
    name = errno.errorcode.get(exc.errno, "") if exc.errno else ""
    text = exc.strerror or str(exc)
    return f"{name}: {text}" if name else text


class I2CReader:
    """
    The read-only policy over a board's I2C declaration (see the module docstring).
    `open_bus(bus, where)` gives the transport of a declared bus, or refuses with a
    three-part error; the reader keeps and closes what it opened. `emit` records events
    (a HAL passes a function that looks `events` up at call time, since a player swaps it).
    """

    def __init__(
        self,
        board: BoardProfile,
        open_bus: Callable[[str, str], I2CTransport],
        emit: Callable[[str, dict[str, Any]], None],
        *,
        retries: int = RETRIES,
    ) -> None:
        self.board = board
        self._open_bus = open_bus
        self._emit = emit
        self._retries = retries
        self._open: dict[str, I2CTransport] = {}

    # -- the allow-list ------------------------------------------------------------
    def _bus(self, bus: str, where: str) -> dict[str, Any]:
        for declared in self.board.i2c_buses:
            if declared["id"] == bus:
                return declared
        ids = [declared["id"] for declared in self.board.i2c_buses]
        raise BoardCapabilityError(
            where=where,
            why=f"board {self.board.id!r} declares no I2C bus {bus!r}; it declares {ids}",
            how=f"add the bus to [capabilities.i2c] in {self.board.source}, or use a declared one",
        )

    def device(self, bus: str, device: str | int, where: str) -> dict[str, Any]:
        """The allow-list entry of `device` (a name, or an address) on `bus`, or a refusal."""
        devices = self._bus(bus, where)["devices"]
        if isinstance(device, bool) or not isinstance(device, str | int):
            raise BoardCapabilityError(
                where=where,
                why=f"an I2C device is named by its board name or its address, not {device!r}",
                how=f"use one of {[d['name'] for d in devices]}",
            )
        key = "name" if isinstance(device, str) else "address"
        for declared in devices:
            if declared[key] == device:
                return declared
        shown = repr(device) if isinstance(device, str) else f"address {device:#04x}"
        raise BoardCapabilityError(
            where=where,
            why=(
                f"{shown} is not in the I2C allow-list of bus {bus!r} on board "
                f"{self.board.id!r} ({[d['name'] for d in devices]}); an address outside "
                "it is reported by a scan and never read (RFC-0007 §3b)"
            ),
            how=f"declare the device under [capabilities.i2c] in {self.board.source}, if it is meant",
        )

    def resolve(
        self,
        bus: str,
        device: str | int,
        register: int | None,
        width: int,
        where: str,
    ) -> dict[str, Any]:
        """Check one read against the board and return the device. No transaction."""
        declared = self.device(bus, device, where)
        if isinstance(width, bool) or width not in (1, 2):
            raise BoardCapabilityError(
                where=where,
                why=f"width {width!r} bytes: a read is one byte or one 16-bit register",
                how="use width=1 or width=2",
            )
        if register is None:
            if width != 1:
                raise BoardCapabilityError(
                    where=where,
                    why="a receive-byte read (no register) returns one byte",
                    how="name a readable register for a 16-bit read, or use width=1",
                )
            return declared
        readable = declared.get("readable_registers", ())
        if isinstance(register, bool) or not isinstance(register, int) or register not in readable:
            what = (
                f"register {register:#04x}"
                if isinstance(register, int) and not isinstance(register, bool)
                else f"register {register!r}"
            )
            raise BoardCapabilityError(
                where=where,
                why=(
                    f"{what} is not in the readable_registers of {declared['name']!r} on "
                    f"bus {bus!r} ({[hex(r) for r in readable] or 'none: receive-byte only'}); "
                    "only a declared register may be pointed at, because some chips take any "
                    "write as a command (RFC-0007 §3b)"
                ),
                how=f"declare it in readable_registers of the device in {self.board.source}",
            )
        return declared

    # -- transports ----------------------------------------------------------------
    def _transport(self, bus: str, where: str) -> I2CTransport:
        if bus not in self._open:
            self._open[bus] = self._open_bus(bus, where)
        return self._open[bus]

    def check_bus(self, bus: str, where: str) -> None:
        """Fail now if the bus cannot be used (declared, mapped, openable): no transaction."""
        self._bus(bus, where)
        transport = self._transport(bus, where)
        try:
            transport.check()
        except OSError as exc:
            node = getattr(transport, "path", None)
            named = f" ({node})" if node else ""
            raise BoardCapabilityError(
                where=where,
                why=f"cannot open the device node{named} of I2C bus {bus!r}: {_reason(exc)}",
                how="check the node exists and the user may read and write it (group `i2c`)",
            ) from exc

    def close(self) -> None:
        errors: list[BaseException] = []
        opened, self._open = list(self._open.values()), {}
        for transport in opened:
            try:
                transport.close()
            except OSError as exc:
                errors.append(exc)
        if errors:
            raise errors[0]

    # -- reads ---------------------------------------------------------------------
    def read(
        self,
        bus: str,
        device: str | int,
        register: int | None = None,
        *,
        width: int = 1,
        called_from: str = "<unknown>",
    ) -> int:
        """
        One read of an allow-listed device: the receive byte, or a declared register (a
        pointer write then a repeated-start read, one or two bytes). Refused — with no
        transaction — outside the allow-list. A NACK, timeout or garbage is retried once
        and then recorded as `i2c_read` with a `reason` and raised as NE5001.
        """
        where = f"{called_from} -> i2c.read {bus!r} {device!r}" + (
            "" if register is None else f" register {register!r}"
        )
        declared = self.resolve(bus, device, register, width, where)
        transport = self._transport(bus, where)
        data: dict[str, Any] = {
            "bus": bus,
            "device": declared["name"],
            "address": declared["address"],
        }
        if register is not None:
            data["register"] = register
        reason = "no attempt was made"
        for _ in range(1 + self._retries):
            try:
                if register is None:
                    value = transport.receive_byte(declared["address"])
                else:
                    value = transport.read_register(declared["address"], register, width)
            except ReadFault as exc:  # a recorded outcome, not a bus that may answer next time
                reason = exc.reason
                break
            except OSError as exc:
                reason = _reason(exc)
                continue
            if isinstance(value, int) and not isinstance(value, bool) and 0 <= value < 256**width:
                self._emit("i2c_read", {**data, "value": value})
                return value
            reason = f"the bus returned {value!r}, not a {width}-byte value"
        self._emit("i2c_read", {**data, "reason": reason})
        raise PerceptionUnavailableError(
            where=where,
            why=f"the read failed after {1 + self._retries} attempts: {reason}",
            how=(
                "the criterion that needed it is undecided and the gate BLOCKs; check the wiring, "
                "the pull-ups and the device's power (RFC-0007 §3e)"
            ),
        )

    def scan(self, bus: str, *, called_from: str = "<unknown>") -> list[I2CProbe]:
        """
        Every address that answers a read-byte probe, each tagged with its allow-list name
        or None. Only the probe is sent — never a quick-write, never a register pointer —
        and nothing outside the allow-list is read beyond it. A bus fault (not an absent
        device) is NE5001, not an empty list.
        """
        where = f"{called_from} -> i2c.scan {bus!r}"
        names = {d["address"]: d["name"] for d in self._bus(bus, where)["devices"]}
        transport = self._transport(bus, where)
        found: list[I2CProbe] = []
        for address in range(SCAN_FIRST, SCAN_LAST + 1):
            try:
                transport.receive_byte(address)
            except OSError as exc:
                if exc.errno in ABSENT:
                    continue
                raise PerceptionUnavailableError(
                    where=where,
                    why=f"the probe of {address:#04x} failed: {_reason(exc)}",
                    how="check the bus wiring and the device node; a scan never reports a broken bus as empty",
                ) from exc
            found.append(I2CProbe(address, names.get(address)))
        return found


def open_mapped(nodes: Mapping[str, str], board: BoardProfile, bus: str, where: str) -> LinuxI2CBus:
    """The transport of `bus` on the machine's device node, or a refusal to guess one."""
    node = nodes.get(bus)
    if node is None:
        raise BoardCapabilityError(
            where=where,
            why=(
                f"no device node is chosen for I2C bus {bus!r} of {board.id!r} on this machine; "
                "refusing to guess one (the adapter number changes across boots and boards)"
            ),
            how=(
                f"set NEUROEDGE_LINUX_I2C='{bus}=/dev/i2c-1' on the device, or pass "
                f"LinuxHAL(i2c_nodes={{'{bus}': '/dev/i2c-1'}})"
            ),
        )
    return LinuxI2CBus(node)
