"""
`analog.in` on `linux` against a real kernel (TSK-I2a-04, RFC-0007 §3c, spike TSK-N3-03).

Run by the `linux-hal` CI job after `scripts/setup_gpio_sim.sh` and `scripts/setup_i2c_stub.sh`
(i2c-stub + the kernel's ads7828 driver → a hwmon device whose `in0_input` is the ADC's
channel 0 in millivolts):

    cd python && python -m pytest -q tests_linux

The ADC code is written into the chip's register with `i2cset`; the HAL reads it back through
the ads7828 driver and hwmon sysfs, converts it to volts and — when an agent binds a numeric
criterion to the channel — decides a gate on it, as it would on a Pi 5 with an ADS7828. A
missing device is a failure, never a skip.

The chip has a 2.5 V internal reference, so `in0_input` is `round(code * 610 / 1000)` mV
(610 = 2_500_000 // 4096, the driver's integer LSB): 0x800 → 1249 mV, the spike's value.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import time
from pathlib import Path

import pytest

from neuroedge.engine.trace_sink import EventLog
from neuroedge.errors import BoardCapabilityError, PerceptionUnavailableError
from neuroedge.hal.linux import ANALOG_ENV, LinuxHAL
from neuroedge.hal.sysfs import SensorSource
from neuroedge.sim import SimSession
from neuroedge.testing import replay

REGISTER, ADDR = "0x8c", "0x4a"  # channel 0, single-ended, internal reference; the chip's address

GATE = """\
schema: neuroedge.gate/v1
name: volt
version: 1.0.0
evaluate:
  line_voltage:
    type: numeric
    unit: V
    range: { min: 0.0, max: 2.5 }
    max_age_ms: 5000
    instructions: Voltage after the divider
allow_when:
  line_voltage: { gte: 1.0, lt: 2.0 }
on_block:
  action: deny
budget:
  p95_latency_ms: 100
  fail: closed
