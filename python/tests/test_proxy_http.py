"""
TSK-I2c-15 (FR-EXT-06) — `neuroedge proxy http` and `neuroedge guard init --http`: a local HTTP API
that moves things, put behind NeuroEdge.

The upstream is `fixtures/http_upstream/server.py`, a stdlib HTTP server in its own process that
appends every request it receives to `UPSTREAM_LOG`: "the upstream was not asked" is read from that
file. The front is exercised with raw sockets, so what the proxy does with bytes is what is tested.
"""

from __future__ import annotations

import asyncio
import json
import re
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
from typer.testing import CliRunner

from neuroedge.cli.main import app
from neuroedge.engine import resolve_gate_file
from neuroedge.errors import AgentManifestError, NeuroEdgeError
from neuroedge.guard import Guard, load_config
from neuroedge.proxy_http import doctor, init, parse_http, serve
from neuroedge.testing import TracePlayer
from neuroedge.trace import validate_trace

from .test_proxy_mcp import open_gate

runner = CliRunner()
ROOT = Path(__file__).resolve().parents[2]
UPSTREAM = ROOT / "fixtures" / "http_upstream" / "server.py"
ROUTES = ["POST /cm/{cmd}", "GET /status", "POST /boom"]
TOKEN = "not-a-real-token"


def free_port() -> int:
    with socket.socket() as spare:
        spare.bind(("127.0.0.1", 0))
        return spare.getsockname()[1]


def wait_listening(port: int) -> None:
    for _ in range(100):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
            return
        except OSError:
            time.sleep(0.1)
    raise AssertionError(f"nothing listens on {port}")


@pytest.fixture
def log(tmp_path, monkeypatch):
    path = tmp_path / "upstream.log"
    monkeypatch.setenv("UPSTREAM_LOG", str(path))
    return path


