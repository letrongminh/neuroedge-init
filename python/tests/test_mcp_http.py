"""
TSK-P2-04 (Q-58, Q-32, NFR-SEC-04, NFR-SEC-09) — `neuroedge mcp serve --http`.

MCP over the network is the stdio server behind an authenticated door, and the door fails
closed. These are the five behaviours of I6 exit criterion 7, each by name:

  * an MCP client over Streamable HTTP + mTLS + a per-device OAuth 2.1 token calls an
    `@action`, and the call takes the gate and lands in the trace
    (`test_an_authenticated_client_lists_and_calls_the_gated_tools`);
  * missing or wrong authentication is refused, with nothing dispatched
    (`test_a_request_without_a_valid_token_is_refused_and_nothing_is_dispatched`,
    `test_a_client_without_a_trusted_certificate_never_reaches_http`);
  * enabling the port without the whole configuration does not start
    (`test_the_network_transport_refuses_to_start_without_the_whole_configuration`,
    `test_the_cli_refuses_to_start_half_configured_before_wiring_a_session_or_binding`);
  * N repeats of a blocked call with the same facts are N `BLOCK`, never an `ALLOW`
    (`test_repeating_a_blocked_call_over_the_network_never_slips_through`, TODOS #29).

Everything runs in this process on 127.0.0.1 with a throwaway CA generated at test time. A real
second machine is the one thing these cannot show.
"""

from __future__ import annotations

import contextlib
import datetime
import ipaddress
import json
import os
import re
import signal
import ssl
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import anyio
import httpx2
import jwt
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from typer.testing import CliRunner

from neuroedge import mcp_http
from neuroedge.cli.main import app
from neuroedge.errors import NeuroEdgeError
from neuroedge.mcp_http import HttpConfig, prepare, thumbprint
from neuroedge.sim import SimSession
from neuroedge.sim.serve import run_http
from neuroedge.trace import validate_trace

PYTHON_DIR = Path(__file__).resolve().parents[1]
ISSUER = "https://auth.example.test"
AUDIENCE = "https://neuroedge.example.test/mcp"
SCOPE = "neuroedge:call"
TIMEOUT = 15.0


# --- a throwaway PKI and token issuer ------------------------------------------------------


def _name(common_name: str) -> x509.Name:
    return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])


def _pem(cert: x509.Certificate) -> bytes:
    return cert.public_bytes(serialization.Encoding.PEM)


def _key_pem(key: ec.EllipticCurvePrivateKey) -> bytes:
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )


def _issue(subject: str, key, issuer: str, issuer_key, *, ca=False, usage=None) -> x509.Certificate:
    now = datetime.datetime.now(datetime.UTC)
    builder = (
        x509.CertificateBuilder()
        .subject_name(_name(subject))
        .issuer_name(_name(issuer))
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=5))
        .not_valid_after(now + datetime.timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=ca, path_length=None), critical=True)
    )
    if usage is not None:
        builder = builder.add_extension(x509.ExtendedKeyUsage([usage]), critical=False)
        builder = builder.add_extension(
            x509.SubjectAlternativeName(
                [x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]
            ),
            critical=False,
        )
    return builder.sign(issuer_key, hashes.SHA256())


@dataclass
class Identity:
    cert: Path
    key: Path
    der: bytes

    @property
    def thumbprint(self) -> str:
        return thumbprint(self.der)


@dataclass
class Pki:
    directory: Path
    ca: Path
    server: Identity
    devices: dict[str, Identity]
    rogue: Identity  # a client certificate signed by a CA the server does not trust
    jwks: Path
    signing_key: ec.EllipticCurvePrivateKey
    other_signing_key: ec.EllipticCurvePrivateKey

    def identity(self, who: str) -> Identity:
        return self.rogue if who == "rogue" else self.devices[who]


