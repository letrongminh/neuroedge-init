"""
TSK-V1b-03 — vision facts: frames in, typed facts out, and the gate decides (RFC-0012 §3c–§3e).

The model is a scripted one; nothing here needs a camera, an ML library or the network. Every
BLOCK below is a *verdict* with a reason, never an exception and never an ALLOW.
"""

from __future__ import annotations

import math

import pytest

from neuroedge.engine import GateVerdict, Reason
from neuroedge.perception.vision import (
    MAX_FRAME_AGE_MS,
    PRESENT_SCORE_FLOOR,
    Detection,
    frame_value,
)

from .vision_support import INSIDE, OUTSIDE, PERSON, Rig, gate, person


def scripted(*scores: float | None, first: int = 1) -> dict[int, list[Detection]]:
    """Frame `first`, `first + 1`, … each seeing one person with the given score (None: nobody)."""
    return {first + i: [] if score is None else [person(score)] for i, score in enumerate(scores)}


# --- the value of a fact on one frame (§3e, §9.13) ---------------------------------------------


@pytest.mark.parametrize(
    ("kind", "scores", "expected"),
    [
        ("confidence", [], 0.0),  # absence is a score of zero, not "undecided"
        ("confidence", [0.2, 0.93, 0.4], 0.93),
        ("count", [], 0),
        ("count", [0.9, 0.5, 0.49], 2),  # the floor counts, a hair under it does not
        ("present", [0.49], False),
        ("present", [PRESENT_SCORE_FLOOR], True),
    ],
)
def test_frame_value(kind, scores, expected):
    assert frame_value(kind, scores) == expected


@pytest.mark.parametrize("bad", [math.nan, math.inf, -0.1, 1.5])
def test_a_score_outside_zero_one_is_a_value_the_gate_refuses_never_a_pass(bad):
    assert math.isnan(frame_value("confidence", [0.9, bad]))
    assert math.isnan(frame_value("count", [0.9, bad]))
    assert frame_value("present", [0.9, bad]) is None  # a bool has no out-of-range: unavailable


# --- what the gate decides over a window of frames (§7: judged frame by frame, ANDed) ----------


async def test_three_good_frames_allow_the_open_gate():
    rig = Rig({**scripted(0.9, 0.9, 0.9)})
    rig.play(1, 2, 3)
    result = await rig.decide("open")
    assert result.verdict is GateVerdict.ALLOW


@pytest.mark.parametrize(
    ("scores", "verdict"),
    [
        ([0.90, 0.80, 0.90], GateVerdict.BLOCK),  # one weak frame blocks `gte`
        ([0.86, 0.90, 0.88], GateVerdict.ALLOW),
    ],
)
async def test_confidence_gte_is_judged_on_every_frame(scores, verdict):
    rig = Rig(scripted(*scores))
    rig.play(1, 2, 3)
    result = await rig.decide("open")
    assert result.verdict is verdict
    if verdict is GateVerdict.BLOCK:
        assert result.reason is Reason.CONDITION_NOT_MET
        assert result.failed_criterion == "person_confidence"


@pytest.mark.parametrize(
    ("people", "verdict"),
    [
        ([0, 1, 0], GateVerdict.BLOCK),  # one frame with someone blocks `count lte 0`
        ([0, 0, 0], GateVerdict.ALLOW),
    ],
)
async def test_count_lte_zero_is_judged_on_every_frame(people, verdict):
    # The close gate also needs `person_confidence lte 0.10` and `person_at_gate: false`: nobody
    # in the zone means a confidence of 0.0, and a frame with a person fails all three.
    script = {i + 1: [person(0.95)] * n for i, n in enumerate(people)}
    rig = Rig(script)
    rig.play(1, 2, 3)
    result = await rig.decide("close")
    assert result.verdict is verdict


async def test_a_detection_outside_the_zone_is_not_in_the_zone():
    rig = Rig({i: [person(0.99, OUTSIDE)] for i in (1, 2, 3)})
    rig.play(1, 2, 3)
    assert (await rig.decide("open")).reason is Reason.CONDITION_NOT_MET
    assert (await rig.decide("close")).verdict is GateVerdict.ALLOW  # nobody *in the gate area*


async def test_the_facts_carry_the_age_of_the_oldest_frame():
    rig = Rig(scripted(0.9, 0.9, 0.9))
    rig.play(1, 2, 3)
    facts = rig.pipeline.facts_for(rig.engine.tree("open"))
    assert facts["person_confidence"].read_ms == 1033.0  # the oldest frame's read mark
    assert facts["person_confidence"].source == "vision"


