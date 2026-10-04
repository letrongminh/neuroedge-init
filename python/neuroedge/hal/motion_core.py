"""
`motion.*` at run time (RFC-0011, TSK-I2a-05): channels, leases, runs and the safe state.

A channel is a motor or a servo the board declares (`board.v1` `capabilities.motion`). A
command moves it only while its **lease** is valid: the verdict token of the gate pass that
allowed it carries the lease (`TokenLedger`), and the lease runs out `lease_ms` after the
verdict. Nothing but a fresh gate pass renews it — never the HAL by itself — so a channel
nobody keeps commanding goes to its declared safe state (`stop`, or `hold` for a servo that
holds its position, for at most `max_hold_ms`).

**A run is a chain of leases.** The first command on an idle channel starts a run: the
envelope reserves `max_continuous_ms` for the whole run (`min_interval_ms` is checked here and
only here), and every command that arrives before the lease runs out renews the run without
asking the envelope again. The run ends — the channel is in its safe state, the unused part of
the reservation goes back to the window — when the lease lapses, when `max_continuous_ms` is
over, or on any of the causes below.

**Toward the safe state nothing is ever refused** (RFC-0011 §3d, §9 item 7). `safe()` needs no
token, no gate verdict and no envelope check, and waits for no ramp: lease expiry, the end of
`max_continuous_ms` or `max_hold_ms`, a barge-in, a BLOCK of a command for the channel, a
lost link, `close()`, an agent's `stop`. It is the one exception to "no command reaches the
hardware without an ALLOW", and every one is recorded as `motion_safe` with its cause.

The controller is the shared logic of `sim` and `linux`; the **actuator** behind it is the
target: `SimActuator` is a model with a ramp (position and speed, visible in the REPL and
`--ui`), `hal/motion_pwm.py` drives hardware PWM and the enable line on `linux`. Time is the
injected clock in milliseconds, never the wall clock, so a replay decides by recorded time.

What is not modelled, on purpose: a motor direction. `board.v1` gives a motor channel no
direction line, so `reverse` is refused on every target until a board can declare one (it
needs an RFC); `sim` is no richer than the reference board.
"""

from __future__ import annotations

import math
import threading
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

from ..errors import BoardCapabilityError, EnvelopeRefusedError

if TYPE_CHECKING:
    from .envelope import Reservation

__all__ = [
    "DEFAULT_LEASE_MS",
    "Channel",
    "MotionController",
    "MotionLease",
    "SimActuator",
    "Setpoint",
    "lease_ms_of",
]

DEFAULT_LEASE_MS = 200
STOP, HOLD = "stop", "hold"
FORWARD = "forward"
# The causes after which a channel is stopped even if it declares `hold`: the energy budget
# (`max_continuous_ms`), the end of the hold itself, the session going away, a supervisor that
# dropped the driver, an actuator that stopped answering. Any other cause leaves a holding servo holding.
STOP_CAUSES = frozenset(
    {
        "close",
        "max_continuous_ms",
        "max_hold_ms",
        "supervisor_deadline",
        "supervisor_heartbeat",
        "actuator_fault",
    }
)
IDLE, ACTIVE, HOLDING = "idle", "active", "holding"


@dataclass(frozen=True)
class Channel:
    """One motor or servo, as `board.v1` declares it (`BoardProfile.motion_channels`)."""

    name: str
    kind: str  # "motor" | "servo"
    enable_pin: str
    safe_state: str = STOP
    lease_ms: int = DEFAULT_LEASE_MS
    speed_max: float | None = None
    ramp_min_ms: int = 0
    target_min: float | None = None
    target_max: float | None = None
    unit: str | None = None
    holds_position: bool = False
    max_hold_ms: int | None = None

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> Channel:
        return cls(
            name=record["name"],
            kind=record["kind"],
            enable_pin=record["enable_pin"],
            safe_state=record.get("safe_state", STOP),  # not declared => stop (Q-35)
            lease_ms=int(record.get("lease_ms", DEFAULT_LEASE_MS)),
            speed_max=record.get("speed_max"),
            ramp_min_ms=int(record.get("ramp_min_ms", 0)),
            target_min=record.get("target_min"),
            target_max=record.get("target_max"),
            unit=record.get("unit"),
            holds_position=bool(record.get("holds_position", False)),
            max_hold_ms=record.get("max_hold_ms"),
        )

    @property
    def holds(self) -> bool:
        """The declared safe state is a hold, and the channel is one that can hold."""
        return (
            self.safe_state == HOLD
            and self.kind == "servo"
            and self.holds_position
            and self.max_hold_ms is not None
        )


