"""
TSK-S3-02 — replaying a trace on a live `SimHAL` (FR-CI-02).

The replay must *recompute* verdicts and pin commands from the recorded facts:
a test that only read the recording back would pass on any engine.
"""

from __future__ import annotations

import copy
import json

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
    recorder = TraceRecorder()
    session = SimSession.load(villa, events=recorder)
    for line in ("mở cửa phòng 101", "mở cửa phòng 202", "hát một bài", "mở cửa phòng 101"):
        await session.handle(line)
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