@pytest.fixture
def upstream(log):
    port = free_port()
    server = subprocess.Popen(
        [sys.executable, str(UPSTREAM), str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    wait_listening(port)
    yield port
    server.terminate()
    server.wait(timeout=10)


def calls(log: Path) -> list[dict]:
    return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []


@pytest.fixture
def project(tmp_path, upstream):
    directory = tmp_path / "plug"
    init(f"http://127.0.0.1:{upstream}", ROUTES, directory, "plug")
    return directory


def edit(project: Path, old: str, new: str) -> None:
    path = project / "guard.toml"
    text = path.read_text(encoding="utf-8")
    assert old in text, old
    path.write_text(text.replace(old, new), encoding="utf-8")


async def request(port, method, target, body=b"", headers=None, *, raw_length=None):
    """One raw HTTP/1.1 request; (status, headers, body)."""
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    head = [f"{method} {target} HTTP/1.1", f"Host: 127.0.0.1:{port}"]
    for name, value in (headers or {}).items():
        head.append(f"{name}: {value}")
    length = len(body) if raw_length is None else raw_length
    if body or raw_length is not None:
        head.append(f"Content-Length: {length}")
    writer.write(("\r\n".join(head) + "\r\n\r\n").encode() + body)
    await writer.drain()
    data = await asyncio.wait_for(reader.read(), 20)
    writer.close()
    head_text, _, payload = data.partition(b"\r\n\r\n")
    lines = head_text.decode("latin-1").split("\r\n")
    status = int(lines[0].split(" ")[1])
    return status, {k.lower(): v for k, _, v in (ln.partition(": ") for ln in lines[1:])}, payload


async def _with_proxy(project: Path, script, **kwargs):
    """`script(port, guard)` against the proxy served in this loop, stopped and traced afterwards."""
    stop = asyncio.Event()
    ready: asyncio.Future = asyncio.get_running_loop().create_future()
    holder = {}

    def on_ready(guard, proxy, port):
        holder["guard"] = guard
        ready.set_result(port)

    trace = project / "trace.json"
    task = asyncio.ensure_future(
        serve(project / "guard.toml", trace_out=trace, on_ready=on_ready, stop=stop, **kwargs)
    )
    try:
        port = await asyncio.wait_for(asyncio.shield(ready), 20)
    except BaseException:
        stop.set()
        await task
        raise
    try:
        return await script(port, holder["guard"])
    finally:
        stop.set()
        await task


def through(project, script):
    # port 0: the OS picks one; the test learns it from `on_ready`
    path = project / "guard.toml"
    path.write_text(
        re.sub(
            r'listen = "127.0.0.1:\d+"', 'listen = "127.0.0.1:0"', path.read_text(encoding="utf-8")
        ),
        encoding="utf-8",
    )
    return asyncio.run(_with_proxy(project, script))


def verdict(payload: bytes) -> dict:
    return json.loads(payload)


# --- forwarding -----------------------------------------------------------------------------------------


def test_the_proxy_forwards_only_after_allow_and_never_on_block(project, log):
    open_gate(project, "post_cm_cmd")

    async def script(port, guard):
        blocked = await request(port, "GET", "/status")
        allowed = await request(
            port, "POST", "/cm/Power?q=a%20b", b'{"x": 1}', {"Content-Type": "application/json"}
        )
        return blocked, allowed

    # the parameters the operator accepts: a query field `q` and a body field `x`
    edit(
        project,
        '[tools.post_cm_cmd.parameters.cmd]\ntype = "string"',
        '[tools.post_cm_cmd.parameters.cmd]\ntype = "string"\n\n[tools.post_cm_cmd.parameters.q]\n'
        'type = "string"\n\n[tools.post_cm_cmd.parameters.x]\ntype = "integer"',
    )
    blocked, allowed = through(project, script)
    assert blocked[0] == 403 and verdict(blocked[2])["status"] == "BLOCK"
    assert verdict(blocked[2])["reason"] == "criterion_unavailable"
    assert allowed[0] == 200
    assert json.loads(allowed[2]) == {"command": "Power", "query": "q=a%20b", "body": '{"x": 1}'}
    (seen,) = calls(log)
    assert (seen["method"], seen["target"], seen["body"]) == (
        "POST",
        "/cm/Power?q=a%20b",
        '{"x": 1}',
    ), "the ORIGINAL method, path, query and body reached the upstream; the BLOCK did not"
    assert allowed[1]["x-device"] == "plug-1" and "keep-alive" not in allowed[1]


def test_an_undeclared_route_is_a_404_and_nothing_is_forwarded(project, log):
    open_gate(project, "get_status")

    async def script(port, guard):
        return [
            await request(port, "GET", "/admin"),
            await request(port, "DELETE", "/status"),  # a declared path, an undeclared method
            await request(port, "GET", "/cm/Power"),
            await request(port, "GET", "/status/extra"),
        ]

    for status, _, body in through(project, script):
        assert status == 404 and "only declared routes pass" in verdict(body)["problems"][0]
    assert calls(log) == []


def test_unsafe_paths_are_refused_before_any_dispatch(project, log):
    open_gate(project, "post_cm_cmd")

    async def script(port, guard):
        out = [
            await request(port, "POST", "/cm/a%2Fb"),
            await request(port, "POST", "/cm/%2e%2e"),
            await request(port, "POST", "/cm//x"),
            await request(port, "POST", "/cm/a%00b"),
        ]
        return out, guard.events.of_type("tool_call")

    results, dispatched = through(project, script)
    assert all(status == 400 for status, _, _ in results)
    assert dispatched == [] and calls(log) == []


# --- source ---------------------------------------------------------------------------------------------


def test_the_proxy_dispatches_as_a_bridge_and_a_gate_listing_only_mcp_blocks_it(project, log):
    open_gate(project, "get_status")

    async def script(port, guard):
        ok = await request(port, "GET", "/status")
        return ok, guard.events

    ok, events = through(project, script)
    assert ok[0] == 200
    assert [e["source"] for e in events.of_type("tool_call")] == ["bridge:http"]
    assert events.of_type("gate_facts")[-1]["call_source"]["value"] == "bridge:http"

    gate = project / "gates" / "get_status@1.0.0.yaml"
    text = gate.read_text(encoding="utf-8")
    gate.write_text(
        text.replace('options: [local_grammar, system_one, system_two, mcp, "bridge:http", test]',
                     "options: [local_grammar, system_one, system_two, mcp, test]")
        .replace('{ in: ["bridge:http"] }', "{ in: [mcp] }"),
        encoding="utf-8",
    )  # fmt: skip

    async def only_mcp(port, guard):
        return await request(port, "GET", "/status")

    before = len(calls(log))
    status, _, body = through(project, only_mcp)
    assert status == 403 and verdict(body)["reason"] == "criterion_unavailable"
    assert len(calls(log)) == before, "a gate that lists only `mcp` never lets the bridge through"


def test_the_bridge_id_is_configurable(project, log):
    open_gate(project, "get_status")
    edit(project, 'id = "http"', 'id = "plug"')

    async def script(port, guard):
        await request(port, "GET", "/status")
        return guard.events

    events = through(project, script)
    assert [e["source"] for e in events.of_type("tool_call")] == ["bridge:plug"]


# --- arguments ----------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("target", "body", "headers", "dispatched", "complaint"),
    [
        ("/cm/Power?surprise=1", b"", {}, True, "surprise"),  # undeclared: the Guard says REJECTED
        ("/cm/Power", b'{"a": {"b": 1}}', {}, False, "not a scalar"),
        ("/cm/Power", b'{"a": [1]}', {}, False, "not a scalar"),
        ("/cm/Power", b'{"a": null}', {}, False, "not a scalar"),
        ("/cm/Power", b"[1, 2]", {}, False, "not a JSON object"),
        ("/cm/Power", b"not json", {}, False, "not JSON"),
        ("/cm/Power", b'{"a": 1, "a": 2}', {}, False, "twice"),
        ("/cm/Power?cmd=x", b"", {}, False, "given twice"),
        ("/cm/Power?a=1&a=2", b"", {}, False, "given twice"),
        ("/cm/Power?a=1", b'{"a": 2}', {}, False, "given twice"),
    ],
)
def test_a_bad_argument_is_a_400_and_nothing_is_forwarded(
    project, log, target, body, headers, dispatched, complaint
):
    open_gate(project, "post_cm_cmd")

    async def script(port, guard):
        response = await request(port, "POST", target, body, headers)
        return response, guard.events

    (status, _, payload), events = through(project, script)
    told = verdict(payload)
    assert status == 400 and told["status"] == "REJECTED", told
    assert complaint in json.dumps(told)
    assert bool(events.of_type("tool_call")) is dispatched
    assert calls(log) == []


def test_a_body_over_one_mebibyte_is_a_413_and_is_not_read(project, log):
    open_gate(project, "post_cm_cmd")

    async def script(port, guard):
        return await request(port, "POST", "/cm/Power", b"", raw_length=(1 << 20) + 1)

    status, _, payload = through(project, script)
    assert status == 413 and "larger than" in json.dumps(verdict(payload))
    assert calls(log) == []


# --- upstream trouble, headers --------------------------------------------------------------------------------


def test_an_upstream_failure_after_allow_is_a_502_and_is_not_retried(project, log):
    open_gate(project, "post_boom")

    async def script(port, guard):
        return await request(port, "POST", "/boom")

    status, _, payload = through(project, script)
    told = verdict(payload)
    assert status == 502 and told["status"] == "ALLOW" and "not retried" in told["problems"][0]
    assert [c["target"] for c in calls(log)] == ["/boom"], "asked once, never again"


def test_the_clients_credentials_are_not_forwarded_and_the_configured_ones_are(
    project, log, monkeypatch
):
    open_gate(project, "get_status")
    monkeypatch.setenv("DEVICE_TOKEN", TOKEN)
    edit(project, 'id = "http"', 'id = "http"\nheaders_env = { Authorization = "DEVICE_TOKEN" }')

    async def script(port, guard):
        return await request(
            port, "GET", "/status", headers={
                "Authorization": "Bearer the-clients-own", "Cookie": "session=abc",
                "X-Trace-Id": "t-1", "Connection": "x-secret", "X-Secret": "hop",
                "Proxy-Authorization": "Basic x",
            },
        )  # fmt: skip

    status, _, _ = through(project, script)
    assert status == 200
    (seen,) = calls(log)
    assert seen["headers"]["authorization"] == TOKEN, "the configured value replaced the client's"
    assert "cookie" not in seen["headers"] and "x-secret" not in seen["headers"]
    assert "proxy-authorization" not in seen["headers"]
    assert seen["headers"]["x-trace-id"] == "t-1", "an ordinary header goes through"
    assert "the-clients-own" not in json.dumps(seen)


def test_a_header_whose_variable_is_not_set_refuses_start(project, monkeypatch):
    monkeypatch.delenv("NEUROEDGE_SURELY_UNSET", raising=False)
    edit(
        project,
        'id = "http"',
        'id = "http"\nheaders_env = { Authorization = "NEUROEDGE_SURELY_UNSET" }',
    )
    with pytest.raises(NeuroEdgeError, match="NEUROEDGE_SURELY_UNSET"):
        asyncio.run(serve(project / "guard.toml"))


# --- refusing to start ----------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("old", "new", "why"),
    [
        ('listen = "127.0.0.1:8787"', 'listen = "0.0.0.0:8787"', "loopback only"),
        ('listen = "127.0.0.1:8787"', 'listen = "192.168.1.5:8787"', "loopback only"),
        ('listen = "127.0.0.1:8787"', 'listen = "example.com:80"', "loopback only"),
        ('listen = "127.0.0.1:8787"', 'listen = "8787"', "host:port"),
        ('upstream = "http://127.0.0.1:', 'upstream = "http://192.168.1.50:', "clear"),
        ('upstream = "http://127.0.0.1:', 'upstream = "http://user:pw@127.0.0.1:', "credentials"),
        ('upstream = "http://127.0.0.1:', 'upstream = "ftp://127.0.0.1:', "http(s)"),
        ('id = "http"', 'id = "Not-Valid"', "bridge id"),
        ('method = "GET"', 'method = "TRACE"', "method"),
        ('tool = "get_status"', 'tool = "nothing"', "not a [tools.<name>]"),
        ("[tools.post_cm_cmd.parameters.cmd]", "[tools.post_cm_cmd.parameters.other]", "REJECTED"),
        (
            'method = "GET"\npath = "/status"\ntool = "get_status"',
            'method = "POST"\npath = "/cm/{cmd}"\ntool = "post_cm_cmd"',
            "twice",
        ),
        ('path = "/status"', 'path = "/a/../b"', "`..`"),
        ('path = "/status"', 'path = "/a?b=1"', "query"),
    ],
)
def test_a_bad_proxy_config_is_a_three_part_error(project, old, new, why):
    edit(project, old, new)
    with pytest.raises(AgentManifestError) as refused:
        parse_http(load_config(project / "guard.toml"))
    error = refused.value
    assert error.code == "NE3002" and error.where and error.how
    assert why in error.where + error.why + error.how


