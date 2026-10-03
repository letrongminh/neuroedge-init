"""
The agent as a gated MCP server **over the network**: `neuroedge mcp serve --http`
(TSK-P2-04, Q-58, Q-32, NFR-SEC-04, NFR-SEC-09).

It is the stdio server of `mcp_server` behind a different door, never a second road to
hardware: the same `build_server`, the same `SimSession.call_tool`, the same gate, verdict
token and trace; `call_source` is the same ``mcp`` (docs/spec/tool_calling.md §5, §8). What
this module adds is the door, and the door fails closed:

* **Complete configuration or no start.** The TLS certificate and key, the client CA (mTLS),
  and the OAuth issuer, audience and signing keys must all be given and loadable.
  `prepare` checks them before any socket is bound or any session is wired (a three-part
  `NeuroEdgeError`); there is no flag that serves with less.
* **mTLS, TLS 1.3 at least.** A client without a certificate the client CA signed never
  completes the handshake, so nothing reaches HTTP.
* **A bearer token per device**, validated as an OAuth 2.1 resource server (RFC 9068, 8707):
  signature against the issuer's public keys (`--jwks`), `iss`, `aud` (this server's own URL),
  `exp`, the required scope, and **bound to the client certificate** (RFC 8705, `cnf.x5t#S256`),
  so a stolen token is useless without its device's key. A request that fails any of these gets
  401 (403 for a missing scope) and nothing is dispatched; it is recorded as `mcp_auth_refused`
  (tool_calling.md §7), never with the token.

The MCP SDK supplies the Streamable HTTP app, the bearer middleware and the protected-resource
metadata (RFC 9728); this module supplies the `TokenVerifier`, the TLS context and the guard
around them. Needs the `mcp` extra only: Starlette, uvicorn, PyJWT and `cryptography` are
dependencies of the SDK, imported here on first use.
"""

from __future__ import annotations

import base64
import contextlib
import contextvars
import hashlib
import hmac
import ipaddress
import json
import socket
import ssl
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .errors import NeuroEdgeError
from .mcp_server import build_server

WHERE = "neuroedge mcp serve --http"
DEFAULT_PORT = 8443
DEFAULT_SCOPE = "neuroedge:call"
# Asymmetric only. A resource server never needs to *sign* a token, so it must never hold a key
# that can: HS* (a shared secret) and `none` are not in this list, and a symmetric or private
# key in the key file is refused at startup.
SIGNING_ALGORITHMS = (
    "RS256",
    "RS384",
    "RS512",
    "PS256",
    "PS384",
    "PS512",
    "ES256",
    "ES384",
    "ES512",
    "EdDSA",
)
# The trace keeps the first refusals; a client that holds a valid certificate and hammers the
# port must not grow the log of a long-running server without bound.
MAX_REFUSALS_TRACED = 10_000
PEER_KEY = "neuroedge.peer_cert_sha256"

# What `_Guard` hands the verifier for the request being served, and what it hands back.
_peer: contextvars.ContextVar[str | None] = contextvars.ContextVar("neuroedge_peer", default=None)
_refusal: contextvars.ContextVar[_Refusal | None] = contextvars.ContextVar(
    "neuroedge_refusal", default=None
)


@dataclass
class _Refusal:
    reason: str = ""
    subject: str | None = None


