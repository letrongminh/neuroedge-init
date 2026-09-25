"""
Trace lines from a device's UART (TSK-S4-09, FR-CI-01, FR-CLI-04).

The firmware writes each trace event as one line — `NE1 ` and one `trace.v1`
event as JSON — among its ordinary log lines, and frames every session:
`device_info` first, `trace_end {events: N}` last, then `NE_TRACE DONE` once it
has nothing more to say (docs/spec/simulation_coverage.md §4). This module keeps
the `NE1 ` lines, drops everything else, checks the framing, and rebuilds one
trace per session with `TraceRecorder`, which validates before it writes.

Nothing in the rebuilt events is the host's: every event is the device's line,
at the device's `offset_ms`. The host adds only `metadata` — the session id
(after the device's `boot_id`), the time it read `device_info`, and the fields
`device_info` declares — so `device_id = "qemu"` says where the evidence came
from. A line that does not parse, a session without its `trace_end`, or a
`trace_end` that counts lines the host never saw is an error, never a shorter
trace read as the truth.

Three sources, one syntax (`--port`): a file (QEMU's `-serial file:uart.log`,
or a saved capture), `tcp://host:port` (QEMU's `-serial tcp::5555,server`), or
a serial device through pyserial (`neuroedge[serial]`).
"""

from __future__ import annotations

import json
import re
import socket
import time
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..errors import TraceValidationError
from .recorder import TraceRecorder

PREFIX = "NE1 "
LINE_MAX = 512  # bytes, prefix included (ne_trace.h NE_TRACE_LINE_MAX)
DONE = "NE_TRACE DONE"
EVENT_KEYS = frozenset({"offset_ms", "type", "data"})
DEVICE_INFO_KEYS = ("board_id", "agent_version", "device_id", "boot_id")
DEFAULT_BAUD = 921600  # neuroedge-prd.md Appendix D.2; ignored by USB-CDC
SPEC = "docs/spec/simulation_coverage.md §4"


def _malformed(where: str, why: str, how: str | None = None) -> TraceValidationError:
    return TraceValidationError(
        where=where,
        why=why,
        how=how or f"the firmware's trace lines must follow {SPEC}; fix the emitter or the capture",
    )


@dataclass
class DeviceSession:
    """One framed session, as the device wrote it."""

    source: str
    line: int  # where its device_info is
    info: dict[str, Any]
    received_utc: str
    events: list[dict[str, Any]] = field(default_factory=list)
    index: int = 0  # sessions before it with the same boot_id

    @property
    def replay_of(self) -> str | None:
        return self.info.get("replay_of")

    @property
    def session_id(self) -> str:
        return f"sess_{self.info['boot_id']}{self.index:02x}"

    def recorder(self, *, anonymize: bool = False) -> TraceRecorder:
        """The session as a `TraceRecorder`: the device's events, the host's metadata."""
        recorder = TraceRecorder(
            target="esp32s3",
            board_id=self.info["board_id"],
            agent_version=self.info["agent_version"],
            anonymize=anonymize,
            session_id=self.session_id,
        )
        recorder.metadata["timestamp_utc"] = self.received_utc
        recorder.metadata["device_id"] = self.info["device_id"]
        for event in self.events:
            recorder.append(event["offset_ms"], event["type"], event["data"])
        return recorder

    def trace(self) -> dict[str, Any]:
        return self.recorder().to_trace()


def parse_line(line: str, where: str) -> dict[str, Any] | None:
    """The event on an `NE1 ` line; None for any other line. A broken `NE1 ` line raises."""
    text = line.rstrip("\r\n")
    if not text.startswith(PREFIX):
        return None
    if len(text.encode("utf-8")) > LINE_MAX:
        raise _malformed(where, f"an NE1 line is longer than {LINE_MAX} bytes")
    try:
        event = json.loads(text[len(PREFIX) :])
    except json.JSONDecodeError as error:
        raise _malformed(
            where,
            f"the NE1 line is not JSON ({error.msg} at column {error.colno + len(PREFIX)})",
            "a line cut or garbled on the UART: capture again; if it repeats, fix the emitter",
        ) from None
    if not isinstance(event, dict) or set(event) != EVENT_KEYS:
        keys = sorted(event) if isinstance(event, dict) else type(event).__name__
        raise _malformed(
            where, f"an NE1 line holds one event {{offset_ms, type, data}}, not {keys}"
        )
    offset = event["offset_ms"]
    if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
        raise _malformed(where, f"offset_ms must be an integer >= 0, not {offset!r}")
    if not isinstance(event["type"], str) or not isinstance(event["data"], dict):
        raise _malformed(where, "type must be a string and data an object")
    return event


def _check_device_info(event: dict[str, Any], where: str) -> None:
    data = event["data"]
    missing = [key for key in DEVICE_INFO_KEYS if not isinstance(data.get(key), str)]
    if missing:
        raise _malformed(where, f"device_info lacks {', '.join(missing)}")
    if not re.fullmatch(r"[0-9a-fA-F]+", data["boot_id"]):
        raise _malformed(where, f"device_info.boot_id must be hex, not {data['boot_id']!r}")
    if event["offset_ms"] != 0:
        raise _malformed(where, "device_info opens a session at offset_ms 0")


