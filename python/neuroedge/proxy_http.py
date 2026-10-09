"""
`neuroedge proxy http` — a local HTTP API that moves things, put behind NeuroEdge (TSK-I2c-15).

    HTTP client ──request──► proxy ──► Guard: gate ─► token ─► envelope ─► trace
                                            │ ALLOW only
                                            ▼
                              the tool's `run`: forward the ORIGINAL request to the real API

For the Tasmota / Shelly / ESPHome web APIs, a home-made REST service, Home Assistant's REST API:
each route declared in `[[proxy.http.routes]]` is a tool of a `neuroedge.guard.Guard`; the real API is
reached **only inside that tool's `run`**, i.e. after the gate said ALLOW. Anything not declared is
refused with a 404 and never forwarded.

HTTP has no built-in `call_source` (a new one is an RFC, `schemas/`), so this front is a **core
bridge**: it dispatches through `guard.dispatcher(id)` and its calls are `bridge:<id>` (default
`bridge:http`). A gate has to list that source; a gate that lists only `mcp` BLOCKs it.

There is no authentication on the front in this task, so it listens on loopback **only**. What it
cannot do, and says so (`neuroedge plugin doctor`): the real API is still reachable around the proxy.
Stdlib only: `asyncio` streams in front, `http.client` behind. No TLS on the front, no websockets, no
streaming bodies.
"""

from __future__ import annotations

import asyncio
import contextvars
import http.client
import ipaddress
import json
import os
import re
import signal
import socket
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, unquote, urlsplit

from .errors import AgentManifestError, NeuroEdgeError
from .guard import Guard, GuardConfig, load_config, resolve_gates
from .models.providers.common import ENV_NAME, NAME, refuse_unknown
from .proxy_mcp import (
    LAN_COMMENT,
    Finding,
    Plan,
    UpstreamFailed,
    _bad,
    _toml,
    default_name,
    lan_flag,
    lan_warning,
    refuse_plain_http,
    tool_name_for,
    validate_plan,
    write_plan,
)
from .sdk import ToolRequest

