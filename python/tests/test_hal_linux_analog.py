"""
TSK-I2a-04 — `analog.in` on `linux`, against a fake /sys tree, so these run everywhere.

An ADC with a hwmon driver (`ads7828`: ``in0_input`` in millivolts) is found by source
(``adc0=hwmon:ads7828/in0``, `NEUROEDGE_LINUX_ANALOG`) or by label, converted to the
channel's unit and refused as a read failure (NE5001) when it is missing, garbage, in another
unit or outside the channel's `[min, max]`. The same HAL against the kernel (`i2c-stub` +
`ads7828`) is `tests_linux/test_analog_in.py`, run by the `linux-hal` CI job.
"""

from __future__ import annotations

import anyio
import pytest

import neuroedge.hal.linux as linux
import neuroedge.hal.sysfs as sysfs
from neuroedge.engine.trace_sink import EventLog
from neuroedge.errors import BoardCapabilityError, PerceptionUnavailableError
from neuroedge.hal.board import load_board_by_id
from neuroedge.hal.sim import SimHAL
from neuroedge.sim import SimSession

from .hand_clock import HandClock
from .test_analog_in import agent
from .test_hal_linux import LINES, FakeGpiod
from .test_hal_linux_io import hwmon, make

SOURCE = {"adc0": "hwmon:ads7828/in0"}


@pytest.fixture(autouse=True)
def no_machine_wiring(monkeypatch):
    for name in (linux.SENSORS_ENV, linux.ANALOG_ENV, linux.DISPLAY_ENV):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def sys_root(tmp_path):
    root = tmp_path / "sys"
    (root / "class" / "hwmon").mkdir(parents=True)
    (root / "bus" / "iio" / "devices").mkdir(parents=True)
    return root


def adc(root, millivolts=1249, index=2):
    """An ads7828 as the kernel shows it: hwmon `in0_input` in millivolts."""
    return hwmon(root, index, "ads7828", {"in0_input": millivolts})


# --- reading --------------------------------------------------------------------------------


def test_a_mapped_hwmon_channel_reads_in_volts_and_records_what_sim_records(tmp_path, sys_root):
    adc(sys_root, 1249)
    hal, _ = make(tmp_path, sysfs_root=sys_root, analog_sources=SOURCE)
    assert hal.analog_in("adc0", called_from="test") == 1.249
    (event,) = hal.events.of_type("analog_in")

    sim = SimHAL(load_board_by_id("sim-rpi5"), events=EventLog())
    sim.set_analog("adc0", 1.249)
    sim.analog_in("adc0")
    (on_sim,) = sim.events.of_type("analog_in")
    assert event == on_sim == {"channel": "adc0", "value": 1.249, "unit": "V"}


def test_a_labelled_channel_is_found_with_no_mapping(tmp_path, sys_root):
    device = adc(sys_root, 800)
    (device / "in0_label").write_text("adc0\n")
    hal, _ = make(tmp_path, sysfs_root=sys_root)
    assert hal.analog_in("adc0") == 0.8


def test_the_machine_environment_maps_the_channel(tmp_path, sys_root, monkeypatch):
    adc(sys_root, 2000)
    monkeypatch.setenv(linux.ANALOG_ENV, "adc0=hwmon:ads7828/in0")
    hal, _ = make(tmp_path, sysfs_root=sys_root)
    assert hal.analog_in("adc0", use="fact") == 2.0
    assert hal.events.of_type("analog_in")[-1]["use"] == "fact"


def test_a_channel_edge_reads_and_every_read_goes_to_the_kernel(tmp_path, sys_root):
    device = adc(sys_root, 0)
    hal, _ = make(tmp_path, sysfs_root=sys_root, analog_sources=SOURCE)
    assert hal.analog_in("adc0") == 0.0
    (device / "in0_input").write_text("2500\n")
    assert hal.analog_in("adc0") == 2.5


def test_a_mapping_for_a_channel_the_board_lacks_is_refused(tmp_path, sys_root):
    adc(sys_root)
    with pytest.raises(BoardCapabilityError, match="adc9"):
        make(tmp_path, sysfs_root=sys_root, analog_sources={"adc9": "hwmon:ads7828/in0"})


def test_an_undeclared_channel_never_touches_the_kernel(tmp_path, sys_root):
    hal, _ = make(tmp_path, sysfs_root=sys_root, analog_sources=SOURCE)
    with pytest.raises(BoardCapabilityError, match="adc9"):
        hal.analog_in("adc9")
    assert hal.events.of_type("analog_in") == []


# --- every way a read fails is NE5001, recorded, never a value ------------------------------

