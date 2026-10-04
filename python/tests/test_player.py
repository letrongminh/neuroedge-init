"""
TSK-S3-02 — replaying a trace on a live `SimHAL` (FR-CI-02).

The replay must *recompute* verdicts and pin commands from the recorded facts:
a test that only read the recording back would pass on any engine.
"""

from __future__ import annotations

import copy
import json
import re

import pytest

from neuroedge.actions import Conversation
from neuroedge.engine.compiler import load_actions, load_agent_manifest, resolve_gates
from neuroedge.engine.gate import ActionContractEngine
from neuroedge.errors import AgentManifestError, ReplayError
from neuroedge.hal.sim import SimHAL
from neuroedge.sim import SimSession
from neuroedge.testing import TracePlayer, recorded_steps, replay, scenario
from neuroedge.testing.recorder import TraceRecorder
from neuroedge.trace import validate_trace


class HandClock:
    """A clock that moves only when the test says so (milliseconds)."""

    def __init__(self) -> None:
        self.now = 1_000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, ms: float) -> None:
        self.now += ms


@pytest.fixture(scope="module")
def villa(root):
    return root / "fixtures" / "agents" / "villa-concierge" / "agent.toml"


def canonical(traces_dir, name):
    return json.loads((traces_dir / f"{name}.json").read_text(encoding="utf-8"))


# --- the three canonical traces ---------------------------------------------------


def test_happy_path_pulses_the_lock_once_for_30_seconds(traces_dir):
    result = replay(traces_dir / "happy-path.json")
    assert result.verdicts == ["ALLOW"]
    assert result.pin("door_lock").pulsed_once(duration_ms=30000)
    assert result.hal.target == "sim"
    validate_trace(result.replayed)


def test_unverified_attempt_blocks_escalates_and_never_touches_the_pin(traces_dir):
    result = replay(traces_dir / "unverified_attempt.json")
    assert result.verdicts == ["BLOCK"]
    assert result.blocked_by == "unlock_door@1.2.0"
    assert result.escalated_to == "human_receptionist"
    assert result.action("unlock_door").blocked
    assert result.pin("door_lock").never_pulsed()


def test_network_offline_replays_as_gate_unreachable(traces_dir):
    result = replay(traces_dir / "network_offline.json")
    assert result.verdicts == ["BLOCK"]
    assert result.reason == "gate_unreachable"
    assert result.gate_results[0]["fail_mode"] == "closed"
    assert result.pin("door_lock").never_pulsed()


def test_the_happy_path_offline_is_blocked_as_unreachable(traces_dir):
    result = scenario(traces_dir / "happy-path.json", network="offline")
    assert result.reason == "gate_unreachable"
    assert result.pin("door_lock").never_pulsed()


def test_a_bare_name_resolves_to_the_canonical_trace():
    assert replay("happy-path.json").verdicts == ["ALLOW"]


# --- the gate the trace was decided by (RFC-0008) -----------------------------------------


def test_canonical_traces_carry_the_compiled_gate_digest(traces_dir, root):
    """RFC-0008: every gate_evaluation_begin of the normative traces names the gate's digest."""
    from neuroedge.engine.compiler import load_agent_manifest, resolve_gates
    from neuroedge.engine.decision_tree import compile_tree

    manifest = load_agent_manifest(root / "fixtures" / "agents" / "villa-concierge" / "agent.toml")
    gates, problems = resolve_gates(manifest)
    assert problems == []
    digests = {tree["gate"]: tree["gate_digest"] for tree in map(compile_tree, gates.values())}
    for name in ("happy-path", "unverified_attempt", "network_offline"):
        trace = canonical(traces_dir, name)
        begins = [e for e in trace["events"] if e["type"] == "gate_evaluation_begin"]
        assert begins
        for begin in begins:
            assert begin["data"]["gate_digest"] == digests[begin["data"]["gate"]]


def test_verify_refuses_a_trace_decided_by_another_gate(traces_dir):
    trace = canonical(traces_dir, "happy-path")
    for event in trace["events"]:
        if event["type"] == "gate_evaluation_begin":
            event["data"]["gate_digest"] = "sha256:" + "0" * 64
    # `neuroedge verify` runs the player with enforce_gate_digests (RFC-0008): the
    # canonical trace must be decided by the very gate it was recorded with.
    with pytest.raises(ReplayError, match="decides unlock_door@1.2.0 as.*compiles it to"):
        replay(trace, enforce_gate_digests=True)