WHERE = "neuroedge proxy http"
MAX_BODY = 1 << 20  # 1 MiB of request body
MAX_RESPONSE = 16 << 20
MAX_HEADERS = 64 << 10
TIMEOUT_S = 30.0
READ_TIMEOUT_S = 15.0
METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE")
HEADER = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,63}")
PARAM = re.compile(r"[a-z][a-z0-9_]{0,63}")
SEGMENT_PARAM = re.compile(r"\{([a-z][a-z0-9_]{0,63})\}")
BRIDGE_ID = re.compile(r"[a-z][a-z0-9_]{0,31}")
LOOPBACK_NAMES = ("localhost",)
HOP_BY_HOP = frozenset(
    ["connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "proxy-connection", "te", "trailer", "trailers", "transfer-encoding", "upgrade"]
)  # fmt: skip
# Never forwarded from the client, whatever else is: the proxy's own credentials replace them.
NEVER_FORWARD = HOP_BY_HOP | {"host", "content-length", "authorization", "cookie", "expect"}
DEFAULT_LISTEN = "127.0.0.1:8787"
DEFAULT_ID = "http"


# --- [proxy.http] ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class Route:
    """One declared route: `method`, `path` (with `{param}` segments) and the tool it is."""

    method: str
    path: str
    tool: str

    @property
    def segments(self) -> tuple[str, ...]:
        return tuple(self.path.split("/")[1:])

    @property
    def params(self) -> tuple[str, ...]:
        return tuple(m.group(1) for seg in self.segments if (m := SEGMENT_PARAM.fullmatch(seg)))


@dataclass(frozen=True)
class HttpProxy:
    """`[proxy.http]` after checking."""

    upstream: str
    host: str
    port: int
    id: str = DEFAULT_ID
    headers_env: Mapping[str, str] = field(default_factory=dict)
    routes: tuple[Route, ...] = ()
    # Opt-in: plain http to a host on the home LAN (`proxy_mcp.refuse_plain_http`).
    allow_lan_http: bool = False

    @property
    def source(self) -> str:
        return f"bridge:{self.id}"


def is_loopback(host: str) -> bool:
    if host.lower() in LOOPBACK_NAMES:
        return True
    try:
        return ipaddress.ip_address(host.strip("[]")).is_loopback
    except ValueError:
        return False


def _split_listen(value: Any, where: str) -> tuple[str, int]:
    if not isinstance(value, str) or ":" not in value:
        raise _bad(
            where + " listen", "`listen` is `host:port`", f'write listen = "{DEFAULT_LISTEN}"'
        )
    host, _, port = value.rpartition(":")
    host = host.strip("[]")
    if not port.isdigit() or int(port) > 65535 or not host:
        raise _bad(where + " listen", "`listen` is `host:port` with a port 0-65535", "x")
    if not is_loopback(host):
        raise _bad(
            where + " listen",
            "the proxy listens on loopback only: it has no authentication on its front in this "
            "version, so any other address would hand the gate's road to the whole network",
            "use 127.0.0.1 (or ::1)",
        )
    return host, int(port)


def check_upstream(url: Any, where: str, allow_lan: bool = False) -> str:
    """
    An http(s) base URL: plain http only to loopback — or, with `allow_lan_http`, to a LAN host;
    no credentials, no query, no fragment.
    """
    if not isinstance(url, str):
        raise _bad(where + " upstream", "`upstream` is a URL string", "x")
    parts = urlsplit(url)
    host = parts.hostname or ""
    if parts.scheme not in ("http", "https") or not host:
        raise _bad(where + " upstream", "`upstream` is an http(s) URL", "x")
    if parts.username or parts.password or parts.query or parts.fragment:
        raise _bad(
            where + " upstream",
            "the URL carries credentials, a query or a fragment; the file is committed and shared",
            "use headers_env for a token, and declare query parameters on the routes",
        )
    if parts.scheme == "http" and not is_loopback(host):
        refuse_plain_http(host, allow_lan, where, "upstream")
    return url.rstrip("/")


def _template(path: Any, where: str) -> str:
    if not isinstance(path, str) or not path.startswith("/") or "?" in path or "#" in path:
        raise _bad(
            where, "a route path starts with `/` and holds no query", 'write path = "/cm/{cmd}"'
        )
    for segment in path.split("/")[1:]:
        if "{" in segment or "}" in segment:
            if not SEGMENT_PARAM.fullmatch(segment):
                raise _bad(where, f"{segment!r}: a parameter is a whole segment `{{name}}`", "x")
        elif segment in ("..", "."):
            raise _bad(where, "a route path has no `.` or `..` segment", "x")
        elif "%" in segment or (segment == "" and path != "/"):
            raise _bad(where, "a route path has no percent-encoding and no empty segment", "x")
    return path


def parse_http(config: GuardConfig) -> HttpProxy:
    """
    `[proxy.http]` of a loaded guard.toml, or `AgentManifestError` (NE3002, three parts). Loopback
    only on both the front and a plain-http upstream; a header secret only by the NAME of an
    environment variable; every route names a tool of the same file, and every `{param}` is a
    parameter that tool declares (or every request would be REJECTED).
    """
    where = f"{config.source} [proxy.http]"
    refuse_unknown(
        config.proxy, config.source, "proxy", ("mcp", "http"),
        "[proxy] has mcp (`proxy mcp`) or http (`proxy http`), exactly one of them",
    )  # fmt: skip
    if "http" in config.proxy and "mcp" in config.proxy:
        raise _bad(
            f"{config.source} [proxy]",
            "both [proxy.mcp] and [proxy.http] are given; a guard.toml fronts one kind of server",
            "keep one of them",
        )
    table = config.proxy.get("http")
    if not isinstance(table, dict):
        raise _bad(
            where,
            "this guard.toml has no [proxy.http] table: there is nothing to put `proxy http` in front of",
            'run `neuroedge guard init --http <upstream> --route "POST /path"`, or add [proxy.http]',
        )
    refuse_unknown(
        table, where, "proxy.http", ("upstream", "listen", "id", "headers_env", "routes", "allow_lan_http"),
        "[proxy.http] has upstream, listen, id, headers_env, allow_lan_http and [[proxy.http.routes]]",
    )  # fmt: skip
    allow_lan = lan_flag(table, where)
    upstream = check_upstream(table.get("upstream"), where, allow_lan)
    host, port = _split_listen(table.get("listen", DEFAULT_LISTEN), where)
    ident = table.get("id", DEFAULT_ID)
    if not isinstance(ident, str) or not BRIDGE_ID.fullmatch(ident):
        raise _bad(
            where + " id", "`id` is the bridge id: [a-z][a-z0-9_]{0,31}", 'write id = "http"'
        )
    headers = table.get("headers_env", {})
    if not isinstance(headers, dict) or not all(
        isinstance(h, str) and HEADER.fullmatch(h) and isinstance(v, str) and ENV_NAME.fullmatch(v)
        for h, v in headers.items()
    ):
        # Never repeat a value: a pasted `Bearer …` is a live token.
        raise _bad(
            where + " headers_env",
            "`headers_env` maps a header name to the NAME of an environment variable (letters, "
            "digits, _); a value that is not such a name is refused — if it was the token itself, "
            "revoke it",
            'write headers_env = { Authorization = "DEVICE_TOKEN" } and export DEVICE_TOKEN',
        )
    raw_routes = table.get("routes")
    if not isinstance(raw_routes, list) or not raw_routes:
        raise _bad(where + " routes", "declare at least one `[[proxy.http.routes]]`", "x")
    tools = {tool.name: tool for tool in config.tools}
    routes: list[Route] = []
    seen: set[tuple[str, tuple[str, ...]]] = set()
    for index, entry in enumerate(raw_routes):
        at = f"{where} routes[{index}]"
        if not isinstance(entry, dict):
            raise _bad(at, "a route is a table", "x")
        refuse_unknown(entry, at, "proxy.http.routes", ("method", "path", "tool"), "x")
        method = entry.get("method")
        if method not in METHODS:
            raise _bad(at + " method", f"`method` is one of {list(METHODS)}", "x")
        path = _template(entry.get("path"), at + " path")
        tool = entry.get("tool")
        if tool not in tools:
            raise _bad(
                at + " tool",
                f"{tool!r} is not a [tools.<name>] of this guard.toml",
                f"declare [tools.{tool}] with its gate, or fix the name",
            )
        route = Route(method, path, tool)
        shape = (method, tuple(SEGMENT_PARAM.sub("{}", s) for s in route.segments))
        if shape in seen:
            raise _bad(at, f"{method} {path} is declared twice (parameter names aside)", "x")
        seen.add(shape)
        missing = [p for p in route.params if p not in tools[tool].parameters]
        if missing:
            raise _bad(
                at,
                f"path parameter(s) {missing} are not declared as parameters of tool {tool!r}: "
                "every request would be REJECTED",
                f'add [tools.{tool}.parameters.{missing[0]}] with type = "string"',
            )
        routes.append(route)
    return HttpProxy(upstream, host, port, ident, dict(headers), tuple(routes), allow_lan)


# --- one request ----------------------------------------------------------------------------------


class BadRequest(Exception):
    """A request refused before the Guard sees it: `status`, and why (told to the client)."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


@dataclass
class RawRequest:
    """What came in, byte for byte; and, once the tool's `run` has forwarded it, what came back."""

    method: str
    target: str  # the original request target: path and query as sent
    headers: list[tuple[str, str]]
    body: bytes
    response: tuple[int, str, list[tuple[str, str]], bytes] | None = None


_current: contextvars.ContextVar[RawRequest | None] = contextvars.ContextVar(
    "neuroedge_proxy_http_request", default=None
)


def match_route(
    routes: tuple[Route, ...], method: str, path: str
) -> tuple[Route, dict[str, str]] | None:
    """The route a request path is, and its path parameters (decoded, and refused if unsafe)."""
    segments = path.split("/")[1:]
    for route in routes:
        if route.method != method or len(route.segments) != len(segments):
            continue
        values: dict[str, str] = {}
        for template, actual in zip(route.segments, segments, strict=True):
            hole = SEGMENT_PARAM.fullmatch(template)
            if hole is None:
                if template != actual:
                    break
                continue
            value = unquote(actual)
            if (
                not value
                or "/" in value
                or "\\" in value
                or value in (".", "..")
                or any(ord(c) < 32 or ord(c) == 127 for c in value)
            ):
                raise BadRequest(400, f"path parameter {hole.group(1)!r} is empty or unsafe")
            values[hole.group(1)] = value
        else:
            return route, values
    return None


def _scalar_object(body: bytes) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in items:
            if key in out:
                raise BadRequest(400, f"the body gives {key!r} twice")
            out[key] = value
        return out

    def refuse(constant: str) -> Any:
        raise BadRequest(400, f"the body has {constant}, which is not JSON")

    try:
        parsed = json.loads(body.decode("utf-8"), object_pairs_hook=pairs, parse_constant=refuse)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise BadRequest(
            400, "the body is not JSON (UTF-8); a body, if any, is a JSON object"
        ) from None
    if not isinstance(parsed, dict):
        raise BadRequest(400, "the body is not a JSON object")
    for key, value in parsed.items():
        if not isinstance(value, str | int | float | bool):
            raise BadRequest(
                400, f"body field {key!r} is not a scalar (a string, number or boolean)"
            )
    return parsed


def arguments_of(route_values: dict[str, str], query: str, body: bytes) -> dict[str, Any]:
    """
    The tool's arguments: path parameters, query parameters and the scalars of a JSON-object body.
    A name given in two places or twice, and anything not scalar, is a 400 and nothing is dispatched.
    """
    arguments: dict[str, Any] = dict(route_values)
    pairs = parse_qsl(query, keep_blank_values=True)
    query_keys = [k for k, _ in pairs]
    if len(set(query_keys)) != len(query_keys):
        raise BadRequest(400, "a query parameter is given twice")
    for key, value in pairs:
        if key in arguments:
            raise BadRequest(400, f"{key!r} is given twice (path and query)")
        arguments[key] = value
    if body:
        for key, value in _scalar_object(body).items():
            if key in arguments:
                raise BadRequest(400, f"{key!r} is given twice (path or query, and body)")
            arguments[key] = value
    return arguments


def _forward_sync(
    proxy: HttpProxy, headers_extra: Mapping[str, str], request: RawRequest
) -> tuple[int, str, list[tuple[str, str]], bytes]:
    parts = urlsplit(proxy.upstream)
    connection_cls = (
        http.client.HTTPSConnection if parts.scheme == "https" else http.client.HTTPConnection
    )
    named = {
        t.strip().lower()
        for v in (h[1] for h in request.headers if h[0].lower() == "connection")
        for t in v.split(",")
    }
    configured = {k.lower() for k in headers_extra}
    headers = {
        name: value
        for name, value in request.headers
        if (lower := name.lower()) not in NEVER_FORWARD
        and lower not in named
        and lower not in configured
        and not lower.startswith("proxy-")
    }
    headers.update(headers_extra)
    headers["Host"] = parts.netloc
    headers["Content-Length"] = str(len(request.body))
    headers["Connection"] = "close"
    conn = connection_cls(parts.hostname or "", parts.port, timeout=TIMEOUT_S)
    try:
        conn.request(
            request.method,
            (parts.path or "") + request.target,
            body=request.body or None,
            headers=headers,
        )
        response = conn.getresponse()
        body = response.read(MAX_RESPONSE + 1)
        if len(body) > MAX_RESPONSE:
            raise UpstreamFailed("the upstream's answer is larger than the proxy forwards")
        return response.status, response.reason, response.getheaders(), body
    except UpstreamFailed:
        raise
    except (OSError, http.client.HTTPException) as problem:
        raise UpstreamFailed(f"{type(problem).__name__}: {problem}"[:240]) from None
    finally:
        conn.close()


def _forward(proxy: HttpProxy, headers_extra: Mapping[str, str]) -> Any:
    """The `run` of every tool: forwards the request this dispatch belongs to. Never retried."""

    async def run(**_arguments: Any) -> None:
        request = _current.get()
        if request is None:
            raise UpstreamFailed("no request is being served: the tool was run outside the proxy")
        request.response = await asyncio.to_thread(_forward_sync, proxy, headers_extra, request)

    return run


# --- the Guard and the server -----------------------------------------------------------------------


def configured_headers(proxy: HttpProxy) -> dict[str, str]:
    missing = [v for v in proxy.headers_env.values() if v not in os.environ]
    if missing:
        raise NeuroEdgeError(
            where=f"{WHERE} -> upstream",
            why=f"environment variable(s) {sorted(set(missing))} named in guard.toml are not set",
            how=f"export {missing[0]}=… in the shell that runs this command",
        )
    return {h: os.environ[v] for h, v in proxy.headers_env.items()}


def reachable(proxy: HttpProxy, timeout: float = 5.0) -> OSError | None:
    parts = urlsplit(proxy.upstream)
    port = parts.port or (443 if parts.scheme == "https" else 80)
    try:
        with socket.create_connection((parts.hostname or "", port), timeout=timeout):
            return None
    except OSError as problem:
        return problem


def build_guard(config: GuardConfig, proxy: HttpProxy, events: Any = None) -> Guard:
    """The proxy's `Guard`: each tool's `run` forwards the dispatching request, after ALLOW."""
    headers = configured_headers(proxy)
    routed = {route.tool for route in proxy.routes}
    tools = []
    for tool in config.tools:
        if tool.requires or tool.drive:
            raise _bad(
                f"{config.source} [tools.{tool.name}]",
                "a proxy tool forwards a request; it holds no pins (`requires`, `drive`)",
                "remove them",
            )
        if tool.name not in routed:
            raise _bad(
                f"{config.source} [tools.{tool.name}]",
                "no [[proxy.http.routes]] reaches this tool, so it could never be called",
                "add a route for it, or remove the tool",
            )
        route = next(r for r in proxy.routes if r.tool == tool.name)
        tools.append(
            replace(tool, run=_forward(proxy, headers), description=f"{route.method} {route.path}")
        )
    guard = Guard(
        tools,
        name=config.name,
        board=config.board,
        registry_root=config.registry_root,
        base=config.base,
        events=events,
        source=config.source,
    )
    guard.events.metadata["proxy"] = {"kind": "http", "upstream": proxy.upstream}
    return guard


def _verdict_body(status: int, content: Mapping[str, Any]) -> tuple[int, bytes, str]:
    return status, json.dumps(content, ensure_ascii=False).encode("utf-8"), "application/json"


async def _read_request(reader: asyncio.StreamReader) -> RawRequest:
    try:
        head = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), READ_TIMEOUT_S)
    except asyncio.LimitOverrunError:
        raise BadRequest(431, "the request head is too large") from None
    except (asyncio.IncompleteReadError, TimeoutError):
        raise BadRequest(400, "an incomplete request") from None
    if len(head) > MAX_HEADERS:
        raise BadRequest(431, "the request head is too large")
    lines = head.decode("latin-1").split("\r\n")
    request_line = lines[0].split(" ")
    if len(request_line) != 3 or not request_line[2].startswith("HTTP/1."):
        raise BadRequest(400, "not an HTTP/1.x request")
    method, target = request_line[0], request_line[1]
    headers: list[tuple[str, str]] = []
    for line in lines[1:]:
        if not line:
            continue
        name, colon, value = line.partition(":")
        if not colon or not HEADER.fullmatch(name):
            raise BadRequest(400, "a malformed header")
        headers.append((name, value.strip()))
    lowered = [n.lower() for n, _ in headers]
    if "transfer-encoding" in lowered:
        raise BadRequest(411, "a body with Transfer-Encoding is not supported; send Content-Length")
    lengths = [v for n, v in headers if n.lower() == "content-length"]
    if len(lengths) > 1 or (lengths and not lengths[0].isdigit()):
        raise BadRequest(400, "a bad Content-Length")
    length = int(lengths[0]) if lengths else 0
    if length > MAX_BODY:
        raise BadRequest(413, f"the body is larger than {MAX_BODY} bytes")
    body = b""
    if length:
        try:
            body = await asyncio.wait_for(reader.readexactly(length), READ_TIMEOUT_S)
        except (asyncio.IncompleteReadError, TimeoutError):
            raise BadRequest(400, "the body is shorter than Content-Length") from None
    return RawRequest(method, target, headers, body)


