"""
Demo "chat điều khiển đèn và cửa qua NeuroEdge Cloud" (`demo/i2f-chat-den-cua/`).

The brain is NeuroClaw (Q-78, Q-80: a hard fork of PicoClaw with all of PicoClaw's capabilities)
on a VPS; the box at home is `neuroedge mcp serve --http --ui`.
What the door itself guarantees is in `test_mcp_http.py` §4. These show the two other halves:

  * the demo chooses a closed brain: NeuroClaw, like PicoClaw, has a shell, cron commands, hooks,
    buses, skill installs and stdio MCP servers, so the demo's configuration turns every one off and
    leaves no road to the world except the box's MCP tools
    (`test_the_demo_brain_is_configured_closed`);
  * the demo's keys and `cau-noi.py` carry a header-only client (original PicoClaw, or any MCP
    client without client certificates) to
    the box over mTLS, and the session replays (`test_a_header_only_brain_reaches_the_box_...`).

NeuroClaw itself is not run here (Go, an LLM and a Telegram bot): its own CI tests mTLS and its
risk labels (github.com/letrongminh/neuroclaw); the guide's manual checks cover the rest.
"""

from __future__ import annotations

import asyncio
import contextlib
import importlib.util
import json
import subprocess
import threading
from pathlib import Path

import anyio
import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from typer.testing import CliRunner

from neuroedge.cli.main import app
from neuroedge.mcp_http import HttpConfig, prepare
from neuroedge.sim import SimSession
from neuroedge.sim.serve import run_http
from neuroedge.sim.ui import SessionServer

TIMEOUT = 15.0


def _demo(root: Path) -> Path:
    return root / "demo" / "i2f-chat-den-cua"


