"""
The aquarium sample's heater, air pump and light on a real kernel (demo/i2b-be-ca-gia-lap/, D2).

Run by the `linux-hal` CI job after `scripts/setup_gpio_sim.sh` and `scripts/setup_i2c_stub.sh`:

    cd python && python -m pytest -q tests_linux

`gate_relay` (the heater), `door_lock` (the air pump) and `porch_light` (the tank light) are
gpio-sim lines read from sysfs independently of the process that drives them; the water
temperature is an LM75 at 0x48 on i2c-stub, read through the kernel's lm75 driver and hwmon
(`NEUROEDGE_LINUX_SENSORS=temperature=hwmon:lm75/temp1`). A missing device is a failure, never a
skip.
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

AGENT = fixtures_dir() / "agents" / "aquarium" / "agent.toml"
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
def tank(monkeypatch):
    """The kit's wiring: the LM75 is the board's `temperature`, in the water."""
    env("NEUROEDGE_LM75_DEVICE")
    monkeypatch.setenv(SENSORS_ENV, "temperature=hwmon:lm75/temp1")
    set_temperature(25.0)
    yield
    set_temperature(25.0)


def test_the_heater_and_the_air_pump_follow_the_water_and_a_block_never_switches(tank, sysfs):
    session = SimSession.load(AGENT, target="linux")
    try:
        heat(session, 25.0)
        assert say(session, "bật sưởi").allowed and wait_for(sysfs, "gate_relay", 1)
        assert say(session, "bật sục khí").allowed and wait_for(sysfs, "door_lock", 1)
        assert say(session, "bật đèn bể").allowed and wait_for(sysfs, "porch_light", 1)

        heat(session, 31.0)  # warm water: no heating, and the air pump is not turned off
        assert say(session, "bật sưởi").result.blocked
        refused = say(session, "tắt sục khí")
        assert refused.result.blocked and refused.confirmation is None
        assert kernel_value(sysfs, "door_lock") == 1, "no BLOCK stopped the air pump"
        assert say(session, "tắt sưởi").allowed and wait_for(sysfs, "gate_relay", 0)

        heat(session, 24.0)  # cool again: turning the pump off asks, and a yes does it
        asked = say(session, "tắt sục khí")
        assert asked.result.blocked and asked.confirmation is not None
        assert kernel_value(sysfs, "door_lock") == 1
        assert say(session, "có").allowed and wait_for(sysfs, "door_lock", 0)
        assert say(session, "tắt đèn bể").allowed and wait_for(sysfs, "porch_light", 0)
    finally:
        session.close()


def test_a_probe_that_is_gone_keeps_the_heater_off_and_the_air_pump_on(tank, sysfs):
    session = SimSession.load(AGENT, target="linux")  # preflight read the healthy chip
    try:
        assert say(session, "bật sục khí").allowed and wait_for(sysfs, "door_lock", 1)
        # What a pulled probe looks like: the source names a device the kernel does not have.
        session.hal.sensors.sources["temperature"] = SensorSource.parse(
            "temperature", "hwmon:lm76/temp1", "test"
        )
        on = say(session, "bật sưởi")
        assert on.result.blocked and on.result.gate.reason.value == "criterion_unavailable"
        off = say(session, "tắt sục khí")
        assert off.result.blocked and off.confirmation is None
        assert kernel_value(sysfs, "gate_relay") == 0
        assert kernel_value(sysfs, "door_lock") == 1
    finally:
        session.close()
