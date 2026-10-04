"""
The villa-concierge kit's door lock on a real kernel (TSK-I2b-01).

Run by the `linux-hal` CI job after `scripts/setup_gpio_sim.sh`:

    cd python && python -m pytest -q tests_linux

`door_lock` is a gpio-sim line; its level is read from sysfs, independently of the process that
drives it. A missing chip is a failure, never a skip.

The kit as shipped asks for hardware echo cancellation (`audio.in` with `aec = true`) that the
`linux-rpi5` profile does not declare (`aec = false`), so `neuroedge build --target linux` refuses
it (NE3003) — the first test pins that. What the Pi can run is the lock and its gate: the other
tests use a copy of the agent whose `[requires]` keeps only what the lock needs. The gate, the
action and the pin are the kit's own.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import time
from pathlib import Path

import pytest

from neuroedge.errors import BuildFailed
from neuroedge.paths import fixtures_dir
from neuroedge.sim import SimSession
from neuroedge.testing import assert_matches_golden, replay

AGENT = fixtures_dir() / "agents" / "villa-concierge" / "agent.toml"
GOLDEN = fixtures_dir() / "traces" / "kits"
# The lines in the order `scripts/setup_gpio_sim.sh` creates them: sim_gpioN is the N-th.
LINES = [
    "door_lock",
    "porch_light",
    "gate_relay",
    "door_contact_raw",
    "limit_switch",
    "fan_en",
    "motor_en",
    "servo_en",
]


@pytest.fixture(scope="module")
def sysfs() -> Path:
    path = os.environ.get("NEUROEDGE_GPIO_SIM_SYSFS")
    assert path, "run scripts/setup_gpio_sim.sh first; it exports NEUROEDGE_GPIO_SIM_SYSFS"
    return Path(path)


def kernel_value(sysfs: Path, pin: str) -> int:
    return int((sysfs / f"sim_gpio{LINES.index(pin)}" / "value").read_text().strip())


def wait_for(sysfs: Path, pin: str, value: int, timeout: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if kernel_value(sysfs, pin) == value:
            return True
        time.sleep(0.01)
    return False


def pi_variant(tmp_path: Path) -> Path:
    """The kit's agent without the voice front-end the Pi 5 profile cannot carry."""
    target = tmp_path / "villa"
    shutil.copytree(AGENT.parent, target)
    manifest = target / "agent.toml"
    kept = [
        text
        for text in manifest.read_text("utf-8").splitlines()
        if not text.startswith(('"audio.in"', '"audio.out"', '"display"'))
    ]
    manifest.write_text("\n".join(kept) + "\n", encoding="utf-8")
    return manifest


def say(session: SimSession, text: str):
    return asyncio.run(session.handle(text))


def test_the_kit_as_shipped_is_refused_on_the_pi_and_no_line_moves(sysfs):
    with pytest.raises(BuildFailed, match="NE3003"):
        SimSession.load(AGENT, target="linux")
    assert kernel_value(sysfs, "door_lock") == 0


def test_an_allowed_unlock_drives_the_kernel_line_and_the_session_ends_with_it_low(
    sysfs, tmp_path, fresh_actions
):
    session = SimSession.load(pi_variant(tmp_path), target="linux")
    try:
        turn = say(session, "mở cửa phòng 101")
        assert turn.allowed
        assert wait_for(sysfs, "door_lock", 1), "the unlock pulse reaches the kernel line"
    finally:
        session.close()
    assert kernel_value(sysfs, "door_lock") == 0, "close drops the line, 30 s pulse or not"


@pytest.mark.parametrize(
    ("facts", "text", "criterion"),
    [
        ({}, "mở cửa phòng 202", "room_matches"),
        ({}, "mở cửa", "room_matches"),
        ({"risk_level": "high"}, "mở cửa phòng 101", "risk_level"),
    ],
    ids=["the wrong room", "no room", "a risky guest"],
)
def test_a_blocked_unlock_never_drives_the_kernel_line(
    sysfs, tmp_path, fresh_actions, facts, text, criterion
):
    session = SimSession.load(pi_variant(tmp_path), target="linux", facts=facts)
    try:
        turn = say(session, text)
        assert turn.result is not None and turn.result.blocked
        assert turn.result.gate.failed_criterion == criterion
        assert not wait_for(sysfs, "door_lock", 1, timeout=0.3), "a BLOCK never moves the lock"
    finally:
        session.close()
    assert kernel_value(sysfs, "door_lock") == 0


@pytest.mark.parametrize("name", ["villa-concierge-allow", "villa-concierge-block"])
def test_the_golden_traces_replay_on_the_kernel_lines_as_recorded(name, sysfs):
    path = GOLDEN / f"{name}.json"
    linux = replay(path, target="linux", agent=AGENT, board_id="linux-rpi5")
    assert linux.verdicts == linux.recorded_verdicts
    assert linux.warnings == [] and linux.divergences == []
    assert_matches_golden(linux, path)
    assert kernel_value(sysfs, "door_lock") == 0, "replay releases the lines when it ends"
