"""
`@action` — a physical action with declared requirements and a gate (proposal §4.4).

The decorator records what the action needs (`requires`, checked against the
board at build time by TSK-S2-02) and which gate authorises it. Calling the
function directly raises `ActionContractViolation`: only `c.do()` may run it,
because only `c.do()` evaluates the gate first.
"""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

from ..errors import ActionContractViolation
from ..hal.board import PRIMITIVES


@dataclass(frozen=True)
class Requirement:
    """One `requires` entry: a primitive and, optionally, the named pin or sensor."""

    primitive: str
    name: str | None = None

    @classmethod
    def parse(cls, text: str, where: str) -> Requirement:
        primitive, _, name = text.partition(":")
        if primitive not in PRIMITIVES:
            raise ActionContractViolation(
                where=where,
                why=f"requires {text!r} names no HAL primitive; primitives are {list(PRIMITIVES)}",
                how='write requires="digital.out:door_lock" (primitive:name)',
            )
        return cls(primitive, name or None)

    def __str__(self) -> str:
        return self.primitive if self.name is None else f"{self.primitive}:{self.name}"


@dataclass(frozen=True)
class ActionSpec:
    name: str
    requires: tuple[Requirement, ...]
    gate: str
    fn: Callable[..., Any]
    source_file: str
    source_line: int

    @property
    def where(self) -> str:
        return f"{self.source_file}:{self.source_line}"

    @property
    def pins(self) -> frozenset[str]:
        return frozenset(r.name for r in self.requires if r.primitive == "digital.out" and r.name)


REGISTRY: dict[str, ActionSpec] = {}


@dataclass
class _Run:
    name: str
    open: bool = True


_running: ContextVar[_Run | None] = ContextVar("neuroedge_running_action", default=None)


@contextmanager
def running(spec: ActionSpec) -> Iterator[None]:
    """
    Used by `c.do()` only: permit `spec` to execute inside this block.

    The permission is a shared flag closed on exit, so a task spawned inside the
    body — which inherits this context — cannot run the action after c.do() returns.
    """
    run = _Run(spec.name)
    handle = _running.set(run)
    try:
        yield
    finally:
        run.open = False
        _running.reset(handle)


def action(
    *,
    name: str | None = None,
    requires: str | Sequence[str] = (),
    gate: str,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorate(fn: Callable[..., Any]) -> Callable[..., Any]:
        action_name = name or fn.__name__
        source_file = inspect.getsourcefile(fn) or "<unknown>"
        source_line = inspect.getsourcelines(fn)[1]
        where = f"{source_file}:{source_line}"
        entries = [requires] if isinstance(requires, str) else list(requires)
        spec = ActionSpec(
            name=action_name,
            requires=tuple(Requirement.parse(entry, where) for entry in entries),
            gate=gate,
            fn=fn,
            source_file=source_file,
            source_line=source_line,
        )
        existing = REGISTRY.get(action_name)
        if existing is not None and existing.where != spec.where:
            raise ActionContractViolation(
                where=where,
                why=f"action {action_name!r} is already defined at {existing.where}",
                how="give each @action a unique name",
            )
        REGISTRY[action_name] = spec

        @functools.wraps(fn)
        def guarded(*args: Any, **kwargs: Any) -> Any:
            run = _running.get()
            if run is None or run.name != action_name or not run.open:
                caller = inspect.stack()[1]
                raise ActionContractViolation(
                    where=f"{caller.filename}:{caller.lineno} -> {action_name}",
                    why="a physical action was called directly; only c.do() may run it",
                    how=f"await c.do({action_name}, ...)",
                )
            return fn(*args, **kwargs)

        guarded.__neuroedge_action__ = spec
        return guarded

    return decorate


def spec_of(target: Any) -> ActionSpec:
    """The `ActionSpec` behind a decorated function, a spec, or a registered name."""
    if isinstance(target, ActionSpec):
        return target
    if isinstance(target, str) and target in REGISTRY:
        return REGISTRY[target]
    spec = getattr(target, "__neuroedge_action__", None)
    if spec is None:
        raise ActionContractViolation(
            where=f"c.do({target!r})",
            why="not an @action function or a registered action name",
            how="decorate the function with @action(name=..., requires=..., gate=...)",
        )
    return spec