def _identity(directory: Path, name: str, subject: str, issuer: str, issuer_key, usage) -> Identity:
    key = ec.generate_private_key(ec.SECP256R1())
    cert = _issue(subject, key, issuer, issuer_key, usage=usage)
    (directory / f"{name}.pem").write_bytes(_pem(cert))
    (directory / f"{name}.key").write_bytes(_key_pem(key))
    return Identity(
        directory / f"{name}.pem",
        directory / f"{name}.key",
        cert.public_bytes(serialization.Encoding.DER),
    )


@pytest.fixture(scope="module")
def pki(tmp_path_factory) -> Pki:
    directory = tmp_path_factory.mktemp("pki")
    ca_key = ec.generate_private_key(ec.SECP256R1())
    ca = _issue("neuroedge test CA", ca_key, "neuroedge test CA", ca_key, ca=True)
    (directory / "ca.pem").write_bytes(_pem(ca))
    rogue_key = ec.generate_private_key(ec.SECP256R1())  # the key of a CA the server does not trust
    client = ExtendedKeyUsageOID.CLIENT_AUTH
    signing_key = ec.generate_private_key(ec.SECP256R1())
    jwk = json.loads(jwt.algorithms.ECAlgorithm.to_jwk(signing_key.public_key()))
    (directory / "jwks.json").write_text(json.dumps({"keys": [{**jwk, "kid": "k1", "use": "sig"}]}))
    return Pki(
        directory=directory,
        ca=directory / "ca.pem",
        server=_identity(
            directory,
            "server",
            "localhost",
            "neuroedge test CA",
            ca_key,
            ExtendedKeyUsageOID.SERVER_AUTH,
        ),
        devices={
            name: _identity(directory, name, name, "neuroedge test CA", ca_key, client)
            for name in ("device-a", "device-b")
        },
        rogue=_identity(directory, "rogue", "rogue", "rogue CA", rogue_key, client),
        jwks=directory / "jwks.json",
        signing_key=signing_key,
        other_signing_key=ec.generate_private_key(ec.SECP256R1()),
    )


def mint(pki: Pki, device: str = "device-a", **override) -> str:
    """A token the issuer would give `device`; `override` replaces (None removes) a claim."""
    now = int(time.time())
    claims = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": device,
        "exp": now + 300,
        "iat": now,
        "scope": SCOPE,
        "cnf": {"x5t#S256": pki.devices[device].thumbprint},
    }
    key = override.pop("signing_key", pki.signing_key)
    for name, value in override.items():
        if value is None:
            claims.pop(name, None)
        else:
            claims[name] = value
    return jwt.encode(claims, key, algorithm="ES256", headers={"kid": "k1"})


def config(pki: Pki, **override) -> HttpConfig:
    values = {
        "host": "127.0.0.1",
        "port": 0,
        "tls_cert": pki.server.cert,
        "tls_key": pki.server.key,
        "client_ca": pki.ca,
        "issuer": ISSUER,
        "audience": AUDIENCE,
        "jwks": pki.jwks,
    }
    values.update(override)
    return HttpConfig(**values)


# --- a running server and a client ---------------------------------------------------------


@dataclass
class Running:
    session: SimSession
    port: int

    @property
    def url(self) -> str:
        return f"https://127.0.0.1:{self.port}/mcp"

    def events(self, kind: str) -> list[dict]:
        return self.session.events.of_type(kind)


@pytest.fixture
def serve(pki, root):
    """Start `run_http` on a free port in a thread; the fixture stops them all."""
    started: list[tuple[threading.Thread, threading.Event]] = []

    def start(agent: str = "driveway", facts=None, **override) -> Running:
        session = SimSession.load(root / "fixtures" / "agents" / agent / "agent.toml", facts=facts)
        prepared = prepare(config(pki, **override))
        ready, stop, box = threading.Event(), threading.Event(), {}

        def on_ready(_host: str, port: int) -> None:
            box["port"] = port
            ready.set()

        def target() -> None:
            try:
                run_http(session, prepared, on_ready=on_ready, stop=stop)
            except BaseException as error:  # reported by the test thread
                box["error"] = error
                ready.set()

        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        started.append((thread, stop))
        assert ready.wait(TIMEOUT), "the server did not come up"
        assert "error" not in box, box.get("error")
        return Running(session, box["port"])

    yield start
    for _, stop in started:
        stop.set()
    for thread, _ in started:
        thread.join(TIMEOUT)
        assert not thread.is_alive(), "the server did not stop"


