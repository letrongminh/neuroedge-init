"""
Plain http to the home LAN, as an explicit opt-in (`allow_lan_http = true`), for both proxies.

The partner's real targets (Home Assistant, Tasmota, Shelly) sit on the LAN over plain http. The
rule, fail-closed: without the key, plain http is for loopback only (unchanged). With it, plain http
is accepted ONLY for a private / link-local / loopback IP literal, or a `*.local`, `*.lan`,
`*.home.arpa` name. Everything else — a public name or address, the carrier-grade NAT range, an
IPv4-mapped address — stays refused with the flag on: no cleartext token over the internet.
"""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
from typer.testing import CliRunner

from neuroedge.cli.main import app
from neuroedge.errors import AgentManifestError
from neuroedge.guard import load_config
from neuroedge.proxy_http import doctor as doctor_http
from neuroedge.proxy_http import init as init_http
from neuroedge.proxy_http import parse_http
from neuroedge.proxy_mcp import doctor as doctor_mcp
from neuroedge.proxy_mcp import init as init_mcp
from neuroedge.proxy_mcp import lan_host, parse_upstream

runner = CliRunner()
ROOT = Path(__file__).resolve().parents[2]

LAN = [
    "10.0.0.5", "10.255.255.254", "172.16.5.1", "172.31.255.254", "192.168.1.10", "169.254.1.2",
    "127.0.0.1", "127.8.9.10", "[fd00::1]", "[fc12::1]", "[fdff::1]", "[fe80::1]", "[::1]",
    "ha.local", "tasmota.lan", "plug.home.arpa", "HA.LOCAL", "a.b.home.arpa", "ha.local.",
]  # fmt: skip
NOT_LAN = [
    "100.64.0.1", "100.127.255.254",  # carrier-grade NAT: refused
    "172.32.0.1", "172.15.255.255", "11.0.0.1", "192.169.0.1", "192.167.1.1", "8.8.8.8", "0.0.0.0",
    "[2001:db8::1]", "[fec0::1]", "[::ffff:192.168.1.1]", "[::ffff:10.0.0.1]",
    "example.com", "local", "lan", "homeassistant", "evil.local.example.com", "home.arpa",
    "ha.localhost.example", "xlocal", "1.2.3.local.net",
]  # fmt: skip


def mcp_config(tmp_path: Path, url: str, flag: str = "") -> Path:
    (tmp_path / "guard.toml").write_text(
        f'[guard]\nname = "x"\n\n[proxy.mcp]\nurl = "{url}"\n{flag}\n[tools.t]\ngate = "g.yaml"\n',
        encoding="utf-8",
    )
    return tmp_path / "guard.toml"


def http_config(tmp_path: Path, upstream: str, flag: str = "") -> Path:
    (tmp_path / "guard.toml").write_text(
        f'[guard]\nname = "x"\n\n[proxy.http]\nupstream = "{upstream}"\n{flag}\n'
        '[[proxy.http.routes]]\nmethod = "GET"\npath = "/status"\ntool = "t"\n\n'
        '[tools.t]\ngate = "g.yaml"\n',
        encoding="utf-8",
    )
    return tmp_path / "guard.toml"


def mcp_check(tmp_path, host, flag):
    return parse_upstream(load_config(mcp_config(tmp_path, f"http://{host}:8123/api/mcp", flag)))


def http_check(tmp_path, host, flag):
    return parse_http(load_config(http_config(tmp_path, f"http://{host}:8080", flag)))


CHECKS = {"mcp": mcp_check, "http": http_check}
ON = "allow_lan_http = true\n"


@pytest.mark.parametrize("proxy", CHECKS)
@pytest.mark.parametrize("host", LAN)
def test_a_lan_host_is_accepted_only_with_the_flag(tmp_path, proxy, host):
    check = CHECKS[proxy]
    result = check(tmp_path, host, ON)
    assert result.allow_lan_http is True
    if lan_host(host) and not host.startswith(("127.", "[::1]")):
        with pytest.raises(AgentManifestError) as refused:
            check(tmp_path, host, "")  # without the key: unchanged, refused
        error = refused.value
        assert error.code == "NE3002" and "allow_lan_http = true" in error.how and error.where
        assert "in clear" in error.why


@pytest.mark.parametrize("proxy", CHECKS)
@pytest.mark.parametrize("host", NOT_LAN)
def test_any_other_host_stays_refused_even_with_the_flag(tmp_path, proxy, host):
    for flag in (ON, ""):
        with pytest.raises(AgentManifestError) as refused:
            CHECKS[proxy](tmp_path, host, flag)
        assert refused.value.code == "NE3002" and refused.value.how
        assert "allow_lan_http does not cover" in refused.value.why or not flag
    assert not lan_host(host)


@pytest.mark.parametrize("proxy", CHECKS)
def test_loopback_and_https_are_unchanged_without_the_flag(tmp_path, proxy):
    check = CHECKS[proxy]
    for host in ("127.0.0.1", "localhost", "[::1]"):
        assert check(tmp_path, host, "").allow_lan_http is False
    path = (mcp_config if proxy == "mcp" else http_config)(tmp_path, "https://8.8.8.8:443", "")
    config = load_config(path)
    assert (parse_upstream if proxy == "mcp" else parse_http)(config)  # https goes anywhere


@pytest.mark.parametrize("proxy", CHECKS)
def test_credentials_in_the_url_stay_refused_with_the_flag(tmp_path, proxy):
    for url in ("http://user:pw@192.168.1.10:8123", "http://:pw@192.168.1.10"):
        path = (mcp_config if proxy == "mcp" else http_config)(tmp_path, url, ON)
        with pytest.raises(AgentManifestError, match="credentials"):
            (parse_upstream if proxy == "mcp" else parse_http)(load_config(path))


