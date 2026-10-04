"""
The factory-monitor kit's exhaust relay and alarm siren on a real kernel (TSK-I2b-01).

Run by the `linux-hal` CI job after `scripts/setup_gpio_sim.sh` and `scripts/setup_i2c_stub.sh`:

    cd python && python -m pytest -q tests_linux

`gate_relay` (the exhaust fan or valve) and `porch_light` (the siren) are gpio-sim lines read from
sysfs independently of the process that drives them; the temperature is an LM75 at 0x48 on i2c-stub,
read back through the kernel's lm75 driver and hwmon, as it would be on a Pi
(`NEUROEDGE_LINUX_SENSORS=temperature=hwmon:lm75/temp1`). A missing device is a failure, never a skip.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import time
from pathlib import Path

import pytest

from neuroedge.hal.linux import SENSORS_ENV
from neuroedge.hal.sysfs import SensorSource
from neuroedge.paths import fixtures_dir
from neuroedge.sim import SimSession
from neuroedge.testing import assert_matches_golden, replay

AGENT = fixtures_dir() / "agents" / "factory-monitor" / "agent.toml"
GOLDEN = fixtures_dir() / "traces" / "kits"
ADDR = "0x48"
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


def env(name: str) -> str:
    value = os.environ.get(name)
    assert value, f"{name} is not set; run the setup script that exports it first"
    return value


@pytest.fixture(scope="module")
def sysfs() -> Path:
    return Path(env("NEUROEDGE_GPIO_SIM_SYSFS"))


def kernel_value(sysfs: Path, pin: str) -> int:
    return int((sysfs / f"sim_gpio{LINES.index(pin)}" / "value").read_text().strip())


def wait_for(sysfs: Path, pin: str, value: int, timeout: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if kernel_value(sysfs, pin) == value:
            return True
        time.sleep(0.01)
    return False


def set_temperature(celsius: float) -> None:
    """Write the LM75 temperature register (9-bit, 0.5 °C steps) through i2c-stub."""
    register = (round(celsius * 2) & 0x1FF) << 7
    word = ((register & 0xFF) << 8) | (register >> 8)  # SMBus words are little-endian
    bus = env("NEUROEDGE_I2C_STUB_BUS")
    subprocess.run(["i2cset", "-f", "-y", bus, ADDR, "0x00", f"0x{word:04x}", "w"], check=True)


def heat(session: SimSession, celsius: float, timeout: float = 3.0) -> None:
    """Set the chip, then wait until the driver reports it (lm75 refreshes about every 1.5 s)."""
    set_temperature(celsius)
    deadline = time.monotonic() + timeout
    while session.hal.sensor_read("temperature", called_from="test") != celsius:
        assert time.monotonic() < deadline, f"the lm75 never reported {celsius} °C"
        time.sleep(0.05)


def say(session: SimSession, text: str):
    return asyncio.run(session.handle(text))


@pytest.fixture
def rig(monkeypatch):
    """The kit's wiring as its page describes it: the LM75 is the board's `temperature`."""
    env("NEUROEDGE_LM75_DEVICE")
    monkeypatch.setenv(SENSORS_ENV, "temperature=hwmon:lm75/temp1")
    set_temperature(30.0)
    yield
    set_temperature(25.0)


def test_the_fan_and_the_siren_follow_the_gates_and_a_block_never_switches_off(rig, sysfs):
    session = SimSession.load(AGENT, target="linux")
    try:
        heat(session, 30.0)
        assert say(session, "bật quạt").allowed and wait_for(sysfs, "gate_relay", 1)
        assert say(session, "bật báo động").allowed and wait_for(sysfs, "porch_light", 1)

        heat(session, 45.0)  # high: stopping the fan asks, silencing the alarm is refused
        asked = say(session, "tắt quạt")
        assert asked.result.blocked and asked.confirmation is not None
        heat(session, 60.0)  # critical: refused without a question
        refused = say(session, "tắt quạt")
        assert refused.result.blocked and refused.confirmation is None
        assert say(session, "tắt báo động").result.blocked
        assert kernel_value(sysfs, "gate_relay") == 1, "no BLOCK stopped the fan"
        assert kernel_value(sysfs, "porch_light") == 1, "no BLOCK silenced the siren"

        heat(session, 30.0)  # the room has cooled
        assert say(session, "tắt báo động").allowed and wait_for(sysfs, "porch_light", 0)
        assert say(session, "tắt quạt").allowed and wait_for(sysfs, "gate_relay", 0)
    finally:
        session.close()
    assert kernel_value(sysfs, "gate_relay") == 0 and kernel_value(sysfs, "porch_light") == 0


def test_a_sensor_that_is_gone_blocks_every_switch_off_and_still_lets_the_safe_ones_through(
    rig, sysfs
):
    session = SimSession.load(AGENT, target="linux")  # preflight read the healthy chip
    try:
        assert say(session, "bật quạt").allowed and wait_for(sysfs, "gate_relay", 1)
        # What a pulled sensor looks like: the source now names a device the kernel does not have.
        session.hal.sensors.sources["temperature"] = SensorSource.parse(
            "temperature", "hwmon:lm76/temp1", "test"
        )
        off = say(session, "tắt quạt")
        assert off.result.blocked and off.confirmation is None
        assert off.result.gate.reason.value == "criterion_unavailable"
        assert kernel_value(sysfs, "gate_relay") == 1
        assert say(session, "bật báo động").allowed and wait_for(sysfs, "porch_light", 1)
    finally:
        session.close()


@pytest.mark.parametrize("name", ["factory-monitor-allow", "factory-monitor-block"])
def test_the_golden_traces_replay_on_the_kernel_lines_as_recorded(name, sysfs):
    path = GOLDEN / f"{name}.json"
    linux = replay(path, target="linux", agent=AGENT, board_id="linux-rpi5")
    assert linux.verdicts == linux.recorded_verdicts
    assert linux.warnings == [] and linux.divergences == []
    assert_matches_golden(linux, path)
    assert kernel_value(sysfs, "gate_relay") == 0 and kernel_value(sysfs, "porch_light") == 0