def test_replay_reports_a_gate_that_changed_since_the_recording(traces_dir, copy_agent, root):
    """A tightened gate is not a replay error: the verdicts are recomputed, the user is told."""
    source = (root / "gates" / "unlock_door@1.2.0.yaml").read_text(encoding="utf-8")
    manifest = (root / "fixtures" / "agents" / "villa-concierge" / "agent.toml").read_text(
        encoding="utf-8"
    )
    agent = copy_agent(
        "villa-concierge",
        files={
            "gates/unlock_door@1.2.0.yaml": source.replace(
                "risk_level:   { lte: low }", "risk_level:   { eq: low }"
            ),
            "agent.toml": manifest.replace(
                'unlock_door = "neuroedge://gates/unlock_door@1.2.0"',
                'unlock_door = "gates/unlock_door@1.2.0.yaml"',
            ),
        },
    )
    result = replay(traces_dir / "happy-path.json", agent=agent)
    assert result.verdicts == ["ALLOW"]
    assert result.pin("door_lock").pulsed_once(duration_ms=30000)
    [warning] = [w for w in result.warnings if w.startswith("unlock_door@1.2.0 changed")]
    recorded = next(
        e["data"]["gate_digest"]
        for e in canonical(traces_dir, "happy-path")["events"]
        if e["type"] == "gate_evaluation_begin"
    )
    old, new = re.findall(r"sha256:[0-9a-f]{64}", warning)
    assert old == recorded != new
    assert "replay recomputed the verdicts with the current gate" in warning


def test_a_trace_without_gate_digest_replays_unchanged(traces_dir):
    """A trace recorded before RFC-0008 has nothing to compare: replay stays as it was."""
    trace = canonical(traces_dir, "happy-path")
    for event in trace["events"]:
        if event["type"] == "gate_evaluation_begin":
            del event["data"]["gate_digest"]
    result = replay(trace)
    assert result.verdicts == ["ALLOW"]
    assert result.pin("door_lock").pulsed_once(duration_ms=30000)
    assert result.warnings == []
    enforce = replay(trace, enforce_gate_digests=True)
    assert enforce.verdicts == ["ALLOW"]
    assert enforce.warnings == []


# --- replay recomputes, it does not copy ----------------------------------------------


def test_changing_a_recorded_fact_changes_the_replayed_verdict(traces_dir):
    trace = canonical(traces_dir, "happy-path")
    for event in trace["events"]:
        if event["type"] == "gate_evaluation_result":
            event["data"]["evaluations"]["risk_level"] = "medium"
    result = replay(trace)
    # The recording still says ALLOW; the gate, evaluated again, does not.
    assert result.recorded_verdicts == ["ALLOW"]
    assert result.verdicts == ["BLOCK"]
    assert result.gate_results[0]["failed_criterion"] == "risk_level"
    assert result.pin("door_lock").never_pulsed()


def test_a_trace_without_a_verdict_the_agent_needs_blocks(traces_dir):
    trace = canonical(traces_dir, "happy-path")
    for event in trace["events"]:
        if event["type"] == "gate_evaluation_result":
            del event["data"]["evaluations"]["room_matches"]
    result = replay(trace)
    assert result.gate_results[0]["reason"] == "criterion_unavailable"


def test_the_input_trace_is_not_modified(traces_dir):
    trace = canonical(traces_dir, "happy-path")
    before = copy.deepcopy(trace)
    replay(trace)
    assert trace == before


# --- round trip: record on sim, replay on sim -------------------------------------------


async def test_a_recorded_session_replays_to_the_same_verdicts_and_pins(villa):
    clock = HandClock()
    recorder = TraceRecorder(clock=clock)
    session = SimSession.load(villa, events=recorder, clock=clock)
    for line in ("mở cửa phòng 101", "mở cửa phòng 202", "hát một bài", "mở cửa phòng 101"):
        await session.handle(line)
        # the door pulses 30 s: the safety envelope lets the next unlock come once it is over
        clock.advance(40_000)
    trace = recorder.to_trace()

    result = await TracePlayer(trace, agent=villa).replay()
    assert result.verdicts == result.recorded_verdicts == ["ALLOW", "BLOCK", "ALLOW"]
    assert result.pin("door_lock").commands == session.hal.pin("door_lock").commands
    requests = [e["data"] for e in result.replayed["events"] if e["type"] == "action_requested"]
    assert [r["arguments"] for r in requests] == [
        {"guest_id": "101"},
        {"guest_id": "202"},
        {"guest_id": "101"},
    ]
    assert result.divergences == []


