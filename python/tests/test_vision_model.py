"""
TSK-V1b-03 — the vision model interface: swapped by configuration alone, and never trusted
(FR-MDL-04, FR-MDL-07, RFC-0012 §3c, §3e).
"""

from __future__ import annotations

import hashlib
import textwrap

import pytest

from neuroedge.engine import ActionContractEngine, EventLog, GateVerdict, Reason
from neuroedge.errors import AgentManifestError
from neuroedge.perception.vision import (
    Detection,
    Frame,
    ModelIdentity,
    ScriptedVisionModel,
    VisionPipeline,
    identity_of_file,
    make_vision_model,
    parse_vision,
    sanitize,
)
from neuroedge.perception.vision.model import MAX_DETECTIONS

from .vision_support import INSIDE, PERSON, VISION_TABLE, FakeClock, Rig, config, open_gate, person

# --- swapping the model is changing configuration, nothing else --------------------------------

SCRIPT = {str(i): [{"label": PERSON, "score": 0.93, "box": list(INSIDE)}] for i in (1, 2, 3)}


async def _decide_with(table: dict, root=None):
    """The whole path from a `[vision]` table to a verdict. Only `table` differs between runs."""
    cfg = parse_vision(table)
    clock = FakeClock()
    events = EventLog(clock)
    pipeline = VisionPipeline(cfg, make_vision_model(cfg, root), events=events)
    engine = ActionContractEngine({"open": open_gate()}, events=events, clock=clock)
    for seq in (1, 2, 3):
        clock.advance(33)
        pipeline.push(Frame(seq, clock.now, f"pixels-{seq}".encode()))
    facts = pipeline.facts_for(engine.tree("open"))
    return await engine.evaluate("open", facts), pipeline.identity


async def test_switching_the_model_is_a_configuration_change_only(tmp_path):
    (tmp_path / "other_model.py").write_text(
        textwrap.dedent(
            """
            from neuroedge.perception.vision import Detection, Inference, ModelIdentity

            class Timid:
                identity = ModelIdentity("timid-det", "b" * 64)
                labels = frozenset({"person"})

                def detect(self, frame):
                    return Inference([Detection("person", 0.40, (0.4, 0.5, 0.6, 0.9))], 5.0)

            def make(config):
                return Timid()
            """
        )
    )
    confident = {**VISION_TABLE, "options": {"name": "person-det", "script": SCRIPT}}
    timid = {**VISION_TABLE, "provider": "python:other_model:make"}

    first, first_id = await _decide_with(confident, tmp_path)
    second, second_id = await _decide_with(timid, tmp_path)

    assert first.verdict is GateVerdict.ALLOW and first_id.name == "person-det"
    assert second.verdict is GateVerdict.BLOCK
    assert second.reason is Reason.CONDITION_NOT_MET  # the *gate's* threshold, not the model's
    assert second_id == ModelIdentity("timid-det", "b" * 64)


def test_a_vision_table_without_a_provider_is_valid_but_makes_no_model():
    cfg = parse_vision({k: v for k, v in VISION_TABLE.items() if k != "provider"})
    with pytest.raises(AgentManifestError) as excinfo:
        make_vision_model(cfg)
    assert "provider" in excinfo.value.where


def test_an_unknown_builtin_and_a_broken_adapter_are_three_part_errors(tmp_path):
    with pytest.raises(AgentManifestError) as excinfo:
        make_vision_model(parse_vision({**VISION_TABLE, "provider": "onnx"}))
    assert "built in" in excinfo.value.why and excinfo.value.how
    (tmp_path / "bad_model.py").write_text("def make(config):\n    return object()\n")
    with pytest.raises(AgentManifestError) as excinfo:
        make_vision_model(
            parse_vision({**VISION_TABLE, "provider": "python:bad_model:make"}), tmp_path
        )
    assert "not a vision model" in excinfo.value.why


def test_the_replay_model_identity_follows_its_script():
    a = make_vision_model(parse_vision({**VISION_TABLE, "options": {"script": SCRIPT}}))
    b = make_vision_model(parse_vision({**VISION_TABLE, "options": {"script": SCRIPT}}))
    c = make_vision_model(
        parse_vision({**VISION_TABLE, "options": {"script": {"1": []}, "labels": [PERSON]}})
    )
    assert a.identity == b.identity != c.identity
    assert len(a.identity.sha256) == 64