class Front:
    """The HTTP front: parse, match a declared route, dispatch through the bridge, answer."""

    def __init__(self, guard: Guard, proxy: HttpProxy) -> None:
        self.guard = guard
        self.proxy = proxy
        self.bridge = guard.dispatcher(proxy.id)

    async def answer(self, request: RawRequest) -> tuple[int, list[tuple[str, str]], bytes]:
        """(status, headers, body) for one parsed request. Raises `BadRequest` for a refusal."""
        if not request.target.startswith("/"):
            raise BadRequest(400, "the request target is a path")
        parts = urlsplit(request.target)
        lowered = parts.path.lower()
        if "%2f" in lowered or "%5c" in lowered or "%00" in lowered or "//" in parts.path:
            raise BadRequest(400, "an encoded slash, NUL or empty segment in the path")
        matched = match_route(self.proxy.routes, request.method, parts.path)
        if matched is None:
            declared = [f"{r.method} {r.path}" for r in self.proxy.routes]
            return self._json(404, {"status": "NOT_FOUND", "problems": [
                f"{request.method} {parts.path} is not a declared route; only declared routes "
                f"pass, and nothing was forwarded (declared: {declared})"]})  # fmt: skip
        route, values = matched
        arguments = arguments_of(values, parts.query, request.body)
        token = _current.set(request)
        try:
            outcome = await self.bridge.dispatch(ToolRequest(route.tool, arguments))
        except UpstreamFailed as failure:
            return self._json(502, {"tool": route.tool, "status": "ALLOW", "problems": [
                "the gate allowed the request, then the upstream failed; it was not retried: "
                f"{failure}"]})  # fmt: skip
        finally:
            _current.reset(token)
        if outcome.status == "ALLOW" and request.response is not None:
            status, _reason, headers, body = request.response
            keep = [
                (k, v) for k, v in headers
                if k.lower() not in HOP_BY_HOP and k.lower() != "content-length"
            ]  # fmt: skip
            return status, keep, body
        code = 403 if outcome.status == "BLOCK" else 400
        return self._json(code, dict(outcome.content))

    @staticmethod
    def _json(status: int, content: Mapping[str, Any]) -> tuple[int, list[tuple[str, str]], bytes]:
        _, body, kind = _verdict_body(status, content)
        return status, [("Content-Type", kind)], body

    async def handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            try:
                request = await _read_request(reader)
                status, headers, body = await self.answer(request)
            except BadRequest as refused:
                status, headers, body = self._json(
                    refused.status, {"status": "REJECTED", "problems": [refused.message]}
                )
            reason = http.client.responses.get(status, "")
            head = [f"HTTP/1.1 {status} {reason}"]
            head += [f"{k}: {v}" for k, v in headers]
            head += [f"Content-Length: {len(body)}", "Connection: close", "", ""]
            writer.write("\r\n".join(head).encode("latin-1", "replace") + body)
            await writer.drain()
        except (ConnectionError, asyncio.CancelledError):
            pass
        finally:
            writer.close()


