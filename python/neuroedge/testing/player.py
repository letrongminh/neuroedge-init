"""
Replay a recorded trace on a live HAL (TSK-S3-02, FR-CI-02, FR-TRC-04/05).

A trace records, for every gate evaluation, the facts the verdict read. Replay
feeds exactly those facts back in and **recomputes** everything after them —
the gate verdict with today's gate documents, the verdict token, the @action
body, the pin commands on a real `SimHAL` (or `LinuxHAL`). Nothing in the
result is copied from the recording, so a changed gate, action or HAL shows up
as a different verdict or pin sequence (FR-CI-LVL, L1).

Per recorded evaluation, the inputs are:

* the facts — `gate_facts` (value + confidence) when the trace has it, else the
  values in `gate_evaluation_result.evaluations` (the canonical traces);
* a recorded degraded reason (`gate_unreachable`, `budget_exceeded`) — replayed
  as a fact source that is offline / times out;
* the action and its arguments — `action_requested` when present, else the
  agent's one @action behind that gate, with its default arguments.

What System 2 said (`tts_stream_start`) is not replayed and cannot be asserted
on: it is not deterministic (L3). `ReplayResult.replies` says so.
"""

from __future__ import annotations

import asyncio
import copy
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..actions import ActionResult, Conversation
from ..engine.compiler import AgentManifest, load_actions, load_agent_manifest, resolve_gates
from ..engine.gate import ActionContractEngine, GateResult
from ..engine.gate_resolver import GateRegistry
from ..engine.trace_sink import EventLog
from ..engine.verdict import DEGRADED_REASONS, Fact, Unavailable
from ..errors import AgentManifestError, ReplayError
from ..hal.board import load_board_by_id
from ..paths import fixtures_dir
from ..trace import load_trace, validate_trace

DEFAULT_BOARD = {"sim": "sim-default", "linux": "linux-rpi5"}
_DEGRADED_AS = {"gate_unreachable": "offline", "budget_exceeded": "timeout"}


@dataclass(frozen=True)
class RecordedStep:
    """One gate evaluation as the trace recorded it."""

    index: int
    gate: str
    facts: dict[str, Fact]
    result: dict[str, Any]
    action: str | None = None
    arguments: dict[str, Any] = field(default_factory=dict)

    @property
    def gate_name(self) -> str:
        return self.gate.partition("@")[0]

    @property
    def degraded(self) -> str | None:
        reason = self.result.get("reason")
        return reason if reason in DEGRADED_REASONS else None


def recorded_steps(trace: Mapping[str, Any]) -> list[RecordedStep]:
    """Every gate evaluation in a trace, with the inputs replay needs."""
    steps: list[RecordedStep] = []
    request: dict[str, Any] | None = None
    gate: str | None = None
    facts: dict[str, Fact] | None = None
    for event in trace.get("events", []):
        kind, data = event.get("type"), event.get("data", {})
        if kind == "action_requested":
            request = data
        elif kind == "gate_evaluation_begin":
            gate, facts = data.get("gate"), None
        elif kind == "gate_facts":
            facts = {
                name: Fact(
                    entry.get("value"), entry.get("confidence"), entry.get("source", "trace")
                )
                for name, entry in data.items()
            }
        elif kind == "gate_evaluation_result" and gate is not None:
            if facts is None:  # a trace from before gate_facts: values only
                facts = {
                    name: Fact(value, None, "trace")
                    for name, value in data.get("evaluations", {}).items()
                }
            steps.append(
                RecordedStep(
                    index=len(steps),
                    gate=gate,
                    facts=facts,
                    result=dict(data),
                    action=None if request is None else request.get("action"),
                    arguments=dict((request or {}).get("arguments", {})),
                )
            )
            request, gate, facts = None, None, None
    return steps


class _Unreachable:
    """The fact source of a degraded step: answers every criterion the same way."""

    def __init__(self, reason: str) -> None:
        self.answer = Unavailable(reason, "replayed from the trace")

    async def adjudicate(self, criterion, definition, state, deadline_ms=None):
        return self.answer


@dataclass
class Divergence:
    """The agent asked for something the recording does not have."""

    index: int
    expected: str | None
    actual: str


