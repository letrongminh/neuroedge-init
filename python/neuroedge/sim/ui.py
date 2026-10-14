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
    POST /command  a typed line — a command, or `:set k v`, `:unset k`, `:sensor n v`,
                   `:analog ch v`, `:input pin v`, `:feedback pin duty=r`
    POST /confirm  {"id": "confirm_1", "answer": "yes"|"no"} — a person's answer to the
                   device's question (RFC-0006), source `ui`

Every POST must come from this page: an `Origin` of this server, and the header
`X-NeuroEdge-UI-Key` with the key made for this run (DP-A-02,
`docs/spec/deployment_profiles.md`). The key itself is never printed: the terminal URL
carries, after `#`, a one-time pairing code that the page trades once for the key
(`POST /pair`). Opening the URL puts it on the browser's command line and Claude
Desktop keeps stderr in a log, so another process on the machine — a brain with a shell,
a script — may see the URL later; by then the code is spent or expired. A refused POST
is traced as `ui_auth_refused`.

    POST /pair     {"code": "..."} — the one-time code from the URL, for the key; Origin only
    POST /pair/new a fresh code, for `neuroedge ui-link`: the header `X-NeuroEdge-UI-Control`
                   with the control secret of `ui.json`; the previous code stops working

Every page writes `ui.json` (mode 0600, `state_dir()`): its URL and a control secret. Under a
service manager (systemd sets `INVOCATION_ID`; `NEUROEDGE_SERVICE=1` says so for any other) the
URL is not printed, as it would land in the journal: the owner runs `neuroedge ui-link`, which
asks the running page for a fresh code (DP-A-10).

Turns run one at a time under a lock: the session, like a device, handles one
utterance after another. `neuroedge mcp serve --ui` (TSK-S3-27) serves this
page next to an MCP server over the same session: each MCP tool call takes the
same `lock` and ends with `notify()`, so the page shows it at once.
"""

from __future__ import annotations

import asyncio
import hmac
import json
import os
import secrets
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from ..errors import NeuroEdgeError
from ..trace import json_safe
from ..viz import board_info, page
from .session import SimSession, level_word


def _json(value: Any) -> str:
    """Strict JSON for the page: a bare NaN would stop `JSON.parse`, and the page with it."""
    return json.dumps(json_safe(value), ensure_ascii=False, allow_nan=False)


MAX_BODY = 4096
KEY_HEADER = "X-NeuroEdge-UI-Key"
MAX_REFUSALS_TRACED = 10_000  # as `mcp_auth_refused`: a flood cannot fill the trace
MAX_TRACED_PATH = 64  # a refused request names its path, cut: the request line is the caller's
PAIRING_TTL_S = 600.0  # the printed code works once, within ten minutes
CONTROL_HEADER = "X-NeuroEdge-UI-Control"
LINK_FILE = "ui.json"


def state_dir() -> Path:
    """Where `ui.json` lives: systemd's `$STATE_DIRECTORY`, else `$XDG_STATE_HOME/neuroedge`."""
    given = os.environ.get("STATE_DIRECTORY", "").split(":")[0]
    if given:
        return Path(given)
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "neuroedge"