class Refused(Exception):
    """A token that does not pass. `reason` is a word of `mcp_auth_refused`, never the token."""

    def __init__(self, reason: str, subject: str | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.subject = subject


@dataclass(frozen=True)
class HttpConfig:
    """What `--http` takes. Every field after `port` has no default on purpose: see `prepare`."""

    host: str = "127.0.0.1"
    port: int = DEFAULT_PORT
    tls_cert: Path | None = None
    tls_key: Path | None = None
    client_ca: Path | None = None
    issuer: str | None = None
    audience: str | None = None
    jwks: Path | None = None
    required_scope: str = DEFAULT_SCOPE


_REQUIRED = (
    ("tls_cert", "--tls-cert", "the server certificate (PEM)"),
    ("tls_key", "--tls-key", "its private key (PEM, not encrypted)"),
    ("client_ca", "--client-ca", "the CA that signs the devices' client certificates (mTLS)"),
    ("issuer", "--issuer", "the OAuth authorization server's issuer URL (https)"),
    ("audience", "--audience", "this server's own MCP URL, the token audience (https)"),
    ("jwks", "--jwks", "the issuer's public signing keys (JWKS file)"),
)


@dataclass
class Prepared:
    """A configuration that passed `prepare`: the TLS context and the token verifier."""

    config: HttpConfig
    tls: ssl.SSLContext
    verifier: DeviceTokenVerifier
    path: str = "/mcp"
    refusals: int = field(default=0, init=False)


def _error(why: str, how: str, where: str = WHERE) -> NeuroEdgeError:
    return NeuroEdgeError(where=where, why=why, how=how)


def _https_url(value: str, flag: str, *, with_path: bool) -> str:
    parts = urlsplit(value)
    if parts.scheme != "https" or not parts.hostname or parts.fragment or parts.query:
        raise _error(
            f"{flag} is {value!r}: it must be an absolute https URL without query or fragment",
            f"pass {flag} https://host[:port]{'/mcp' if with_path else ''}",
            f"{WHERE} ({flag})",
        )
    return value


def _is_loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host.strip("[]")).is_loopback
    except ValueError:
        return False


def prepare(config: HttpConfig) -> Prepared:
    """
    Check a configuration completely, and build what serving needs from it.

    Raises `NeuroEdgeError` (three parts) for anything missing or unusable. It runs before the
    session is wired and before any socket exists, so a half-configured network transport
    cannot be started, whatever the bind address (a non-loopback `host` asks for nothing more:
    it already needs all of it).
    """
    missing = [(flag, what) for name, flag, what in _REQUIRED if not getattr(config, name)]
    if missing:
        raise _error(
            "the network transport is not fully configured; missing "
            + "; ".join(f"{flag} ({what})" for flag, what in missing)
            + " — it never serves without TLS, client certificates and token checks (NFR-SEC-09)",
            "pass every one of those flags; stdio (`neuroedge mcp serve` without --http) needs none",
        )
    if not 0 <= config.port <= 65535:
        raise _error(f"--port is {config.port}", "use a port from 0 to 65535", f"{WHERE} (--port)")
    if not config.host or any(c.isspace() for c in config.host):
        raise _error(f"--host is {config.host!r}", "pass an address or a name", f"{WHERE} (--host)")
    if not config.required_scope or any(c.isspace() for c in config.required_scope):
        raise _error(
            f"--required-scope is {config.required_scope!r}: it must be one scope token",
            f"pass one scope, as the issuer puts it in `scope` (default {DEFAULT_SCOPE})",
            f"{WHERE} (--required-scope)",
        )
    issuer = _https_url(config.issuer or "", "--issuer", with_path=False)
    audience = _https_url(config.audience or "", "--audience", with_path=True)

    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.minimum_version = ssl.TLSVersion.TLSv1_3  # NFR-SEC-04
    tls.verify_mode = ssl.CERT_REQUIRED
    tls.set_alpn_protocols(["http/1.1"])
    assert config.tls_cert and config.tls_key and config.client_ca and config.jwks
    try:
        tls.load_cert_chain(config.tls_cert, config.tls_key)
    except (OSError, ssl.SSLError) as exc:
        raise _error(
            f"cannot load the server certificate {config.tls_cert} and key {config.tls_key}: {exc}",
            "pass a PEM certificate and the unencrypted PEM key that belongs to it",
            f"{WHERE} (--tls-cert, --tls-key)",
        ) from exc
    try:
        tls.load_verify_locations(cafile=str(config.client_ca))
    except (OSError, ssl.SSLError) as exc:
        raise _error(
            f"cannot load the client CA {config.client_ca}: {exc}",
            "pass the PEM file of the CA that signed the devices' client certificates",
            f"{WHERE} (--client-ca)",
        ) from exc
    if not tls.cert_store_stats().get("x509_ca"):
        raise _error(
            f"{config.client_ca} holds no CA certificate, so no client certificate could ever pass",
            "pass the PEM file of the CA that signed the devices' client certificates",
            f"{WHERE} (--client-ca)",
        )

    verifier = DeviceTokenVerifier(
        issuer=issuer,
        audience=audience,
        keys=_load_keys(config.jwks),
        required_scope=config.required_scope,
    )
    path = urlsplit(audience).path.rstrip("/") or "/mcp"
    return Prepared(config=config, tls=tls, verifier=verifier, path=path)