def test_https_is_accepted_for_any_host_and_loopback_names_for_listen(project):
    edit(project, 'upstream = "http://127.0.0.1:', 'upstream = "https://device.example:')
    edit(project, 'listen = "127.0.0.1:8787"', 'listen = "localhost:8787"')
    proxy = parse_http(load_config(project / "guard.toml"))
    assert proxy.upstream.startswith("https://device.example") and proxy.host == "localhost"
    edit(project, 'listen = "localhost:8787"', 'listen = "[::1]:8787"')
    assert parse_http(load_config(project / "guard.toml")).host == "::1"


@pytest.mark.parametrize(
    "edit_to",
    [
        ('headers_env = { Authorization = "Bearer not-a-real-value" }', "NAME of an environment"),
        ('api_key = "not-a-real-value"', "api_key"),
        ('token = "not-a-real-value"', "token"),
    ],
)
def test_a_literal_secret_in_proxy_config_is_refused(project, edit_to):
    line, why = edit_to
    edit(project, 'id = "http"', f'id = "http"\n{line}')
    with pytest.raises(AgentManifestError) as refused:
        parse_http(load_config(project / "guard.toml"))
    assert why in refused.value.where + refused.value.why
    assert "not-a-real-value" not in json.dumps(refused.value.as_dict()), (
        "a pasted value is never echoed"
    )


