"""
`digital.out(pin)` — the actuator API used inside an `@action` body (proposal §4.4).

    @action(name="unlock_door", requires="digital.out:door_lock", gate="unlock_door")
    def unlock_door(guest_id: str, duration_s: int = 30) -> None:
        digital.out("door_lock").pulse(seconds=duration_s)

The call only works while `c.do()` has granted the action a verdict token: the
grant (HAL + token) travels in a `ContextVar`, so there is no argument an agent
could forge. Outside a grant every call is an `ActionContractViolation`.

`after_ms` schedules the command: the gate decides now, the pin moves later, and
until then barge-in cancels it (docs/spec/voice_fsm.md §5). A HAL that cannot
schedule refuses it — it never delivers early instead.

`digital.input(pin).level()` is the input side (RFC-0007 §3a): the logic level of a declared
input pin, True for high. Reading moves nothing, so it needs no verdict token — but it uses the
HAL of the `c.do()` that is running the action, and a line that cannot be read raises
`PerceptionUnavailableError` rather than returning a level. Every read is a `digital_in` event.
"""

from __future__ import annotations

import math
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

from ..errors import ActionContractViolation, BoardCapabilityError


@dataclass(frozen=True)
class _Grant:
    hal: Any
    token: Any
    action: str


_active: ContextVar[_Grant | None] = ContextVar("neuroedge_actuator_grant", default=None)


@contextmanager
def grant(hal: Any, token: Any, action: str) -> Iterator[None]:
    """Used by `c.do()` only: make `token` the proof for pins driven in this block."""
    handle = _active.set(_Grant(hal, token, action))
    try:
        yield
    finally:
        _active.reset(handle)


def _caller() -> str:
    # Runs between the verdict and `authorize`, inside the lease. `inspect.stack()` looks up the module
    # and reads the source of every frame — tens of ms the first time, more with many modules loaded —
    # and a 200 ms lease could run out before the command reached `authorize`. The frames alone suffice.
    frame = sys._getframe(2)
    while frame is not None:
        filename = frame.f_code.co_filename
        if not filename.endswith(("hal/digital.py", "hal/motion.py", "contextlib.py")):
            return f"{filename}:{frame.f_lineno}"
        frame = frame.f_back
    return "<unknown>"


class _Pin:
    def __init__(self, name: str) -> None:
        self.name = name

    def _drive(
        self,
        operation: str,
        duration_ms: int,
        after_ms: int | None = None,
        **extra: Any,
    ) -> Any:
        where = _caller()
        active = _active.get()
        if active is None:
            raise ActionContractViolation(
                where=f"{where} -> digital.out({self.name!r})",
                why="no verdict token is active; actuators move only inside c.do()",
                how="put the pin change in an @action function and call it with await c.do(...)",
            )
        called_from = f"{where} ({active.action})"
        if after_ms is not None and after_ms < 0:
            raise BoardCapabilityError(
                where=f"{called_from} -> digital.out({self.name!r})",
                why=f"negative after_ms {after_ms}",
                how="use after_ms >= 0",
            )
        scheduled: dict[str, int] = {}
        if after_ms:
            if not getattr(active.hal, "schedules_commands", False):
                raise BoardCapabilityError(
                    where=f"{called_from} -> digital.out({self.name!r})",
                    why=f"target {getattr(active.hal, 'target', '?')!r} cannot schedule a command",
                    how="drive the pin without after_ms; scheduled commands exist on `sim` (TSK-S3-11)",
                )
            # Rounded up: a scheduled command is never delivered early (0.5 ms is 1 ms).
            scheduled["delay_ms"] = math.ceil(after_ms)
        return active.hal.digital_out(
            self.name,
            operation,
            duration_ms,
            signature=active.token,
            called_from=called_from,
            **scheduled,
            **extra,
        )

    def pulse(
        self, *, seconds: float | None = None, ms: int | None = None, after_ms: int | None = None
    ) -> Any:
        duration = ms if ms is not None else round((seconds or 0) * 1000)
        return self._drive("pulse", int(duration), after_ms)

    def on(self, *, after_ms: int | None = None) -> Any:
        return self._drive("on", 0, after_ms)

    def off(self, *, after_ms: int | None = None) -> Any:
        return self._drive("off", 0, after_ms)

    def pwm(
        self,
        *,
        frequency_hz: int,
        duty: float,
        ms: int | None = None,
        seconds: float | None = None,
    ) -> Any:
        """
        Drive a PWM channel at `frequency_hz` and `duty` (0..1) for `ms` milliseconds
        (RFC-0010 §3b). The duration has no default and no "forever": it is required, and the
        HAL turns the channel off when it is up. Only a PWM channel of the board takes it.
        """
        duration = ms if ms is not None else (None if seconds is None else round(seconds * 1000))
        return self._drive("pwm", duration, frequency_hz=frequency_hz, duty=duty)  # type: ignore[arg-type]

    def state(self) -> Any:
        """
        The state of a PWM channel: `duty` and `frequency_hz` with the `source` of the numbers,
        `measured` where the board declares a hardware read-back for the pin, else `commanded`
        (RFC-0010 §3b). Reading moves nothing, so it needs no token.
        """
        where = _caller()
        active = _active.get()
        if active is None:
            raise ActionContractViolation(
                where=f"{where} -> digital.out({self.name!r}).state()",
                why="no HAL is active; state is read inside an @action run by c.do()",
                how="read it in an @action function, or call hal.pin_state() in a test",
            )
        return active.hal.pin_state(self.name, called_from=f"{where} ({active.action})")


def out(pin: str) -> _Pin:
    return _Pin(pin)


class _Input:
    def __init__(self, name: str) -> None:
        self.name = name

    def level(self) -> bool:
        where = _caller()
        active = _active.get()
        if active is None:
            raise ActionContractViolation(
                where=f"{where} -> digital.input({self.name!r})",
                why="no HAL is active; inputs are read inside an @action run by c.do()",
                how="read the input in an @action function, or call hal.digital_in() in a test",
            )
        return active.hal.digital_in(self.name, called_from=f"{where} ({active.action})")


def input(pin: str) -> _Input:  # noqa: A001 - the agent API names the primitive, like `out`
    return _Input(pin)