def _load_keys(path: Path) -> list[tuple[str | None, Any]]:
    """`(kid, public key)` for each signing key of a JWKS file; anything that could mint a token is refused."""
    where = f"{WHERE} (--jwks)"
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        entries = data["keys"]
        if not isinstance(entries, list):
            raise TypeError("`keys` is not a list")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise _error(
            f'cannot read {path} as a JWKS (RFC 7517: {{"keys": [...]}}): {exc}',
            "pass the issuer's public keys, as published at its `jwks_uri`",
            where,
        ) from exc
    import jwt

    keys: list[tuple[str | None, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("use", "sig") != "sig":
            continue
        if entry.get("kty") not in ("RSA", "EC", "OKP") or "d" in entry:
            raise _error(
                f"{path} holds a {entry.get('kty')!r} key"
                + (" with private parameters" if "d" in entry else "")
                + ": a server that can sign could forge the tokens it is there to check",
                "give it the issuer's public keys only: RSA, EC or OKP, no `d`, no shared secret",
                where,
            )
        try:
            key = jwt.PyJWK.from_dict(entry).key
        except Exception as exc:  # PyJWT raises several types for a malformed JWK
            raise _error(
                f"{path} holds a key PyJWT cannot read: {exc}", "fix or remove it", where
            ) from exc
        keys.append((entry.get("kid"), key))
    if not keys:
        raise _error(
            f'{path} holds no signing key (`use` absent or "sig")',
            "pass the issuer's public signing keys",
            where,
        )
    return keys


def thumbprint(der: bytes) -> str:
    """The RFC 8705 `x5t#S256` of a DER certificate: base64url(SHA-256), no padding."""
    return base64.urlsafe_b64encode(hashlib.sha256(der).digest()).rstrip(b"=").decode("ascii")


class DeviceTokenVerifier:
    """
    The MCP SDK's `TokenVerifier`: a bearer JWT access token for this server, for one device.

    `check` is the whole rule, and a function of the token, the keys and the clock alone;
    `verify_token` is the SDK's door to it. Anything that is not a clean pass is a refusal,
    including a bug in this code: the verifier cannot raise into the server.
    """

    def __init__(
        self,
        *,
        issuer: str,
        audience: str,
        keys: list[tuple[str | None, Any]],
        required_scope: str = DEFAULT_SCOPE,
    ) -> None:
        self.issuer = issuer
        self.audience = audience
        self.required_scope = required_scope
        self._keys = keys

    def _key(self, kid: str | None) -> Any:
        if kid is None:
            candidates = self._keys if len(self._keys) == 1 else []
        else:
            candidates = [pair for pair in self._keys if pair[0] == kid]
        if len(candidates) != 1:
            raise Refused("invalid_token")
        return candidates[0][1]

    def check(self, token: str, peer: str | None) -> Any:
        """The `AccessToken` of a token that passes, for a client whose certificate is `peer`; else `Refused`."""
        import jwt
        from mcp.server.auth.provider import AccessToken

        try:
            header = jwt.get_unverified_header(token)
            alg = header.get("alg")
            if alg not in SIGNING_ALGORITHMS:
                raise Refused("invalid_token")
            claims = jwt.decode(
                token,
                self._key(header.get("kid")),
                algorithms=[alg],
                audience=self.audience,
                issuer=self.issuer,
                options={"require": ["exp", "iss", "aud", "sub"]},
            )
        except Refused:
            raise
        except jwt.ExpiredSignatureError:
            raise Refused("expired") from None
        except jwt.InvalidAudienceError:
            raise Refused("wrong_audience") from None
        except jwt.InvalidIssuerError:
            raise Refused("wrong_issuer") from None
        except Exception:
            raise Refused("invalid_token") from None

        subject = claims["sub"]
        if not isinstance(subject, str) or not subject:
            raise Refused("invalid_token")
        # From here the signature held: the subject is the issuer's word, safe to trace.
        bound = (
            (claims.get("cnf") or {}).get("x5t#S256")
            if isinstance(claims.get("cnf"), dict)
            else None
        )
        if not isinstance(bound, str):
            raise Refused(
                "not_cert_bound", subject
            )  # a per-device token names its device's certificate
        if peer is None or not hmac.compare_digest(bound, peer):
            raise Refused("cert_mismatch", subject)
        scopes = claims.get("scope", claims.get("scp", ""))
        if isinstance(scopes, str):
            scopes = scopes.split()
        if not isinstance(scopes, list) or not all(isinstance(s, str) for s in scopes):
            raise Refused("invalid_token", subject)
        client_id = claims.get("client_id")
        return AccessToken(
            token=token,
            client_id=client_id if isinstance(client_id, str) and client_id else subject,
            scopes=scopes,
            expires_at=int(claims["exp"]),
            resource=self.audience,
            subject=subject,
            claims={"iss": self.issuer},
        )

    async def verify_token(self, token: str) -> Any:
        holder = _refusal.get()
        try:
            return self.check(token, _peer.get())
        except Refused as refused:
            reason, subject = refused.reason, refused.subject
        except Exception:
            reason, subject = "invalid_token", None
        if holder is not None:
            holder.reason, holder.subject = reason, subject
        return None


class _Guard:
    """
    An ASGI wrapper around the SDK's app. It gives the verifier the request's client certificate,
    and writes every 401 / 403 the SDK sends as `mcp_auth_refused` — the one place refusals are
    counted, whichever check refused.
    """

    def __init__(self, app: Any, record: Callable[[dict[str, Any]], None]) -> None:
        self.app = app
        self.record = record

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        holder = _Refusal()
        headers = {k.lower(): v for k, v in scope.get("headers", [])}
        authorization = headers.get(b"authorization", b"").decode("latin1")
        marks = (_peer.set(scope.get(PEER_KEY)), _refusal.set(holder))

        async def watch(message: Any) -> None:
            if message["type"] == "http.response.start" and message["status"] in (401, 403):
                self._record(message["status"], authorization, holder, scope)
            await send(message)

        try:
            await self.app(scope, receive, watch)
        finally:
            _peer.reset(marks[0])
            _refusal.reset(marks[1])

    def _record(self, status: int, authorization: str, holder: _Refusal, scope: Any) -> None:
        subject = holder.subject
        if status == 403:
            reason = "insufficient_scope"
            user = scope.get("user")
            subject = getattr(getattr(user, "access_token", None), "subject", None)
        elif holder.reason:
            reason = holder.reason
        elif not authorization:
            reason = "no_token"
        elif not authorization.lower().startswith("bearer "):
            reason = "malformed_authorization"
        else:
            reason = "invalid_token"
        data: dict[str, Any] = {"reason": reason, "status": status}
        if subject:
            data["subject"] = subject
        self.record(data)


def build_app(session: Any, prepared: Prepared) -> Any:
    """The Streamable HTTP ASGI app of `session` behind the token checks and the guard."""
    from mcp.server.auth.settings import AuthSettings

    config = prepared.config
    server = build_server(
        session
    )  # source "mcp", the one road to the gate: nothing network-specific
    inner = server.streamable_http_app(
        streamable_http_path=prepared.path,
        host=config.host,
        auth=AuthSettings(
            issuer_url=config.issuer,
            resource_server_url=config.audience,
            required_scopes=[config.required_scope],
            validate_token_resource=True,
        ),
        token_verifier=prepared.verifier,
    )

    def record(data: dict[str, Any]) -> None:
        prepared.refusals += 1
        if prepared.refusals <= MAX_REFUSALS_TRACED:
            if prepared.refusals == MAX_REFUSALS_TRACED:
                data = {**data, "last_recorded": True}  # the trace stops here; the count goes on
            session.events.emit("mcp_auth_refused", data)

    return _Guard(inner, record)


def bind(config: HttpConfig) -> socket.socket:
    """The listening socket, or a three-part error: bound once, here, after `prepare` passed."""
    family = socket.AF_INET6 if ":" in config.host else socket.AF_INET
    sock = socket.socket(family, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((config.host.strip("[]"), config.port))
        # Listen now, not when uvicorn starts: on Linux a socket that is only bound does not hold
        # the port against another bind with SO_REUSEADDR, so a second server could take it.
        sock.listen(128)
    except OSError as exc:
        sock.close()
        raise _error(
            f"cannot listen on {config.host}:{config.port}: {exc}",
            "free the port, pass another --port (0 picks one), or an address of this machine",
            f"{WHERE} (--host, --port)",
        ) from exc
    return sock


async def serve_http(
    session: Any,
    prepared: Prepared,
    *,
    on_ready: Callable[[str, int], None] | None = None,
    stop: threading.Event | None = None,
) -> None:
    """
    Serve `session` over mTLS Streamable HTTP until a signal arrives (SIGINT, SIGTERM, SIGHUP)
    or `stop` is set. `on_ready(host, port)` runs once connections are accepted.
    """
    import anyio
    import uvicorn
    from uvicorn.protocols.http.h11_impl import H11Protocol

    class CertAware(H11Protocol):
        """uvicorn does not tell the app who connected: remember the client certificate per connection."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            self._peer: str | None = None
            inner = self.app

            async def app(scope: Any, receive: Any, send: Any) -> None:
                if scope["type"] == "http":
                    scope = {**scope, PEER_KEY: self._peer}
                await inner(scope, receive, send)

            self.app = app

        def connection_made(self, transport: Any) -> None:  # type: ignore[override]
            super().connection_made(transport)
            ssl_object = transport.get_extra_info("ssl_object")
            der = ssl_object.getpeercert(binary_form=True) if ssl_object is not None else None
            self._peer = thumbprint(der) if der else None

    class Server(uvicorn.Server):
        @contextlib.contextmanager
        def capture_signals(self):  # type: ignore[override]
            yield  # signals are `serve_http`'s: the server must leave through the caller's cleanup

    sock = bind(prepared.config)
    app = build_app(session, prepared)
    config = uvicorn.Config(
        app,
        http=CertAware,
        ssl_certfile=str(prepared.config.tls_cert),
        ssl_keyfile=str(prepared.config.tls_key),
        lifespan="on",
        log_level="warning",
        access_log=False,
        ws="none",
        timeout_graceful_shutdown=5,
    )
    config.load()
    config.ssl = (
        prepared.tls
    )  # TLS 1.3 minimum and a client certificate required, whatever uvicorn builds
    server = Server(config)
    host, port = sock.getsockname()[:2]

    async def ready() -> None:
        while not server.started and not server.should_exit:
            await anyio.sleep(0.02)
        if server.started and on_ready is not None:
            on_ready(host, port)

    async def watch_stop() -> None:
        while not server.should_exit:
            if stop is not None and stop.is_set():
                server.should_exit = True
            await anyio.sleep(0.05)

    async def watch_signals() -> None:
        import signal

        names = [n for n in ("SIGINT", "SIGTERM", "SIGHUP") if hasattr(signal, n)]
        try:
            with anyio.open_signal_receiver(*(getattr(signal, n) for n in names)) as signals:
                async for _ in signals:
                    server.should_exit = True
                    return
        except (NotImplementedError, RuntimeError, ValueError):
            return  # no signal receiver on this platform or loop: it stops by `stop` or Ctrl-C only

    try:
        async with anyio.create_task_group() as group:
            group.start_soon(ready)
            group.start_soon(watch_stop)
            if threading.current_thread() is threading.main_thread():
                group.start_soon(watch_signals)
            await server.serve(sockets=[sock])
            group.cancel_scope.cancel()
    except BaseExceptionGroup as failed:
        if failed.subgroup(SystemExit) is None:
            raise
        raise _error(
            f"the server could not start on {host}:{port}",
            "see the log lines above it on stderr",
            f"{WHERE} (--host, --port)",
        ) from None
    finally:
        sock.close()
