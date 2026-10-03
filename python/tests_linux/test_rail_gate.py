"""
The sensor-pack sample agent `rail-gate` on a real kernel (TSK-I2a-02/03/04, I2a exit criterion 3).

Run by the `linux-hal` CI job after `scripts/setup_gpio_sim.sh` (the lines `gate_relay` and
`limit_switch`) and `scripts/setup_i2c_stub.sh` (an `ads7828` bound to its hwmon driver at 0x4a,
an `ina219` at 0x40 with no driver):

    cd python && python -m pytest -q tests_linux

Every primitive of the pack goes through the kernel: the limit switch is a gpio-sim line whose
`pull` is its level (`digital.in`), the rail is the ADC's channel 0 read through hwmon
(`analog.in`), the supply is the ina219's bus-voltage register read over `/dev/i2c-N` (`i2c`), and
the gate relay is a gpio-sim output. A missing device is a failure, never a skip.

ADC codes: `in0_input = round(code * 610 / 1000)` mV (the driver's integer LSB, 2.5 V / 4096), so
2951 -> 1800 mV and 1639 -> 1000 mV. ina219 register 0x02 holds `(mV / 4) << 3` in wire order:
12 000 mV is 0x5dc0, which `i2cset ... w` takes byte-swapped (0xc05d, an SMBus word being
little-endian).
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import time
from pathlib import Path

import pytest

from neuroedge.hal.linux import ANALOG_ENV, DISPLAY_ENV, I2C_ENV
from neuroedge.hal.sysfs import SensorSource
from neuroedge.paths import fixtures_dir
from neuroedge.sim import SimSession
from neuroedge.testing import assert_matches_golden, replay

AGENT = fixtures_dir() / "agents" / "rail-gate" / "agent.toml"
PINS = ["door_lock", "porch_light", "gate_relay"]  # the outputs, first on the chip
INPUTS = ["door_contact_raw", "limit_switch"]
INA219, ADS7828 = "0x40", "0x4a"
HEALTHY_CODE, SAGGING_CODE = 2951, 1639  # 1.8 V and 1.0 V on the channel (the gate wants 1.2 V)


def env(name: str) -> str:
    value = os.environ.get(name)
    assert value, f"{name} is not set; run the setup script that exports it first"
    return value


def i2cset(address: str, register: int, value: int) -> None:
    subprocess.run(
        [
            "i2cset",
            "-f",
            "-y",
            env("NEUROEDGE_I2C_STUB_BUS"),
            address,
            hex(register),
            hex(value),
            "w",
        ],
        check=True,
    )


def set_adc(code: int) -> None:
    """The 12-bit conversion result of channel 0 (an SMBus word is little-endian)."""
    i2cset(ADS7828, 0x8C, ((code & 0xFF) << 8) | (code >> 8))


def set_supply(millivolts: int) -> None:
    raw = (millivolts // 4) << 3  # ina219 bus voltage: 4 mV steps in bits 15..3
    i2cset(INA219, 0x02, ((raw & 0xFF) << 8) | (raw >> 8))


def pull(sysfs: Path, pin: str, high: bool) -> None:
    """What a switch wired to the line does: gpio-sim's `pull` is the level an input reads."""
    index = [*PINS, *INPUTS].index(pin)
    (sysfs / f"sim_gpio{index}" / "pull").write_text("pull-up" if high else "pull-down")


def kernel_value(sysfs: Path, pin: str) -> int:
    return int((sysfs / f"sim_gpio{PINS.index(pin)}" / "value").read_text().strip())