def lease_ms_of(board: Any, channel: str) -> int:
    """The lease of a channel on `board`: its declared `lease_ms`, else the default 200 ms."""
    if board is not None:
        for record in board.motion_channels:
            if record["name"] == channel:
                return int(record.get("lease_ms", DEFAULT_LEASE_MS))
    return DEFAULT_LEASE_MS


@dataclass(frozen=True)
class Setpoint:
    """What a command asks of a channel: a motor's speed and ramp, a servo's target and slew."""

    speed: float = 0.0
    ramp_ms: int = 0
    target: float | None = None
    slew: float | None = None  # units per second; None = as fast as the servo goes


@dataclass(frozen=True)
class MotionLease:
    """What a command returns: the run it belongs to and the lease it holds."""

    channel: str
    run: str  # "new" | "renewed"
    expires_ms: float


class Actuator(Protocol):
    """The target's end of a channel. Raises `OSError` when the hardware did not move."""

    def drive(
        self, channel: Channel, setpoint: Setpoint, now_ms: float, limit_ms: float
    ) -> None: ...

    def safe(self, channel: Channel, state: str, now_ms: float, limit_ms: float) -> None: ...

    def snapshot(self, channel: Channel, now_ms: float) -> dict[str, Any]: ...

    def close(self) -> None: ...


# -- the simulated actuator ------------------------------------------------------------


@dataclass
class _Model:
    enabled: bool = False
    # motor: speed ramps linearly from `from_value` to `to_value` over `ramp_ms` after `t0`
    from_value: float = 0.0
    to_value: float = 0.0
    t0: float = 0.0
    ramp_ms: float = 0.0
    distance: float = 0.0  # motor: the integral of speed (speed-seconds), servo: unused
    # servo: the position moves from `from_value` to `to_value` at `slew` units per second
    slew: float | None = None

    def value_at(self, now: float) -> float:
        if self.ramp_ms <= 0 and self.slew is None:
            return self.to_value
        if self.slew is not None:  # servo
            span = abs(self.to_value - self.from_value)
            travelled = max(0.0, now - self.t0) / 1000.0 * self.slew
            if travelled >= span:
                return self.to_value
            return self.from_value + math.copysign(travelled, self.to_value - self.from_value)
        elapsed = now - self.t0
        if elapsed >= self.ramp_ms:
            return self.to_value
        if elapsed <= 0:
            return self.from_value
        return self.from_value + (self.to_value - self.from_value) * elapsed / self.ramp_ms

    def distance_at(self, now: float) -> float:
        """Motor: the integral of the speed up to `now`, in speed-seconds."""
        elapsed = max(0.0, now - self.t0)
        ramp = min(elapsed, self.ramp_ms) if self.ramp_ms > 0 else 0.0
        slope = (self.to_value - self.from_value) / self.ramp_ms if self.ramp_ms > 0 else 0.0
        during = self.from_value * ramp + slope * ramp * ramp / 2
        after = self.to_value * (elapsed - ramp)
        return self.distance + (during + after) / 1000.0


