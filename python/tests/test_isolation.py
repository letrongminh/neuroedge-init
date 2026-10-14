"""
TSK-I2d-24, Q-83 (DP-A-03) — `neuroedge doctor` names every way the brain's user reaches the box.

The checks read a `System`; here it is a fake one: files in a temporary directory with the modes
a real box would have, an account that is not the file owner, and a `/proc/mounts` line.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from neuroedge import isolation
from neuroedge.cli.main import app

HIDEPID = "proc /proc proc rw,nosuid,nodev,noexec,relatime,hidepid=2 0 0\n"
OPEN_PROC = "proc /proc proc rw,nosuid,nodev,noexec,relatime 0 0\n"


@pytest.fixture
def box(tmp_path) -> Path:
    """A key directory and a device node as the box keeps them (owned by this test's user)."""
    keys = tmp_path / "keys"
    keys.mkdir(mode=0o700)
    for name in ("issuer.key", "ca.key", "hop.key"):
        (keys / name).write_text("secret")
        (keys / name).chmod(0o600)
    dev = tmp_path / "dev"
    dev.mkdir()
    (dev / "gpiochip0").write_text("")
    (dev / "gpiochip0").chmod(0o660)
    return tmp_path


def brain(**groups: int) -> isolation.Account:
    """Not the owner of the box's files; in `groups` only."""
    return isolation.Account("neuroclaw", os.getuid() + 1000, 4242, dict(groups))


def check(box: Path, account, mounts=HIDEPID) -> list[str]:
    return isolation.problems(isolation.System(account, mounts, box / "dev"), box / "keys")


def test_a_brain_kept_apart_has_no_problem(box):
    assert check(box, brain(neuroclaw=4242)) == []


def test_a_brain_in_a_device_group_is_named(box):
    """TC-A-03-1: in group gpio (and so able to open the chip, which belongs to that group)."""
    found = check(box, brain(gpio=os.getgid()))
    assert "neuroclaw is in group gpio: it can drive devices" in found
    assert any(p.startswith("neuroclaw can open") and "gpiochip0" in p for p in found)


def test_a_brain_that_can_read_the_keys_is_named(box):
    """TC-A-03-1: the key directory and a key file readable by other users."""
    (box / "keys").chmod(0o755)
    (box / "keys" / "issuer.key").chmod(0o644)
    found = check(box, brain())
    assert f"neuroclaw can read the key directory {box / 'keys'}" in found
    assert f"neuroclaw can read {box / 'keys' / 'issuer.key'}" in found
    assert not any("ca.key" in p for p in found)


def test_proc_without_hidepid_is_named(box):
    """TC-A-03-1: without hidepid=2 the brain reads the box's command line and environment."""
    assert [p for p in check(box, brain(), OPEN_PROC) if p.startswith("/proc")]


def test_a_readable_key_deeper_in_the_directory_is_named(box):
    """TC-A-03-1: every file under the key directory, not only its first level."""
    nested = box / "keys" / "old"
    nested.mkdir(mode=0o700)
    (nested / "issuer.key").write_text("secret")
    (nested / "issuer.key").chmod(0o644)
    nested.chmod(0o755)
    (box / "keys").chmod(0o711)  # not listable, but the brain can go through it
    found = check(box, brain())
    assert f"neuroclaw can read {nested}" in found
    assert f"neuroclaw can read {nested / 'issuer.key'}" in found


def test_public_files_behind_a_closed_directory_are_not_named(box):
    """TC-A-03-2 as `neuroedge pair init` leaves it: 0644 certificates in a 0700 directory."""
    for name in ("ca.pem", "hop.pem", "jwks.json"):
        (box / "keys" / name).write_text("public")
        (box / "keys" / name).chmod(0o644)
    assert check(box, brain()) == []


def test_the_last_mount_of_proc_is_the_one_in_force(box):
    assert [p for p in check(box, brain(), HIDEPID + OPEN_PROC) if p.startswith("/proc")]
    assert check(box, brain(neuroclaw=4242), OPEN_PROC + HIDEPID) == []


def test_a_brain_in_procs_exempt_group_is_named(box):
    exempt = HIDEPID.replace("hidepid=2", "hidepid=2,gid=4243")
    found = check(box, brain(neuroclaw=4242, monitor=4243), exempt)
    assert any("exempt group (gid=4243)" in p for p in found)
    assert check(box, brain(neuroclaw=4242), exempt) == []


def test_root_and_a_missing_user_fail_closed(box):
    assert check(box, None) and "no such user" in check(box, None)[0]
    assert "neuroclaw is root" in check(box, isolation.Account("neuroclaw", 0, 0, {}))


def test_doctor_exits_one_naming_each_problem(box, monkeypatch):
    """TC-A-03-1 through the command: exit 1, each problem on its own line; exit 0 when clean."""
    (box / "keys").chmod(0o755)
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(
        isolation.System,
        "live",
        classmethod(lambda cls, user: cls(brain(gpio=4), OPEN_PROC, box / "dev")),
    )
    result = CliRunner().invoke(app, ["doctor", "--keys", str(box / "keys")])
    assert result.exit_code == 1
    assert "group gpio" in result.output and "key directory" in result.output
    assert "hidepid" in result.output
    (box / "keys").chmod(0o700)
    monkeypatch.setattr(
        isolation.System, "live", classmethod(lambda cls, user: cls(brain(), HIDEPID, box / "dev"))
    )
    result = CliRunner().invoke(app, ["doctor", "--keys", str(box / "keys")])
    assert result.exit_code == 0, result.output
