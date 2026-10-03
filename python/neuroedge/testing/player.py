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

`gate_evaluation_begin` also records `gate_digest` (RFC-0008): the digest of the
gate the verdict was computed with. One comparison,
`gate_digest_changes`, serves three callers with two policies — `neuroedge
verify` on the canonical traces *errors* (a canonical trace must be decided by
the very gate it was recorded with, like the device check), `neuroedge replay`
on a user's own trace *warns* (the gate may have been tightened on purpose) and
keeps recomputing verdicts; a trace without the field replays exactly as before.

What System 2 said (`tts_stream_start`) is not replayed and cannot be asserted
on: it is not deterministic (L3). `ReplayResult.replies` says so.
"""

from __future__ import annotations

import asyncio
import copy
import json
import tomllib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from ..actions import ActionResult, Conversation
from ..engine.compiler import AgentManifest, load_actions, load_agent_manifest, resolve_gates
from ..engine.gate import ActionContractEngine, GateResult
from ..engine.gate_resolver import GateRegistry, ResolvedGate
from ..engine.trace_sink import EventLog
from ..engine.verdict import DEGRADED_REASONS, DIGITAL_IN_SOURCE, Fact, Unavailable
from ..errors import AgentManifestError, EnvelopeRefusedError, ReplayError
from ..hal import ensure_envelope
from ..hal.board import load_board_by_id
from ..hal.sim import reading_value
from ..paths import fixtures_dir
from ..trace import load_trace, validate_trace
from .recorder import DEFAULT_ANONYMIZE, anonymise

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
    # RFC-0009: per numeric criterion, (read_offset_ms, eval_offset_ms, age_ms) as recorded and
    # found consistent; `mark_problems` says, per criterion, why a recorded reading was refused.
    marks: dict[str, tuple[int, int, int]] = field(default_factory=dict)
    mark_problems: dict[str, str] = field(default_factory=dict)
    # RFC-0007 §3d: the trace offset in ms of the verdict, and of the command that followed it
    # (it reached the pin, or the envelope refused it). The replayed envelope decides at the
    # command's instant on a clock of its own, never the wall clock. `refusal` is the
    # `envelope_refused` data recorded for the step, if the envelope refused the command.
    at_ms: int = 0
    command_ms: int | None = None
    refusal: dict[str, Any] | None = None

    @property
    def gate_name(self) -> str:
        return self.gate.partition("@")[0]

    @property
    def degraded(self) -> str | None:
        reason = self.result.get("reason")
        return reason if reason in DEGRADED_REASONS else None


_NON_FINITE = {"nan": float("nan"), "inf": float("inf"), "-inf": float("-inf")}
_MARK_KEYS = ("read_offset_ms", "eval_offset_ms", "age_ms")


def _whole(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _numeric_entry(
    entry: Mapping[str, Any], window: tuple[int, int] | None
) -> tuple[Any, tuple[int, int, int] | None, str | None]:
    """
    ``(value, marks, problem)`` of a `gate_facts` entry that carries numeric read marks.

    `marks` is None, and the reading therefore unavailable, unless all three marks are whole
    milliseconds, the recorded age is exactly `eval_offset_ms - read_offset_ms`, and the
    evaluation instant lies within the evaluation's own events (RFC-0009 §5, §9.8): replay
    never trusts an age the trace cannot account for.
    """
    value = entry.get("value")
    if isinstance(value, str) and value in _NON_FINITE:
        value = _NON_FINITE[value]
    missing = [key for key in _MARK_KEYS if key not in entry]
    if missing:
        return value, None, f"read marks incomplete, missing {', '.join(missing)}"
    read_off, eval_off, recorded = (entry[key] for key in _MARK_KEYS)
    if not (_whole(read_off) and _whole(eval_off) and _whole(recorded)):
        return value, None, "read marks are not whole milliseconds"
    if recorded != eval_off - read_off:
        return (
            value,
            None,
            f"recorded age_ms={recorded} differs from eval_offset_ms - read_offset_ms "
            f"({eval_off - read_off})",
        )
    if window is not None and not window[0] <= eval_off <= window[1] + 1:
        return value, None, "eval_offset_ms lies outside the events of this evaluation"
    return value, (read_off, eval_off, eval_off - read_off), None


def recorded_steps(trace: Mapping[str, Any]) -> list[RecordedStep]:
    """Every gate evaluation in a trace, with the inputs replay needs."""
    steps: list[RecordedStep] = []
    request: dict[str, Any] | None = None
    gate: str | None = None
    begin_offset = 0
    raw_facts: Mapping[str, Any] | None = None
    open_step = False  # the commands that follow a verdict belong to its step
    for event in trace.get("events", []):
        kind, data = event.get("type"), event.get("data", {})
        if kind in ("action_requested", "gate_evaluation_begin"):
            open_step = False
        if kind == "action_requested":
            request = data
        elif (
            open_step
            and steps
            and steps[-1].command_ms is None
            and (kind == "envelope_refused" or (kind == "actuator_command" and "cause" not in data))
        ):
            steps[-1] = replace(
                steps[-1],
                command_ms=event.get("offset_ms", 0),
                refusal=dict(data) if kind == "envelope_refused" else None,
            )
        elif kind == "gate_evaluation_begin":
            gate, raw_facts = data.get("gate"), None
            begin_offset = event.get("offset_ms", 0)
        elif kind == "gate_facts":
            raw_facts = data
        elif kind == "gate_evaluation_result" and gate is not None:
            marks: dict[str, tuple[int, int, int]] = {}
            problems: dict[str, str] = {}
            if raw_facts is None:  # a trace from before gate_facts: values only
                facts = {
                    name: Fact(value, None, "trace")
                    for name, value in data.get("evaluations", {}).items()
                }
            else:
                window = (begin_offset, event.get("offset_ms", begin_offset))
                facts = {}
                for name, entry in raw_facts.items():
                    if not isinstance(entry, dict):
                        facts[name] = Fact(entry)
                    elif any(key in entry for key in _MARK_KEYS):
                        value, mark, problem = _numeric_entry(entry, window)
                        facts[name] = Fact(
                            value,
                            entry.get("confidence"),
                            entry.get("source", "trace"),
                            age_ms=None if mark is None else mark[2],
                        )
                        if mark is not None:
                            marks[name] = mark
                        if problem is not None:
                            problems[name] = problem
                    else:
                        facts[name] = Fact(
                            entry.get("value"),
                            entry.get("confidence"),
                            entry.get("source", "trace"),
                        )
            steps.append(
                RecordedStep(
                    index=len(steps),
                    gate=gate,
                    facts=facts,
                    result=dict(data),
                    action=None if request is None else request.get("action"),
                    arguments=dict((request or {}).get("arguments", {})),
                    marks=marks,
                    mark_problems=problems,
                    at_ms=event.get("offset_ms", begin_offset),
                )
            )
            request, gate, raw_facts = None, None, None
            open_step = True
    return steps


# --- the gate the trace was decided by (RFC-0008) -----------------------------------


@dataclass(frozen=True)
class GateDigestChange:
    """A gate_evaluation_begin whose `gate_digest` differs from what these gates compile to."""

    gate: str
    recorded: str | None
    current: str | None


def gate_digest_changes(
    events: Iterable[Mapping[str, Any]], gates: Mapping[str, ResolvedGate]
) -> list[GateDigestChange]:
    """
    Every `gate_evaluation_begin` whose recorded `gate_digest` (RFC-0008) differs from
    what `gates` compile to now — the one comparison behind the device check
    (`verify --targets esp32s3`), the host check on the canonical traces (`verify` on
    sim/linux, enforced) and the `replay` warning (a gate edited on purpose).

    A begin without the field — a trace recorded before RFC-0008 — yields a change with
    `recorded=None`, and a begin for a gate `gates` does not have yields `current=None`:
    the device check refuses both (a device always writes the field), while the host
    replay compares only changes where both sides exist (`_decided_changes`).
    """
    from ..engine.decision_tree import compile_tree

    digests: dict[str, str | None] = {}

    def compiled(label: str) -> str | None:
        if label not in digests:
            match = next((g for g in gates.values() if f"{g.name}@{g.version}" == label), None)
            digests[label] = None if match is None else compile_tree(match)["gate_digest"]
        return digests[label]

    changes: list[GateDigestChange] = []
    for event in events:
        if event.get("type") != "gate_evaluation_begin":
            continue
        data = event.get("data", {})
        label, recorded = data.get("gate"), data.get("gate_digest")
        if (current := compiled(label)) != recorded:
            changes.append(GateDigestChange(label, recorded, current))
    return changes


def _decided_changes(changes: list[GateDigestChange]) -> list[GateDigestChange]:
    """Those where both sides exist: a recorded digest that today's gate differs from."""
    return [
        change for change in changes if change.recorded is not None and change.current is not None
    ]