def sessions_from_lines(lines: Iterable[str], source: str) -> list[DeviceSession]:
    """Every framed session in `lines`, in order. Any broken frame raises."""
    sessions: list[DeviceSession] = []
    current: DeviceSession | None = None
    seen: dict[str, int] = {}
    number = 0
    for number, line in enumerate(lines, start=1):
        where = f"{source}:{number}"
        event = parse_line(line, where)
        if event is None:
            continue
        kind = event["type"]
        if kind == "device_info":
            if current is not None:
                raise _malformed(
                    where,
                    f"a new session starts before the one at line {current.line} ended "
                    "(no trace_end): the device restarted mid-session",
                    "capture a boot that runs to NE_TRACE DONE, or cut the log before the restart",
                )
            _check_device_info(event, where)
            boot = event["data"]["boot_id"]
            current = DeviceSession(
                source=source,
                line=number,
                info=dict(event["data"]),
                received_utc=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                index=seen.get(boot, 0),
            )
            seen[boot] = current.index + 1
            current.events.append(event)
        elif current is None:
            raise _malformed(
                where, f"a {kind} line before any device_info: the capture began mid-session"
            )
        elif kind == "trace_end":
            announced = event["data"].get("events")
            if announced != len(current.events):
                raise _malformed(
                    where,
                    f"the device wrote {announced!r} line(s) for the session at line "
                    f"{current.line}, {len(current.events)} arrived",
                    "a line was lost on the UART or dropped by the device (longer than "
                    f"{LINE_MAX} bytes): capture again, or shorten what the event carries",
                )
            current.events.append(event)
            sessions.append(current)
            current = None
        else:
            current.events.append(event)
    if current is not None:
        raise _malformed(
            f"{source}:{current.line}",
            f"the session opened here has no trace_end (the capture ends at line {number})",
            "capture until NE_TRACE DONE, or give the device longer (--timeout)",
        )
    return sessions


# --- sources -------------------------------------------------------------------------------


def _until_done(lines: Iterable[str]) -> Iterator[str]:
    for line in lines:
        yield line
        if line.startswith(DONE):
            return


def _file_lines(path: Path) -> Iterator[str]:
    if not path.is_file():
        raise TraceValidationError(
            where=str(path),
            why="no such file, and not tcp://host:port or a serial device",
            how="pass QEMU's -serial file:… log, tcp://host:port, or the board's /dev/tty…",
        )
    with open(path, encoding="utf-8", errors="replace", newline="") as handle:
        yield from _until_done(handle)


def _tcp_lines(port: str, timeout_s: float) -> Iterator[str]:
    match = re.fullmatch(r"tcp://([^:/]+):(\d+)/?", port)
    if match is None:
        raise TraceValidationError(
            where=port, why="expected tcp://host:port", how="e.g. tcp://localhost:5555"
        )
    host, number = match.group(1), int(match.group(2))
    deadline = time.monotonic() + timeout_s
    try:
        sock = socket.create_connection((host, number), timeout=timeout_s)
    except OSError as error:
        raise TraceValidationError(
            where=port,
            why=f"cannot connect: {error}",
            how="start QEMU with -serial tcp::<port>,server (it waits for this reader), then retry",
        ) from None
    with sock, sock.makefile("r", encoding="utf-8", errors="replace", newline="") as stream:
        try:
            for line in _until_done(stream):
                yield line
                sock.settimeout(max(0.1, deadline - time.monotonic()))
        except TimeoutError:
            return  # the frame check reports what the capture lacks


def _serial_lines(port: str, baud: int, timeout_s: float) -> Iterator[str]:
    try:
        import serial  # pyserial, extra `neuroedge[serial]`
    except ImportError:
        raise TraceValidationError(
            where=port,
            why="reading a serial device needs pyserial, which is not installed",
            how="pip install 'neuroedge[serial]' — or read QEMU's log file or tcp:// instead",
        ) from None
    try:
        device = serial.serial_for_url(port, baudrate=baud, timeout=0.2)
    except (serial.SerialException, ValueError) as error:
        raise TraceValidationError(
            where=port,
            why=f"cannot open the serial device: {error}",
            how="check the port name (ls /dev/tty*), that nothing else holds it, and the cable",
        ) from None
    deadline = time.monotonic() + timeout_s
    with device:
        pending = b""
        while time.monotonic() < deadline:
            pending += device.readline()
            if not pending.endswith(b"\n"):
                continue
            line = pending.decode("utf-8", errors="replace")
            pending = b""
            yield line
            if line.startswith(DONE):
                return


# A serial device or a pyserial URL (loop://, socket://, rfc2217://…); anything else is a file.
SERIAL = re.compile(r"^(/dev/|COM\d+$|\\\\\.\\|[a-z][a-z0-9+]*://)", re.IGNORECASE)


def read_lines(port: str, *, baud: int = DEFAULT_BAUD, timeout_s: float = 30.0) -> Iterator[str]:
    """The lines a device wrote, up to `NE_TRACE DONE`, the end of a file, or `timeout_s`."""
    if port.startswith("tcp://"):
        return _tcp_lines(port, timeout_s)
    if port.startswith("file:"):
        return _file_lines(Path(port[len("file:") :]))
    if SERIAL.match(port):
        return _serial_lines(port, baud, timeout_s)
    return _file_lines(Path(port))


def read_sessions(
    port: str, *, baud: int = DEFAULT_BAUD, timeout_s: float = 30.0
) -> list[DeviceSession]:
    """Every framed session the device at `port` writes. None at all is an error."""
    sessions = sessions_from_lines(read_lines(port, baud=baud, timeout_s=timeout_s), port)
    if not sessions:
        raise TraceValidationError(
            where=port,
            why="no NE1 trace session in what the device wrote",
            how=(
                "flash a firmware with the trace sink (TSK-S4-09) and capture from boot; "
                "on QEMU the log is build/uart.log"
            ),
        )
    return sessions
