"""
Profile A on one machine in one command: `neuroedge install --profile full` (Q-83, DP-A-09).

What a home box needs so the brain and the box run side by side and stay apart
(docs/spec/deployment_profiles.md DP-A-01, DP-A-03, DP-A-04, DP-A-09, DP-NF-02):

* two system users: `neuroedge` (the box; in the device groups on `--target linux`) and
  `neuroclaw` (the brain; no group at all);
* the box's keys (`neuroedge pair init`) in `/var/lib/neuroedge/keys`, 0700; the brain gets only
  its certificate, key, token and the CA certificate, in `/var/lib/neuroclaw/keys` — never
  `issuer.key`, `ca.key` or `hop.key`;
* NeuroClaw itself, the release named in `install_pins.json`, its archive checked by SHA-256
  before anything is unpacked;
* the brain's `config.json` (0600): the box over MCP with mTLS and its token, every
  hardware tool off;
* three systemd units: the box (`mcp serve --http --ui`, its page link in its state directory),
  the brain (no devices, its own /proc view, read-only system), and a one-shot that mounts /proc
  with `hidepid=2` so neither user reads the other's command line;
* then `neuroedge doctor` (DP-A-03) on what was made.

With `--root <dir>` every file is written under that directory and no command runs: the plan is
printed instead. That is how it is tested on the host; on a machine it runs as root.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import platform
import shlex
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from . import pairing
from .errors import NeuroEdgeError

PINS = Path(__file__).with_name("install_pins.json")
BOX_USER = "neuroedge"
BRAIN_USER = "neuroclaw"
DEVICE_GROUPS = ("gpio", "i2c", "spi")  # the box's, on --target linux (never the brain's)
BRAIN_FILES = ("ca.pem", "nao.pem", "nao.key", "nao.token")  # nothing else leaves the box
WHERE = "neuroedge install"
UNITS = ("neuroedge-hidepid.service", "neuroedge-box.service", "neuroclaw.service")


@dataclass
class Settings:
    """What the owner chooses; secrets come from an env file, never the command line."""

    agent: Path
    target: str = "linux"
    host: str = "localhost"
    port: int = 8443
    telegram_token: str | None = None
    telegram_owner: str | None = None
    telegram_base_url: str | None = None
    llm_key: str | None = None
    llm_model: str = "anthropic/claude-haiku-4.5"
    llm_provider: str = "openrouter"
    llm_api_base: str | None = None
    allow: tuple[str, ...] = ()  # Q-80 capabilities the owner turns on, each a risk label

    @property
    def audience(self) -> str:
        return f"https://{self.host}:{self.port}/mcp"


@dataclass
class System:
    """Where the install writes and what it runs. `live` False: nothing runs, commands are listed."""

    root: Path = Path("/")
    live: bool = True
    ran: list[list[str]] = field(default_factory=list)

    def path(self, absolute: str) -> Path:
        return self.root / absolute.lstrip("/")

    def run(self, *command: str, check: bool = True) -> int:
        self.ran.append(list(command))
        if not self.live:
            return 0
        done = subprocess.run(list(command), check=False, capture_output=True, text=True)
        if check and done.returncode != 0:
            raise NeuroEdgeError(
                where=f"{WHERE}: {shlex.join(command)}",
                why=(done.stderr or done.stdout).strip() or f"exit {done.returncode}",
                how="fix the cause and run the install again: every step can be run twice",
            )
        return done.returncode


# Q-80: what each opt-in turns on in NeuroClaw's config, and the label it carries (Q-73).
ALLOWABLE = {
    "shell": (("tools", "exec", "enabled"),),
    "cron_shell": (("tools", "cron", "allow_command"),),
    "skill_install": (("tools", "install_skill", "enabled"),),
}


def labels(config: dict) -> list[str]:
    """`risk=<name>` for every Q-80 capability on in a NeuroClaw config (DP-COM-06)."""
    found = []
    for name, paths in ALLOWABLE.items():
        for path in paths:
            node = config
            for key in path:
                node = node.get(key, {}) if isinstance(node, dict) else {}
            if node is True:
                found.append(f"risk={name}")
                break
    tools = config.get("tools", {})
    if any(tools.get(bus, {}).get("enabled") for bus in ("i2c", "spi", "serial")):
        found.append("risk=hardware_bus")
    return found


def read_env_file(path: Path) -> dict[str, str]:
    """`KEY=value` lines (`#` comments, optional quotes), as the demo's `.env.txt`."""
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.removeprefix("export ").split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def settings_from_env(agent: Path, env: dict[str, str], **chosen) -> Settings:
    return Settings(
        agent=agent,
        telegram_token=env.get("TELEGRAM_BOT_TOKEN") or None,
        telegram_owner=env.get("TELEGRAM_OWNER_ID") or None,
        telegram_base_url=env.get("TELEGRAM_BASE_URL") or None,
        llm_key=env.get("LLM_API_KEY") or env.get("OPENROUTER_API_KEY") or None,
        llm_model=env.get("LLM_MODEL") or Settings.llm_model,
        llm_provider=env.get("LLM_PROVIDER") or Settings.llm_provider,
        llm_api_base=env.get("LLM_API_BASE") or None,
        **chosen,
    )