# --- fail closed (§3e): every way a fact is not there blocks `criterion_unavailable` -----------


def _unavailable(result):
    assert result.verdict is GateVerdict.BLOCK
    assert result.reason is Reason.CRITERION_UNAVAILABLE


async def test_a_window_not_yet_full_blocks():
    rig = Rig(scripted(0.9, 0.9))
    rig.play(1, 2)
    _unavailable(await rig.decide("open"))
    assert rig.events.of_type("vision_fact")[-1]["unavailable"] == "window_size"


async def test_a_lost_frame_restarts_the_window():
    rig = Rig(scripted(*[0.9] * 7))
    rig.play(1, 2, 3)
    assert (await rig.decide("open")).verdict is GateVerdict.ALLOW
    rig.play(5)  # frame 4 never arrived
    _unavailable(await rig.decide("open"))
    rig.play(6)
    _unavailable(await rig.decide("open"))  # only two consecutive frames since the gap
    rig.play(7)
    assert (await rig.decide("open")).verdict is GateVerdict.ALLOW


async def test_a_camera_that_repeats_a_frame_is_frozen_whatever_time_it_stamps():
    rig = Rig(scripted(0.9, 0.9, 0.9))
    rig.clock.advance(33)
    rig.feed(1, tag="same")
    rig.clock.advance(33)
    rig.feed(2, tag="same")  # byte-identical, a fresh timestamp and a fresh frame number
    rig.clock.advance(33)
    rig.feed(3)
    _unavailable(await rig.decide("open"))
    assert rig.events.of_type("vision_fact")[-1]["unavailable"] == "frozen"


async def test_a_window_older_than_the_ceiling_blocks_even_when_the_gate_allows_longer():
    # The gate says 5000 ms is fine; the perception layer's own ceiling is 1000 and is not configurable.
    gates = {
        "open": gate(
            "open_gate", {"person_at_gate": True, "person_confidence": {"gte": 0.85}}, 5000
        )
    }
    rig = Rig(scripted(0.9, 0.9, 0.9), gates)
    rig.play(1, 2, 3)
    rig.clock.advance(MAX_FRAME_AGE_MS)  # the oldest frame is now 1033 ms old
    _unavailable(await rig.decide("open"))
    assert rig.events.of_type("vision_fact")[-1]["unavailable"] == "stale"


async def test_a_window_older_than_the_gates_max_age_blocks_even_inside_the_ceiling():
    rig = Rig(scripted(0.9, 0.9, 0.9))  # the gates allow 300 ms
    rig.play(1, 2, 3)
    rig.clock.advance(400)  # the oldest frame is 466 ms old: inside 1000, outside 300
    facts = rig.pipeline.facts_for(rig.engine.tree("open"))
    assert "person_confidence" in facts  # the perception layer read it ...
    result = await rig.engine.evaluate("open", facts)
    _unavailable(result)  # ... and the gate's own numeric age check refused it


async def test_a_frame_read_after_the_instant_it_is_judged_blocks():
    rig = Rig(scripted(0.9, 0.9, 0.9))
    rig.play(1, 2)
    rig.feed(3, ago=-50)  # stamped 50 ms in the future
    _unavailable(await rig.decide("open"))
    assert rig.events.of_type("vision_fact")[-1]["unavailable"] == "future"


async def test_present_never_stands_alone():
    """RFC-0012 §3c: `present: false` without the numeric `confidence` would pass on a frozen camera."""
    lonely = {"close": gate("close_gate", {"person_at_gate": False})}
    rig = Rig({i: [] for i in (1, 2, 3)}, lonely)
    rig.play(1, 2, 3)
    _unavailable(await rig.decide("close"))
    assert rig.events.of_type("vision_fact")[-1]["unavailable"] == "unpaired"


async def test_count_without_confidence_is_refused_the_same_way():
    lonely = {"close": gate("close_gate", {"people_at_gate": {"lte": 0}})}
    rig = Rig({i: [] for i in (1, 2, 3)}, lonely)
    rig.play(1, 2, 3)
    _unavailable(await rig.decide("close"))


async def test_a_frozen_camera_cannot_close_the_gate():
    """The attack of RFC-0012 §3c: a camera repeating "nobody there" while someone stands in the way."""
    rig = Rig({i: [] for i in (1, 2, 3)})
    for seq in (1, 2, 3):
        rig.clock.advance(33)
        rig.feed(seq, tag="empty-scene")
    assert (await rig.decide("close")).reason is Reason.CRITERION_UNAVAILABLE
    rig.clock.advance(2000)  # and a camera that simply stopped
    assert (await rig.decide("close")).reason is Reason.CRITERION_UNAVAILABLE


