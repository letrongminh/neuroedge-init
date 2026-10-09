"""
`neuroedge proxy mcp` — an MCP server that already exists, put behind NeuroEdge (TSK-I2c-14).

    MCP client ──tools/call──► proxy ──► Guard: gate ─► token ─► envelope ─► trace
                                                 │ ALLOW only
                                                 ▼
                                   the tool's `run`: forward to the real server

The real server (Home Assistant's MCP server, any stdio MCP server) is reached **only inside the
`run` of a tool of a `neuroedge.guard.Guard`**, i.e. after the gate said ALLOW: there is no "if
allowed, forward" for anyone to write wrongly. The call keeps the source of the client in front,
`mcp`, through the Guard's internal front path (RFC-0016 §3b item 4); a bridge can never get it.

Three commands put a server behind it (RFC-0016, FR-EXT-06):

    pip install 'neuroedge[mcp]'
    neuroedge guard init --mcp "python my_server.py"      # connect, list tools, write guard.toml + gates
    neuroedge proxy mcp                                   # serve those tools over stdio, gated

What it cannot do, and says so (`neuroedge plugin doctor`): it guards the road that goes through
it. A server that still listens, or a second client entry that still launches it, is a road
around it (RFC-0016 §5 risk 3).

Configuration is the `[proxy.mcp]` table of `guard.toml`; the generated gates block every tool
until the operator edits them on purpose. The grammar is in `docs/spec/extension_sdk.md` §4.
"""

from __future__ import annotations

import asyncio
import ipaddress
import json
import os
import re
import shlex
import socket
import sys
import tempfile
from collections.abc import AsyncIterator, Iterator, Mapping, Sequence
from contextlib import AsyncExitStack, asynccontextmanager, suppress
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from .errors import AgentManifestError, NeuroEdgeError
from .guard import Guard, GuardConfig, Tool, load_config, resolve_gates
from .mcp_server import _sdk
from .models.providers.common import ENV_NAME, NAME, SECRET, looks_like_key, refuse_unknown
from .sdk import ToolRequest

WHERE = "neuroedge proxy mcp"
TIMEOUT_S = 30.0
CONNECT_TIMEOUT_S = 20.0
SCALARS = ("string", "integer", "number", "boolean")
HEADER = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,63}")
UPSTREAM_NAME = re.compile(r"[^\s\x00-\x1f]{1,128}")
LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1")


class UpstreamFailed(Exception):
    """The real server failed while answering a call the gate had allowed. Never retried."""


# --- [proxy.mcp] ----------------------------------------------------------------------------------


@dataclass(frozen=True)
class Upstream:
    """`[proxy.mcp]`: where the real server is, and how the proxy names its tools."""

    command: tuple[str, ...] = ()
    url: str = ""
    env_from: tuple[str, ...] = ()
    headers_env: Mapping[str, str] = field(default_factory=dict)
    names: Mapping[str, str] = field(default_factory=dict)
    # Opt-in: plain http to a host on the home LAN (see `refuse_plain_http`).
    allow_lan_http: bool = False

    def upstream_name(self, tool: str) -> str:
        return self.names.get(tool, tool)

    @property
    def kind(self) -> str:
        return "stdio" if self.command else "http"


LAN_NAME_SUFFIXES = (".local", ".lan", ".home.arpa")
_LAN_V4 = tuple(
    ipaddress.ip_network(n)
    for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "169.254.0.0/16", "127.0.0.0/8")
)
_LAN_V6 = tuple(ipaddress.ip_network(n) for n in ("fc00::/7", "fe80::/10", "::1/128"))


def lan_host(host: str) -> bool:
    """
    A host plain http may go to when the operator opted in (`allow_lan_http`): an IP literal in
    RFC 1918, link-local or loopback space (IPv6: fc00::/7, fe80::/10, ::1) — never the carrier-grade
    NAT range 100.64.0.0/10, never an IPv4-mapped IPv6 address — or a `*.local`, `*.lan`,
    `*.home.arpa` name with at least one label before the suffix. Any other host, a public name
    included, is not LAN: the answer is no.
    """
    host = host.strip("[]").split("%", 1)[0].rstrip(".").lower()
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return any(
            host.endswith(suffix) and len(host) > len(suffix) for suffix in LAN_NAME_SUFFIXES
        )
    networks = _LAN_V4 if address.version == 4 else _LAN_V6
    return any(address in network for network in networks)


