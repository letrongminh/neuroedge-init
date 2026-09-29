"""
The studio's HTTP server (docs/spec/studio.md). It is the sim page's
`SessionServer` — same lock, same `/events`, `/state`, `/command`, `/confirm`,
same 127.0.0.1-only binding and same-origin POSTs — with a studio page at `/`
and the `/api/*` routes of the spec's §4, each answered by one module.
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
from http import HTTPStatus
from pathlib import Path
from typing import Any

from ..errors import NeuroEdgeError
from ..sim.session import SimSession
from ..sim.ui import MAX_BODY, SessionServer, _Handler, _json
from . import api_agent, api_checks, api_device, voice
from .page import studio_page

# (method, pattern) -> handler(server, match, body) -> (status, payload). A payload
# that is `bytes` goes out as is, with the content type the handler names.
Route = Callable[["StudioServer", re.Match[str], str], tuple[int, Any]]
ROUTES: list[tuple[str, re.Pattern[str], Route]] = []
NAME = r"[A-Za-z0-9_.@-]{1,128}"


def route(method: str, pattern: str) -> Callable[[Route], Route]:
    def register(handler: Route) -> Route:
        ROUTES.append((method, re.compile(f"^{pattern}$"), handler))
        return handler

    return register


def _api(call: Callable[[], Any]) -> tuple[int, Any]:
    """Run one API call: a NeuroEdgeError is the spec's error shape (§2.8), a stub is 501."""
    try:
        return HTTPStatus.OK, call()
    except NotImplementedError:
        return HTTPStatus.NOT_IMPLEMENTED, {"ok": False, "error": {"why": "not implemented yet"}}
    except NeuroEdgeError as error:
        return HTTPStatus.OK, {"ok": False, "error": error.as_dict()}
    except ValueError as error:
        return HTTPStatus.BAD_REQUEST, {"ok": False, "error": {"why": str(error)}}


def _body_json(body: str) -> dict[str, Any]:
    try:
        value = json.loads(body or "{}")
    except json.JSONDecodeError as error:
        raise ValueError(f"the body is not JSON: {error.msg}") from None
    if not isinstance(value, dict):
        raise ValueError("the body must be a JSON object")
    return value


@route("GET", "/api/agent")
def _agent(server: StudioServer, match: re.Match[str], body: str) -> tuple[int, Any]:
    return _api(lambda: api_agent.agent(server))


@route("GET", "/api/gates")
def _gates(server: StudioServer, match: re.Match[str], body: str) -> tuple[int, Any]:
    return _api(lambda: api_agent.gates(server))


@route("GET", f"/api/gates/(?P<name>{NAME})")
def _gate(server: StudioServer, match: re.Match[str], body: str) -> tuple[int, Any]:
    return _api(lambda: api_agent.gate(server, match["name"]))


@route("POST", f"/api/gates/(?P<name>{NAME})/whatif")
def _whatif(server: StudioServer, match: re.Match[str], body: str) -> tuple[int, Any]:
    return _api(lambda: api_agent.whatif(server, match["name"], _body_json(body)))


@route("GET", "/api/mcp")
def _mcp(server: StudioServer, match: re.Match[str], body: str) -> tuple[int, Any]:
    return _api(lambda: api_agent.mcp(server))


@route("GET", "/api/traces")
def _traces(server: StudioServer, match: re.Match[str], body: str) -> tuple[int, Any]:
    return _api(lambda: api_checks.traces(server))


@route("GET", f"/api/traces/(?P<name>{NAME})")
def _trace(server: StudioServer, match: re.Match[str], body: str) -> tuple[int, Any]:
    return _api(lambda: api_checks.trace(server, match["name"]))


@route("POST", f"/api/traces/(?P<name>{NAME})/replay")
def _replay(server: StudioServer, match: re.Match[str], body: str) -> tuple[int, Any]:
    return _api(lambda: api_checks.replay(server, match["name"]))


@route("POST", "/api/record")
def _record(server: StudioServer, match: re.Match[str], body: str) -> tuple[int, Any]:
    return _api(lambda: api_checks.record(server))


@route("POST", "/api/lint")
def _lint(server: StudioServer, match: re.Match[str], body: str) -> tuple[int, Any]:
    return _api(lambda: api_checks.lint(server))