def tls_context(pki: Pki, who: str | None) -> ssl.SSLContext:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.load_verify_locations(cafile=str(pki.ca))
    if who is not None:
        identity = pki.identity(who)
        context.load_cert_chain(identity.cert, identity.key)
    return context


def client_for(pki: Pki, who: str | None, token: str | None) -> httpx2.AsyncClient:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return httpx2.AsyncClient(verify=tls_context(pki, who), headers=headers, timeout=TIMEOUT)


INITIALIZE = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {"name": "buzz_in", "arguments": {"zone": "front", "seconds": 3}},
}
MCP_HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}


def post(pki: Pki, running: Running, who: str | None, token: str | None, headers=None):
    async def go():
        async with client_for(pki, who, token) as client:
            return await client.post(
                running.url, json=INITIALIZE, headers={**MCP_HEADERS, **(headers or {})}
            )

    return anyio.run(go)


def nothing_dispatched(running: Running) -> None:
    for kind in ("tool_call", "action_requested", "gate_evaluation_result", "actuator_command"):
        assert running.events(kind) == [], f"a refused request reached {kind}"


# --- 1. the configuration gate -------------------------------------------------------------

REQUIRED_FLAGS = {
    "tls_cert": "--tls-cert",
    "tls_key": "--tls-key",
    "client_ca": "--client-ca",
    "issuer": "--issuer",
    "audience": "--audience",
    "jwks": "--jwks",
}


@pytest.mark.parametrize("name", REQUIRED_FLAGS)
def test_the_network_transport_refuses_to_start_without_the_whole_configuration(pki, name):
    with pytest.raises(NeuroEdgeError) as refused:
        prepare(config(pki, **{name: None}))
    assert REQUIRED_FLAGS[name] in refused.value.why
    assert refused.value.where and refused.value.how  # the three parts


def test_nothing_at_all_is_refused_naming_everything_missing_and_a_non_local_bind_is_no_different():
    for host in ("127.0.0.1", "0.0.0.0"):
        with pytest.raises(NeuroEdgeError) as refused:
            prepare(HttpConfig(host=host))
        assert all(flag in refused.value.why for flag in REQUIRED_FLAGS.values())


def test_a_complete_configuration_prepares(pki):
    prepared = prepare(config(pki))
    assert prepared.tls.minimum_version == ssl.TLSVersion.TLSv1_3
    assert prepared.tls.verify_mode == ssl.CERT_REQUIRED
    assert prepared.path == "/mcp"


def test_a_configuration_it_cannot_use_is_refused_at_startup(pki, tmp_path):
    garbage = tmp_path / "garbage.pem"
    garbage.write_text("not a certificate")
    cases = {
        "a certificate that is not one": config(pki, tls_cert=garbage),
        "a key of another certificate": config(pki, tls_key=pki.devices["device-a"].key),
        "a client CA that is not one": config(pki, client_ca=garbage),
        "a missing key file": config(pki, jwks=tmp_path / "absent.json"),
        "an issuer without https": config(pki, issuer="http://auth.example.test"),
        "an audience without https": config(pki, audience="http://neuroedge.example.test/mcp"),
        "a scope that is two words": config(pki, required_scope="a b"),
        "a port out of range": config(pki, port=70000),
    }
    for label, bad in cases.items():
        with pytest.raises(NeuroEdgeError, match=r"\[NE0000\]") as refused:
            prepare(bad)
        assert refused.value.why and refused.value.how, label


