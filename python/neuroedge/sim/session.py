"""
`SimSession` — one agent wired up on target `sim` (TSK-S3-06, FR-CLI-02, Q-15).

This is what `neuroedge run --target sim` drives and what a scaffolded
project's tests import. It assembles the Sprint 2 parts, nothing new:

    typed text ─► SimHAL.audio_in ─► CommandGrammar ─► intent + slots
                                        │
                  [sim] session facts ──┴─► c.do(@action) ─► gate ─► digital.out

Loading runs the same checks as `neuroedge build` first, so a session never
starts on a board the agent does not fit. Input is typed text matched by the
local command grammar (Q-14/Q-15): no network, no key, deterministic.

Where gate facts come from. `SystemOne` is offline here, so a criterion is
decided by, in order:

1. the `[sim.facts]` table of `agent.toml` — session state such as
   "the guest is authenticated", which on a device the property system
   supplies and which is never inferred from what the guest typed;
2. `[sim.slot_facts]` — a fact computed from a slot the grammar extracted,
   e.g. ``room_matches = { slot = "room", equals = "101" }``;
3. the grammar, through `SystemOne`'s local fallback, for the facts a matched
   command declares (``command_recognized``).

Anything else is undecided, and the gate blocks.
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..actions import ActionResult, Conversation
from ..engine.compiler import AgentManifest, build, load_actions, load_agent_manifest
from ..engine.compiler import resolve_gates as _resolve_gates
from ..engine.gate import ActionContractEngine
from ..engine.gate_resolver import GateRegistry
from ..engine.trace_sink import Clock, EventLog, monotonic_ms
from ..errors import AgentManifestError
from ..hal.board import load_board_by_id
from ..hal.sim import SimHAL
from ..models import CommandGrammar, SystemOne
from ..models.grammar import Recognition
from ..trace import validate_trace


@dataclass(frozen=True)
class Turn:
    """What one typed line did."""

    text: str
    recognition: Recognition
    result: ActionResult | None = None

    @property
    def recognised(self) -> bool:
        return self.recognition.recognised

    @property
    def action(self) -> str | None:
        command = self.recognition.command
        return None if command is None else command.action

    @property
    def arguments(self) -> dict[str, str]:
        """The action's keyword arguments, taken from the recognised slots."""
        command, slots = self.recognition.command, self.recognition.slots
        if command is None:
            return {}
        return {param: slots[slot] for param, slot in command.arguments.items() if slot in slots}

    @property
    def allowed(self) -> bool:
        return self.result is not None and not self.result.blocked


def _sim_tables(manifest: AgentManifest) -> tuple[dict[str, Any], dict[str, tuple[str, Any]]]:
    sim = tomllib.loads(manifest.source.read_text(encoding="utf-8")).get("sim", {})
    facts = sim.get("facts", {})
    if not isinstance(facts, dict):
        raise AgentManifestError(
            where=f"{manifest.source} -> [sim.facts]",
            why=f"[sim.facts] must be a table of criterion = value, found {facts!r}",
            how="write [sim.facts] with lines such as guest_authenticated = true",
        )
    slot_facts: dict[str, tuple[str, Any]] = {}
    for criterion, rule in sim.get("slot_facts", {}).items():
        if (
            not isinstance(rule, dict)
            or not isinstance(rule.get("slot"), str)
            or "equals" not in rule
        ):
            raise AgentManifestError(
                where=f"{manifest.source} -> [sim.slot_facts] {criterion}",
                why="a slot fact needs a string `slot` and an `equals` value",
                how=f'write {criterion} = {{ slot = "room", equals = "101" }}',
            )
        slot_facts[criterion] = (rule["slot"], rule["equals"])
    return dict(facts), slot_facts


