"""
TSK-N2-01, TSK-N2-02 — the safety envelope on `LinuxHAL`, against the in-memory gpiod
(RFC-0007 §3d). The envelope's own rules are `test_envelope.py`; here is what only `linux` has:
the timer that ends an on, the line that must be down before the on-time is given back, and the
record that is written before a line goes up. Real kernel lines: `tests_linux/test_gpio_envelope.py`.
"""

from __future__ import annotations

import time

import pytest

from neuroedge.engine.trace_sink import EventLog
from neuroedge.errors import ActionContractViolation, EnvelopeRefusedError
from neuroedge.hal.envelope import EnvelopeLimits, FileEnvelopeStore, SafetyEnvelope
from neuroedge.hal.linux import LinuxHAL

from .test_hal_linux import LINES, FakeGpiod


@pytest.fixture
def chips(tmp_path):
    path = tmp_path / "gpiochip0"
    path.write_text("")
    return str(tmp_path / "gpiochip*"), {str(path): LINES}


def limits(**changes) -> EnvelopeLimits:
    base = {
        "window_s": 100,
        "max_on_ms_per_window": 10_000,
        "min_interval_ms": 0,
        "max_continuous_ms": 80,
    }
    return EnvelopeLimits(**{**base, **changes})


def open_hal(chips, *, store=None, envelope_limits=None, init_store=False, **kwargs):
    pattern, table = chips
    fake = FakeGpiod(table)
    events = EventLog(target="linux", board_id="linux-rpi5")
    envelope = SafetyEnvelope(
        {"door_lock": envelope_limits or limits(), "porch_light": envelope_limits or limits()},
        virtual=False,
        store=store,
        init_store=init_store,
    )
    hal = LinuxHAL(
        chip_glob=pattern,
        gpiod=fake,
        events=events,
        envelope=envelope,
        authorize=kwargs.pop("authorize", lambda *_: None),
        **kwargs,
    )
    return hal, fake, events, envelope


def _last(fake, pin) -> bool:
    values = [value for name, value in fake.history if name == pin]
    return bool(values and values[-1])


def wait_until(condition, timeout_s: float = 3.0) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if condition():
            return
        time.sleep(0.005)
    pytest.fail("the condition never held")


def test_an_on_with_no_duration_is_turned_off_by_the_hal_at_max_continuous_ms(chips):
    hal, fake, events, envelope = open_hal(chips)
    hal.digital_out("porch_light", "on")
    assert hal.line_value("porch_light")
    wait_until(lambda: not hal.line_value("porch_light"))
    wait_until(lambda: envelope.live("porch_light") is None)
    assert events.of_type("actuator_command") == [
        {"pin": "porch_light", "operation": "on", "duration_ms": 0},
        {"pin": "porch_light", "operation": "off", "duration_ms": 0, "cause": "max_continuous_ms"},
    ]
    hal.close()


def test_a_pulse_longer_than_the_cap_is_cut_and_one_inside_it_is_not_reported(chips):
    hal, _, events, envelope = open_hal(chips)
    hal.digital_out("door_lock", "pulse", 30_000)  # cut at 80 ms
    wait_until(lambda: not hal.line_value("door_lock"))
    wait_until(lambda: envelope.live("door_lock") is None)
    assert events.of_type("actuator_command")[-1]["cause"] == "max_continuous_ms"
    hal.digital_out("porch_light", "pulse", 30)  # ends by its own duration
    wait_until(lambda: not hal.line_value("porch_light"))
    wait_until(lambda: envelope.live("porch_light") is None)
    assert [c.get("cause") for c in events.of_type("actuator_command")] == [
        None,
        "max_continuous_ms",
        None,
    ]
    hal.close()


def test_the_on_time_goes_back_only_when_the_line_is_down(chips):
    hal, fake, _, envelope = open_hal(chips)
    hal.digital_out("porch_light", "on")
    assert envelope.live("porch_light") is not None
    hal.digital_out("porch_light", "off")
    assert not hal.line_value("porch_light") and envelope.live("porch_light") is None
    hal.close()


def test_a_refused_command_does_not_touch_the_line_or_the_timers(chips):
    hal, fake, events, _ = open_hal(
        chips, envelope_limits=limits(max_continuous_ms=60_000, max_on_ms_per_window=1_000_000)
    )
    hal.digital_out("door_lock", "on")
    before = list(fake.history)
    with pytest.raises(EnvelopeRefusedError) as raised:
        hal.digital_out("door_lock", "pulse", 10)
    assert raised.value.reason == "already_on"
    assert fake.history == before, "the refused command never reached the line"
    assert hal.line_value("door_lock"), "and the on that holds the pin is undisturbed"
    assert events.of_type("envelope_refused") == [
        {
            "pin": "door_lock",
            "operation": "pulse",
            "reason": "already_on",
            "remaining_ms": raised.value.event["remaining_ms"],
        }
    ]
    hal.close()