class SimActuator:
    """
    A model of the actuators with a ramp, on the session's virtual clock — no richer than the
    board declares: a motor's speed goes to the commanded value over `ramp_ms` and an `off`
    (`safe`) is instant; a servo moves to its target at the commanded slew and a `hold` keeps
    it where it is, powered. `snapshot()` is what the REPL and the page show.
    """

    def __init__(self) -> None:
        self._models: dict[str, _Model] = {}

    def _model(self, channel: Channel) -> _Model:
        model = self._models.get(channel.name)
        if model is None:
            # A servo is somewhere before its first command: at the low end of its range.
            start = float(channel.target_min or 0.0) if channel.kind == "servo" else 0.0
            model = self._models[channel.name] = _Model(from_value=start, to_value=start)
        return model

    def drive(self, channel: Channel, setpoint: Setpoint, now_ms: float, limit_ms: float) -> None:
        model = self._model(channel)
        if channel.kind == "motor":
            model.distance = model.distance_at(now_ms)
            model.from_value = model.value_at(now_ms)
            model.to_value = float(setpoint.speed)
            model.ramp_ms = float(setpoint.ramp_ms)
            model.slew = None
        else:
            model.from_value = model.value_at(now_ms) if model.enabled else model.to_value
            model.to_value = float(setpoint.target if setpoint.target is not None else 0.0)
            model.slew = setpoint.slew
            model.ramp_ms = 0.0
        model.t0 = now_ms
        model.enabled = True

    def safe(self, channel: Channel, state: str, now_ms: float, limit_ms: float) -> None:
        model = self._model(channel)
        if channel.kind == "motor":
            model.distance = model.distance_at(now_ms)
            model.from_value = model.to_value = 0.0
            model.ramp_ms = 0.0
            model.t0 = now_ms
            model.enabled = False
        elif state == HOLD:
            here = model.value_at(now_ms)
            model.from_value = model.to_value = here
            model.slew = None
            model.t0 = now_ms
            model.enabled = True
        else:  # a stopped servo is unpowered: it stays where it was
            here = model.value_at(now_ms)
            model.from_value = model.to_value = here
            model.slew = None
            model.t0 = now_ms
            model.enabled = False

    def snapshot(self, channel: Channel, now_ms: float) -> dict[str, Any]:
        model = self._model(channel)
        if channel.kind == "motor":
            return {
                "enabled": model.enabled,
                "speed": round(model.value_at(now_ms), 6),
                "distance": round(model.distance_at(now_ms), 6),
            }
        return {"enabled": model.enabled, "position": round(model.value_at(now_ms), 6)}

    def close(self) -> None:
        return None


# -- the controller ----------------------------------------------------------------------


@dataclass
class _State:
    channel: Channel
    mode: str = IDLE
    reservation: Reservation | None = None
    lease_expires: float = 0.0
    hold_until: float = 0.0
    setpoint: Setpoint | None = None
    commands: int = 0  # how many commands this run has taken: leases chained


