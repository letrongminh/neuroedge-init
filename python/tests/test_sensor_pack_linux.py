"""
TSK-I2a-02/03/04 — the sample agent `rail-gate` as a live `linux` session, against fakes of the
kernel: an in-memory gpiod (the limit switch is an input line, the relay an output), a fake /sys
with an ads7828 (`in0_input`, millivolts) and a fake i2c-dev node answering the ina219.

The same agent against the real kernel (gpio-sim, `i2c-stub` + `ads7828`) is
`tests_linux/test_rail_gate.py`, run by the `linux-hal` CI job. Here every line of the wiring that
does not need a kernel — the environment names, the three input paths into one session, the
trace a linux session records and the replay of it on both targets — runs everywhere.
"""

from __future__ import annotations

import anyio
import pytest

import neuroedge.hal.linux as linux
import neuroedge.hal.sysfs as sysfs
from neuroedge.actions.tools import ToolCall
from neuroedge.errors import BoardCapabilityError
from neuroedge.hal.i2c_bus import I2C_SMBUS_READ
from neuroedge.sim import SimSession
from neuroedge.testing import assert_matches_golden, replay

from .test_digital_in_linux import WITH_INPUTS, drive
from .test_hal_i2c import FakeKernel
from .test_hal_linux import FakeGpiod, Value


@pytest.fixture
def agent(root):
    return root / "fixtures" / "agents" / "rail-gate" / "agent.toml"


@pytest.fixture
def rig(monkeypatch, tmp_path):
    """A healthy rig: gate at its stop, 1.8 V on the ADC, 12 000 mV on the ina219."""
    chip = tmp_path / "gpiochip0"
    chip.write_text("")
    fake = FakeGpiod({str(chip): WITH_INPUTS})
    monkeypatch.setattr(linux, "CHIP_GLOB", str(tmp_path / "gpiochip*"))
    monkeypatch.setattr(linux, "_import_gpiod", lambda: fake)
    where = (str(tmp_path / "gpiochip*"), str(chip))  # as test_digital_in_linux's `chip`
    drive(fake, where, "limit_switch", True)

    device = tmp_path / "sys" / "class" / "hwmon" / "hwmon2"
    device.mkdir(parents=True)
    (device / "name").write_text("ads7828\n")
    (device / "in0_input").write_text("1800\n")
    monkeypatch.setattr(sysfs, "SYSFS_ROOT", str(tmp_path / "sys"))
    monkeypatch.setenv(linux.ANALOG_ENV, "adc0=hwmon:ads7828/in0")

    # i2c-stub holds the register byte-swapped (an SMBus word is little-endian): 0xc05d is 0x5dc0.
    kernel = FakeKernel(monkeypatch, word=0xC05D)
    monkeypatch.setenv(linux.I2C_ENV, "i2c1=/dev/i2c-1")
    monkeypatch.setenv(linux.DISPLAY_ENV, "memory")
    return type(
        "Rig", (), {"gpio": fake, "adc": device / "in0_input", "kernel": kernel, "chip": where}
    )


async def tool(session, name):
    return (await session.call_tool(ToolCall(name, {}, source="local_grammar"))).action


def relay(rig) -> Value:
    return rig.gpio.values.get((rig.chip[1], WITH_INPUTS.index("gate_relay")), Value.INACTIVE)


def test_a_closed_gate_on_a_healthy_rail_opens_the_relay_and_the_report_reads_the_ina219(
    agent, rig
):
    session = SimSession.load(agent, target="linux")
    try:
        report = anyio.run(tool, session, "rail_report")
        assert not report.blocked and session.hal.frames[-1].text == "Nguồn: 12000 mV"
        opened = anyio.run(tool, session, "rail_open_gate")
        assert not opened.blocked and relay(rig) is Value.ACTIVE
        facts = session.events.of_type("gate_facts")[-1]
        assert facts["limit_closed"]["source"] == "digital.in" and facts["limit_closed"]["value"]
        assert facts["rail_voltage"]["value"] == 1.8 and facts["rail_voltage"]["age_ms"] >= 0
        assert session.events.of_type("analog_in")[-1]["unit"] == "V"
        assert {call[0] for call in rig.kernel.calls} <= {"open", "close", "slave", "smbus"}
        assert [call[1] for call in rig.kernel.smbus()] == [I2C_SMBUS_READ] * len(
            rig.kernel.smbus()
        )
    finally:
        session.close()
    assert relay(rig) is Value.INACTIVE


@pytest.mark.parametrize(
    ("set_up", "criterion"),
    [
        (lambda rig: rig.adc.write_text("999\n"), "rail_voltage"),
        (lambda rig: drive(rig.gpio, rig.chip, "limit_switch", False), "limit_closed"),
    ],
    ids=["a sagging rail", "a gate off its stop"],
)
def test_a_condition_the_gate_does_not_admit_never_moves_the_relay(agent, rig, set_up, criterion):
    session = SimSession.load(agent, target="linux")
    try:
        set_up(rig)
        action = anyio.run(tool, session, "rail_open_gate")
        assert action.blocked and action.gate.reason == "condition_not_met"
        assert action.gate.failed_criterion == criterion
        assert relay(rig) is Value.INACTIVE
    finally:
        session.close()


@pytest.mark.parametrize(
    ("break_it", "criterion"),
    [
        (lambda rig: rig.adc.write_text("2501\n"), "rail_voltage"),  # past the channel's 2.5 V
        (lambda rig: rig.adc.write_text("garbage\n"), "rail_voltage"),
        (lambda rig: rig.adc.unlink(), "rail_voltage"),
    ],
    ids=["ADC past range", "ADC garbage", "ADC file gone"],
)
def test_an_adc_that_fails_mid_session_blocks_criterion_unavailable(
    agent, rig, break_it, criterion
):
    session = SimSession.load(agent, target="linux")  # preflight read the healthy ADC
    try:
        break_it(rig)
        action = anyio.run(tool, session, "rail_open_gate")
        assert action.blocked and action.gate.reason == "criterion_unavailable"
        assert action.gate.failed_criterion == criterion
        assert "error" in session.events.of_type("analog_in")[-1]
        assert relay(rig) is Value.INACTIVE
    finally:
        session.close()


def test_a_rig_whose_adc_is_missing_at_start_is_refused_before_any_line(agent, rig):
    rig.adc.unlink()
    with pytest.raises(BoardCapabilityError, match="does not exist"):
        SimSession.load(agent, target="linux")
    assert rig.gpio.requests == []


def test_a_session_recorded_on_linux_replays_the_same_on_sim_and_linux(agent, rig, tmp_path):
    session = SimSession.load(agent, target="linux")
    out = tmp_path / "rail.json"
    try:
        anyio.run(tool, session, "rail_report")
        anyio.run(tool, session, "rail_open_gate")
        rig.adc.write_text("999\n")
        anyio.run(tool, session, "rail_open_gate")
        session.write_trace(out)
    finally:
        session.close()
    sim = replay(out, target="sim", agent=agent, board_id="sim-rpi5")
    on_linux = replay(out, target="linux", agent=agent, board_id="linux-rpi5")
    assert on_linux.verdicts == sim.verdicts == sim.recorded_verdicts == ["ALLOW", "ALLOW", "BLOCK"]
    assert sim.warnings == [] and on_linux.warnings == []
    assert_matches_golden(sim, out)
    assert_matches_golden(on_linux, out)
