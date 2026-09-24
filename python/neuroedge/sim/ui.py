"""
`neuroedge run --ui` — the `sim` session in a browser (TSK-S2-09, FR-TGT-06).

A local page, served from this process on 127.0.0.1 only, that shows the
virtual devices, sensors, screen and gate verdicts **live**, and takes typed
commands. Standard library only, no network access and no external asset:
the page is `neuroedge.viz.page(live=True)`, the same renderer as
`trace view`.

    GET  /         the page
    GET  /events   Server-Sent Events: {"events": [...], "now_ms": n} on change
    GET  /state    the same, once, as JSON
    POST /command  a typed line — a command, or `:set k v`, `:unset k`, `:sensor n v`
    POST /confirm  {"id": "confirm_1", "answer": "yes"|"no"} — a person's answer to the
                   device's question (RFC-0006), source `ui`; same-origin only

Turns run one at a time under a lock: the session, like a device, handles one
utterance after another. `neuroedge mcp serve --ui` (TSK-S3-27) serves this
page next to an MCP server over the same session: each MCP tool call takes the
same `lock` and ends with `notify()`, so the page shows it at once.
"""

from __future__ import annotations

import asyncio
import json
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from ..errors import NeuroEdgeError
from ..viz import board_info, page
from .session import SimSession

MAX_BODY = 4096


def _parse_value(text: str) -> Any:
    lowered = text.casefold()
    if lowered in ("true", "false"):
        return lowered == "true"
    for kind in (int, float):
        try:
            return kind(text)
        except ValueError:
            continue
    return text


class SessionServer:
    def __init__(self, session: SimSession, host: str = "127.0.0.1", port: int = 0) -> None:
        self.session = session
        self.lock = threading.Lock()
        self.changed = threading.Condition()
        self.version = 0
        handler = type("Handler", (_Handler,), {"server_state": self})
        try:
            self.httpd = ThreadingHTTPServer((host, port), handler)
        except OSError as error:
            raise NeuroEdgeError(
                where=f"sim UI on {host}:{port}",
                why=f"cannot listen on port {port}: {error.strerror or error}",
                how=f"stop what holds port {port}, or pass another with --port (0 picks a free one)",
            ) from error
        self.httpd.daemon_threads = True
        self._thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        host, port = self.httpd.server_address[:2]
        return f"http://{host}:{port}/"

    def state(self) -> dict[str, Any]:
        with self.lock:
            return {
                "events": list(self.session.events.events),
                "now_ms": self.session.events.elapsed_ms(),
            }

    def command(self, line: str) -> dict[str, Any]:
        """Run one typed line and say what happened, in the shape the page shows."""
        with self.lock:
            reply = self._command(line.strip())
        self.notify()
        return reply

    def notify(self) -> None:
        """The session changed: wake every `/events` stream now. Also the hook for MCP calls."""
        with self.changed:
            self.version += 1
            self.changed.notify_all()

    def _command(self, line: str) -> dict[str, Any]:
        session = self.session
        if line.startswith(":"):
            name, _, rest = line[1:].partition(" ")
            parts = rest.split(maxsplit=1)
            if name == "set" and len(parts) == 2:
                session.facts[parts[0]] = _parse_value(parts[1])
                return {"ok": True, "fact": parts[0]}
            if name == "unset" and len(parts) == 1:
                session.facts.pop(parts[0], None)
                return {"ok": True, "fact": parts[0]}
            if name == "sensor" and len(parts) == 2:
                try:
                    session.set_sensor(parts[0], _parse_value(parts[1]))
                except NeuroEdgeError as error:
                    return {"ok": False, "error": error.as_dict()}
                return {"ok": True, "sensor": parts[0]}
            return {"ok": False, "error": {"why": f"unknown command {line!r}"}}
        if not line:
            return {"ok": False, "error": {"why": "empty command"}}
        try:
            turn = asyncio.run(session.handle(line))
        except NeuroEdgeError as error:
            return {"ok": False, "error": error.as_dict()}
        reply: dict[str, Any] = {
            "ok": True,
            "recognised": turn.recognised,
            "intent": turn.recognition.intent,
        }
        if turn.result is not None:
            reply["verdict"] = str(turn.result.verdict)
            reply["action"] = turn.result.action
        return reply

    def confirm(self, body: str) -> dict[str, Any]:
        """A click on "Đồng ý" / "Huỷ": the page is the device's own screen (source `ui`)."""
        try:
            request = json.loads(body)
            confirm_id, answer = str(request["id"]), request["answer"]
            if answer not in ("yes", "no"):
                raise ValueError(answer)
        except (ValueError, KeyError, TypeError):
            return {"ok": False, "error": {"why": 'expected {"id": "...", "answer": "yes"|"no"}'}}
        with self.lock:
            call = self.session.confirm if answer == "yes" else self.session.decline
            try:
                turn = asyncio.run(call(confirm_id, source="ui"))
            except NeuroEdgeError as error:
                reply: dict[str, Any] = {"ok": False, "error": error.as_dict()}
            else:
                reply = {"ok": turn.reply_source != "confirm_refused", "reply": turn.reply}
                if turn.result is not None:
                    reply["verdict"] = str(turn.result.verdict)
        with self.changed:
            self.version += 1
            self.changed.notify_all()
        return reply

    def wait_for_change(self, seen: int, timeout: float) -> int:
        with self.changed:
            self.changed.wait_for(lambda: self.version != seen, timeout=timeout)
            return self.version

    def start(self) -> SessionServer:
        self._thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()


