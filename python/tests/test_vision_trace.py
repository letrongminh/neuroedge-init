"""
TSK-V1b-08 — vision evidence in the trace, and replay from it (RFC-0012 §3d, FR-CI-02).

The lint's counter-examples are the corpus in `fixtures/traces/invalid/vision_*.json`
(`test_trace_fixtures.py`). Here: what a *valid* trace of the live path looks like, the lint rules
that need a valid neighbour to show, and the replay that recomputes a verdict from the recorded
labels — with no model, no frame, no camera.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import yaml

from neuroedge.errors import TraceValidationError
from neuroedge.perception.vision import EVENT_TYPE, ScriptedVisionModel
from neuroedge.testing import TracePlayer, recorded_steps
from neuroedge.testing.player import vision_problems
from neuroedge.trace import VISION_EVENT, load_trace, validate_trace

from .vision_support import PERSON, Rig, gate, gate_document, person

ALLOW_WHEN = {"person_at_gate": True, "person_confidence": {"gte": 0.85}}


def _gates():
    return {
        "unlock_door": gate(
            "unlock_door", {"person_at_gate": True, "person_confidence": {"gte": 0.85}}
        )
    }


async def _record(script, *, frames=(1, 2, 3), prepare=None):
    """A live session of the vision path -> (rig, trace): the verdict is in `trace`."""
    rig = Rig(script, _gates())
    rig.events.emit("action_requested", {"action": "unlock_door", "arguments": {}})
    if prepare is not None:
        prepare(rig)
    rig.play(*frames)
    result = await rig.decide("unlock_door")
    return rig, rig.events.to_trace(), result


def _agent(copy_agent) -> Path:
    document = yaml.safe_dump(gate_document("unlock_door", ALLOW_WHEN), sort_keys=False)
    manifest = copy_agent("villa-concierge", files={"unlock_door.yaml": document})
    text = manifest.read_text("utf-8").replace(
        'unlock_door = "neuroedge://gates/unlock_door@1.2.0"', 'unlock_door = "unlock_door.yaml"'
    )
    manifest.write_text(text, encoding="utf-8")
    return manifest


def _events(trace, kind=VISION_EVENT):
    return [e for e in trace["events"] if e["type"] == kind]


GOOD = {1: [person(0.93)], 2: [person(0.91)], 3: [person(0.95)]}


# --- the trace the live path writes ------------------------------------------------------------


def test_the_event_name_is_one_name_in_both_places():
    assert VISION_EVENT == EVENT_TYPE == "vision_fact"


async def test_the_live_trace_validates_and_carries_no_image(tmp_path):
    rig, trace, _ = await _record(GOOD)
    validate_trace(trace)
    text = json.dumps(trace)
    assert "pixels-" not in text and "data:" not in text  # hashes and sizes, never pixels
    for event in _events(trace):
        for item in event["data"]["frames"]:
            assert set(item["vision_ref"]) == {"sha256", "size"}
    assert trace["metadata"]["vision_models"] == [rig.model.identity.to_json()]
    # and it survives the file round trip `neuroedge trace validate` takes
    path = tmp_path / "t.json"
    path.write_text(json.dumps(trace))
    load_trace(path)


async def test_only_the_frames_of_the_window_are_recorded():
    rig = Rig({i: [person(0.9)] for i in range(1, 7)}, _gates())
    rig.play(1, 2, 3, 4, 5)
    await rig.decide("unlock_door")
    for event in _events(rig.events.to_trace()):
        assert [f["frame_seq"] for f in event["data"]["frames"]] == [3, 4, 5]


async def test_a_model_swap_mid_session_leaves_every_verdict_traceable_to_its_model():
    rig = Rig({i: [person(0.9)] for i in range(1, 4)}, _gates())
    rig.play(1, 2, 3)
    await rig.decide("unlock_door")
    second = ScriptedVisionModel(
        {i: [person(0.9)] for i in range(4, 8)}, labels=[PERSON], name="person-det-v2"
    )
    rig.pipeline.set_model(second)
    rig.play(4, 5, 6)
    await rig.decide("unlock_door")
    trace = rig.events.to_trace()
    validate_trace(trace)
    by_model = {e["data"]["model"]["name"] for e in _events(trace)}
    assert by_model == {"person-det", "person-det-v2"}
    assert {m["name"] for m in trace["metadata"]["vision_models"]} == by_model


async def test_a_refused_window_is_recorded_and_valid_even_short_or_in_the_future():
    # short window: two frames of three
    rig, trace, result = await _record(GOOD, frames=(1, 2))
    validate_trace(trace)
    assert result.verdict.value == "BLOCK"
    assert _events(trace)[-1]["data"]["unavailable"] == "window_size"
    # a frame stamped after the instant it is judged at blocks, and the trace still validates
    rig = Rig(GOOD, _gates())
    rig.play(1, 2)
    rig.feed(3, ago=-80)
    await rig.decide("unlock_door")
    trace = rig.events.to_trace()
    validate_trace(trace)
    last = _events(trace)[-1]["data"]
    assert last["unavailable"] == "future" and last["age_ms"] >= 0
    # every frame in the future: the age itself is negative (RFC-0012 §3e), refused all the same
    rig = Rig(GOOD, _gates())
    for seq in (1, 2, 3):
        rig.clock.advance(33)
        rig.feed(seq, ago=-500)
    result = await rig.decide("unlock_door")
    trace = rig.events.to_trace()
    validate_trace(trace)
    last = _events(trace)[-1]["data"]
    assert last["unavailable"] == "future" and last["age_ms"] < 0
    assert result.reason.value == "criterion_unavailable"


def test_raw_capture_is_the_only_way_a_uri_gets_in():
    base = json.loads(
        (
            Path(__file__).resolve().parents[2]
            / "fixtures/traces/invalid/vision_uri_without_raw_capture.json"
        ).read_text()
    )
    with pytest.raises(TraceValidationError):
        validate_trace(base)
    base["metadata"]["raw_capture"] = True
    validate_trace(base)  # recorded on purpose: the uri is allowed (and only a string)
    base["events"][0]["data"]["frames"][1]["vision_ref"]["uri"] = 7
    with pytest.raises(TraceValidationError):
        validate_trace(base)


def test_the_three_canonical_traces_are_untouched_by_the_lint(traces_dir):
    for name in ("happy-path", "unverified_attempt", "network_offline"):
        trace = load_trace(traces_dir / f"{name}.json")
        assert not _events(trace)
        assert "vision_models" not in trace["metadata"]


# --- replay recomputes the verdict from the recorded labels (no model) --------------------------


@pytest.fixture
def forbid_models(monkeypatch):
    """
    `forbid_models()`, called once a session is recorded: any model call after it fails the
    test, because replay never calls a model.
    """

    def refuse(self, frame):
        raise AssertionError("replay called a vision model")

    return lambda: monkeypatch.setattr(ScriptedVisionModel, "detect", refuse)


async def _replay(trace, agent):
    return await TracePlayer(trace, target="sim", agent=agent).replay()


async def test_replay_reproduces_an_allow_from_the_perception_events(copy_agent, forbid_models):
    _, trace, live = await _record(GOOD)
    assert live.verdict.value == "ALLOW"
    forbid_models()
    result = await _replay(trace, _agent(copy_agent))
    assert result.verdicts == ["ALLOW"] == result.recorded_verdicts
    assert not result.warnings
    assert not result.action("unlock_door").blocked


async def test_replay_reproduces_a_block_and_its_reason(copy_agent, forbid_models):
    weak = {1: [person(0.93)], 2: [person(0.80)], 3: [person(0.95)]}
    _, trace, live = await _record(weak)
    assert live.reason.value == "condition_not_met"
    forbid_models()
    result = await _replay(trace, _agent(copy_agent))
    assert result.verdicts == ["BLOCK"] and result.reason == "condition_not_met"
    assert result.action("unlock_door").blocked


async def test_replay_reproduces_a_fail_closed_block(copy_agent, forbid_models):
    def freeze(rig):
        for seq in (1, 2, 3):
            rig.clock.advance(33)
            rig.feed(seq, tag="same")

    rig = Rig(GOOD, _gates())
    rig.events.emit("action_requested", {"action": "unlock_door", "arguments": {}})
    freeze(rig)
    live = await rig.decide("unlock_door")
    assert live.reason.value == "criterion_unavailable"
    forbid_models()
    result = await _replay(rig.events.to_trace(), _agent(copy_agent))
    assert result.verdicts == ["BLOCK"] and result.reason == "criterion_unavailable"


async def test_a_replay_can_itself_be_replayed(copy_agent, forbid_models):
    _, trace, _ = await _record(GOOD)
    agent = _agent(copy_agent)
    forbid_models()
    first = await _replay(trace, agent)
    validate_trace(first.replayed)  # the event is written again, on the replay's own timeline
    assert _events(first.replayed)
    second = await _replay(first.replayed, agent)
    assert second.verdicts == ["ALLOW"] and not second.warnings


def _rewrite(trace, edit):
    trace = copy.deepcopy(trace)
    for event in _events(trace):
        edit(event["data"])
    return trace


async def test_the_verdict_comes_from_the_recorded_labels_not_the_recorded_gate_fact(
    copy_agent, forbid_models
):
    """The labels say the person is weakly seen; the recorded `gate_facts` still says 0.93."""
    _, trace, _ = await _record(GOOD)

    def weaken(data):
        if data["kind"] != "confidence":
            return
        for item in data["frames"]:
            item["labels"][0]["score"] = 0.40
        data["values"] = [0.40, 0.40, 0.40]
        data["value"] = 0.40

    tampered = _rewrite(trace, weaken)
    [step] = recorded_steps(tampered)
    assert step.facts["person_confidence"].value == pytest.approx(0.95)  # the recorded scalar
    assert not vision_problems(tampered)  # consistent: nothing for replay to complain about
    forbid_models()
    result = await _replay(tampered, _agent(copy_agent))
    assert result.verdicts == ["BLOCK"] and result.reason == "condition_not_met"


async def test_an_event_its_own_labels_do_not_support_replays_as_unavailable(
    copy_agent, forbid_models
):
    _, trace, _ = await _record(GOOD)

    def lie(data):
        if data["kind"] == "confidence":
            data["frames"][1]["labels"][0]["score"] = 0.40  # but `values` still say 0.91

    tampered = _rewrite(trace, lie)
    problems = vision_problems(tampered)
    assert problems and "the labels give" in problems[0].why
    forbid_models()
    result = await _replay(tampered, _agent(copy_agent))
    assert result.verdicts == ["BLOCK"] and result.reason == "criterion_unavailable"
    assert any("altered or is incomplete" in w for w in result.warnings)
    assert any(e["type"] == "vision_fact_problem" for e in result.replayed["events"])


async def test_replay_refuses_a_trace_whose_window_is_not_what_it_claims(copy_agent):
    _, trace, _ = await _record(GOOD)
    tampered = _rewrite(trace, lambda data: data["frames"].pop())
    with pytest.raises(TraceValidationError):
        await _replay(tampered, _agent(copy_agent))


async def test_replay_does_not_take_a_window_with_pinned_constants_changed(copy_agent):
    """An event recorded with another floor or ceiling is not this code's reading of the labels."""
    _, trace, _ = await _record(GOOD)
    tampered = _rewrite(trace, lambda data: data.update(present_score_floor=0.1))
    result = await _replay(tampered, _agent(copy_agent))
    assert result.verdicts == ["BLOCK"] and result.reason == "criterion_unavailable"
    assert any("present_score_floor" in w for w in result.warnings)


