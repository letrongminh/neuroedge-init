"""
TSK-S2-09 — `neuroedge run --ui` (FR-TGT-06): the sim session live in a browser.

The server is started for real on 127.0.0.1 and driven over HTTP, as the page does.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

import pytest

from neuroedge.sim import SimSession
from neuroedge.sim.ui import SessionServer

from .ui_support import page_headers


@pytest.fixture
def server(root):
    session = SimSession.load(root / "fixtures" / "agents" / "villa-concierge" / "agent.toml")
    server = SessionServer(session, port=0).start()
    yield server
    server.stop()


def get(server, path):
    with urllib.request.urlopen(server.url.rstrip("/") + path, timeout=5) as response:
        return (
            response.status,
            response.headers.get("Content-Type"),
            response.read().decode("utf-8"),
        )


def post(server, text, headers=None):
    request = urllib.request.Request(
        server.url + "command",
        data=text.encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "text/plain; charset=utf-8",
            **page_headers(server),
            **(headers or {}),
        },
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read())


def test_the_page_is_live_and_offline(server):
    status, kind, body = get(server, "/")
    assert status == 200 and kind.startswith("text/html")
    assert "new EventSource('/events')" in body
    assert "fetch('/command'" in body
    assert not re.search(r"<(script|link|img)[^>]+(src|href)=", body)
    assert "villa-concierge@0.1.0" in body


def test_a_command_from_the_page_runs_the_gate_and_moves_the_pin(server):
    reply = post(server, "mở cửa phòng 101")
    assert reply == {
        "ok": True,
        "recognised": True,
        "intent": "unlock",
        "verdict": "ALLOW",
        "action": "unlock_door",
    }
    _, kind, body = get(server, "/state")
    assert kind == "application/json"
    state = json.loads(body)
    commands = [e["data"] for e in state["events"] if e["type"] == "actuator_command"]
    assert commands == [{"pin": "door_lock", "operation": "pulse", "duration_ms": 30000}]
    assert state["now_ms"] >= 0


def test_facts_and_sensors_change_from_the_page(server):
    assert post(server, ":set guest_authenticated false") == {
        "ok": True,
        "fact": "guest_authenticated",
    }
    assert post(server, "mở cửa phòng 101")["verdict"] == "BLOCK"
    assert post(server, ":sensor temperature 31")["ok"] is True
    state = json.loads(get(server, "/state")[2])
    assert {"sensor": "temperature", "value": 31} in [
        e["data"] for e in state["events"] if e["type"] == "sensor_set"
    ]
    assert post(server, ":sensor co2 400")["ok"] is False  # the board has no co2 sensor


def test_an_unknown_line_is_answered_not_crashed(server):
    assert post(server, "hát một bài") == {"ok": True, "recognised": False, "intent": None}
    assert post(server, ":nope")["ok"] is False


def test_another_origin_cannot_send_commands(server):
    with pytest.raises(urllib.error.HTTPError) as refused:
        post(server, "mở cửa phòng 101", headers={"Origin": "http://evil.example"})
    assert refused.value.code == 403
    state = json.loads(get(server, "/state")[2])
    assert not [e for e in state["events"] if e["type"] == "actuator_command"]


def test_the_event_stream_pushes_the_session(server):
    post(server, "mở cửa phòng 101")
    with urllib.request.urlopen(server.url + "events", timeout=5) as stream:
        assert stream.headers.get("Content-Type") == "text/event-stream"
        line = stream.readline().decode("utf-8")
    assert line.startswith("data: ")
    pushed = json.loads(line[len("data: ") :])
    assert any(e["type"] == "actuator_command" for e in pushed["events"])


def test_the_key_is_never_in_the_page_or_the_state(server):
    # DP-A-02: the key lives only after `#` in the printed URL; anyone can GET the page.
    post(server, "mở cửa phòng 101")
    for path in ("/", "/state"):
        assert server.key not in get(server, path)[2]
    assert server.open_url == f"{server.url}#k={server.key}"
    assert len(server.key) >= 43  # 32 random bytes
    with urllib.request.urlopen(server.url + "events", timeout=5) as stream:
        assert server.key not in stream.readline().decode("utf-8")


def test_each_run_has_its_own_key(root):
    agent = root / "fixtures" / "agents" / "villa-concierge" / "agent.toml"
    a = SessionServer(SimSession.load(agent), port=0).start()
    b = SessionServer(SimSession.load(agent), port=0).start()
    try:
        assert a.key != b.key
    finally:
        a.stop()
        b.stop()
