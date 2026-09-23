"""
HAL backend for target `sim` (TSK-S2-01, FR-TGT-01).

The simulator has no hardware, so each primitive is a recorded state change and
a trace event. Its capabilities come from `boards/sim-default.toml`, which
mirrors the reference board rather than exceeding it (CHANGELOG §3.3 #7).

* `digital_out` — the only way a pin changes; records `actuator_command` and
  returns a cancellable `PendingCommand` (RB-3: barge-in must be able to abort a
  pending pulse, so the handle exists on every target from day one).
* `audio_in` — Q-15: typed text by default, queued with `type_text()`.
* `audio_out` — records `tts_stream_start`.
* `sensor_read` — values scripted with `set_sensor()`; an unscripted sensor
  raises instead of inventing a reading.
* `display` — a virtual frame, checked against the declared resolution.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from ..errors import BoardCapabilityError
from . import Authorizer, HardwareAbstractionLayer, _require_signature
from .board import BoardProfile, load_board_by_id

ABORTED_BY_BARGE_IN = "ACTUATOR_ABORTED_BY_BARGE_IN"


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

    def cancel(self, reason: str = ABORTED_BY_BARGE_IN) -> None:
        if self.cancelled:
            return
        self.cancelled = True
        self.events.emit("actuator_aborted", {"pin": self.pin, "reason": reason})


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
        self._typed: deque[str] = deque()
        self.frame: str | bytes | None = None
        self.spoken: list[str] = []

    def _require(self, primitive: str, called_from: str) -> dict[str, Any]:
        if not self.board.supports(primitive):
            raise BoardCapabilityError(
                where=f"{called_from} -> {primitive}",
                why=f"board {self.board.id!r} does not declare the {primitive!r} primitive",
                how=f"add it to {self.board.source}, or choose a board that provides it",
            )
        return self.board.capability(primitive)

    # -- digital.out -----------------------------------------------------------
    def digital_out(
        self,
        pin: str,
        operation: str,
        duration_ms: int = 0,
        signature: Any = "",
        called_from: str = "<unknown>",
    ) -> PendingCommand:
        if operation not in ("pulse", "on", "off"):
            raise BoardCapabilityError(
                where=f"{called_from} -> digital.out {pin!r}",
                why=f"unknown operation {operation!r}",
                how="use one of 'pulse', 'on', 'off'",
            )
        super().digital_out(pin, operation, duration_ms, signature, called_from)
        self.events.emit(
            "actuator_command", {"pin": pin, "operation": operation, "duration_ms": duration_ms}
        )
        return PendingCommand(pin, operation, duration_ms, self.events)

    # -- sensor.read -------------------------------------------------------------
    def set_sensor(self, sensor: str, value: Any) -> None:
        self.board.require_sensor(sensor, called_from="SimHAL.set_sensor()")
        self._sensors[sensor] = value

    def sensor_read(self, sensor: str, called_from: str = "<unknown>") -> Any:
        self.board.require_sensor(sensor, called_from=called_from)
        if sensor not in self._sensors:
            raise BoardCapabilityError(
                where=f"{called_from} -> sensor.read {sensor!r}",
                why="the simulator has no scripted value for this sensor",
                how=f"call hal.set_sensor({sensor!r}, value) in the scenario first",
            )
        return self._sensors[sensor]

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
        called_from: str = "<unknown>",
    ) -> None:
        declared = self._require("display", called_from)
        for axis, value in (("width", width), ("height", height)):
            if value is not None and value > declared[axis]:
                raise BoardCapabilityError(
                    where=f"{called_from} -> display",
                    why=f"frame {axis} {value} exceeds the board's {declared[axis]}",
                    how=f"render at most {declared['width']}x{declared['height']}",
                )
        self.frame = frame
