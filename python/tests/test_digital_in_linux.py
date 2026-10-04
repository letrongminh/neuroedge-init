"""
TSK-I2a-02 — `digital.in` on `linux` (RFC-0007 §3a): `LinuxHAL` reads input lines through gpiod.

Against the in-memory gpiod stand-in of `test_hal_linux.py`, so these run everywhere. The same
lines on real kernel lines — the level set through gpio-sim's own sysfs — are in
`tests_linux/test_gpio_sim.py`. An input line is requested as an input, by name, never driven,
held until `close()`; a line that cannot be found, requested or read is a failed read
(`PerceptionUnavailableError`), which the gate turns into BLOCK `criterion_unavailable`.
"""

from __future__ import annotations

import pytest

import neuroedge.hal.linux as linux
from neuroedge.engine import EventLog
from neuroedge.errors import BoardCapabilityError, PerceptionUnavailableError
from neuroedge.hal.linux import LinuxHAL, TypedLinuxHAL
from neuroedge.sim import SimSession
from neuroedge.testing import TracePlayer
from neuroedge.testing.recorder import TraceRecorder

from .hand_clock import HandClock
from .test_digital_in import agent
from .test_hal_linux import LINES, Direction, FakeGpiod, Value

INPUTS = ["door_contact_raw", "limit_switch"]
WITH_INPUTS = [*LINES, *INPUTS]


@pytest.fixture
def chip(tmp_path):
    path = tmp_path / "gpiochip0"
    path.write_text("")
    return str(tmp_path / "gpiochip*"), str(path)


def make(chip, *, lines=WITH_INPUTS, events=None, **kwargs):
    pattern, path = chip
    fake = FakeGpiod({path: lines})
    hal = LinuxHAL(chip_glob=pattern, gpiod=fake, events=events, **kwargs)
    return hal, fake


def drive(fake, chip, pin, value):
    """What a switch wired to the line does: the kernel then reads it back as `value`."""
    fake.values[(chip[1], WITH_INPUTS.index(pin))] = Value.ACTIVE if value else Value.INACTIVE


def inputs_of(fake):
    return [r for r in fake.requests if r.direction is Direction.INPUT]


# --- a level, read from a line requested as an input ---------------------------------------


def test_a_line_is_read_as_a_level_and_the_read_is_recorded(chip):
    events = EventLog()
    hal, fake = make(chip, events=events)
    drive(fake, chip, "limit_switch", True)
    assert hal.digital_in("limit_switch", called_from="test") is True
    drive(fake, chip, "limit_switch", False)
    assert hal.digital_in("limit_switch", called_from="test") is False
    assert [e["data"] for e in events.events if e["type"] == "digital_in"] == [
        {"pin": "limit_switch", "value": True},
        {"pin": "limit_switch", "value": False},
    ]
    hal.close()


def test_an_input_is_requested_as_an_input_and_never_driven(chip):
    hal, fake = make(chip)
    drive(fake, chip, "door_contact_raw", True)
    hal.digital_in("door_contact_raw", called_from="test")
    (request,) = inputs_of(fake)
    assert request.direction is Direction.INPUT and request.offsets == (
        WITH_INPUTS.index("door_contact_raw"),
    )
    assert fake.history == [], (
        "no value was ever written to any line"
    )  # the fake refuses set_value on an input
    hal.close()


def test_the_first_read_requests_the_line_and_later_reads_reuse_it(chip):
    hal, fake = make(chip)
    assert inputs_of(fake) == []
    hal.digital_in("limit_switch", called_from="test")
    hal.digital_in("limit_switch", called_from="test")
    assert len(inputs_of(fake)) == 1
    hal.close()


def test_an_input_line_is_found_by_the_name_line_names_gives_it(chip):
    pattern, path = chip
    fake = FakeGpiod({path: [*LINES, "GPIO23", "GPIO24"]})
    hal = LinuxHAL(chip_glob=pattern, gpiod=fake, line_names={"limit_switch": "GPIO24"})
    fake.values[(path, 5)] = Value.ACTIVE
    assert hal.digital_in("limit_switch", called_from="test") is True
    hal.close()


def test_close_releases_the_inputs_with_the_outputs_and_a_read_after_it_is_refused(chip):
    hal, fake = make(chip)
    hal.digital_in("limit_switch", called_from="test")
    hal.close()
    assert all(request.released for request in fake.requests)
    requests = len(fake.requests)
    with pytest.raises(PerceptionUnavailableError, match="closed"):
        hal.digital_in("door_contact_raw", called_from="test")
    assert len(fake.requests) == requests, "a closed HAL requests nothing new"
    hal.close()  # idempotent


