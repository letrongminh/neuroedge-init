"""
The conversation state machine's compliance corpus (TSK-S3-10) on the Python
implementation (TSK-S3-11). docs/spec/voice_fsm.md §9: an implementation is
compliant when it passes every case; the C/C++ one runs the same files.
"""

from __future__ import annotations

import json

import pytest

from neuroedge.errors import NeuroEdgeError
from neuroedge.testing import voice_corpus as vc

CASES = vc.case_files()


def test_corpus_is_not_empty():
    assert CASES, f"no case in {vc.corpus_dir()}"


def test_corpus_is_closed_both_ways():
    assert vc.closure_problems() == []


def test_corpus_covers_every_scenario_row_and_trigger():
    assert vc.coverage_problems() == []


@pytest.mark.parametrize("path", CASES, ids=[p.name for p in CASES])
def test_case_passes(path):
    case = vc.load_case(path)
    expected = vc.load_expected()[case.name]
    differences = vc.run_case(case, expected)
    assert differences == [], "\n".join(differences)


def test_closure_catches_a_file_without_an_answer(tmp_path):
    (tmp_path / "vx.json").write_text("{}", encoding="utf-8")
    (tmp_path / vc.EXPECTED_FILE).write_text(
        "gone.json: {proves: x, events: []}\n", encoding="utf-8"
    )
    problems = vc.closure_problems(tmp_path)
    assert any("vx.json: no entry" in p for p in problems)
    assert any("gone.json: an entry" in p for p in problems)


def test_a_wrong_answer_is_reported():
    case = vc.load_case(vc.corpus_dir() / "v2_barge_in_during_running_pulse.json")
    expected = vc.load_expected()[case.name]
    # An implementation that cut the running pulse would add an abort: the answer has none.
    tampered = {
        "events": [
            *expected["events"][:7],
            {
                "offset_ms": 3300,
                "type": "actuator_aborted",
                "data": {"pin": "door_lock", "reason": "ACTUATOR_ABORTED_BY_BARGE_IN"},
            },
            *expected["events"][7:],
        ]
    }
    assert vc.run_case(case, tampered)


def test_covers_must_match_the_answer(tmp_path):
    source = vc.corpus_dir() / "v7_slow_speaker_pauses_are_not_turn_ends.json"
    document = json.loads(source.read_text(encoding="utf-8"))
    document["covers"] = [*document["covers"], "T12"]
    (tmp_path / source.name).write_text(json.dumps(document), encoding="utf-8")
    answers = vc.load_expected()
    import yaml

    (tmp_path / vc.EXPECTED_FILE).write_text(
        yaml.safe_dump({source.name: answers[source.name]}, allow_unicode=True), encoding="utf-8"
    )
    assert any("covers" in p for p in vc.coverage_problems(tmp_path))


@pytest.mark.parametrize(
    "mutate, fragment",
    [
        (lambda d: d.update(scenario="V9"), "scenario"),
        (lambda d: d.update(covers=["T99"]), "covers"),
        (lambda d: d.update(agent="nobody"), "agent"),
        (lambda d: d.update(params={"silence": 1}), "params"),
        (
            lambda d: d["inputs"].append(
                {"offset_ms": 0, "type": "wake_word_detected", "data": {}}
            ),
            "inputs",
        ),
        (
            lambda d: d["inputs"].append(
                {"offset_ms": 99999, "type": "tts_stream_start", "data": {}}
            ),
            "inputs",
        ),
        (lambda d: d.update(until_ms=1), "until_ms"),
    ],
)
def test_malformed_cases_are_refused(tmp_path, mutate, fragment):
    source = vc.corpus_dir() / "v7_slow_speaker_pauses_are_not_turn_ends.json"
    document = json.loads(source.read_text(encoding="utf-8"))
    mutate(document)
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(NeuroEdgeError) as caught:
        vc.load_case(path)
    assert fragment in caught.value.where


def test_barge_in_is_not_an_input(tmp_path):
    source = vc.corpus_dir() / "v2_barge_in_during_running_pulse.json"
    document = json.loads(source.read_text(encoding="utf-8"))
    document["inputs"][-1]["data"]["reason"] = "barge_in"
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(NeuroEdgeError, match="output"):
        vc.load_case(path)