def test_a_key_file_that_could_forge_tokens_is_refused(pki, tmp_path):
    public = json.loads(pki.jwks.read_text())["keys"][0]
    private = {**public, "d": "AAAA"}
    symmetric = {"kty": "oct", "k": "c2VjcmV0", "kid": "k2", "use": "sig"}
    for label, keys in {
        "private parameters": [private],
        "a shared secret": [public, symmetric],
        "no signing key": [{**public, "use": "enc"}],
    }.items():
        path = tmp_path / "jwks.json"
        path.write_text(json.dumps({"keys": keys}))
        with pytest.raises(NeuroEdgeError) as refused:
            prepare(config(pki, jwks=path))
        assert "--jwks" in refused.value.where, label


def test_the_cli_refuses_to_start_half_configured_before_wiring_a_session_or_binding(
    pki, root, monkeypatch
):
    def wired(*_a, **_k):
        raise AssertionError("a session was wired, or a socket bound, for a refused configuration")

    monkeypatch.setattr(SimSession, "load", wired)
    monkeypatch.setattr(mcp_http, "bind", wired)
    agent = str(root / "fixtures" / "agents" / "driveway" / "agent.toml")
    for extra in ([], ["--host", "0.0.0.0"], ["--tls-cert", str(pki.server.cert)]):
        result = CliRunner().invoke(app, ["mcp", "serve", "--http", "--agent", agent, *extra])
        assert result.exit_code == 1, result.output
        assert (
            "--client-ca" in result.output and "why:" in result.output and "fix:" in result.output
        )


def test_the_network_flags_without_http_are_refused_not_ignored(root):
    agent = str(root / "fixtures" / "agents" / "driveway" / "agent.toml")
    result = CliRunner().invoke(app, ["mcp", "serve", "--agent", agent, "--tls-cert", "x.pem"])
    assert result.exit_code == 1
    assert "--http" in result.output


def test_the_network_door_and_the_live_page_are_not_combined(pki, root):
    agent = str(root / "fixtures" / "agents" / "driveway" / "agent.toml")
    result = CliRunner().invoke(app, ["mcp", "serve", "--http", "--ui", "--agent", agent])
    assert result.exit_code == 2


def test_a_port_that_is_taken_is_a_three_part_error_and_the_session_is_closed(pki, root):
    session = SimSession.load(root / "fixtures" / "agents" / "driveway" / "agent.toml")
    closed = []
    real_close = session.close
    session.close = lambda: (closed.append(True), real_close())  # type: ignore[method-assign]
    taken = mcp_http.bind(HttpConfig(port=0))
    try:
        port = taken.getsockname()[1]
        with pytest.raises(NeuroEdgeError) as refused:
            run_http(session, prepare(config(pki, port=port)))
        assert str(port) in refused.value.why and refused.value.how
    finally:
        taken.close()
    assert closed == [True]


# --- 2. refusing what is not authenticated -------------------------------------------------

BAD_TOKENS = {
    "garbage": (lambda pki: "not.a.jwt", "invalid_token"),
    "signed by another key": (
        lambda pki: mint(pki, signing_key=pki.other_signing_key),
        "invalid_token",
    ),
    "expired": (lambda pki: mint(pki, exp=int(time.time()) - 5), "expired"),
    "for another audience": (
        lambda pki: mint(pki, aud="https://elsewhere.example.test/mcp"),
        "wrong_audience",
    ),
    "from another issuer": (lambda pki: mint(pki, iss="https://evil.example.test"), "wrong_issuer"),
    "without an expiry": (lambda pki: mint(pki, exp=None), "invalid_token"),
    "without a subject": (lambda pki: mint(pki, sub=None), "invalid_token"),
    "not bound to a certificate": (lambda pki: mint(pki, cnf=None), "not_cert_bound"),
    "bound to another device's certificate": (
        lambda pki: mint(pki, cnf={"x5t#S256": thumbprint(b"another")}),
        "cert_mismatch",
    ),
    "unsigned (alg none)": (
        lambda pki: jwt.encode(
            {"iss": ISSUER, "aud": AUDIENCE, "sub": "device-a", "exp": int(time.time()) + 300},
            None,
            algorithm="none",
        ),
        "invalid_token",
    ),
}