# --- files ------------------------------------------------------------------------------------


def _write(path: Path, data: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    fd = os.open(
        temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), mode
    )
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def brain_config(settings: Settings, keys: str, home: str) -> dict:
    """NeuroClaw's config.json: the box over mTLS, every hardware tool off (Q-80 labels)."""
    model: dict = {
        "model_name": "nao",
        "provider": settings.llm_provider,
        "model": settings.llm_model,
    }
    if settings.llm_key:
        model["api_keys"] = [settings.llm_key]
    if settings.llm_api_base:
        model["api_base"] = settings.llm_api_base
    telegram: dict = {
        "enabled": bool(settings.telegram_token),
        "type": "telegram",
        "allow_from": [settings.telegram_owner] if settings.telegram_owner else [],
        "settings": {"streaming": {"enabled": False}},
    }
    if settings.telegram_token:
        telegram["settings"]["token"] = settings.telegram_token
    if settings.telegram_base_url:
        telegram["base_url"] = settings.telegram_base_url
    config = {
        "version": 3,
        "agents": {
            "defaults": {
                "workspace": f"{home}/workspace",
                "restrict_to_workspace": True,
                "model_name": "nao",
                "max_tokens": 4096,
                "max_tool_iterations": 10,
            }
        },
        "model_list": [model],
        "channel_list": {"telegram": telegram},
        "tools": {
            "exec": {"enabled": False},
            "i2c": {"enabled": False},
            "spi": {"enabled": False},
            "serial": {"enabled": False},
            "install_skill": {"enabled": False},
            "cron": {"enabled": True, "allow_command": False},
            "mcp": {
                "enabled": True,
                "discovery": {"enabled": False},
                "servers": {
                    "neuroedge": {
                        "enabled": True,
                        "type": "http",
                        "url": settings.audience,
                        "headers": {"Authorization": "Bearer TOKEN"},
                        "tls": {
                            "ca_file": f"{keys}/ca.pem",
                            "cert_file": f"{keys}/nao.pem",
                            "key_file": f"{keys}/nao.key",
                            "server_name": settings.host,
                        },
                    }
                },
            },
        },
        "devices": {"enabled": False, "monitor_usb": False},
        "hooks": {"enabled": False},
        "gateway": {"host": "127.0.0.1", "port": 18790, "log_level": "info"},
    }
    for name in settings.allow:
        if name not in ALLOWABLE:
            raise NeuroEdgeError(
                where=f"{WHERE} --allow {name}",
                why=f"not one of {sorted(ALLOWABLE)}",
                how="each opt-in is a NeuroClaw capability of Q-80, labelled risk=<name>",
            )
        for *parents, leaf in ALLOWABLE[name]:
            node = config
            for key in parents:
                node = node.setdefault(key, {})
            node[leaf] = True
    return config


def _neuroedge_command() -> list[str]:
    found = shutil.which("neuroedge")
    return [found] if found else [str(Path(sys.executable).resolve()), "-m", "neuroedge"]


