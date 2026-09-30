"""
`neuroedge studio` (TSK-I1-04, Q-51): the server skeleton of docs/spec/studio.md —
127.0.0.1 only, the sim page's session routes kept, the studio page at `/` with no
external asset, same-origin POSTs on /api/*, the error shapes of §2.8.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from neuroedge.sim import SimSession
from neuroedge.studio import StudioServer
from neuroedge.studio.server import ROUTES

ROOT = Path(__file__).resolve().parents[2]
VILLA = ROOT / "fixtures" / "agents" / "villa-concierge" / "agent.toml"


@pytest.fixture
def studio():
    session = SimSession.load(VILLA)
    server = StudioServer(session, agent_path=VILLA).start()
    yield server
    server.stop()
    session.close()


def get(server, path):
    with urllib.request.urlopen(server.url.rstrip("/") + path, timeout=5) as reply:
        return reply.status, reply.headers.get("Content-Type"), reply.read()


def post(server, path, body=b"{}", origin=None):
    request = urllib.request.Request(server.url.rstrip("/") + path, data=body, method="POST")
    request.add_header("Content-Type", "application/json")
    if origin is not None:
        request.add_header("Origin", origin)
    try:
        with urllib.request.urlopen(request, timeout=5) as reply:
            return reply.status, json.loads(reply.read())
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def test_the_studio_listens_on_loopback_only(studio):
    assert studio.url.startswith("http://127.0.0.1:")


def test_the_page_is_the_studio_and_loads_nothing_from_outside(studio):
    status, content_type, body = get(studio, "/")
    page = body.decode("utf-8")
    assert status == 200 and content_type.startswith("text/html")
    assert 'id="ne-boot"' in page and "NeuroEdge Studio" in page
    assert not re.search(r"<(script|link|img)[^>]+(src|href)=", page)
    assert "@import" not in page and "url(" not in page


def test_the_sim_routes_are_kept(studio):
    status, content_type, body = get(studio, "/state")
    assert status == 200 and set(json.loads(body)) == {"events", "now_ms"}


def test_every_api_route_of_the_spec_is_registered():
    spec = (ROOT / "docs" / "spec" / "studio.md").read_text(encoding="utf-8")
    documented = set(re.findall(r"`(GET|POST) (/api/[^ `]+)", spec))
    registered = {(method, pattern.pattern) for method, pattern, _ in ROUTES}
    assert len(documented) == len(registered) == 17
    for method, path in documented:
        probe = re.sub(r"<(lang)>", "vi", path)
        probe = re.sub(r"<[a-z]+>", "x", probe)
        assert any(m == method and p.match(probe) for m, p, _ in ROUTES), (method, path)


def test_an_unknown_api_path_is_404(studio):
    with pytest.raises(urllib.error.HTTPError) as caught:
        get(studio, "/api/nope")
    assert caught.value.code == 404


def test_a_cross_origin_api_post_is_refused(studio):
    status, _ = post(studio, "/api/lint", origin="http://evil.example")
    assert status == 403


def test_a_malformed_body_is_400(studio):
    status, _ = post(studio, "/api/gates/unlock_door/whatif", body=b"[1, 2]")
    assert status == 400


def test_voice_without_a_microphone_says_so(studio):
    status, _, body = get(studio, "/api/voice")
    assert status == 200 and json.loads(body) == {"ok": True, "enabled": False, "running": False}


def raw_request(server, request: bytes) -> bytes:
    import socket

    host, port = server.httpd.server_address[:2]
    with socket.create_connection((host, port), timeout=5) as conn:
        conn.sendall(request)
        conn.shutdown(socket.SHUT_WR)
        return b"".join(iter(lambda: conn.recv(65536), b""))


def test_a_foreign_host_reads_nothing_dns_rebinding(studio):
    # A page on evil.example that rebinds its name to 127.0.0.1 keeps its name in Host.
    for path in ("/", "/state", "/events", "/api/agent", "/api/traces"):
        reply = raw_request(
            studio, f"GET {path} HTTP/1.1\r\nHost: evil.example:80\r\n\r\n".encode()
        )
        assert reply.startswith(b"HTTP/1.0 403") or reply.startswith(b"HTTP/1.1 403"), (
            path,
            reply[:40],
        )


def test_the_sim_page_refuses_a_foreign_host_too():
    from neuroedge.sim.ui import SessionServer

    session = SimSession.load(VILLA)
    server = SessionServer(session).start()
    try:
        reply = raw_request(server, b"GET /state HTTP/1.1\r\nHost: evil.example\r\n\r\n")
        assert b" 403 " in reply.split(b"\r\n", 1)[0]
    finally:
        server.stop()
        session.close()


def test_a_bad_content_length_is_400_and_does_not_hang(studio):
    port = studio.httpd.server_address[1]
    for value in ("abc", "-1"):
        reply = raw_request(
            studio,
            f"POST /api/lint HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nContent-Length: {value}\r\n\r\n".encode(),
        )
        assert b" 400 " in reply.split(b"\r\n", 1)[0], (value, reply[:60])


def test_an_origin_without_a_scheme_is_refused(studio):
    port = studio.httpd.server_address[1]
    status, _ = post(studio, "/api/lint", origin=f"127.0.0.1:{port}")
    assert status == 403


def test_one_subprocess_run_at_a_time_and_secrets_are_redacted(monkeypatch):
    from neuroedge.errors import NeuroEdgeError
    from neuroedge.studio import api_checks

    with api_checks.one_at_a_time("verify"):  # noqa: SIM117 - the nesting is the test
        with pytest.raises(NeuroEdgeError) as busy:
            with api_checks.one_at_a_time("test"):
                pass
    assert "still going" in busy.value.why
    with api_checks.one_at_a_time("test"):  # released after the first run
        pass
    fake = "sk-or-v1-" + "0123456789abcdef"  # made up; built at run time so no scanner sees a key
    monkeypatch.setenv("OPENROUTER_API_KEY", fake)
    assert api_checks.redact(f"key={fake}!") == "key=***!"