class _Handler(BaseHTTPRequestHandler):
    server_state: SessionServer

    def log_message(self, format: str, *args: Any) -> None:  # quiet: the terminal shows turns
        return None

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - http.server API
        state = self.server_state
        if self.path == "/":
            session = state.session
            snapshot = state.state()
            body = page(
                title=f"{session.manifest.label} · sim",
                meta=dict(session.events.metadata),
                events=snapshot["events"],
                board=board_info(session.hal.board.id),
                live=True,
            ).encode("utf-8")
            self._send(HTTPStatus.OK, body, "text/html; charset=utf-8")
        elif self.path == "/state":
            self._send(HTTPStatus.OK, json.dumps(state.state()).encode(), "application/json")
        elif self.path == "/events":
            self._stream()
        else:
            self._send(HTTPStatus.NOT_FOUND, b"not found", "text/plain")

    def _stream(self) -> None:
        state = self.server_state
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        seen = -1
        try:
            while True:
                payload = json.dumps(state.state(), ensure_ascii=False)
                self.wfile.write(f"data: {payload}\n\n".encode())
                self.wfile.flush()
                # Wake on a change, or every second so a running pulse can end on screen.
                seen = state.wait_for_change(seen, timeout=1.0)
        except (BrokenPipeError, ConnectionResetError):
            return

    def _same_origin(self) -> bool:
        """
        Only this page may send commands. A page on another site could otherwise
        POST to 127.0.0.1 from the user's browser and drive the simulator.
        """
        host = self.headers.get("Host", "")
        port = self.server.server_address[1]
        allowed = {f"127.0.0.1:{port}", f"localhost:{port}"}
        origin = self.headers.get("Origin")
        return host in allowed and (origin is None or origin.removeprefix("http://") in allowed)

    def do_POST(self) -> None:  # noqa: N802 - http.server API
        if not self._same_origin():
            self._send(HTTPStatus.FORBIDDEN, b"cross-origin request refused", "text/plain")
            return
        if self.path not in ("/command", "/confirm"):
            self._send(HTTPStatus.NOT_FOUND, b"not found", "text/plain")
            return
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            self._send(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, b"too long", "text/plain")
            return
        line = self.rfile.read(length).decode("utf-8", errors="replace")
        if self.path == "/confirm":
            reply = self.server_state.confirm(line)
        else:
            reply = self.server_state.command(line)
        self._send(
            HTTPStatus.OK, json.dumps(reply, ensure_ascii=False).encode(), "application/json"
        )


def serve(session: SimSession, port: int, console: Any, open_browser: bool = True) -> None:
    """Serve until Ctrl-C."""
    server = SessionServer(session, port=port).start()
    console.print(
        f"[bold green]✓[/bold green] sim UI at [link]{server.url}[/link] — Ctrl-C to stop"
    )
    if open_browser:
        import webbrowser

        webbrowser.open(server.url)
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        console.print()
    finally:
        server.stop()