def units(settings: Settings, groups: list[str], issuer: str) -> dict[str, str]:
    keys = "/var/lib/neuroedge/keys"
    serve = [
        *_neuroedge_command(),
        "mcp", "serve", "--http", "--ui",
        "--target", settings.target,
        "--agent", "/var/lib/neuroedge/agent/agent.toml",
        "--host", "0.0.0.0", "--port", str(settings.port),
        "--tls-cert", f"{keys}/hop.pem", "--tls-key", f"{keys}/hop.key",
        "--client-ca", f"{keys}/ca.pem",
        "--issuer", issuer, "--audience", settings.audience,
        "--jwks", f"{keys}/jwks.json", "--revoked", f"{keys}/revoked.txt",
    ]  # fmt: skip
    hardening = (
        "NoNewPrivileges=yes\nProtectSystem=strict\nProtectHome=yes\nPrivateTmp=yes\n"
        "ProtectKernelTunables=yes\nProtectKernelModules=yes\nProtectControlGroups=yes\n"
    )
    return {
        "neuroedge-hidepid.service": (
            "# Q-83 DP-A-03: no user reads another's command line or environment.\n"
            "[Unit]\nDescription=Mount /proc with hidepid=2 (NeuroEdge)\nDefaultDependencies=no\n"
            "Before=neuroedge-box.service neuroclaw.service\n\n"
            "[Service]\nType=oneshot\nRemainAfterExit=yes\n"
            "ExecStart=/bin/mount -o remount,hidepid=2 /proc\n\n"
            "[Install]\nWantedBy=multi-user.target\n"
        ),
        "neuroedge-box.service": (
            "# Q-83 Profile A: the box. Its page link (ui.json) is in its state directory;\n"
            "# `sudo -u neuroedge neuroedge ui-link` prints a fresh one (DP-A-10).\n"
            "[Unit]\nDescription=NeuroEdge box (gate, devices, MCP over mTLS)\n"
            "After=network-online.target neuroedge-hidepid.service\nWants=network-online.target\n\n"
            f"[Service]\nUser={BOX_USER}\nGroup={BOX_USER}\n"
            + (f"SupplementaryGroups={' '.join(groups)}\n" if groups else "")
            + "StateDirectory=neuroedge\nStateDirectoryMode=0750\nEnvironment=NEUROEDGE_SERVICE=1\n"
            f"ExecStart={shlex.join(serve)}\nStandardInput=null\nRestart=on-failure\n"
            "ReadWritePaths=/var/lib/neuroedge\n" + hardening + "\n"
            "[Install]\nWantedBy=multi-user.target\n"
        ),
        "neuroclaw.service": (
            "# Q-83 Profile A: the brain. No device, no other user's processes, nothing to write\n"
            "# outside its own directory (DP-A-03).\n"
            "[Unit]\nDescription=NeuroClaw brain (talks to the box over MCP only)\n"
            "After=neuroedge-box.service neuroedge-hidepid.service\nWants=neuroedge-box.service\n\n"
            f"[Service]\nUser={BRAIN_USER}\nGroup={BRAIN_USER}\n"
            "Environment=NEUROCLAW_HOME=/var/lib/neuroclaw\n"
            "Environment=NEUROCLAW_CONFIG=/var/lib/neuroclaw/config.json\n"
            "ExecStart=/var/lib/neuroclaw/bin/neuroclaw gateway\nRestart=on-failure\n"
            "ReadWritePaths=/var/lib/neuroclaw\nPrivateDevices=yes\nProtectProc=invisible\n"
            "ProcSubset=pid\nRestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX\n" + hardening + "\n"
            "[Install]\nWantedBy=multi-user.target\n"
        ),
    }


# --- NeuroClaw, pinned (DP-NF-02) ---------------------------------------------------------------


def load_pins() -> dict:
    return json.loads(PINS.read_text(encoding="utf-8"))


def fetch_brain(destination: Path, machine: str | None = None) -> str:
    """The pinned release's `neuroclaw` binary at `destination`; its archive checked first."""
    pins = load_pins()
    machine = machine or platform.machine()
    asset = pins["assets"].get({"arm64": "aarch64", "amd64": "x86_64"}.get(machine, machine))
    if asset is None:
        raise NeuroEdgeError(
            where=f"{WHERE} ({PINS.name})",
            why=f"no NeuroClaw {pins['version']} build is pinned for {machine}",
            how="run on x86_64 or aarch64 Linux, or pin a build for this machine in one commit",
        )
    url = f"{pins['repository']}/releases/download/{pins['version']}/{asset['name']}"
    try:
        with urllib.request.urlopen(url, timeout=120) as response:  # noqa: S310 - https, pinned
            data = response.read()
    except OSError as error:
        raise NeuroEdgeError(
            where=f"{WHERE} ({url})",
            why=f"cannot fetch NeuroClaw {pins['version']}: {error}",
            how="check the network and run the install again",
        ) from error
    found = hashlib.sha256(data).hexdigest()
    if found != asset["sha256"]:
        raise NeuroEdgeError(
            where=f"{WHERE} ({PINS.name})",
            why=f"{asset['name']} has SHA-256 {found}, the pin says {asset['sha256']}",
            how="nothing was unpacked; fetch again, and if it persists the release changed",
        )
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        member = archive.getmember("neuroclaw")
        extracted = archive.extractfile(member) if member.isfile() else None
        if extracted is None:
            raise NeuroEdgeError(
                where=f"{WHERE} ({asset['name']})",
                why="the archive holds no regular file named neuroclaw",
                how="the release is not what the pin names; do not install it",
            )
        _write(destination, extracted.read(), 0o755)
    return f"{pins['version']} ({asset['name']}, sha256 {found[:12]})"


