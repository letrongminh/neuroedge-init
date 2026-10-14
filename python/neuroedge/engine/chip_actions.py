"""
What an @action does to its pins, for the chip (Q-83 Profile B, TODOS.md #70).

On the host an action is a Python body (`digital.out("door_lock").pulse(seconds=duration_s)`);
the chip has no Python, only the generated `ne_agent` tables. At build time each body runs
once against a recording HAL, under the same grant `c.do()` gives it, and what it drove becomes
the action's pin operations: `on`, `off`, or a pulse whose length is a constant or a constant
times one argument. Two runs with different argument values tell which: a duration that moves
with exactly one numeric argument, in proportion, is that argument; one that does not move is a
constant.

Anything else (PWM, a scheduled command, a duration that is not proportional to one argument,
a body that reads inputs or raises on probe values) is recorded as `unsupported`: the chip
then refuses to drive that action's pins (`ne_agent.h` NE_AGENT_OP_UNSUPPORTED), it never
guesses. The host's replay names the difference.
"""

from __future__ import annotations

import inspect
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

ON, OFF, PULSE, UNSUPPORTED = 0, 1, 2, 3
OPERATIONS = {"on": ON, "off": OFF, "pulse": PULSE}
PROBES = (3, 5)  # two values for a numeric argument: a duration in proportion follows them


@dataclass(frozen=True)
class PinOp:
    pin: str
    op: int
    ms: int  # the pulse's length, or its length per unit of `arg`
    arg: str | None = None


class _Unsupported(Exception):
    pass


class _Recorder:
    """The HAL a probe run drives: it writes down what the body asked for, and moves nothing."""

    target = "chip"
    schedules_commands = False

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, int | None]] = []

    def digital_out(self, pin, operation, duration_ms, **extra) -> None:
        if extra.get("delay_ms") or operation not in OPERATIONS:
            raise _Unsupported(operation)
        self.calls.append((pin, operation, duration_ms))

    def __getattr__(self, name: str) -> Any:
        raise _Unsupported(name)  # an input read, PWM state, motion: not for the chip's table


def _numeric(parameter: inspect.Parameter) -> bool:
    return (
        parameter.annotation in (int, float, "int", "float")
        or isinstance(parameter.default, int | float)
        and not isinstance(parameter.default, bool)
    )


def _probe(spec: Any, values: dict[str, Any]) -> list[tuple[str, str, int | None]]:
    from ..hal.digital import grant

    recorder = _Recorder()
    with grant(recorder, None, spec.name):
        spec.fn(**values)
    return recorder.calls


def pin_operations(spec: Any) -> tuple[PinOp, ...]:
    """The pin operations of one action, in the order its body drives them."""
    parameters = [
        p
        for p in inspect.signature(spec.fn).parameters.values()
        if p.kind in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY)
    ]
    numeric = [p.name for p in parameters if _numeric(p)]
    base = {p.name: PROBES[0] if p.name in numeric else "probe" for p in parameters}
    try:
        first = _probe(spec, base)
        moved = {name: _probe(spec, {**base, name: PROBES[1]}) for name in numeric}
    except Exception:  # noqa: BLE001 - any failure of a probe run means "not for the chip"
        return tuple(PinOp(pin, UNSUPPORTED, 0) for pin in sorted(spec.pins))
    ops = []
    for i, (pin, operation, duration) in enumerate(first):
        if operation != "pulse":
            ops.append(PinOp(pin, OPERATIONS[operation], 0))
            continue
        changed = [
            name
            for name, calls in moved.items()
            if len(calls) != len(first) or calls[i][2] != duration
        ]
        if not changed:
            ops.append(PinOp(pin, PULSE, int(duration or 0)))
            continue
        name = changed[0]
        later = moved[name][i][2] or 0
        per_unit, rest = divmod(int(duration or 0), PROBES[0])
        if len(changed) == 1 and rest == 0 and later == per_unit * PROBES[1]:
            ops.append(PinOp(pin, PULSE, per_unit, name))
        else:
            ops.append(PinOp(pin, UNSUPPORTED, 0))
    return tuple(ops)


def operations(specs: Iterable[Any]) -> list[tuple[PinOp, ...]]:
    """`pin_operations` per @action, sorted by name as `firmware.action_table` is."""
    return [pin_operations(spec) for spec in sorted(specs, key=lambda spec: spec.name)]
