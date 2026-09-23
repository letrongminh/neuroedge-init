"""
Deterministic test doubles for SystemOne providers.

`ScriptedSource` answers from a script and can produce every `Unavailable`
reason, so tests exercise each degradation path without a network. It is also
the baseline for "swap the model ⇒ same verdicts": a golden verdict set built
on a script must hold for any provider that gives the same answers.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from ..engine.verdict import Fact, Unavailable


class ScriptedSource:
    def __init__(
        self,
        answers: Mapping[str, Fact | Unavailable],
        *,
        clock: Any | None = None,
        delay_ms: float = 0.0,
        default: Fact | Unavailable | None = None,
    ) -> None:
        self.answers = dict(answers)
        self.clock = clock
        self.delay_ms = delay_ms
        self.default = default if default is not None else Unavailable("empty")
        self.calls: list[str] = []

    async def adjudicate(
        self,
        criterion: str,
        definition: Mapping[str, Any],
        state: Mapping[str, Any] | None,
        deadline_ms: float | None = None,
    ) -> Fact | Unavailable:
        self.calls.append(criterion)
        advance: Callable[[float], None] | None = getattr(self.clock, "advance", None)
        if advance is not None and self.delay_ms:
            advance(self.delay_ms)
        return self.answers.get(criterion, self.default)
