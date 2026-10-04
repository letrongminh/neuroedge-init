"""
Hardware Abstraction Layer (HAL) — L1.

Five immutable primitives (FR-HAL-01): `audio.in`, `audio.out`, `digital.out`,
`sensor.read`, `display`. The set is closed on purpose; see
docs/spec/hal_mcu_review.md for what that buys on the microcontroller. Extension primitives
(RFC-0013) are optional per board: `digital.in` (RFC-0007 §3a) is read with `digital_in()`.
"""

import time
from collections import deque
from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING, Any, NamedTuple

from ..errors import (
    ActionContractViolation,
    BoardCapabilityError,
    EnvelopeRefusedError,
    PerceptionUnavailableError,
)
from .board import (
    ALL_PRIMITIVES,
    EXTENSION_PRIMITIVES,
    PRIMITIVES,
    REQUIRABLE_PRIMITIVES,
    SUPPORTED_TARGETS,
    BoardProfile,
    available_boards,
    load_board,
    load_board_by_id,
)
from .envelope import Reservation, SafetyEnvelope
from .motion_core import Actuator, Channel, MotionController, MotionLease
from .pwm import COMMANDED, MEASURED, PinState, check_pwm, pin_state_data, pwm_limits

if TYPE_CHECKING:
    from .audio import WavSource
    from .audio_live import LiveAudioIn, LiveAudioOut
    from .vision import Camera, Mode

__all__ = [
    "ALL_PRIMITIVES",
    "EXTENSION_PRIMITIVES",
    "PRIMITIVES",
    "REQUIRABLE_PRIMITIVES",
    "SUPPORTED_TARGETS",
    "BoardProfile",
    "DigitalReading",
    "HardwareAbstractionLayer",
    "PinAssertion",
    "PinState",
    "available_boards",
    "ensure_envelope",
    "load_board",
    "load_board_by_id",
]


class PinAssertion:
    """
    Observed state of one digital output, as asserted by Action CI (FR-CI-03).

    `never_pulsed()` is the assertion that matters most: the compliance suite
    proves a blocked action left the physical pin untouched, not merely that a
    verdict object said BLOCK.
    """

    def __init__(
        self,
        pin_name: str,
        pulsed: bool = False,
        duration_ms: int = 0,
        commands: list[tuple[str, int]] | None = None,
    ):
        self.pin_name = pin_name
        # Every accepted command, in order. The history — not the last write —
        # is what the assertions read, so an `on()` or an `off()` after a pulse
        # can never make a touched pin look untouched.
        self.commands: list[tuple[str, int]] = (
            list(commands) if commands is not None else ([("pulse", duration_ms)] if pulsed else [])
        )
        # The `(frequency_hz, duty)` of every accepted `pwm` command, in order (RFC-0010).
        self.pwm: list[tuple[int, float]] = []

    def record(
        self,
        operation: str,
        duration_ms: int,
        pwm: tuple[int, float] | None = None,
    ) -> None:
        self.commands.append((operation, duration_ms))
        if pwm is not None:
            self.pwm.append(pwm)

    @property
    def pulses(self) -> list[int]:
        return [duration for operation, duration in self.commands if operation == "pulse"]

    @property
    def pulsed(self) -> bool:
        return bool(self.pulses)

    @property
    def duration_ms(self) -> int:
        return self.pulses[-1] if self.pulses else 0

    def never_pulsed(self) -> bool:
        """True only if the pin never accepted *any* command."""
        return not self.commands

    def pulsed_once(self, duration_ms: int = 0) -> bool:
        if len(self.commands) != 1 or not self.pulsed:
            return False
        return duration_ms <= 0 or self.pulses[0] == duration_ms

    def __repr__(self) -> str:  # pragma: no cover - diagnostic aid
        state = f"pulse {self.duration_ms}ms" if self.pulsed else "idle"
        return f"<PinAssertion {self.pin_name} {state}>"


class DigitalReading(NamedTuple):
    """
    One `digital.in` level and the instant the HAL read it (RFC-0007 §3a).

    `read_ms` is on the clock of the HAL's event log — the clock the gate ages a reading by —
    and is taken before the line is read, so a reading is never younger than it looks.
    """

    value: bool
    read_ms: float