def test_a_model_file_is_identified_by_its_name_and_hash(tmp_path):
    path = tmp_path / "person-det.tflite"
    path.write_bytes(b"weights")
    identity = identity_of_file(path)
    assert identity.name == "person-det"
    assert identity.sha256 == hashlib.sha256(b"weights").hexdigest()


# --- a model is untrusted: every way it can fail is a fact that is not there -------------------


async def _verdict_with(model: ScriptedVisionModel, **rig_kw):
    rig = Rig({}, **rig_kw)
    rig.pipeline.set_model(model)
    rig.play(1, 2, 3)
    return rig, await rig.decide("open")


async def _blocked_unavailable(rig, result, reason: str):
    assert result.verdict is GateVerdict.BLOCK
    assert result.reason is Reason.CRITERION_UNAVAILABLE
    assert rig.events.of_type("vision_fact")[-1]["unavailable"] == reason
    assert not any(e["type"] == "actuator_command" for e in rig.events.events)


async def test_a_model_that_cannot_be_reached_blocks():
    model = ScriptedVisionModel({}, labels=[PERSON], name="m", fail=True)
    rig, result = await _verdict_with(model)
    await _blocked_unavailable(rig, result, "model_unavailable")


async def test_a_model_that_crashes_blocks():
    def boom(frame):
        raise RuntimeError("CUDA out of memory")

    rig, result = await _verdict_with(ScriptedVisionModel(boom, labels=[PERSON], name="m"))
    await _blocked_unavailable(rig, result, "model_error")


async def test_a_model_that_answers_after_the_timeout_blocks():
    slow = ScriptedVisionModel(
        {i: [person(0.99)] for i in (1, 2, 3)}, labels=[PERSON], name="m", latency_ms=5000
    )
    rig, result = await _verdict_with(slow)  # timeout_ms defaults to 200
    await _blocked_unavailable(rig, result, "timeout")


async def test_a_script_with_nothing_for_the_frame_is_not_an_empty_scene():
    model = ScriptedVisionModel({1: [person(0.99)], 2: [person(0.99)]}, labels=[PERSON], name="m")
    rig, result = await _verdict_with(model)  # frame 3 is not in the script
    await _blocked_unavailable(rig, result, "model_unavailable")


@pytest.mark.parametrize(
    "garbage",
    [
        [Detection("unicorn", 0.99, INSIDE)],  # a label the model cannot say
        "person",  # not a list
        None,
        [{"label": PERSON, "score": 0.99}],  # a dict is not a Detection
        [Detection(PERSON, "0.99", INSIDE)],  # a score that is not a number
        [Detection(PERSON, True, INSIDE)],
        [Detection(PERSON, 0.99, (0.5, 0.5, 0.4, 0.9))],  # not a rectangle
        [Detection(PERSON, 0.99, (0.0, 0.0, 2.0, 1.0))],  # outside the frame
        [Detection(PERSON, 0.99, None)],  # no box: it cannot be placed in a zone
        [person(0.99)] * (MAX_DETECTIONS + 1),
    ],
    ids=repr,
)
async def test_garbage_from_the_model_blocks_and_is_never_read_as_nobody_there(garbage):
    model = ScriptedVisionModel(lambda frame: garbage, labels=[PERSON], name="m")
    rig, result = await _verdict_with(model)
    await _blocked_unavailable(rig, result, "garbage")
    # the close gate is just as shut: garbage is not "nobody in the gate area"
    close = await rig.decide("close") if "close" in rig.engine._gates else None
    assert close is None or close.verdict is GateVerdict.BLOCK


async def test_garbage_in_one_frame_poisons_the_window_until_it_ages_out():
    script = {i: [person(0.99)] for i in range(1, 8)}
    rig = Rig({})
    bad = {2: "garbage"}
    rig.pipeline.set_model(
        ScriptedVisionModel(lambda f: bad.get(f.seq, script[f.seq]), labels=[PERSON], name="m")
    )
    rig.play(1, 2, 3)
    assert (await rig.decide("open")).reason is Reason.CRITERION_UNAVAILABLE
    rig.play(4)
    assert (await rig.decide("open")).reason is Reason.CRITERION_UNAVAILABLE  # 2, 3, 4
    rig.play(5)
    assert (await rig.decide("open")).verdict is GateVerdict.ALLOW  # 3, 4, 5: clean again


