"""
TSK-V1b-04 — Action CI for frames: record, replay and assert on the verdict sequence (FR-CI-01→04).

The scenes of `fixtures/vision/` are frames from files; nothing here needs a camera, a model or the
sim. The corpus is closed both ways: each scene directory has an entry in `expected_results.yaml`,
each entry a directory.
"""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import shutil
from pathlib import Path

import pytest
import yaml

from neuroedge.errors import AgentManifestError, TraceValidationError
from neuroedge.testing import TracePlayer, assert_matches_golden
from neuroedge.testing.vision import (
    assert_replay_matches,
    assert_verdicts,
    load_frames,
    load_scene,
    record_scene,
    replay_verdicts,
    run_scene,
)
from neuroedge.trace import load_trace, validate_trace

SCENES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "vision"
EXPECTED = yaml.safe_load((SCENES_DIR / "expected_results.yaml").read_text(encoding="utf-8"))
SCENES = sorted(p.name for p in SCENES_DIR.iterdir() if (p / "scene.toml").is_file())


def test_the_scene_corpus_is_closed_both_ways():
    assert set(SCENES) - set(EXPECTED) == set(), "scene without an expected verdict sequence"
    assert set(EXPECTED) - set(SCENES) == set(), "expectation with no scene"


@pytest.mark.parametrize("name", SCENES)
def test_a_scene_decides_as_recorded_in_the_corpus(name):
    run = run_scene(SCENES_DIR / name)
    assert_verdicts(run, EXPECTED[name]["verdicts"], reason=EXPECTED[name]["reasons"])
    assert len(run.verdicts) == len(run.frames)


@pytest.mark.parametrize("name", SCENES)
def test_the_trace_alone_replays_to_the_same_verdicts(name):
    run = run_scene(SCENES_DIR / name)
    assert_replay_matches(run)  # no model, no frame, no agent
    validate_trace(run.trace)


def test_the_attack_scenes_never_allow():
    for name in ("frozen-camera-at-door",):
        run = run_scene(SCENES_DIR / name)
        assert set(run.verdicts) == {"BLOCK"} and set(run.reasons) == {"criterion_unavailable"}


# --- record: no raw image unless asked ---------------------------------------------------------


def test_a_default_recording_holds_hashes_and_sizes_and_no_image(tmp_path):
    out = tmp_path / "t" / "stranger.json"
    record_scene(SCENES_DIR / "stranger-at-door", out)
    text = out.read_text(encoding="utf-8")
    trace = load_trace(out)
    assert "raw_capture" not in trace["metadata"] and '"uri"' not in text
    assert not (out.parent / "frames").exists()
    assert b"P5" not in out.read_bytes()  # no pixel of the .pgm files
    refs = [
        f["vision_ref"]
        for e in trace["events"]
        if e["type"] == "vision_fact"
        for f in e["data"]["frames"]
    ]
    assert refs and all(set(r) == {"sha256", "size"} for r in refs)
    assert trace["metadata"]["vision_models"][0]["name"] == "stranger-at-door"


def test_raw_capture_is_an_explicit_opt_in_and_says_so(tmp_path):
    out = tmp_path / "raw" / "stranger.json"
    run = record_scene(SCENES_DIR / "stranger-at-door", out, raw=True)
    trace = load_trace(out)  # the lint accepts the uri because raw_capture is true
    assert trace["metadata"]["raw_capture"] is True
    copies = sorted((out.parent / "frames").glob("*.bin"))
    assert {p.stem for p in copies} == {f.ref.sha256 for f in run.frames}
    for path in copies:
        assert hashlib.sha256(path.read_bytes()).hexdigest() == path.stem
    uris = {
        f["vision_ref"]["uri"]
        for e in trace["events"]
        if e["type"] == "vision_fact"
        for f in e["data"]["frames"]
    }
    assert uris <= {f"frames/{p.name}" for p in copies}


def test_a_uri_without_the_flag_is_refused_by_the_lint(tmp_path):
    out = tmp_path / "t.json"
    record_scene(SCENES_DIR / "stranger-at-door", out, raw=True)
    trace = json.loads(out.read_text())
    del trace["metadata"]["raw_capture"]
    with pytest.raises(TraceValidationError) as excinfo:
        validate_trace(trace)
    assert "raw_capture" in excinfo.value.why


# --- replay from the recording ---------------------------------------------------------------


