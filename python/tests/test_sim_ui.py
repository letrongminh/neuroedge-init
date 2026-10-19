"""
TSK-S2-09 — `neuroedge run --ui` (FR-TGT-06): the sim session live in a browser.

The server is started for real on 127.0.0.1 and driven over HTTP, as the page does.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import select
import shlex
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from neuroedge.paths import repo_root
from neuroedge.sim import SimSession
from neuroedge.sim.ui import SessionServer, describe_agent

from .ui_support import page_headers

TIMEOUT = 10.0


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


def test_the_key_is_never_in_the_page_the_state_or_the_printed_url(server):
    # DP-A-02: anyone can GET the page, and the printed URL ends up in argv and logs.
    post(server, "mở cửa phòng 101")
    for path in ("/", "/state"):
        assert server.key not in get(server, path)[2]
    assert server.key not in server.open_url
    assert server.open_url.startswith(f"{server.url}#c=")
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


def pair(server, code, origin=True):
    headers = {"Content-Type": "application/json"}
    if origin:
        headers["Origin"] = page_headers(server)["Origin"]
    request = urllib.request.Request(
        server.url + "pair",
        data=json.dumps({"code": code}).encode(),
        method="POST",
        headers=headers,
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, None


def refusals(server):
    return json.loads(get(server, "/state")[2])["events"]


def test_the_printed_code_pairs_once_and_then_is_spent(server):
    # Whoever reads the URL after the page opened it (ps, a log) holds a spent code.
    code = server.open_url.split("#c=", 1)[1]
    assert pair(server, code) == (200, {"ok": True, "key": server.key})
    assert pair(server, code) == (403, None)
    assert server.open_url.endswith("#c=spent")
    refused = [e["data"] for e in refusals(server) if e["type"] == "ui_auth_refused"]
    assert refused == [{"reason": "bad_code", "path": "/pair"}]


def test_a_wrong_or_late_code_does_not_pair(server, monkeypatch):
    code = server.open_url.split("#c=", 1)[1]
    assert pair(server, "x" * 22) == (403, None)
    assert pair(server, code, origin=False) == (403, None)  # curl: no Origin
    monkeypatch.setattr(server, "_code_deadline", 0.0)  # ten minutes have passed
    assert pair(server, code) == (403, None)


def test_a_refused_path_is_traced_cut_short(server):
    # The request line is the caller's: a flood of long paths must not grow the trace.
    request = urllib.request.Request(server.url + "command/" + "a" * 5000, data=b"x", method="POST")
    with pytest.raises(urllib.error.HTTPError):
        urllib.request.urlopen(request, timeout=5)
    refused = [e["data"] for e in refusals(server) if e["type"] == "ui_auth_refused"]
    assert len(refused[0]["path"]) == 64


# --- the page explains any agent in its own words ([ui.labels], docs/spec/simulation_coverage.md §5.1)


def test_labels_are_words_for_people_and_anything_else_is_left_out(tmp_path):
    from neuroedge.sim.ui import ui_labels

    manifest = tmp_path / "agent.toml"
    manifest.write_text(
        '[ui.labels]\ngate_relay = "Máy sưởi"\nblank = "  "\nnumber = 3\n', encoding="utf-8"
    )
    assert ui_labels(manifest) == {"gate_relay": "Máy sưởi"}
    manifest.write_text("[ui]\nlabels = 1\n", encoding="utf-8")
    assert ui_labels(manifest) == {}
    manifest.write_text("not toml [", encoding="utf-8")
    assert ui_labels(manifest) == {}
    assert ui_labels(tmp_path / "missing.toml") == {}


def test_the_page_carries_what_it_needs_to_explain_the_aquarium(root):
    from neuroedge.sim.ui import describe_agent

    session = SimSession.load(root / "fixtures" / "agents" / "aquarium" / "agent.toml")
    agent = describe_agent(session)
    assert agent["labels"]["gate_relay"] == "Máy sưởi"
    heater = next(a for a in agent["actions"] if a["name"] == "tank_heater_on")
    assert heater["pins"] == ["gate_relay"]
    assert {"tool": "tank_heater_on", "say": "bật sưởi"} in agent["commands"]
    assert agent["sensor_facts"]["water_hot"] == {"sensor": "temperature", "rule": "gte 29"}
    asks = [g for g in agent["gates"].values() if g["on_block"].get("confirms")]
    assert asks and all(g["criteria"] for g in agent["gates"].values())
    assert agent["facts"]["owner_confirmed"] is False
    assert agent["sensors"] == ["temperature"]  # not every sensor the board has
    json.dumps(agent)  # embedded in the page as JSON


def test_the_live_page_embeds_the_agent_and_a_trace_view_has_none(root):
    from neuroedge.viz import render_trace_html

    session = SimSession.load(root / "fixtures" / "agents" / "aquarium" / "agent.toml")
    server = SessionServer(session, port=0).start()
    try:
        _, _, body = get(server, "/")
    finally:
        server.stop()
    assert "Máy sưởi" in body and "agent: data.agent" in body
    assert '"agent": {}' in render_trace_html({"metadata": {}, "events": []})


SAMPLES = sorted((repo_root() / "fixtures" / "agents").iterdir())


@pytest.mark.parametrize("sample", SAMPLES, ids=[s.name for s in SAMPLES])
def test_the_page_can_describe_every_sample_agent(sample):
    """Every sample's page loads: `describe_agent` runs for each, on its own board or the first
    reference board that fits (factory-monitor's banded fact once made the page answer nothing)."""
    from neuroedge.errors import BuildFailed

    for board in (None, "sim-rpi5"):
        try:
            session = SimSession.load(sample / "agent.toml", board_id=board)
            break
        except BuildFailed:
            continue
    try:
        described = describe_agent(session)
    finally:
        session.hal.close()
    json.dumps(described)  # the page embeds it as JSON
    assert described["actions"], sample.name


# --- a page started in the background stops on its own (2026-10-19: 44 orphaned pages) ---------


def test_idle_timeout_counts_requests_not_the_open_stream(server):
    from neuroedge.sim.ui import stop_reason

    parent = os.getppid()
    assert stop_reason(server, parent, exit_with_parent=False, idle_timeout=None) is None
    server.last_request -= 30
    assert "--idle-timeout" in stop_reason(server, parent, False, idle_timeout=20)
    get(server, "/state")  # any request resets it
    assert stop_reason(server, parent, False, idle_timeout=20) is None


def test_exit_with_parent_stops_once_the_parent_is_gone(server):
    from neuroedge.sim.ui import stop_reason

    assert stop_reason(server, os.getppid(), exit_with_parent=True, idle_timeout=None) is None
    assert "--exit-with-parent" in stop_reason(server, os.getppid() + 1, True, None)
    assert "--exit-with-parent" in stop_reason(server, 1, True, None)  # orphaned from the start
    assert stop_reason(server, os.getppid() + 1, exit_with_parent=False, idle_timeout=None) is None


@pytest.mark.parametrize("flag", [["--exit-with-parent"], ["--idle-timeout", "5"]])
def test_the_stop_options_need_the_page(root, flag):
    from typer.testing import CliRunner

    from neuroedge.cli.main import app

    agent = root / "fixtures" / "agents" / "villa-concierge" / "agent.toml"
    result = CliRunner().invoke(app, ["run", "--agent", str(agent), "-c", "bật đèn", *flag])
    assert result.exit_code != 0
    assert "add --ui" in result.output


def _run_ui(root, *extra: str) -> list[str]:
    agent = root / "fixtures" / "agents" / "villa-concierge" / "agent.toml"
    return [sys.executable, "-m", "neuroedge.cli.main", "run", "--agent", str(agent), "--ui"] + [
        "--no-browser",
        "--port",
        "0",
        *extra,
    ]


def _child_env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k != "FORCE_COLOR"}
    env.update({"PYTHONPATH": str(repo_root() / "python"), "NO_COLOR": "1"})
    return env