FAULTS = {  # what breaks -> a word of the reason
    "a negative voltage": (lambda d: (d / "in0_input").write_text("-1\n"), "outside the range"),
    "past the top": (lambda d: (d / "in0_input").write_text("2501\n"), "outside the range"),
    "far past the top": (lambda d: (d / "in0_input").write_text("99999\n"), "outside the range"),
    "garbage": (lambda d: (d / "in0_input").write_text("x\n"), "not a number"),
    "NaN": (lambda d: (d / "in0_input").write_text("nan\n"), "not a number"),
    "an empty file": (lambda d: (d / "in0_input").write_text(""), "not a number"),
    "a fractional integer file": (lambda d: (d / "in0_input").write_text("1.5\n"), "not a number"),
    "the file gone": (lambda d: (d / "in0_input").unlink(), "does not exist"),
    "the driver's fault flag": (lambda d: (d / "in0_fault").write_text("1\n"), "in0_fault"),
    "the device gone": (lambda d: (d / "name").write_text("other\n"), "no hwmon device"),
}


@pytest.mark.parametrize("fault", FAULTS, ids=list(FAULTS))
def test_a_read_that_fails_is_unavailable_and_recorded(tmp_path, sys_root, fault):
    device = adc(sys_root)
    hal, _ = make(tmp_path, sysfs_root=sys_root, analog_sources=SOURCE)
    assert hal.analog_in("adc0") == 1.249
    breaks, why = FAULTS[fault]
    breaks(device)
    with pytest.raises(PerceptionUnavailableError) as raised:
        hal.analog_in("adc0", called_from="test", use="fact")
    assert raised.value.code == "NE5001" and why in raised.value.why
    assert "test -> analog.in 'adc0'" in raised.value.where or "adc0" in raised.value.where
    first, failed = hal.events.of_type("analog_in")
    assert first["value"] == 1.249
    assert failed["channel"] == "adc0" and failed["use"] == "fact" and why in failed["error"]
    assert "value" not in failed


def test_another_unit_than_the_channels_is_unavailable(tmp_path, sys_root):
    hwmon(sys_root, 4, "ina219", {"curr1_input": 500})  # 0.5 A, on a channel declared in V
    hal, _ = make(tmp_path, sysfs_root=sys_root, analog_sources={"adc0": "hwmon:ina219/curr1"})
    with pytest.raises(PerceptionUnavailableError, match="in 'A', and the board declares 'V'"):
        hal.analog_in("adc0")


def test_no_source_and_no_label_never_reads_as_a_default(tmp_path, sys_root):
    hal, _ = make(tmp_path, sysfs_root=sys_root)
    with pytest.raises(PerceptionUnavailableError, match="labelled 'adc0'"):
        hal.analog_in("adc0")


def test_a_replay_never_reads_the_machine(tmp_path, sys_root):
    adc(sys_root)
    hal, _ = make(tmp_path, sysfs_root=sys_root, analog_sources=SOURCE, replay=True)
    with pytest.raises(PerceptionUnavailableError, match="does not read the machine"):
        hal.analog_in("adc0")


def test_a_linux_channel_cannot_be_set(tmp_path, sys_root):
    from neuroedge.hal.linux import TypedLinuxHAL

    with pytest.raises(BoardCapabilityError, match="cannot be set"):
        TypedLinuxHAL.set_analog(object(), "adc0", 1.0)
    assert TypedLinuxHAL.analog_values(object()) == {}


# --- preflight: refused at load, as a board problem, before any line ------------------------


def test_preflight_reads_each_channel_once_unrecorded(tmp_path, sys_root):
    adc(sys_root)
    hal, _ = make(
        tmp_path, sysfs_root=sys_root, analog_sources=SOURCE, needs={"analog": ["adc0", "adc0"]}
    )
    assert hal.events.of_type("analog_in") == []


@pytest.mark.parametrize("fault", ["past the top", "garbage", "the file gone"])
def test_an_adc_that_cannot_be_read_at_start_is_a_board_problem_before_any_line(
    tmp_path, sys_root, fault
):
    device = adc(sys_root)
    FAULTS[fault][0](device)
    fake = FakeGpiod({str(tmp_path / "gpiochip0"): LINES})
    with pytest.raises(BoardCapabilityError) as raised:
        make(tmp_path, fake, sysfs_root=sys_root, analog_sources=SOURCE, needs={"analog": ["adc0"]})
    assert not isinstance(raised.value, PerceptionUnavailableError)
    assert fake.requests == []


# --- a gate verdict from the kernel reading -------------------------------------------------


@pytest.fixture
def gpio(monkeypatch, tmp_path):
    chip = tmp_path / "gpiochip0"
    chip.write_text("")
    fake = FakeGpiod({str(chip): LINES})
    monkeypatch.setattr(linux, "CHIP_GLOB", str(tmp_path / "gpiochip*"))
    monkeypatch.setattr(linux, "_import_gpiod", lambda: fake)
    return fake