def test_replay_recomputes_from_the_labels_and_notices_a_changed_verdict(tmp_path):
    out = tmp_path / "t.json"
    run = record_scene(SCENES_DIR / "stranger-at-door", out)
    trace = load_trace(out)
    gates = [run.gate]
    assert replay_verdicts(trace, gates)[3] == ("BLOCK", "condition_not_met")

    # Erase the stranger from every recorded frame, consistently: the verdict is recomputed from
    # the labels, so the replay now allows where the recording blocked.
    def erase(event):
        data = event["data"]
        for frame in data["frames"]:
            frame["labels"] = []
        data["values"] = [False if data["kind"] == "present" else 0.0] * len(data["frames"])
        if data.get("value") is not None:
            data["value"] = data["values"][-1]

    edited = copy.deepcopy(trace)
    for event in edited["events"]:
        if event["type"] == "vision_fact":
            erase(event)
    validate_trace(edited)
    again = replay_verdicts(edited, gates)
    assert [v for v, _ in again][3:8] == ["ALLOW"] * 5  # once the window is full and empty

    # An event its labels do not support is unavailable: it can only block more.
    liar = copy.deepcopy(trace)
    first = next(e for e in liar["events"] if e["type"] == "vision_fact" and e["data"]["value"])
    first["data"]["value"] = not first["data"]["value"]
    assert any(r == "criterion_unavailable" for _, r in replay_verdicts(liar, gates))


def test_an_agent_replay_of_the_same_recording_agrees_and_drives_the_pin(tmp_path, copy_agent):
    out = tmp_path / "t.json"
    run = record_scene(SCENES_DIR / "stranger-at-door", out)
    manifest = copy_agent("villa-concierge")
    manifest.write_text(
        manifest.read_text("utf-8").replace(
            "neuroedge://gates/unlock_door@1.2.0",
            "neuroedge://gates/vision/entry-no-stranger@1.0.0",
        ),
        encoding="utf-8",
    )
    result = asyncio.run(TracePlayer(load_trace(out), target="sim", agent=manifest).replay())
    assert result.verdicts == run.verdicts
    assert not result.action("unlock_door").blocked  # the pin is driven at the ALLOW frames
    assert [r.get("reason") for r in result.gate_results] == run.reasons


def test_a_golden_of_a_scene_catches_a_gate_that_stopped_blocking(tmp_path):
    golden = tmp_path / "golden.json"
    record_scene(SCENES_DIR / "stranger-at-door", golden)
    again = run_scene(SCENES_DIR / "stranger-at-door")
    assert_matches_golden(again.trace, golden)
    other = run_scene(SCENES_DIR / "frozen-camera-at-door")
    with pytest.raises(AssertionError):
        assert_matches_golden(other.trace, golden)


def test_assert_verdicts_names_the_difference():
    run = run_scene(SCENES_DIR / "frozen-camera-at-door")
    with pytest.raises(AssertionError, match="verdicts"):
        assert_verdicts(run, ["ALLOW"] * 5)
    with pytest.raises(AssertionError, match="reasons"):
        assert_verdicts(run, ["BLOCK"] * 5, reason="condition_not_met")


# --- frames from files -------------------------------------------------------------------------


def test_a_numeric_stem_is_the_camera_frame_number_and_a_gap_is_a_lost_frame():
    frames = load_frames(SCENES_DIR / "lost-frames-at-door").frames
    assert [f.seq for f in frames] == [1, 2, 3, 5, 6, 7, 8]
    assert [f.captured_ms for f in frames][:2] == [33.0, 66.0]


def test_a_frame_without_a_sidecar_is_a_silent_model_not_an_empty_scene():
    run = run_scene(SCENES_DIR / "silent-model-at-door")
    events = [e["data"] for e in run.trace["events"] if e["type"] == "vision_fact"]
    assert any(f.get("rejected") == "model_unavailable" for d in events for f in d["frames"])


def test_a_scene_that_is_malformed_is_a_three_part_error(tmp_path):
    with pytest.raises(AgentManifestError):
        load_scene(tmp_path)  # no scene.toml
    scene = tmp_path / "s"
    shutil.copytree(SCENES_DIR / "frozen-camera-at-door", scene)
    (scene / "scene.toml").write_text('gate = "vision/zone-clear@1.0.0"\nbogus = 1\n')
    with pytest.raises(AgentManifestError) as excinfo:
        load_scene(scene)
    assert "bogus" in excinfo.value.why and excinfo.value.how
    (scene / "scene.toml").write_text('gate = "vision/zone-clear@1.0.0"\n')
    (scene / "0001.json").write_text("[{}]")
    with pytest.raises(AgentManifestError):
        load_scene(scene)
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(AgentManifestError):
        load_frames(empty)
