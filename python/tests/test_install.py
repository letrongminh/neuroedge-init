"""
Q-83 Profile A — `neuroedge install --profile full` (DP-A-09, with DP-A-03, DP-A-04, DP-NF-02).

Staged under a temporary root: every file the install writes, its mode and what it says, and the
commands it would run as root. The live install runs on a CI runner (`ci-sim-linux.yml` job
`install-full`, TC-A-09-1).
"""

from __future__ import annotations

import hashlib
import io
import json
import tarfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from neuroedge import install
from neuroedge.cli.main import app
from neuroedge.errors import NeuroEdgeError

DEMO = Path(__file__).resolve().parents[2] / "fixtures" / "agents" / "chat-den-cua"


def stand_in(destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(b"#!/bin/sh\n")
    return "v-test (stand-in)"


def staged(tmp_path: Path, **env) -> tuple[Path, install.System, list[str]]:
    settings = install.settings_from_env(
        DEMO,
        {"TELEGRAM_BOT_TOKEN": "7000000003:AAstagedNotARealTokenzzzzzzzzzzzzzz",
         "TELEGRAM_OWNER_ID": "123456789", "LLM_API_KEY": "sk-staged", **env},
    )  # fmt: skip
    system = install.System(root=tmp_path / "root", live=False)
    done = install.install(settings, system, start=False, fetch=stand_in)
    return system.root, system, done


def test_the_brain_gets_four_files_and_never_a_signing_key(tmp_path):
    """TC-A-09-1, staged: the brain's directory holds its certificate, key, token, the CA."""
    root, _, _ = staged(tmp_path)
    brain = root / "var/lib/neuroclaw/keys"
    assert sorted(p.name for p in brain.iterdir()) == ["ca.pem", "nao.key", "nao.pem", "nao.token"]
    for name in ("nao.key", "nao.token"):
        assert (brain / name).stat().st_mode & 0o777 == 0o600
    box = root / "var/lib/neuroedge/keys"
    for secret in ("issuer.key", "ca.key", "hop.key"):
        assert (box / secret).is_file() and not (brain / secret).exists()
        assert not list(root.joinpath("var/lib/neuroclaw").rglob(secret))


def test_the_brain_reaches_the_box_over_mtls_with_every_hardware_tool_off(tmp_path):
    root, _, _ = staged(tmp_path, LLM_API_BASE="http://127.0.0.1:9/v1")
    path = root / "var/lib/neuroclaw/config.json"
    assert path.stat().st_mode & 0o777 == 0o600
    config = json.loads(path.read_text())
    box = config["tools"]["mcp"]["servers"]["neuroedge"]
    token = (root / "var/lib/neuroedge/keys/nao.token").read_text().strip()
    assert box["url"] == "https://localhost:8443/mcp"
    assert box["headers"]["Authorization"] == f"Bearer {token}"
    assert box["tls"]["cert_file"] == "/var/lib/neuroclaw/keys/nao.pem"
    for tool in ("exec", "i2c", "spi", "serial", "install_skill"):
        assert config["tools"][tool]["enabled"] is False
    assert config["tools"]["cron"]["allow_command"] is False
    assert config["model_list"][0]["api_base"] == "http://127.0.0.1:9/v1"
    assert config["channel_list"]["telegram"]["allow_from"] == ["123456789"]


def test_the_units_keep_the_brain_away_from_devices_and_processes(tmp_path):
    root, system, done = staged(tmp_path)
    units = root / "etc/systemd/system"
    brain = (units / "neuroclaw.service").read_text()
    box = (units / "neuroedge-box.service").read_text()
    for line in ("User=neuroclaw", "PrivateDevices=yes", "ProtectProc=invisible",
                 "NoNewPrivileges=yes", "ProtectSystem=strict"):  # fmt: skip
        assert line in brain, line
    assert "SupplementaryGroups" not in brain
    assert "User=neuroedge" in box and "--revoked /var/lib/neuroedge/keys/revoked.txt" in box
    assert "--agent /var/lib/neuroedge/agent/agent.toml" in box
    assert "hidepid=2" in (units / "neuroedge-hidepid.service").read_text()
    assert [
        "useradd",
        "--system",
        "--no-create-home",
        "--shell",
        "/usr/sbin/nologin",
        "neuroclaw",
    ] in system.ran
    assert ["systemctl", "enable", *install.UNITS] in system.ran
    assert not any(c[:2] == ["usermod", "--append"] and "neuroclaw" in c for c in system.ran)
    assert any("not started" in line for line in done)


def test_a_second_install_keeps_the_keys_and_renews_the_token(tmp_path):
    root, _, _ = staged(tmp_path)
    keys = root / "var/lib/neuroedge/keys"
    ca, token = (keys / "ca.pem").read_bytes(), (keys / "nao.token").read_text()
    staged(tmp_path)
    assert (keys / "ca.pem").read_bytes() == ca
    assert (keys / "nao.token").read_text() != token
    assert (root / "var/lib/neuroclaw/keys/nao.token").read_text() == (
        keys / "nao.token"
    ).read_text()


def _release(monkeypatch, payload: bytes, member: str = "neuroclaw") -> None:
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode="w:gz") as archive:
        info = tarfile.TarInfo(member)
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))
    archive_bytes = data.getvalue()

    class Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    monkeypatch.setattr(
        install.urllib.request, "urlopen", lambda *_a, **_k: Response(archive_bytes)
    )
    pins = install.load_pins()
    pins["assets"]["x86_64"]["sha256"] = hashlib.sha256(archive_bytes).hexdigest()
    monkeypatch.setattr(install, "load_pins", lambda: pins)


