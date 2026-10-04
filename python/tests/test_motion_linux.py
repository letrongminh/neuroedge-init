"""
TSK-I2a-05 — `motion.*` on `linux` (RFC-0011): a PWM channel and the driver's enable line.

Against the in-memory gpiod of `test_hal_linux.py` and a fake `/sys/class/pwm` tree, so these run
everywhere; the supervised cases use the supervisor stand-ins of the envelope tests and one real
supervisor process on `tests/fake_gpiod`. What no CI machine has — a motor, a servo, a driver whose
enable line cuts the power, a Pi's RP1 PWM — is `tests_linux/test_gpio_motion.py` (the enable
line on gpio-sim) and the stage-B rig (RFC-0011 §3f). The suite sets NEUROEDGE_LINUX_SUPERVISE=0.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

from neuroedge.engine import EventLog
from neuroedge.errors import BoardCapabilityError, EnvelopeRefusedError
from neuroedge.hal import linux
from neuroedge.hal.linux import LinuxHAL
from neuroedge.hal.motion_pwm import (
    MOTION_ENV,
    MOTOR_PWM_HZ,
    SERVO_MAX_NS,
    SERVO_MIN_NS,
    parse_motion_sources,
)
from neuroedge.hal.pwm import SysfsPwm

from .test_hal_linux import LINES, FakeGpiod
from .test_hal_linux_envelope import FakeSupervisor
from .test_motion import FakeClock

LINES_WITH_DRIVERS = [*LINES, "motor_en", "servo_en"]
SOURCES = {"wheel_left": "pwmchip0/0", "gripper": "pwmchip0/1"}
MOTOR_PERIOD_NS = round(1e9 / MOTOR_PWM_HZ)


@pytest.fixture
def chips(tmp_path):
    path = tmp_path / "gpiochip0"
    path.write_text("")
    return str(tmp_path / "gpiochip*"), {str(path): LINES_WITH_DRIVERS}


@pytest.fixture
def sysfs(tmp_path):
    """`/sys` with one PWM chip of two channels already exported, as the pwm-2chan overlay gives."""
    root = tmp_path / "sys"
    chip = root / "class" / "pwm" / "pwmchip0"
    chip.mkdir(parents=True)
    (chip / "export").write_text("")
    (chip / "npwm").write_text("2\n")
    for index in (0, 1):
        channel = chip / f"pwm{index}"
        channel.mkdir()
        for name in ("period", "duty_cycle", "enable"):
            (channel / name).write_text("0\n")
    return root


def pwm(sysfs, index, name):
    # The fake sysfs is a plain file: the ramp thread's write truncates it before writing, so a
    # read can land in between and see "". The kernel's attribute write is atomic; read again.
    path = sysfs / "class" / "pwm" / "pwmchip0" / f"pwm{index}" / name
    for _ in range(100):
        text = path.read_text().strip()
        if text:
            return int(text)
        time.sleep(0.001)
    raise AssertionError(f"{path} stayed empty")


def open_hal(chips, sysfs, *, clock=None, **kwargs):
    pattern, table = chips
    fake = FakeGpiod(table)
    events = (
        EventLog(clock) if clock is not None else EventLog(target="linux", board_id="linux-rpi5")
    )
    options = {
        "authorize": lambda *_: None,
        "motion": ["wheel_left", "gripper"],
        "motion_sources": SOURCES,
        "sysfs_root": sysfs,
    }
    hal = LinuxHAL(chip_glob=pattern, gpiod=fake, events=events, **{**options, **kwargs})
    return hal, fake, events


@pytest.fixture
def fake_supervisor(monkeypatch):
    """The supervisor process, replaced by the stand-in of the envelope tests."""
    FakeSupervisor.started, FakeSupervisor.fail_with = [], None
    monkeypatch.setattr(linux, "SupervisorClient", FakeSupervisor)
    return FakeSupervisor


def level(fake, pin):
    values = [value for name, value in fake.history if name == pin]
    return bool(values and values[-1])


def wait_until(condition, timeout_s: float = 3.0):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if condition():
            return
        time.sleep(0.005)
    pytest.fail("the condition never held")


# -- a motor and a servo behind PWM and an enable line -------------------------------------------------


def test_the_pwm_is_set_up_silent_when_the_hal_starts(chips, sysfs):
    (sysfs / "class/pwm/pwmchip0/pwm0/duty_cycle").write_text("40000\n")  # a crashed run's leftover
    hal, fake, _ = open_hal(chips, sysfs)
    assert pwm(sysfs, 0, "duty_cycle") == 0 and pwm(sysfs, 0, "enable") == 0
    assert pwm(sysfs, 1, "enable") == 0  # a servo gets no pulse until it is commanded
    assert fake.history == [], "no enable line was driven"
    hal.close()


def test_the_pwm_is_programmed_before_the_enable_line_rises_and_the_line_falls_first(
    chips, sysfs, monkeypatch
):
    """RFC-0010's ordering rule, for a motion channel: controller up, then the line; line down, then off."""
    from .test_hal_linux import FakeRequest

    order: list[tuple] = []
    write, set_value = SysfsPwm._write, FakeRequest.set_value

    def traced_write(directory, name, value):
        order.append(("pwm", name, value))
        return write(directory, name, value)

    def traced_set(self, offset, value):
        order.append(("line", self.world.chips[self.path][offset], value.value))
        return set_value(self, offset, value)

    monkeypatch.setattr(SysfsPwm, "_write", staticmethod(traced_write))
    monkeypatch.setattr(FakeRequest, "set_value", traced_set)
    hal, fake, events = open_hal(chips, sysfs)
    order.clear()
    hal.motion_motor("wheel_left", 0.3, ramp_ms=200, called_from="t")
    up = order.index(("line", "motor_en", 1))
    assert ("pwm", "enable", 1) in order[:up], order  # programmed and enabled before the line rises
    assert order[0] == ("pwm", "duty_cycle", 0)  # duty to zero, then the period, then the duty
    order.clear()
    hal.motion_stop("wheel_left", called_from="t")
    down = order.index(("line", "motor_en", 0))
    assert ("pwm", "enable", 0) in order[down:], order  # the line first, the controller after
    assert not level(fake, "motor_en") and pwm(sysfs, 0, "duty_cycle") == 0
    assert [e["data"]["state"] for e in events.events if e["type"] == "motion_safe"] == ["stop"]
    hal.close()


