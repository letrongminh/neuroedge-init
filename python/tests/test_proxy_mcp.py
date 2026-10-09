"""
TSK-I2c-14 (FR-EXT-06) — `neuroedge guard init --mcp` and `neuroedge proxy mcp`: an MCP server that
already exists, put behind NeuroEdge.

The upstream is `fixtures/mcp_upstream/server.py`, a real stdio MCP server that appends every call
it receives to `UPSTREAM_LOG`: "the upstream was not asked" is a fact the tests read from that
file, not something they assume. The front client is a real MCP `Client` too.
"""

from __future__ import annotations

import asyncio
import json
import socket
import subprocess
import sys
from pathlib import Path

import pytest
from mcp import Client, StdioServerParameters
from typer.testing import CliRunner

from neuroedge.cli.main import app
from neuroedge.engine import resolve_gate_file
from neuroedge.errors import AgentManifestError, NeuroEdgeError
from neuroedge.guard import Guard, load_config
from neuroedge.proxy_mcp import (
    build_front,
    doctor,
    init,
    parse_upstream,
    prepare,
)
from neuroedge.sdk import ToolRequest
from neuroedge.testing import TracePlayer
from neuroedge.trace import validate_trace

runner = CliRunner()
ROOT = Path(__file__).resolve().parents[2]
# a key-shaped prefix built at run time: a literal one in the history is what secret scanners flag
KEY = "sk" + "-"
UPSTREAM = ROOT / "fixtures" / "mcp_upstream" / "server.py"


def run(coroutine):
    return asyncio.run(coroutine)


@pytest.fixture
def log(tmp_path, monkeypatch):
    path = tmp_path / "upstream.log"
    monkeypatch.setenv("UPSTREAM_LOG", str(path))
    return path


def calls(log: Path) -> list[dict]:
    return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []


@pytest.fixture
def project(tmp_path, log):
    """`guard init --mcp` against the fixture upstream, in a fresh directory."""
    directory = tmp_path / "proxy"
    plan = run(
        init(f'"{sys.executable}" "{UPSTREAM}"', directory, "home", env_from=["UPSTREAM_LOG"])
    )
    assert plan.exposed
    return directory


def open_gate(project: Path, tool: str) -> None:
    """What the operator does on purpose: drop the criterion nobody sets."""
    path = project / "gates" / f"{tool}@1.0.0.yaml"
    lines = path.read_text(encoding="utf-8").splitlines()
    drop = False
    kept = []
    for line in lines:
        if line.startswith("  operator_approved:"):
            drop = True
            continue
        if drop and line.startswith("    "):
            continue
        drop = False
        if line.startswith("allow_when:") or not line.strip().startswith("operator_approved"):
            kept.append(line)
    path.write_text("\n".join(kept) + "\n", encoding="utf-8")


async def _through(project: Path, script, **kwargs):
    """`script(client, guard)` against a proxy front served in memory over a real upstream."""
    guard, stack = await prepare(project / "guard.toml", **kwargs)
    try:
        async with Client(build_front(guard)) as client:
            return await script(client, guard)
    finally:
        guard.close()
        await stack.aclose()


def through(project, script):
    return run(_through(project, script))


def structured(result):
    return dict(result.structured_content or json.loads(result.content[0].text))


# --- guard init ---------------------------------------------------------------------------------


def test_guard_init_writes_a_guard_and_blocking_gates_that_lint_and_load(project):
    assert (project / "guard.toml").is_file()
    gates = sorted(p.name for p in (project / "gates").iterdir())
    assert gates == ["crash@1.0.0.yaml", "get_state@1.0.0.yaml", "turn_on@1.0.0.yaml"]
    for gate in (project / "gates").iterdir():
        resolve_gate_file(gate)  # resolves, not merely schema-valid
    result = runner.invoke(app, ["gate", "lint", str(project / "gates")])
    assert result.exit_code == 0, result.output
    guard = Guard.load(project / "guard.toml")  # as written, no edits
    try:
        assert {t.name for t in guard.config.tools} == {"crash", "get_state", "turn_on"}
    finally:
        guard.close()
    config = load_config(project / "guard.toml")
    up = parse_upstream(config)
    assert up.command[0] == sys.executable or up.command[0].endswith("python")
    assert up.names == {"get_state": "get-state"}  # the hyphen is mapped, not lost
    assert up.env_from == ("UPSTREAM_LOG",)
    parameters = {t.name: t.parameters for t in config.tools}
    assert parameters["turn_on"]["brightness"] == {"type": "integer", "default": 100}
    assert parameters["turn_on"]["note"] == {"type": "string", "required": False}
    assert "attributes" not in parameters["turn_on"], "an optional object is dropped, with a note"


