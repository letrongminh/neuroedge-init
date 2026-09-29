"""
`neuroedge studio` device routes (docs/spec/studio.md §4): firmware status, golden screens,
QEMU and OTA logs, the ESP-IDF project build. Nothing here compiles C or runs QEMU.
"""

from __future__ import annotations

import json
import shutil
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from neuroedge import paths
from neuroedge.sim import SimSession
from neuroedge.studio import StudioServer

ROOT = Path(__file__).resolve().parents[2]
VILLA_DIR = ROOT / "fixtures" / "agents" / "villa-concierge"

OTA_LINES = {
    "a": ["NE_OTA CHECK url=http://x/ota", "NE_OTA SKIP reason=same_version version=0.1.0"],
    "b": ["NE_OTA SWITCH partition=ota_0", "NE_OTA VALID partition=ota_0"],
    "c": ["NE_OTA REJECTED reason=signature"],
    "d": [
        "NE_OTA SWITCH partition=ota_1",
        "NE_OTA TEST BOOTLOOP",
        "NE_OTA ROLLBACK from=ota_1 to=ota_0",
        "NE_OTA SKIP reason=rolled_back version=0.3.0",
    ],
    "e": [
        "NE_OTA INVALID partition=ota_1",
        "NE_OTA ROLLBACK from=ota_1 to=ota_0",
        "NE_OTA SKIP reason=rolled_back version=0.3.1",
    ],
    "f": ["NE_OTA ROLLBACK from=ota_1 to=ota_0", "NE_OTA ERASED partition=ota_1"],
    "g": ["NE_OTA ROLLBACK from=ota_1 to=ota_0", "NE_OTA SKIP reason=downgrade version=0.1.0"],
}


def serve(agent_dir: Path):
    agent = agent_dir / "agent.toml"
    session = SimSession.load(agent)
    server = StudioServer(session, agent_path=agent).start()
    return server, session


@pytest.fixture
def agent_copy(tmp_path, fresh_actions):
    target = tmp_path / "agent"
    shutil.copytree(VILLA_DIR, target)
    return target


@pytest.fixture
def studio(agent_copy):
    server, session = serve(agent_copy)
    yield server
    server.stop()
    session.close()


def call(server, path, method="GET"):
    request = urllib.request.Request(
        server.url.rstrip("/") + path, data=b"{}" if method == "POST" else None, method=method
    )
    if method == "POST":
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=30) as reply:
            return reply.status, reply.headers.get("Content-Type"), reply.read()
    except urllib.error.HTTPError as error:
        return error.code, error.headers.get("Content-Type"), error.read()


def get_json(server, path, method="GET"):
    status, _, body = call(server, path, method)
    assert status == 200
    return json.loads(body)


