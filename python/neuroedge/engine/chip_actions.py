"""
What an @action does to its pins, for the chip (Q-83 Profile B, TODOS.md #70).

On the host an action is a Python body (`digital.out("door_lock").pulse(seconds=duration_s)`);
the chip has no Python, only the generated `ne_agent` tables. At build time each body runs
against a recording HAL, under the same grant `c.do()` gives it, and what it drove becomes the
action's pin operations: `on`, `off`, or a pulse whose length is a constant or a constant times
one argument. Every argument is probed with several values (numbers 3, 5 and 1000; booleans
both ways; two strings): the pins and operations must not change with any of them, and a pulse
length that moves must move with exactly one number, in proportion at all three values.

Anything else (PWM, a scheduled command, a branch on an argument, a clamped or offset length,
a body that drives nothing, reads inputs, is async or raises) is recorded as `unsupported`: the chip
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
        self.refused = False  # set even when the body swallows the exception

    def digital_out(self, pin, operation, duration_ms, **extra) -> None:
        if extra.get("delay_ms") or operation not in OPERATIONS:
            self.refused = True
            raise _Unsupported(operation)
        self.calls.append((pin, operation, duration_ms))

    def __getattr__(self, name: str) -> Any:
        self.refused = True
        raise _Unsupported(name)  # an input read, PWM state, motion: not for the chip's table


NUMBERS = (3, 5, 1000)  # a duration in proportion follows all three (a clamp does not)
CHOICES = {"bool": (True, False), "str": ("a", "b")}


def _kind(parameter: inspect.Parameter) -> str:
    annotation, default = parameter.annotation, parameter.default
    if annotation in (bool, "bool") or isinstance(default, bool):
        return "bool"
    if annotation in (int, float, "int", "float") or isinstance(default, int | float):
        return "number"
    return "str"


def _probe(spec: Any, values: dict[str, Any]) -> list[tuple[str, str, int | None]]:
    from ..hal.digital import grant

    recorder = _Recorder()
    with grant(recorder, None, spec.name):
        spec.fn(**values)
    if recorder.refused:
        raise _Unsupported("refused inside the body")
    return recorder.calls


def _classify(spec: Any) -> tuple[PinOp, ...]:
    if inspect.iscoroutinefunction(spec.fn) or inspect.isgeneratorfunction(spec.fn):
        raise _Unsupported("not a plain function")
    parameters = [
        p
        for p in inspect.signature(spec.fn).parameters.values()
        if p.kind in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY)
    ]
    kinds = {p.name: _kind(p) for p in parameters}
    base = {
        name: NUMBERS[0] if kind == "number" else CHOICES[kind][0] for name, kind in kinds.items()
    }
    first = _probe(spec, base)
    if not first or any(pin not in spec.pins for pin, _, _ in first):
        raise _Unsupported("drives no declared pin")
    shape = [(pin, op) for pin, op, _ in first]
    # Every other value of every argument: the same pins and operations, or not for the chip.
    variants: dict[str, list[list[tuple[str, str, int | None]]]] = {}
    for name, kind in kinds.items():
        others = NUMBERS[1:] if kind == "number" else CHOICES[kind][1:]
        variants[name] = [_probe(spec, {**base, name: value}) for value in others]
        for calls in variants[name]:
            if [(pin, op) for pin, op, _ in calls] != shape:
                raise _Unsupported(f"what it drives depends on {name}")
    ops = []
    for i, (pin, operation, duration) in enumerate(first):
        if operation != "pulse":
            ops.append(PinOp(pin, OPERATIONS[operation], 0))
            continue
        moving = [n for n, runs in variants.items() if any(r[i][2] != duration for r in runs)]
        if not moving:
            ops.append(PinOp(pin, PULSE, int(duration or 0)))
            continue
        name = moving[0]
        if len(moving) != 1 or kinds[name] != "number":
            raise _Unsupported(f"a pulse length that depends on {moving}")
        per_unit, rest = divmod(int(duration or 0), NUMBERS[0])
        values = dict(zip(NUMBERS[1:], (r[i][2] for r in variants[name]), strict=True))
        if rest or per_unit <= 0 or any(got != per_unit * n for n, got in values.items()):
            raise _Unsupported(f"a pulse length not in proportion to {name}")
        ops.append(PinOp(pin, PULSE, per_unit, name))
    return tuple(ops)


def pin_operations(spec: Any) -> tuple[PinOp, ...]:
    """The pin operations of one action, in the order its body drives them; fail closed."""
    try:
        return _classify(spec)
    except Exception:  # noqa: BLE001 - anything unclear about the body means "not for the chip"
        return tuple(PinOp(pin, UNSUPPORTED, 0) for pin in sorted(spec.pins))


def operations(specs: Iterable[Any]) -> list[tuple[PinOp, ...]]:
    """`pin_operations` per @action, sorted by name as `firmware.action_table` is."""
    return [pin_operations(spec) for spec in sorted(specs, key=lambda spec: spec.name)]