def test_guard_init_never_overwrites_a_file(tmp_path, log):
    directory = tmp_path / "again"
    (directory / "gates").mkdir(parents=True)
    mine = directory / "gates" / "turn_on@1.0.0.yaml"
    mine.write_text("# mine\n", encoding="utf-8")
    with pytest.raises(NeuroEdgeError) as refused:
        run(init(f'"{sys.executable}" "{UPSTREAM}"', directory, env_from=["UPSTREAM_LOG"]))
    assert "already exists" in refused.value.why and refused.value.how and refused.value.where
    assert mine.read_text(encoding="utf-8") == "# mine\n"
    assert (
        not (directory / "guard.toml").exists() and len(list((directory / "gates").iterdir())) == 1
    ), "all-or-nothing: nothing was written next to the file that stood in the way"


def test_a_tool_with_a_required_object_parameter_is_not_exposed(project):
    text = (project / "guard.toml").read_text(encoding="utf-8")
    assert "# Not exposed" in text and "call_service" in text and "[tools.call_service]" not in text
    assert not (project / "gates" / "call_service@1.0.0.yaml").exists()

    async def script(client, guard):
        return [t.name for t in (await client.list_tools()).tools]

    assert sorted(through(project, script)) == ["crash", "get_state", "turn_on"]
    result = runner.invoke(
        app,
        [
            "guard",
            "init",
            "--mcp",
            f'"{sys.executable}" "{UPSTREAM}"',
            "--dir",
            str(project.parent / "second"),
            "--env-from",
            "UPSTREAM_LOG",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "NOT exposed: call_service" in result.output
    assert "turn_on: optional parameter(s) not exposed: attributes" in result.output


# --- a generated gate blocks; the proxy forwards only after ALLOW --------------------------------------


def test_a_generated_gate_blocks_until_the_operator_opens_it(project, log):
    async def blocked(client, guard):
        return await client.call_tool("get_state", {"entity_id": "light.hall"})

    result = through(project, blocked)
    verdict = structured(result)
    assert (verdict["status"], verdict["reason"]) == ("BLOCK", "criterion_unavailable")
    assert verdict["failed_criterion"] == "operator_approved"
    assert result.is_error is False, "a BLOCK is the gate working, not an error"
    assert calls(log) == []

    open_gate(project, "get_state")

    async def allowed(client, guard):
        return await client.call_tool("get_state", {"entity_id": "light.hall"})

    result = through(project, allowed)
    assert result.content[0].text == "light.hall: on" and result.is_error is False
    assert calls(log) == [{"tool": "get-state", "arguments": {"entity_id": "light.hall"}}]


def test_the_proxy_forwards_only_after_allow_and_never_on_block(project, log):
    open_gate(project, "get_state")

    async def script(client, guard):
        blocked = await client.call_tool("turn_on", {"entity_id": "light.hall"})
        rejected = await client.call_tool("get_state", {"entity_id": "x", "surprise": 1})
        unknown = await client.call_tool("call_service", {"domain": "a", "data": {}})
        allowed = await client.call_tool("get_state", {"entity_id": "light.hall"})
        return blocked, rejected, unknown, allowed

    blocked, rejected, unknown, allowed = through(project, script)
    assert structured(blocked)["status"] == "BLOCK"
    assert structured(rejected)["status"] == "REJECTED" and rejected.is_error
    assert structured(unknown)["status"] == "REJECTED"
    assert allowed.content[0].text == "light.hall: on"
    assert calls(log) == [{"tool": "get-state", "arguments": {"entity_id": "light.hall"}}], (
        "the BLOCK, the schema rejection and the unexposed tool left the upstream untouched"
    )


def test_the_proxy_keeps_the_front_source_mcp(project):
    open_gate(project, "get_state")

    async def script(client, guard):
        await client.call_tool("get_state", {"entity_id": "light.hall"})
        return guard.events

    events = through(project, script)
    assert [e["source"] for e in events.of_type("tool_call")] == ["mcp"]
    facts = events.of_type("gate_facts")[-1]
    assert facts["call_source"]["value"] == "mcp"


def test_a_bridge_cannot_obtain_the_front_source(project, log):
    import neuroedge.guard as module
    from neuroedge.guard import Dispatcher

    open_gate(project, "get_state")

    async def script(client, guard):
        sneaky = guard.dispatcher("mcp")  # asks for the id `mcp`: it is `bridge:mcp`, not `mcp`
        outcome = await sneaky.dispatch(ToolRequest("get_state", {"entity_id": "light.hall"}))
        return outcome, guard.events

    outcome, events = through(project, script)
    assert [e["source"] for e in events.of_type("tool_call")] == ["bridge:mcp"]
    assert (outcome.status, outcome.content["reason"]) == ("BLOCK", "criterion_unavailable")
    assert calls(log) == []
    assert not hasattr(Dispatcher, "_dispatch_front") and "_dispatch_front" not in dir(Dispatcher)
    assert "Guard" in module.__all__ and not any("front" in n for n in module.__all__)


def test_an_upstream_error_after_allow_is_an_error_result_not_a_retry(project, log):
    open_gate(project, "crash")

    async def script(client, guard):
        first = await client.call_tool("crash", {})
        second = await client.call_tool("crash", {})
        return first, second

    first, second = through(project, script)
    for result in (first, second):
        told = structured(result)
        assert result.is_error is True and told["status"] == "ALLOW"
        assert "not retried" in told["problems"][0]
    assert calls(log) == [{"tool": "crash", "arguments": {}}], (
        "the first call reached the upstream once; the dead upstream was never asked again"
    )


# --- refusing to start ----------------------------------------------------------------------------------


def test_a_missing_upstream_tool_refuses_start(project):
    text = (project / "guard.toml").read_text(encoding="utf-8")
    ghost = 'gate = "gates/get_state@1.0.0.yaml"\n'
    (project / "guard.toml").write_text(text + f"\n[tools.ghost]\n{ghost}", encoding="utf-8")
    with pytest.raises(NeuroEdgeError) as refused:
        run(prepare(project / "guard.toml"))
    assert "ghost" in refused.value.why and "no tool" in refused.value.why and refused.value.how
    result = runner.invoke(app, ["proxy", "mcp", "--config", str(project / "guard.toml")])
    assert result.exit_code == 1 and "ghost" in result.output, "exit 1, serving nothing"
    # a parameter that does not fit is refused the same way
    (project / "guard.toml").write_text(
        text.replace('type = "integer"', 'type = "string"'), encoding="utf-8"
    )
    with pytest.raises(NeuroEdgeError, match="brightness"):
        run(prepare(project / "guard.toml"))


def test_an_unreachable_upstream_refuses_start(project, tmp_path):
    text = (project / "guard.toml").read_text(encoding="utf-8")
    broken = text.replace(
        f'command = ["{sys.executable}", "{UPSTREAM}"]', 'command = ["no-such-program-anywhere"]'
    )
    assert broken != text
    (project / "guard.toml").write_text(broken, encoding="utf-8")
    with pytest.raises(NeuroEdgeError) as refused:
        run(prepare(project / "guard.toml"))
    assert "cannot connect" in refused.value.why and refused.value.how
    with socket.socket() as spare:
        spare.bind(("127.0.0.1", 0))
        closed = spare.getsockname()[1]
    http = broken.replace(
        'command = ["no-such-program-anywhere"]', f'url = "http://127.0.0.1:{closed}/mcp"'
    )
    http = http.replace('env_from = ["UPSTREAM_LOG"]\n', "")
    (project / "guard.toml").write_text(http, encoding="utf-8")
    with pytest.raises(NeuroEdgeError, match="cannot connect"):
        run(prepare(project / "guard.toml"))
    # an environment variable the config names but the shell lacks refuses too, before connecting
    named = text.replace("UPSTREAM_LOG", "NEUROEDGE_SURELY_UNSET")
    (project / "guard.toml").write_text(named, encoding="utf-8")
    with pytest.raises(NeuroEdgeError, match="NEUROEDGE_SURELY_UNSET"):
        run(prepare(project / "guard.toml"))


@pytest.mark.parametrize(
    ("edit", "why"),
    [
        (
            f'[proxy.mcp]\ncommand = ["x", "--key", "{KEY}abcdef0123456789abcd"]',
            "looks like a secret",
        ),
        (
            f'[proxy.mcp]\nurl = "https://h/mcp"\nheaders_env = {{ Authorization = "Bearer {KEY}abcdef0123456789" }}',
            "NAME of an environment",
        ),
        ('[proxy.mcp]\nurl = "https://h/mcp"\napi_key = "abc"', "api_key"),
        ('[proxy.mcp]\nurl = "https://user:pw@h/mcp"', "credentials"),
        ('[proxy.mcp]\nurl = "https://h/mcp?token=abc"', "secret-named"),
        ('[proxy.mcp]\nurl = "http://h.example/mcp"', "clear"),
        ('[proxy.mcp]\ncommand = ["x"]\nurl = "https://h/mcp"', "exactly one"),
        ('[proxy.mcp]\ncommand = ["x"]\nenv_from = ["TOKEN=abc"]', "NAMES"),
        ('[proxy.mcp]\ncommand = ["x"]\nsurprise = 1', "surprise"),
        ('[proxy.mcp]\ncommand = ["x"]\n[proxy.mcp.names]\nnot_a_tool = "x"', "not tools"),
        ('[proxy.http]\nupstream = "http://127.0.0.1:1"', "use `proxy http`"),
    ],
)
def test_a_literal_secret_in_proxy_config_is_refused(project, edit, why):
    text = (project / "guard.toml").read_text(encoding="utf-8")
    start, end = text.index("[proxy.mcp]"), text.index("# Not exposed")
    (project / "guard.toml").write_text(text[:start] + edit + "\n\n" + text[end:], encoding="utf-8")
    with pytest.raises(AgentManifestError) as refused:
        parse_upstream(load_config(project / "guard.toml"))
    error = refused.value
    assert error.code == "NE3002" and error.where and error.how
    assert why in error.where + error.why + error.how
    assert KEY + "abcdef" not in str(error.as_dict()), "a pasted key is never echoed"


# --- doctor ---------------------------------------------------------------------------------------------


def _url_project(project: Path, port: int) -> Path:
    text = (project / "guard.toml").read_text(encoding="utf-8")
    text = text.replace(
        f'command = ["{sys.executable}", "{UPSTREAM}"]', f'url = "http://127.0.0.1:{port}/mcp"'
    ).replace('env_from = ["UPSTREAM_LOG"]\n', "")
    (project / "guard.toml").write_text(text, encoding="utf-8")
    return project / "guard.toml"


def test_doctor_warns_when_the_upstream_is_reachable_directly(project):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        config = _url_project(project, listener.getsockname()[1])
        findings = doctor(config)
        warnings = [f for f in findings if f.level == "warning" and "còn tới được" in f.message]
        assert warnings and "127.0.0.1" in warnings[0].message
        result = runner.invoke(app, ["plugin", "doctor", "--config", str(config), "--json"])
        assert result.exit_code == 1, "a warning is a non-zero exit"
        report = json.loads(result.output)
        assert report["warnings"] >= 1
    # nothing listens now: it still does not say OK
    unreachable = doctor(config)
    assert not [f for f in unreachable if "còn tới được" in f.message]
    assert any(f.level == "unverifiable" and "không kiểm được" in f.message for f in unreachable)


def test_doctor_says_what_it_cannot_check(project, tmp_path):
    findings = doctor(project / "guard.toml", desktop_config=tmp_path / "missing.json")
    text = "\n".join(f.message for f in findings)
    assert "không kiểm được: plugin (TSK-I2c-11)" in text
    assert "không kiểm được: không đọc được cấu hình Claude Desktop" in text
    assert "không kiểm được: ứng dụng khác" in text
    assert not any(f.message.strip().upper() == "OK" for f in findings)
    result = runner.invoke(app, ["plugin", "doctor", "--config", str(project / "guard.toml")])
    assert "không kiểm được: plugin (TSK-I2c-11)" in result.output
    assert "không chứng minh" in result.output, "the closing line says it proves nothing"


def test_doctor_finds_another_desktop_entry_that_launches_the_upstream(project, tmp_path):
    desktop = tmp_path / "claude_desktop_config.json"
    desktop.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "direct": {"command": "/usr/bin/python3", "args": [str(UPSTREAM)]},
                    "unrelated": {"command": "npx", "args": ["other"]},
                    "front": {
                        "command": sys.executable,
                        "args": ["-m", "neuroedge", "proxy", "mcp"],
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    findings = doctor(project / "guard.toml", desktop_config=desktop)
    warned = [f.message for f in findings if f.level == "warning"]
    assert len(warned) == 1 and "`direct`" in warned[0]
    only_proxy = tmp_path / "only.json"
    only_proxy.write_text(
        json.dumps({"mcpServers": {"front": {"command": "neuroedge", "args": ["proxy", "mcp"]}}}),
        encoding="utf-8",
    )
    findings = doctor(project / "guard.toml", desktop_config=only_proxy)
    assert not [f for f in findings if f.level == "warning"]
    assert any("không kiểm được: ứng dụng khác" in f.message for f in findings)


def test_doctor_warns_for_a_gate_that_does_not_read_call_source(project):
    gate = project / "gates" / "get_state@1.0.0.yaml"
    text = gate.read_text(encoding="utf-8")
    start = text.index("\nevaluate:\n") + 1
    gate.write_text(
        text[:start]
        + "evaluate:\n  operator_approved:\n    type: bool\n    instructions: 'x'\n\n"
        + "allow_when:\n  operator_approved: true\n\non_block:\n  action: deny\n\n"
        + "budget:\n  p95_latency_ms: 150\n  fail: closed\n",
        encoding="utf-8",
    )
    warned = [f.message for f in doctor(project / "guard.toml") if f.level == "warning"]
    assert any("`get_state`" in m and "call_source" in m for m in warned)
    assert not any("`turn_on`" in m and "call_source" in m for m in warned)


# --- end to end -----------------------------------------------------------------------------------------


def test_three_commands_put_a_server_behind_the_proxy(tmp_path, log):
    """pip is the environment; then `guard init`, a deliberate gate edit, `proxy mcp`, a real client."""
    directory = tmp_path / "ha"
    env_up = f'"{sys.executable}" "{UPSTREAM}"'
    init_run = subprocess.run(
        [sys.executable, "-m", "neuroedge", "guard", "init", "--mcp", env_up,
         "--dir", str(directory), "--env-from", "UPSTREAM_LOG"],
        capture_output=True, text=True, timeout=120, check=False,
    )  # fmt: skip
    assert init_run.returncode == 0, init_run.stderr
    assert "neuroedge proxy mcp" in init_run.stdout, "it prints the next command"
    open_gate(directory, "get_state")
    trace = tmp_path / "proxy-trace.json"

    async def front():
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "neuroedge", "proxy", "mcp", "--config", str(directory / "guard.toml"),
                  "--trace-out", str(trace)],
            env={"UPSTREAM_LOG": str(log)},
        )  # fmt: skip
        async with Client(params) as client:
            listed = {t.name: t for t in (await client.list_tools()).tools}
            allowed = await client.call_tool("get_state", {"entity_id": "light.hall"})
            blocked = await client.call_tool("turn_on", {"entity_id": "light.hall"})
            return listed, allowed, blocked

    listed, allowed, blocked = run(front())
    assert sorted(listed) == ["crash", "get_state", "turn_on"]
    assert listed["get_state"].description.startswith("The state of one entity.")
    assert allowed.content[0].text == "light.hall: on"
    assert structured(blocked)["status"] == "BLOCK"
    assert calls(log) == [{"tool": "get-state", "arguments": {"entity_id": "light.hall"}}]
    validate_trace(json.loads(trace.read_text(encoding="utf-8")))


def test_the_proxy_trace_validates_and_replays(project, log):
    open_gate(project, "get_state")

    async def script(client, guard):
        await client.call_tool("turn_on", {"entity_id": "light.hall"})
        await client.call_tool("get_state", {"entity_id": "light.hall"})
        return guard.trace()

    trace = through(project, script)
    validate_trace(trace)
    assert trace["metadata"]["agent_version"].startswith("guard:home@")
    assert trace["metadata"]["proxy"]["kind"] == "mcp"
    assert "UPSTREAM_LOG" not in json.dumps(trace["metadata"]), "no argument of the command"
    before = calls(log)
    result = run(TracePlayer(trace, guard=project / "guard.toml").replay())
    assert result.verdicts == result.recorded_verdicts == ["BLOCK", "ALLOW"]
    assert result.divergences == []
    assert calls(log) == before, "a replay never contacts the upstream"


def test_the_proxy_also_fronts_a_streamable_http_upstream(tmp_path, log):
    with socket.socket() as spare:
        spare.bind(("127.0.0.1", 0))
        port = spare.getsockname()[1]
    server = subprocess.Popen(
        [sys.executable, str(UPSTREAM), "--http", str(port)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )  # fmt: skip
    try:
        for _ in range(100):
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
                break
            except OSError:
                import time

                time.sleep(0.1)
        directory = tmp_path / "http"
        plan = run(init(f"http://127.0.0.1:{port}/mcp", directory, "ha"))
        assert "get_state" in plan.exposed
        open_gate(directory, "get_state")

        async def script(client, guard):
            return await client.call_tool("get_state", {"entity_id": "light.hall"})

        assert through(directory, script).content[0].text == "light.hall: on"
        # headers come from the environment only: a missing variable refuses
        text = (directory / "guard.toml").read_text(encoding="utf-8")
        (directory / "guard.toml").write_text(
            text.replace(f'url = "http://127.0.0.1:{port}/mcp"',
                         f'url = "http://127.0.0.1:{port}/mcp"\nheaders_env = {{ Authorization = "NEUROEDGE_SURELY_UNSET" }}'),
            encoding="utf-8",
        )  # fmt: skip
        with pytest.raises(NeuroEdgeError, match="NEUROEDGE_SURELY_UNSET"):
            run(prepare(directory / "guard.toml"))
    finally:
        server.terminate()
        server.wait(timeout=10)


# --- desktop --------------------------------------------------------------------------------------------


def test_the_proxy_registers_in_claude_desktop_like_mcp_serve(project, tmp_path):
    target = tmp_path / "claude_desktop_config.json"
    target.write_text(
        json.dumps({"mcpServers": {"other": {"command": "x"}}, "keep": 1}), encoding="utf-8"
    )
    args = ["proxy", "mcp", "--config", str(project / "guard.toml"), "--desktop-config"]
    printed = runner.invoke(app, args)
    assert printed.exit_code == 0, printed.output
    entry = json.loads(printed.stdout)["mcpServers"]["home"]
    assert entry["args"][:5] == ["-m", "neuroedge", "proxy", "mcp", "--config"]
    assert Path(entry["args"][5]).is_absolute() and Path(entry["command"]).is_absolute()
    assert not target.read_text(encoding="utf-8").count("home"), "printing writes nothing"
    wrote = runner.invoke(app, [*args, "--write", "--config-path", str(target)])
    assert wrote.exit_code == 0, wrote.output
    config = json.loads(target.read_text(encoding="utf-8"))
    assert set(config["mcpServers"]) == {"other", "home"} and config["keep"] == 1
    assert list(tmp_path.glob("claude_desktop_config.json.bak-*")), "the old file is kept"
    again = runner.invoke(app, [*args, "--write", "--config-path", str(target)])
    assert "already up to date" in again.output
    lonely = runner.invoke(
        app, ["proxy", "mcp", "--config", str(project / "guard.toml"), "--write"]
    )
    assert lonely.exit_code == 2