def refuse_plain_http(host: str, allow_lan: bool, where: str, key: str = "url") -> None:
    """
    Plain http is for loopback; with `allow_lan_http = true`, for a LAN host too (`lan_host`). Anything
    else is refused, flag or not: a token must not cross the internet in clear.
    """
    if host in LOCAL_HOSTS or host.lower() == "localhost":
        return
    if allow_lan and lan_host(host):
        return
    if lan_host(host):
        raise _bad(
            f"{where} {key}",
            "plain http to another machine on the LAN sends the calls and the token in clear",
            "use https, or — if that is the device you have — set allow_lan_http = true (the "
            "credentials and calls then travel unencrypted on your LAN; `plugin doctor` warns)",
        )
    raise _bad(
        f"{where} {key}",
        "plain http to a host outside loopback and the home LAN would send the token in clear "
        "over the internet; allow_lan_http does not cover it either",
        "use https (a LAN host needs allow_lan_http = true: a private IP literal, or a *.local, "
        "*.lan or *.home.arpa name)",
    )


LAN_COMMENT = "# allow_lan_http: plain http to a host on the home LAN. Calls and the token travel UNENCRYPTED on the LAN."


def lan_warning(url: str) -> Finding:
    """The `plugin doctor` warning for `allow_lan_http = true` (both proxies)."""
    return Finding(
        "warning",
        f"allow_lan_http đang bật: lời gọi và thông tin đăng nhập tới {urlsplit(url).netloc} đi bằng http "
        "THUẦN trên LAN — ai nghe được mạng nhà (Wi-Fi, thiết bị bị chiếm) đọc và chép lại được token. "
        "Chỉ chấp nhận cho mạng nhà tin cậy; dùng https nếu thiết bị hỗ trợ",
    )


def lan_flag(table: Mapping[str, Any], where: str) -> bool:
    value = table.get("allow_lan_http", False)
    if not isinstance(value, bool):
        raise _bad(where + " allow_lan_http", "`allow_lan_http` is true or false", "x")
    return value


def _bad(where: str, why: str, how: str) -> AgentManifestError:
    return AgentManifestError(where=where, why=why, how=how)


def parse_upstream(config: GuardConfig) -> Upstream:
    """
    `[proxy.mcp]` of a loaded guard.toml, or `AgentManifestError` (NE3002, three parts). Exactly one
    of `command` / `url`; secrets only by the NAME of an environment variable; a literal secret is
    refused without being repeated.
    """
    where = f"{config.source} [proxy.mcp]"
    refuse_unknown(
        config.proxy, config.source, "proxy", ("mcp", "http"),
        "[proxy] has mcp (`proxy mcp`) or http (`proxy http`), exactly one of them",
    )  # fmt: skip
    if "http" in config.proxy and "mcp" in config.proxy:
        raise _bad(
            f"{config.source} [proxy]",
            "both [proxy.mcp] and [proxy.http] are given; a guard.toml fronts one kind of server",
            "keep one of them, in separate directories if you need both",
        )
    table = config.proxy.get("mcp")
    if not isinstance(table, dict):
        raise _bad(
            where,
            "this guard.toml has no [proxy.mcp] table: there is nothing to put `proxy mcp` in "
            "front of"
            + (" (it has [proxy.http]: use `proxy http`)" if "http" in config.proxy else ""),
            "run `neuroedge guard init --mcp <command or url>`, or add [proxy.mcp]",
        )
    refuse_unknown(
        table, where, "proxy.mcp", ("command", "url", "env_from", "headers_env", "names", "allow_lan_http"),
        "[proxy.mcp] has command or url, env_from, headers_env, names and allow_lan_http",
    )  # fmt: skip
    command, url = table.get("command"), table.get("url")
    if (command is None) == (url is None):
        raise _bad(where, "give exactly one of `command` (stdio) and `url` (Streamable HTTP)", "x")
    if command is not None:
        if (
            not isinstance(command, list)
            or not command
            or not all(isinstance(a, str) and a for a in command)
        ):
            raise _bad(where + " command", "`command` is a non-empty list of strings", "x")
        if any(looks_like_key(a) for a in command):
            raise _bad(
                where + " command",
                "an argument looks like a secret; the file is committed and shared",
                "pass secrets through `env_from` (the NAME of an environment variable)",
            )
    allow_lan = lan_flag(table, where)
    if allow_lan and url is None:
        raise _bad(where + " allow_lan_http", "`allow_lan_http` is for a `url`", "remove it")
    if url is not None:
        _check_url(url, where, allow_lan)
    env_from = table.get("env_from", [])
    if not isinstance(env_from, list) or not all(
        isinstance(n, str) and ENV_NAME.fullmatch(n) for n in env_from
    ):
        raise _bad(
            where + " env_from",
            "`env_from` lists the NAMES of environment variables (letters, digits, _)",
            "never write a value there",
        )
    if env_from and command is None:
        raise _bad(where + " env_from", "`env_from` is for a stdio `command`", "use headers_env")
    headers = table.get("headers_env", {})
    if not isinstance(headers, dict) or not all(
        isinstance(h, str) and HEADER.fullmatch(h) and isinstance(v, str) and ENV_NAME.fullmatch(v)
        for h, v in headers.items()
    ):
        # Never repeat a value: a pasted `Bearer …` is a live token.
        raise _bad(
            where + " headers_env",
            "`headers_env` maps a header name to the NAME of an environment variable "
            "(letters, digits, _); a value that is not such a name is refused — if it was the "
            "token itself, revoke it",
            'write headers_env = { Authorization = "HA_TOKEN" } and export HA_TOKEN',
        )
    if headers and url is None:
        raise _bad(where + " headers_env", "`headers_env` is for a `url`", "use env_from")
    names = table.get("names", {})
    if not isinstance(names, dict) or not all(
        isinstance(k, str) and isinstance(v, str) and UPSTREAM_NAME.fullmatch(v)
        for k, v in names.items()
    ):
        raise _bad(
            where + " names", "`names` maps a guard tool name to the upstream tool's name", "x"
        )
    known = {tool.name for tool in config.tools}
    stray = sorted(set(names) - known)
    if stray:
        raise _bad(
            where + " names",
            f"{stray} are not tools of this guard.toml",
            "rename the key to a [tools.<name>], or remove it",
        )
    return Upstream(
        tuple(command or ()), url or "", tuple(env_from), dict(headers), dict(names), allow_lan
    )