@pytest.mark.parametrize("label", BAD_TOKENS)
def test_a_request_without_a_valid_token_is_refused_and_nothing_is_dispatched(pki, serve, label):
    make, reason = BAD_TOKENS[label]
    running = serve()
    response = post(pki, running, "device-a", make(pki))
    assert response.status_code == 401, label
    assert response.headers["www-authenticate"].startswith("Bearer ")
    nothing_dispatched(running)
    [refusal] = running.events("mcp_auth_refused")
    assert refusal["reason"] == reason and refusal["status"] == 401


def test_a_request_with_no_token_at_all_is_a_401_and_is_traced(pki, serve):
    running = serve()
    assert post(pki, running, "device-a", None).status_code == 401
    assert (
        post(
            pki, running, "device-a", None, headers={"Authorization": "Basic dXNlcjpwYXNz"}
        ).status_code
        == 401
    )
    nothing_dispatched(running)
    assert [e["reason"] for e in running.events("mcp_auth_refused")] == [
        "no_token",
        "malformed_authorization",
    ]


def test_a_token_without_the_required_scope_is_a_403(pki, serve):
    running = serve()
    response = post(pki, running, "device-a", mint(pki, scope="read:something"))
    assert response.status_code == 403
    nothing_dispatched(running)
    [refusal] = running.events("mcp_auth_refused")
    assert refusal == {"reason": "insufficient_scope", "status": 403, "subject": "device-a"}


def test_the_refused_attempts_never_record_the_token(pki, serve):
    running = serve()
    token = BAD_TOKENS["expired"][0](pki)
    post(pki, running, "device-a", token)
    assert token not in json.dumps(running.session.events.events)
    assert token.split(".")[1] not in json.dumps(running.session.events.events)


def test_the_trace_stops_recording_refusals_at_its_cap_and_says_so(pki, serve, monkeypatch):
    monkeypatch.setattr(mcp_http, "MAX_REFUSALS_TRACED", 3)
    running = serve()
    for _ in range(5):
        post(pki, running, "device-a", None)
    events = running.events("mcp_auth_refused")
    assert len(events) == 3 and events[-1].get("last_recorded") is True


@pytest.mark.parametrize("who", [None, "rogue"])
def test_a_client_without_a_trusted_certificate_never_reaches_http(pki, serve, who):
    running = serve()
    with pytest.raises((httpx2.HTTPError, OSError)):
        # even with a perfectly good token: mTLS comes first
        post(pki, running, who, mint(pki))
    nothing_dispatched(running)


def test_a_client_that_will_not_speak_tls_13_is_refused(pki, serve):
    running = serve()
    context = tls_context(pki, "device-a")
    context.maximum_version = ssl.TLSVersion.TLSv1_2

    async def go():
        async with httpx2.AsyncClient(verify=context, timeout=TIMEOUT) as client:
            await client.get(running.url)

    with pytest.raises((httpx2.HTTPError, OSError)):
        anyio.run(go)


def test_the_protected_resource_metadata_names_the_issuer(pki, serve):
    running = serve()

    async def go():
        async with client_for(pki, "device-a", None) as client:
            return await client.get(
                f"https://127.0.0.1:{running.port}/.well-known/oauth-protected-resource/mcp"
            )

    response = anyio.run(go)
    assert response.status_code == 200
    body = response.json()
    assert body["resource"].rstrip("/") == AUDIENCE
    assert [s.rstrip("/") for s in body["authorization_servers"]] == [ISSUER]


# --- 3. the one road to hardware -----------------------------------------------------------


@contextlib.asynccontextmanager
async def mcp_client(pki: Pki, running: Running, who: str, token: str):
    # the http client is ours to close: the SDK leaves a client it was given open
    async with (
        client_for(pki, who, token) as http,
        Client(streamable_http_client(running.url, http_client=http)) as client,
    ):
        yield client