def test_one_kind_of_proxy_per_file_and_the_right_command(project):
    text = (project / "guard.toml").read_text(encoding="utf-8")
    (project / "guard.toml").write_text(text + '\n[proxy.mcp]\ncommand = ["x"]\n', encoding="utf-8")
    with pytest.raises(AgentManifestError, match="both"):
        parse_http(load_config(project / "guard.toml"))
    from neuroedge.proxy_mcp import parse_upstream

    (project / "guard.toml").write_text(text, encoding="utf-8")
    with pytest.raises(AgentManifestError, match="use `proxy http`"):
        parse_upstream(load_config(project / "guard.toml"))


def test_a_tool_no_route_reaches_and_an_unreachable_upstream_refuse_start(project, tmp_path):
    text = (project / "guard.toml").read_text(encoding="utf-8")
    (project / "guard.toml").write_text(
        text + '\n[tools.orphan]\ngate = "gates/get_status@1.0.0.yaml"\n', encoding="utf-8"
    )
    with pytest.raises(AgentManifestError, match="no .*routes"):
        asyncio.run(serve(project / "guard.toml"))
    (project / "guard.toml").write_text(text, encoding="utf-8")
    edit(project, 'upstream = "http://127.0.0.1:', f'upstream = "http://127.0.0.1:{free_port()}" #')
    with pytest.raises(NeuroEdgeError) as refused:
        asyncio.run(serve(project / "guard.toml"))
    assert "cannot reach the real API" in refused.value.why and refused.value.how
    result = runner.invoke(app, ["proxy", "http", "--config", str(project / "guard.toml")])
    assert result.exit_code == 1 and "cannot reach" in result.output


