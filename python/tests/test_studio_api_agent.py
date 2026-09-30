"""
`neuroedge studio`, slice S1a (docs/spec/studio.md §4): /api/agent, /api/gates,
/api/gates/<name>, …/whatif and /api/mcp over the real HTTP server.
"""

from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from neuroedge.sim import SimSession
from neuroedge.studio import StudioServer
from neuroedge.templates import TEMPLATES

ROOT = Path(__file__).resolve().parents[2]
AGENTS = ROOT / "fixtures" / "agents"
VILLA = AGENTS / "villa-concierge" / "agent.toml"
HOME = AGENTS / "home-voice" / "agent.toml"
ENDPOINTS = ("/api/agent", "/api/gates", "/api/gates/unlock_door", "/api/mcp")
SECRET = "sk-test-do-not-leak-0123456789"


def serve(agent: Path):
    session = SimSession.load(agent)
    return StudioServer(session, agent_path=agent).start(), session


@pytest.fixture
def villa():
    server, session = serve(VILLA)
    yield server
    server.stop()
    session.close()


@pytest.fixture
def home():
    server, session = serve(HOME)
    yield server
    server.stop()
    session.close()


def call(server, path, body=None):
    url = server.url.rstrip("/") + path
    request = urllib.request.Request(url, data=None if body is None else json.dumps(body).encode())
    if body is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=10) as reply:
            return reply.status, reply.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def get(server, path):
    status, raw = call(server, path)
    return status, json.loads(raw)


def whatif(server, name, facts):
    status, raw = call(server, f"/api/gates/{name}/whatif", {"facts": facts})
    return status, json.loads(raw)


def test_agent_of_villa_concierge(villa):
    status, agent = get(villa, "/api/agent")
    assert status == 200 and agent["ok"] is True
    assert agent["label"] == "villa-concierge@0.1.0"
    assert agent["root"] == str(VILLA.parent.resolve())
    assert agent["requires"]["digital.out"] == {"pins": ["door_lock"]}
    assert agent["targets"] == ["sim", "linux", "esp32s3"]
    assert agent["board"]["id"] == "sim-default"
    assert "digital_out" in agent["board"]["capabilities"]
    assert agent["providers"] == []
    assert agent["templates"] == list(TEMPLATES)


def test_agent_of_home_voice(home):
    status, agent = get(home, "/api/agent")
    assert status == 200 and agent["label"] == "home-voice@0.1.0"
    assert set(agent["requires"]) == {"audio.out", "digital.out", "sensor.read"}
    assert agent["providers"] == []


def test_a_provider_reports_the_variable_name_and_whether_it_is_set(copy_agent, monkeypatch):
    toml = copy_agent(
        "home-voice",
        '\n[system_two]\nprovider = "litellm"\nmodel = "anthropic/claude-sonnet-5"\n'
        'api_key_env = "STUDIO_TEST_KEY"\n'
        '\n[tts]\nprovider = "openai"\nmodel = "tts-1"\nvoice = "alloy"\napi_key_env = "STUDIO_TEST_KEY"\n',
    )
    monkeypatch.delenv("STUDIO_TEST_KEY", raising=False)
    server, session = serve(toml)
    try:
        _, absent = get(server, "/api/agent")
        monkeypatch.setenv("STUDIO_TEST_KEY", SECRET)
        _, present = get(server, "/api/agent")
        roles = {row["role"]: row for row in present["providers"]}
        assert set(roles) == {"tts", "system_two"}
        assert all(row["key_env"] == "STUDIO_TEST_KEY" for row in roles.values())
        assert all(row["key_present"] is True for row in roles.values())
        assert all(row["key_present"] is False for row in absent["providers"])
        for path in ENDPOINTS + ("/api/gates/light_on",):
            status, raw = call(server, path)
            assert status == 200 and SECRET.encode() not in raw, path
    finally:
        server.stop()
        session.close()


