"""
The `linux` end of a motion channel: a hardware PWM channel and the driver's enable line
(RFC-0011 §3a, TSK-I2a-05).

A motor is a PWM duty (its speed, 0..1) behind a driver with an **enable line**; a servo is a
pulse of 1000–2000 µs in a 20 ms period (its target across the declared range) behind a
driver with one too. The enable line is the HAL's, never an agent's (`BoardProfile.require_pin`
refuses it), and it is held by the **supervisor process** with a deadline — the end of the
lease plus a margin — so a runtime that freezes or dies leaves the driver unpowered whatever the
PWM was left at (RFC-0007 §3d, RFC-0011 §3c, §9 item 12). The PWM itself is written
before the line goes up and zeroed first thing when the HAL starts, because the kernel keeps a
PWM's last duty after the process that set it is gone.

The kernel's PWM sysfs is written by `hal/pwm.py`'s `SysfsPwm` — the same writer the
`digital.out` PWM channels of RFC-0010 use (`check`, `apply_ns`, `set_duty_ns`, `off`) — with the
motion channels as its keys. This module is only the motion policy on top: which duty or pulse a
speed or a target is, the ramp, and the order of the two writes.

Which `pwmchipN/M` drives which channel is the machine's wiring, not the board's (`board.v1`
gives a channel no PWM node), like the sensors' `hwmon` source: ``motion_sources`` of
`LinuxHAL`, or ``NEUROEDGE_LINUX_MOTION=wheel_left=pwmchip0/0;gripper=pwmchip0/1``. A channel
with no source is refused when the HAL starts, never guessed.

A ramp is stepped by a daemon thread every `RAMP_STEP_MS`; a stop cancels it and zeroes the duty
at once. Nothing here runs on `sim` (`SimActuator`) or in a replay.
"""

from __future__ import annotations

import contextlib
import re
import threading
import time
from collections.abc import Callable, Mapping
from typing import Any

from ..errors import BoardCapabilityError
from .motion_core import HOLD, Channel, Setpoint
from .pwm import SysfsPwm

__all__ = [
    "MOTION_ENV",
    "MOTOR_PWM_HZ",
    "PwmActuator",
    "parse_motion_sources",
]

MOTION_ENV = "NEUROEDGE_LINUX_MOTION"  # wheel_left=pwmchip0/0;gripper=pwmchip0/1
MOTOR_PWM_HZ = 20_000
SERVO_PERIOD_NS = 20_000_000
SERVO_MIN_NS = 1_000_000
SERVO_MAX_NS = 2_000_000
RAMP_STEP_MS = 20.0
_SPEC = re.compile(r"(pwmchip\d+)/(\d+)")


def parse_motion_sources(text: str, where: str) -> dict[str, str]:
    """``wheel_left=pwmchip0/0;gripper=pwmchip0/1`` → a mapping channel → ``pwmchipN/M``."""
    sources: dict[str, str] = {}
    for item in filter(None, (part.strip() for part in text.split(";"))):
        channel, sep, spec = item.partition("=")
        if not sep or not channel.strip() or not _SPEC.fullmatch(spec.strip()):
            raise BoardCapabilityError(
                where=where,
                why=f"{item!r} is not channel=pwmchipN/M",
                how="separate entries with ';', e.g. wheel_left=pwmchip0/0",
            )
        sources[channel.strip()] = spec.strip()
    return sources


class _Ramp:
    __slots__ = ("channel", "end", "start", "started", "seconds")

    def __init__(self, channel: Channel, start: float, end: float, seconds: float) -> None:
        self.channel, self.start, self.end, self.seconds = channel, start, end, seconds
        self.started = time.monotonic()

    def value(self, now: float) -> tuple[float, bool]:
        elapsed = now - self.started
        if self.seconds <= 0 or elapsed >= self.seconds:
            return self.end, True
        return self.start + (self.end - self.start) * elapsed / self.seconds, False