def _gate_digest_replay_error(change: GateDigestChange) -> ReplayError:
    """The canonical trace must be decided by the very gate it was recorded with."""
    return ReplayError(
        where=f"trace event gate_evaluation_begin ({change.gate})",
        why=f"the trace decides {change.gate} as {change.recorded}, "
        f"this checkout compiles it to {change.current}",
        how="a canonical trace is frozen with its gate (RFC-0008): changing either needs an RFC, "
        "then python/.venv/bin/python scripts/gen_firmware_vectors.py",
    )


def _gate_digest_warning(change: GateDigestChange) -> str:
    return (
        f"{change.gate} changed since the trace was recorded "
        f"({change.recorded} → {change.current}): replay recomputed the verdicts with the "
        "current gate"
    )


# --- numeric readings the trace cannot account for (RFC-0009 §5) -----------------------


@dataclass(frozen=True)
class FactMarkProblem:
    """A recorded numeric reading replay refused: its read marks do not add up."""

    gate: str | None
    criterion: str
    why: str


def fact_mark_problems(trace: Mapping[str, Any]) -> list[FactMarkProblem]:
    """Every recorded numeric reading whose read marks replay will not trust (it replays as unavailable)."""
    return [
        FactMarkProblem(step.gate, criterion, why)
        for step in recorded_steps(trace)
        for criterion, why in step.mark_problems.items()
    ]