def test_neuroclaw_is_unpacked_only_when_its_archive_matches_the_pin(tmp_path, monkeypatch):
    """TC-NF-02-1 for the installer: one version, one SHA-256 per archive."""
    pins = json.loads(install.PINS.read_text())
    assert pins["version"].startswith("v") and len(pins["commit"]) == 40
    assert all(len(a["sha256"]) == 64 for a in pins["assets"].values())
    _release(monkeypatch, b"\x7fELF brain")
    target = tmp_path / "bin" / "neuroclaw"
    assert "v0.2.2" in install.fetch_brain(target, "x86_64")
    assert target.read_bytes() == b"\x7fELF brain" and target.stat().st_mode & 0o777 == 0o755
    tampered = tmp_path / "other" / "neuroclaw"
    monkeypatch.setattr(install, "load_pins", lambda: pins)  # the real pin: the archive differs
    with pytest.raises(NeuroEdgeError, match="SHA-256"):
        install.fetch_brain(tampered, "x86_64")
    assert not tampered.exists()
    with pytest.raises(NeuroEdgeError, match="no NeuroClaw"):
        install.fetch_brain(tampered, "mips")


def test_the_cli_stages_and_refuses_what_it_cannot_do(tmp_path, monkeypatch):
    monkeypatch.setattr(install, "fetch_brain", stand_in)
    env = tmp_path / ".env.txt"
    env.write_text("TELEGRAM_OWNER_ID=123456789\nLLM_API_KEY='sk-x'\n")
    staged_root = tmp_path / "staged"
    result = CliRunner().invoke(
        app,
        ["install", "--profile", "full", "--agent", str(DEMO), "--env-file", str(env),
         "--root", str(staged_root)],
    )  # fmt: skip
    assert result.exit_code == 0, result.output
    assert "systemctl enable" in result.output and "sk-x" not in result.output
    other = CliRunner().invoke(
        app, ["install", "--profile", "lite", "--agent", str(DEMO), "--root", str(tmp_path)]
    )
    assert other.exit_code == 2
    missing = CliRunner().invoke(
        app,
        ["install", "--profile", "full", "--agent", str(tmp_path), "--root", str(tmp_path / "r")],
    )
    assert missing.exit_code == 1 and "agent.toml" in missing.output