class PwmActuator:
    """
    The actuator behind `MotionController` on `linux`. `enable(pin, active, limit_ms)` drives the
    driver's enable line through the HAL (its supervisor holds it); `pwms` maps a channel to its
    `SysfsPwm`. `drive` writes the PWM *before* the line goes up, `safe` takes the line down
    *first*: the cheapest cut is the one that does not depend on a file write succeeding.
    """

    def __init__(
        self,
        pwm: SysfsPwm,
        enable: Callable[[str, bool, float | None], None],
        *,
        step_ms: float = RAMP_STEP_MS,
        on_fault: Callable[[str], None] | None = None,
    ) -> None:
        # `on_fault(channel)`: a ramp step the PWM refused — the channel is stopped, not left
        # at the duty it had (the HAL turns it into `motion_safe`, cause `actuator_fault`).
        self.on_fault = on_fault
        self._pwm = pwm
        self._enable = enable
        self._step_s = step_ms / 1000.0
        self._lock = threading.Lock()
        self._value: dict[str, float] = {}  # what each channel was last told, in its own unit
        self._powered: set[str] = set()  # the controller is programmed and enabled
        self._ramps: dict[str, _Ramp] = {}
        self._wake = threading.Event()
        self._thread: threading.Thread | None = None
        self._closed = False
        self._channels: dict[str, Channel] = {}

    # -- start -------------------------------------------------------------------------
    def open(self, channels: Mapping[str, Channel]) -> None:
        """Every wanted channel exists in the kernel and is silent. Raises `BoardCapabilityError`."""
        self._channels = dict(channels)
        for name, channel in self._channels.items():
            where = f"LinuxHAL -> motion {name!r}"
            self._pwm.check(name, where)  # no software fallback, nothing guessed
            try:
                self._pwm.off(name, where)  # a crashed run's duty is gone before anything moves
            except OSError as exc:
                raise BoardCapabilityError(
                    where=where,
                    why=f"the PWM channel cannot be silenced: {exc.strerror or exc}",
                    how="check the pwm overlay is loaded and the user may write the channel "
                    "(udev rule or group), and that no other process holds it",
                ) from exc
            if channel.kind == "motor":
                self._value[name] = 0.0

    # -- the Actuator protocol ----------------------------------------------------------
    def drive(self, channel: Channel, setpoint: Setpoint, now_ms: float, limit_ms: float) -> None:
        name = channel.name
        where = f"LinuxHAL -> motion {name!r}"
        try:
            if channel.kind == "motor":
                start, end = self._value.get(name, 0.0), setpoint.speed
                seconds = setpoint.ramp_ms / 1000.0
            else:
                end = float(setpoint.target if setpoint.target is not None else 0.0)
                known = name in self._value and name in self._powered
                start = self._value.get(name, end) if known else end
                seconds = abs(end - start) / setpoint.slew if setpoint.slew and known else 0.0
            with self._lock:
                value = start if seconds > 0 else end
                if name not in self._powered:
                    # the controller first, then (below) the enable line: duty, period, enable
                    self._pwm.apply_ns(
                        name, self._period_ns(channel), self._duty_ns(channel, value), where
                    )
                    self._powered.add(name)
                else:
                    self._pwm.set_duty_ns(name, self._duty_ns(channel, value), where)
                self._value[name] = value
                if seconds > 0:
                    self._ramps[name] = _Ramp(channel, start, end, seconds)
                else:
                    self._ramps.pop(name, None)
                    self._value[name] = end
            self._enable(channel.enable_pin, True, limit_ms)  # the driver last
            self._ensure_thread()
            self._wake.set()
        except OSError as exc:
            raise BoardCapabilityError(
                where=f"LinuxHAL -> motion {name!r}",
                why=f"the PWM channel could not be written: {exc.strerror or exc}",
                how="check the PWM wiring (NEUROEDGE_LINUX_MOTION) and permissions",
            ) from exc

    def safe(self, channel: Channel, state: str, now_ms: float, limit_ms: float) -> None:
        name = channel.name
        errors: list[BaseException] = []
        with self._lock:
            self._ramps.pop(name, None)
        if state == HOLD:
            try:
                self._enable(channel.enable_pin, True, limit_ms)  # keep power, keep the pulse
            except BaseException as exc:
                errors.append(exc)
        else:
            try:
                self._enable(channel.enable_pin, False, None)  # the driver first
            except BaseException as exc:
                errors.append(exc)
            self._powered.discard(name)
            try:
                with self._lock:
                    if channel.kind == "motor":
                        self._value[name] = 0.0
                    self._pwm.off(name, f"LinuxHAL -> motion {name!r}")
            except OSError as exc:
                errors.append(exc)
        if errors:
            raise errors[0]

    def snapshot(self, channel: Channel, now_ms: float) -> dict[str, Any]:
        with self._lock:
            ramp = self._ramps.get(channel.name)
            value = self._value.get(channel.name, 0.0)
            if ramp is not None:
                value = ramp.value(time.monotonic())[0]
        key = "speed" if channel.kind == "motor" else "position"
        return {"enabled": channel.name in self._powered, key: round(value, 6)}

    def close(self) -> None:
        self._closed = True
        self._wake.set()
        errors: list[BaseException] = []
        for name, channel in self._channels.items():
            try:
                self._enable(channel.enable_pin, False, None)
            except BaseException as exc:
                errors.append(exc)
            try:
                self._pwm.off(name, f"LinuxHAL -> motion {name!r}")
            except OSError as exc:
                errors.append(exc)
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        if errors:
            raise errors[0]

    # -- the hardware -------------------------------------------------------------------
    @staticmethod
    def _period_ns(channel: Channel) -> int:
        return round(1e9 / MOTOR_PWM_HZ) if channel.kind == "motor" else SERVO_PERIOD_NS

    @staticmethod
    def _duty_ns(channel: Channel, value: float) -> int:
        """A motor's speed is its duty; a servo's target is a pulse across its declared range."""
        if channel.kind == "motor":
            return round(value * (1e9 / MOTOR_PWM_HZ))
        low, high = float(channel.target_min), float(channel.target_max)  # type: ignore[arg-type]
        fraction = 0.0 if high == low else (value - low) / (high - low)
        return round(SERVO_MIN_NS + max(0.0, min(1.0, fraction)) * (SERVO_MAX_NS - SERVO_MIN_NS))

    def _ensure_thread(self) -> None:
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(
                target=self._run_ramps, name="neuroedge-motion-ramp", daemon=True
            )
            self._thread.start()

    def _run_ramps(self) -> None:
        while not self._closed:
            with self._lock:
                ramps = dict(self._ramps)
            if not ramps:
                self._wake.wait(timeout=0.5)
                self._wake.clear()
                continue
            now = time.monotonic()
            faulted: list[str] = []
            for name, ramp in ramps.items():
                value, done = ramp.value(now)
                with self._lock:
                    if self._ramps.get(name) is not ramp:
                        continue  # a newer command or a stop took the channel
                    try:
                        self._pwm.set_duty_ns(
                            name, self._duty_ns(ramp.channel, value), "LinuxHAL -> motion"
                        )
                    except OSError:
                        self._ramps.pop(name, None)
                        faulted.append(name)
                        continue
                    self._value[name] = value
                    if done:
                        del self._ramps[name]
            for name in faulted:  # outside the lock: stopping takes it
                if self.on_fault is not None:
                    with contextlib.suppress(Exception):
                        self.on_fault(name)
            time.sleep(self._step_s)