async def test_recorded_confidence_is_replayed(villa):
    recorder = TraceRecorder()
    session = SimSession.load(villa, events=recorder)
    await session.handle("mở cửa phòng 101")
    trace = recorder.to_trace()
    for event in trace["events"]:
        if event["type"] == "gate_facts":
            event["data"]["guest_authenticated"]["confidence"] = 0.97
    (step,) = recorded_steps(trace)
    assert step.facts["guest_authenticated"].confidence == 0.97
    assert step.action == "unlock_door"


# --- degrade: the fallback consumes its own recorded step ---------------------------------


def _degrade_agent(tmp_path):
    suffix = abs(hash(str(tmp_path)))
    main, fallback = f"open_gate_{suffix}", f"notify_desk_{suffix}"
    (tmp_path / "actions").mkdir()
    (tmp_path / "actions" / "acts.py").write_text(
        "from neuroedge import action\nfrom neuroedge.hal import digital\n\n"
        f'@action(name="{main}", requires="digital.out:gate_relay", gate="main")\n'
        "def open_gate() -> None:\n"
        '    digital.out("gate_relay").pulse(seconds=2)\n\n'
        f'@action(name="{fallback}", requires="digital.out:porch_light", gate="safe")\n'
        "def notify() -> None:\n"
        '    digital.out("porch_light").pulse(seconds=1)\n',
        encoding="utf-8",
    )
    common = "budget:\n  p95_latency_ms: 100\n  fail: closed\n"
    (tmp_path / "main.yaml").write_text(
        "schema: neuroedge.gate/v1\nname: main\nversion: 1.0.0\n"
        "evaluate:\n  ok:\n    type: bool\n    instructions: ok\n"
        "allow_when:\n  ok: true\n"
        f"on_block:\n  action: degrade\n  fallback_action: {fallback}\n" + common,
        encoding="utf-8",
    )
    (tmp_path / "safe.yaml").write_text(
        "schema: neuroedge.gate/v1\nname: safe\nversion: 1.0.0\n"
        "evaluate:\n  lit:\n    type: bool\n    instructions: lit\n"
        "allow_when:\n  lit: true\n"
        "on_block:\n  action: deny\n" + common,
        encoding="utf-8",
    )
    (tmp_path / "agent.toml").write_text(
        '[agent]\nname = "degrade-test"\nversion = "0.1.0"\n\n'
        '[requires]\n"digital.out" = { pins = ["gate_relay", "porch_light"] }\n\n'
        '[gates]\nmain = "main.yaml"\nsafe = "safe.yaml"\n',
        encoding="utf-8",
    )
    return tmp_path / "agent.toml", main, fallback


async def test_a_degrade_fallback_replays_through_its_own_gate(tmp_path):
    agent, main, fallback = _degrade_agent(tmp_path)
    manifest = load_agent_manifest(agent)
    load_actions(manifest)
    gates, problems = resolve_gates(manifest)
    assert problems == []
    recorder = TraceRecorder()
    engine = ActionContractEngine(gates, events=recorder)
    hal = SimHAL(events=recorder)
    c = Conversation(engine=engine, hal=hal, facts={"ok": False, "lit": True})
    recorded = await c.do(main)
    assert recorded.fallback is not None and not recorded.fallback.blocked

    result = await TracePlayer(recorder.to_trace(), agent=agent).replay()
    assert result.verdicts == result.recorded_verdicts == ["BLOCK", "ALLOW"]
    assert len(result.actions) == 1, "the fallback runs inside the first c.do(), not again"
    assert result.pin("gate_relay").never_pulsed()
    assert result.pin("porch_light").pulsed_once(duration_ms=1000)


# --- refusals ---------------------------------------------------------------------------


def test_an_unknown_agent_is_a_manifest_error(traces_dir):
    trace = canonical(traces_dir, "happy-path")
    trace["metadata"]["agent_version"] = "nobody@1.0.0"
    with pytest.raises(AgentManifestError, match="agent_version"):
        TracePlayer(trace)


def test_a_gate_the_agent_does_not_have_cannot_be_replayed(traces_dir):
    trace = canonical(traces_dir, "happy-path")
    for event in trace["events"]:
        if event["type"] == "gate_evaluation_begin":
            event["data"]["gate"] = "order_food@1.0.0"
    with pytest.raises(ReplayError, match="0 action"):
        replay(trace)