async def serve(
    config_path: Path,
    *,
    trace_out: Path | None = None,
    on_ready: Any = None,
    stop: asyncio.Event | None = None,
) -> None:
    """Serve until SIGINT/SIGTERM; write the trace on the way out. Refuses to start before listening."""
    config = load_config(config_path)
    proxy = parse_http(config)
    problem = reachable(proxy)
    if problem is not None:
        raise NeuroEdgeError(
            where=f"{WHERE} -> upstream {proxy.upstream}",
            why=f"cannot reach the real API: {type(problem).__name__}: {problem}",
            how="start it (or fix `upstream` in [proxy.http]) and run again",
        )
    guard = build_guard(config, proxy)
    stop = stop if stop is not None else asyncio.Event()  # set by SIGINT/SIGTERM, or by a caller
    loop = asyncio.get_running_loop()
    installed = []
    for name in ("SIGINT", "SIGTERM"):
        if hasattr(signal, name):
            try:
                loop.add_signal_handler(getattr(signal, name), stop.set)
                installed.append(getattr(signal, name))
            except (NotImplementedError, RuntimeError):
                pass
    server = None
    try:
        front = Front(guard, proxy)
        server = await asyncio.start_server(front.handle, proxy.host, proxy.port, limit=MAX_HEADERS)
        port = server.sockets[0].getsockname()[1]
        if on_ready is not None:
            on_ready(guard, proxy, port)
        await stop.wait()
    finally:
        if server is not None:
            server.close()
            await server.wait_closed()
        for sig in installed:
            loop.remove_signal_handler(sig)
        try:
            if trace_out is not None:
                trace_out.write_text(
                    json.dumps(guard.trace(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
                )
        finally:
            guard.close()


# --- guard init --http ----------------------------------------------------------------------------


def parse_route(spec: str) -> tuple[str, str]:
    method, _, path = spec.strip().partition(" ")
    path = path.strip()
    if method not in METHODS or not path:
        raise NeuroEdgeError(
            where="neuroedge guard init --route",
            why=f"{spec!r} is not `METHOD /path`",
            how=f'write --route "POST /cm/{{cmd}}" (methods: {", ".join(METHODS)})',
        )
    try:
        _template(path, "neuroedge guard init --route")
    except AgentManifestError as error:
        raise NeuroEdgeError(where=error.where, why=error.why, how=error.how) from None
    return method, path


def http_gate_text(tool: str, route: Route, source: str) -> str:
    return f"""\
# Gate sinh bởi `neuroedge guard init --http` cho route `{route.method} {route.path}`.
#
# MẶC ĐỊNH BỊ CHẶN: `operator_approved` là một tiêu chí không ai đặt (proxy không `set_fact` nó),
# nên mọi request tới route này bị chặn (`criterion_unavailable`, HTTP 403) cho tới khi người vận hành
# sửa gate này CÓ CHỦ Ý.
#
# Nguồn của proxy http là `{source}` (một bridge của lõi, RFC-0017): gate PHẢI liệt kê nó,
# gate chỉ liệt kê `mcp` sẽ chặn nó. `allow_when` ở dưới chỉ nhận `{source}`.
#
# Để mở (BY DESIGN you must do this yourself):
#   1. Xoá tiêu chí `operator_approved` ở `evaluate:` VÀ dòng `operator_approved: true` ở `allow_when:`,
#      hoặc thay bằng điều kiện thật của bạn.
#   2. Query và body JSON chỉ vào được qua tham số khai ở guard.toml (`[tools.{tool}.parameters.<tên>]`);
#      tham số không khai ⇒ HTTP 400.
#   3. Chạy `neuroedge gate lint gates` rồi `neuroedge plugin doctor`.
# Route có tác dụng không hoàn tác (mở khoá, bật nguồn) nên thêm điều kiện, đừng chỉ mở cho bridge.
schema:  neuroedge.gate/v1
name:    {tool}
version: 1.0.0

evaluate:
  call_source:
    type: choice
    options: [local_grammar, system_one, system_two, mcp, "{source}", test]
    instructions: "Nguồn của tool call, do dispatcher đặt (Q-24); proxy http là {source}"
  operator_approved:
    type: bool
    instructions: "Người vận hành đã mở gate này có chủ ý — không ai đặt dữ kiện này lúc sinh"

allow_when:
  call_source:       {{ in: ["{source}"] }}
  operator_approved: true

on_block:
  action: deny

budget:
  p95_latency_ms: 150
  fail:           closed
"""


def plan_http(
    upstream: str, routes: list[tuple[str, str]], base: Path, name: str, *,
    ident: str = DEFAULT_ID, listen: str = DEFAULT_LISTEN, header_env: dict[str, str] | None = None,
    allow_lan_http: bool = False,
) -> Plan:  # fmt: skip
    """The files `guard init --http` writes (nothing is written here)."""
    plan = Plan()
    taken: set[str] = set()
    head = [
        "# guard.toml — sinh bởi `neuroedge guard init --http` (TSK-I2c-15). Cú pháp: docs/spec/extension_sdk.md.",
        "# Mọi route bị CHẶN cho tới khi bạn sửa gate của nó (xem đầu mỗi tệp trong gates/).",
        "[guard]",
        f"name = {_toml(name)}",
        "",
        "[proxy.http]",
        f"upstream = {_toml(upstream)}",
        f"listen = {_toml(listen)}",
        f"id = {_toml(ident)}",
    ]
    if header_env:
        head.append(
            "headers_env = { "
            + ", ".join(f"{h} = {_toml(e)}" for h, e in header_env.items())
            + " }"
        )
    if allow_lan_http:
        head += [LAN_COMMENT, "allow_lan_http = true"]
    tools_toml: list[str] = []
    for method, path in routes:
        segments = [SEGMENT_PARAM.sub(lambda m: m.group(1), s) for s in path.split("/")[1:] if s]
        tool = tool_name_for("_".join([method.lower(), *segments]), taken)
        taken.add(tool)
        route = Route(method, path, tool)
        head += [
            "",
            "[[proxy.http.routes]]",
            f"method = {_toml(method)}",
            f"path = {_toml(path)}",
            f"tool = {_toml(tool)}",
        ]
        block = [f"[tools.{tool}]", f'gate = "gates/{tool}@1.0.0.yaml"']
        for param in route.params:
            block += ["", f"[tools.{tool}.parameters.{param}]", 'type = "string"']
        block.append(
            f"# query and body fields: declare each as [tools.{tool}.parameters.<name>] to accept it"
        )
        tools_toml.append("\n".join(block) + "\n")
        plan.exposed.append(tool)
        plan.files[base / "gates" / f"{tool}@1.0.0.yaml"] = http_gate_text(
            tool, route, f"bridge:{ident}"
        )
    plan.files[base / "guard.toml"] = "\n".join(head) + "\n\n" + "\n".join(tools_toml)
    return plan


def init(
    upstream: str,
    routes: list[str],
    directory: Path,
    name: str | None = None,
    header_env: list[str] | None = None,
    allow_lan_http: bool = False,
) -> Plan:
    """`neuroedge guard init --http <upstream> --route "METHOD /path"…`: blocking gates, never overwriting."""
    where = "neuroedge guard init --http"
    headers: dict[str, str] = {}
    for item in header_env or []:
        header, _, var = item.partition("=")
        headers[header] = var
    if not routes:
        raise NeuroEdgeError(
            where=where, why="no route given", how='add --route "POST /cm/{cmd}" (repeatable)'
        )
    parsed = [parse_route(r) for r in routes]
    if name is not None and not NAME.fullmatch(name):
        raise NeuroEdgeError(
            where=where, why=f"{name!r} is not a guard name", how="use letters, digits, _ . -"
        )
    base = directory.resolve()
    plan = plan_http(
        check_upstream_for_init(upstream, headers, allow_lan_http), parsed, base,
        name or _default_name(upstream), header_env=headers, allow_lan_http=allow_lan_http,
    )  # fmt: skip
    validate_plan_http(plan, base)
    write_plan(plan)
    return plan


def check_upstream_for_init(
    upstream: str, headers: dict[str, str], allow_lan_http: bool = False
) -> str:
    url = check_upstream(upstream, "<guard init> --http", allow_lan_http)
    for header, var in headers.items():
        if not HEADER.fullmatch(header) or not ENV_NAME.fullmatch(var):
            raise _bad(
                "<guard init> --header-env",
                "write HEADER=ENVVAR: a header name and the NAME of an environment variable",
                "e.g. --header-env Authorization=DEVICE_TOKEN",
            )
    return url


def _default_name(upstream: str) -> str:
    from .proxy_mcp import Upstream

    return default_name(Upstream(url=upstream))


def validate_plan_http(plan: Plan, base: Path) -> None:
    """The written files load: guard.toml parses, `[proxy.http]` checks, gates resolve, a Guard builds."""
    validate_plan(plan, base)
    import tempfile

    with tempfile.TemporaryDirectory(prefix="guard-init-http-") as scratch:
        root = Path(scratch)
        for path, text in plan.files.items():
            target = root / path.relative_to(base)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
        parse_http(load_config(root / "guard.toml"))


# --- doctor ---------------------------------------------------------------------------------------


def doctor(config: GuardConfig) -> list[Finding]:
    """The `plugin doctor` findings for a `[proxy.http]` guard: what it saw, and what it cannot check."""
    proxy = parse_http(config)
    findings: list[Finding] = []
    if proxy.allow_lan_http:
        findings.append(lan_warning(proxy.upstream))
    if reachable(proxy, 2.0) is None:
        findings.append(
            Finding(
                "warning",
                f"đích còn tới được mà không qua proxy: {proxy.upstream} nhận kết nối TCP trực tiếp từ "
                "máy này — và với một API cục bộ thì luôn như vậy. Proxy chỉ canh con đường đi qua nó: "
                "người vận hành phải đặt API của thiết bị sau tường lửa/ACL hoặc bind chỉ cho proxy "
                "(vd. thiết bị chỉ nhận từ địa chỉ của máy proxy), nếu không bất kỳ máy nào trong "
                "mạng gọi thẳng được và gate chỉ để trang trí",
            )
        )
    else:
        findings.append(
            Finding(
                "unverifiable",
                f"không kiểm được: đích {proxy.upstream} không tới được từ máy này — máy khác trong mạng "
                "thì chưa biết; hãy chặn ở tường lửa/ACL để chỉ proxy tới được",
            )
        )
    findings.append(
        Finding(
            "unverifiable",
            "không kiểm được: ứng dụng, script hay thiết bị khác trong mạng gọi thẳng API (doctor không "
            "quét mạng và không đọc tường lửa)",
        )
    )
    gates = resolve_gates(config)
    for route in proxy.routes:
        criteria = set(gates[route.tool].constraints)
        if not criteria & {"call_source", "call_channel"}:
            findings.append(
                Finding(
                    "warning",
                    f"gate của tool `{route.tool}` ({route.method} {route.path}) không đọc "
                    "call_source/call_channel: mọi nguồn đi qua nó như nhau (RFC-0016 §5 rủi ro 8)",
                )
            )
    findings.append(Finding("unverifiable", "không kiểm được: plugin (TSK-I2c-11)"))
    return findings