def wait_for(sysfs: Path, pin: str, value: int, timeout: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout
    while kernel_value(sysfs, pin) != value:
        if time.monotonic() > deadline:
            return False
        time.sleep(0.02)
    return True


@pytest.fixture
def sysfs() -> Path:
    return Path(env("NEUROEDGE_GPIO_SIM_SYSFS"))


@pytest.fixture
def rig(monkeypatch, sysfs):
    """The machine's wiring, as the sample agent's README would set it, and a healthy rig."""
    monkeypatch.setenv(ANALOG_ENV, f"adc0=hwmon:ads7828@{env('NEUROEDGE_ADS7828_DEVICE')}/in0")
    monkeypatch.setenv(I2C_ENV, f"i2c1=/dev/i2c-{env('NEUROEDGE_I2C_STUB_BUS')}")
    monkeypatch.setenv(DISPLAY_ENV, "memory")
    pull(sysfs, "limit_switch", True)
    set_adc(HEALTHY_CODE)
    set_supply(12000)
    yield
    pull(sysfs, "limit_switch", True)
    set_adc(0x800)


async def tool(session: SimSession, name: str):
    from neuroedge.actions.tools import ToolCall

    return (await session.call_tool(ToolCall(name, {}, source="local_grammar"))).action


def test_a_closed_gate_on_a_healthy_rail_opens_the_relay_and_the_report_reads_the_ina219(
    rig, sysfs
):
    session = SimSession.load(AGENT, target="linux")
    try:
        report = asyncio.run(tool(session, "rail_report"))
        assert not report.blocked and session.hal.frames[-1].text == "Nguồn: 12000 mV"
        assert session.events.of_type("i2c_read") == [
            {"bus": "i2c1", "device": "ina219", "address": 0x40, "register": 2, "value": 24000}
        ]
        opened = asyncio.run(tool(session, "rail_open_gate"))
        assert not opened.blocked and wait_for(sysfs, "gate_relay", 1)
        facts = session.events.of_type("gate_facts")[-1]
        assert (
            facts["limit_closed"]["value"] is True
            and facts["limit_closed"]["source"] == "digital.in"
        )
        assert facts["rail_voltage"]["value"] == 1.8 and facts["rail_voltage"]["age_ms"] >= 0
    finally:
        session.close()
    assert kernel_value(sysfs, "gate_relay") == 0, "the session ends with every line low"


@pytest.mark.parametrize(
    ("set_up", "criterion"),
    [
        (lambda sysfs: set_adc(SAGGING_CODE), "rail_voltage"),
        (lambda sysfs: pull(sysfs, "limit_switch", False), "limit_closed"),
    ],
    ids=["a sagging rail", "a gate off its stop"],
)
def test_a_condition_the_gate_does_not_admit_never_moves_the_relay(rig, sysfs, set_up, criterion):
    session = SimSession.load(AGENT, target="linux")
    try:
        set_up(sysfs)
        action = asyncio.run(tool(session, "rail_open_gate"))
        assert action.blocked and action.gate.reason == "condition_not_met"
        assert action.gate.failed_criterion == criterion
        assert kernel_value(sysfs, "gate_relay") == 0
    finally:
        session.close()


def test_an_adc_that_is_not_there_blocks_criterion_unavailable(rig, sysfs):
    session = SimSession.load(AGENT, target="linux")  # preflight read the healthy ADC
    try:
        # Re-map the channel to a device the kernel does not have: what a pulled ADC looks like.
        session.hal.analog.sources["adc0"] = SensorSource.parse("adc0", "hwmon:ads7829/in0", "test")
        action = asyncio.run(tool(session, "rail_open_gate"))
        assert action.blocked and action.gate.reason == "criterion_unavailable"
        assert action.gate.failed_criterion == "rail_voltage"
        assert "error" in session.events.of_type("analog_in")[-1]
        assert kernel_value(sysfs, "gate_relay") == 0
    finally:
        session.close()


def test_a_session_recorded_on_the_kernel_replays_the_same_on_sim_and_linux(rig, sysfs, tmp_path):
    session = SimSession.load(AGENT, target="linux")
    out = tmp_path / "rail.json"
    try:
        asyncio.run(tool(session, "rail_report"))
        asyncio.run(tool(session, "rail_open_gate"))
        wait_for(sysfs, "gate_relay", 1)
        set_adc(SAGGING_CODE)
        asyncio.run(tool(session, "rail_open_gate"))
        session.write_trace(out)
    finally:
        session.close()
    sim = replay(out, target="sim", agent=AGENT, board_id="sim-rpi5")
    linux = replay(out, target="linux", agent=AGENT, board_id="linux-rpi5")
    assert linux.verdicts == sim.verdicts == sim.recorded_verdicts == ["ALLOW", "ALLOW", "BLOCK"]
    assert sim.warnings == [] and linux.warnings == []
    assert_matches_golden(sim, out)
    assert_matches_golden(linux, out)