@pytest.mark.parametrize("bad", [math.nan, math.inf, 1.5, -0.2])
async def test_a_score_that_is_not_a_probability_is_value_out_of_range(bad):
    rig = Rig({1: [person(0.9)], 2: [person(bad)], 3: [person(0.9)]})
    rig.play(1, 2, 3)
    result = await rig.decide("open")
    assert result.verdict is GateVerdict.BLOCK
    # `present` over that frame is unavailable (a bool has no range): the first criterion says so
    assert result.reason is Reason.CRITERION_UNAVAILABLE
    assert result.failed_criterion == "person_at_gate"
    only_confidence = {"open": gate("open_gate", {"person_confidence": {"gte": 0.85}})}
    rig = Rig({1: [person(0.9)], 2: [person(bad)], 3: [person(0.9)]}, only_confidence)
    rig.play(1, 2, 3)
    assert (await rig.decide("open")).reason is Reason.VALUE_OUT_OF_RANGE


async def test_a_count_above_the_gates_range_is_value_out_of_range():
    gates = {
        "close": gate(
            "close_gate", {"people_at_gate": {"lte": 0}, "person_confidence": {"lte": 0.1}}
        )
    }
    rig = Rig({i: [person(0.9)] * 60 for i in (1, 2, 3)}, gates)  # the gate says 0..50
    rig.play(1, 2, 3)
    result = await rig.decide("close")
    assert result.reason is Reason.VALUE_OUT_OF_RANGE
    assert result.failed_criterion == "people_at_gate"


# --- the evidence the live path writes ---------------------------------------------------------


async def test_one_vision_fact_event_per_fact_the_gate_reads_and_no_pixels():
    rig = Rig(scripted(0.9, 0.9, 0.9))
    rig.play(1, 2, 3)
    await rig.decide("open")
    events = [e for e in rig.events.events if e["type"] == "vision_fact"]
    assert [e["data"]["fact"] for e in events] == ["person_at_gate", "person_confidence"]
    for event in events:
        assert "pixels" not in str(event)
        data = event["data"]
        assert data["model"]["name"] == "person-det"
        assert [f["frame_seq"] for f in data["frames"]] == [1, 2, 3]
        assert data["age_ms"] == event["offset_ms"] - data["frames"][0]["captured_ms"]
        assert data["max_frame_age_ms"] == MAX_FRAME_AGE_MS
        assert data["present_score_floor"] == PRESENT_SCORE_FLOOR
    # Only the frames of the window: a fourth frame pushes the first out of the evidence.
    rig.model.script[4] = [person(0.9)]
    rig.play(4)
    await rig.decide("open")
    last = [e for e in rig.events.events if e["type"] == "vision_fact"][-1]["data"]
    assert [f["frame_seq"] for f in last["frames"]] == [2, 3, 4]


async def test_the_session_lists_every_model_it_used_and_a_swap_restarts_the_window():
    from neuroedge.perception.vision import ScriptedVisionModel

    rig = Rig(scripted(0.9, 0.9, 0.9, 0.9, 0.9, 0.9))
    rig.play(1, 2, 3)
    assert (await rig.decide("open")).verdict is GateVerdict.ALLOW
    other = ScriptedVisionModel(scripted(0.9, first=4), labels=[PERSON], name="person-det-v2")
    rig.pipeline.set_model(other)
    rig.play(4)
    _unavailable(await rig.decide("open"))  # one frame of the new model: no mixed window
    listed = {m["name"] for m in rig.events.metadata["vision_models"]}
    assert listed == {"person-det", "person-det-v2"}


async def test_a_fact_that_reads_a_label_the_model_cannot_say_is_refused_at_wiring():
    from neuroedge.errors import AgentManifestError
    from neuroedge.perception.vision import ScriptedVisionModel, VisionPipeline

    rig = Rig({})
    other = ScriptedVisionModel({}, labels=["dog"], name="dog-det")
    with pytest.raises(AgentManifestError) as excinfo:
        VisionPipeline(rig.config, other, events=rig.events)
    assert "cannot say" in excinfo.value.why


def test_the_zone_edge_counts_and_centre_decides():
    from neuroedge.perception.vision import Zone

    zone = Zone("z", (0.25, 0.4, 0.75, 1.0))
    assert zone.contains(INSIDE)
    assert zone.contains((0.0, 0.0, 0.5, 0.8))  # centre (0.25, 0.4): on the corner
    assert not zone.contains(OUTSIDE)