def test_authorize_failing_after_the_reservation_returns_it_and_leaves_the_line_down(chips):
    def refuse(signature, pin, called_from):
        raise ActionContractViolation("w", "no proof", "h")

    hal, fake, _, envelope = open_hal(chips, authorize=refuse)
    with pytest.raises(ActionContractViolation):
        hal.digital_out("porch_light", "on")
    assert envelope.live("porch_light") is None and fake.history == []
    hal.close()


def test_a_line_that_will_not_move_gives_the_reservation_back_once_it_is_known_to_be_down(chips):
    hal, fake, _, envelope = open_hal(chips)
    real = hal._set

    def broken(pin, active, limit_ms=None):
        if active:
            raise OSError(5, "I/O error")
        real(pin, active, limit_ms)

    hal._set = broken
    with pytest.raises(OSError):
        hal.digital_out("porch_light", "on")
    assert envelope.live("porch_light") is None
    hal._set = real
    hal.close()


def test_a_line_that_will_not_drop_keeps_its_reservation(chips):
    hal, _, _, envelope = open_hal(chips)
    hal.digital_out("porch_light", "on")
    real = hal._set
    hal._set = lambda pin, active, limit_ms=None: (_ for _ in ()).throw(OSError(5, "stuck"))
    with pytest.raises(OSError):
        hal.digital_out("porch_light", "off")
    assert envelope.live("porch_light") is not None, "the line may still be on: still reserved"
    hal._set = real
    hal.close()
    assert envelope.live("porch_light") is None


def test_the_record_is_written_before_the_line_goes_up(chips, tmp_path):
    store = FileEnvelopeStore(tmp_path / "state")
    hal, fake, _, _ = open_hal(chips, store=store, init_store=True)
    seen: list[list[float]] = []
    real = hal._set

    def watch(pin, active, limit_ms=None):
        if active:
            seen.append(store.load(pin))  # the line has not moved yet
        real(pin, active, limit_ms)

    hal._set = watch
    hal.digital_out("porch_light", "on")
    assert seen == [[80.0]]
    hal._set = real
    hal.close()
    assert store.load("porch_light")[0] < 80, "close() lowered the record to what was used"


def test_close_ends_every_reservation_and_drops_every_line(chips):
    hal, fake, _, envelope = open_hal(
        chips, envelope_limits=limits(max_continuous_ms=60_000, max_on_ms_per_window=1_000_000)
    )
    hal.digital_out("door_lock", "on")
    hal.digital_out("porch_light", "pulse", 30_000)
    hal.close()
    assert envelope.live("door_lock") is None and envelope.live("porch_light") is None
    assert not _last(fake, "door_lock") and not _last(fake, "porch_light")


def test_run_c_does_not_wait_for_the_cap_of_an_on_but_does_for_a_pulse(chips):
    """`settle()` waits for pulses the agent asked for, not for the envelope's cap on an on."""
    from neuroedge.hal.linux import TypedLinuxHAL

    pattern, table = chips
    envelope = SafetyEnvelope(
        {"door_lock": limits(max_continuous_ms=600_000, max_on_ms_per_window=1_000_000)},
        virtual=False,
    )
    hal = TypedLinuxHAL(
        chip_glob=pattern, gpiod=FakeGpiod(table), envelope=envelope, authorize=lambda *_: None
    )
    hal.digital_out("door_lock", "on")  # capped at 600 s by the envelope
    assert hal.pulsing() == []
    started = time.monotonic()
    hal.settle()
    assert time.monotonic() - started < 1, "settle() must not wait out a 600 s cap"
    hal.digital_out("porch_light", "pulse", 50)  # no envelope here: a pulse as it always was
    assert hal.pulsing() == ["porch_light"]
    hal.settle()
    assert hal.pulsing() == [] and not hal.line_value("porch_light")
    hal.close()


# --- supervision is ON by default, and fail-closed (RFC-0007 §3d, §9 item 9) -----------------------