@route("POST", "/api/verify")
def _verify(server: StudioServer, match: re.Match[str], body: str) -> tuple[int, Any]:
    return _api(lambda: api_checks.verify(server))


@route("POST", "/api/test")
def _test(server: StudioServer, match: re.Match[str], body: str) -> tuple[int, Any]:
    return _api(lambda: api_checks.test(server))


@route("GET", "/api/device")
def _device(server: StudioServer, match: re.Match[str], body: str) -> tuple[int, Any]:
    return _api(lambda: api_device.device(server))


@route("POST", "/api/device/build")
def _build(server: StudioServer, match: re.Match[str], body: str) -> tuple[int, Any]:
    return _api(lambda: api_device.build(server))


@route("GET", f"/api/device/golden/(?P<lang>vi|en)/(?P<name>{NAME})\\.png")
def _golden(server: StudioServer, match: re.Match[str], body: str) -> tuple[int, Any]:
    return _api(lambda: api_device.golden(server, match["lang"], match["name"]))


@route("GET", "/api/voice")
def _voice(server: StudioServer, match: re.Match[str], body: str) -> tuple[int, Any]:
    return _api(lambda: voice.status(server))


@route("POST", "/api/voice/mute")
def _mute(server: StudioServer, match: re.Match[str], body: str) -> tuple[int, Any]:
    return _api(lambda: voice.mute(server, _body_json(body)))


class StudioServer(SessionServer):
    """The sim page's server with the studio's page and API (docs/spec/studio.md)."""

    def __init__(
        self, session: SimSession, *, agent_path: Path, host: str = "127.0.0.1", port: int = 0
    ) -> None:
        super().__init__(session, host=host, port=port)
        self.agent_path = Path(agent_path).resolve()
        self.agent_root = self.agent_path.parent
        self.voice: Any = None  # voice.StudioVoice when started with --mic (slice S2)
        self.httpd.RequestHandlerClass = type("Handler", (_StudioHandler,), {"server_state": self})

    def dispatch(self, method: str, path: str, body: str) -> tuple[int, Any]:
        for verb, pattern, handler in ROUTES:
            match = pattern.match(path)
            if verb == method and match:
                return handler(self, match, body)
        return HTTPStatus.NOT_FOUND, {"ok": False, "error": {"why": f"no such path {path!r}"}}


class _StudioHandler(_Handler):
    server_state: StudioServer

    def _reply(self, status: int, payload: Any) -> None:
        if isinstance(payload, tuple):  # (bytes, content type): an image
            data, content_type = payload
            self._send(status, data, content_type)
            return
        self._send(status, _json(payload).encode(), "application/json")

    def do_GET(self) -> None:  # noqa: N802 - http.server API
        path = self.path.split("?", 1)[0]
        if path == "/":
            body = studio_page(self.server_state).encode("utf-8")
            self._send(HTTPStatus.OK, body, "text/html; charset=utf-8")
        elif path.startswith("/api/"):
            self._reply(*self.server_state.dispatch("GET", path, ""))
        else:
            super().do_GET()

    def do_POST(self) -> None:  # noqa: N802 - http.server API
        path = self.path.split("?", 1)[0]
        if not path.startswith("/api/"):
            super().do_POST()
            return
        if not self._same_origin():
            self._send(HTTPStatus.FORBIDDEN, b"cross-origin request refused", "text/plain")
            return
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            self._send(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, b"too long", "text/plain")
            return
        body = self.rfile.read(length).decode("utf-8", errors="replace")
        status, payload = self.server_state.dispatch("POST", path, body)
        self.server_state.notify()  # an action may have changed the session
        self._reply(status, payload)


def serve(
    session: SimSession,
    agent_path: Path,
    port: int,
    console: Any,
    open_browser: bool = True,
    on_start: Callable[[StudioServer], None] | None = None,
) -> None:
    """Serve until Ctrl-C. `on_start` runs once the server listens (the microphone, S2)."""
    server = StudioServer(session, agent_path=agent_path, port=port).start()
    console.print(
        f"[bold green]✓[/bold green] studio at [link]{server.url}[/link] — Ctrl-C to stop"
    )
    try:
        if on_start is not None:
            on_start(server)
        if open_browser:
            import webbrowser

            webbrowser.open(server.url)
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        console.print()
    finally:
        if server.voice is not None:
            server.voice.stop()
        server.stop()