def test_replies_cannot_be_asserted_on(traces_dir):
    result = replay(traces_dir / "happy-path.json")
    with pytest.raises(AssertionError, match="L3"):
        _ = result.replies


def test_esp32s3_has_no_live_hal_here(traces_dir):
    with pytest.raises(ReplayError, match="esp32s3"):
        replay(traces_dir / "happy-path.json", target="esp32s3")


# --- the safety envelope replays on the recorded timeline (RFC-0007 §3d, TSK-N2-02) -------------


async def _session_with_a_refused_unlock(villa):
    """Unlock at 0 s; again 5 s later (the door still pulses: refused); a third 40 s later."""
    from neuroedge.errors import EnvelopeRefusedError

    clock = HandClock()
    recorder = TraceRecorder(clock=clock)
    session = SimSession.load(villa, events=recorder, clock=clock)
    await session.handle("mở cửa phòng 101")
    clock.advance(5_000)
    with pytest.raises(EnvelopeRefusedError):
        await session.handle("mở cửa phòng 101")
    clock.advance(40_000)
    await session.handle("mở cửa phòng 101")
    return session, recorder.to_trace()


async def test_a_recorded_envelope_refusal_replays_as_the_same_refusal(villa):
    session, trace = await _session_with_a_refused_unlock(villa)
    recorded = [e["data"] for e in trace["events"] if e["type"] == "envelope_refused"]
    assert [(r["pin"], r["operation"], r["reason"]) for r in recorded] == [
        ("door_lock", "pulse", "already_on")
    ]
    (refused_step,) = [s for s in recorded_steps(trace) if s.refusal is not None]
    assert refused_step.index == 1 and refused_step.refusal == recorded[0]

    result = await TracePlayer(trace, agent=villa).replay()
    replayed = [e["data"] for e in result.replayed["events"] if e["type"] == "envelope_refused"]
    assert replayed == recorded, "the same refusal, with the same numbers, at the recorded instant"
    assert result.divergences == []
    assert result.pin("door_lock").commands == session.hal.pin("door_lock").commands
    assert len(result.pin("door_lock").pulses) == 2


async def test_a_replay_decides_on_recorded_time_not_on_how_fast_it_runs(villa):
    """The recording ran 45 s of session time; the replay takes milliseconds and agrees."""
    _, trace = await _session_with_a_refused_unlock(villa)
    first = await TracePlayer(trace, agent=villa).replay()
    second = await TracePlayer(trace, agent=villa).replay()
    assert first.divergences == second.divergences == []
    assert [e["data"] for e in first.replayed["events"] if e["type"] == "envelope_refused"] == [
        e["data"] for e in second.replayed["events"] if e["type"] == "envelope_refused"
    ]


async def test_a_refusal_the_recording_does_not_have_is_a_divergence(villa):
    _, trace = await _session_with_a_refused_unlock(villa)
    trace["events"] = [e for e in trace["events"] if e["type"] != "envelope_refused"]
    result = await TracePlayer(trace, agent=villa).replay()
    (divergence,) = result.divergences
    assert divergence.expected is None
    assert divergence.actual == "envelope_refused door_lock pulse: already_on"


async def test_a_recorded_refusal_the_replay_does_not_make_is_a_divergence(villa):
    _, trace = await _session_with_a_refused_unlock(villa)
    # everything after the first unlock moves 30 s later: the door was free by the time of the
    # second one, so the refusal the recording holds is no longer what the envelope decides
    first = next(i for i, e in enumerate(trace["events"]) if e["type"] == "actuator_command")
    for event in trace["events"][first + 1 :]:
        event["offset_ms"] += 30_000
    result = await TracePlayer(trace, agent=villa).replay()
    (divergence,) = result.divergences
    assert divergence.expected == "envelope_refused door_lock pulse: already_on"
    assert divergence.actual == "no refusal"


async def test_a_refusal_for_another_reason_is_a_divergence(villa):
    _, trace = await _session_with_a_refused_unlock(villa)
    next(e for e in trace["events"] if e["type"] == "envelope_refused")["data"]["reason"] = (
        "window_budget"
    )
    result = await TracePlayer(trace, agent=villa).replay()
    (divergence,) = result.divergences
    assert divergence.expected == "envelope_refused door_lock pulse: window_budget"
    assert divergence.actual == "envelope_refused door_lock pulse: already_on"
