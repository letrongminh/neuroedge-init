"""
`digital.out(pin)` — the actuator API used inside an `@action` body (proposal §4.4).

    @action(name="unlock_door", requires="digital.out:door_lock", gate="unlock_door")
    def unlock_door(guest_id: str, duration_s: int = 30) -> None:
        digital.out("door_lock").pulse(seconds=duration_s)

The call only works while `c.do()` has granted the action a verdict token: the
grant (HAL + token) travels in a `ContextVar`, so there is no argument an agent
could forge. Outside a grant every call is an `ActionContractViolation`.
"""

from __future__ import annotations

import inspect
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

from ..errors import ActionContractViolation


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

    def _drive(self, operation: str, duration_ms: int) -> Any:
        where = _caller()
        active = _active.get()
        if active is None:
            raise ActionContractViolation(
                where=f"{where} -> digital.out({self.name!r})",
                why="no verdict token is active; actuators move only inside c.do()",
                how="put the pin change in an @action function and call it with await c.do(...)",
            )
        return active.hal.digital_out(
            self.name,
            operation,
            duration_ms,
            signature=active.token,
            called_from=f"{where} ({active.action})",
        )

    def pulse(self, *, seconds: float | None = None, ms: int | None = None) -> Any:
        duration = ms if ms is not None else round((seconds or 0) * 1000)
        return self._drive("pulse", int(duration))

    def on(self) -> Any:
        return self._drive("on", 0)

    def off(self) -> Any:
        return self._drive("off", 0)


def out(pin: str) -> _Pin:
    return _Pin(pin)