def _fact_mark_warning(problem: FactMarkProblem) -> str:
    gate_label = f" in {problem.gate}" if problem.gate else ""
    return (
        f"numeric fact {problem.criterion!r}{gate_label}: {problem.why}; "
        "the trace was altered or is incomplete, so replay treats the reading as unavailable"
    )


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
        self._marks: dict[str, tuple[int, int, int]] = {}

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

    def _numeric_marks(
        self, criterion: str, fact: Fact, eval_offset_ms: int
    ) -> tuple[int, int, int] | None:
        """
        A replayed reading keeps the age `recorded_steps` found consistent in the trace, placed on
        the replay's own timeline, so the replayed trace accounts for its readings as well.
        """
        mark = self._marks.get(criterion)
        if mark is None:
            return None
        age = mark[2]
        return eval_offset_ms - age, eval_offset_ms, age

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
                # A digital.in level is the device's own read, not a model's answer.
                facts = {
                    k: f for k, f in facts.items() if f.source in ("context", DIGITAL_IN_SOURCE)
                }
                source = _Unreachable("offline")
            elif step.degraded:
                source = _Unreachable(_DEGRADED_AS[step.degraded])
        self.facts_source = source
        self._marks = {} if step is None else step.marks
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
    # What replay cannot check but a person should know — `neuroedge replay` prints it.
    warnings: list[str] = field(default_factory=list)

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
        how="pass the agent that recorded the trace: `neuroedge replay <trace> --agent "
        "path/to/agent.toml`, or run it in that agent's project (Python: TracePlayer(trace, "
        "agent='agent.toml'))",
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

    return LinuxHAL(board, events=events, replay=True)


