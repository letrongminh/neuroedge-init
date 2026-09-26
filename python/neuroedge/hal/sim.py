"""
HAL backend for target `sim` (TSK-S2-01, FR-TGT-01).

The simulator has no hardware, so each primitive is a recorded state change and
a trace event. Its capabilities come from `boards/sim-default.toml`, which
mirrors the reference board rather than exceeding it (CHANGELOG §3.3 #7).

* `digital_out` — the only way a pin changes; records `actuator_command` and
  returns a cancellable `PendingCommand` (RB-3: barge-in must be able to abort a
  pending pulse, so the handle exists on every target from day one). With
  `delay_ms` the command is *scheduled*: authorised now, delivered — pin recorded,
  `actuator_command` — only when `run_due()` reaches its time on the clock given
  to `enable_scheduling()`. Until then it is a pending command in the sense of
  docs/spec/voice_fsm.md §5.1, and barge-in cancels it (TSK-S3-11).
* `audio_in` — Q-15: typed text by default, queued with `type_text()`.
* `audio_out` — records `tts_stream_start`.
* `sensor_read` — values scripted with `set_sensor()` (or a sequence with
  `script_sensor()`, which replay uses); records `sensor_read`. An unscripted
  sensor raises instead of inventing a reading.
* `display` — a virtual frame (text, or raw RGB565 / RGB888 pixels) checked
  against the declared resolution; records `display_frame` with its digest
  (docs/spec/simulation_coverage.md §3).
"""

from __future__ import annotations

import hashlib
import math
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from ..errors import ActionContractViolation, BoardCapabilityError
from . import Authorizer, HardwareAbstractionLayer, PinAssertion, _require_signature
from .board import BoardProfile, load_board_by_id

ABORTED_BY_BARGE_IN = "ACTUATOR_ABORTED_BY_BARGE_IN"
# The @action that scheduled the command raised: its verdict never completed (review of TSK-S3-11).
ABORTED_BY_ACTION_ERROR = "ACTUATOR_ABORTED_BY_ACTION_ERROR"


def reading_data(
    sensor: str, value: Any, unit: str | None = None, use: str | None = None
) -> dict[str, Any]:
    """
    `sensor_read` / `sensor_set` data, the same on every target. JSON has no NaN or
    inf: such a reading is written as "nan", "inf" or "-inf" with `non_finite: true`,
    and `reading_value` gives replay the float back.
    """
    data: dict[str, Any] = {"sensor": sensor, "value": value}
    if isinstance(value, float) and not math.isfinite(value):
        data["value"], data["non_finite"] = repr(value), True
    if unit is not None:
        data["unit"] = unit
    if use is not None:
        data["use"] = use
    return data


def reading_value(data: Mapping[str, Any]) -> Any:
    """The reading a `sensor_read` event recorded (the inverse of `reading_data`)."""
    value = data.get("value")
    return float(value) if data.get("non_finite") else value


class EventSink(Protocol):
    def emit(self, type: str, data: dict[str, Any]) -> None: ...


class _NullSink:
    def emit(self, type: str, data: dict[str, Any]) -> None:
        return None


@dataclass
class PendingCommand:
    """A physical command in flight. `cancel()` aborts it and records why."""

    pin: str
    operation: str
    duration_ms: int
    events: EventSink = field(repr=False)
    cancelled: bool = False
    # What the target must do to stop the command physically (LinuxHAL drops the line).
    on_cancel: Callable[[], None] | None = field(default=None, repr=False)
    # False while a scheduled command waits for its time (voice_fsm.md §5.1). A
    # delivered command is no longer pending: barge-in never cancels it (§5.3).
    delivered: bool = True
    deliver_at_ms: float | None = None
    # The verdict token that authorised the command, so barge-in can close it (§5.2 step 2).
    token: Any = field(default=None, repr=False)

    def cancel(self, reason: str = ABORTED_BY_BARGE_IN) -> None:
        if self.cancelled:
            return
        self.cancelled = True
        if self.on_cancel is not None:
            self.on_cancel()
        self.events.emit("actuator_aborted", {"pin": self.pin, "reason": reason})


BYTES_PER_PIXEL = {"rgb565": 2, "rgb888": 3}