class _ReplayEngine(ActionContractEngine):
    """Serves each evaluation the facts of the next recorded step, in order."""

    def __init__(self, gates, steps: list[RecordedStep], *, network: str, **kwargs) -> None:
        super().__init__(gates, **kwargs)
        self.steps = steps
        self.cursor = 0
        self.network = network
        self.divergences: list[Divergence] = []

    def _next(self, key: str) -> RecordedStep | None:
        gate = self.gate(key)
        name = gate.name if gate is not None else key
        step = self.steps[self.cursor] if self.cursor < len(self.steps) else None
        self.cursor += 1
        if step is None or step.gate_name != name:
            self.divergences.append(
                Divergence(self.cursor - 1, None if step is None else step.gate, name)
            )
            return None
        return step

    async def evaluate(
        self, key, context=None, *, state=None, arguments=None, confirmed=False
    ) -> GateResult:
        step = self._next(key)
        # A person's "yes" is an input the trace recorded (RFC-0006), replayed as such.
        confirmed = bool(step is not None and step.result.get("confirmed"))
        facts: dict[str, Fact] = {}
        source = None
        if step is not None:
            facts = dict(step.facts)
            if self.network == "offline":
                # Only session context survives a network loss; model answers do not.
                facts = {k: f for k, f in facts.items() if f.source == "context"}
                source = _Unreachable("offline")
            elif step.degraded:
                source = _Unreachable(_DEGRADED_AS[step.degraded])
        self.facts_source = source
        return await super().evaluate(
            key, facts, state=state, arguments=arguments, confirmed=confirmed
        )


# --- the result ------------------------------------------------------------------


@dataclass(frozen=True)
class ActionState:
    name: str
    blocked: bool


@dataclass(frozen=True)
class GateState:
    name: str
    verdict: str


@dataclass
class ReplayResult:
    recorded: dict[str, Any]
    replayed: dict[str, Any]
    steps: list[RecordedStep]
    actions: list[ActionResult]
    hal: Any
    divergences: list[Divergence]
    target: str
    slow: str | None = None

    # -- verdict sequence ------------------------------------------------------
    @property
    def gate_results(self) -> list[dict[str, Any]]:
        return [e["data"] for e in self.replayed["events"] if e["type"] == "gate_evaluation_result"]

    @property
    def verdicts(self) -> list[str]:
        return [result["verdict"] for result in self.gate_results]

    @property
    def recorded_verdicts(self) -> list[str]:
        return [step.result.get("verdict") for step in self.steps]

    def _last_block(self) -> dict[str, Any]:
        blocks = [r for r in self.gate_results if r["verdict"] == "BLOCK"]
        return blocks[-1] if blocks else {}

    @property
    def blocked_by(self) -> str | None:
        return self._last_block().get("blocked_by")

    @property
    def escalated_to(self) -> str | None:
        return self._last_block().get("escalated_to")

    @property
    def reason(self) -> str | None:
        return self._last_block().get("reason")

    # -- the proposal §4.7 surface --------------------------------------------
    def action(self, name: str) -> ActionState:
        runs = [a for a in self.actions if a.action == name]
        # An action the replay never ran is, physically, blocked.
        return ActionState(name, blocked=not runs or all(a.blocked for a in runs))

    def gate(self, name: str) -> GateState:
        results = [
            r
            for r, begin in zip(self.gate_results, self._begins(), strict=False)
            if begin.partition("@")[0] == name.partition("@")[0]
        ]
        return GateState(name, results[-1]["verdict"] if results else "BLOCK")

    def _begins(self) -> list[str]:
        return [
            e["data"]["gate"]
            for e in self.replayed["events"]
            if e["type"] == "gate_evaluation_begin"
        ]

    def pin(self, name: str):
        return self.hal.pin(name)

    @property
    def replies(self):
        raise AssertionError(
            "L3 (FR-CI-LVL): what System 2 says is not deterministic and is never asserted "
            "on. Assert the gate verdict and the pins instead: "
            "assert_gate_blocked(result, ...), assert_never_pulsed(result, ...)"
        )


# --- the player ------------------------------------------------------------------