# --- guard init --http -----------------------------------------------------------------------------------------


def test_guard_init_http_writes_blocking_gates_that_lint_and_load(project):
    gates = sorted(p.name for p in (project / "gates").iterdir())
    assert gates == ["get_status@1.0.0.yaml", "post_boom@1.0.0.yaml", "post_cm_cmd@1.0.0.yaml"]
    for gate in (project / "gates").iterdir():
        resolve_gate_file(gate)
        text = gate.read_text(encoding="utf-8")
        assert 'in: ["bridge:http"]' in text and "operator_approved: true" in text
    assert runner.invoke(app, ["gate", "lint", str(project / "gates")]).exit_code == 0
    guard = Guard.load(project / "guard.toml")  # as written
    guard.close()
    proxy = parse_http(load_config(project / "guard.toml"))
    assert [(r.method, r.path, r.tool) for r in proxy.routes] == [
        ("POST", "/cm/{cmd}", "post_cm_cmd"),
        ("GET", "/status", "get_status"),
        ("POST", "/boom", "post_boom"),
    ]
    assert proxy.host == "127.0.0.1" and proxy.id == "http"


def test_a_generated_gate_blocks_until_the_operator_opens_it(project, log):
    async def blocked(port, guard):
        return await request(port, "GET", "/status")

    status, _, payload = through(project, blocked)
    assert status == 403 and verdict(payload)["failed_criterion"] == "operator_approved"
    assert calls(log) == []
    open_gate(project, "get_status")
    status, _, payload = through(project, blocked)
    assert status == 200 and json.loads(payload) == {"power": "ON"}


def test_guard_init_http_never_overwrites_a_file(tmp_path):
    directory = tmp_path / "again"
    (directory / "gates").mkdir(parents=True)
    mine = directory / "gates" / "get_status@1.0.0.yaml"
    mine.write_text("# mine\n", encoding="utf-8")
    with pytest.raises(NeuroEdgeError, match="already exists"):
        init("http://127.0.0.1:1", ["GET /status"], directory)
    assert mine.read_text(encoding="utf-8") == "# mine\n"
    assert not (directory / "guard.toml").exists()


@pytest.mark.parametrize(
    ("upstream", "routes", "why"),
    [
        ("http://127.0.0.1:1", [], "no route"),
        ("http://127.0.0.1:1", ["FETCH /x"], "not `METHOD /path`"),
        ("http://127.0.0.1:1", ["GET status"], "starts with `/`"),
        ("http://127.0.0.1:1", ["GET /a/../b"], "`..`"),
        ("http://10.1.2.3", ["GET /x"], "clear"),
    ],
)
def test_guard_init_http_refuses_bad_input_and_writes_nothing(tmp_path, upstream, routes, why):
    with pytest.raises(NeuroEdgeError) as refused:
        init(upstream, routes, tmp_path / "x")
    assert why in refused.value.where + refused.value.why + refused.value.how
    assert not (tmp_path / "x").exists()


def test_guard_init_http_through_the_cli_needs_exactly_one_kind(tmp_path):
    both = runner.invoke(app, ["guard", "init", "--mcp", "x", "--http", "http://127.0.0.1:1"])
    neither = runner.invoke(app, ["guard", "init"])
    lonely_route = runner.invoke(app, ["guard", "init", "--mcp", "x", "--route", "GET /x"])
    no_route = runner.invoke(app, ["guard", "init", "--http", "http://127.0.0.1:1"])
    assert [r.exit_code for r in (both, neither, lonely_route, no_route)] == [2, 2, 2, 2]
    ok = runner.invoke(
        app,
        [
            "guard",
            "init",
            "--http",
            "http://127.0.0.1:1",
            "--route",
            "POST /cm/{cmd}",
            "--dir",
            str(tmp_path / "ok"),
        ],
    )
    assert ok.exit_code == 0, ok.output
    assert "neuroedge proxy http --config" in ok.output and "BLOCKED" in ok.output


# --- doctor ---------------------------------------------------------------------------------------------------