@dataclass(frozen=True)
class Frame:
    """One frame shown on `display`: text, or raw pixels in a declared format."""

    width: int
    height: int
    format: str
    data: bytes

    @classmethod
    def make(cls, frame: str | bytes, width: int, height: int, fmt: str | None, where: str):
        if isinstance(frame, str):
            if fmt not in (None, "text"):
                raise BoardCapabilityError(
                    where=where,
                    why=f"a text frame cannot have format {fmt!r}",
                    how="pass bytes for pixel formats, or omit format for text",
                )
            return cls(width, height, "text", frame.encode("utf-8"))
        fmt = fmt or "rgb565"
        if fmt not in BYTES_PER_PIXEL:
            raise BoardCapabilityError(
                where=where,
                why=f"unknown pixel format {fmt!r}",
                how=f"use one of {sorted(BYTES_PER_PIXEL)}, or pass a str for a text frame",
            )
        expected = width * height * BYTES_PER_PIXEL[fmt]
        if len(frame) != expected:
            raise BoardCapabilityError(
                where=where,
                why=f"{fmt} frame of {width}x{height} needs {expected} bytes, got {len(frame)}",
                how="pass width and height matching the pixel buffer",
            )
        return cls(width, height, fmt, bytes(frame))

    @property
    def sha256(self) -> str:
        return "sha256:" + hashlib.sha256(self.data).hexdigest()

    @property
    def text(self) -> str | None:
        return self.data.decode("utf-8") if self.format == "text" else None

    def event_data(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "width": self.width,
            "height": self.height,
            "format": self.format,
            "sha256": self.sha256,
        }
        if self.format == "text":
            data["text"] = self.text  # hashed by the recorder under --anonymize
        return data

    def rgb888(self) -> bytes:
        """Pixels as RGB888, for export; text frames have none."""
        if self.format == "rgb888":
            return self.data
        if self.format != "rgb565":
            raise ValueError("a text frame has no pixels")
        # Big-endian, as SPI panels take it: high byte RRRRRGGG, low byte GGGBBBBB.
        # Each channel widens by repeating its top bits; done per byte with lookup
        # tables, since a Python loop per pixel takes seconds on a full panel.
        high, low = self.data[0::2], self.data[1::2]
        out = bytearray(len(high) * 3)
        out[0::3] = high.translate(_R565)
        out[1::3] = _bitor(high.translate(_G565_HIGH), low.translate(_G565_LOW))
        out[2::3] = low.translate(_B565)
        return bytes(out)


def _bitor(a: bytes, b: bytes) -> bytes:
    """Byte-wise OR of two equal-length byte strings (bits that never overlap)."""
    return (int.from_bytes(a, "big") | int.from_bytes(b, "big")).to_bytes(len(a), "big")


_R565 = bytes(((h >> 3) << 3) | ((h >> 3) >> 2) for h in range(256))
# g6 = (h & 7) << 3 | l >> 5 widens to g6 << 2 | g6 >> 4, and g6 >> 4 == (h & 7) >> 1.
_G565_HIGH = bytes(((h & 7) << 5) | ((h & 7) >> 1) for h in range(256))
_G565_LOW = bytes((low >> 5) << 2 for low in range(256))
_B565 = bytes(((low & 0x1F) << 3) | ((low & 0x1F) >> 2) for low in range(256))


def make_frame(
    board: BoardProfile,
    frame: str | bytes,
    width: int | None,
    height: int | None,
    format: str | None,
    called_from: str,
) -> Frame:
    """
    Check a frame against the board's declared display and build it. Every target
    that draws goes through here (`sim`, `linux`), so a call is accepted or refused,
    and recorded with the same `display_frame` data, alike on each.
    """
    if not board.supports("display"):
        raise BoardCapabilityError(
            where=f"{called_from} -> display",
            why=f"board {board.id!r} does not declare the 'display' primitive",
            how=f"add it to {board.source}, or choose a board that provides it",
        )
    declared = board.capability("display")
    for axis, value in (("width", width), ("height", height)):
        if value is not None and value > declared[axis]:
            raise BoardCapabilityError(
                where=f"{called_from} -> display",
                why=f"frame {axis} {value} exceeds the board's {declared[axis]}",
                how=f"render at most {declared['width']}x{declared['height']}",
            )
    return Frame.make(
        frame,
        width if width is not None else declared["width"],
        height if height is not None else declared["height"],
        format,
        where=f"{called_from} -> display",
    )


