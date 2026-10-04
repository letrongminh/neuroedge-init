"""
`neuroedge studio` checks API (docs/spec/studio.md §4): traces, replay, record, lint, verify, test.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from neuroedge.sim import SimSession
from neuroedge.studio import StudioServer
from neuroedge.templates import scaffold

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def agent(tmp_path, fresh_actions):
    scaffold("villa", "villa-concierge", parent=tmp_path)
    return tmp_path / "villa" / "agent.toml"


@pytest.fixture
def studio(agent):
    session = SimSession.load(agent)
    server = StudioServer(session, agent_path=agent).start()
    yield server
    server.stop()
    session.close()


def _open(request):
    try:
        with urllib.request.urlopen(request, timeout=200) as reply:
            return reply.status, json.loads(reply.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def get(server, path):
    return _open(server.url.rstrip("/") + path)


def post(server, path, body=b"{}"):
    request = urllib.request.Request(server.url.rstrip("/") + path, data=body, method="POST")
    request.add_header("Content-Type", "application/json")
    return _open(request)


def type_command(server, text):
    status, reply = post(server, "/command", text.encode())
    assert status == 200, reply


def test_record_list_get_replay_round_trip_and_the_words_are_hashed(studio, agent):
    type_command(studio, "mở cửa phòng 101")
    status, recorded = post(studio, "/api/record")
    assert status == 200 and recorded["ok"] and recorded["events"] > 0
    name = recorded["name"]

    saved = agent.parent / "traces" / f"{name}.json"
    text = saved.read_text(encoding="utf-8")
    assert "mở cửa phòng 101" not in text
    assert json.loads(text)["metadata"]["anonymized"] is True

    _, listing = get(studio, "/api/traces")
    entry = next(t for t in listing["traces"] if t["name"] == name)
    assert entry["valid"] and entry["anonymized"] is True
    assert entry["events"] == recorded["events"] and entry["target"] == "sim"

    _, full = get(studio, f"/api/traces/{name}")
    assert full["ok"] and full["metadata"]["session_id"] == name and full["events"]

    _, replayed = post(studio, f"/api/traces/{name}/replay")
    assert replayed["ok"] and replayed["match"] is True
    assert replayed["verdicts"] == ["ALLOW"] and replayed["pins"]


def test_a_trace_in_a_subfolder_is_listed_and_golden_is_not(studio, agent):
    traces = agent.parent / "traces"
    (traces / "incidents").mkdir(parents=True, exist_ok=True)
    (traces / "golden").mkdir(parents=True, exist_ok=True)
    happy = (ROOT / "fixtures" / "traces" / "happy-path.json").read_text(encoding="utf-8")
    (traces / "incidents" / "door.json").write_text(happy, encoding="utf-8")
    (traces / "golden" / "ref.json").write_text(happy, encoding="utf-8")
    _, listing = get(studio, "/api/traces")
    names = [t["name"] for t in listing["traces"]]
    assert "incidents@door" in names and not any("ref" in n for n in names)
    _, full = get(studio, "/api/traces/incidents@door")
    assert full["ok"]


def test_an_invalid_trace_file_is_listed_not_fatal(studio, agent):
    traces = agent.parent / "traces"
    traces.mkdir(exist_ok=True)
    (traces / "broken.json").write_text("{not json", encoding="utf-8")
    _, listing = get(studio, "/api/traces")
    entry = next(t for t in listing["traces"] if t["name"] == "broken")
    assert entry["valid"] is False and entry["error"]
    _, full = get(studio, "/api/traces/broken")
    assert full["ok"] is False


@pytest.mark.parametrize(
    "name", ["..@x", "..", "%2e%2e", "%2e%2e%2fagent", "%2Fetc%2Fpasswd", "nope"]
)
def test_names_that_are_not_recordings_are_refused(studio, name):
    for status, reply in (
        get(studio, f"/api/traces/{name}"),
        post(studio, f"/api/traces/{name}/replay"),
    ):
        assert status in (200, 404) and reply["ok"] is False


def test_an_absolute_path_is_not_a_trace_name(studio, agent):
    status, reply = get(studio, f"/api/traces/{agent}")
    assert status == 404 and reply["ok"] is False


def test_lint_resolves_the_villa_vision_and_library_gates(studio):
    _, reply = post(studio, "/api/lint")
    assert reply["ok"] and (reply["resolved"], reply["total"]) == (13, 13)
    assert {g["name"] for g in reply["gates"]} >= {"unlock_door"}
    assert all(g["status"] == "OK" and g["fail"] == "closed" for g in reply["gates"])


def test_verify_passes_and_the_matrix_defers_the_other_targets_to_ci(studio):
    _, reply = post(studio, "/api/verify")
    assert reply["ok"] and reply["passed"] is True
    assert reply["summary"].startswith("Passed:")
    assert reply["compared"] == "decisions only — not timing"
    rows = {row["item"]: row for row in reply["matrix"]}
    assert "happy-path.json" in rows and "tool-call corpus" in rows
    for row in rows.values():
        assert row["sim"] == {"status": "pass", "source": "local"}
        assert row["linux"] == {"source": "ci", "job": "linux-hal"}
        assert row["esp32s3"] == {"source": "ci", "job": "uart-trace"}


def test_test_runs_the_agents_own_tests(studio):
    _, reply = post(studio, "/api/test")
    assert reply["ok"] and reply["passed"] >= 1 and reply["failed"] == 0
    assert "passed" in reply["output_tail"]