@pytest.mark.parametrize("proxy", CHECKS)
def test_the_flag_is_a_bool(tmp_path, proxy):
    path = (mcp_config if proxy == "mcp" else http_config)(
        tmp_path, "http://127.0.0.1:1", 'allow_lan_http = "yes"\n'
    )
    with pytest.raises(AgentManifestError, match="true or false"):
        (parse_upstream if proxy == "mcp" else parse_http)(load_config(path))


def test_the_flag_means_nothing_for_a_stdio_command(tmp_path):
    (tmp_path / "guard.toml").write_text(
        '[guard]\nname = "x"\n\n[proxy.mcp]\ncommand = ["x"]\nallow_lan_http = true\n\n'
        '[tools.t]\ngate = "g.yaml"\n',
        encoding="utf-8",
    )
    with pytest.raises(AgentManifestError, match="for a `url`"):
        parse_upstream(load_config(tmp_path / "guard.toml"))


# --- guard init --allow-lan-http ----------------------------------------------------------------------------


def test_guard_init_http_writes_the_key_and_the_files_load(tmp_path):
    refused = runner.invoke(
        app,
        [
            "guard",
            "init",
            "--http",
            "http://192.168.1.50",
            "--route",
            "POST /cm/{cmd}",
            "--dir",
            str(tmp_path / "a"),
        ],
    )
    assert refused.exit_code == 1 and "allow_lan_http" in refused.output
    assert not (tmp_path / "a").exists(), "nothing written when it is refused"
    ok = runner.invoke(
        app,
        ["guard", "init", "--http", "http://192.168.1.50", "--route", "POST /cm/{cmd}", "--allow-lan-http",
         "--dir", str(tmp_path / "b")],
    )  # fmt: skip
    assert ok.exit_code == 0, ok.output
    text = (tmp_path / "b" / "guard.toml").read_text(encoding="utf-8")
    assert "allow_lan_http = true" in text and "UNENCRYPTED" in text
    assert parse_http(load_config(tmp_path / "b" / "guard.toml")).allow_lan_http is True
    assert runner.invoke(app, ["gate", "lint", str(tmp_path / "b" / "gates")]).exit_code == 0
    public = runner.invoke(
        app,
        [
            "guard",
            "init",
            "--http",
            "http://example.com",
            "--route",
            "GET /x",
            "--allow-lan-http",
            "--dir",
            str(tmp_path / "c"),
        ],
    )
    assert public.exit_code == 1 and "allow_lan_http does not cover" in public.output
    assert not (tmp_path / "c").exists()


def test_guard_init_mcp_writes_the_key_and_refuses_it_for_a_command(tmp_path, monkeypatch):
    monkeypatch.setenv("UPSTREAM_LOG", str(tmp_path / "up.log"))
    stdio = runner.invoke(
        app, ["guard", "init", "--mcp", f'"{sys.executable}" "{ROOT / "fixtures" / "mcp_upstream" / "server.py"}"',
              "--allow-lan-http", "--dir", str(tmp_path / "s")]
    )  # fmt: skip
    assert stdio.exit_code == 1 and "for a `url`" in stdio.output
    public = runner.invoke(
        app,
        [
            "guard",
            "init",
            "--mcp",
            "http://example.com/mcp",
            "--allow-lan-http",
            "--dir",
            str(tmp_path / "p"),
        ],
    )
    assert public.exit_code == 1 and "allow_lan_http does not cover" in public.output
    # a real MCP server over plain http (loopback here: the key is written whether or not it is needed)
    with socket.socket() as spare:
        spare.bind(("127.0.0.1", 0))
        port = spare.getsockname()[1]
    server = subprocess.Popen(
        [sys.executable, str(ROOT / "fixtures" / "mcp_upstream" / "server.py"), "--http", str(port)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )  # fmt: skip
    try:
        for _ in range(100):
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
                break
            except OSError:
                time.sleep(0.1)
        import asyncio

        plan = asyncio.run(
            init_mcp(f"http://127.0.0.1:{port}/mcp", tmp_path / "m", "ha", allow_lan_http=True)
        )
        assert plan.exposed
        text = (tmp_path / "m" / "guard.toml").read_text(encoding="utf-8")
        assert "allow_lan_http = true" in text
        assert parse_upstream(load_config(tmp_path / "m" / "guard.toml")).allow_lan_http is True
        warned = [
            f
            for f in doctor_mcp(tmp_path / "m" / "guard.toml")
            if f.level == "warning" and "allow_lan_http" in f.message
        ]
        assert len(warned) == 1 and "THUẦN" in warned[0].message
    finally:
        server.terminate()
        server.wait(timeout=10)


# --- doctor ---------------------------------------------------------------------------------------------------


def test_doctor_warns_when_the_key_is_on_and_not_when_it_is_off(tmp_path):
    init_http("http://192.168.1.50", ["GET /status"], tmp_path / "on", "plug", allow_lan_http=True)
    init_http("http://127.0.0.1:1", ["GET /status"], tmp_path / "off", "plug")
    on = doctor_http(load_config(tmp_path / "on" / "guard.toml"))
    off = doctor_http(load_config(tmp_path / "off" / "guard.toml"))
    lan = [f for f in on if f.level == "warning" and "allow_lan_http" in f.message]
    assert len(lan) == 1 and "192.168.1.50" in lan[0].message and "THUẦN" in lan[0].message
    assert not [f for f in off if "allow_lan_http" in f.message]
    result = runner.invoke(
        app, ["plugin", "doctor", "--config", str(tmp_path / "on" / "guard.toml"), "--json"]
    )
    report = json.loads(result.output)
    assert result.exit_code == 1
    assert any(
        "allow_lan_http" in f["message"] for f in report["findings"] if f["level"] == "warning"
    )