def test_gate_digests_are_the_ones_a_session_writes(villa):
    session = villa.session
    with villa.lock:
        asyncio.run(session.handle("mở cửa phòng 101"))
    begun = {e["gate"]: e["gate_digest"] for e in session.events.of_type("gate_evaluation_begin")}
    assert begun
    status, listing = get(villa, "/api/gates")
    assert status == 200 and listing["lint"] == {"resolved": 1, "total": 1}
    [row] = listing["gates"]
    assert row["name"] == "unlock_door" and row["status"] == "OK"
    assert row["version"] == "1.2.0" and row["levels"] == 2 and row["fail"] == "closed"
    assert row["ref"] == "neuroedge://gates/unlock_door@1.2.0"
    assert begun[f"unlock_door@{row['version']}"] == row["digest"]


def test_a_gate_that_fails_to_resolve_is_a_row_not_a_crash(copy_agent):
    toml = copy_agent("home-voice")
    agent = toml.parent
    server, session = serve(toml)
    try:
        (agent / "gates" / "light_off@1.0.0.yaml").write_text("not: [a gate", encoding="utf-8")
        status, listing = get(server, "/api/gates")
        assert status == 200 and listing["lint"] == {"resolved": 1, "total": 2}
        rows = {row["name"]: row for row in listing["gates"]}
        assert rows["light_on"]["status"] == "OK"
        assert rows["light_off"]["status"] == "FAIL" and rows["light_off"]["digest"] is None
        assert rows["light_off"]["error"]["why"]
    finally:
        server.stop()
        session.close()


def test_one_gate_with_its_chain_and_explanation(villa):
    status, gate = get(villa, "/api/gates/unlock_door")
    assert status == 200 and gate["ok"] is True
    assert gate["name"] == "unlock_door" and gate["version"] == "1.2.0"
    assert gate["chain"] == ["base-access@1.0.0", "unlock_door@1.2.0"]
    assert set(gate["evaluate"]) == {"guest_authenticated", "risk_level", "room_matches"}
    assert gate["evaluate"]["risk_level"]["type"] == "level"
    assert gate["on_block"]["action"] == "escalate"
    assert gate["budget"]["fail"] == "closed"
    clauses = {c["criterion"]: c for c in gate["explanation"]["clauses"]}
    assert clauses["risk_level"]["status"] == "tightened"
    assert clauses["room_matches"]["status"] == "new"
    by_name = {c["name"]: c for c in gate["explanation"]["criteria"]}
    assert by_name["guest_authenticated"]["inherited"] is True


def test_a_gate_is_found_by_name_and_version(villa):
    status, gate = get(villa, "/api/gates/unlock_door@1.2.0")
    assert status == 200 and gate["ok"] is True and gate["name"] == "unlock_door"


@pytest.mark.parametrize("name", ["nope", "unlock_door@9.9.9", "base-access"])
def test_an_unknown_gate_is_a_business_error(villa, name):
    status, answer = get(villa, f"/api/gates/{name}")
    assert status == 200 and answer["ok"] is False and answer["error"]["why"]
    status, answer = whatif(villa, name, {})
    assert status in (200, 404) and answer["ok"] is False


def test_whatif_agrees_with_the_engine(villa):
    _, blocked = whatif(
        villa,
        "unlock_door",
        {"guest_authenticated": True, "risk_level": "low", "room_matches": False},
    )
    assert blocked["ok"] is True and blocked["verdict"] == "BLOCK"
    assert blocked["failed_criterion"] == "room_matches"
    assert blocked["reason"] == "condition_not_met" and blocked["action"] == "escalate"

    _, allowed = whatif(
        villa,
        "unlock_door",
        {"guest_authenticated": True, "risk_level": "low", "room_matches": True},
    )
    assert allowed["verdict"] == "ALLOW" and "reason" not in allowed
    assert allowed["evaluations"]["room_matches"] is True

    _, missing = whatif(villa, "unlock_door", {"guest_authenticated": True, "room_matches": True})
    assert missing["verdict"] == "BLOCK" and missing["reason"] == "criterion_unavailable"
    assert missing["failed_criterion"] == "risk_level"

    _, tighter = whatif(
        villa,
        "unlock_door",
        {"guest_authenticated": True, "risk_level": "medium", "room_matches": True},
    )
    assert tighter["verdict"] == "BLOCK" and tighter["failed_criterion"] == "risk_level"