def _monotonic_ms() -> float:
    return time.monotonic() * 1000.0


Authorizer = Callable[[Any, str, str], None]


def _require_signature(signature: Any, pin: str, called_from: str) -> None:
    """
    Default check: refuse everything. Only a token ledger — installed by `c.do()`'s
    `Conversation` — can authorise a pin, so a HAL that nobody wired up cannot be
    driven by any string that merely looks like proof (A3).
    """
    if not signature:
        why = (
            "actuator command carries no gate signature; every digital.out "
            "must prove which gate authorised it (Proposal Appendix A.2)"
        )
    else:
        why = "no verdict-token ledger is installed on this HAL, so no proof can be checked"
    raise ActionContractViolation(
        where=f"{called_from} -> digital.out {pin!r}",
        why=why,
        how=(
            "route the command through an @action function run by c.do(), which "
            "installs the ledger and attaches a single-use verdict token"
        ),
    )


class HardwareAbstractionLayer:
    """
    Standard interface across `sim`, `linux` and `esp32s3`.

    `digital_out` is the only way a pin changes state. It asks the safety envelope first and
    `authorize` second; both are installed from outside. The default `authorize` refuses
    every command; `Conversation` (TSK-S2-05) installs the single-use verdict-token check and,
    for a board that declares envelopes, the envelope (RFC-0007 §3d, TSK-N2-01).
    """

    def __init__(
        self,
        target: str = "sim",
        board: BoardProfile | None = None,
        *,
        authorize: Authorizer = _require_signature,
        envelope: SafetyEnvelope | None = None,
    ):
        self.target = target
        self.board = board
        self.authorize = authorize
        self.pins: dict[str, PinAssertion] = {}
        self._replayed_levels: dict[str, deque[bool | None]] = {}
        self._replayed_states: dict[str, deque[dict[str, Any] | None]] = {}
        # What each PWM channel was last commanded to: (frequency_hz, duty, off at this instant
        # of the HAL's clock). The HAL's own memory — `commanded`, never a measurement.
        self._pwm_runs: dict[str, tuple[int, float, float]] = {}
        self._envelope: SafetyEnvelope | None = None
        self.envelope = envelope
        # The channels of `motion.*`, once a target gives them an actuator (`_install_motion`).
        self._motion: MotionController | None = None

    @property
    def envelope(self) -> SafetyEnvelope | None:
        """
        The per-pin safety envelope, or None when none is installed: then `digital_out` is
        what it was before the envelope existed (a pin the board does not bound moves as it
        always did).
        """
        return self._envelope

    @envelope.setter
    def envelope(self, envelope: SafetyEnvelope | None) -> None:
        self._envelope = envelope
        if envelope is not None:
            envelope.on_auto_off = self._auto_off

    def _emit(self, type: str, data: dict[str, Any]) -> None:
        events = getattr(self, "events", None)
        if events is not None:
            events.emit(type, data)

    def _auto_off(self, reservation: Reservation) -> None:
        """The HAL turned a pin off itself (a command toward the safe state, never refused)."""
        if self._motion is not None and self._motion.covers(reservation.name):
            return  # a channel's run ends in the controller (it records `motion_safe`)
        self._pwm_stopped(reservation.name)
        if reservation.auto_off_cause is not None:
            self._emit(
                "actuator_command",
                {
                    "pin": reservation.name,
                    "operation": "off",
                    "duration_ms": 0,
                    "cause": reservation.auto_off_cause,
                },
            )

    def _admit(
        self,
        pin: str,
        operation: str,
        duration_ms: int,
        signature: Any,
        called_from: str,
        *,
        after_ms: float = 0,
        record: bool = True,
        pwm: tuple[int, float] | None = None,
    ) -> Reservation | None:
        """
        What every target does before it moves a pin: `require_pin`, then the envelope, then
        `authorize`, then `record`. The envelope stands before `authorize`, so a refused
        command spends no token; and a command `authorize` refuses gives back every
        millisecond it reserved. The command toward the safe state (`off`) is none of the
        envelope's business and needs no proof (RFC-0007 §3d): it only has to name a real pin.
        Returns the reservation the caller must `ended()` or `refund()` once the pin has moved
        (or not), or None.
        """
        if self.board is not None:
            self.board.require_pin(pin, called_from=called_from)
        reservation = None
        if operation != "off":
            envelope = self._envelope
            if envelope is not None:
                try:
                    reservation = envelope.reserve(
                        pin,
                        duration_ms,
                        operation=operation,
                        after_ms=after_ms,
                        called_from=called_from,
                    )
                except EnvelopeRefusedError as refusal:
                    self._emit("envelope_refused", refusal.event)
                    raise
            try:
                self.authorize(signature, pin, called_from)
            except BaseException:
                if reservation is not None and envelope is not None:
                    envelope.refund(reservation)
                raise
        if record:
            self.pins.setdefault(pin, PinAssertion(pin)).record(operation, duration_ms, pwm)
        return reservation

    def _pwm_prepare(
        self,
        pin: str,
        operation: str,
        duration_ms: Any,
        frequency_hz: Any,
        duty: Any,
        called_from: str,
    ) -> tuple[str, int, float]:
        """
        The board's limits on one command, before the envelope and `authorize` (RFC-0010 §3b):
        `(operation, duration_ms, applied duty)`. A pin the board does not declare is refused
        here as it is in `_admit`; a PWM command whose duty quantises to zero comes back as `off`.
        """
        if self.board is None:
            if operation == "pwm":  # no board, no limits to check a PWM command against
                raise BoardCapabilityError(
                    where=f"{called_from} -> digital.out {pin!r}",
                    why="a pwm command is checked against the board's PWM limits, and this HAL has no board",
                    how="build the HAL with a board that declares the channel under digital_out.pwm",
                )
            return operation, duration_ms, 0.0
        self.board.require_pin(pin, called_from=called_from)
        return check_pwm(self.board, pin, operation, duration_ms, frequency_hz, duty, called_from)

    def _pwm_started(
        self,
        pin: str,
        frequency_hz: int,
        duty: float,
        duration_ms: int,
        reservation: Reservation | None,
    ) -> None:
        """A `pwm` command was accepted: the channel is commanded for the time it may stay on."""
        reserved: float = float(duration_ms)
        if reservation is not None:
            reserved = reservation.reserved_ms
        else:
            limits = None if self.board is None else pwm_limits(self.board, pin)
            if limits is not None and limits.max_continuous_ms is not None:
                reserved = min(reserved, limits.max_continuous_ms)
        self._pwm_runs[pin] = (frequency_hz, duty, self._clock_ms() + reserved)

    def _pwm_stopped(self, pin: str) -> None:
        self._pwm_runs.pop(pin, None)

    def pwm_enabled(self, pin: str) -> bool:
        """
        Whether the HAL holds the enable line of a PWM channel up: only while a gated `pwm`
        command is running (RFC-0010 §9.2). On `linux` the line itself is `line_value(pin)`.
        """
        return self.commanded_pwm(pin) is not None

    def commanded_pwm(self, pin: str) -> tuple[int, float] | None:
        """`(frequency_hz, duty)` the channel is commanded to now, or None when it is off."""
        run = self._pwm_runs.get(pin)
        if run is None:
            return None
        if self._clock_ms() >= run[2]:  # the on-time is over: the channel goes off by itself
            self._pwm_runs.pop(pin, None)
            return None
        return run[0], run[1]

    def digital_out(
        self,
        pin: str,
        operation: str,
        duration_ms: int = 0,
        signature: Any = "",
        called_from: str = "<unknown>",
        *,
        frequency_hz: int | None = None,
        duty: float | None = None,
    ) -> None:
        """
        Drive a digital output.

        Appendix A.2 makes the gate signature non-optional: there is no code
        path from agent logic to a physical pin that does not carry proof of an
        authorising gate. An unsigned command is a contract violation, not a
        permission error to be retried. The pin is checked before the proof is
        spent, so a typo never consumes a verdict token. The one exception is the
        command toward the safe state, `off`, which is never blocked (RFC-0007 §3d).

        `operation = "pwm"` (RFC-0010) takes `frequency_hz`, `duty` and a positive
        `duration_ms`, all three; only a PWM channel takes it, and a PWM channel takes only it
        and `off`.
        """
        operation, duration_ms, applied = self._pwm_prepare(
            pin, operation, duration_ms, frequency_hz, duty, called_from
        )
        pwm = (int(frequency_hz), applied) if operation == "pwm" else None  # type: ignore[arg-type]
        reservation = self._admit(pin, operation, duration_ms, signature, called_from, pwm=pwm)
        if operation == "pwm" and pwm is not None:
            self._pwm_started(pin, pwm[0], pwm[1], duration_ms, reservation)
        if operation == "off":
            self._pwm_stopped(pin)
            if self._envelope is not None:
                self._envelope.ended(pin)

    # -- motion.* (RFC-0011) ---------------------------------------------------------------
    def _install_motion(
        self,
        actuator: Actuator,
        *,
        on_deadline: Callable[[float | None], None] | None = None,
        only: Iterable[str] | None = None,
    ) -> None:
        """
        Give the board's motion channels their target's actuator (`only` those named). A board
        with none: no-op.
        """
        if self.board is None or not self.board.motion_channels:
            return
        keep = None if only is None else set(only)
        channels = [
            Channel.from_record(record)
            for record in self.board.motion_channels
            if keep is None or record["name"] in keep
        ]
        if not channels:
            return
        self._motion = MotionController(
            self, channels, actuator, self._motion_clock, on_deadline=on_deadline
        )

    def _motion_clock(self) -> float:
        """The clock the leases and the envelope share: the envelope's own when it has one."""
        envelope = self._envelope
        return envelope.clock() if envelope is not None else self._clock_ms()

    def _require_motion(self, called_from: str, primitive: str) -> MotionController:
        if self._motion is None:
            board = self.board
            raise BoardCapabilityError(
                where=f"{called_from} -> {primitive}",
                why=(
                    f"board {board.id!r} declares no motion channel"
                    if board is not None and not board.motion_channels
                    else "no motion channel is set up on this HAL: a linux session brings up the "
                    "channels its [requires] names, and LinuxHAL(motion=[...]) does it directly"
                    if board is not None and self.target == "linux"
                    else f"motion.* is not implemented on target {self.target!r} yet"
                ),
                how="use a board that declares `[capabilities.motion]` (linux-rpi5, sim-rpi5); "
                "see docs/spec/simulation_coverage.md",
            )
        if self._envelope is None:
            ensure_envelope(self, self._clock_ms)  # a channel is always an actuator
        return self._motion

    def motion_motor(
        self,
        channel: str,
        speed: float,
        direction: str = "forward",
        ramp_ms: int | None = None,
        signature: Any = "",
        called_from: str = "<unknown>",
    ) -> MotionLease:
        """
        Command a motor channel: `speed` (0..`speed_max` of the board), `direction`, `ramp_ms`
        (at least `ramp_min_ms`). Checked in this order: the channel exists and is a motor, the
        board's limits, the safety envelope (a run's start), then the proof — a lease from the
        verdict token (RFC-0011 §3b, §3c). A command moves the motor only until its lease runs
        out; the next command, a fresh gate pass, renews it.
        """
        controller = self._require_motion(called_from, "motion.motor")
        return controller.motor(
            channel, speed, direction, ramp_ms, signature=signature, called_from=called_from
        )

    def motion_servo(
        self,
        channel: str,
        target: float,
        speed_max: float | None = None,
        signature: Any = "",
        called_from: str = "<unknown>",
    ) -> MotionLease:
        """Command a servo channel to `target` (inside the board's range), at most `speed_max`."""
        controller = self._require_motion(called_from, "motion.servo")
        return controller.servo(
            channel, target, speed_max, signature=signature, called_from=called_from
        )

    def motion_stop(self, channel: str, called_from: str = "<unknown>") -> None:
        """A command toward the safe state: never refused, needs no token, no envelope, no ramp."""
        self._require_motion(called_from, "motion.stop").safe(
            channel, "stop", called_from=called_from
        )

    def motion_safe(self, channel: str, cause: str, called_from: str = "<unknown>") -> None:
        """
        The HAL's own command toward the safe state, for a `cause` (a BLOCK, a lost link, the
        end of a session). A channel the board does not have is none of its business: ignored.
        """
        if self._motion is not None and self._motion.covers(channel):
            self._motion.safe(channel, cause, called_from=called_from)

    def motion_barge_in(self) -> list[str]:
        """The user spoke over the agent (voice_fsm.md §5.2): every moving channel goes safe now."""
        return [] if self._motion is None else self._motion.barge_in()

    def motion_values(self) -> dict[str, dict[str, Any]]:
        """Every channel as a person sees it: mode, setpoint, lease left, what the actuator does."""
        if self._motion is None:
            return {}
        return {name: self._motion.describe(name) for name in self._motion.names}

    def settle_motion(self) -> None:
        """A tick of the clock: leases, holds and runs that are over end (their causes recorded)."""
        if self._motion is not None:
            self._motion.settle()

    # -- digital.in (RFC-0007 §3a) -------------------------------------------------------
    # `SimHAL` and `LinuxHAL` set the event sink; the clock of an `EventLog` is the clock the
    # gate ages a reading by, so a HAL with another sink still marks reads on its own clock.
    events: Any = None

    def _clock_ms(self) -> float:
        clock = getattr(self.events, "clock", None)
        return clock() if callable(clock) else _monotonic_ms()

    def digital_in(self, pin: str, called_from: str = "<unknown>", use: str | None = None) -> bool:
        """
        The logic level of an input line: True is the line high. Reading moves nothing, so it
        needs no token (as `sensor.read`), and every read is a `digital_in` event. A read that
        fails raises `PerceptionUnavailableError` (NE5001), never a level. `use="fact"` marks a
        read made to compute a gate fact rather than by an action.
        """
        return self.digital_reading(pin, called_from, use).value

    def digital_reading(
        self, pin: str, called_from: str = "<unknown>", use: str | None = None
    ) -> DigitalReading:
        """`digital_in()` with the read mark the gate ages the level by."""
        if self.board is not None:
            self.board.require_input_pin(pin, called_from=called_from)
        where = f"{called_from} -> digital.in {pin!r}"
        read_ms = self._clock_ms()
        try:
            queue = self._replayed_levels.get(pin)
            if queue is not None:
                level = self._next_replayed_level(pin, queue, where)
            else:
                level = self._read_level(pin, where)
            if not isinstance(level, bool):
                raise PerceptionUnavailableError(
                    where=where,
                    why=f"the line gave {level!r}, not a logic level",
                    how="check the wiring of the input, or the backend that reads it",
                )
        except PerceptionUnavailableError as error:
            self._emit_digital_in({"pin": pin, "reason": error.why}, use)
            raise
        self._emit_digital_in({"pin": pin, "value": level}, use)
        return DigitalReading(level, read_ms)

    def _emit_digital_in(self, data: dict[str, Any], use: str | None) -> None:
        if use is not None:
            data["use"] = use
        if self.events is not None:
            self.events.emit("digital_in", data)

    def _read_level(self, pin: str, where: str) -> bool:
        """The target's own read of a declared input line; a read that fails raises NE5001."""
        raise BoardCapabilityError(
            where=where,
            why=f"digital.in is not implemented on target {self.target!r} yet",
            how="see docs/spec/simulation_coverage.md for the task that adds it; `sim` and `linux` have it",
        )

    def script_digital_in(self, pin: str, values: Iterable[bool | None]) -> None:
        """
        Levels returned in order, one per read, instead of the line's own — how replay feeds a
        recorded session back; a None is a read that failed when it was recorded. Reading past
        the last one is a failed read, never the last level again.
        """
        if self.board is not None:
            self.board.require_input_pin(
                pin, called_from=f"{type(self).__name__}.script_digital_in()"
            )
        self._replayed_levels[pin] = deque(values)

    @staticmethod
    def _next_replayed_level(pin: str, queue: deque[bool | None], where: str) -> bool:
        level = queue.popleft() if queue else None
        if level is None:
            raise PerceptionUnavailableError(
                where=where,
                why="the trace being replayed holds no reading of this line here (it had failed, or ended)",
                how="replay a trace recorded with its digital_in events",
            )
        return level

    # -- state() of a digital.out pin (RFC-0010 §3b, §9.4) ---------------------------------
    def pin_state(
        self, pin: str, called_from: str = "<unknown>", use: str | None = None
    ) -> PinState:
        """
        The state of a PWM channel: `duty` and `frequency_hz`, each with the `source` of the
        numbers. A pin the board lists in `digital_out.feedback.pins` is read back from the
        hardware (`measured`); any other is what the HAL last commanded (`commanded`). A
        read-back that fails raises `PerceptionUnavailableError` (NE5001) and never returns the
        commanded value in its place. Reading moves nothing, so it needs no token, and every
        read is a `pin_state` event (`use="fact"`: a read made to compute a gate fact).
        """
        if self.board is not None:
            self.board.require_pin(pin, called_from=called_from)
        where = f"{called_from} -> digital.out {pin!r} state()"
        limits = None if self.board is None else pwm_limits(self.board, pin)
        if limits is None:
            raise BoardCapabilityError(
                where=where,
                why=f"{pin!r} is not a PWM channel; state() reads back the duty and frequency of a "
                "PWM channel (RFC-0010 §3b)",
                how="use a pin listed in [capabilities.digital_out.pwm].pins",
            )
        read_ms = self._clock_ms()
        try:
            queue = self._replayed_states.get(pin)
            if queue is not None:
                state = self._next_replayed_state(pin, queue, where, read_ms)
            elif pin in self.board.capabilities["digital_out"].get("feedback", {}).get("pins", ()):
                state = PinState(pin, MEASURED, self._read_feedback(pin, limits, where), read_ms)
            else:
                run = self.commanded_pwm(pin)
                values = {
                    "duty": 0.0 if run is None else run[1],
                    "frequency_hz": None if run is None else float(run[0]),
                }
                state = PinState(pin, COMMANDED, values, read_ms)
        except PerceptionUnavailableError as error:
            self._emit("pin_state", pin_state_data(pin, reason=error.why, use=use))
            raise
        self._emit("pin_state", pin_state_data(pin, state, use=use))
        return state

    def _read_feedback(self, pin: str, limits: Any, where: str) -> dict[str, float | None]:
        """The target's own read-back of a channel in `feedback.pins`; a read that fails raises NE5001."""
        raise BoardCapabilityError(
            where=where,
            why=f"the read-back of a PWM channel is not implemented on target {self.target!r} yet",
            how="see docs/spec/simulation_coverage.md; `sim` and `linux` have it",
        )

    def script_pin_state(self, pin: str, entries: Iterable[dict[str, Any] | None]) -> None:
        """
        States returned in order, one per `state()`, instead of the hardware's — how replay
        feeds a recorded session back, `source` included. A None is a read that failed when it
        was recorded; reading past the last is a failed read.
        """
        if self.board is not None:
            self.board.require_pin(pin, called_from=f"{type(self).__name__}.script_pin_state()")
        self._replayed_states[pin] = deque(entries)

    @staticmethod
    def _next_replayed_state(
        pin: str, queue: deque[dict[str, Any] | None], where: str, read_ms: float
    ) -> PinState:
        entry = queue.popleft() if queue else None
        if entry is None:
            raise PerceptionUnavailableError(
                where=where,
                why="the trace being replayed holds no state of this channel here (it had failed, or ended)",
                how="replay a trace recorded with its pin_state events",
            )
        values = {k: entry.get(k) for k in ("duty", "frequency_hz")}
        return PinState(pin, str(entry.get("source", COMMANDED)), values, read_ms)

    def _not_on_target(self, primitive: str, called_from: str) -> None:
        raise BoardCapabilityError(
            where=f"{called_from} -> {primitive}",
            why=f"{primitive} is not implemented on target {self.target!r} yet",
            how="see docs/spec/simulation_coverage.md for the task that adds it; `sim` has it",
        )

    def sensor_read(self, sensor: str, called_from: str = "<unknown>") -> Any:
        self._not_on_target("sensor.read", called_from)

    def analog_in(
        self, channel: str, called_from: str = "<unknown>", use: str | None = None
    ) -> float:
        """One reading of an `analog.in` channel, in the unit the board declares (RFC-0007 §3c)."""
        self._not_on_target("analog.in", called_from)

    def display(self, frame: Any, *, called_from: str = "<unknown>", **_: Any) -> Any:
        self._not_on_target("display", called_from)

    # -- i2c (RFC-0007 §3b): read-only; there is no method that writes data ----------
    def i2c_read(
        self,
        bus: str,
        device: str | int,
        register: int | None = None,
        *,
        width: int = 1,
        called_from: str = "<unknown>",
    ) -> int:
        """A receive byte, or a declared register (`width` 1 or 2 bytes), of an allow-listed device."""
        self._not_on_target("i2c", called_from)

    def i2c_scan(self, bus: str, called_from: str = "<unknown>") -> list[Any]:
        """The addresses that answer a read-byte probe, tagged with their allow-list name or None."""
        self._not_on_target("i2c", called_from)

    # -- audio: the signatures `SimHAL` and `LinuxHAL` implement -------------------
    def audio_in(self, called_from: str = "<unknown>") -> str | None:
        """One typed utterance, or None when nothing is queued (the text input of `sim`)."""
        self._not_on_target("audio.in", called_from)

    def audio_out(self, text: str, called_from: str = "<unknown>") -> None:
        """Say `text` (the text output of `sim`)."""
        self._not_on_target("audio.out", called_from)

    def audio_file(self, path: Any, called_from: str = "<unknown>") -> "WavSource":
        """A WAV file as `audio.in`: PCM frames from a file, never a microphone."""
        self._not_on_target("audio.in", called_from)

    def audio_source(self, called_from: str = "<unknown>") -> "LiveAudioIn":
        """The live capture device as `audio.in`."""
        self._not_on_target("audio.in", called_from)

    def audio_sink(self, called_from: str = "<unknown>") -> "LiveAudioOut":
        """The live playback device as `audio.out`."""
        self._not_on_target("audio.out", called_from)

    def speaker(self, called_from: str = "<unknown>") -> Any:
        """`audio.out` as a timeline at the board's rate (`play`, `stop`, `render`, `write`)."""
        self._not_on_target("audio.out", called_from)

    def pin(self, name: str) -> PinAssertion:
        """
        Observed state of a pin. A name the board does not declare raises, so a
        misspelled assertion can never pass as "never pulsed" (CEO-S5-2).
        """
        if self.board is not None:
            self.board.require_pin(name, called_from="hal.pin()")
        return self.pins.get(name, PinAssertion(name, pulsed=False))

    # -- vision.in (extension primitive, RFC-0012) -----------------------------------
    def vision_in(
        self,
        mode: "Mode",
        called_from: str = "<unknown>",
        *,
        clock: Callable[[], float] | None = None,
    ) -> "Camera":
        """
        The camera, running in `mode` — one of the modes the board declares in `vision_in`
        (`hal/vision.py`) — stamping frames with `clock` (the session's: `Fact.read_ms` is on
        it too). Frames come from `Camera.read_available()`; a camera that cannot deliver
        raises `CameraUnavailable`, it never invents a frame.
        """
        self._not_on_target("vision.in", called_from)


def ensure_envelope(hal: Any, clock: Callable[[], float], *, virtual: bool | None = None) -> None:
    """
    Give a HAL the envelope its board declares, unless one is installed already (a session
    installs its own, with the durable record on `linux`). `Conversation` calls this next to
    installing the token ledger, so a HAL driven through `c.do()` is bounded by its board
    whoever built it. `clock` is the session's, in milliseconds. On `sim` the envelope ends
    an on-time by itself at its deadline (there is no timer); anywhere else the HAL ends it
    — unless `virtual` says otherwise (replay decides by recorded time on every target).
    """
    if not isinstance(hal, HardwareAbstractionLayer) or hal.envelope is not None:
        return
    if hal.board is None:
        return
    envelope = SafetyEnvelope.for_board(
        hal.board, clock=clock, virtual=hal.target == "sim" if virtual is None else virtual
    )
    if envelope.names:
        hal.envelope = envelope