async def test_replay_of_a_trace_without_vision_events_is_unchanged(traces_dir):
    result = await TracePlayer(traces_dir / "happy-path.json", target="sim").replay()
    assert result.verdicts == ["ALLOW"]
    assert not result.warnings


def _boom(frame):
    raise RuntimeError("boom")


@pytest.mark.parametrize(
    ("model", "rejected"),
    [
        ({"fail": True}, "model_unavailable"),
        ({"script": _boom}, "model_error"),
        ({"latency_ms": 5000}, "timeout"),
        ({"script": lambda frame: "not a list"}, "garbage"),
    ],
    ids=lambda case: case if isinstance(case, str) else "",
)
async def test_a_model_failure_is_a_valid_trace_and_replays_as_the_same_block(
    copy_agent, forbid_models, model, rejected
):
    rig = Rig({}, _gates())
    rig.pipeline.set_model(
        ScriptedVisionModel(
            model.pop("script", {i: [person(0.99)] for i in (1, 2, 3)}),
            labels=[PERSON],
            name="person-det",
            **model,
        )
    )
    rig.events.emit("action_requested", {"action": "unlock_door", "arguments": {}})
    rig.play(1, 2, 3)
    live = await rig.decide("unlock_door")
    assert live.verdict.value == "BLOCK" and live.reason.value == "criterion_unavailable"
    trace = rig.events.to_trace()
    validate_trace(trace)
    last = _events(trace)[-1]["data"]
    assert last["value"] is None and last["unavailable"] == rejected
    assert {f["rejected"] for f in last["frames"]} == {rejected}
    forbid_models()
    result = await _replay(trace, _agent(copy_agent))
    assert result.verdicts == ["BLOCK"] and result.reason == "criterion_unavailable"
    assert result.action("unlock_door").blocked
    assert not result.warnings