def test_whatif_with_a_value_of_the_wrong_type_blocks(villa):
    _, answer = whatif(
        villa,
        "unlock_door",
        {"guest_authenticated": "yes", "risk_level": "low", "room_matches": True},
    )
    assert answer["verdict"] == "BLOCK" and answer["reason"] == "criterion_unavailable"
    assert answer["failed_criterion"] == "guest_authenticated"


def test_whatif_does_not_touch_the_session(villa):
    session = villa.session
    with villa.lock:
        asyncio.run(session.handle("mở cửa phòng 101"))
    before_events = json.dumps(session.events.events, default=str)
    before_pins = {name: repr(pin) for name, pin in session.hal.pins.items()}
    for facts in (
        {"guest_authenticated": True, "risk_level": "low", "room_matches": True},
        {"guest_authenticated": True, "risk_level": "low", "room_matches": False},
        {},
    ):
        whatif(villa, "unlock_door", facts)
    get(villa, "/api/gates")
    get(villa, "/api/gates/unlock_door")
    assert json.dumps(session.events.events, default=str) == before_events
    assert {name: repr(pin) for name, pin in session.hal.pins.items()} == before_pins


def test_whatif_with_an_unknown_criterion_is_400(villa):
    status, answer = whatif(villa, "unlock_door", {"guest_authenticted": True})
    assert (
        status == 400 and answer["ok"] is False and "guest_authenticted" in answer["error"]["why"]
    )


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"facts": [1]},
        {"facts": {"room_matches": [True]}},
        {"facts": {"room_matches": {"x": 1}}},
    ],
)
def test_whatif_with_a_malformed_body_is_400(villa, body):
    status, answer = whatif_raw(villa, body)
    assert status == 400 and answer["ok"] is False


def whatif_raw(server, body):
    status, raw = call(server, "/api/gates/unlock_door/whatif", body)
    return status, json.loads(raw)


def test_whatif_defaults_call_source_to_the_local_grammar(home):
    _, answer = whatif(home, "light_off", {"room_empty": True})
    assert answer["verdict"] == "ALLOW" and answer["evaluations"]["call_source"] == "local_grammar"
    _, forced = whatif(home, "light_off", {"room_empty": True, "call_source": "test"})
    assert forced["verdict"] == "BLOCK" and forced["failed_criterion"] == "call_source"
    _, occupied = whatif(home, "light_off", {"room_empty": False})
    assert occupied["failed_criterion"] == "room_empty" and occupied["action"] == "ask"


def test_mcp_tools_are_the_agents_actions(villa, home):
    for server, agent in ((villa, VILLA), (home, HOME)):
        status, mcp = get(server, "/api/mcp")
        assert status == 200 and mcp["ok"] is True
        assert [t["name"] for t in mcp["tools"]] == list(server.session.tools.specs)
        assert all(t["input_schema"]["type"] == "object" and t["description"] for t in mcp["tools"])
        config = json.loads(mcp["desktop_config"])
        [entry] = config["mcpServers"].values()
        assert entry["args"][-3:] == ["--ui", "--port", "8765"]
        assert str(agent.resolve()) in entry["args"]


def test_mcp_lists_the_external_servers(home):
    _, mcp = get(home, "/api/mcp")
    assert mcp["servers"] == [{"name": "news", "tools": ["headlines"]}]


def test_mcp_without_the_sdk_still_lists_the_tools(villa, monkeypatch):
    import neuroedge.mcp_desktop as desktop
    from neuroedge.errors import NeuroEdgeError

    def no_sdk(*args, **kwargs):
        raise NeuroEdgeError(
            where="mcp", why="the MCP SDK is not installed", how="pip install 'neuroedge[mcp]'"
        )

    monkeypatch.setattr(desktop, "desktop_entry", no_sdk)
    status, mcp = get(villa, "/api/mcp")
    assert status == 200 and mcp["ok"] is True
    assert [t["name"] for t in mcp["tools"]] == list(villa.session.tools.specs)
    assert mcp["desktop_config"] is None
    assert "neuroedge[mcp]" in mcp["desktop_config_error"]["how"]


def test_mcp_writes_no_file(villa, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    get(villa, "/api/mcp")
    assert list(tmp_path.iterdir()) == []


def test_a_path_that_is_not_a_gate_name_is_404(villa):
    assert call(villa, "/api/gates/..%2Fagent.toml")[0] == 404