def test_a_pin_the_board_does_not_declare_as_an_input_is_refused_before_any_line_is_touched(chip):
    events = EventLog()
    hal, fake = make(chip, events=events)
    with pytest.raises(BoardCapabilityError, match="declares no input pin named 'door_lock'"):
        hal.digital_in("door_lock", called_from="actions/a.py:9")  # an output
    with pytest.raises(BoardCapabilityError):
        hal.digital_in("spare", called_from="test")  # a line the chip has, the board does not name
    assert inputs_of(fake) == [] and not [e for e in events.events if e["type"] == "digital_in"]
    hal.close()


# --- a read that fails is a failed read ------------------------------------------------------


def test_a_line_the_chip_does_not_have_is_a_failed_read(chip):
    events = EventLog()
    hal, _fake = make(chip, lines=LINES, events=events)  # no input lines on this chip
    with pytest.raises(PerceptionUnavailableError, match="no line named 'limit_switch'") as raised:
        hal.digital_in("limit_switch", called_from="test")
    assert raised.value.code == "NE5001"
    (event,) = [e["data"] for e in events.events if e["type"] == "digital_in"]
    assert "value" not in event and "limit_switch" in event["reason"]
    hal.close()


def test_a_refused_line_request_is_a_failed_read(chip):
    events = EventLog()
    hal, fake = make(chip, events=events)
    fake.input_request_error = OSError(16, "Device or resource busy")
    with pytest.raises(PerceptionUnavailableError, match="cannot be read"):
        hal.digital_in("limit_switch", called_from="test")
    fake.input_request_error = None  # a line that frees up is read again, not remembered as failed
    drive(fake, chip, "limit_switch", True)
    assert hal.digital_in("limit_switch", called_from="test") is True
    hal.close()


@pytest.mark.parametrize("error", [OSError(5, "I/O error"), OSError(19, "No such device")])
def test_a_read_that_fails_in_the_kernel_is_a_failed_read(chip, error):
    hal, fake = make(chip)
    hal.digital_in("limit_switch", called_from="test")
    fake.read_error = error
    with pytest.raises(PerceptionUnavailableError, match="cannot be read"):
        hal.digital_in("limit_switch", called_from="test")
    hal.close()


def test_a_chip_that_went_away_is_a_failed_read(chip):
    hal, fake = make(chip)

    def gone(path):
        raise OSError(19, "No such device")

    fake.Chip = gone
    with pytest.raises(PerceptionUnavailableError, match="cannot be read"):
        hal.digital_in("limit_switch", called_from="test")
    hal.close()


# --- a session asks for its lines when it starts -------------------------------------------------


def test_needs_request_the_input_lines_with_the_outputs(chip):
    hal, fake = make(chip, needs={"digital_in": INPUTS, "where": "agent.toml on target 'linux'"})
    assert len(inputs_of(fake)) == 2
    hal.close()
    assert all(request.released for request in fake.requests)


def test_a_missing_input_line_is_refused_before_any_output_is_held(chip):
    pattern, path = chip
    fake = FakeGpiod({path: [*LINES, "door_contact_raw"]})
    with pytest.raises(BoardCapabilityError, match="no line named 'limit_switch'"):
        LinuxHAL(chip_glob=pattern, gpiod=fake, needs={"digital_in": INPUTS, "where": "w"})
    assert fake.requests == []


def test_a_pin_needs_names_that_the_board_does_not_declare_is_refused(chip):
    with pytest.raises(BoardCapabilityError, match="declares no input pin named 'door_lock'"):
        make(chip, needs={"digital_in": ["door_lock"], "where": "w"})


def test_an_input_request_the_kernel_refuses_releases_the_outputs_and_the_session_does_not_start(
    chip,
):
    pattern, path = chip
    fake = FakeGpiod({path: WITH_INPUTS})
    fake.input_request_error = OSError(16, "Device or resource busy")
    with pytest.raises(BoardCapabilityError, match="cannot open the GPIO chip or its lines"):
        LinuxHAL(chip_glob=pattern, gpiod=fake, needs={"digital_in": INPUTS, "where": "w"})
    assert fake.requests and all(request.released for request in fake.requests)