class FakeSupervisor:
    """What `LinuxHAL` needs of a `SupervisorClient`, with no process."""

    started: list[FakeSupervisor] = []
    fail_with: Exception | None = None

    def __init__(self, lines, **options):
        if FakeSupervisor.fail_with is not None:
            raise FakeSupervisor.fail_with
        self.lines, self.options, self.running = dict(lines), options, True
        self.on: dict[str, bool] = {}
        FakeSupervisor.started.append(self)

    def alive(self):
        return self.running

    def set(self, pin, active, limit_ms=None):
        self.on[pin] = active

    def get(self, pin):
        return self.on.get(pin, False)

    def close(self):
        self.running = False


@pytest.fixture
def fake_supervisor(monkeypatch):
    from neuroedge.hal import linux

    FakeSupervisor.started, FakeSupervisor.fail_with = [], None
    monkeypatch.setattr(linux, "SupervisorClient", FakeSupervisor)
    return FakeSupervisor


def supervised_hal(chips, **kwargs):
    pattern, table = chips
    fake = FakeGpiod(table)
    events = EventLog(target="linux", board_id="linux-rpi5")
    consulted: list[str] = []
    hal = LinuxHAL(
        chip_glob=pattern,
        gpiod=fake,
        events=events,
        authorize=lambda *args: consulted.append("authorize"),
        **kwargs,
    )
    return hal, fake, events, consulted


def test_supervision_is_on_by_default_and_holds_every_enveloped_line(
    chips, fake_supervisor, monkeypatch
):
    monkeypatch.delenv("NEUROEDGE_LINUX_SUPERVISE")  # the suite opts out; a deployment does not
    hal, fake, _, _ = supervised_hal(chips)
    assert hal.supervision == "on"
    (supervisor,) = fake_supervisor.started
    assert sorted(supervisor.lines) == ["door_lock", "gate_relay", "porch_light"]
    assert fake.requests == [] or all(not r.offsets for r in fake.requests), (
        "the runtime holds none of the supervised lines"
    )
    hal.digital_out("porch_light", "on")
    assert supervisor.on == {"porch_light": True}
    hal.close()
    assert supervisor.on["porch_light"] is False and not supervisor.running


@pytest.mark.parametrize("how", ["env", "argument"])
def test_the_opt_out_is_explicit_and_recorded(chips, fake_supervisor, monkeypatch, how):
    monkeypatch.delenv("NEUROEDGE_LINUX_SUPERVISE")
    if how == "env":
        monkeypatch.setenv("NEUROEDGE_LINUX_SUPERVISE", "0")
        hal, *_ = supervised_hal(chips)
    else:
        hal, *_ = supervised_hal(chips, supervise=False)
    assert hal.supervision == "off" and fake_supervisor.started == []
    hal.close()


def test_a_supervisor_that_cannot_start_refuses_every_on_and_keeps_off_working(
    chips, fake_supervisor
):
    from neuroedge.errors import BoardCapabilityError

    fake_supervisor.fail_with = BoardCapabilityError("w", "no gpiod in the child", "h")
    hal, fake, events, consulted = supervised_hal(chips, supervise=True)
    assert hal.supervision == "failed"
    assert events.of_type("supervision_unavailable") == [{"reason": "no gpiod in the child"}]
    for operation in ("on", "pulse"):
        with pytest.raises(EnvelopeRefusedError) as raised:
            hal.digital_out("porch_light", operation, 100)
        assert raised.value.reason == "supervisor_unavailable"
        assert "no gpiod in the child" in raised.value.why and "off" in raised.value.how
    assert consulted == [], "refused before authorize: no token is spent"
    assert hal.pin("porch_light").never_pulsed()
    assert [e["reason"] for e in events.of_type("envelope_refused")] == [
        "supervisor_unavailable"
    ] * 2
    hal.digital_out("porch_light", "off")  # off always works
    assert events.of_type("actuator_command") == [
        {"pin": "porch_light", "operation": "off", "duration_ms": 0}
    ]
    hal.close()


def test_a_supervisor_that_is_lost_refuses_the_next_on_and_not_the_off(chips, fake_supervisor):
    hal, _, events, consulted = supervised_hal(chips, supervise=True)
    hal.digital_out("porch_light", "on")
    assert consulted == ["authorize"]
    fake_supervisor.started[0].running = False  # the process died: its lines went down with it
    with pytest.raises(EnvelopeRefusedError) as raised:
        hal.digital_out("door_lock", "on")
    assert raised.value.reason == "supervisor_unavailable"
    assert consulted == ["authorize"]
    hal.digital_out("porch_light", "off")
    assert not hal.line_value("porch_light")
    hal.close()
