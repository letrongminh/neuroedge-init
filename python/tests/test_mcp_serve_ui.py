"""
TSK-S3-27 — `neuroedge mcp serve --ui`: one process, one session, two doors.

An MCP client (Claude Desktop, Cursor) calls tools over stdio; the `sim` page on
127.0.0.1 shows the same session live. A tool call from the client moves the
virtual device on the page at once, and a line typed on the page and a call
from the client never run at the same time (`docs/spec/tool_calling.md` §8).

stdout is the JSON-RPC channel, so the subprocess tests are the proof that
nothing else writes to it: a polluted stdout breaks the handshake.
"""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import anyio
import pytest
from mcp import Client, ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from neuroedge.mcp_server import build_server
from neuroedge.sim import SimSession
from neuroedge.sim.ui import SessionServer
from neuroedge.trace import validate_trace

PYTHON_DIR = Path(__file__).resolve().parents[1]
TIMEOUT = 10.0


@pytest.fixture
def home(root):
    return root / "fixtures" / "agents" / "home-voice" / "agent.toml"


@pytest.fixture
def served(home):
    session = SimSession.load(home)
    server = SessionServer(session, port=0).start()
    yield session, server
    server.stop()


def mcp_server_for(server: SessionServer):
    return build_server(server.session, lock=server.lock, on_change=server.notify)


def get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=TIMEOUT) as response:
        return json.loads(response.read())


def post(url: str, text: str, headers: dict | None = None) -> dict:
    request = urllib.request.Request(
        url + "command",
        data=text.encode("utf-8"),
        method="POST",
        headers={"Content-Type": "text/plain; charset=utf-8", **(headers or {})},
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return json.loads(response.read())


def of_type(events: list[dict], kind: str) -> list[dict]:
    return [e["data"] for e in events if e["type"] == kind]


def poll(check, timeout: float = TIMEOUT, every: float = 0.02):
    """Return `check()` as soon as it is truthy; fail after `timeout` seconds."""
    deadline = time.monotonic() + timeout
    while True:
        value = check()
        if value:
            return value
        if time.monotonic() > deadline:
            raise AssertionError(f"not true within {timeout} s")
        time.sleep(every)


# --- in process: the MCP server and the page over one session -----------------------------------


def test_an_mcp_call_shows_on_the_page_state(served):
    session, server = served

    async def main():
        async with Client(mcp_server_for(server)) as client:
            return await client.call_tool("light_on", {})

    result = anyio.run(main)
    assert (result.is_error, result.structured_content["status"]) == (False, "ALLOW")
    state = get_json(server.url + "state")
    assert of_type(state["events"], "actuator_command") == [
        {"pin": "porch_light", "operation": "on", "duration_ms": 0}
    ]
    (call,) = of_type(state["events"], "tool_call")
    assert (call["name"], call["source"]) == ("light_on", "mcp")


def test_every_mcp_call_wakes_the_event_stream_even_a_rejected_one(served):
    _, server = served

    async def main():
        async with Client(mcp_server_for(server)) as client:
            before = server.version
            await client.call_tool("light_on", {})
            after_allow = server.version
            rejected = await client.call_tool("light_on", {"brightness": 3})
            return before, after_allow, server.version, rejected

    before, after_allow, after_reject, rejected = anyio.run(main)
    assert rejected.is_error
    assert before < after_allow < after_reject


def test_the_event_stream_pushes_an_mcp_call_at_once(served):
    _, server = served

    def pushes(stream):
        for line in stream:
            if line.startswith(b"data: "):
                yield json.loads(line[len(b"data: ") :])

    with urllib.request.urlopen(server.url + "events", timeout=TIMEOUT) as stream:
        messages = pushes(stream)
        assert not of_type(next(messages)["events"], "actuator_command")

        async def main():
            async with Client(mcp_server_for(server)) as client:
                await client.call_tool("light_on", {})

        anyio.run(main)
        # Pushes sent before the call finished may still be queued: read on until it shows.
        deadline = time.monotonic() + TIMEOUT
        for pushed in messages:
            if of_type(pushed["events"], "actuator_command") or time.monotonic() > deadline:
                break
    assert of_type(pushed["events"], "actuator_command") == [
        {"pin": "porch_light", "operation": "on", "duration_ms": 0}
    ]
    assert [c["source"] for c in of_type(pushed["events"], "tool_call")] == ["mcp"]


def test_page_commands_and_mcp_calls_interleave_without_corrupting_the_session(served):
    session, server = served
    rounds = 12
    page_errors: list[BaseException] = []

    def page_side():
        try:
            for i in range(rounds):
                reply = post(server.url, "bật đèn" if i % 2 == 0 else "tắt đèn")
                assert reply["verdict"] == "ALLOW", reply
        except BaseException as error:  # reported by the main thread
            page_errors.append(error)

    async def mcp_side():
        async with Client(mcp_server_for(server)) as client:
            for i in range(rounds):
                result = await client.call_tool("light_off" if i % 2 == 0 else "light_on", {})
                assert result.structured_content["status"] == "ALLOW"

    typist = threading.Thread(target=page_side)
    typist.start()
    anyio.run(mcp_side)
    typist.join(TIMEOUT)
    assert not typist.is_alive() and not page_errors, page_errors

    events = list(session.events.events)
    calls = of_type(events, "tool_call")
    assert len(calls) == 2 * rounds
    assert [c["source"] for c in calls].count("mcp") == rounds
    assert [c["id"] for c in calls] == [f"call_{n}" for n in range(1, 2 * rounds + 1)]
    # One call at a time: between two tool_call events sits exactly that call's pin command.
    starts = [i for i, e in enumerate(events) if e["type"] == "tool_call"] + [len(events)]
    for start, end in zip(starts, starts[1:], strict=False):
        call = events[start]["data"]
        (command,) = of_type(events[start:end], "actuator_command")
        assert command["operation"] == ("on" if call["name"] == "light_on" else "off")
        (verdict,) = of_type(events[start:end], "gate_evaluation_result")
        assert verdict["evaluations"]["call_source"] == call["source"]
    offsets = [e["offset_ms"] for e in events]
    assert offsets == sorted(offsets)
    # The pin saw the commands in the order the calls were logged, none lost, none doubled.
    assert session.hal.pin("porch_light").commands == [
        ("on" if c["name"] == "light_on" else "off", 0) for c in calls
    ]
    validate_trace(session.trace())


def test_the_page_names_the_caller_of_each_verdict(served):
    _, server = served
    with urllib.request.urlopen(server.url, timeout=TIMEOUT) as response:
        body = response.read().decode("utf-8")
    assert '"tool_call " + g.call.name + " · " + g.call.source' in body
    # Trace text is only ever textContent; the one innerHTML is the constant SVG icons.
    assert set(re.findall(r"innerHTML\s*=\s*(\w+)", body)) == {"markup"}
    assert not re.search(r"<(script|link|img)[^>]+(src|href)=", body)


def test_another_origin_still_cannot_send_commands(served):
    session, server = served
    with pytest.raises(urllib.error.HTTPError) as refused:
        post(server.url, "bật đèn", headers={"Origin": "http://evil.example"})
    assert refused.value.code == 403
    assert not session.hal.pin("porch_light").commands


# --- the real command, as Claude Desktop starts it ----------------------------------------------


def serve_args(home: Path, *extra: str) -> list[str]:
    return ["-m", "neuroedge.cli.main", "mcp", "serve", "--agent", str(home), "--ui", *extra]


def child_env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in ("FORCE_COLOR",)}
    env.update({"PYTHONPATH": str(PYTHON_DIR), "NO_COLOR": "1"})
    return env