def test_an_authenticated_client_lists_and_calls_the_gated_tools(pki, serve):
    running = serve(facts={"visitor_expected": True})

    async def go():
        async with mcp_client(pki, running, "device-a", mint(pki)) as client:
            tools = {tool.name for tool in (await client.list_tools()).tools}
            allowed = await client.call_tool("buzz_in", {"zone": "front", "seconds": 3})
            degraded = await client.call_tool("open_gate", {})
            claimed = await client.call_tool(
                "buzz_in", {"zone": "front", "call_source": "local_grammar"}
            )
        return tools, allowed, degraded, claimed

    tools, allowed, degraded, claimed = anyio.run(go)
    assert {"buzz_in", "open_gate", "porch_light_on"} <= tools

    assert allowed.structured_content["status"] == "ALLOW" and not allowed.is_error
    # the gate, not the transport, decides: the driveway's gate does not let `mcp` open the gate
    assert degraded.structured_content["status"] == "BLOCK" and not degraded.is_error
    assert degraded.structured_content["on_block"] == "degrade"
    # a client never states its own call_source
    assert claimed.is_error and claimed.structured_content["status"] == "REJECTED"

    calls = running.events("tool_call")
    assert [c["name"] for c in calls] == ["buzz_in", "open_gate", "buzz_in"]
    assert {c["source"] for c in calls} == {"mcp"}  # a network call is an `mcp` call (§5)
    verdicts = [e["verdict"] for e in running.events("gate_evaluation_result")]
    assert verdicts == [
        "ALLOW",
        "BLOCK",
        "ALLOW",
    ]  # buzz_in; open_gate, then its fallback's own gate
    assert running.events("actuator_command"), "the allowed call moved a pin through the HAL"
    assert running.events("mcp_auth_refused") == []


def test_every_device_gets_its_own_token_and_one_cannot_use_anothers(pki, serve):
    running = serve(facts={"visitor_expected": True})

    async def call_as(device: str):
        async with mcp_client(pki, running, device, mint(pki, device)) as client:
            return (
                await client.call_tool("buzz_in", {"zone": "front", "seconds": 1})
            ).structured_content

    assert anyio.run(call_as, "device-a")["status"] == "ALLOW"
    assert anyio.run(call_as, "device-b")["status"] == "ALLOW"
    # a token issued to device-a, presented with device-b's certificate
    assert post(pki, running, "device-b", mint(pki, "device-a")).status_code == 401
    assert [e["reason"] for e in running.events("mcp_auth_refused")] == ["cert_mismatch"]


def test_a_session_belongs_to_the_device_that_opened_it(pki, serve):
    running = serve()
    initialize = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1"},
        },
    }
    listing = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}

    async def go():
        async with client_for(pki, "device-a", mint(pki, "device-a")) as a:
            opened = await a.post(running.url, json=initialize, headers=MCP_HEADERS)
            session = {
                "mcp-session-id": opened.headers["mcp-session-id"],
                "mcp-protocol-version": "2025-06-18",
            }
            async with client_for(pki, "device-b", mint(pki, "device-b")) as b:
                theirs = await b.post(running.url, json=listing, headers={**MCP_HEADERS, **session})
            mine = await a.post(running.url, json=listing, headers={**MCP_HEADERS, **session})
        return opened.status_code, theirs.status_code, mine.status_code

    assert anyio.run(go) == (
        200,
        404,
        200,
    )  # device-b, fully authenticated, cannot use device-a's session