def test_a_pushed_frame_never_raises_for_what_the_model_does():
    rig = Rig({})

    def boom(frame):
        raise ValueError("x")

    rig.pipeline.set_model(ScriptedVisionModel(boom, labels=[PERSON], name="m"))
    observation = rig.feed(1)
    assert observation.rejected == "model_error"


def test_an_async_detect_is_rejected_not_awaited():
    class Async:
        identity = ModelIdentity("a", "a" * 64)
        labels = frozenset({PERSON})

        async def detect(self, frame):
            return []

    rig = Rig({})
    rig.pipeline.set_model(Async())
    assert rig.feed(1).rejected == "model_error"


def test_sanitize_keeps_a_score_that_is_a_number_even_when_it_is_not_a_probability():
    kept, rejected = sanitize({PERSON}, [Detection(PERSON, float("nan"), INSIDE)])
    assert rejected is None and len(kept) == 1  # the gate refuses it as value_out_of_range


# --- the [vision] table ------------------------------------------------------------------------

BAD_TABLES = {
    "kind": ({"person_at_gate": {"label": "p", "zone": "gate_area", "kind": "bands"}}, "kind"),
    "bands": (
        {"x": {"label": "p", "zone": "gate_area", "kind": "count", "bands": {"low": 1}}},
        "bands",
    ),
    "threshold": (
        {"x": {"label": "p", "zone": "gate_area", "kind": "confidence", "gte": 0.9}},
        "gte",
    ),
    "min_frames one": (
        {"x": {"label": "p", "zone": "gate_area", "kind": "present", "min_frames": 1}},
        "min_frames",
    ),
    "min_frames bool": (
        {"x": {"label": "p", "zone": "gate_area", "kind": "present", "min_frames": True}},
        "min_frames",
    ),
    "zone not declared": ({"x": {"label": "p", "zone": "elsewhere", "kind": "present"}}, "zone"),
}


@pytest.mark.parametrize("name", BAD_TABLES)
def test_a_bad_fact_is_a_three_part_manifest_error(name):
    facts, field = BAD_TABLES[name]
    with pytest.raises(AgentManifestError) as excinfo:
        parse_vision({**VISION_TABLE, "facts": facts})
    error = excinfo.value
    assert error.code == "NE3002" and field in error.where + error.why and error.how


@pytest.mark.parametrize(
    "zone",
    [
        [0.1, 0.2, 0.3],  # three numbers
        [0.0, 0.0, 1.2, 1.0],  # outside [0, 1]
        [0.5, 0.0, 0.5, 1.0],  # x0 == x1
        [0.0, 0.9, 1.0, 0.1],  # y0 > y1
        [[0.0, 0.0], [1.0, 0.0], [0.5, 1.0]],  # a polygon
        [0.0, 0.0, "1", 1.0],
        [0.0, 0.0, float("nan"), 1.0],
        "0.1,0.2,0.3,0.4",
    ],
    ids=repr,
)
def test_a_zone_is_one_normalised_rectangle(zone):
    with pytest.raises(AgentManifestError) as excinfo:
        parse_vision({**VISION_TABLE, "zones": {"gate_area": zone}})
    assert "gate_area" in excinfo.value.where


def test_a_key_in_the_table_is_refused_and_not_echoed():
    with pytest.raises(AgentManifestError) as excinfo:
        parse_vision({**VISION_TABLE, "api_key": "sk-live-1234567890abcdef"})
    assert "sk-live" not in str(excinfo.value)


def test_the_valid_table_has_no_threshold_in_it():
    cfg = config()
    assert cfg.facts["person_at_gate"].min_frames == 3  # RFC-0012 §3c default
    assert cfg.facts["person_at_gate"].criterion_type == "bool"
    assert cfg.facts["people_at_gate"].criterion_type == "numeric"
    assert not any("thresh" in str(spec).lower() for spec in cfg.facts.values())


@pytest.mark.parametrize(
    "bad",
    [
        {"seq": "1", "captured_ms": 1.0, "pixels": b""},
        {"seq": True, "captured_ms": 1.0, "pixels": b""},
        {"seq": 1, "captured_ms": float("nan"), "pixels": b""},
        {"seq": 1, "captured_ms": 1.0, "pixels": "not bytes"},
    ],
    ids=repr,
)
def test_a_malformed_frame_is_the_cameras_bug_and_is_refused_loudly(bad):
    with pytest.raises(ValueError):
        Frame(**bad)