class SimSession:
    def __init__(
        self,
        manifest: AgentManifest,
        *,
        hal: SimHAL,
        events: EventLog,
        grammar: CommandGrammar,
        conversation: Conversation,
        facts: Mapping[str, Any],
        slot_facts: Mapping[str, tuple[str, Any]],
    ) -> None:
        self.manifest = manifest
        self.hal = hal
        self.events = events
        self.grammar = grammar
        self.conversation = conversation
        self.facts: dict[str, Any] = dict(facts)
        self.slot_facts = dict(slot_facts)

    @classmethod
    def load(
        cls,
        agent_toml: str | Path = "agent.toml",
        *,
        board_id: str = "sim-default",
        facts: Mapping[str, Any] | None = None,
        registry: GateRegistry | None = None,
        clock: Clock = monotonic_ms,
        events: EventLog | None = None,
    ) -> SimSession:
        """
        Build-check the agent for `sim`, then wire it up.

        `facts` overrides entries of `[sim.facts]`. `events` is where the session
        writes — a `TraceRecorder` to record it; its metadata is set from the
        agent and board. Raises `BuildFailed` with every problem when the agent
        does not fit the board.
        """
        build(agent_toml, target="sim", board_id=board_id, registry=registry)
        manifest = load_agent_manifest(agent_toml)
        grammar_path = manifest.root / "commands.toml"
        if not grammar_path.is_file():
            raise AgentManifestError(
                where=str(grammar_path),
                why="`sim` takes typed text, which needs the agent's command grammar (Q-15)",
                how="add commands.toml next to agent.toml (see `neuroedge new`)",
            )
        grammar = CommandGrammar.load(grammar_path)
        sim_facts, slot_facts = _sim_tables(manifest)

        if events is None:
            events = EventLog(clock)
        events.metadata.update(target="sim", board_id=board_id, agent_version=manifest.label)
        hal = SimHAL(load_board_by_id(board_id), events=events)
        load_actions(manifest)
        gates, _ = _resolve_gates(manifest, registry)  # build() has already vetted them
        engine = ActionContractEngine(
            gates,
            facts_source=SystemOne("sim", fallback=grammar, network="offline", events=events),
            clock=clock,
            events=events,
        )
        conversation = Conversation(engine=engine, hal=hal)
        return cls(
            manifest,
            hal=hal,
            events=events,
            grammar=grammar,
            conversation=conversation,
            facts={**sim_facts, **(facts or {})},
            slot_facts=slot_facts,
        )

    @property
    def pins(self) -> tuple[str, ...]:
        """The digital outputs this agent declares, in manifest order."""
        return tuple(self.manifest.requires.get("digital.out", {}).get("pins", ()))

    def gate_facts(self, recognition: Recognition) -> dict[str, Any]:
        facts = dict(self.facts)
        for criterion, (slot, expected) in self.slot_facts.items():
            if slot in recognition.slots:
                facts[criterion] = str(recognition.slots[slot]) == str(expected)
        return facts

    async def handle(self, text: str) -> Turn:
        """Run one typed line: recognise it, and `c.do()` the command's action."""
        self.hal.type_text(text)
        utterance = self.hal.audio_in(called_from="SimSession.handle()") or ""
        recognition = self.grammar.recognize(utterance)
        if not recognition.recognised:
            self.events.emit(
                "command_not_recognized",
                {
                    "text": utterance,
                    "confidence": recognition.confidence,
                    "threshold": self.grammar.threshold,
                },
            )
            return Turn(utterance, recognition)
        self.events.emit(
            "intent_extracted",
            {
                "intent": recognition.intent,
                "confidence": recognition.confidence,
                "system": "SystemOne",
                "backend": "local/command-grammar",
            },
        )
        turn = Turn(utterance, recognition)
        if turn.action is None:
            return turn
        c = self.conversation
        c.utterance = utterance
        c.facts = self.gate_facts(recognition)
        result = await c.do(turn.action, **turn.arguments)
        return Turn(utterance, recognition, result)

    def trace(self) -> dict[str, Any]:
        """The session so far as a `trace.v1` document, validated before it is returned."""
        trace = self.events.to_trace()
        validate_trace(trace, label=f"session {self.events.session_id}")
        return trace
