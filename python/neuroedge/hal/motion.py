"""
`motion.motor(...)` and `motion.servo(...)` — the actuator API used inside an `@action` body
(RFC-0011 §3b).

    @action(name="drive", requires="motion:wheel_left", gate="drive")
    def drive(speed: float = 0.3) -> None:
        motion.motor("wheel_left", speed=speed, ramp_ms=300)

    @action(name="grip", requires="motion:gripper", gate="grip")
    def grip(angle: float = 45.0) -> None:
        motion.servo("gripper", target=angle)

A command moves its channel only while its **lease** is valid: the verdict token of the gate
pass that allowed the action carries one lease per channel in `requires`, good for one command
and for the channel's `lease_ms` after the verdict. Nothing renews it but another gate pass —
call the action again — so a channel nobody keeps commanding goes to its safe state, and a
BLOCK, a barge-in or the end of the session sends it there at once. `motion.stop(channel)` is
a command toward the safe state: it needs no verdict and is never refused.

The call only works while `c.do()` has granted the action a verdict token (the grant of
`hal/digital.py`); outside one, every call is an `ActionContractViolation`. `speed` is the
magnitude 0..`speed_max` of the board and `direction` is `"forward"` (a motor channel has no
direction line to declare another); a servo's `target` lies inside the board's range, and
`speed_max` is how fast it may move there, in units per second.
"""

from __future__ import annotations

from typing import Any

from ..errors import ActionContractViolation
from .digital import _active, _caller


def _grant(primitive: str, channel: str) -> tuple[Any, str]:
    where = _caller()
    active = _active.get()
    if active is None:
        raise ActionContractViolation(
            where=f"{where} -> {primitive}({channel!r})",
            why="no verdict token is active; channels move only inside c.do()",
            how="put the command in an @action function and call it with await c.do(...)",
        )
    return active, f"{where} ({active.action})"


def motor(
    channel: str, speed: float, *, direction: str = "forward", ramp_ms: int | None = None
) -> Any:
    active, called_from = _grant("motion.motor", channel)
    return active.hal.motion_motor(
        channel, speed, direction, ramp_ms, signature=active.token, called_from=called_from
    )


def servo(channel: str, target: float, *, speed_max: float | None = None) -> Any:
    active, called_from = _grant("motion.servo", channel)
    return active.hal.motion_servo(
        channel, target, speed_max, signature=active.token, called_from=called_from
    )


def stop(channel: str) -> None:
    active, called_from = _grant("motion.stop", channel)
    active.hal.motion_stop(channel, called_from=called_from)