def test_the_real_command_serves_mcp_on_stdout_and_the_page_on_127_0_0_1(home, tmp_path):
    trace_out = tmp_path / "session.json"
    errlog_path = tmp_path / "stderr.txt"
    params = StdioServerParameters(
        command=sys.executable,
        args=serve_args(home, "--port", "0", "--trace-out", str(trace_out)),
        env=child_env(),
    )

    def ui_url() -> str | None:
        found = re.search(r"http://127\.0\.0\.1:\d+/", errlog_path.read_text(encoding="utf-8"))
        return found.group(0) if found else None

    # A line on stdout that is not JSON-RPC reaches the client as a transport exception.
    garbage: list[Exception] = []

    async def on_message(message):
        if isinstance(message, Exception):
            garbage.append(message)

    async def main():
        with errlog_path.open("w", encoding="utf-8") as errlog:
            async with (
                stdio_client(params, errlog=errlog) as (read, write),
                ClientSession(read, write, message_handler=on_message) as client,
            ):
                with anyio.fail_after(TIMEOUT):
                    await client.initialize()
                    tools = [t.name for t in (await client.list_tools()).tools]
                    result = await client.call_tool("light_on", {})
                    url = poll(ui_url)
                    state = await anyio.to_thread.run_sync(get_json, url + "state")
        return tools, result, url, state

    tools, result, url, state = anyio.run(main)
    assert garbage == []  # stdout carried the protocol and nothing else
    assert tools == ["light_on", "light_off"]
    assert (result.is_error, result.structured_content["status"]) == (False, "ALLOW")
    assert url.startswith("http://127.0.0.1:")
    assert of_type(state["events"], "actuator_command") == [
        {"pin": "porch_light", "operation": "on", "duration_ms": 0}
    ]
    assert [c["source"] for c in of_type(state["events"], "tool_call")] == ["mcp"]
    stderr = errlog_path.read_text(encoding="utf-8")
    assert "neuroedge MCP server · home-voice@0.1.0" in stderr
    assert "sim UI at http://127.0.0.1:" in stderr
    # Closing stdin ends the server cleanly: the trace is written and the page is gone.
    trace = poll(lambda: trace_out.exists() and json.loads(trace_out.read_text("utf-8")))
    validate_trace(trace)
    assert [e["type"] for e in trace["events"]].count("actuator_command") == 1
    with pytest.raises(urllib.error.URLError):
        urllib.request.urlopen(url + "state", timeout=2)


def test_a_taken_port_fails_before_the_mcp_loop_with_nothing_on_stdout(home):
    with socket.socket() as taken:
        taken.bind(("127.0.0.1", 0))
        taken.listen()
        port = taken.getsockname()[1]
        done = subprocess.run(
            [sys.executable, *serve_args(home, "--port", str(port))],
            env=child_env(),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=60,
        )
    assert done.returncode == 1
    assert done.stdout == b""
    stderr = done.stderr.decode("utf-8")
    assert f"sim UI on 127.0.0.1:{port}" in stderr
    assert "why:" in stderr and f"cannot listen on port {port}" in stderr
    assert "fix:" in stderr and "--port" in stderr
    assert "neuroedge MCP server" not in stderr  # the banner comes only once serving