def _gone(pid: int, within: float) -> bool:
    deadline = time.monotonic() + within
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        time.sleep(0.1)
    return False


def test_a_page_backgrounded_by_a_shell_that_exits_stops_with_it(root, tmp_path):
    """The leak's shape: `cmd &` in a script that then exits leaves the page to PID 1."""
    command = " ".join(shlex.quote(part) for part in _run_ui(root, "--exit-with-parent"))
    started = subprocess.run(
        ["sh", "-c", f"{command} >{shlex.quote(str(tmp_path / 'ui.log'))} 2>&1 & echo $!"],
        capture_output=True,
        text=True,
        env=_child_env(),
        timeout=TIMEOUT,
    )
    pid = int(started.stdout.strip())
    try:
        assert _gone(pid, within=3 * TIMEOUT), (tmp_path / "ui.log").read_text()
        assert "--exit-with-parent" in (tmp_path / "ui.log").read_text()
    finally:
        with contextlib.suppress(ProcessLookupError):
            os.kill(pid, signal.SIGKILL)


def test_an_idle_page_stops_and_removes_its_link_file(root, tmp_path):
    link = Path(os.environ["XDG_STATE_HOME"]) / "neuroedge" / "ui.json"
    process = subprocess.Popen(
        _run_ui(root, "--idle-timeout", "1"),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=_child_env(),
        start_new_session=True,
    )
    try:
        output, _ = process.communicate(timeout=3 * TIMEOUT)
        assert process.returncode == 0, output.decode()
        assert "--idle-timeout" in output.decode()
        assert not link.exists()
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()


def _ready(process: subprocess.Popen, within: float) -> str:
    """The output up to the printed URL: the page serves, and SIGTERM is handled."""
    output, deadline = b"", time.monotonic() + within
    while b"sim UI at" not in output and time.monotonic() < deadline:
        if select.select([process.stdout], [], [], 0.1)[0]:
            chunk = os.read(process.stdout.fileno(), 4096)
            if not chunk:
                break
            output += chunk
    return output.decode(errors="replace")


def test_sigterm_stops_the_page_like_ctrl_c(root):
    link = Path(os.environ["XDG_STATE_HOME"]) / "neuroedge" / "ui.json"
    process = subprocess.Popen(
        _run_ui(root),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=_child_env(),
        start_new_session=True,
    )
    try:
        output = _ready(process, within=3 * TIMEOUT)
        assert "sim UI at" in output, output
        assert link.exists()
        process.terminate()
        assert process.wait(3 * TIMEOUT) == 128 + signal.SIGTERM
        assert not link.exists()  # the `finally` ran: with Python's default it would stay
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()


def test_a_signal_just_after_the_link_file_is_written_still_removes_it(root):
    """The 3.12 CI race of PR #148: SIGTERM between `start()` and the serving loop."""
    from neuroedge.sim.ui import serve

    link = Path(os.environ["XDG_STATE_HOME"]) / "neuroedge" / "ui.json"

    class Console:
        def print(self, *args, **kwargs):  # the first thing after `ui.json` is written
            assert link.exists()
            raise SystemExit(128 + signal.SIGTERM)

    session = SimSession.load(root / "fixtures" / "agents" / "villa-concierge" / "agent.toml")
    with pytest.raises(SystemExit):
        serve(session, 0, Console(), open_browser=False)
    assert not link.exists()
