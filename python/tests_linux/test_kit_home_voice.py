"""
The home-voice kit's light on a real kernel (TSK-I2b-01).

Run by the `linux-hal` CI job after `scripts/setup_gpio_sim.sh`:

    cd python && python -m pytest -q tests_linux

`porch_light` is a gpio-sim line, read from sysfs independently of the process that drives it.

The kit's `motion` sensor has no kernel source: `linux` reads sensors from hwmon and IIO, and there
is no driver for a PIR on a GPIO line. So the session is refused until a source is named (Q-16: a
reading is never guessed), and a named source gives a number with a unit, never the true/false
`room_empty` asks for — `light_off` then stays blocked, `criterion_unavailable`. The stand-in
below is a hwmon device built in a temporary directory; it exists only to let the session start.
What the tests prove is the safe direction: the light turns on, and no BLOCK ever reaches the line.
"""

from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path

import pytest

import neuroedge.hal.sysfs as sysfs_module
from neuroedge.errors import BoardCapabilityError
from neuroedge.hal.linux import SENSORS_ENV
from neuroedge.paths import fixtures_dir
from neuroedge.sim import SimSession
from neuroedge.testing import assert_matches_golden, replay

AGENT = fixtures_dir() / "agents" / "home-voice" / "agent.toml"
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


@pytest.fixture
def stand_in_motion_source(monkeypatch, tmp_path):
    """A hwmon device `pir` reading 0, in a /sys of its own: the kernel has nothing for a PIR."""
    device = tmp_path / "sys" / "class" / "hwmon" / "hwmon0"
    device.mkdir(parents=True)
    (device / "name").write_text("pir\n")
    (device / "in0_input").write_text("0\n")
    monkeypatch.setattr(sysfs_module, "SYSFS_ROOT", str(tmp_path / "sys"))
    monkeypatch.setenv(SENSORS_ENV, "motion=hwmon:pir/in0")


def say(session: SimSession, text: str):
    return asyncio.run(session.handle(text))


def test_without_a_motion_source_the_session_is_refused_before_any_line_moves(sysfs):
    with pytest.raises(BoardCapabilityError, match="motion"):
        SimSession.load(AGENT, target="linux")
    assert kernel_value(sysfs, "porch_light") == 0


def test_the_light_turns_on_and_a_blocked_off_never_moves_the_line(sysfs, stand_in_motion_source):
    session = SimSession.load(AGENT, target="linux")
    try:
        assert say(session, "bật đèn").allowed
        assert wait_for(sysfs, "porch_light", 1), "light_on reaches the kernel line"
        off = say(session, "tắt đèn")
        assert off.result.blocked and off.result.gate.failed_criterion == "room_empty"
        assert off.result.gate.reason.value == "criterion_unavailable"
        assert not wait_for(sysfs, "porch_light", 0, timeout=0.3), "a BLOCK never moves the light"
    finally:
        session.close()
    assert kernel_value(sysfs, "porch_light") == 0, "the session ends with every line low"


@pytest.mark.parametrize("name", ["home-voice-allow", "home-voice-block"])
def test_the_golden_traces_replay_on_the_kernel_lines_as_recorded(name, sysfs):
    path = GOLDEN / f"{name}.json"
    linux = replay(path, target="linux", agent=AGENT, board_id="linux-rpi5")
    assert linux.verdicts == linux.recorded_verdicts
    assert linux.warnings == [] and linux.divergences == []
    assert_matches_golden(linux, path)
    assert kernel_value(sysfs, "porch_light") == 0, "replay releases the lines when it ends"