class ReplayClock:
    """
    The clock the replayed safety envelope decides on (RFC-0007 §3d): the recorded instant of
    the command being replayed, in ms of trace time. The wall clock never enters a replay, so a
    command the envelope refused at 40 s of the recording is refused at 40 s of the replay.
    """

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


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
        enforce_gate_digests: bool = False,
    ) -> None:
        """
        `enforce_gate_digests` (RFC-0008): a recorded `gate_digest` that differs from
        what the resolved gates compile to is a `ReplayError` instead of a warning.
        `neuroedge verify` turns it on for the canonical traces — those must be decided
        by the very gate they were recorded with. A trace without the field replays
        exactly as before under both settings.
        """
        self.trace = _load(trace)
        self.target = target
        self.manifest = _agent_for(self.trace, agent)
        self.board_id = board_id
        self.hal = hal
        self.network = network
        self.slow = slow  # accepted for the §4.7 API; System 2 never changes a verdict
        self.registry = registry
        self.enforce_gate_digests = enforce_gate_digests

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
        actions = load_actions(self.manifest)
        gates, problems = resolve_gates(self.manifest, self.registry)
        if problems:
            raise problems[0]
        # RFC-0008: the recorded gate_digest against what this checkout compiles.
        changed = _decided_changes(gate_digest_changes(self.trace.get("events", []), gates))
        if changed and self.enforce_gate_digests:
            raise _gate_digest_replay_error(changed[0])
        hal = self.hal if self.hal is not None else make_hal(self.target, self.board_id, events)
        if self.hal is not None and hasattr(hal, "events"):
            hal.events = events
        # Pins are bounded by the board's envelope on every target, on the recorded timeline.
        envelope_clock = ReplayClock()
        ensure_envelope(hal, envelope_clock, virtual=True)
        _script_sensors(hal, self.trace)
        _script_i2c(hal, self.trace)
        _script_digital_in(hal, self.trace)
        _script_pin_state(hal, self.trace)
        warnings = _sensor_rules_changed(self.trace, self.manifest, events)
        warnings += [_gate_digest_warning(change) for change in changed]
        problems = fact_mark_problems(self.trace)
        for problem in problems:
            events.emit(
                "fact_mark_problem",
                {"gate": problem.gate, "criterion": problem.criterion, "why": problem.why},
            )
        warnings += [_fact_mark_warning(problem) for problem in problems]
        engine = _ReplayEngine(gates, steps, network=self.network, events=events)
        conversation = Conversation(engine=engine, hal=hal)

        results: list[ActionResult] = []
        recorded_events = self.trace.get("events", [])
        try:
            while engine.cursor < len(steps):
                step = steps[engine.cursor]
                name = self._action_for(step, actions, gates)
                envelope_clock.now = float(
                    step.command_ms if step.command_ms is not None else step.at_ms
                )
                refused: EnvelopeRefusedError | None = None
                try:
                    results.append(await conversation.do(name, **step.arguments))
                except EnvelopeRefusedError as refusal:
                    refused = refusal
                _check_refusal(step, refused, engine.divergences)
            # The recording ran on after its last command: a pin whose on-time ran out by then
            # went off in it, and goes off in the replay (its `cause` is part of the decisions).
            envelope = getattr(hal, "envelope", None)
            if envelope is not None:
                envelope_clock.now = max(
                    [envelope_clock.now, *(float(e.get("offset_ms", 0)) for e in recorded_events)]
                )
                envelope.settle()
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
            warnings=warnings,
        )


def _check_refusal(
    step: RecordedStep, refused: EnvelopeRefusedError | None, divergences: list[Divergence]
) -> None:
    """
    A recorded `envelope_refused` must replay as the same refusal, and a command the envelope
    let through must not be refused now: either difference is a divergence (RFC-0007 §3d). The
    refusal is compared by pin, operation and reason — the numbers follow from them.
    """
    recorded = step.refusal
    if recorded is None and refused is None:
        return
    key = ("pin", "operation", "reason")
    if (
        recorded is not None
        and refused is not None
        and all(recorded.get(k) == refused.event.get(k) for k in key)
    ):
        return
    divergences.append(
        Divergence(
            step.index,
            None if recorded is None else _refusal_label(recorded),
            "no refusal" if refused is None else _refusal_label(refused.event),
        )
    )


def _refusal_label(event: Mapping[str, Any]) -> str:
    return f"envelope_refused {event.get('pin')} {event.get('operation')}: {event.get('reason')}"


def _sensor_rules_changed(
    trace: Mapping[str, Any], manifest: AgentManifest, events: EventLog
) -> list[str]:
    """
    Replay feeds the recorded gate facts back; it cannot recompute a sensor fact.
    If `[sim.sensor_facts]` changed since the recording (its digest in the metadata),
    the verdicts say nothing about the new rules — which the person must be told.
    """
    recorded = trace.get("metadata", {}).get("sensor_facts_digest")
    if recorded is None:
        return []
    from ..sim.session import sensor_facts_digest

    sim = tomllib.loads(manifest.source.read_text(encoding="utf-8")).get("sim", {})
    current = sensor_facts_digest(sim)
    if current == recorded:
        return []
    events.emit("sensor_facts_changed", {"recorded": recorded, "current": current})
    return [
        f"[sim.sensor_facts] of {manifest.source} changed since the trace was recorded "
        f"({recorded} → {current}): replay feeds the recorded gate facts back, so these "
        "verdicts do not test the new rules — record the session again"
    ]


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
            readings.setdefault(data["sensor"], []).append(reading_value(data))
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


