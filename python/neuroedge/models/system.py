"""
SystemOne and SystemTwo — the two model interfaces agent code sees (FR-MDL-01).

`SystemOne` answers structured questions — `bool`, `level`, `choice`, and
nothing else (FR-MDL-02) — and is the engine's `FactSource`. Behind it sit a
primary provider and a local fallback (FR-MDL-03):

* the primary answers when it can;
* when it cannot — offline, timeout, refusal — a `system_one_fallback` event is
  recorded and the fallback is asked instead;
* when there is no fallback, or it cannot run, the `Unavailable` answer reaches
  the engine, which turns ``offline`` into `gate_unreachable`.

Real cloud connectors arrive with TSK-S2-11 behind `neuroedge.models.providers`
(Q-10); until then a primary is any `FactSource`, such as a test double. The
core imports no provider SDK.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from ..engine.circuit_breaker import DegradationBreaker
from ..engine.gate import FactSource
from ..engine.trace_sink import EventLog
from ..engine.verdict import Fact, Unavailable
from ..errors import PerceptionUnavailableError
from .grammar import BACKEND, CommandGrammar, GrammarAdjudicator

TYPES = ("bool", "level", "choice")


def _fallback_source(
    fallback: FactSource | CommandGrammar | str | None, grammar_path: str | Path | None
) -> FactSource | None:
    if fallback is None or hasattr(fallback, "adjudicate"):
        return fallback
    if isinstance(fallback, CommandGrammar):
        return GrammarAdjudicator(fallback)
    if fallback == BACKEND:
        return GrammarAdjudicator(CommandGrammar.load(grammar_path or "commands.toml"))
    raise PerceptionUnavailableError(
        where=f"SystemOne(fallback={fallback!r})",
        why=f"unknown fallback; the only built-in local fallback is {BACKEND!r} (Q-14)",
        how=f'use fallback="{BACKEND}" with grammar=<commands.toml>, or pass a FactSource',
    )


class SystemOne:
    def __init__(
        self,
        model: str,
        *,
        primary: FactSource | None = None,
        fallback: FactSource | CommandGrammar | str | None = None,
        grammar: str | Path | None = None,
        network: str = "online",
        events: EventLog | None = None,
        breaker: DegradationBreaker | None = None,
    ) -> None:
        self.model = model
        self.primary = primary
        self.fallback = _fallback_source(fallback, grammar)
        self.network = network
        self.events = events
        self.breaker = breaker

    async def adjudicate(
        self,
        criterion: str,
        definition: Mapping[str, Any],
        state: Mapping[str, Any] | None,
        deadline_ms: float | None = None,
    ) -> Fact | Unavailable:
        kind = definition.get("type")
        if kind not in TYPES:
            return Unavailable("refused", f"SystemOne answers {TYPES}, not {kind!r}")

        if self.network == "offline" or self.primary is None:
            answer: Fact | Unavailable = Unavailable("offline", f"{self.model} not reachable")
        elif self.breaker is not None and not self.breaker.allow_primary():
            answer = Unavailable("offline", f"circuit breaker open for {self.model}")
        else:
            answer = await self.primary.adjudicate(criterion, definition, state, deadline_ms)
            if self.breaker is not None:
                if isinstance(answer, Fact):
                    self.breaker.record_success()
                else:
                    self.breaker.record_failure(answer.reason)
        if isinstance(answer, Fact) or self.fallback is None:
            return answer

        if self.events is not None:
            self.events.emit(
                "system_one_fallback",
                {
                    "from": self.model,
                    "to": BACKEND,
                    "reason": answer.reason,
                    "criterion": criterion,
                },
            )
        try:
            return await self.fallback.adjudicate(criterion, definition, state, deadline_ms)
        except PerceptionUnavailableError as exc:
            # An unrunnable fallback is the Q-14 case for gate_unreachable.
            return Unavailable("offline", exc.why)

    # -- the agent-facing API (proposal §4.6) --------------------------------
    async def bool(
        self, name: str, *, instructions: str = "", state: Mapping | None = None
    ) -> Fact | Unavailable:
        return await self.adjudicate(name, {"type": "bool", "instructions": instructions}, state)

    async def level(
        self,
        name: str,
        *,
        levels: Sequence[str],
        instructions: str = "",
        state: Mapping | None = None,
    ) -> Fact | Unavailable:
        definition = {"type": "level", "levels": list(levels), "instructions": instructions}
        return await self.adjudicate(name, definition, state)

    async def choice(
        self,
        name: str,
        *,
        options: Sequence[str],
        instructions: str = "",
        state: Mapping | None = None,
    ) -> Fact | Unavailable:
        definition = {"type": "choice", "options": list(options), "instructions": instructions}
        answer = await self.adjudicate(name, definition, state)
        if self.events is not None and name == "intent" and isinstance(answer, Fact):
            self.events.emit(
                "intent_extracted",
                {
                    "intent": answer.value,
                    "confidence": answer.confidence,
                    "system": "SystemOne",
                    "backend": answer.source,
                },
            )
        return answer


class SystemTwo:
    """
    Open-ended generation — replies and free-text extraction (FR-MDL-01).

    A provider is a callable ``(task, name, state) -> str``. With none configured,
    or when it fails, the fallback is used; with neither, `PerceptionUnavailableError`.
    Cloud providers arrive with TSK-S2-11.
    """

    Provider = Callable[[str, str | None, Mapping | None], Any]

    def __init__(
        self,
        model: str,
        *,
        provider: SystemTwo.Provider | None = None,
        fallback: SystemTwo.Provider | None = None,
    ) -> None:
        self.model = model
        self.provider = provider
        self.fallback = fallback

    async def _run(self, task: str, name: str | None, state: Mapping | None) -> str:
        for candidate in (self.provider, self.fallback):
            if candidate is None:
                continue
            try:
                answer = candidate(task, name, state)
                if hasattr(answer, "__await__"):
                    answer = await answer
                return str(answer)
            except Exception:  # try the next candidate; the last failure is reported
                continue
        raise PerceptionUnavailableError(
            where=f"SystemTwo({self.model!r}).{task}",
            why="no provider or fallback produced an answer",
            how="configure a provider (TSK-S2-11) or a fallback for SystemTwo",
        )

    async def reply(self, state: Mapping | None = None) -> str:
        return await self._run("reply", None, state)

    async def extract(self, name: str, state: Mapping | None = None) -> str:
        return await self._run("extract", name, state)
