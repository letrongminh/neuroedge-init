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

With `criteria`, the primary decides only those criteria; every other one goes
straight to the fallback — no call, no `system_one_fallback`, nothing failed. The
primary waits at most `timeout_ms`, and when a fallback exists it is cut off
`FALLBACK_RESERVE_MS` before the gate's deadline, so the fallback still answers
inside the budget. The breaker counts a primary that is down, slow or broken; an
answer below the confidence threshold (``empty``) is still an answer.

The providers — System 2's (LiteLLM, custom adapters, TSK-S2-11) and System 1's
cloud primary (Jev over the System One API, `[system_one]`, TSK-I4-02) — live
behind `neuroedge.models.providers`; a `SystemOne` primary is any `FactSource`,
such as a test double. The core imports no provider SDK.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from ..engine.circuit_breaker import DegradationBreaker
from ..engine.gate import FactSource
from ..engine.trace_sink import EventLog
from ..engine.verdict import Fact, Unavailable
from ..errors import NeuroEdgeError, PerceptionUnavailableError
from .grammar import BACKEND, CommandGrammar, GrammarAdjudicator

TYPES = ("bool", "level", "choice")
# What the fallback keeps of the gate's budget when the primary is slow. The
# command grammar answers in about a millisecond; the rest is room for the event
# loop to wake up after the primary's deadline.
FALLBACK_RESERVE_MS = 50.0


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
        criteria: Iterable[str] | None = None,
        timeout_ms: float | None = None,
    ) -> None:
        self.model = model
        self.primary = primary
        self.fallback = _fallback_source(fallback, grammar)
        self.network = network
        self.events = events
        self.breaker = breaker
        # The criteria the primary may decide; None = every criterion (a test double).
        self.criteria = None if criteria is None else frozenset(criteria)
        self.timeout_ms = timeout_ms

    def delegates(self, criterion: str) -> bool:
        """True when `criterion` is the primary's to decide."""
        return self.primary is not None and (self.criteria is None or criterion in self.criteria)

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

        if self.primary is not None and not self.delegates(criterion):
            # Not the primary's to decide: the fallback is this criterion's source.
            if self.fallback is None:
                return Unavailable("refused", f"{criterion!r} is not delegated to {self.model}")
            return await self._ask_fallback(criterion, definition, state, deadline_ms)
        limit = self._primary_limit(deadline_ms)
        if self.network == "offline" or self.primary is None:
            answer: Fact | Unavailable = Unavailable("offline", f"{self.model} not reachable")
        elif self.breaker is not None and not self.breaker.allow_primary():
            answer = Unavailable("offline", f"circuit breaker open for {self.model}")
        elif limit is not None and limit <= 0:
            # Not asked, so nothing to hold against the provider's health.
            answer = Unavailable("timeout", f"no time left in the budget for {self.model}")
        else:
            answer = await self._ask_primary(criterion, definition, state, limit)
            if self.breaker is not None:
                # "empty" — the model answered, below the threshold — is a healthy
                # provider: the breaker is for one that is down, slow or broken.
                if isinstance(answer, Fact) or answer.reason == "empty":
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
        return await self._ask_fallback(criterion, definition, state, deadline_ms)

    async def _ask_fallback(
        self,
        criterion: str,
        definition: Mapping[str, Any],
        state: Mapping[str, Any] | None,
        deadline_ms: float | None,
    ) -> Fact | Unavailable:
        try:
            return await self.fallback.adjudicate(criterion, definition, state, deadline_ms)
        except PerceptionUnavailableError as exc:
            # An unrunnable fallback is the Q-14 case for gate_unreachable.
            return Unavailable("offline", exc.why)
        except Exception as exc:
            return Unavailable("offline", f"fallback failed: {type(exc).__name__}: {exc}")

    def _primary_limit(self, deadline_ms: float | None) -> float | None:
        """How long the primary may take: its own timeout, and room left for the fallback."""
        limit = deadline_ms
        if self.timeout_ms is not None:
            limit = self.timeout_ms if limit is None else min(limit, self.timeout_ms)
        if deadline_ms is not None and self.fallback is not None:
            limit = min(limit, deadline_ms - FALLBACK_RESERVE_MS)
        return limit

    async def _ask_primary(
        self,
        criterion: str,
        definition: Mapping[str, Any],
        state: Mapping[str, Any] | None,
        deadline_ms: float | None,
    ) -> Fact | Unavailable:
        """A primary that raises or hangs is an answer, not a crash: route to the fallback."""
        timeout = None if deadline_ms is None else max(deadline_ms, 0) / 1000.0
        try:
            return await asyncio.wait_for(
                self.primary.adjudicate(criterion, definition, state, deadline_ms), timeout
            )
        except TimeoutError:
            return Unavailable("timeout", f"{self.model} exceeded {deadline_ms:g} ms")
        except Exception as exc:
            return Unavailable("offline", f"{self.model} failed: {type(exc).__name__}: {exc}")

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

    A provider is a callable ``(task, name, state) -> answer`` — the contract is
    `neuroedge.models.providers.base`; the real ones (LiteLLM, a custom adapter)
    are built from `agent.toml` `[system_two]` by `providers.system_two_for`.
    With none configured, or when it fails, the fallback is used; with neither,
    `PerceptionUnavailableError` whose `why` is the last failure's reason.

    With `events`, every model call is traced as ``system_two_call`` — provider,
    model, task, latency and, when the provider reports them, tokens and cost;
    never the prompt, never a key (FR-MDL-06).
    """

    Provider = Callable[[str, str | None, Mapping | None], Any]

    def __init__(
        self,
        model: str,
        *,
        provider: SystemTwo.Provider | None = None,
        fallback: SystemTwo.Provider | None = None,
        events: EventLog | None = None,
    ) -> None:
        self.model = model
        self.provider = provider
        self.fallback = fallback
        self.events = events

    @property
    def available(self) -> bool:
        """A provider or a fallback is configured (it may still fail when asked)."""
        return self.provider is not None or self.fallback is not None

    async def respond(self, state: Mapping | None = None) -> Any:
        """
        A reply that may carry tool calls: text, or ``{"text": ..., "tool_calls": [...]}``
        (flat or OpenAI shape). The caller parses it with
        `neuroedge.actions.tools.parse_tool_calls` and dispatches every call through a gate.
        """
        return await self._run("respond", None, state, raw=True)

    async def _run(
        self, task: str, name: str | None, state: Mapping | None, raw: bool = False
    ) -> Any:
        failure: Exception | None = None
        for candidate in (self.provider, self.fallback):
            if candidate is None:
                continue
            started = self.events.clock() if self.events is not None else 0.0
            try:
                answer = candidate(task, name, state)
                if hasattr(answer, "__await__"):
                    answer = await answer
            except Exception as exc:  # try the next candidate; the last failure is reported
                failure = exc
                self._trace(candidate, task, state, started, exc)
                continue
            self._trace(candidate, task, state, started, None)
            return answer if raw else str(answer)
        if isinstance(failure, NeuroEdgeError):
            why, how = failure.why, failure.how
        elif failure is not None:
            why = f"{self.model} failed: {type(failure).__name__}: {failure}"[:300]
            how = "check the provider; meanwhile the agent answers offline"
        else:
            why = "no provider or fallback produced an answer"
            how = "add [system_two] to agent.toml, or pass SystemTwo a provider or a fallback"
        raise PerceptionUnavailableError(
            where=f"SystemTwo({self.model!r}).{task}", why=why, how=how
        )

    def _trace(
        self,
        candidate: Any,
        task: str,
        state: Mapping | None,
        started: float,
        failure: Exception | None,
    ) -> None:
        """
        One `system_two_call` per model call. A provider that gave up before
        calling (``called = False``: no extra, no key) made no call.
        """
        if self.events is None or getattr(failure, "called", True) is False:
            return
        data: dict[str, Any] = {
            "provider": str(getattr(candidate, "name", "custom")),
            "model": str(getattr(candidate, "model", self.model)),
            "task": str((state or {}).get("task") or task),
            "latency_ms": max(0, int(self.events.clock() - started)),
            "status": "ok" if failure is None else "error",
        }
        usage = getattr(candidate, "last_usage", None) if failure is None else None
        if isinstance(usage, Mapping):
            for key in ("prompt_tokens", "completion_tokens", "cost_usd"):
                if usage.get(key) is not None:
                    data[key] = usage[key]
        if failure is not None:
            data["error"] = type(failure).__name__
        self.events.emit("system_two_call", data)

    async def reply(self, state: Mapping | None = None) -> str:
        return await self._run("reply", None, state)

    async def extract(self, name: str, state: Mapping | None = None) -> str:
        return await self._run("extract", name, state)
