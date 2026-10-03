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
* `audio_in` — Q-15: typed text by default, queued with `type_text()`; or a
  WAV file (`audio_file()`, TSK-S3-13) at the board's rate, which the voice
  driver (`perception.VoiceSession.play`) frames, runs through VAD and sends to STT.
* `audio_out` — records `tts_stream_start`; the audio of a reply, when a TTS
  provider made one, plays on `speaker()`, a timeline written out as WAV
  (`hal/audio.py`).
* `digital_out` also takes `operation = "pwm"` (RFC-0010): the channel's duty and frequency are
  the HAL's commanded state, the enable line is up while the command runs, and `pin_state()` reads
  back what was commanded — or, where the board declares `feedback`, what `set_feedback()` says the
  hardware reports.
* `sensor_read` — values scripted with `set_sensor()` (or a sequence with
  `script_sensor()`, which replay uses); records `sensor_read`. An unscripted
  sensor raises instead of inventing a reading.
* `analog_in` — a value set with `set_analog()`, in the channel's unit; a value that is not
  a finite number inside the channel's `[min, max]`, or none set, raises
  `PerceptionUnavailableError` instead of being clamped; records `analog_in` (TSK-I2a-04);
* `i2c_read` — values scripted with `set_i2c()` (or a sequence with `script_i2c()`, which
  replay uses), through the same allow-list as `linux`; records `i2c_read`. It never
  scans and never invents a reading (RFC-0007 §3b).
* `digital_in` — levels scripted with `set_digital_in()` (RFC-0007 §3a); records `digital_in`.
  An input nobody set raises `PerceptionUnavailableError` instead of inventing a level.
* `vision_in` — the board's camera, replayed: whoever owns the wiring attaches a factory
  (`attach_camera`; the session does, from `[sim.vision]`), and the camera it makes runs
  only in a mode the board declares. `sim` reads no camera of its own (`sim/vision/`).
* `display` — a virtual frame (text, or raw RGB565 / RGB888 pixels) checked
  against the declared resolution; records `display_frame` with its digest
  (docs/spec/simulation_coverage.md §3).