@pytest.fixture
def ads(monkeypatch, tmp_path):
    """A fake /sys with an ads7828 at 1.5 V, mapped to the board's `adc0` by name."""
    device = tmp_path / "sys" / "class" / "hwmon" / "hwmon2"
    device.mkdir(parents=True)
    (device / "name").write_text("ads7828\n")
    (device / "in0_input").write_text("1500\n")
    monkeypatch.setattr(sysfs, "SYSFS_ROOT", str(tmp_path / "sys"))
    monkeypatch.setenv(linux.ANALOG_ENV, "adc0=hwmon:ads7828/in0")
    return device


def test_the_gate_reads_the_kernel_voltage_into_a_numeric_fact(tmp_path, gpio, ads):
    clock = HandClock()
    session = SimSession.load(agent(tmp_path), target="linux", clock=clock)
    try:
        for millivolts, allowed in (
            (1500, True),
            (999, False),
            (1000, True),
            (1999, True),
            (2000, False),
        ):
            (ads / "in0_input").write_text(f"{millivolts}\n")
            turn = anyio.run(session.handle, "bật quạt")
            assert turn.allowed is allowed, millivolts
            fact = session.events.of_type("gate_facts")[-1]["line_voltage"]
            assert fact["value"] == millivolts / 1000 and fact["age_ms"] >= 0
            assert session.events.of_type("analog_in")[-1] == {
                "channel": "adc0",
                "value": millivolts / 1000,
                "unit": "V",
                "use": "fact",
            }
            # The fan relay stays on for its whole `max_continuous_ms` on a real line: turn it off
            # (never refused) and let `min_interval_ms` pass, so the envelope admits the next `on`.
            session.hal.digital_out("gate_relay", "off")
            clock.advance(2_000)
    finally:
        session.close()
    assert all(request.released for request in gpio.requests)


FAILS = {
    "past the top": lambda d: (d / "in0_input").write_text("2501\n"),
    "garbage": lambda d: (d / "in0_input").write_text("x\n"),
    "the file gone": lambda d: (d / "in0_input").unlink(),
    "the device gone": lambda d: (d / "name").write_text("other\n"),
}


@pytest.mark.parametrize("fault", FAILS, ids=list(FAILS))
def test_an_adc_that_fails_mid_session_blocks_criterion_unavailable(tmp_path, gpio, ads, fault):
    session = SimSession.load(agent(tmp_path), target="linux")  # preflight read it healthy
    try:
        assert anyio.run(session.handle, "bật quạt").allowed
        FAILS[fault](ads)
        turn = anyio.run(session.handle, "bật quạt")
    finally:
        session.close()
    assert turn.result.blocked and turn.result.gate.reason == "criterion_unavailable"
    assert session.hal.pin("gate_relay").commands == [("on", 0)], "only the healthy read ran"
    assert "error" in session.events.of_type("analog_in")[-1]
    assert session.events.of_type("gate_facts")[-1]["line_voltage"]["value"] is None


def test_an_adc_that_is_missing_at_start_is_refused_before_any_line(tmp_path, gpio, ads):
    (ads / "in0_input").unlink()
    with pytest.raises(BoardCapabilityError, match="does not exist"):
        SimSession.load(agent(tmp_path), target="linux")
    assert gpio.requests == []


def test_no_adc_mapping_is_refused_before_any_line(tmp_path, gpio, ads, monkeypatch):
    monkeypatch.delenv(linux.ANALOG_ENV)
    with pytest.raises(BoardCapabilityError, match="labelled 'adc0'"):
        SimSession.load(agent(tmp_path), target="linux")
    assert gpio.requests == []


def test_a_trace_recorded_on_linux_replays_the_same_on_sim(tmp_path, gpio, ads):
    from neuroedge.testing import TracePlayer
    from neuroedge.testing.recorder import TraceRecorder

    path = agent(tmp_path)
    clock = HandClock()
    session = SimSession.load(path, target="linux", events=TraceRecorder(clock=clock), clock=clock)
    try:
        for millivolts in (1500, 500, 1999):
            (ads / "in0_input").write_text(f"{millivolts}\n")
            anyio.run(session.handle, "bật quạt")
            session.hal.digital_out("gate_relay", "off")  # see above: the envelope's interval
            clock.advance(2_000)
        trace = session.events.to_trace()
    finally:
        session.close()
    assert [
        e["data"]["verdict"] for e in trace["events"] if e["type"] == "gate_evaluation_result"
    ] == ["ALLOW", "BLOCK", "ALLOW"]
    result = anyio.run(TracePlayer(trace, agent=path, board_id="sim-rpi5").replay)
    assert result.verdicts == result.recorded_verdicts and result.warnings == []