def test_doctor_warns_that_the_device_api_is_reachable_directly(project):
    findings = doctor(load_config(project / "guard.toml"))
    warned = [f.message for f in findings if f.level == "warning"]
    assert len(warned) == 1 and "còn tới được" in warned[0] and "tường lửa" in warned[0]
    text = "\n".join(f.message for f in findings)
    assert "không kiểm được: ứng dụng, script hay thiết bị khác" in text
    assert "không kiểm được: plugin (TSK-I2c-11)" in text
    result = runner.invoke(
        app, ["plugin", "doctor", "--config", str(project / "guard.toml"), "--json"]
    )
    assert result.exit_code == 1 and json.loads(result.output)["warnings"] == 1


def test_doctor_says_what_it_cannot_check_when_nothing_listens(project, upstream):
    edit(project, f"127.0.0.1:{upstream}", f"127.0.0.1:{free_port()}")
    findings = doctor(load_config(project / "guard.toml"))
    assert not [f for f in findings if f.level == "warning"]
    assert any(f.level == "unverifiable" and "không kiểm được: đích" in f.message for f in findings)
    result = runner.invoke(app, ["plugin", "doctor", "--config", str(project / "guard.toml")])
    assert result.exit_code == 0 and "không chứng minh" in result.output


def test_doctor_warns_for_a_gate_that_does_not_read_call_source(project):
    gate = project / "gates" / "get_status@1.0.0.yaml"
    text = gate.read_text(encoding="utf-8")
    start = text.index("\nevaluate:\n") + 1
    gate.write_text(
        text[:start]
        + "evaluate:\n  operator_approved:\n    type: bool\n    instructions: 'x'\n\n"
        + "allow_when:\n  operator_approved: true\n\non_block:\n  action: deny\n\n"
        + "budget:\n  p95_latency_ms: 150\n  fail: closed\n",
        encoding="utf-8",
    )
    warned = [
        f.message for f in doctor(load_config(project / "guard.toml")) if "call_source" in f.message
    ]
    assert len(warned) == 1 and "`get_status`" in warned[0]


# --- trace and the three commands -----------------------------------------------------------------------------------


def test_the_proxy_trace_validates_and_replays(project, log):
    open_gate(project, "get_status")

    async def script(port, guard):
        await request(port, "POST", "/cm/Power")  # BLOCK
        await request(port, "GET", "/status")  # ALLOW

    through(project, script)
    trace = json.loads((project / "trace.json").read_text(encoding="utf-8"))
    validate_trace(trace)  # written on the way out
    assert trace["metadata"]["agent_version"].startswith("guard:plug@")
    assert trace["metadata"]["proxy"]["kind"] == "http"
    before = calls(log)
    result = asyncio.run(TracePlayer(trace, guard=project / "guard.toml").replay())
    assert result.verdicts == result.recorded_verdicts == ["BLOCK", "ALLOW"]
    assert result.divergences == []
    assert calls(log) == before, "a replay never contacts the upstream"


def test_three_commands_put_an_http_api_behind_the_proxy(tmp_path, upstream, log):
    directory = tmp_path / "e2e"
    init_run = subprocess.run(
        [sys.executable, "-m", "neuroedge", "guard", "init", "--http", f"http://127.0.0.1:{upstream}",
         "--route", "GET /status", "--route", "POST /cm/{cmd}", "--dir", str(directory)],
        capture_output=True, text=True, timeout=120, check=False,
    )  # fmt: skip
    assert init_run.returncode == 0, init_run.stderr
    assert "neuroedge proxy http" in init_run.stdout
    open_gate(directory, "get_status")
    port = free_port()
    edit(directory, 'listen = "127.0.0.1:8787"', f'listen = "127.0.0.1:{port}"')
    trace = tmp_path / "trace.json"
    proxy = subprocess.Popen(
        [sys.executable, "-m", "neuroedge", "proxy", "http", "--config", str(directory / "guard.toml"),
         "--trace-out", str(trace)],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
    )  # fmt: skip
    try:
        wait_listening(port)

        async def client():
            allowed = await request(port, "GET", "/status")
            blocked = await request(port, "POST", "/cm/Power")
            missing = await request(port, "GET", "/nope")
            return allowed, blocked, missing

        allowed, blocked, missing = asyncio.run(client())
    finally:
        proxy.send_signal(signal.SIGTERM)
        err = proxy.communicate(timeout=30)[1]
    assert (allowed[0], blocked[0], missing[0]) == (200, 403, 404), err
    assert [c["target"] for c in calls(log)] == ["/status"]
    validate_trace(json.loads(trace.read_text(encoding="utf-8")))