# --- the install ---------------------------------------------------------------------------------


def _existing_groups(groups: tuple[str, ...]) -> list[str]:
    import grp

    found = []
    for name in groups:
        try:
            grp.getgrnam(name)
        except KeyError:
            continue
        found.append(name)
    return found


def install(
    settings: Settings, system: System, *, start: bool = True, fetch=fetch_brain
) -> list[str]:
    """Every step, in order; returns what was done, one line each. Running it twice is safe."""
    if system.live and os.geteuid() != 0:
        raise NeuroEdgeError(
            where=WHERE,
            why="it makes system users, writes /etc/systemd and /var/lib and mounts /proc",
            how="run it as root (sudo), or stage it with --root <dir> to read what it would do",
        )
    if not (settings.agent / "agent.toml").is_file():
        raise NeuroEdgeError(
            where=f"{WHERE} --agent {settings.agent}",
            why="no agent.toml in that directory",
            how="pass the agent's directory (fixtures/agents/chat-den-cua, or your own)",
        )
    done: list[str] = []
    groups = _existing_groups(DEVICE_GROUPS) if settings.target == "linux" and system.live else []

    # users: the brain in no group at all
    for user in (BOX_USER, BRAIN_USER):
        if system.live:
            if system.run("id", user, check=False) != 0:
                system.run(
                    "useradd", "--system", "--no-create-home", "--shell", "/usr/sbin/nologin", user
                )
        else:
            system.run(
                "useradd", "--system", "--no-create-home", "--shell", "/usr/sbin/nologin", user
            )
    if groups:
        system.run("usermod", "--append", "--groups", ",".join(groups), BOX_USER)
    done.append(f"users {BOX_USER} (groups: {', '.join(groups) or 'none'}), {BRAIN_USER} (none)")

    # the box: its agent and its keys
    box = system.path("/var/lib/neuroedge")
    agent = box / "agent"
    if agent.exists():
        shutil.rmtree(agent)
    shutil.copytree(settings.agent, agent, ignore=shutil.ignore_patterns("build", "__pycache__"))
    keys = box / "keys"
    if not (keys / "hop.json").is_file():
        pairing.create(keys, settings.audience, hosts=[settings.host, "127.0.0.1", "localhost"])
        done.append(f"keys for {settings.audience}")
    else:
        pairing.renew(keys)
        done.append("keys kept; a fresh brain token (pair renew)")
    issuer = json.loads((keys / "hop.json").read_text())["issuer"]

    # the brain: its four files, its config, its binary
    brain = system.path("/var/lib/neuroclaw")
    brain_keys = brain / "keys"
    brain_keys.mkdir(mode=0o700, parents=True, exist_ok=True)
    for name in BRAIN_FILES:
        _write(brain_keys / name, (keys / name).read_bytes(), 0o600 if name != "ca.pem" else 0o644)
    config = brain_config(settings, "/var/lib/neuroclaw/keys", "/var/lib/neuroclaw")
    token = (keys / "nao.token").read_text().strip()
    config["tools"]["mcp"]["servers"]["neuroedge"]["headers"]["Authorization"] = f"Bearer {token}"
    _write(brain / "config.json", json.dumps(config, indent=2).encode(), 0o600)
    done.extend(labels(config) or ["no risk label: every Q-80 capability off"])
    (brain / "workspace").mkdir(parents=True, exist_ok=True)
    done.append(f"NeuroClaw {fetch(brain / 'bin' / 'neuroclaw')}")

    # ownership: each its own, nothing shared
    system.run("chown", "-R", f"{BOX_USER}:{BOX_USER}", str(box))
    system.run("chmod", "0750", str(box))
    system.run("chmod", "0700", str(keys))
    system.run("chown", "-R", f"{BRAIN_USER}:{BRAIN_USER}", str(brain))
    system.run("chmod", "0700", str(brain))

    # the units
    for name, text in units(settings, groups, issuer).items():
        _write(system.path(f"/etc/systemd/system/{name}"), text.encode(), 0o644)
    system.run("systemctl", "daemon-reload")
    if start:
        system.run("systemctl", "enable", "--now", *UNITS)
        done.append(f"started {', '.join(UNITS)}")
    else:
        system.run("systemctl", "enable", *UNITS)
        done.append(f"enabled {', '.join(UNITS)} (not started: --no-start)")
    return done