def _script_i2c(hal: Any, trace: Mapping[str, Any]) -> None:
    """
    Feed the recorded `i2c_read`s back, in order, per bus, device and register (RFC-0007
    §3b): a read that failed is fed back as a failure with its recorded reason. Replay never
    reaches a bus.
    """
    from ..hal.i2c_bus import ReadFault

    reads: dict[tuple[str, str, int | None], list[Any]] = {}
    for event in trace.get("events", []):
        data = event.get("data", {})
        if event.get("type") != "i2c_read":
            continue
        outcome = data["value"] if "value" in data else ReadFault(str(data.get("reason", "")))
        reads.setdefault((data["bus"], data["device"], data.get("register")), []).append(outcome)
    script = getattr(hal, "script_i2c", None)
    if reads and script is None:
        raise ReplayError(
            where=f"replay on {getattr(hal, 'target', '?')}",
            why="the trace reads I2C, and this HAL cannot be fed recorded readings",
            how="replay on sim or linux",
        )
    for (bus, device, register), values in reads.items():
        # The width only bounds what is scripted; the read checks the width it asks for.
        script(bus, device, register, values, width=1 if register is None else 2)


def _script_digital_in(hal: Any, trace: Mapping[str, Any]) -> None:
    """
    Feed the recorded `digital_in` levels back, in order (RFC-0007 §3a), to the reads an
    @action body makes — a read that failed (`reason`, no `value`) as a failed read again.
    Reads made to compute a gate fact (`use: fact`) are not replayed: what they gave is
    already in `gate_facts`.
    """
    levels: dict[str, list[bool | None]] = {}
    for event in trace.get("events", []):
        data = event.get("data", {})
        if event.get("type") == "digital_in" and "use" not in data:
            levels.setdefault(data["pin"], []).append(data.get("value"))
    script = getattr(hal, "script_digital_in", None)
    if levels and script is None:
        raise ReplayError(
            where=f"replay on {getattr(hal, 'target', '?')}",
            why="the trace reads input lines, and this HAL cannot be fed recorded levels",
            how="replay on sim or linux, or wait for digital.in on this target",
        )
    for pin, values in levels.items():
        script(pin, values)


def _script_pin_state(hal: Any, trace: Mapping[str, Any]) -> None:
    """
    Feed the recorded `pin_state` reads back, in order (RFC-0010 §3b), to the `state()` calls an
    @action body makes — each with the `source` it was recorded with, a read that failed
    (`reason`, no `source`) as a failed read again. Reads made to compute a gate fact
    (`use: fact`) are not replayed: what they gave is already in `gate_facts`.
    """
    states: dict[str, list[dict[str, Any] | None]] = {}
    for event in trace.get("events", []):
        data = event.get("data", {})
        if event.get("type") == "pin_state" and "use" not in data:
            entry = None if "source" not in data else dict(data)
            states.setdefault(data["pin"], []).append(entry)
    script = getattr(hal, "script_pin_state", None)
    if states and script is None:
        raise ReplayError(
            where=f"replay on {getattr(hal, 'target', '?')}",
            why="the trace reads the state of PWM channels, and this HAL cannot be fed recorded states",
            how="replay on sim or linux",
        )
    for pin, entries in states.items():
        script(pin, entries)


def replay_sync(trace, **kwargs) -> ReplayResult:
    """`TracePlayer(...).replay()` for synchronous callers (pytest functions, the CLI)."""
    return asyncio.run(TracePlayer(trace, **kwargs).replay())


def dump(result: ReplayResult, path: str | Path, *, anonymize: bool = DEFAULT_ANONYMIZE) -> None:
    """
    Write the replayed trace, hashed by default like every trace file (NFR-PRIV-03).
    `anonymize=False` (`--raw`) cannot bring back words the recording already hashed:
    the replayed trace of a hashed recording stays marked `anonymized: true`.
    """
    trace = result.replayed
    hashed = bool(anonymize) or bool(result.recorded.get("metadata", {}).get("anonymized"))
    metadata = {**trace["metadata"], "anonymized": hashed}
    if anonymize:
        trace = {
            **trace,
            "metadata": metadata,
            "events": [{**event, "data": anonymise(event["data"])} for event in trace["events"]],
        }
    else:
        trace = {**trace, "metadata": metadata}
    Path(path).write_text(json.dumps(trace, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