def test_a_motors_speed_is_its_duty_cycle_and_it_gets_there_by_a_ramp(chips, sysfs):
    hal, _fake, _ = open_hal(chips, sysfs)
    hal.motion_motor("wheel_left", 0.5, ramp_ms=200, called_from="t")
    # ramping: the duty is somewhere between zero and the commanded half period, never above it
    wait_until(lambda: 0 < pwm(sysfs, 0, "duty_cycle") <= MOTOR_PERIOD_NS // 2, 2.0)
    assert 0 < hal.motion_values()["wheel_left"]["speed"] <= 0.5
    hal.close()


@pytest.mark.parametrize(
    ("target", "pulse_ns"), [(0, SERVO_MIN_NS), (45, 1_500_000), (90, SERVO_MAX_NS)]
)
def test_a_servos_target_is_a_pulse_across_its_declared_range(chips, sysfs, target, pulse_ns):
    hal, fake, _ = open_hal(chips, sysfs)
    hal.motion_servo("gripper", target, called_from="t")
    assert pwm(sysfs, 1, "duty_cycle") == pulse_ns and pwm(sysfs, 1, "enable") == 1
    assert level(fake, "servo_en")
    hal.close()


def test_the_enable_line_is_never_an_agents_to_drive(chips, sysfs):
    hal, fake, _ = open_hal(chips, sysfs)
    with pytest.raises(BoardCapabilityError, match="enable line"):
        hal.digital_out("motor_en", "on", called_from="actions/a.py:3")
    assert fake.history == []
    hal.close()


def test_a_lease_that_runs_out_stops_the_channel_by_the_hals_own_timer(chips, sysfs):
    hal, fake, events = open_hal(chips, sysfs)
    hal.motion_motor("wheel_left", 0.3, called_from="t")  # no ledger: the board's 200 ms lease
    assert level(fake, "motor_en")
    wait_until(lambda: not level(fake, "motor_en"))
    wait_until(lambda: pwm(sysfs, 0, "duty_cycle") == 0)
    # The HAL's timer acts on the hardware first (line down, duty 0) and records afterwards.
    wait_until(lambda: any(e["type"] == "motion_safe" for e in events.events))
    assert [e["data"] for e in events.events if e["type"] == "motion_safe"] == [
        {"channel": "wheel_left", "state": "stop", "cause": "lease_expired"}
    ]
    hal.close()


def test_a_renewal_before_the_lease_ends_keeps_the_run_going(chips, sysfs):
    hal, fake, events = open_hal(chips, sysfs)
    for _ in range(4):
        hal.motion_motor("wheel_left", 0.3, called_from="t")
        time.sleep(0.1)  # half a lease
    assert level(fake, "motor_en")
    assert not [e for e in events.events if e["type"] == "motion_safe"]
    assert [e["data"]["run"] for e in events.events if e["type"] == "motion_command"] == [
        "new",
        "renewed",
        "renewed",
        "renewed",
    ]
    hal.close()


def test_a_servo_that_declares_hold_keeps_power_and_its_pulse_when_the_lease_ends(chips, sysfs):
    clock = FakeClock()
    hal, fake, events = open_hal(chips, sysfs, clock=clock)
    hal.motion_servo("gripper", 60, called_from="t")
    clock.advance(200)
    hal.settle_motion()
    assert level(fake, "servo_en") and pwm(sysfs, 1, "enable") == 1  # holding
    assert pwm(sysfs, 1, "duty_cycle") == round(SERVO_MIN_NS + 60 / 90 * 1_000_000)
    clock.advance(2000)  # max_hold_ms
    hal.settle_motion()
    assert not level(fake, "servo_en") and pwm(sysfs, 1, "enable") == 0
    assert [
        (e["data"]["state"], e["data"]["cause"])
        for e in events.events
        if e["type"] == "motion_safe"
    ] == [
        ("hold", "lease_expired"),
        ("stop", "max_hold_ms"),
    ]
    hal.close()


def test_a_barge_in_stops_a_motor_at_once(chips, sysfs):
    hal, fake, events = open_hal(chips, sysfs)
    hal.motion_motor("wheel_left", 0.4, called_from="t")
    assert hal.motion_barge_in() == ["wheel_left"]
    assert not level(fake, "motor_en") and pwm(sysfs, 0, "duty_cycle") == 0
    assert [e["data"]["cause"] for e in events.events if e["type"] == "motion_safe"] == ["barge_in"]
    hal.close()


def test_close_stops_every_channel_and_leaves_no_pwm_putting_out(chips, sysfs):
    hal, fake, events = open_hal(chips, sysfs)
    hal.motion_motor("wheel_left", 0.4, called_from="t")
    hal.motion_servo("gripper", 30, called_from="t")
    hal.close()
    assert not level(fake, "motor_en") and not level(fake, "servo_en")
    assert pwm(sysfs, 0, "enable") == 0 and pwm(sysfs, 1, "enable") == 0
    assert pwm(sysfs, 0, "duty_cycle") == 0
    assert all(request.released for request in fake.requests)
    assert {e["data"]["cause"] for e in events.events if e["type"] == "motion_safe"} == {"close"}


def test_a_write_the_pwm_refuses_leaves_the_driver_down_and_the_budget_whole(
    chips, sysfs, monkeypatch
):
    hal, fake, events = open_hal(chips, sysfs)

    real = SysfsPwm.apply_ns

    def refuse(self, pin, period_ns, duty_ns, called_from="x"):
        if duty_ns > 0:
            raise OSError(5, "Input/output error")
        return real(self, pin, period_ns, duty_ns, called_from)

    monkeypatch.setattr(SysfsPwm, "apply_ns", refuse)
    with pytest.raises(BoardCapabilityError, match="PWM channel could not be written"):
        hal.motion_servo("gripper", 30, called_from="t")  # a servo's first pulse is immediate
    assert not level(fake, "servo_en")
    assert hal.envelope.live("gripper") is None  # the channel is known to be down: refunded
    assert not [e for e in events.events if e["type"] == "motion_command"]
    hal.close()


def test_a_ramp_step_the_pwm_refuses_stops_the_channel_and_says_why(chips, sysfs, monkeypatch):
    hal, fake, events = open_hal(chips, sysfs)

    def refuse(self, pin, duty_ns, called_from="x"):  # the first program passes; ramp steps do not
        raise OSError(5, "Input/output error")

    monkeypatch.setattr(SysfsPwm, "set_duty_ns", refuse)
    hal.motion_motor("wheel_left", 0.4, called_from="t")
    # The driver goes down first, then the event is written (the safe state never waits on
    # the log): wait for both, then the record is exact.
    wait_until(lambda: not level(fake, "motor_en"))
    wait_until(lambda: any(e["type"] == "motion_safe" for e in events.events))
    assert not level(fake, "motor_en")
    assert [e["data"]["cause"] for e in events.events if e["type"] == "motion_safe"] == [
        "actuator_fault"
    ]
    monkeypatch.undo()
    hal.close()


def test_when_the_channel_cannot_be_told_to_stop_the_reservation_stays_held(
    chips, sysfs, monkeypatch
):
    hal, fake, _ = open_hal(chips, sysfs)

    def refuse(self, *_, **__):
        raise OSError(5, "Input/output error")

    monkeypatch.setattr(SysfsPwm, "apply_ns", refuse)
    monkeypatch.setattr(SysfsPwm, "off", refuse)
    with pytest.raises(BoardCapabilityError):
        hal.motion_motor("wheel_left", 0.3, called_from="t")
    assert hal.envelope.live("wheel_left") is not None  # the safe side of not knowing
    monkeypatch.undo()
    hal.close()


def test_the_envelope_gates_a_run_on_linux_too(chips, sysfs):
    clock = FakeClock()
    hal, fake, events = open_hal(chips, sysfs, clock=clock)
    hal.motion_motor("wheel_left", 0.3, called_from="t")
    clock.advance(250)
    hal.settle_motion()  # the run ended: min_interval_ms is 2000
    with pytest.raises(EnvelopeRefusedError) as raised:
        hal.motion_motor("wheel_left", 0.3, called_from="t")
    assert raised.value.reason == "min_interval_ms"
    assert not level(fake, "motor_en")
    assert events.of_type("envelope_refused")[-1]["pin"] == "wheel_left"
    hal.close()


# -- the machine's wiring and what is refused when the HAL starts ---------------------------------------------


def test_a_channel_with_no_pwm_wired_is_refused_before_any_line_is_requested(chips, sysfs):
    pattern, table = chips
    fake = FakeGpiod(table)
    with pytest.raises(BoardCapabilityError, match="no PWM channel is wired") as raised:
        LinuxHAL(
            chip_glob=pattern,
            gpiod=fake,
            motion=["wheel_left"],
            motion_sources={},
            sysfs_root=sysfs,
        )
    assert MOTION_ENV in raised.value.how
    assert fake.requests == []


def test_a_channel_the_board_does_not_declare_is_refused(chips, sysfs):
    with pytest.raises(BoardCapabilityError, match="declares no motion channel 'arm'"):
        open_hal(chips, sysfs, motion=["arm"], motion_sources={"arm": "pwmchip0/0"})


def test_an_enable_line_the_chip_does_not_have_is_refused_before_any_line_is_held(tmp_path, sysfs):
    path = tmp_path / "gpiochip0"
    path.write_text("")
    fake = FakeGpiod({str(path): LINES})  # no motor_en
    with pytest.raises(BoardCapabilityError, match="motor_en"):
        LinuxHAL(
            chip_glob=str(tmp_path / "gpiochip*"),
            gpiod=fake,
            motion=["wheel_left"],
            motion_sources=SOURCES,
            sysfs_root=sysfs,
        )
    assert fake.requests == []


def test_a_pwm_that_cannot_be_set_up_releases_every_line(chips, tmp_path):
    bare = tmp_path / "bare-sys"  # no pwmchip at all: no software PWM stands in for it
    (bare / "class" / "pwm").mkdir(parents=True)
    pattern, table = chips
    fake = FakeGpiod(table)
    with pytest.raises(BoardCapabilityError, match="kernel has no PWM chip"):
        LinuxHAL(
            chip_glob=pattern, gpiod=fake, motion=["wheel_left"], motion_sources=SOURCES,
            sysfs_root=bare,
        )  # fmt: skip
    assert all(request.released for request in fake.requests)


def test_a_channel_not_brought_up_is_refused_with_the_way_to_bring_it(chips, sysfs):
    pattern, table = chips
    hal = LinuxHAL(chip_glob=pattern, gpiod=FakeGpiod(table), authorize=lambda *_: None)
    with pytest.raises(BoardCapabilityError, match="no motion channel is set up"):
        hal.motion_motor("wheel_left", 0.2, called_from="t")
    hal.close()


def test_the_wiring_comes_from_the_environment_like_the_sensors(chips, sysfs, monkeypatch):
    monkeypatch.setenv(MOTION_ENV, "wheel_left=pwmchip0/0;gripper=pwmchip0/1")
    hal, _fake, _ = open_hal(chips, sysfs, motion_sources=None)
    hal.motion_motor("wheel_left", 0.2, called_from="t")
    hal.close()


@pytest.mark.parametrize("text", ["wheel_left", "wheel_left=hwmon0", "=pwmchip0/0", "a=pwmchip0/x"])
def test_a_malformed_wiring_is_a_three_part_error(text):
    with pytest.raises(BoardCapabilityError, match="not channel=pwmchipN/M"):
        parse_motion_sources(text, MOTION_ENV)


def test_an_unexported_channel_is_exported_and_waited_for(tmp_path, monkeypatch):
    from neuroedge.hal import pwm as pwm_module

    root = tmp_path / "sys"
    chip = root / "class" / "pwm" / "pwmchip0"
    chip.mkdir(parents=True)
    (chip / "export").write_text("")
    (chip / "npwm").write_text("2\n")
    monkeypatch.setattr(pwm_module, "EXPORT_WAIT_S", 0.05)
    with pytest.raises(OSError, match="did not appear"):
        SysfsPwm(root, {"wheel_left": "pwmchip0/0"}, "t").apply_ns("wheel_left", 50_000, 0)
    assert (chip / "export").read_text().strip() == "0"


def test_a_kernel_pwm_channel_has_one_owner(chips, sysfs):
    """A motion channel and a digital.out PWM pin (RFC-0010) cannot be wired to one pwmchipN/M."""
    pattern, table = chips
    with pytest.raises(BoardCapabilityError, match="one owner") as raised:
        LinuxHAL(
            chip_glob=pattern, gpiod=FakeGpiod(table), motion=["wheel_left"],
            motion_sources={"wheel_left": "pwmchip0/0"}, pwm_channels={"fan": "pwmchip0/0"},
            sysfs_root=sysfs,
        )  # fmt: skip
    assert "PWM pin 'fan'" in raised.value.why
    with pytest.raises(BoardCapabilityError, match="one owner"):
        open_hal(chips, sysfs, motion_sources={"wheel_left": "pwmchip0/0", "gripper": "pwmchip0/0"})


def test_a_motion_channel_and_a_pwm_channel_run_side_by_side(chips, sysfs):
    """Both enable families (fan_en and motor_en) are held at once, each by its own backend."""
    pattern, table = chips
    fake = FakeGpiod({next(iter(table)): [*LINES_WITH_DRIVERS, "fan_en"]})
    hal = LinuxHAL(
        chip_glob=pattern, gpiod=fake, authorize=lambda *_: None, motion=["wheel_left"],
        motion_sources={"wheel_left": "pwmchip0/0"}, pwm_channels={"fan": "pwmchip0/1"},
        needs={"pwm": ["fan"], "where": "t"}, sysfs_root=sysfs,
    )  # fmt: skip
    try:
        hal.motion_motor("wheel_left", 0.3, called_from="t")
        hal.digital_out("fan", "pwm", 5000, frequency_hz=1000, duty=0.4, called_from="t")
        assert level(fake, "motor_en") and level(fake, "fan_en")
        assert 390_000 < pwm(sysfs, 1, "duty_cycle") <= 400_000  # the fan's quantised 40 %
    finally:
        hal.close()
    assert not level(fake, "motor_en") and not level(fake, "fan_en")


# -- a replay never touches the machine's PWM or lines --------------------------------------------------------------


def test_a_replay_brings_up_the_model_and_leaves_the_machine_alone(chips, sysfs):
    pattern, table = chips
    fake = FakeGpiod(table)
    hal = LinuxHAL(chip_glob=pattern, gpiod=fake, replay=True, authorize=lambda *_: None)
    hal.motion_motor("wheel_left", 0.3, called_from="t")
    assert hal.motion_values()["wheel_left"]["mode"] == "active"
    assert not level(fake, "motor_en") and pwm(sysfs, 0, "duty_cycle") == 0
    hal.close()


# -- supervision: the enable line is held by the supervisor process ------------------------------------------------------


def test_the_enable_lines_are_supervised_with_a_deadline_and_a_drop_stops_the_channel(
    chips,
    sysfs,
    fake_supervisor,
    monkeypatch,
):
    monkeypatch.delenv("NEUROEDGE_LINUX_SUPERVISE")
    clock = FakeClock()
    hal, fake, events = open_hal(chips, sysfs, clock=clock)
    (supervisor,) = fake_supervisor.started
    assert {"motor_en", "servo_en"} <= set(supervisor.lines)
    assert all(not r.offsets or "motor_en" not in str(r.offsets) for r in fake.requests)
    hal.motion_motor("wheel_left", 0.3, called_from="t")
    assert supervisor.on["motor_en"] is True
    hal._supervisor_dropped("motor_en", "heartbeat")  # the runtime was frozen: the driver is down
    assert hal.motion_values()["wheel_left"]["mode"] == "idle"
    assert [e["data"]["cause"] for e in events.events if e["type"] == "motion_safe"] == [
        "supervisor_heartbeat"
    ]
    hal.close()
    assert supervisor.on["motor_en"] is False


def test_a_command_is_refused_when_the_supervisor_that_holds_the_driver_is_gone(
    chips,
    sysfs,
    fake_supervisor,
    monkeypatch,
):
    monkeypatch.delenv("NEUROEDGE_LINUX_SUPERVISE")
    hal, _fake, events = open_hal(chips, sysfs)
    (supervisor,) = fake_supervisor.started
    supervisor.running = False
    with pytest.raises(BoardCapabilityError, match="supervisor"):
        hal.motion_motor("wheel_left", 0.3, called_from="t")
    assert hal.envelope.live("wheel_left") is None
    assert not [e for e in events.events if e["type"] == "motion_command"]
    hal.close()


FAKE_GPIOD = str(Path(__file__).parent / "fake_gpiod")

RUNTIME = textwrap.dedent(
    """
    import sys
    from neuroedge.engine.trace_sink import EventLog
    from neuroedge.hal.linux import LinuxHAL

    hal = LinuxHAL(
        chip_glob=sys.argv[1], authorize=lambda *args: None, events=EventLog(),
        supervise=True, supervisor_options={"heartbeat_timeout_ms": 400},
        motion=["wheel_left"], motion_sources={"wheel_left": "pwmchip0/0"}, sysfs_root=sys.argv[2],
    )
    hal.motion_motor("wheel_left", 0.3)
    print("moving", flush=True)
    sys.stdin.readline()
    hal.close()
    print("closed", flush=True)
    """
)


def test_a_runtime_stopped_with_sigstop_while_a_motor_runs_loses_its_driver(
    tmp_path, sysfs, monkeypatch
):
    """RFC-0011 §7: a hung runtime — the lease timer cannot run — and the driver still goes down."""
    chip = tmp_path / "gpiochip0"
    chip.write_text("")
    state = tmp_path / "state.json"
    env = {
        **os.environ,
        "PYTHONPATH": FAKE_GPIOD + os.pathsep + os.environ.get("PYTHONPATH", ""),
        "FAKE_GPIOD_STATE": str(state),
        "FAKE_GPIOD_LINES": json.dumps({str(chip): LINES_WITH_DRIVERS}),
        "NEUROEDGE_LINUX_SUPERVISE": "1",
    }

    def value():
        try:
            return json.loads(state.read_text(encoding="utf-8")).get(
                f"{chip}:{LINES_WITH_DRIVERS.index('motor_en')}"
            )
        except (FileNotFoundError, ValueError):
            return None

    runtime = subprocess.Popen(
        [sys.executable, "-c", RUNTIME, str(chip.parent / "gpiochip*"), str(sysfs)],
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert runtime.stdout.readline().strip() == "moving"
        wait_until(lambda: value() == 1, 5)
        os.kill(runtime.pid, signal.SIGSTOP)  # no timer of the runtime runs from here on
        started = time.monotonic()
        wait_until(lambda: value() == 0, 5)
        assert time.monotonic() - started <= 0.4 + 0.05 + 1.5  # heartbeat + margin + CI allowance
        os.kill(runtime.pid, signal.SIGCONT)
        runtime.stdin.write("go\n")
        runtime.stdin.flush()
        assert runtime.stdout.readline().strip() == "closed"
        assert runtime.wait(10) == 0
    finally:
        if runtime.poll() is None:
            os.kill(runtime.pid, signal.SIGCONT)
            runtime.kill()
            runtime.wait()
    assert value() == 0


# -- a session on linux ----------------------------------------------------------------------------------------------------


def test_a_session_on_linux_brings_up_the_channels_its_agent_names(
    tmp_path, chips, sysfs, monkeypatch
):
    import asyncio

    from neuroedge.sim import SimSession

    from .test_motion import write_agent

    pattern, table = chips
    fake = FakeGpiod(table)
    monkeypatch.setattr(linux, "CHIP_GLOB", pattern)
    monkeypatch.setattr(linux, "_import_gpiod", lambda: fake)
    monkeypatch.setenv(MOTION_ENV, "wheel_left=pwmchip0/0")
    agent = write_agent(tmp_path)
    session = SimSession.load(agent, target="linux", target_options={"sysfs_root": sysfs})
    try:
        assert session.hal.motion_values().keys() == {"wheel_left"}  # the gripper is not asked for
        turn = asyncio.run(session.handle("đi tới"))
        assert turn.allowed
        assert level(fake, "motor_en") and pwm(sysfs, 0, "duty_cycle") > 0
        assert session.events.of_type("motion_command")[0]["channel"] == "wheel_left"
    finally:
        session.close()
    assert not level(fake, "motor_en")


def test_a_session_whose_channel_has_no_pwm_wired_does_not_start(
    tmp_path, chips, sysfs, monkeypatch
):
    from neuroedge.sim import SimSession

    from .test_motion import write_agent

    pattern, table = chips
    fake = FakeGpiod(table)
    monkeypatch.setattr(linux, "CHIP_GLOB", pattern)
    monkeypatch.setattr(linux, "_import_gpiod", lambda: fake)
    monkeypatch.delenv(MOTION_ENV, raising=False)
    with pytest.raises(BoardCapabilityError, match="no PWM channel is wired"):
        SimSession.load(write_agent(tmp_path), target="linux", target_options={"sysfs_root": sysfs})
    assert fake.requests == []