def test_a_replay_never_touches_the_machines_lines(chip):
    pattern, path = chip
    fake = FakeGpiod({path: WITH_INPUTS})
    fake.values[(path, WITH_INPUTS.index("limit_switch"))] = (
        Value.ACTIVE
    )  # today's level: not the trace's
    hal = LinuxHAL(
        chip_glob=pattern, gpiod=fake, replay=True, needs={"digital_in": INPUTS, "where": "w"}
    )
    assert inputs_of(fake) == []
    with pytest.raises(PerceptionUnavailableError, match="holds no reading"):
        hal.digital_in("limit_switch", called_from="test")
    hal.script_digital_in("limit_switch", [False])
    assert hal.digital_in("limit_switch", called_from="test") is False
    assert inputs_of(fake) == []
    hal.close()


def test_a_typed_hal_reads_the_kernel_and_cannot_set_a_level(chip):
    pattern, path = chip
    hal = TypedLinuxHAL(chip_glob=pattern, gpiod=FakeGpiod({path: WITH_INPUTS}))
    assert hal.digital_in_values() == {}
    with pytest.raises(BoardCapabilityError, match="read from the kernel"):
        hal.set_digital_in("limit_switch", True)
    hal.close()


# --- an interactive session on linux ------------------------------------------------------------


@pytest.fixture
def gpio(monkeypatch, chip):
    fake = FakeGpiod({chip[1]: WITH_INPUTS})
    monkeypatch.setattr(linux, "CHIP_GLOB", chip[0])
    monkeypatch.setattr(linux, "_import_gpiod", lambda: fake)
    return fake


def load(tmp_path, clock=None, **kwargs):
    options = {} if clock is None else {"clock": clock}
    return SimSession.load(agent(tmp_path, **kwargs), target="linux", **options)


async def test_the_kernel_level_is_the_fact_and_decides_both_ways(tmp_path, gpio, chip):
    # A hand clock: the verdict token's 300 ms TTL and the gate budget are measured on the
    # session clock, and a loaded CI runner outran them on the wall clock (rightly refused,
    # NE1002 — PR #96). This test is about the kernel level deciding the gate.
    session = load(tmp_path, clock=HandClock())
    try:
        assert [r.direction for r in gpio.requests].count(
            Direction.INPUT
        ) == 2  # at load, not the first turn
        drive(gpio, chip, "door_contact_raw", False)
        blocked = await session.handle("đóng cổng")
        assert not blocked.allowed and blocked.result.gate.reason == "condition_not_met"
        drive(gpio, chip, "door_contact_raw", True)
        allowed = await session.handle("đóng cổng")
        assert allowed.allowed
        facts = session.events.of_type("gate_facts")[-1]["door_closed"]
        assert facts["value"] is True and facts["source"] == "digital.in" and facts["age_ms"] >= 0
        assert not any(  # the HAL never wrote to an input line
            name in ("door_contact_raw", "limit_switch") for name, _ in gpio.history
        )
    finally:
        session.close()
    assert all(request.released for request in gpio.requests)


async def test_a_line_that_fails_to_read_blocks_criterion_unavailable_on_linux(tmp_path, gpio):
    session = load(tmp_path)
    try:
        gpio.read_error = OSError(5, "I/O error")
        turn = await session.handle("đóng cổng")
        assert not turn.allowed and turn.result.gate.reason == "criterion_unavailable"
        assert ("gate_relay", 1) not in gpio.history
        assert "cannot be read" in session.events.of_type("digital_in")[-1]["reason"]
    finally:
        session.close()


async def test_a_session_on_linux_replays_the_same_verdicts_on_sim(tmp_path, gpio, chip):
    path = agent(tmp_path)
    recorder = TraceRecorder()
    session = SimSession.load(path, target="linux", events=recorder)
    try:
        drive(gpio, chip, "door_contact_raw", False)
        await session.handle("đóng cổng")
        drive(gpio, chip, "door_contact_raw", True)
        await session.handle("đóng cổng")
        out = tmp_path / "trace.json"
        session.write_trace(out)
    finally:
        session.close()
    result = await TracePlayer(out, agent=path, board_id="sim-rpi5").replay()
    assert result.recorded_verdicts == ["BLOCK", "ALLOW"] and result.verdicts == ["BLOCK", "ALLOW"]
    on_linux = await TracePlayer(out, agent=path, target="linux", board_id="linux-rpi5").replay()
    assert on_linux.verdicts == ["BLOCK", "ALLOW"]


def test_a_session_whose_input_line_is_missing_does_not_start(tmp_path, monkeypatch, chip):
    fake = FakeGpiod({chip[1]: LINES})  # the chip has no input lines
    monkeypatch.setattr(linux, "CHIP_GLOB", chip[0])
    monkeypatch.setattr(linux, "_import_gpiod", lambda: fake)
    with pytest.raises(BoardCapabilityError, match="no line named"):
        load(tmp_path)
    assert fake.requests == []