def fake_repo(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    (root / "targets" / "esp32s3" / "build").mkdir(parents=True)
    monkeypatch.setattr(paths, "repo_root", lambda: root)
    return root, root / "targets" / "esp32s3" / "build"


def test_screens_of_this_checkout_have_both_languages(studio):
    device = get_json(studio, "/api/device")
    assert device["ok"] is True and device["firmware"] == {"built": False}
    assert len(device["screens"]) == 33
    assert all(screen["langs"] == ["vi", "en"] for screen in device["screens"])
    assert device["golden"] == {}


def test_a_listed_golden_image_is_a_png(studio):
    name = get_json(studio, "/api/device")["screens"][0]["name"]
    for lang in ("vi", "en"):
        status, content_type, body = call(studio, f"/api/device/golden/{lang}/{name}.png")
        assert status == 200 and content_type == "image/png"
        assert body.startswith(b"\x89PNG")


@pytest.mark.parametrize("name", ["..", "%2E%2E", "%2Fetc%2Fpasswd", "no-such-screen", "a%2Fb"])
def test_golden_refuses_anything_not_listed(studio, name):
    status, _, body = call(studio, f"/api/device/golden/vi/{name}.png")
    if status == 200:
        assert json.loads(body)["ok"] is False
    else:
        assert status in (400, 404)
    assert not body.startswith(b"\x89PNG")


def test_qemu_and_ota_logs_are_parsed(agent_copy, tmp_path, monkeypatch):
    server, session = serve(agent_copy)
    _, build_dir = fake_repo(tmp_path, monkeypatch)
    uart = [
        "boot noise",
        "NE_SELFTEST PASS walker=26 token=11",
        "NE_TRACE DONE sessions=4",
        "  NE_SELFTEST FAIL walker=1 token=1 (indented, not a marker)",
    ]
    (build_dir / "uart.log").write_text("\r\n".join(uart) + "\r\n", encoding="utf-8")
    logs = build_dir / "ota-test" / "logs"
    logs.mkdir(parents=True)
    (logs / "build.esp32s3.log").write_text("NE_OTA SWITCH partition=ota_0\n", encoding="utf-8")
    for phase, lines in OTA_LINES.items():
        if phase == "d":
            (logs / "d-1.log").write_text("\n".join(lines[:2]) + "\n", encoding="utf-8")
            (logs / "d-2.log").write_text("\n".join(lines[2:]) + "\n", encoding="utf-8")
        else:
            (logs / f"{phase}.log").write_text(
                "noise\r\n" + "\r\n".join(lines) + "\r\n", encoding="utf-8"
            )
    # phase e also broke a rule of the script: a VALID on the new slot.
    (logs / "e.log").write_text(
        "\n".join([*OTA_LINES["e"], "NE_OTA VALID partition=ota_1"]) + "\n", encoding="utf-8"
    )

    try:
        device = get_json(server, "/api/device")
    finally:
        server.stop()
        session.close()
    assert device["screens"] == []
    assert device["qemu"]["selftest"] == "NE_SELFTEST PASS walker=26 token=11"
    assert device["qemu"]["trace_done"] == "NE_TRACE DONE sessions=4"
    assert len(device["qemu"]["log"]) == 4
    phases = {p["phase"]: p for p in device["ota"]["phases"]}
    assert list(phases) == list("abcdefg")
    assert phases["a"]["markers"] == OTA_LINES["a"]
    assert phases["d"]["markers"] == OTA_LINES["d"]
    assert all(phases[p]["ok"] for p in "abcdfg")
    assert phases["e"]["ok"] is False


def test_no_log_directories_mean_null(agent_copy, tmp_path, monkeypatch):
    server, session = serve(agent_copy)
    fake_repo(tmp_path, monkeypatch)
    try:
        device = get_json(server, "/api/device")
    finally:
        server.stop()
        session.close()
    assert device["qemu"] is None and device["ota"] is None
    assert "run.sh" in device["hint"]


def test_outside_a_checkout_there_are_no_screens(agent_copy, tmp_path, monkeypatch):
    server, session = serve(agent_copy)
    monkeypatch.setattr(paths, "repo_root", lambda: paths.PACKAGED)
    try:
        device = get_json(server, "/api/device")
    finally:
        server.stop()
        session.close()
    assert device["screens"] == [] and device["qemu"] is None and "repository" in device["hint"]


def test_build_writes_the_esp_idf_project(studio, agent_copy):
    built = get_json(studio, "/api/device/build", "POST")
    assert built["ok"] is True and built["built"] is True
    assert (agent_copy / "build" / "esp32s3" / "CMakeLists.txt").is_file()
    assert built["files"] > 0 and "gate(s)" in built["checked"]
    device = get_json(studio, "/api/device")
    assert device["firmware"]["built"] is True and device["firmware"]["files"] > 0


def test_a_board_that_cannot_serve_the_agent_fails_and_writes_nothing(agent_copy):
    server, session = serve(agent_copy)
    # The pins change after the sim session loaded, as the CI job's copy would have them.
    manifest = agent_copy / "agent.toml"
    manifest.write_text(
        manifest.read_text(encoding="utf-8").replace(
            'pins = ["door_lock"]', 'pins = ["garage_door"]'
        ),
        encoding="utf-8",
    )
    assert "garage_door" in manifest.read_text(encoding="utf-8")
    try:
        result = get_json(server, "/api/device/build", "POST")
    finally:
        server.stop()
        session.close()
    assert result["ok"] is False and result["error"]["problems"]
    assert not (agent_copy / "build").exists()