def _load(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --- the brain -----------------------------------------------------------------------------

# every PicoClaw v0.3.1 tool (`pkg/config/config.go` ToolsConfig) that reaches past the
# workspace and the chat: a shell, a bus, a port, or code fetched from elsewhere
CLOSED = ("exec", "i2c", "spi", "serial", "install_skill", "find_skills")


def test_the_demo_brain_is_configured_closed(root):
    """NeuroClaw opens these by default, as PicoClaw (Q-80): the demo's config must say off."""
    config = json.loads((_demo(root) / "neuroclaw" / "config.json").read_text())
    tools = config["tools"]

    for name in CLOSED:
        assert tools[name]["enabled"] is False, name
    # a cron job may otherwise run a shell command even with `exec` off
    assert tools["cron"]["allow_command"] is False
    # process hooks run commands; USB monitoring watches hardware
    assert config["hooks"]["enabled"] is False
    assert config["devices"]["enabled"] is False
    assert all(not registry["enabled"] for registry in tools["skills"]["registries"].values())

    # files: the workspace and nothing else
    assert config["agents"]["defaults"]["restrict_to_workspace"] is True
    assert tools["allow_read_paths"] == [] and tools["allow_write_paths"] == []

    # MCP: one server, the box behind the loopback bridge; no stdio server (that is a command)
    servers = {n: s for n, s in tools["mcp"]["servers"].items() if s.get("enabled")}
    assert list(servers) == ["neuroedge"]
    assert all("command" not in server for server in tools["mcp"]["servers"].values())
    assert servers["neuroedge"]["type"] == "http"
    # NeuroClaw speaks mTLS itself (Q-78): https, the box's CA, the brain's certificate
    assert servers["neuroedge"]["url"].startswith("https://")
    assert set(servers["neuroedge"]["tls"]) >= {"ca_file", "cert_file", "key_file"}

    # what the goal keeps: chat, LLM, memory, files, cron, heartbeat, web, message, subagents
    assert config["channel_list"]["telegram"]["enabled"] is True
    assert config["heartbeat"]["enabled"] is True and tools["cron"]["enabled"] is True
    for name in ("read_file", "write_file", "web_fetch", "message", "spawn", "subagent"):
        assert tools[name]["enabled"] is True, name
    assert tools["web"]["enabled"] is True


def test_no_secret_is_committed_with_the_brain(root):
    folder = _demo(root) / "neuroclaw"
    text = (folder / "config.json").read_text()
    for marker in ("sk-", "api_key", '"token"'):
        assert marker not in text, marker
    assert "NOI_DUNG_NAO_TOKEN" in text  # the guide pastes the token here on the VPS


# --- the keys and the bridge, end to end --------------------------------------------------


class Bridge:
    """`cau-noi.py` on its own event loop in a thread, as on the VPS."""

    def __init__(self, module, keys: Path, target_port: int) -> None:
        self.ready = threading.Event()
        self.port = 0
        context = module.tls_context(
            str(keys / "ca.pem"), str(keys / "nao.pem"), str(keys / "nao.key")
        )
        self.loop = asyncio.new_event_loop()

        def on_ready(port: int) -> None:
            self.port = port
            self.ready.set()

        async def main() -> None:
            await module.serve(
                "127.0.0.1:0",
                f"127.0.0.1:{target_port}",
                context,
                server_name="localhost",
                on_ready=on_ready,
                log=lambda _line: None,
            )

        self.task = self.loop.create_task(main())
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        assert self.ready.wait(TIMEOUT), "the bridge did not come up"

    def _run(self) -> None:
        asyncio.set_event_loop(self.loop)
        with contextlib.suppress(asyncio.CancelledError):
            self.loop.run_until_complete(self.task)

    def stop(self) -> None:
        self.loop.call_soon_threadsafe(self.task.cancel)
        self.thread.join(TIMEOUT)


def test_a_header_only_brain_reaches_the_box_through_the_bridge_and_the_session_replays(
    root, tmp_path
):
    demo = _demo(root)
    keys = tmp_path / "khoa"
    audience = "https://localhost:8443/mcp"
    _load(demo / "tao-khoa.py").main(["--out", str(keys), "--audience", audience])
    settings = json.loads((keys / "hop.json").read_text())
    token = (keys / "nao.token").read_text().strip()

    agent = root / "fixtures" / "agents" / "chat-den-cua" / "agent.toml"
    session = SimSession.load(agent)
    page = SessionServer(session).start()
    prepared = prepare(
        HttpConfig(
            host="127.0.0.1",
            port=0,
            tls_cert=keys / "hop.pem",
            tls_key=keys / "hop.key",
            client_ca=keys / "ca.pem",
            issuer=settings["issuer"],
            audience=settings["audience"],
            jwks=keys / "jwks.json",
        )
    )
    trace = tmp_path / "vet-ghi.json"
    ready, stop, box = threading.Event(), threading.Event(), {}

    def on_ready(_host: str, port: int) -> None:
        box["port"] = port
        ready.set()

    def target() -> None:
        try:
            run_http(
                session,
                prepared,
                trace_out=trace,
                on_ready=on_ready,
                stop=stop,
                lock=page.lock,
                on_change=page.notify,
                on_close=page.stop,
            )
        except BaseException as error:
            box["error"] = error
            ready.set()

    server = threading.Thread(target=target, daemon=True)
    server.start()
    assert ready.wait(TIMEOUT) and "error" not in box, box.get("error")
    bridge = Bridge(_load(demo / "cau-noi.py"), keys, box["port"])

    async def brain():
        # a client like original PicoClaw's: plain HTTP to the bridge, a token, no certificate
        headers = {"Authorization": f"Bearer {token}"}
        async with (
            httpx2.AsyncClient(headers=headers, timeout=TIMEOUT) as http,
            Client(
                streamable_http_client(f"http://127.0.0.1:{bridge.port}/mcp", http_client=http)
            ) as client,
        ):
            tools = {tool.name for tool in (await client.list_tools()).tools}
            light = await client.call_tool("living_light_on", {})
            door = await client.call_tool("front_door_unlock", {})
            return tools, light, door

    try:
        tools, light, door = anyio.run(brain)
        assert tools == {"living_light_on", "living_light_off", "front_door_unlock"}
        assert light.structured_content["status"] == "ALLOW"
        assert door.structured_content["status"] == "BLOCK"
        question = door.structured_content["confirmation"]
        reply = page.confirm(json.dumps({"id": question["id"], "answer": "yes"}))
        assert reply["ok"] and reply["verdict"] == "ALLOW", reply
    finally:
        bridge.stop()
        stop.set()
        server.join(TIMEOUT)
    assert not server.is_alive()

    pins = [(e["pin"], e["operation"]) for e in session.events.of_type("actuator_command")]
    assert pins == [("porch_light", "on"), ("door_lock", "pulse")]
    # step 6 of the demo: the recorded verdicts are recomputed and agree
    replayed = CliRunner().invoke(app, ["replay", str(trace), "--agent", str(agent)])
    assert replayed.exit_code == 0, replayed.output


def test_the_scripts_parse_and_the_vps_never_gets_the_keys_that_mint_or_serve(root):
    demo = _demo(root)
    for script in ("chay-hop.sh", "chay-nao.sh", "dung-vps.sh"):
        checked = subprocess.run(["bash", "-n", str(demo / script)], capture_output=True)
        assert checked.returncode == 0, (script, checked.stderr)
    # what goes to the VPS: the brain's certificate, key and token, and the CA to check the box
    copied = [line for line in (demo / "dung-vps.sh").read_text().splitlines() if "cp " in line]
    shipped = " ".join(copied)
    for name in ("ca.pem", "nao.pem", "nao.key", "nao.token"):
        assert name in shipped, name
    for name in ("issuer.key", "hop.key", "jwks.json"):
        assert name not in shipped, name