class SimHAL(HardwareAbstractionLayer):
    def __init__(
        self,
        board: BoardProfile | None = None,
        *,
        events: EventSink | None = None,
        sensors: Mapping[str, Any] | None = None,
        authorize: Authorizer = _require_signature,
    ) -> None:
        board = board if board is not None else load_board_by_id("sim-default")
        if board.target != "sim":
            raise BoardCapabilityError(
                where=f"SimHAL(board={board.id!r})",
                why=f"board {board.id!r} targets {board.target!r}, not 'sim'",
                how="use a sim board such as sim-default, or the HAL for that target",
            )
        super().__init__(target="sim", board=board, authorize=authorize)
        self.events: EventSink = events if events is not None else _NullSink()
        self._sensors: dict[str, Any] = dict(sensors or {})
        self._units: dict[str, str] = {}
        self._scripted: dict[str, deque[Any]] = {}
        self._typed: deque[str] = deque()
        self.frame: str | bytes | None = None
        self.frames: list[Frame] = []
        self.spoken: list[str] = []
        # Scheduled commands (voice_fsm.md §5.1); None = scheduling refused.
        self._clock: Callable[[], float] | None = None
        self._scheduled: list[PendingCommand] = []

    def _require(self, primitive: str, called_from: str) -> dict[str, Any]:
        if not self.board.supports(primitive):
            raise BoardCapabilityError(
                where=f"{called_from} -> {primitive}",
                why=f"board {self.board.id!r} does not declare the {primitive!r} primitive",
                how=f"add it to {self.board.source}, or choose a board that provides it",
            )
        return self.board.capability(primitive)

    # -- digital.out -----------------------------------------------------------
    # Scheduled commands are what barge-in cancels (voice_fsm.md §5.2), so they
    # exist only where a driver delivers them on a clock: `perception.VoiceSession`.
    schedules_commands = True

    def enable_scheduling(self, clock: Callable[[], float]) -> None:
        """Accept `delay_ms` commands, delivered by `run_due()` on this clock."""
        self._clock = clock

    def digital_out(
        self,
        pin: str,
        operation: str,
        duration_ms: int = 0,
        signature: Any = "",
        called_from: str = "<unknown>",
        delay_ms: int = 0,
    ) -> PendingCommand:
        if operation not in ("pulse", "on", "off"):
            raise BoardCapabilityError(
                where=f"{called_from} -> digital.out {pin!r}",
                why=f"unknown operation {operation!r}",
                how="use one of 'pulse', 'on', 'off'",
            )
        if delay_ms:
            return self._schedule(pin, operation, duration_ms, signature, called_from, delay_ms)
        super().digital_out(pin, operation, duration_ms, signature, called_from)
        self.events.emit(
            "actuator_command", {"pin": pin, "operation": operation, "duration_ms": duration_ms}
        )
        return PendingCommand(pin, operation, duration_ms, self.events, token=signature)

    def _schedule(
        self,
        pin: str,
        operation: str,
        duration_ms: int,
        signature: Any,
        called_from: str,
        delay_ms: int,
    ) -> PendingCommand:
        where = f"{called_from} -> digital.out {pin!r}"
        if self._clock is None:
            raise BoardCapabilityError(
                where=where,
                why="a scheduled command needs a driver that delivers it on a clock, and none runs",
                how="run the agent in a perception.VoiceSession, or drive the pin without after_ms",
            )
        if delay_ms < 0:
            raise BoardCapabilityError(
                where=where, why=f"negative delay {delay_ms} ms", how="use after_ms >= 0"
            )
        # Checked and authorised now — the verdict is spent when the gate allowed —
        # but the pin is recorded only on delivery, so a cancelled command never moved it.
        if self.board is not None:
            self.board.require_pin(pin, called_from=called_from)
        self.authorize(signature, pin, called_from)
        # A verdict is fresh for its TTL (actions/token.py); a command delivered after
        # that would move the pin on facts the gate never saw, so it is refused now.
        issued_at = getattr(signature, "issued_at_ms", None)
        ttl = getattr(signature, "ttl_ms", None)
        if issued_at is not None and ttl is not None:
            deliver_at = self._clock() + delay_ms
            if deliver_at - issued_at > ttl:
                raise ActionContractViolation(
                    where=where,
                    why=(
                        f"after_ms {delay_ms} delivers the command {deliver_at - issued_at:g} ms "
                        f"after the verdict, past its TTL of {ttl:g} ms"
                    ),
                    how="schedule within the verdict's TTL (p95_latency_ms x 3 of the gate)",
                )
        command = PendingCommand(
            pin,
            operation,
            duration_ms,
            self.events,
            delivered=False,
            deliver_at_ms=self._clock() + delay_ms,
            token=signature,
        )
        self._scheduled.append(command)
        return command

    def cancel_scheduled(self, token: Any, reason: str = ABORTED_BY_ACTION_ERROR) -> None:
        """Cancel every pending command `token` authorised (its @action raised)."""
        for command in self.pending_commands():
            if command.token is token:
                command.cancel(reason)

    def pending_commands(self) -> list[PendingCommand]:
        """Scheduled commands not yet delivered and not cancelled, oldest first."""
        return [c for c in self._scheduled if not c.delivered and not c.cancelled]

    def next_delivery_ms(self) -> float | None:
        due = [c.deliver_at_ms for c in self.pending_commands() if c.deliver_at_ms is not None]
        return min(due) if due else None

    def run_due(self) -> list[PendingCommand]:
        """Deliver every pending command whose time has come on the clock, in time order."""
        if self._clock is None:
            return []
        now = self._clock()
        due = sorted(
            (c for c in self.pending_commands() if (c.deliver_at_ms or 0) <= now),
            key=lambda c: c.deliver_at_ms or 0,
        )
        for command in due:
            command.delivered = True
            self.pins.setdefault(command.pin, PinAssertion(command.pin)).record(
                command.operation, command.duration_ms
            )
            self.events.emit(
                "actuator_command",
                {
                    "pin": command.pin,
                    "operation": command.operation,
                    "duration_ms": command.duration_ms,
                },
            )
        self._scheduled = [c for c in self._scheduled if not c.delivered and not c.cancelled]
        return due

    # -- sensor.read -------------------------------------------------------------
    def set_sensor(self, sensor: str, value: Any, unit: str | None = None) -> None:
        self.board.require_sensor(sensor, called_from="SimHAL.set_sensor()")
        self._sensors[sensor] = value
        if unit is not None:
            self._units[sensor] = unit

    def sensor_values(self) -> dict[str, tuple[Any, str | None]]:
        """Current value and unit of every declared sensor (None when not set)."""
        return {
            name: (self._sensors.get(name), self._units.get(name)) for name in self.board.sensors
        }

    def script_sensor(self, sensor: str, values: list[Any], unit: str | None = None) -> None:
        """Readings returned in order, one per read — how replay feeds a recorded session."""
        self.board.require_sensor(sensor, called_from="SimHAL.script_sensor()")
        self._scripted[sensor] = deque(values)
        if unit is not None:
            self._units[sensor] = unit

    def sensor_read(
        self, sensor: str, called_from: str = "<unknown>", use: str | None = None
    ) -> Any:
        """`use="fact"` marks a read made to compute a gate fact rather than by an action."""
        self.board.require_sensor(sensor, called_from=called_from)
        queue = self._scripted.get(sensor)
        if queue and use is None:
            self._sensors[sensor] = queue.popleft()
        if sensor not in self._sensors:
            raise BoardCapabilityError(
                where=f"{called_from} -> sensor.read {sensor!r}",
                why="the simulator has no scripted value for this sensor",
                how=f"call hal.set_sensor({sensor!r}, value) in the scenario first",
            )
        value = self._sensors[sensor]
        self.events.emit("sensor_read", reading_data(sensor, value, self._units.get(sensor), use))
        return value

    # -- audio -------------------------------------------------------------------
    def type_text(self, text: str) -> None:
        """Queue one typed utterance — the default `sim` input (Q-15)."""
        self._typed.append(text)

    def audio_in(self, called_from: str = "<unknown>") -> str | None:
        self._require("audio.in", called_from)
        if not self._typed:
            return None
        text = self._typed.popleft()
        self.events.emit("text_input", {"text": text})
        return text

    def audio_out(self, text: str, called_from: str = "<unknown>") -> None:
        self._require("audio.out", called_from)
        self.spoken.append(text)
        self.events.emit("tts_stream_start", {"text": text})

    # -- display -----------------------------------------------------------------
    def display(
        self,
        frame: str | bytes,
        *,
        width: int | None = None,
        height: int | None = None,
        format: str | None = None,
        called_from: str = "<unknown>",
    ) -> Frame:
        shown = make_frame(self.board, frame, width, height, format, called_from)
        self.frame = frame
        self.frames.append(shown)
        self.events.emit("display_frame", shown.event_data())
        return shown