def _check_url(url: Any, where: str, allow_lan: bool = False) -> None:
    if not isinstance(url, str):
        raise _bad(where + " url", "`url` is a string", "x")
    parts = urlsplit(url)
    host = parts.hostname or ""
    if parts.scheme not in ("http", "https") or not host:
        raise _bad(where + " url", "`url` is an http(s) URL", "x")
    if parts.username or parts.password:
        raise _bad(
            where + " url",
            "the URL carries credentials; the file is committed and shared",
            "use headers_env for a token",
        )
    if any(SECRET.search(k) for k, _ in _query(parts.query)):
        raise _bad(
            where + " url",
            "the query string carries a secret-named parameter",
            "use headers_env for a token",
        )
    if parts.scheme == "http":
        refuse_plain_http(host, allow_lan, where)


def _query(query: str) -> Iterator[tuple[str, str]]:
    for pair in query.split("&"):
        if pair:
            key, _, value = pair.partition("=")
            yield key, value


# --- the upstream connection ----------------------------------------------------------------------


def _reason(exc: BaseException) -> str:
    while isinstance(exc, BaseExceptionGroup) and exc.exceptions:
        exc = exc.exceptions[0]
    return f"{type(exc).__name__}: {exc}"[:240]


def describe(up: Upstream) -> str:
    """The upstream for people and the trace: never an argument, never a query."""
    if up.command:
        return f"stdio: {Path(up.command[0]).name}"
    parts = urlsplit(up.url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


@asynccontextmanager
async def open_upstream(up: Upstream, base: Path, where: str = WHERE) -> AsyncIterator[Any]:
    """
    An MCP client session to the real server. The headers and the child's environment come from
    the environment variables the config names; one that is not set refuses the connection.
    Any failure to connect is a three-part `NeuroEdgeError`.
    """
    _sdk()
    from mcp import Client, StdioServerParameters

    def need(names: Sequence[str]) -> dict[str, str]:
        missing = [n for n in names if n not in os.environ]
        if missing:
            raise NeuroEdgeError(
                where=f"{where} -> upstream",
                why=f"environment variable(s) {missing} named in guard.toml are not set",
                how=f"export {missing[0]}=… in the shell that runs this command",
            )
        return {n: os.environ[n] for n in names}

    async with AsyncExitStack() as stack:
        try:
            if up.command:
                command = (
                    sys.executable if up.command[0] in ("python", "python3") else up.command[0]
                )
                args = [str(base / a) if (base / a).is_file() else a for a in up.command[1:]]
                env = need(up.env_from)
                transport: Any = StdioServerParameters(
                    command=command, args=args, env=env or None, cwd=str(base)
                )
            else:
                import httpx2
                from mcp.client.streamable_http import streamable_http_client

                values = need(list(up.headers_env.values()))
                headers = {h: values[e] for h, e in up.headers_env.items()}
                http = await stack.enter_async_context(
                    httpx2.AsyncClient(headers=headers, timeout=TIMEOUT_S)
                )
                transport = streamable_http_client(up.url, http_client=http)
            # `asyncio.timeout`, not `wait_for`: on Python 3.11 `wait_for` runs the coroutine in a
            # task of its own, so the client's cancel scope would be entered there and left here.
            async with asyncio.timeout(CONNECT_TIMEOUT_S):
                client = await stack.enter_async_context(
                    Client(transport, read_timeout_seconds=TIMEOUT_S)
                )
        except NeuroEdgeError:
            raise
        except BaseException as exc:
            if not isinstance(exc, Exception):
                raise
            raise NeuroEdgeError(
                where=f"{where} -> upstream {describe(up)}",
                why=f"cannot connect to the real MCP server: {_reason(exc)}",
                how="start it (or fix the command or url in [proxy.mcp]) and run again; the "
                "proxy never serves a partial set of tools",
            ) from None
        yield client


async def list_upstream(client: Any) -> dict[str, Any]:
    """Every tool the upstream lists, by name (all pages)."""
    tools: dict[str, Any] = {}
    cursor = None
    while True:
        page = await client.list_tools(cursor=cursor) if cursor else await client.list_tools()
        tools.update({tool.name: tool for tool in page.tools})
        cursor = getattr(page, "next_cursor", None)
        if not cursor:
            return tools


def scalar_type(prop: Mapping[str, Any]) -> str | None:
    """`string` / `integer` / `number` / `boolean` for a property, `Optional[scalar]` included."""
    kind = prop.get("type")
    if isinstance(kind, str):
        return kind if kind in SCALARS else None
    branches = prop.get("anyOf")
    if isinstance(branches, list):
        kinds = [b.get("type") for b in branches if isinstance(b, dict) and b.get("type") != "null"]
        if len(kinds) == 1 and kinds[0] in SCALARS:
            return str(kinds[0])
    return None


def incompatibilities(tool: Tool, upstream_name: str, listed: Mapping[str, Any]) -> list[str]:
    """Why the guard's tool does not fit the upstream's tool of that name (empty: it fits)."""
    found = listed.get(upstream_name)
    if found is None:
        return [f"the upstream has no tool {upstream_name!r}; it lists {sorted(listed)}"]
    schema = found.input_schema or {}
    properties = schema.get("properties") or {}
    problems = []
    for name, declared in tool.parameters.items():
        prop = properties.get(name)
        if prop is None:
            problems.append(f"parameter {name!r} is not a parameter of {upstream_name!r}")
        elif scalar_type(prop) != declared.get("type"):
            problems.append(
                f"parameter {name!r} is {declared.get('type')} here, "
                f"{scalar_type(prop) or 'not a scalar'} upstream"
            )
    for name in schema.get("required") or []:
        if name not in tool.parameters:
            problems.append(
                f"{upstream_name!r} requires {name!r}, which this tool does not declare — "
                "the proxy could never supply it"
            )
    return problems


# --- serving --------------------------------------------------------------------------------------


def _forward(client: Any, upstream_name: str) -> Any:
    async def run(**arguments: Any) -> Any:
        try:
            return await client.call_tool(upstream_name, arguments, read_timeout_seconds=TIMEOUT_S)
        except Exception as exc:
            # After ALLOW the call may have happened; it is told, not retried.
            raise UpstreamFailed(f"{type(exc).__name__}: {exc}"[:240]) from None

    return run


def build_guard(
    config: GuardConfig, up: Upstream, client: Any, listed: Mapping[str, Any], events: Any = None
) -> Guard:
    """
    The `Guard` of the proxy: each tool of guard.toml, its `run` forwarding to the upstream, its
    description the upstream's. A tool that does not fit the upstream refuses the start.
    """
    where = f"{WHERE} -> {config.source}"
    tools, problems = [], []
    for tool in config.tools:
        if tool.requires or tool.drive:
            raise _bad(
                f"{config.source} [tools.{tool.name}]",
                "a proxy tool forwards a call; it holds no pins (`requires`, `drive`)",
                "remove them, or serve the tool with a Guard of its own",
            )
        name = up.upstream_name(tool.name)
        for problem in incompatibilities(tool, name, listed):
            problems.append(f"{tool.name}: {problem}")
        found = listed.get(name)
        tools.append(
            replace(
                tool,
                run=_forward(client, name),
                description=(getattr(found, "description", None) or "") if found else "",
            )
        )
    if not tools:
        problems.append("guard.toml declares no tool")
    if problems:
        raise NeuroEdgeError(
            where=where,
            why="the upstream does not match guard.toml: " + "; ".join(problems),
            how="run `neuroedge guard init --mcp …` again in a new directory and merge, or fix "
            "[tools] / [proxy.mcp.names]; the proxy never serves what is left",
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
    guard.events.metadata["proxy"] = {"kind": "mcp", "upstream": describe(up)}
    return guard


def build_front(guard: Guard) -> Any:
    """The MCP `Server` the client talks to: the guard's tools, each `tools/call` through the Guard."""
    import json as _json

    from . import __version__

    types, Server = _sdk()

    async def list_tools(ctx: Any, params: Any) -> Any:
        return types.ListToolsResult(
            tools=[
                types.Tool(
                    name=tool["name"],
                    description=tool["description"],
                    input_schema=tool["inputSchema"],
                )
                for tool in guard._tools.mcp()
            ]
        )

    async def call_tool(ctx: Any, params: Any) -> Any:
        request = ToolRequest(params.name, dict(params.arguments or {}))
        try:
            result = await guard._dispatch_front(request)
        except UpstreamFailed as failure:
            told = {
                "tool": params.name,
                "status": "ALLOW",
                "problems": [
                    "the gate allowed the call, then the upstream server failed; it was not "
                    f"retried: {failure}"
                ],
            }
            return types.CallToolResult(
                content=[types.TextContent(text=_json.dumps(told, ensure_ascii=False))],
                structured_content=told,
                is_error=True,
            )
        if result.status == "ALLOW":
            upstream = result.action.value if result.action is not None else None
            if upstream is not None:
                return types.CallToolResult(
                    content=list(upstream.content),
                    structured_content=upstream.structured_content,
                    is_error=bool(upstream.is_error),
                )
        content = result.content()
        return types.CallToolResult(
            content=[types.TextContent(text=_json.dumps(content, ensure_ascii=False))],
            structured_content=content,
            is_error=result.status == "REJECTED",
        )

    return Server(
        f"neuroedge-proxy:{guard.config.name}",
        version=__version__,
        instructions=(
            "Each tool is forwarded to another MCP server only if a NeuroEdge safety gate "
            "allows the call. A BLOCK result says why; nothing was forwarded."
        ),
        on_list_tools=list_tools,
        on_call_tool=call_tool,
    )


async def prepare(config_path: Path, events: Any = None) -> tuple[Guard, AsyncExitStack]:
    """
    Everything `serve` needs, or a refusal: the config, the upstream connected and checked, the
    Guard built. The caller closes the stack (the upstream) and the guard.
    """
    config = load_config(config_path)
    up = parse_upstream(config)
    stack = AsyncExitStack()
    try:
        client = await stack.enter_async_context(open_upstream(up, config.base or Path.cwd()))
        try:
            listed = await list_upstream(client)
        except Exception as exc:
            raise NeuroEdgeError(
                where=f"{WHERE} -> upstream {describe(up)}",
                why=f"the upstream did not list its tools: {_reason(exc)}",
                how="check the server, then run again",
            ) from None
        guard = build_guard(config, up, client, listed, events)
    except BaseException:
        await stack.aclose()
        raise
    return guard, stack


async def serve(config_path: Path, *, trace_out: Path | None = None, on_ready: Any = None) -> None:
    """Serve the proxy over stdio until the client closes it; write the trace on the way out."""
    from mcp.server.stdio import stdio_server

    guard, stack = await prepare(config_path)
    try:
        server = build_front(guard)
        if on_ready is not None:
            on_ready(guard)
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())
    finally:
        try:
            if trace_out is not None:
                trace_out.write_text(
                    json.dumps(guard.trace(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
                )
        finally:
            guard.close()
            with suppress(BaseException):
                await stack.aclose()


# --- guard init -----------------------------------------------------------------------------------


def parse_target(spec: str) -> tuple[tuple[str, ...], str]:
    """`--mcp` value: a URL (http/https), or a command line split like a shell would."""
    spec = spec.strip()
    if re.match(r"https?://", spec):
        return (), spec
    try:
        words = tuple(shlex.split(spec))
    except ValueError as problem:
        raise NeuroEdgeError(
            where="neuroedge guard init --mcp",
            why=f"cannot read the command: {problem}",
            how='quote it: --mcp "python server.py --flag"',
        ) from None
    if not words:
        raise NeuroEdgeError(
            where="neuroedge guard init --mcp",
            why="an empty command",
            how='give a command ("python server.py") or an https URL',
        )
    # A script named relative to where this runs is written absolute: the proxy starts the server
    # from guard.toml's directory, which is not necessarily here.
    # (abspath, not resolve: a venv's python is a symlink, and resolving it leaves the venv)
    resolved = tuple(os.path.abspath(w) if Path(w).is_file() else w for w in words)
    return resolved, ""


def tool_name_for(upstream_name: str, taken: set[str]) -> str:
    """A guard tool name (`[a-z][a-z0-9_]{0,63}`) for an upstream name, unique among `taken`."""
    name = re.sub(r"[^a-z0-9_]+", "_", upstream_name.lower()).strip("_")
    if not name or not name[0].isalpha():
        name = f"t_{name}".rstrip("_")
    name = name[:60]
    candidate, n = name, 2
    while candidate in taken:
        candidate = f"{name}_{n}"
        n += 1
    return candidate


def default_name(up: Upstream) -> str:
    if up.command:
        words = [w for w in up.command if not w.startswith("-")]
        stem = next(
            (
                Path(w).stem
                for w in words
                if Path(w).stem not in ("python", "python3", "uv", "uvx", "npx")
            ),
            "upstream",
        )
    else:
        stem = urlsplit(up.url).hostname or "upstream"
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", stem).strip("-.") or "upstream"
    return cleaned[:64]


def _toml(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


@dataclass
class Plan:
    """What `guard init` will write, and what it will not expose."""

    files: dict[Path, str] = field(default_factory=dict)
    exposed: list[str] = field(default_factory=list)
    not_exposed: dict[str, str] = field(default_factory=dict)
    dropped: dict[str, list[str]] = field(default_factory=dict)


def gate_text(tool: str, upstream: str, description: str) -> str:
    about = " ".join((description or "").split())[:160]
    return f"""\
# Gate sinh bởi `neuroedge guard init` cho tool `{upstream}` của máy chủ MCP phía sau proxy.
# {about}
#
# MẶC ĐỊNH BỊ CHẶN: `operator_approved` là một tiêu chí không ai đặt (proxy không `set_fact` nó),
# nên mọi lời gọi `BLOCK` với `criterion_unavailable` cho tới khi người vận hành sửa gate này CÓ CHỦ Ý.
#
# Để mở (BY DESIGN you must do this yourself):
#   1. Quyết định ai được gọi tool này: `call_source` ở dưới nói nguồn nào được qua (client MCP
#      phía trước proxy là `mcp`).
#   2. Xoá tiêu chí `operator_approved` ở `evaluate:` VÀ dòng `operator_approved: true` ở `allow_when:`,
#      hoặc thay bằng điều kiện thật của bạn (một dữ kiện bool/choice mà gate nhận được).
#   3. Chạy `neuroedge gate lint gates` rồi `neuroedge plugin doctor`.
# Tool có tác dụng không hoàn tác (mở khoá, bật thiết bị) nên thêm điều kiện, đừng chỉ mở cho `mcp`.
schema:  neuroedge.gate/v1
name:    {tool}
version: 1.0.0

evaluate:
  call_source:
    type: choice
    options: [local_grammar, system_one, system_two, mcp, test]
    instructions: "Nguồn của tool call, do dispatcher đặt (Q-24); client MCP phía trước proxy là mcp"
  operator_approved:
    type: bool
    instructions: "Người vận hành đã mở gate này có chủ ý — không ai đặt dữ kiện này lúc sinh"

allow_when:
  call_source:       {{ in: [mcp] }}
  operator_approved: true

on_block:
  action: deny

budget:
  p95_latency_ms: 150
  fail:           closed
"""


def plan_init(
    up: Upstream, listed: Mapping[str, Any], base: Path, name: str, *, command: str = ""
) -> Plan:
    """The files `guard init` writes for the tools the upstream listed (nothing is written here)."""
    plan = Plan()
    taken: set[str] = set()
    tools_toml: list[str] = []
    mapping: dict[str, str] = {}
    for upstream_name in sorted(listed):
        tool = listed[upstream_name]
        schema = tool.input_schema or {}
        properties = schema.get("properties") or {}
        required = set(schema.get("required") or [])
        blocked = sorted(p for p in required if scalar_type(properties.get(p) or {}) is None)
        if blocked:
            why = (
                f"required parameter(s) {blocked} are not a string, integer, number or boolean — "
                "a guard.toml parameter cannot describe them, so the proxy cannot pass them safely"
            )
            plan.not_exposed[upstream_name] = why
            tools_toml.append(f"# Not exposed — tool {_toml(upstream_name)}: {why}.\n")
            continue
        guard_name = tool_name_for(upstream_name, taken)
        taken.add(guard_name)
        if guard_name != upstream_name:
            mapping[guard_name] = upstream_name
        block = [f"[tools.{guard_name}]", f'gate = "gates/{guard_name}@1.0.0.yaml"']
        dropped = []
        params: list[str] = []
        for pname in sorted(properties):
            prop = properties[pname]
            kind = scalar_type(prop)
            if kind is None or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", pname):
                dropped.append(pname)
                continue
            lines = [f"[tools.{guard_name}.parameters.{pname}]", f'type = "{kind}"']
            default = prop.get("default")
            if default is not None and _is_kind(default, kind):
                lines.append(f"default = {_toml_value(default)}")
            elif pname not in required:
                lines.append("required = false")
            description = " ".join(str(prop.get("description") or "").split())[:200]
            if description:
                lines.append(f"description = {_toml(description)}")
            params.append("\n".join(lines))
        # a required parameter whose name is not a legal guard parameter name cannot be passed on
        illegal = [p for p in dropped if p in required]
        if illegal:
            why = f"required parameter(s) {illegal} have names a guard.toml cannot hold"
            plan.not_exposed[upstream_name] = why
            tools_toml.append(f"# Not exposed — tool {_toml(upstream_name)}: {why}.\n")
            taken.discard(guard_name)
            mapping.pop(guard_name, None)
            continue
        if dropped:
            plan.dropped[upstream_name] = dropped
            block.append(f"# optional parameter(s) not exposed (not scalar): {', '.join(dropped)}")
        tools_toml.append(
            "\n".join(block) + "\n\n" + "\n\n".join(params) + ("\n" if params else "")
        )
        plan.exposed.append(guard_name)
        plan.files[base / "gates" / f"{guard_name}@1.0.0.yaml"] = gate_text(
            guard_name, upstream_name, tool.description or ""
        )
    head = [
        "# guard.toml — sinh bởi `neuroedge guard init --mcp` (TSK-I2c-14). Cú pháp: docs/spec/extension_sdk.md.",
        "# Mọi tool bị CHẶN cho tới khi bạn sửa gate của nó (xem đầu mỗi tệp trong gates/).",
        "[guard]",
        f"name = {_toml(name)}",
        "",
        "[proxy.mcp]",
    ]
    if up.command:
        head.append("command = [" + ", ".join(_toml(w) for w in up.command) + "]")
        if up.env_from:
            head.append("env_from = [" + ", ".join(_toml(n) for n in up.env_from) + "]")
    else:
        head.append(f"url = {_toml(up.url)}")
        if up.headers_env:
            head.append(
                "headers_env = { "
                + ", ".join(f"{h} = {_toml(e)}" for h, e in up.headers_env.items())
                + " }"
            )
        if up.allow_lan_http:
            head.append(LAN_COMMENT)
            head.append("allow_lan_http = true")
    if mapping:
        head += ["", "[proxy.mcp.names]"] + [
            f"{g} = {_toml(u)}" for g, u in sorted(mapping.items())
        ]
    plan.files[base / "guard.toml"] = "\n".join(head) + "\n\n" + "\n".join(tools_toml)
    return plan


def _is_kind(value: Any, kind: str) -> bool:
    if kind == "boolean":
        return isinstance(value, bool)
    if isinstance(value, bool):
        return False
    return {"integer": isinstance(value, int), "number": isinstance(value, int | float)}.get(
        kind, isinstance(value, str)
    )


def _toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return _toml(value)
    return repr(value)


def validate_plan(plan: Plan, base: Path) -> None:
    """The generated files, as written, load as a Guard and resolve as gates — checked in a scratch copy."""
    with tempfile.TemporaryDirectory(prefix="guard-init-") as scratch:
        root = Path(scratch)
        for path, text in plan.files.items():
            target = root / path.relative_to(base)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
        config = load_config(root / "guard.toml")
        resolve_gates(config)
        Guard(
            config.tools, name=config.name, board=config.board, base=config.base,
            registry_root=config.registry_root, source=config.source,
        ).close()  # fmt: skip


def write_plan(plan: Plan) -> None:
    """Write every file, never over an existing one: all are checked first, then created exclusively."""
    existing = sorted(str(p) for p in plan.files if p.exists())
    if existing:
        raise NeuroEdgeError(
            where="neuroedge guard init",
            why=f"{existing[0]} already exists"
            + (f" (and {len(existing) - 1} more)" if len(existing) > 1 else ""),
            how="use a new directory (--dir), or move the old files aside; nothing was written",
        )
    for path, text in plan.files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(path, "x", encoding="utf-8") as out:
                out.write(text)
        except FileExistsError:
            raise NeuroEdgeError(
                where="neuroedge guard init",
                why=f"{path} appeared while writing",
                how="run again in a clean directory",
            ) from None


async def init(
    spec: str,
    directory: Path,
    name: str | None = None,
    env_from: Sequence[str] = (),
    header_env: Sequence[str] = (),
    allow_lan_http: bool = False,
) -> Plan:
    """
    `neuroedge guard init --mcp <command|url>`: connect, list the upstream's tools, write
    `guard.toml` and one blocking gate per tool. See the module docstring.
    """
    command, url = parse_target(spec)
    headers: dict[str, str] = {}
    for item in header_env:
        header, _, var = item.partition("=")
        headers[header] = var
    if name is not None and not NAME.fullmatch(name):
        raise NeuroEdgeError(
            where="neuroedge guard init --name",
            why=f"{name!r} is not a guard name",
            how="use letters, digits, _ . -",
        )
    # The same checks the proxy applies to the file this writes.
    shell = GuardConfig(
        "init", (), source="<guard init>",
        proxy={"mcp": {k: v for k, v in (
            ("command", list(command) or None), ("url", url or None),
            ("env_from", list(env_from) or None), ("headers_env", headers or None),
            ("allow_lan_http", True if allow_lan_http else None)) if v}},
    )  # fmt: skip
    probe = parse_upstream(shell)
    async with open_upstream(probe, Path.cwd(), "neuroedge guard init") as client:
        listed = await list_upstream(client)
    if not listed:
        raise NeuroEdgeError(
            where=f"neuroedge guard init -> upstream {describe(probe)}",
            why="the server lists no tools",
            how="check that it is the right server",
        )
    base = directory.resolve()
    plan = plan_init(probe, listed, base, name or default_name(probe))
    if not plan.exposed:
        raise NeuroEdgeError(
            where="neuroedge guard init",
            why="no tool of the server can be exposed: "
            + "; ".join(f"{t}: {w}" for t, w in plan.not_exposed.items()),
            how="the proxy takes tools whose required parameters are scalar",
        )
    validate_plan(plan, base)
    write_plan(plan)
    return plan


# --- doctor ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Finding:
    level: str  # "warning" | "info" | "unverifiable"
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"level": self.level, "message": self.message}


def _program(path: str) -> str:
    """The program of an argv[0] by its name; every `python`, `python3`, `python3.13` is one."""
    name = Path(path).name
    return "python" if re.fullmatch(r"python[0-9.]*(\.exe)?", name) else name


def _argv_contains(entry: Sequence[str], upstream: Sequence[str]) -> bool:
    """Does `entry` launch the upstream: its argv holds the upstream's, program by name."""
    if not upstream or len(entry) < len(upstream):
        return False
    wanted = [_program(upstream[0]), *upstream[1:]]
    for start in range(len(entry) - len(upstream) + 1):
        window = [_program(entry[start]), *entry[start + 1 : start + len(upstream)]]
        if window == wanted:
            return True
    return False


def doctor(config_path: Path, *, desktop_config: Path | None = None) -> list[Finding]:
    """
    What `plugin doctor` can and cannot say about "the proxy is the only road" (RFC-0016 §3d
    item 6, §5 risk 3). A warning is something found; "unverifiable" is something it cannot check
    — never a bare OK.
    """
    config = load_config(config_path)
    if "http" in config.proxy:
        from .proxy_http import doctor as doctor_http

        return doctor_http(config)
    up = parse_upstream(config)
    findings: list[Finding] = []
    if up.url and up.allow_lan_http:
        findings.append(lan_warning(up.url))
    if up.url:
        findings += _reach(up)
    else:
        findings += _desktop(up, config_path, desktop_config)
    gates = resolve_gates(config)
    for tool in config.tools:
        criteria = set(gates[tool.name].constraints)
        if not criteria & {"call_source", "call_channel"}:
            findings.append(
                Finding(
                    "warning",
                    f"gate của tool `{tool.name}` không đọc call_source/call_channel: mọi nguồn "
                    "đi qua nó như nhau (RFC-0016 §5 rủi ro 8)",
                )
            )
    findings.append(Finding("unverifiable", "không kiểm được: plugin (TSK-I2c-11)"))
    return findings


def _reach(up: Upstream) -> list[Finding]:
    parts = urlsplit(up.url)
    port = parts.port or (443 if parts.scheme == "https" else 80)
    try:
        with socket.create_connection((parts.hostname or "", port), timeout=2.0):
            pass
    except OSError as problem:
        return [
            Finding(
                "unverifiable",
                f"không kiểm được: đích {describe(up)} không tới được từ máy này ({type(problem).__name__}) — "
                "máy khác trong mạng thì chưa biết; hãy chặn ở tường lửa/ACL để chỉ proxy tới được",
            )
        ]
    return [
        Finding(
            "warning",
            f"đích còn tới được mà không qua proxy: {describe(up)} nhận kết nối TCP trực tiếp từ máy này. "
            "Proxy chỉ canh con đường đi qua nó; client nào gọi thẳng đích thì gate chỉ để trang trí "
            "— đặt đích sau tường lửa/ACL, chỉ cho proxy tới",
        )
    ]


def _desktop(up: Upstream, config_path: Path, desktop_config: Path | None) -> list[Finding]:
    from .mcp_desktop import default_config_path

    path = desktop_config or default_config_path()
    more = Finding(
        "unverifiable",
        "không kiểm được: ứng dụng khác (Cursor, VS Code, shell, script) có thể chạy cùng lệnh "
        f"`{Path(up.command[0]).name}` — chỉ đọc được cấu hình Claude Desktop",
    )
    try:
        servers = json.loads(path.read_text(encoding="utf-8")).get("mcpServers", {})
        if not isinstance(servers, dict):
            raise ValueError("`mcpServers` is not an object")
    except (OSError, ValueError) as problem:
        return [
            Finding(
                "unverifiable",
                f"không kiểm được: không đọc được cấu hình Claude Desktop ({path}): {problem}",
            ),
            more,
        ]
    found = []
    for key, entry in servers.items():
        if not isinstance(entry, dict):
            continue
        argv = [str(entry.get("command", "")), *map(str, entry.get("args") or [])]
        if "proxy" in argv and "mcp" in argv:
            continue  # a proxy entry, ours or another's
        if _argv_contains(argv, up.command):
            found.append(key)
    if found:
        return [
            Finding(
                "warning",
                f"đích còn tới được mà không qua proxy: mục `{k}` trong cấu hình Claude Desktop "
                "vẫn khởi chạy chính máy chủ đó — Claude gọi thẳng, không qua gate"
                " (đổi mục đó sang `neuroedge proxy mcp --desktop-config --write`)",
            )
            for k in found
        ] + [more]
    return [
        Finding(
            "info", f"cấu hình Claude Desktop ({path}) không có mục nào khác chạy cùng máy chủ"
        ),
        more,
    ]