"""

from __future__ import annotations

import hashlib
import math
import os
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from ..errors import ActionContractViolation, BoardCapabilityError, PerceptionUnavailableError
from . import Authorizer, HardwareAbstractionLayer, PinAssertion, _require_signature
from .analog import analog_data, check_reading, unavailable
from .audio import Speaker, WavSource
from .audio_live import (
    LiveAudioIn,
    LiveAudioOut,
    LiveSpeaker,
    _audio_node,
)
from .audio_live import (
    _import_sounddevice as _live_import_sounddevice,
)
from .board import BoardProfile, load_board_by_id
from .envelope import Reservation, SafetyEnvelope
from .i2c_bus import I2CReader, ReadFault, ScriptedI2C
from .motion_core import SimActuator
from .pwm import pwm_limits
from .vision import Camera, CameraFactory, CameraUnavailable, Mode, modes_of, monotonic_ms

AUDIO_ENV = "NEUROEDGE_AUDIO"
AUDIO_IN_ENV = "NEUROEDGE_AUDIO_IN"
AUDIO_OUT_ENV = "NEUROEDGE_AUDIO_OUT"
AUDIO_BACKENDS = ("file", "live")


def _import_sounddevice(where: str = "SimHAL -> audio.in/audio.out") -> Any:
    return _live_import_sounddevice(where=where)


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


def _i2c_value(value: Any, width: int, where: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value < 256**width:
        raise BoardCapabilityError(
            where=where,
            why=f"{value!r} is not a {width}-byte register value (0..{256**width - 1})",
            how="script integers that fit the read width",
        )
    return value


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
            data["text"] = self.text  # hashed by the recorder unless --raw
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
        envelope: SafetyEnvelope | None = None,
        audio: str | None = None,
        audio_in_device: str | None = None,
        audio_out_device: str | None = None,
        sounddevice: Any = None,
    ) -> None:
        board = board if board is not None else load_board_by_id("sim-default")
        if board.target != "sim":
            raise BoardCapabilityError(
                where=f"SimHAL(board={board.id!r})",
                why=f"board {board.id!r} targets {board.target!r}, not 'sim'",
                how="use a sim board such as sim-default, or the HAL for that target",
            )
        super().__init__(target="sim", board=board, authorize=authorize, envelope=envelope)
        self.events: EventSink = events if events is not None else _NullSink()
        self._sensors: dict[str, Any] = dict(sensors or {})
        self._units: dict[str, str] = {}
        self._levels: dict[str, bool] = {}
        self._scripted: dict[str, deque[Any]] = {}
        self._analog: dict[str, Any] = {}
        self._feedback: dict[str, tuple[float | None, float | None, str | None]] = {}
        self._i2c_script = ScriptedI2C()
        self._i2c = I2CReader(
            board,
            lambda bus, where: self._i2c_script.transport(bus),
            lambda type, data: self.events.emit(type, data),
        )
        self._typed: deque[str] = deque()
        self.frame: str | bytes | None = None
        self.frames: list[Frame] = []
        self.spoken: list[str] = []
        self._speaker: Speaker | LiveSpeaker | None = None
        # Scheduled commands (voice_fsm.md §5.1); None = scheduling refused.
        self._clock: Callable[[], float] | None = None
        self._scheduled: list[PendingCommand] = []
        # `motion.*` (RFC-0011): a model of the actuators the board declares, on the session clock.
        self._install_motion(SimActuator())

        audio_where = "SimHAL(audio=...)" if audio is not None else AUDIO_ENV
        audio_choice = audio if audio is not None else os.environ.get(AUDIO_ENV) or None
        if audio_choice is not None and audio_choice not in AUDIO_BACKENDS:
            raise BoardCapabilityError(
                where=audio_where,
                why=(
                    f"unknown audio backend {audio_choice!r}; the backends are "
                    f"{list(AUDIO_BACKENDS)}"
                ),
                how=f"set {AUDIO_ENV}=file for WAV sessions, or =live for sounddevice (Q-50)",
            )
        self.audio_backend: str | None = audio_choice
        self._sounddevice = sounddevice
        self._audio_in: LiveAudioIn | None = None
        self._audio_out: LiveAudioOut | None = None
        self.audio_in_device = _audio_node(audio_in_device, AUDIO_IN_ENV, None)
        self.audio_out_device = _audio_node(audio_out_device, AUDIO_OUT_ENV, None)
        self._camera_factory: CameraFactory | None = None
        self._cameras: list[Camera] = []

    def _require(self, primitive: str, called_from: str) -> dict[str, Any]:
        if not self.board.supports(primitive):
            raise BoardCapabilityError(
                where=f"{called_from} -> {primitive}",
                why=f"board {self.board.id!r} does not declare the {primitive!r} primitive",
                how=f"add it to {self.board.source}, or choose a board that provides it",
            )
        return self.board.capability(primitive)

    # -- vision.in -------------------------------------------------------------
    def attach_camera(self, factory: CameraFactory | None) -> None:
        """Say how a camera is made here: the virtual one of `[sim.vision]`, or none."""
        self._camera_factory = factory

    def vision_in(
        self,
        mode: Mode,
        called_from: str = "<unknown>",
        *,
        clock: Callable[[], float] | None = None,
    ) -> Camera:
        """
        The virtual camera in `mode`. Only a mode of the board is accepted — `sim` is never
        richer than the board it mirrors (CHANGELOG §3.3 #7) — and with no camera attached
        it raises: a simulator that handed out frames of nothing would turn every vision
        agent into a pass.
        """
        self._require("vision.in", called_from)
        declared = modes_of(self.board.vision_modes)
        if mode not in declared:
            raise BoardCapabilityError(
                where=f"{called_from} -> vision.in",
                why=f"board {self.board.id!r} declares no camera mode {mode}; it has "
                f"{[str(m) for m in declared]}",
                how="open the camera in one of the board's modes",
            )
        if self._camera_factory is None:
            raise CameraUnavailable(
                where=f"{called_from} -> vision.in",
                why="the simulator reads no camera of its own, and none is attached",
                how='add [sim.vision] to agent.toml: a directory of frames, or source = "synthetic"',
            )
        camera = self._camera_factory(mode, clock or monotonic_ms)
        self._cameras.append(camera)
        return camera

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
        *,
        frequency_hz: int | None = None,
        duty: float | None = None,
    ) -> PendingCommand:
        if operation not in ("pulse", "on", "off", "pwm"):
            raise BoardCapabilityError(
                where=f"{called_from} -> digital.out {pin!r}",
                why=f"unknown operation {operation!r}",
                how="use one of 'pulse', 'on', 'off', 'pwm'",
            )
        if operation == "pwm" and delay_ms:
            raise BoardCapabilityError(
                where=f"{called_from} -> digital.out {pin!r}",
                why="a pwm command cannot be scheduled (after_ms): it starts when the gate allows it",
                how="call pwm() without after_ms",
            )
        operation, duration_ms, applied = self._pwm_prepare(
            pin, operation, duration_ms, frequency_hz, duty, called_from
        )
        if delay_ms:
            return self._schedule(pin, operation, duration_ms, signature, called_from, delay_ms)
        pwm = (int(frequency_hz), applied) if operation == "pwm" else None  # type: ignore[arg-type]
        reservation = self._admit(pin, operation, duration_ms, signature, called_from, pwm=pwm)
        data: dict[str, Any] = {"pin": pin, "operation": operation, "duration_ms": duration_ms}
        if pwm is not None:
            self._pwm_started(pin, pwm[0], pwm[1], duration_ms, reservation)
            data.update(frequency_hz=pwm[0], duty=pwm[1])
        if operation == "off":
            self._pwm_stopped(pin)
            if self.envelope is not None:
                self.envelope.ended(pin)
            if duty is not None and pin in self.board.pwm_pins:
                data["cause"] = "duty_zero"  # a pwm command whose duty quantised to nothing
        self.events.emit("actuator_command", data)
        return PendingCommand(
            pin,
            operation,
            duration_ms,
            self.events,
            on_cancel=self._ending(reservation, pin),
            token=signature,
        )

    def _ending(
        self, reservation: Reservation | None, pin: str | None = None
    ) -> Callable[[], None] | None:
        """What aborting a command does to its pin: it goes off now, and the envelope is told."""
        envelope = self.envelope
        if reservation is None or envelope is None:
            return None

        def abort() -> None:
            self._pwm_stopped(reservation.name)
            envelope.ended(reservation.name, reservation)

        return abort

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
        # The envelope reserves the on-time of the delivery, so a command that would not
        # fit is refused now, not when the pin is meant to move.
        reservation = self._admit(
            pin, operation, duration_ms, signature, called_from, after_ms=delay_ms, record=False
        )
        # A verdict is fresh for its TTL (actions/token.py); a command delivered after
        # that would move the pin on facts the gate never saw, so it is refused now.
        issued_at = getattr(signature, "issued_at_ms", None)
        ttl = getattr(signature, "ttl_ms", None)
        if issued_at is not None and ttl is not None:
            deliver_at = self._clock() + delay_ms
            if deliver_at - issued_at > ttl:
                if reservation is not None and self.envelope is not None:
                    self.envelope.refund(reservation)
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
            on_cancel=self._ending(reservation),
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
        if self._motion is not None:  # a lease, a hold or a run that ends is a due time too
            motion = self._motion.next_deadline_ms()
            if motion is not None:
                due.append(motion)
        return min(due) if due else None

    def run_due(self) -> list[PendingCommand]:
        """Deliver every pending command whose time has come on the clock, in time order."""
        if self.envelope is not None:
            self.envelope.settle()  # a pin whose on-time is up goes off, whoever is listening
        self.settle_motion()  # ... and a channel whose lease ran out goes to its safe state
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

    # -- state() read-back (RFC-0010 §3b) -------------------------------------------------
    def set_feedback(
        self,
        pin: str,
        *,
        duty: float | None = None,
        frequency_hz: float | None = None,
        fail: str | None = None,
    ) -> None:
        """
        What the simulated hardware reads back for a channel in `feedback.pins`, instead of the
        commanded output — a drifting fan, a dead sensor. `fail` makes the read-back fail with
        that reason (NE5001). `clear_feedback()` returns to the output the HAL commanded.
        """
        where = "SimHAL.set_feedback()"
        self.board.require_pin(pin, called_from=where)
        if pwm_limits(self.board, pin) is None:
            raise BoardCapabilityError(
                where=f"{where} {pin!r}",
                why=f"{pin!r} is not a PWM channel",
                how="name a pin of [capabilities.digital_out.pwm].pins",
            )
        if pin not in self.board.capabilities["digital_out"].get("feedback", {}).get("pins", ()):
            raise BoardCapabilityError(
                where=f"{where} {pin!r}",
                why=f"board {self.board.id!r} declares no feedback for {pin!r}, so its state() is "
                "what was commanded and there is no read-back to set",
                how="list the pin in [capabilities.digital_out.feedback].pins of the board",
            )
        self._feedback[pin] = (duty, frequency_hz, fail)

    def clear_feedback(self, pin: str) -> None:
        self._feedback.pop(pin, None)

    def _read_feedback(self, pin: str, limits: Any, where: str) -> dict[str, float | None]:
        injected = self._feedback.get(pin)
        if injected is not None:
            duty, frequency, fail = injected
            if fail is not None:
                raise PerceptionUnavailableError(
                    where=where,
                    why=f"the simulated read-back of {pin!r} fails: {fail}",
                    how="the criterion stays undecided; clear it with clear_feedback()",
                )
            return {"duty": duty, "frequency_hz": frequency}
        run = self.commanded_pwm(pin)
        return {
            "duty": 0.0 if run is None else run[1],
            "frequency_hz": None if run is None else float(run[0]),
        }

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

    # -- analog.in ---------------------------------------------------------------
    def set_analog(self, channel: str, value: Any) -> None:
        """
        What the next read of `channel` returns, in the channel's declared unit. Any value
        is accepted, so a scenario can break the ADC (NaN, out of range); `analog_in` then
        refuses it exactly as `linux` refuses the same reading from the kernel.
        """
        self.board.require_analog(channel, called_from="SimHAL.set_analog()")
        self._analog[channel] = value

    def analog_values(self) -> dict[str, tuple[Any, str]]:
        """Current value (None when not set) and declared unit of every `analog.in` channel."""
        return {
            c["name"]: (self._analog.get(c["name"]), c["unit"]) for c in self.board.analog_channels
        }

    def analog_in(
        self, channel: str, called_from: str = "<unknown>", use: str | None = None
    ) -> float:
        """
        One reading of `channel`, recorded as `analog_in`. A value that is not a finite number
        inside `[min, max]`, or none set, is `PerceptionUnavailableError` (NE5001) — recorded
        as a failed read too, so the trace shows the attempt.
        """
        declared = self.board.require_analog(channel, called_from=called_from)
        where = f"{called_from} -> analog.in {channel!r}"
        try:
            if channel not in self._analog:
                raise unavailable(
                    where,
                    "the simulator has no value for this channel",
                    f"call hal.set_analog({channel!r}, value) in the scenario first",
                )
            value = check_reading(declared, self._analog[channel], None, where)
        except PerceptionUnavailableError as error:
            self.events.emit("analog_in", analog_data(channel, use=use, error=error.why))
            raise
        self.events.emit("analog_in", analog_data(channel, value, declared["unit"], use))
        return value

    # -- i2c ---------------------------------------------------------------------
    def set_i2c(
        self, bus: str, device: str | int, register: int | None, value: int, *, width: int = 1
    ) -> None:
        """What a read of this device (and register) returns from now on; the board decides what exists."""
        where = "SimHAL.set_i2c()"
        declared = self._i2c.resolve(bus, device, register, width, where)
        self._i2c_script.set(bus, declared["address"], register, _i2c_value(value, width, where))

    def script_i2c(
        self,
        bus: str,
        device: str | int,
        register: int | None,
        values: list[int | ReadFault],
        *,
        width: int = 1,
    ) -> None:
        """Readings returned in order, one per read — how replay feeds a recorded session."""
        where = "SimHAL.script_i2c()"
        declared = self._i2c.resolve(bus, device, register, width, where)
        checked = [v if isinstance(v, ReadFault) else _i2c_value(v, width, where) for v in values]
        self._i2c_script.script(bus, declared["address"], register, checked)

    def i2c_read(
        self,
        bus: str,
        device: str | int,
        register: int | None = None,
        *,
        width: int = 1,
        called_from: str = "<unknown>",
    ) -> int:
        return self._i2c.read(bus, device, register, width=width, called_from=called_from)

    def i2c_scan(self, bus: str, called_from: str = "<unknown>") -> list[Any]:
        raise BoardCapabilityError(
            where=f"{called_from} -> i2c.scan {bus!r}",
            why="the simulator has no bus to scan: sim only replays what was recorded (RFC-0007 §3b)",
            how="scan on the linux target, where a probe reaches a real or i2c-stub bus",
        )

    # -- digital.in ----------------------------------------------------------------
    def set_digital_in(self, pin: str, level: bool) -> None:
        """Set the level a declared input line reads (`set_sensor`'s counterpart for a pin)."""
        where = "SimHAL.set_digital_in()"
        self.board.require_input_pin(pin, called_from=where)
        if not isinstance(level, bool):
            raise BoardCapabilityError(
                where=f"{where} -> digital.in {pin!r}",
                why=f"{level!r} is not a logic level",
                how="pass True (the line high) or False (low)",
            )
        self._levels[pin] = level

    def digital_in_values(self) -> dict[str, bool | None]:
        """Current level of every declared input line (None when nobody set it)."""
        return {pin: self._levels.get(pin) for pin in self.board.input_pins}

    def _read_level(self, pin: str, where: str) -> bool:
        if pin not in self._levels:
            raise PerceptionUnavailableError(
                where=where,
                why="the simulator has no level set for this input line",
                how=f"call hal.set_digital_in({pin!r}, level) in the scenario first, or `:input` in the REPL",
            )
        return self._levels[pin]

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

    def _rate(self, primitive: str, called_from: str) -> int:
        rate = self._require(primitive, called_from).get("sample_rate_hz")
        if isinstance(rate, bool) or not isinstance(rate, int) or rate <= 0:
            raise BoardCapabilityError(
                where=f"{called_from} -> {primitive}",
                why=f"board {self.board.id!r} declares {primitive} without a sample_rate_hz, and "
                "PCM audio needs one",
                how=f"add sample_rate_hz = 16000 to {primitive} in {self.board.source}",
            )
        return rate

    def _device(self) -> Any:
        if self._sounddevice is None:
            self._sounddevice = _import_sounddevice()
        return self._sounddevice

    def audio_file(self, path: Any, called_from: str = "<unknown>") -> WavSource:
        """A WAV file as `audio.in`: 16-bit mono PCM at the board's `sample_rate_hz` only."""
        rate = self._rate("audio.in", called_from)
        return WavSource.open(path, sample_rate_hz=rate, called_from=called_from)

    def audio_source(self, called_from: str = "<unknown>") -> LiveAudioIn:
        """The live capture device (system default by default); live backend only."""
        if self.audio_backend != "live":
            raise BoardCapabilityError(
                where=f"{called_from} -> audio.in",
                why="no live audio backend is chosen for this machine; refusing to guess one",
                how=(
                    f"set {AUDIO_ENV}=live or run with --mic (TSK-I4-04 slice 2) or "
                    "pass SimHAL(audio='live'); a WAV session uses audio_file()"
                ),
            )
        capability = self._require("audio.in", called_from)
        if self._audio_in is None:
            self._audio_in = LiveAudioIn(
                self._device(),
                sample_rate_hz=self._rate("audio.in", called_from),
                channels=int(capability.get("channels") or 1),
                device=self.audio_in_device,
                events=self.events,
                caller="SimHAL",
                env_var=AUDIO_IN_ENV,
            )
        self._audio_in.open()
        return self._audio_in

    def audio_sink(self, called_from: str = "<unknown>") -> LiveAudioOut:
        """The live playback device (system default by default); live backend only."""
        if self.audio_backend != "live":
            raise BoardCapabilityError(
                where=f"{called_from} -> audio.out",
                why="no live audio backend is chosen for this machine; refusing to guess one",
                how=(
                    f"set {AUDIO_ENV}=live or run with --mic (TSK-I4-04 slice 2) or "
                    "pass SimHAL(audio='live'); speaker() timeline writes a WAV instead"
                ),
            )
        capability = self._require("audio.out", called_from)
        if self._audio_out is None:
            self._audio_out = LiveAudioOut(
                self._device(),
                sample_rate_hz=self._rate("audio.out", called_from),
                channels=int(capability.get("channels") or 1),
                device=self.audio_out_device,
                caller="SimHAL",
                env_var=AUDIO_OUT_ENV,
            )
        self._audio_out.open()
        return self._audio_out

    def speaker(self, called_from: str = "<unknown>") -> Any:
        """
        `audio.out` as a timeline at the board's rate — what `--voice-out` writes and
        what `VoiceSession` plays a reply on. With the live backend the same `play()`
        also writes to the device; with the file backend the timeline is all there is.
        """
        rate = self._rate("audio.out", called_from)
        if self._speaker is None:
            self._speaker = (
                LiveSpeaker(self.audio_sink(called_from), rate)
                if self.audio_backend == "live"
                else Speaker(rate)
            )
        return self._speaker

    def close(self) -> None:
        """Release live audio streams and cameras and end every on-time the envelope holds; idempotent."""
        errors: list[BaseException] = []
        if self._motion is not None:  # every channel to its safe state first (cause `close`)
            try:
                self._motion.close()
            except BaseException as exc:
                errors.append(exc)
        if self.envelope is not None:
            self.envelope.end_all()
        cameras, self._cameras = self._cameras, []
        for device in (self._audio_in, self._audio_out, *cameras):
            if device is None:
                continue
            try:
                device.close()
            except BaseException as exc:
                errors.append(exc)
        if errors:
            raise errors[0]

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