@pytest.mark.parametrize(
    ("tool", "arguments", "facts"),
    [
        ("buzz_in", {"zone": "front", "seconds": 3}, {"visitor_expected": False}),
        ("open_gate", {}, {}),
    ],
    ids=["deny", "degrade"],
)
def test_repeating_a_blocked_call_over_the_network_never_slips_through(
    pki, serve, tool, arguments, facts
):
    """TODOS #29: N calls with the same facts are N BLOCK, and N trace events each."""
    repeats = 25
    running = serve(facts=facts)

    async def go():
        statuses = []
        # one connection, then a fresh connection every few calls: a client may do either
        for _ in range(repeats // 5):
            async with mcp_client(pki, running, "device-a", mint(pki)) as client:
                for _ in range(5):
                    result = await client.call_tool(tool, arguments)
                    statuses.append(result.structured_content["status"])
        return statuses

    assert anyio.run(go) == ["BLOCK"] * repeats
    assert len(running.events("tool_call")) == repeats
    verdicts = [e["verdict"] for e in running.events("gate_evaluation_result")]
    assert (
        verdicts.count("BLOCK") == repeats
    )  # one BLOCK per call, from the gate the call asked for
    # `degrade` runs the fallback through its own gate, so its ALLOW is that gate's, once per call
    assert verdicts.count("ALLOW") == (repeats if tool == "open_gate" else 0)
    if tool == "buzz_in":
        assert running.events("actuator_command") == []  # not one pulse, however often it asked


def test_the_same_facts_give_the_same_verdict_with_or_without_the_network(root):
    """The gate is deterministic: the door in front of it changes nothing (invariant #4)."""
    agent = root / "fixtures" / "agents" / "driveway" / "agent.toml"

    async def go():
        from neuroedge.actions.tools import ToolCall

        statuses = []
        for facts, expected in (
            ({"visitor_expected": False}, "BLOCK"),
            ({"visitor_expected": True}, "ALLOW"),
        ):
            session = SimSession.load(agent, facts=facts)
            for _ in range(20):
                result = await session.call_tool(
                    ToolCall("buzz_in", {"zone": "front", "seconds": 3}, source="mcp")
                )
                statuses.append((result.status, expected))
            session.close()
        return statuses

    assert all(status == expected for status, expected in anyio.run(go))


# --- 4. the real command -------------------------------------------------------------------


def test_the_cli_serves_over_the_network_and_leaves_cleanly_on_sigterm(pki, root, tmp_path):
    agent = root / "fixtures" / "agents" / "driveway" / "agent.toml"
    trace = tmp_path / "trace.json"
    env = {**os.environ, "NO_COLOR": "1"}
    process = subprocess.Popen(
        [
            sys.executable, "-m", "neuroedge", "mcp", "serve", "--http", "--agent", str(agent),
            "--port", "0", "--trace-out", str(trace),
            "--tls-cert", str(pki.server.cert), "--tls-key", str(pki.server.key),
            "--client-ca", str(pki.ca), "--issuer", ISSUER, "--audience", AUDIENCE,
            "--jwks", str(pki.jwks),
        ],
        cwd=PYTHON_DIR, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )  # fmt: skip
    try:
        port = None
        deadline = time.monotonic() + TIMEOUT
        lines = []
        while time.monotonic() < deadline and port is None:
            line = process.stderr.readline()
            if not line:
                break
            lines.append(line)
            found = re.search(r"listening on 127\.0\.0\.1:(\d+)/mcp", line)
            port = int(found.group(1)) if found else None
        assert port, "no listening line:\n" + "".join(lines)
        running = Running(session=None, port=port)  # type: ignore[arg-type]

        assert post(pki, running, "device-a", None).status_code == 401

        async def go():
            async with mcp_client(pki, running, "device-a", mint(pki)) as client:
                return await client.call_tool("open_gate", {})

        assert anyio.run(go).structured_content["status"] == "BLOCK"
        process.send_signal(signal.SIGTERM)
        assert process.wait(TIMEOUT) == 0
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        process.stderr.close()
        process.stdout.close()
    assert process.stdout is not None
    document = json.loads(trace.read_text())
    validate_trace(document)
    kinds = [event["type"] for event in document["events"]]
    assert "mcp_auth_refused" in kinds and "tool_call" in kinds
    assert [e["data"]["source"] for e in document["events"] if e["type"] == "tool_call"] == ["mcp"]
    # the refusal is an event a replay steps over: the recorded verdicts are recomputed and agree
    replayed = CliRunner().invoke(app, ["replay", str(trace), "--agent", str(agent)])
    assert replayed.exit_code == 0, replayed.output