def _load(trace: str | Path | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(trace, Mapping):
        data = copy.deepcopy(dict(trace))
        validate_trace(data)
        return data
    path = Path(trace)
    if not path.exists() and not path.is_absolute():
        candidate = fixtures_dir() / "traces" / path.name
        if candidate.is_file():
            path = candidate
    return load_trace(path)


def _agent_for(trace: Mapping[str, Any], agent: str | Path | None) -> AgentManifest:
    if agent is not None:
        return load_agent_manifest(agent)
    name = str(trace["metadata"].get("agent_version", "")).partition("@")[0]
    sample = fixtures_dir() / "agents" / name / "agent.toml"
    if name and sample.is_file():
        return load_agent_manifest(sample)
    raise AgentManifestError(
        where="trace metadata.agent_version",
        why=f"no agent.toml given, and no sample agent named {name!r} in {fixtures_dir() / 'agents'}",
        how="pass the agent that produced the trace: TracePlayer(trace, agent='agent.toml')",
    )


def make_hal(target: str, board_id: str | None, events: EventLog):
    if target not in DEFAULT_BOARD:
        raise ReplayError(
            where=f"--target {target}",
            why=f"replay runs on a live HAL; {target!r} has none on this machine",
            how="replay on sim or linux; esp32s3 replay arrives with TSK-S4-04",
        )
    board = load_board_by_id(board_id or DEFAULT_BOARD[target])
    if target == "sim":
        from ..hal.sim import SimHAL

        return SimHAL(board, events=events)
    from ..hal.linux import LinuxHAL

    return LinuxHAL(board, events=events)


class TracePlayer:
    def __init__(
        self,
        trace: str | Path | Mapping[str, Any],
        *,
        target: str = "sim",
        agent: str | Path | None = None,
        board_id: str | None = None,
        hal: Any = None,
        network: str = "online",
        slow: str | None = None,
        registry: GateRegistry | None = None,
    ) -> None:
        self.trace = _load(trace)
        self.target = target
        self.manifest = _agent_for(self.trace, agent)
        self.board_id = board_id
        self.hal = hal
        self.network = network
        self.slow = slow  # accepted for the §4.7 API; System 2 never changes a verdict
        self.registry = registry

    def _action_for(self, step: RecordedStep, actions: list[Any], gates) -> str:
        if step.action is not None:
            return step.action
        keys = {key for key, gate in gates.items() if gate.name == step.gate_name}
        matches = sorted(spec.name for spec in actions if spec.gate in keys)
        if len(matches) != 1:
            raise ReplayError(
                where=f"trace event gate_evaluation_begin #{step.index} ({step.gate})",
                why=(
                    f"the trace does not say which action asked for this gate, and the agent "
                    f"has {len(matches)} action(s) behind it: {matches}"
                ),
                how="re-record the session with `neuroedge record` (it writes action_requested)",
            )
        return matches[0]

    async def replay(self) -> ReplayResult:
        steps = recorded_steps(self.trace)
        events = EventLog(
            session_id=self.trace["metadata"]["session_id"],
            target=self.target,
            board_id=self.board_id or DEFAULT_BOARD.get(self.target, ""),
            agent_version=self.manifest.label,
        )
        hal = self.hal if self.hal is not None else make_hal(self.target, self.board_id, events)
        if self.hal is not None and hasattr(hal, "events"):
            hal.events = events
        _script_sensors(hal, self.trace)
        actions = load_actions(self.manifest)
        gates, problems = resolve_gates(self.manifest, self.registry)
        if problems:
            raise problems[0]
        engine = _ReplayEngine(gates, steps, network=self.network, events=events)
        conversation = Conversation(engine=engine, hal=hal)

        results: list[ActionResult] = []
        try:
            while engine.cursor < len(steps):
                step = steps[engine.cursor]
                name = self._action_for(step, actions, gates)
                results.append(await conversation.do(name, **step.arguments))
        finally:
            # A divergence or a contract error must not leave a real line driven (linux).
            close = getattr(hal, "close", None)
            if close is not None:
                close()
        return ReplayResult(
            recorded=self.trace,
            replayed=events.to_trace(),
            steps=steps,
            actions=results,
            hal=hal,
            divergences=engine.divergences,
            target=self.target,
            slow=self.slow,
        )


def _script_sensors(hal: Any, trace: Mapping[str, Any]) -> None:
    """
    Feed the recorded readings back, in order (docs/spec/simulation_coverage.md §3).
    Reads made to compute a gate fact (`use: fact`) are not replayed: their result
    is already in `gate_facts`.
    """
    readings: dict[str, list[Any]] = {}
    units: dict[str, str] = {}
    for event in trace.get("events", []):
        data = event.get("data", {})
        if event.get("type") == "sensor_read" and "use" not in data:
            readings.setdefault(data["sensor"], []).append(data.get("value"))
            if "unit" in data:
                units[data["sensor"]] = data["unit"]
    script = getattr(hal, "script_sensor", None)
    if readings and script is None:
        raise ReplayError(
            where=f"replay on {getattr(hal, 'target', '?')}",
            why="the trace reads sensors, and this HAL cannot be fed recorded readings",
            how="replay on sim, or wait for sensor.read on this target (simulation_coverage.md)",
        )
    for sensor, values in readings.items():
        script(sensor, values, units.get(sensor))


def replay_sync(trace, **kwargs) -> ReplayResult:
    """`TracePlayer(...).replay()` for synchronous callers (pytest functions, the CLI)."""
    return asyncio.run(TracePlayer(trace, **kwargs).replay())


def dump(result: ReplayResult, path: str | Path) -> None:
    Path(path).write_text(
        json.dumps(result.replayed, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
