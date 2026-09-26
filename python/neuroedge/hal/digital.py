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
"""

from __future__ import annotations

import inspect
import math
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
    for frame in inspect.stack()[2:]:
        if not frame.filename.endswith(("hal/digital.py", "contextlib.py")):
            return f"{frame.filename}:{frame.lineno}"
    return "<unknown>"


class _Pin:
    def __init__(self, name: str) -> None:
        self.name = name

    def _drive(self, operation: str, duration_ms: int, after_ms: int | None = None) -> Any:
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


def out(pin: str) -> _Pin:
    return _Pin(pin)