"""


def env(name: str) -> str:
    value = os.environ.get(name)
    assert value, f"{name} is not set; run scripts/setup_i2c_stub.sh first"
    return value


def set_code(code: int) -> None:
    """Write the 12-bit conversion result (an SMBus word is little-endian: bytes swapped)."""
    word = ((code & 0xFF) << 8) | (code >> 8)
    bus = env("NEUROEDGE_I2C_STUB_BUS")
    subprocess.run(["i2cset", "-f", "-y", bus, ADDR, REGISTER, f"0x{word:04x}", "w"], check=True)


def millivolts(code: int) -> int:
    return (code * 610 + 500) // 1000  # DIV_ROUND_CLOSEST(code * lsb, 1000)


@pytest.fixture(scope="module")
def ads7828() -> str:
    """The kernel device the ads7828 driver is bound to, e.g. 3-004a."""
    return env("NEUROEDGE_ADS7828_DEVICE")


@pytest.fixture(autouse=True)
def restore_code():
    yield
    set_code(0x800)


def read_until(hal: LinuxHAL, expected: float, timeout: float = 3.0) -> float:
    deadline = time.monotonic() + timeout
    value = hal.analog_in("adc0", called_from="test")
    while value != expected and time.monotonic() < deadline:
        time.sleep(0.05)
        value = hal.analog_in("adc0", called_from="test")
    return value


@pytest.fixture
def hal(ads7828):
    hal = LinuxHAL(
        events=EventLog(target="linux", board_id="linux-rpi5"),
        authorize=lambda *_: None,
        analog_sources={"adc0": f"hwmon:ads7828@{ads7828}/in0"},
        display="memory",
    )
    yield hal
    hal.close()


@pytest.mark.parametrize("code", [0x000, 0x001, 0x300, 0x800, 0xA00, 0xFFF])
def test_the_hal_reads_the_ads7828_through_hwmon_in_volts(hal, code):
    set_code(code)
    expected = millivolts(code) / 1000
    assert read_until(hal, expected) == expected, "every read reaches the chip; none is cached"
    assert hal.events.of_type("analog_in")[-1] == {
        "channel": "adc0",
        "value": expected,
        "unit": "V",
    }


def test_the_spike_value_reads_as_1_249_volts(hal):
    set_code(0x800)
    assert read_until(hal, 1.249) == 1.249


def test_the_device_is_found_by_name_alone_too(ads7828):
    hal = LinuxHAL(authorize=lambda *_: None, analog_sources={"adc0": "hwmon:ads7828/in0"})
    try:
        set_code(0x800)
        assert read_until(hal, 1.249) == 1.249
    finally:
        hal.close()


def test_a_device_the_kernel_does_not_have_is_unavailable_not_a_default(ads7828):
    missing = LinuxHAL(
        events=EventLog(target="linux", board_id="linux-rpi5"),
        authorize=lambda *_: None,
        analog_sources={"adc0": "hwmon:ads7829/in0"},
    )
    try:
        with pytest.raises(
            PerceptionUnavailableError, match="no hwmon device named 'ads7829'"
        ) as raised:
            missing.analog_in("adc0", use="fact")
        assert "ads7828" in raised.value.why, "it lists what the kernel does have"
        assert missing.events.of_type("analog_in")[-1]["error"]
    finally:
        missing.close()


def test_a_channel_with_no_label_and_no_source_is_unavailable(ads7828):
    unmapped = LinuxHAL(authorize=lambda *_: None)  # the ads7828 driver sets no `inN_label`
    try:
        with pytest.raises(PerceptionUnavailableError, match="labelled 'adc0'"):
            unmapped.analog_in("adc0")
    finally:
        unmapped.close()


def test_a_channel_the_chip_does_not_have_is_unavailable(ads7828):  # it has in0..in7
    other = LinuxHAL(authorize=lambda *_: None, analog_sources={"adc0": "hwmon:ads7828/in8"})
    try:
        with pytest.raises(PerceptionUnavailableError, match="does not exist"):
            other.analog_in("adc0")
    finally:
        other.close()


def test_a_channel_the_board_does_not_declare_never_reaches_the_kernel(hal):
    with pytest.raises(BoardCapabilityError, match="adc9"):
        hal.analog_in("adc9")


# --- end to end: a gate decides on the kernel reading, and the trace replays ---------------


def agent(directory: Path) -> Path:
    (directory / "actions").mkdir()
    (directory / "actions" / "fan.py").write_text(
        "from neuroedge import action\n"
        "from neuroedge.hal import digital\n\n"
        '@action(name="adc_fan_on", requires="digital.out:gate_relay", gate="volt")\n'
        "def fan_on() -> None:\n"
        '    digital.out("gate_relay").on()\n',
        encoding="utf-8",
    )
    (directory / "volt.yaml").write_text(GATE, encoding="utf-8")
    (directory / "commands.toml").write_text(
        '[grammar]\nversion = 1\n\n[[command]]\nintent = "fan_on"\npatterns = ["bật quạt"]\n'
        'tool = "adc_fan_on"\n',
        encoding="utf-8",
    )
    (directory / "agent.toml").write_text(
        '[agent]\nname = "adc-linux"\nversion = "0.1.0"\n\n'
        '[requires]\n"digital.out" = { pins = ["gate_relay"] }\n'
        '"analog.in" = { channels = ["adc0"] }\n\n'
        '[gates]\nvolt = "volt.yaml"\n\n'
        '[sim.analog_facts]\nline_voltage = { channel = "adc0" }\n',
        encoding="utf-8",
    )
    return directory / "agent.toml"


@pytest.mark.usefixtures("fresh_actions")
@pytest.mark.parametrize(
    ("code", "verdict"),
    [
        (0x800, "ALLOW"),  # 1.249 V
        (0x666, "BLOCK"),  # 0.999 V, one millivolt under the closed lower bound
        (0x667, "ALLOW"),  # 1.000 V: the bound belongs to the interval
        (0xCCD, "ALLOW"),  # 1.999 V
        (0xCCE, "BLOCK"),  # 2.000 V: the upper bound is open
        (0x300, "BLOCK"),  # 0.468 V
        (0xFFF, "BLOCK"),  # 2.498 V, the highest the chip can say
    ],
)
def test_the_kernel_voltage_decides_the_gate_and_replays(
    ads7828, monkeypatch, tmp_path: Path, code, verdict
):
    monkeypatch.setenv(ANALOG_ENV, f"adc0=hwmon:ads7828@{ads7828}/in0")
    path = agent(tmp_path)
    set_code(code)
    volts = millivolts(code) / 1000
    session = SimSession.load(path, target="linux")
    try:
        turn = asyncio.run(session.handle("bật quạt"))
        out = tmp_path / "adc.json"
        session.write_trace(out)
    finally:
        session.close()
    assert str(turn.result.verdict) == verdict
    if verdict == "BLOCK":
        assert turn.result.gate.reason == "condition_not_met"
    else:
        assert turn.allowed and session.hal.pin("gate_relay").commands == [("on", 0)]

    trace = json.loads(out.read_text(encoding="utf-8"))
    reads = [e["data"] for e in trace["events"] if e["type"] == "analog_in"]
    assert reads == [{"channel": "adc0", "value": volts, "unit": "V", "use": "fact"}]
    (facts,) = [e["data"] for e in trace["events"] if e["type"] == "gate_facts"]
    assert facts["line_voltage"]["value"] == volts
    assert facts["line_voltage"]["age_ms"] == (
        facts["line_voltage"]["eval_offset_ms"] - facts["line_voltage"]["read_offset_ms"]
    )

    replayed = replay(out, target="sim", agent=path)
    assert replayed.verdicts == replayed.recorded_verdicts == [verdict]
    assert replayed.warnings == []


@pytest.mark.usefixtures("fresh_actions")
def test_an_adc_that_is_not_there_blocks_criterion_unavailable(ads7828, monkeypatch, tmp_path):
    monkeypatch.setenv(ANALOG_ENV, f"adc0=hwmon:ads7828@{ads7828}/in0")
    session = SimSession.load(agent(tmp_path), target="linux")  # preflight reads the chip
    try:
        # Re-map the channel to a device the kernel does not have: what a pulled ADC looks like.
        session.hal.analog.sources["adc0"] = SensorSource.parse("adc0", "hwmon:ads7829/in0", "test")
        turn = asyncio.run(session.handle("bật quạt"))
        assert turn.result.blocked and turn.result.gate.reason == "criterion_unavailable"
        assert session.hal.pin("gate_relay").never_pulsed()
        assert session.events.of_type("analog_in")[-1]["error"]
    finally:
        session.close()
