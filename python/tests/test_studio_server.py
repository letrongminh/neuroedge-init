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
    assert status in (400, 501)  # 501 until slice S1a implements whatif


def test_voice_without_a_microphone_says_so(studio):
    status, _, body = get(studio, "/api/voice")
    assert status == 200 and json.loads(body) == {"ok": True, "enabled": False, "running": False}