def under_service_manager() -> bool:
    """Run by systemd (or a manager that says so): stdout and stderr go to a journal."""
    return bool(os.environ.get("INVOCATION_ID") or os.environ.get("NEUROEDGE_SERVICE"))


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
        self.key = secrets.token_urlsafe(32)
        self._code: str | None = secrets.token_urlsafe(16)
        self._code_deadline = time.monotonic() + PAIRING_TTL_S
        self._control = secrets.token_urlsafe(32)
        self.link_file: Path | None = None
        self.refusals = 0

    @property
    def url(self) -> str:
        host, port = self.httpd.server_address[:2]
        return f"http://{host}:{port}/"

    @property
    def open_url(self) -> str:
        """
        The URL a person opens. After `#` (never sent by a browser) it carries the one-time
        pairing code, not the key: the URL lands in the browser's command line and in logs.
        """
        return f"{self.url}#c={self._code or 'spent'}"

    def pair(self, code: str) -> str | None:
        """Trade the printed code for the key, once, within PAIRING_TTL_S; else None (and why)."""
        with self.lock:
            if self._code is None or time.monotonic() > self._code_deadline:
                self._code = None
                return None
            if not hmac.compare_digest(code.encode(), self._code.encode()):
                return None
            self._code = None  # spent: whoever reads the URL later gets nothing
            return self.key

    def new_code(self) -> str:
        """A fresh pairing code, for `neuroedge ui-link`: the previous one stops working."""
        with self.lock:
            self._code = secrets.token_urlsafe(16)
            self._code_deadline = time.monotonic() + PAIRING_TTL_S
        self._write_link()
        return self.open_url

    def control_ok(self, given: str | None) -> bool:
        return bool(given) and hmac.compare_digest(given.encode(), self._control.encode())

    def publish(self, directory: Path | None = None) -> Path:
        """Write `ui.json` (0600): the page's URL and the control secret `ui-link` needs."""
        self.link_file = (directory or state_dir()) / LINK_FILE
        self._write_link()
        return self.link_file

    def _write_link(self) -> None:
        if self.link_file is None:
            return
        self.link_file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        body = json.dumps({"url": self.open_url, "control": self._control, "pid": os.getpid()})
        temporary = self.link_file.with_name(f".{LINK_FILE}.{os.getpid()}")
        handle = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(handle, "w", encoding="utf-8") as out:
            out.write(body)
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.link_file)

    @property
    def announced_url(self) -> str:
        """What a terminal shows: the URL, or under a service manager where to get one."""
        if under_service_manager():
            return f"{self.link_file} (`neuroedge ui-link` prints a fresh link)"
        return self.open_url

    def refuse(self, reason: str, path: str) -> None:
        """Trace one refused POST (`ui_auth_refused`): the reason and path, never a key."""
        self.refusals += 1
        if self.refusals > MAX_REFUSALS_TRACED:
            return
        data: dict[str, Any] = {"reason": reason, "path": path[:MAX_TRACED_PATH]}
        if self.refusals == MAX_REFUSALS_TRACED:
            data["last_recorded"] = True  # the trace stops here; the count goes on
        with self.lock:
            self.session.events.emit("ui_auth_refused", data)
        self.notify()

    def state(self) -> dict[str, Any]:
        with self.lock:
            envelope = getattr(self.session.hal, "envelope", None)
            if envelope is not None:
                envelope.settle()  # a pin whose on-time is up has gone off: the page shows it
            self.session.hal.settle_motion()  # ... and a lease that ran out is the stop it was
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
                try:
                    session.set_fact(parts[0], _parse_value(parts[1]))
                except NeuroEdgeError as error:
                    return {"ok": False, "error": error.as_dict()}
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
            if name == "analog" and len(parts) == 2:
                try:
                    session.set_analog(parts[0], _parse_value(parts[1]))
                except NeuroEdgeError as error:
                    return {"ok": False, "error": error.as_dict()}
                return {"ok": True, "analog": parts[0]}
            if name == "feedback" and rest.split():
                pin, *words = rest.split()
                try:
                    session.set_feedback(pin, words)
                except NeuroEdgeError as error:
                    return {"ok": False, "error": error.as_dict()}
                return {"ok": True, "feedback": pin}
            if name == "input" and len(parts) == 2:
                level = level_word(parts[1])
                if level is None:
                    return {"ok": False, "error": {"why": f"{parts[1]!r} is not a level"}}
                try:
                    session.set_digital_in(parts[0], level)
                except NeuroEdgeError as error:
                    return {"ok": False, "error": error.as_dict()}
                return {"ok": True, "input": parts[0]}
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

    def start(self, publish: bool = True) -> SessionServer:
        self._thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self._thread.start()
        if publish:
            try:
                self.publish()
            except OSError as error:
                if under_service_manager():  # the journal must not get the URL instead
                    self.stop()
                    raise NeuroEdgeError(
                        where=f"page link file {state_dir() / LINK_FILE}",
                        why=f"cannot write it: {error.strerror or error}",
                        how="give the service a writable StateDirectory= (or $STATE_DIRECTORY)",
                    ) from error
                self.link_file = None
        return self

    def stop(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        link, self.link_file = self.link_file, None
        if link is not None:
            try:
                if json.loads(link.read_text(encoding="utf-8")).get("control") == self._control:
                    link.unlink()
            except (OSError, ValueError):
                pass


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
        if self._refuse_foreign_host():
            return
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
            self._send(HTTPStatus.OK, _json(state.state()).encode(), "application/json")
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
                payload = _json(state.state())
                self.wfile.write(f"data: {payload}\n\n".encode())
                self.wfile.flush()
                # Wake on a change, or every second so a running pulse can end on screen.
                seen = state.wait_for_change(seen, timeout=1.0)
        except (BrokenPipeError, ConnectionResetError):
            return

    def _hosts(self) -> set[str]:
        port = self.server.server_address[1]
        return {f"127.0.0.1:{port}", f"localhost:{port}"}

    def _host_ok(self) -> bool:
        """
        Every request names this server in `Host`. A page on another site that rebinds its
        DNS name to 127.0.0.1 (DNS rebinding) keeps its own name in `Host`, so it can read
        nothing — not the page, not /state, not /events (the user's words).
        """
        return self.headers.get("Host", "") in self._hosts()

    def _post_refusal(self) -> str | None:
        """
        Why this POST may not run, or None. Only this page may send commands or answer the
        device: a page on another site could POST to 127.0.0.1 from the user's browser, and
        any process on this machine could send no `Origin` at all. Both lack the run's key.
        """
        if not self._host_ok():
            return "foreign_host"
        origin = self.headers.get("Origin")
        if origin is None:
            return "no_origin"
        if origin not in {f"http://{host}" for host in self._hosts()}:
            return "foreign_origin"
        key = self.headers.get(KEY_HEADER)
        if not key:
            return "no_key"
        if not hmac.compare_digest(key.encode(), self.server_state.key.encode()):
            return "wrong_key"
        return None

    def _refuse_post(self) -> bool:
        """Answer 403 and trace the refusal when this POST may not run; True if it was refused."""
        reason = self._post_refusal()
        if reason is None:
            return False
        self.server_state.refuse(reason, self.path.split("?", 1)[0])
        self._send(HTTPStatus.FORBIDDEN, f"request refused: {reason}".encode(), "text/plain")
        return True

    def _body_length(self) -> int | None:
        """`Content-Length` as a size from 0 to MAX_BODY, or None (the caller answers 400/413)."""
        raw = self.headers.get("Content-Length") or "0"
        if not raw.isdigit():
            return None
        return int(raw)

    def _refuse_foreign_host(self) -> bool:
        if self._host_ok():
            return False
        self._send(HTTPStatus.FORBIDDEN, b"unknown host", "text/plain")
        return True

    def _pair(self) -> None:
        """`POST /pair`: same host and Origin as any POST, but no key yet — the code is the proof."""
        reason = self._post_refusal()
        if reason not in (None, "no_key", "wrong_key"):
            self.server_state.refuse(reason, "/pair")
            self._send(HTTPStatus.FORBIDDEN, f"request refused: {reason}".encode(), "text/plain")
            return
        length = self._body_length()
        if length is None or length > MAX_BODY:
            self._send(HTTPStatus.BAD_REQUEST, b"bad Content-Length", "text/plain")
            return
        try:
            code = str(json.loads(self.rfile.read(length) or b"{}")["code"])
        except (ValueError, KeyError, TypeError):
            code = ""
        key = self.server_state.pair(code)
        if key is None:
            self.server_state.refuse("bad_code", "/pair")
            self._send(HTTPStatus.FORBIDDEN, b"request refused: bad_code", "text/plain")
            return
        self._send(HTTPStatus.OK, _json({"ok": True, "key": key}).encode(), "application/json")

    def _link(self) -> None:
        """`POST /pair/new` from `neuroedge ui-link`: this host, and the control secret."""
        if not self._host_ok():
            self.server_state.refuse("foreign_host", "/pair/new")
            self._send(HTTPStatus.FORBIDDEN, b"request refused: foreign_host", "text/plain")
            return
        if not self.server_state.control_ok(self.headers.get(CONTROL_HEADER)):
            self.server_state.refuse("bad_control", "/pair/new")
            self._send(HTTPStatus.FORBIDDEN, b"request refused: bad_control", "text/plain")
            return
        url = self.server_state.new_code()
        self._send(HTTPStatus.OK, _json({"ok": True, "url": url}).encode(), "application/json")

    def do_POST(self) -> None:  # noqa: N802 - http.server API
        if self.path == "/pair":
            self._pair()
            return
        if self.path == "/pair/new":
            self._link()
            return
        if self._refuse_post():
            return
        if self.path not in ("/command", "/confirm"):
            self._send(HTTPStatus.NOT_FOUND, b"not found", "text/plain")
            return
        length = self._body_length()
        if length is None:
            self._send(HTTPStatus.BAD_REQUEST, b"bad Content-Length", "text/plain")
            return
        if length > MAX_BODY:
            self._send(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, b"too long", "text/plain")
            return
        line = self.rfile.read(length).decode("utf-8", errors="replace")
        if self.path == "/confirm":
            reply = self.server_state.confirm(line)
        else:
            reply = self.server_state.command(line)
        self._send(HTTPStatus.OK, _json(reply).encode(), "application/json")


def serve(session: SimSession, port: int, console: Any, open_browser: bool = True) -> None:
    """Serve until Ctrl-C."""
    server = SessionServer(session, port=port).start()
    console.print(
        f"[bold green]✓[/bold green] sim UI at [link]{server.announced_url}[/link] — Ctrl-C to stop",
        soft_wrap=True,  # one line: the key after `#` stays part of the URL
    )
    if open_browser and not under_service_manager():
        import webbrowser

        webbrowser.open(server.open_url)
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        console.print()
    finally:
        server.stop()