@dataclass
class MotionController:
    """
    The channels of one HAL. `hal` supplies the pieces that are installed from outside — the
    `authorize` check (set by `Conversation`), the envelope, the event sink — read at the moment
    of use, so a controller built with the HAL sees what `Conversation` installs later.
    """

    hal: Any
    channels: Iterable[Channel]
    actuator: Actuator
    clock: Callable[[], float]
    # Called after any change to the next deadline (a lease, a hold, a run's end), with that
    # deadline in clock ms or None: `linux` arms a timer here, `sim` is ticked by its clock.
    on_deadline: Callable[[float | None], None] | None = None
    # How long the driver stays powered beyond a lease: the runtime's own timers win, and the
    # supervisor drops the enable line at this backstop if the runtime is frozen.
    margin_ms: float = 250.0
    _states: dict[str, _State] = field(default_factory=dict, init=False)
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)
    # While a command is being driven, a safe-state request that arrives from inside it (the
    # supervisor reporting a drop on the reply to our own `set`) waits for the command to
    # finish: the channel then goes safe as a fact of the record, not half-way through it.
    _driving: bool = field(default=False, init=False)
    _deferred: list[tuple[str, str]] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self._states = {c.name: _State(c) for c in self.channels}

    # -- what the controller knows ----------------------------------------------------
    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self._states)

    def channel(self, name: str) -> Channel:
        return self._states[name].channel

    def covers(self, name: str) -> bool:
        return name in self._states

    def require(self, name: str, kind: str | None, called_from: str, primitive: str) -> Channel:
        """The channel `name` (of `kind`, if given), or the refusal a stranger gets."""
        state = self._states.get(name)
        if state is None or (kind is not None and state.channel.kind != kind):
            board = getattr(self.hal, "board", None)
            of_kind = sorted(n for n, s in self._states.items() if kind in (None, s.channel.kind))
            raise BoardCapabilityError(
                where=f"{called_from} -> {primitive} {name!r}",
                why=(
                    f"board {getattr(board, 'id', '?')!r} declares no motion {kind or 'channel'} "
                    f"named {name!r}; it offers {of_kind or 'none'}"
                    + (
                        f" ({name!r} is a {state.channel.kind})"
                        if state is not None and kind is not None
                        else ""
                    )
                ),
                how="use a declared channel of that kind: motion.motor for a motor, "
                "motion.servo for a servo",
            )
        return state.channel

    # -- limits of the board (checked before the envelope and the proof) ----------------
    def _motor_setpoint(
        self, channel: Channel, speed: Any, direction: Any, ramp_ms: Any, where: str
    ) -> Setpoint:
        limit = float(channel.speed_max or 0.0)
        if not _real(speed) or not 0 <= speed <= limit:
            raise self._limit(
                where,
                f"speed {speed!r} is outside 0..{limit:g}, the board's speed_max of "
                f"{channel.name!r}",
                f"command a speed from 0 to {limit:g}",
            )
        if direction != FORWARD:
            raise self._limit(
                where,
                f"direction {direction!r} is not supported: board.v1 gives a motor channel no "
                "direction line, so only 'forward' exists on every target (RFC-0011 §3a)",
                "command 'forward', or ask for a board that declares a direction line",
            )
        ramp = channel.ramp_min_ms if ramp_ms is None else ramp_ms
        if not _real(ramp) or (isinstance(ramp, float) and not ramp.is_integer()):
            raise self._limit(
                where, f"ramp_ms {ramp_ms!r} is not a whole number of ms", "pass ramp_ms as an int"
            )
        if ramp < channel.ramp_min_ms:
            raise self._limit(
                where,
                f"ramp_ms {ramp} is below ramp_min_ms {channel.ramp_min_ms} of {channel.name!r}",
                f"ramp over at least {channel.ramp_min_ms} ms",
            )
        return Setpoint(speed=float(speed), ramp_ms=int(ramp))

    def _servo_setpoint(
        self, channel: Channel, target: Any, speed_max: Any, where: str
    ) -> Setpoint:
        low, high = float(channel.target_min), float(channel.target_max)  # type: ignore[arg-type]
        if not _real(target) or not low <= target <= high:
            raise self._limit(
                where,
                f"target {target!r} is outside {low:g}..{high:g} {channel.unit}, the board's "
                f"range of {channel.name!r}",
                f"command a target from {low:g} to {high:g}",
            )
        if speed_max is not None and (not _real(speed_max) or speed_max <= 0):
            raise self._limit(
                where,
                f"speed_max {speed_max!r} is not a positive number",
                f"pass speed_max in {channel.unit} per second, or omit it",
            )
        return Setpoint(target=float(target), slew=None if speed_max is None else float(speed_max))

    @staticmethod
    def _limit(where: str, why: str, how: str) -> BoardCapabilityError:
        return BoardCapabilityError(where=where, why=why, how=how)

    # -- commands (the path that needs a proof) -------------------------------------------
    def motor(
        self,
        name: str,
        speed: Any,
        direction: Any = FORWARD,
        ramp_ms: Any = None,
        *,
        signature: Any = "",
        called_from: str = "<unknown>",
    ) -> MotionLease:
        channel = self.require(name, "motor", called_from, "motion.motor")
        where = f"{called_from} -> motion.motor {name!r}"
        setpoint = self._motor_setpoint(channel, speed, direction, ramp_ms, where)
        event = {
            "kind": "motor",
            "speed": setpoint.speed,
            "direction": FORWARD,
            "ramp_ms": setpoint.ramp_ms,
        }
        return self._command(channel, setpoint, event, signature, called_from)

    def servo(
        self,
        name: str,
        target: Any,
        speed_max: Any = None,
        *,
        signature: Any = "",
        called_from: str = "<unknown>",
    ) -> MotionLease:
        channel = self.require(name, "servo", called_from, "motion.servo")
        where = f"{called_from} -> motion.servo {name!r}"
        setpoint = self._servo_setpoint(channel, target, speed_max, where)
        event: dict[str, Any] = {"kind": "servo", "target": setpoint.target}
        if setpoint.slew is not None:
            event["speed_max"] = setpoint.slew
        return self._command(channel, setpoint, event, signature, called_from)

    def _command(
        self,
        channel: Channel,
        setpoint: Setpoint,
        event: dict[str, Any],
        signature: Any,
        called_from: str,
    ) -> MotionLease:
        """require_channel -> board limits (done) -> envelope -> authorize -> drive -> record."""
        hal = self.hal
        with self._lock:
            now = self.clock()
            self._settle(now)
            state = self._states[channel.name]
            envelope = hal.envelope
            reservation: Reservation | None = None
            new_run = state.mode == IDLE
            if new_run and envelope is not None:
                try:
                    reservation = envelope.reserve(
                        channel.name,
                        0,
                        operation="run",
                        called_from=called_from,
                        primitive="motion",
                    )
                except EnvelopeRefusedError as refusal:
                    hal._emit("envelope_refused", refusal.event)
                    raise
            try:
                remaining = hal.authorize(signature, channel.name, called_from)
            except BaseException:
                if reservation is not None and envelope is not None:
                    envelope.refund(reservation)
                raise
            lease_ms = (
                float(remaining)
                if isinstance(remaining, int | float) and not isinstance(remaining, bool)
                else float(channel.lease_ms)
            )
            expires = now + lease_ms
            run_end = (
                reservation.deadline_ms
                if reservation is not None
                else (state.reservation.deadline_ms if state.reservation is not None else math.inf)
            )
            powered_until = min(expires, run_end) + self.margin_ms
            self._driving = True
            try:
                self.actuator.drive(channel, setpoint, now, powered_until - now)
            except BaseException:
                self._driving = False
                self._deferred.clear()
                # The driver did not move as asked. It is told to stop; the reservation goes
                # back only once it is known to be down — otherwise it stays, the safe side
                # of not knowing.
                try:
                    self.actuator.safe(channel, STOP, now, 0.0)
                except BaseException:
                    pass
                else:
                    if reservation is not None and envelope is not None:
                        envelope.refund(reservation)
                    if not new_run:  # the run that was going is over, and the record says why
                        self._end_run(state, now)
                        hal._emit(
                            "motion_safe",
                            {"channel": channel.name, "state": STOP, "cause": "actuator_fault"},
                        )
                raise
            self._driving = False
            if new_run:
                state.reservation, state.commands = reservation, 0
            state.mode = ACTIVE
            state.lease_expires = expires
            state.setpoint = setpoint
            state.commands += 1
            hal._emit(
                "motion_command",
                {
                    "channel": channel.name,
                    **event,
                    "lease_ms": int(lease_ms),
                    "run": "new" if new_run else "renewed",
                },
            )
            deferred, self._deferred = self._deferred, []
            for name, cause in deferred:  # see `_driving`
                self._to_safe(self._states[name], cause, self.clock())
            self._arm()
            return MotionLease(channel.name, "new" if new_run else "renewed", expires)

    # -- toward the safe state: never refused ---------------------------------------------
    def safe(self, name: str, cause: str, *, called_from: str = "<unknown>") -> None:
        """Send `name` to its declared safe state now. No proof, no envelope, no ramp."""
        self.require(name, None, called_from, "motion")  # a stranger is refused
        with self._lock:
            if self._driving:
                self._deferred.append((name, cause))
                return
            self._to_safe(self._states[name], cause, self.clock())
            self._arm()

    def safe_all(self, cause: str) -> list[str]:
        """Every channel that moves or holds goes to its safe state; the channels it was."""
        sent: list[str] = []
        errors: list[BaseException] = []
        with self._lock:
            now = self.clock()
            for state in self._states.values():
                if state.mode == IDLE:
                    continue
                try:
                    self._to_safe(state, cause, now)
                except BaseException as exc:  # one that will not stop must not hide the others
                    errors.append(exc)
                else:
                    sent.append(state.channel.name)
            self._arm()
        if errors:
            raise errors[0]
        return sent

    def barge_in(self) -> list[str]:
        """The user spoke over the agent: every moving channel goes to its safe state at once."""
        return self.safe_all("barge_in")

    def close(self) -> None:
        """The HAL is closing: every channel stops, whatever it declares, and the driver goes."""
        errors: list[BaseException] = []
        try:
            self.safe_all("close")
        except BaseException as exc:
            errors.append(exc)
        try:
            self.actuator.close()
        except BaseException as exc:
            errors.append(exc)
        if errors:
            raise errors[0]

    def _to_safe(self, state: _State, cause: str, when: float) -> None:
        """`state` goes to its safe state as of `when` (the instant it was due, or now)."""
        channel = state.channel
        if state.mode == IDLE:
            return
        if state.mode == HOLDING and cause not in STOP_CAUSES:
            return  # already in the safe state it declares
        hold = state.mode == ACTIVE and channel.holds and cause not in STOP_CAUSES
        if hold:
            end = when + float(channel.max_hold_ms or 0)
            if state.reservation is not None:
                end = min(end, state.reservation.deadline_ms)
            self.actuator.safe(channel, HOLD, when, max(0.0, end - when) + self.margin_ms)
            state.mode, state.hold_until, state.setpoint = HOLDING, end, None
            self.hal._emit("motion_safe", {"channel": channel.name, "state": HOLD, "cause": cause})
            return
        self.actuator.safe(channel, STOP, when, 0.0)
        self._end_run(state, when)
        self.hal._emit("motion_safe", {"channel": channel.name, "state": STOP, "cause": cause})

    def _end_run(self, state: _State, when: float) -> None:
        envelope = self.hal.envelope
        if state.reservation is not None and envelope is not None:
            envelope.ended(state.channel.name, state.reservation, at=when)
        state.mode, state.reservation, state.setpoint = IDLE, None, None

    # -- time -----------------------------------------------------------------------------
    def settle(self) -> None:
        """Let every lease, hold and run whose time has come on the clock end (the clock ticked)."""
        with self._lock:
            self._settle(self.clock())
            self._arm()

    def _settle(self, now: float) -> None:
        errors: list[BaseException] = []
        for state in self._states.values():
            try:
                # More than one thing can have come due between two ticks (a lease, then the end
                # of the hold it began): take them in order until the channel is where it is.
                while state.mode != IDLE:
                    res = state.reservation
                    # The channel went safe when its time came, not when somebody looked: the
                    # actuator is told that instant (a model freezes where it was then).
                    if res is not None and res.deadline_ms <= now:
                        self._to_safe(state, "max_continuous_ms", res.deadline_ms)
                    elif state.mode == ACTIVE and state.lease_expires <= now:
                        self._to_safe(state, "lease_expired", state.lease_expires)
                    elif state.mode == HOLDING and state.hold_until <= now:
                        self._to_safe(state, "max_hold_ms", state.hold_until)
                    else:
                        break
            except BaseException as exc:
                errors.append(exc)
        if errors:
            raise errors[0]

    def next_deadline_ms(self) -> float | None:
        """When `settle()` next has something to do, in clock ms, or None when nothing moves."""
        with self._lock:
            due: list[float] = []
            for state in self._states.values():
                if state.mode == IDLE:
                    continue
                if state.reservation is not None:
                    due.append(state.reservation.deadline_ms)
                due.append(state.lease_expires if state.mode == ACTIVE else state.hold_until)
            return min(due) if due else None

    def _arm(self) -> None:
        if self.on_deadline is not None:
            self.on_deadline(self.next_deadline_ms())

    # -- what a person sees -------------------------------------------------------------------
    def describe(self, name: str) -> dict[str, Any]:
        """The channel now: its mode, the setpoint, the lease left, and what the actuator reports."""
        with self._lock:
            now = self.clock()
            self._settle(now)  # a lease that ran out is not shown as running
            state = self._states[name]
            channel = state.channel
            info: dict[str, Any] = {
                "kind": channel.kind,
                "mode": state.mode,
                "safe_state": channel.safe_state,
                "lease_ms": channel.lease_ms,
            }
            if state.mode == ACTIVE:
                info["lease_left_ms"] = max(0, int(state.lease_expires - now))
            elif state.mode == HOLDING:
                info["hold_left_ms"] = max(0, int(state.hold_until - now))
            if state.setpoint is not None:
                info["setpoint"] = {
                    k: v
                    for k, v in {
                        "speed": state.setpoint.speed if channel.kind == "motor" else None,
                        "ramp_ms": state.setpoint.ramp_ms if channel.kind == "motor" else None,
                        "target": state.setpoint.target,
                        "speed_max": state.setpoint.slew,
                    }.items()
                    if v is not None
                }
            info.update(self.actuator.snapshot(channel, now))
            return info


def _real(value: Any) -> bool:
    """A finite number that is not a bool (a bool is an int to Python, not a speed)."""
    return isinstance(value, int | float) and not isinstance(value, bool) and math.isfinite(value)
