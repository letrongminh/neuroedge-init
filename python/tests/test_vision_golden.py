"""
TSK-V1b-04 — the inference golden and the tolerance check (RFC-0012 §3f clause 2, §9.6, §9.9).

"The model sees the same on every target" is its own claim, proved apart from "the gate decides
the same": per model SHA-256 and frame content hash, a target's detections must match the host's
within the board's `vision_in.tolerance`. No model runs on a real target here; the machinery is
exercised with the scripted model, perturbed.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from neuroedge.errors import SafetyRegressionError, VerificationError
from neuroedge.hal.board import load_board_by_id
from neuroedge.perception.vision import (
    Detection,
    ScriptedVisionModel,
    VisionUnavailable,
)
from neuroedge.testing.vision import (
    check_scene_inference,
    load_scene,
    record_scene_golden,
    scene_model,
)
from neuroedge.testing.vision_golden import (
    InferenceGolden,
    Tolerance,
    assert_inference_matches,
    check_model,
    compare_inference,
    infer,
    iou,
    match_detections,
    record_golden,
    tolerance_of,
)

ROOT = Path(__file__).resolve().parents[2]
SCENES = ROOT / "fixtures" / "vision"
GOLDEN_DIR = SCENES / "golden"
TOL = Tolerance(score_abs=0.03, box_iou_min=0.85)  # sim-rpi5 / linux-rpi5
BOX = (0.4, 0.5, 0.6, 0.9)  # width 0.2: a shift d gives IoU (0.2 - d) / (0.2 + d)
SCENE = SCENES / "stranger-at-door"


@pytest.fixture(scope="module")
def golden() -> InferenceGolden:
    return InferenceGolden.load(GOLDEN_DIR / "stranger-at-door.json")


@pytest.fixture(scope="module")
def scene():
    return load_scene(SCENE)


def _observed(golden, edit=lambda dets: dets):
    return {digest: edit(list(dets)) for digest, dets in golden.frames.items()}


def _with_person(golden):
    """The digest of a frame that has a detection, and its detections."""
    return next((h, d) for h, d in sorted(golden.frames.items()) if d)


def _compare(golden, observed, tol=TOL):
    return compare_inference(golden, golden.model, observed, tol)


# --- the committed goldens ---------------------------------------------------------------------


def test_the_goldens_are_pinned_to_what_the_host_model_says_now():
    for path in sorted(GOLDEN_DIR.glob("*.json")):
        fresh = record_scene_golden(SCENES / path.stem).to_document()
        assert fresh == json.loads(path.read_text()), (
            f"{path.name} drifted from its scene: re-record with "
            "record_scene_golden(scene, path) — a changed golden is a reviewed change"
        )


def test_every_golden_has_a_scene_and_every_scene_that_can_has_a_golden():
    goldens = {p.stem for p in GOLDEN_DIR.glob("*.json")}
    scenes = {p.name for p in SCENES.iterdir() if (p / "scene.toml").is_file()}
    assert goldens <= scenes
    # the one scene without a golden is the one whose model does not answer a frame
    assert scenes - goldens == {"silent-model-at-door"}
    with pytest.raises(VisionUnavailable):
        record_scene_golden(SCENES / "silent-model-at-door")


def test_a_golden_is_keyed_by_content_hash_and_holds_no_pixels(golden):
    text = (GOLDEN_DIR / "stranger-at-door.json").read_text()
    assert "pixels" not in text and "P5" not in text
    assert golden.model.name == "stranger-at-door" and len(golden.model.sha256) == 64
    assert all(len(h) == 64 for h in golden.frames)


# --- the check ---------------------------------------------------------------------------------


def test_identical_inference_passes(golden, scene):
    check_model(golden, scene_model(scene), scene.frameset.frames, TOL)
    check_scene_inference(scene, golden, TOL)
    assert _compare(golden, _observed(golden)) == []


def test_an_inference_perturbed_within_tolerance_passes(golden):
    def nudge(dets):
        return [
            replace(
                d, score=d.score - TOL.score_abs * 0.99, box=(0.4 + 0.016, 0.5, 0.6 + 0.016, 0.9)
            )
            for d in dets
        ]

    assert _compare(golden, _observed(golden, nudge)) == []


def test_a_score_just_outside_score_abs_fails_naming_the_frame_and_detection(golden):
    digest, _ = _with_person(golden)
    observed = _observed(golden)
    observed[digest] = [replace(d, score=d.score - TOL.score_abs - 0.001) for d in observed[digest]]
    with pytest.raises(SafetyRegressionError) as excinfo:
        assert_inference_matches(golden, golden.model, observed, TOL, "linux/linux-rpi5")
    error = excinfo.value
    assert error.code == "NE4002"
    assert digest[:12] in error.why and "score_abs" in error.why and "detection 0" in error.why
    assert "linux/linux-rpi5" in error.where and error.how


def test_the_score_edge_is_inclusive(golden):
    digest, _ = _with_person(golden)
    observed = _observed(golden)
    observed[digest] = [replace(d, score=d.score - TOL.score_abs) for d in observed[digest]]
    assert _compare(golden, observed) == []


def test_a_box_whose_iou_is_just_below_the_minimum_fails():
    golden = InferenceGolden(
        scene_model_identity(),
        {"a" * 64: (Detection("person", 0.9, BOX),)},
    )
    inside = (0.4 + 0.0160, 0.5, 0.6 + 0.0160, 0.9)  # IoU ~0.852
    outside = (0.4 + 0.0163, 0.5, 0.6 + 0.0163, 0.9)  # IoU ~0.849
    assert iou(BOX, inside) >= TOL.box_iou_min > iou(BOX, outside)
    assert _compare(golden, {"a" * 64: [Detection("person", 0.9, inside)]}) == []
    found = _compare(golden, {"a" * 64: [Detection("person", 0.9, outside)]})
    assert [d.where for d in found] == ["detection 0 (person)", "extra detection 0"]
    assert "missing" in found[0].why and "best IoU 0.84" in found[0].why


def scene_model_identity():
    return ScriptedVisionModel({1: []}, labels=["person"], name="person-det").identity


def test_a_missing_detection_fails(golden):
    digest, _ = _with_person(golden)
    observed = _observed(golden)
    observed[digest] = observed[digest][1:]
    found = _compare(golden, observed)
    assert len(found) == 1 and "missing" in found[0].why and digest[:12] in str(found[0])


def test_an_extra_detection_fails_even_with_a_low_score(golden):
    digest, _ = _with_person(golden)
    observed = _observed(golden)
    observed[digest] = [*observed[digest], Detection("unknown_person", 0.02, (0.1, 0.1, 0.2, 0.2))]
    found = _compare(golden, observed)
    assert [d.where for d in found] == ["extra detection 1"]


def test_a_detection_of_another_label_is_a_missing_and_an_extra(golden):
    digest, _ = _with_person(golden)
    observed = _observed(golden)
    observed[digest] = [replace(d, label="person") for d in observed[digest]]
    assert {d.where.split(" ")[0] for d in _compare(golden, observed)} == {"detection", "extra"}


def test_a_frame_the_target_did_not_infer_or_the_golden_does_not_know_fails(golden):
    observed = _observed(golden)
    gone = sorted(observed)[0]
    del observed[gone]
    observed["f" * 64] = []
    whys = sorted(d.why for d in _compare(golden, observed))
    assert whys == ["the golden has no such frame", "the target did not infer it"]


def test_matching_is_one_to_one_and_does_not_depend_on_order():
    two = (Detection("person", 0.9, BOX), Detection("person", 0.8, (0.41, 0.5, 0.61, 0.9)))
    golden, observed = list(two), [Detection("person", 0.9, BOX)]
    pairs, missing, extra = match_detections(golden, observed, TOL)
    assert pairs == [(0, 0)] and missing == [1] and extra == []  # one target detection, one pair
    for shuffled in (list(two), list(reversed(two))):
        assert match_detections(shuffled, shuffled, TOL)[1:] == ([], [])
    swapped = match_detections(list(two), list(reversed(two)), TOL)
    assert swapped[0] == [(0, 1), (1, 0)] and swapped[1:] == ([], [])


def test_a_golden_for_another_model_is_refused_not_compared(golden):
    other = ScriptedVisionModel(
        {1: []}, labels=["unknown_person"], name="stranger-at-door"
    ).identity
    assert other.name == golden.model.name and other.sha256 != golden.model.sha256
    with pytest.raises(VerificationError) as excinfo:
        compare_inference(golden, other, _observed(golden), TOL)
    assert excinfo.value.code == "NE4004" and "another model" in excinfo.value.why
    # and not as a (possibly passing) equivalence: not a SafetyRegressionError either
    assert not isinstance(excinfo.value, SafetyRegressionError)


def test_a_perturbed_model_through_the_whole_path(golden, scene):
    """The model itself, run on the frames, nudged past the tolerance: refused with the frame."""
    base = scene_model(scene)

    def drifting(delta):
        def script(frame):
            return [replace(d, score=d.score - delta) for d in base.detect(frame).detections]

        return ScriptedVisionModel(
            script, labels=base.labels, name=base.identity.name, sha256=base.identity.sha256
        )

    check_model(golden, drifting(0.02), scene.frameset.frames, TOL)
    with pytest.raises(SafetyRegressionError):
        check_model(golden, drifting(0.04), scene.frameset.frames, TOL)
    # the same drift is within a board that declared more room, never beyond the hard ceiling
    check_model(golden, drifting(0.04), scene.frameset.frames, Tolerance(0.05, 0.8))


# --- tolerance ---------------------------------------------------------------------------------


@pytest.mark.parametrize("bad", [(0.06, 0.85), (0.03, 0.79), (-0.01, 0.9), (float("nan"), 0.9)])
def test_a_tolerance_beyond_the_hard_ceiling_cannot_be_built(bad):
    with pytest.raises(ValueError):
        Tolerance(*bad)


def test_the_tolerance_is_each_boards_own():
    assert tolerance_of(load_board_by_id("sim-rpi5")) == TOL
    assert tolerance_of(load_board_by_id("linux-rpi5")) == TOL
    assert tolerance_of(load_board_by_id("sim-default")) is None  # no camera, no check


# --- recording and loading ---------------------------------------------------------------------


def test_record_golden_refuses_a_hole_or_nonsense(scene):
    frames = scene.frameset.frames
    failing = ScriptedVisionModel({}, labels=["person"], name="m", fail=True)
    with pytest.raises(VisionUnavailable):
        record_golden(failing, frames)
    garbage = ScriptedVisionModel(lambda f: "nonsense", labels=["person"], name="m")
    with pytest.raises(VisionUnavailable):
        record_golden(garbage, frames)
    nan = ScriptedVisionModel(
        lambda f: [Detection("person", float("nan"), BOX)], labels=["person"], name="m"
    )
    with pytest.raises(VisionUnavailable):
        record_golden(nan, frames)
    with pytest.raises(VisionUnavailable):
        record_golden(scene_model(scene), [])


def test_the_same_bytes_must_get_the_same_answer(scene):
    frames = [scene.frameset.frames[0], scene.frameset.frames[0]]
    calls = iter([[Detection("person", 0.9, BOX)], []])
    flaky = ScriptedVisionModel(lambda f: next(calls), labels=["person"], name="m")
    with pytest.raises(VisionUnavailable) as excinfo:
        infer(flaky, frames)
    assert "not deterministic" in excinfo.value.why


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.update({"$format": "other"}),
        lambda d: d.pop("model"),
        lambda d: d["model"].update(sha256="xyz"),
        lambda d: d.update(frames={}),
        lambda d: d["frames"].update({"nothash": []}),
        lambda d: d["frames"].update(
            {"a" * 64: [{"label": "p", "score": 2.0, "box": [0, 0, 1, 1]}]}
        ),
        lambda d: d["frames"].update(
            {"a" * 64: [{"label": "p", "score": 0.5, "box": [0.5, 0, 0.4, 1]}]}
        ),
    ],
    ids=range(7),
)
def test_a_malformed_golden_is_a_three_part_error(golden, tmp_path, mutate):
    document = json.loads(json.dumps(golden.to_document()))
    mutate(document)
    path = tmp_path / "g.json"
    path.write_text(json.dumps(document))
    with pytest.raises(VerificationError) as excinfo:
        InferenceGolden.load(path)
    assert excinfo.value.how and str(path) in excinfo.value.where
    with pytest.raises(VerificationError):
        InferenceGolden.load(tmp_path / "absent.json")


def test_a_golden_round_trips(golden, tmp_path):
    golden.save(tmp_path / "x" / "g.json")
    assert InferenceGolden.load(tmp_path / "x" / "g.json") == golden


# --- wired into `neuroedge verify` -------------------------------------------------------------


@pytest.fixture
def vision_tree(tmp_path, monkeypatch):
    """A fixtures/ tree holding only a copy of fixtures/vision, for `verify` to read."""
    shutil.copytree(SCENES, tmp_path / "vision")
    from neuroedge.cli import main

    monkeypatch.setattr(main, "fixtures_dir", lambda: tmp_path)
    return tmp_path / "vision" / "golden"


COLUMNS = [
    ("sim/sim-default", "sim", "sim-default"),
    ("sim/sim-rpi5", "sim", "sim-rpi5"),
    ("linux/linux-rpi5", "linux", "linux-rpi5"),
    ("esp32s3", "esp32s3", None),
]


def test_verify_holds_every_board_with_a_camera_to_every_golden(vision_tree):
    from neuroedge.cli.main import _verify_inference

    problems, compared = _verify_inference(COLUMNS)
    assert problems == 0
    # the board without a camera and the device (a capture, TSK-I3a) are not compared
    assert compared == {"sim/sim-rpi5": 5, "linux/linux-rpi5": 5}


def test_verify_fails_on_a_golden_the_model_no_longer_meets(vision_tree):
    from neuroedge.cli.main import _verify_inference

    path = vision_tree / "stranger-at-door.json"
    document = json.loads(path.read_text())
    frame = next(h for h, d in document["frames"].items() if d)
    document["frames"][frame][0]["score"] -= 0.04  # beyond score_abs 0.03
    path.write_text(json.dumps(document))
    problems, compared = _verify_inference(COLUMNS[1:3])
    assert problems == 2 and compared == {"sim/sim-rpi5": 4, "linux/linux-rpi5": 4}


def test_verify_refuses_a_golden_whose_model_is_not_the_scenes(vision_tree):
    from neuroedge.cli.main import _verify_inference

    path = vision_tree / "package-on-porch.json"
    document = json.loads(path.read_text())
    document["model"]["sha256"] = "0" * 64
    path.write_text(json.dumps(document))
    problems, compared = _verify_inference(COLUMNS[1:2])
    assert problems == 1 and compared == {"sim/sim-rpi5": 4}


def test_verify_counts_zero_goldens_so_an_empty_corpus_cannot_pass(vision_tree):
    """A board with a camera and no golden compared is a zero the sweep reports (NE4004)."""
    from neuroedge.cli.main import _verify_inference

    for path in vision_tree.glob("*.json"):
        path.unlink()
    problems, compared = _verify_inference(COLUMNS)
    assert problems == 0 and compared == {"sim/sim-rpi5": 0, "linux/linux-rpi5": 0}
