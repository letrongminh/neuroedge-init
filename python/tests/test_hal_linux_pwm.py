"""
TSK-W1-01 — PWM on `linux` against a fake `/sys/class/pwm`, the in-memory gpiod and a fake supervisor
(RFC-0010 §3e, §9.1, §9.2, §9.11).

The kernel's PWM is the only PWM there is: the controller is programmed through sysfs files and
the only GPIO line a PWM command touches is the channel's enable line, which the HAL raises after
the controller is programmed and drops first when it goes down. The pwm rules of the board, the
envelope and the gate are `test_pwm.py`; the same HAL on real kernel lines is `tests_linux/`
(gpio-sim has lines but no PWM chip, so the controller itself is only ever the fake tree here).
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from neuroedge.engine.trace_sink import EventLog
from neuroedge.errors import BoardCapabilityError, EnvelopeRefusedError, PerceptionUnavailableError
from neuroedge.hal import pwm as pwm_module
from neuroedge.hal.envelope import EnvelopeLimits, SafetyEnvelope
from neuroedge.hal.linux import PWM_ENV, LinuxHAL
from neuroedge.hal.pwm import SysfsPwm, parse_channels

from .test_hal_linux import FakeGpiod
from .test_hal_linux_envelope import wait_until

LINES = ["door_lock", "porch_light", "gate_relay", "fan_en"]
CHANNEL = "pwmchip0/2"


@pytest.fixture(autouse=True)
def no_machine_wiring(monkeypatch):
    monkeypatch.delenv(PWM_ENV, raising=False)


@pytest.fixture
def sysfs(tmp_path):
    """`/sys` with one PWM chip of 4 channels, channel 2 already exported."""
    root = tmp_path / "sys"
    chip = root / "class" / "pwm" / "pwmchip0"
    channel = chip / "pwm2"
    channel.mkdir(parents=True)
    (chip / "npwm").write_text("4\n")
    (chip / "export").write_text("")
    for name in ("period", "duty_cycle", "enable"):
        (channel / name).write_text("0\n")
    return root


def files(sysfs) -> dict[str, int]:
    channel = sysfs / "class" / "pwm" / "pwmchip0" / "pwm2"
    while True:
        try:
            return {
                name: int((channel / name).read_text())
                for name in ("period", "duty_cycle", "enable")
            }
        except ValueError:  # the HAL's timer thread is between truncating a file and writing it
            time.sleep(0.001)


def make(
    tmp_path,
    sysfs,
    *,
    board=None,
    needs=True,
    envelope=None,
    supervise=False,
    **kwargs,
):
    chip = tmp_path / "gpiochip0"
    chip.write_text("")
    fake = FakeGpiod({str(chip): LINES})
    events = EventLog(target="linux", board_id="linux-rpi5")
    hal = LinuxHAL(
        board,
        chip_glob=str(tmp_path / "gpiochip*"),
        gpiod=fake,
        events=events,
        envelope=envelope,
        authorize=kwargs.pop("authorize", lambda *_: None),
        sysfs_root=sysfs,
        pwm_channels={"fan": CHANNEL},
        supervise=supervise,
        needs={"pwm": ["fan"], "where": "agent"} if needs else None,
        **kwargs,
    )
    return hal, fake, events


def fan(hal, *, frequency_hz=1000, duty=0.5, duration_ms=60, **kw):
    return hal.digital_out(
        "fan",
        "pwm",
        duration_ms,
        signature="token",
        called_from="actions/fan.py:3",
        frequency_hz=frequency_hz,
        duty=duty,
        **kw,
    )


def enable_history(fake) -> list[bool]:
    return [bool(value) for name, value in fake.history if name == "fan_en"]


# --- the kernel's PWM, programmed through sysfs ---------------------------------------------


def test_a_command_programs_the_controller_then_raises_the_enable_line(tmp_path, sysfs):
    hal, fake, events = make(tmp_path, sysfs)
    assert not hal.line_value("fan")
    fan(hal, frequency_hz=1000, duty=0.5, duration_ms=5_000)
    assert files(sysfs) == {"period": 1_000_000, "duty_cycle": 500_000, "enable": 1}
    assert hal.line_value("fan") and hal.line_value("fan_en"), (
        "the channel is up while its enable line is"
    )
    assert enable_history(fake) == [True], (
        "the one GPIO move of a PWM command: the enable line, once"
    )
    assert events.of_type("actuator_command") == [
        {
            "pin": "fan",
            "operation": "pwm",
            "duration_ms": 5_000,
            "frequency_hz": 1000,
            "duty": 0.5,
        }
    ]
    hal.close()


def test_the_nanosecond_duty_never_exceeds_the_checked_ratio(tmp_path, sysfs):
    hal, *_ = make(tmp_path, sysfs)
    fan(hal, frequency_hz=7_001, duty=0.3, duration_ms=5_000)  # a period that is not whole ns
    state = files(sysfs)
    assert state["duty_cycle"] / state["period"] <= 0.3
    hal.close()


def test_the_pwm_is_hardware_only_nothing_toggles_a_gpio_line_at_a_frequency(tmp_path, sysfs):
    hal, fake, _ = make(tmp_path, sysfs)
    fan(hal, frequency_hz=25_000, duty=0.5, duration_ms=5_000)
    time.sleep(0.05)
    assert [name for name, _ in fake.history] == ["fan_en"] and enable_history(fake) == [True]
    hal.close()


def test_the_channel_goes_off_when_the_time_is_up_enable_line_first(tmp_path, sysfs):
    hal, fake, events = make(tmp_path, sysfs)
    fan(hal, duration_ms=60)
    wait_until(lambda: not hal.line_value("fan"))
    wait_until(lambda: files(sysfs)["enable"] == 0)
    # off() writes enable = 0 first, then duty_cycle = 0 (the output stops before anything
    # else): wait for the second write too, then the end state is exact.
    wait_until(lambda: files(sysfs)["duty_cycle"] == 0)
    assert files(sysfs)["enable"] == 0
    assert enable_history(fake) == [True, False]
    assert hal.commanded_pwm("fan") is None
    hal.close()


def test_off_never_needs_a_token_and_drops_the_enable_line(tmp_path, sysfs):
    def refuse(*_):
        raise AssertionError("an off asked for a token")

    hal, fake, events = make(tmp_path, sysfs, authorize=lambda *_: None)
    fan(hal, duration_ms=5_000)
    hal.authorize = refuse
    hal.digital_out("fan", "off")
    assert not hal.line_value("fan") and files(sysfs)["enable"] == 0
    assert events.of_type("actuator_command")[-1] == {
        "pin": "fan",
        "operation": "off",
        "duration_ms": 0,
    }
    assert hal.commanded_pwm("fan") is None
    hal.close()


def test_close_brings_the_controller_and_the_line_down(tmp_path, sysfs):
    hal, fake, _ = make(tmp_path, sysfs)
    fan(hal, duration_ms=60_000)
    hal.close()
    assert enable_history(fake)[-1] is False
    assert files(sysfs)["enable"] == 0 and files(sysfs)["duty_cycle"] == 0
    hal.close()  # idempotent


# --- an agent drives only the channels its session prepared ----------------------------------


def test_a_channel_the_session_did_not_prepare_is_not_driven_and_no_token_is_spent(tmp_path, sysfs):
    spent: list[str] = []
    hal, fake, events = make(
        tmp_path, sysfs, needs=False, authorize=lambda *args: spent.append("token")
    )
    with pytest.raises(BoardCapabilityError, match="not prepared to drive the PWM channel"):
        fan(hal)
    assert spent == [] and fake.history == [] and files(sysfs)["enable"] == 0
    hal.digital_out("fan", "off")  # off is always allowed, and has nothing to bring down
    hal.close()


def test_on_and_pulse_are_refused_on_linux_too_before_anything_moves(tmp_path, sysfs):
    hal, fake, _ = make(tmp_path, sysfs)
    for operation in ("on", "pulse"):
        with pytest.raises(BoardCapabilityError, match="takes only 'pwm' and 'off'"):
            hal.digital_out("fan", operation, 100, "token", "t")
    with pytest.raises(BoardCapabilityError, match="enable line"):
        hal.digital_out("fan_en", "on", 100, "token", "t")
    assert fake.history == [] and files(sysfs)["enable"] == 0
    hal.close()


def test_a_board_limit_is_refused_before_the_controller_is_touched(tmp_path, sysfs):
    hal, fake, _ = make(tmp_path, sysfs)
    with pytest.raises(BoardCapabilityError, match="above max_duty"):
        fan(hal, duty=0.9)
    assert fake.history == [] and files(sysfs) == {"period": 0, "duty_cycle": 0, "enable": 0}
    hal.close()


def test_needs_names_only_pwm_channels(tmp_path, sysfs):
    chip = tmp_path / "gpiochip0"
    chip.write_text("")
    fake = FakeGpiod({str(chip): LINES})
    with pytest.raises(BoardCapabilityError, match="not a PWM channel"):
        LinuxHAL(
            chip_glob=str(tmp_path / "gpiochip*"),
            gpiod=fake,
            needs={"pwm": ["door_lock"], "where": "agent"},
            sysfs_root=sysfs,
        )
    assert fake.requests == []


# --- the machine's wiring and the kernel's channel: refused now, never a software fallback -------


def test_the_channel_can_come_from_the_environment(tmp_path, sysfs, monkeypatch):
    monkeypatch.setenv(PWM_ENV, f" fan = {CHANNEL} ; ")
    chip = tmp_path / "gpiochip0"
    chip.write_text("")
    hal = LinuxHAL(
        chip_glob=str(tmp_path / "gpiochip*"),
        gpiod=FakeGpiod({str(chip): LINES}),
        authorize=lambda *_: None,
        sysfs_root=sysfs,
        supervise=False,
        needs={"pwm": ["fan"]},
    )
    fan(hal, duration_ms=5_000)
    assert files(sysfs)["enable"] == 1
    hal.close()


def test_no_channel_is_guessed_and_the_session_is_refused_before_any_line(tmp_path, sysfs):
    chip = tmp_path / "gpiochip0"
    chip.write_text("")
    fake = FakeGpiod({str(chip): LINES})
    with pytest.raises(BoardCapabilityError, match="refusing to guess") as raised:
        LinuxHAL(
            chip_glob=str(tmp_path / "gpiochip*"),
            gpiod=fake,
            needs={"pwm": ["fan"], "where": "agent"},
            sysfs_root=sysfs,
        )
    assert "NEUROEDGE_LINUX_PWM" in raised.value.how
    assert fake.requests == []


@pytest.mark.parametrize(
    ("setup", "why"),
    [
        ("no_chip", "no PWM chip"),
        ("few_channels", "has 1 channel"),
    ],
)
def test_a_kernel_without_the_channel_refuses_the_session_not_a_bit_banged_fallback(
    tmp_path, sysfs, setup, why
):
    root = sysfs / "class" / "pwm" / "pwmchip0"
    if setup == "no_chip":
        (root / "npwm").unlink()
    else:
        (root / "npwm").write_text("1\n")
    chip = tmp_path / "gpiochip0"
    chip.write_text("")
    fake = FakeGpiod({str(chip): LINES})
    with pytest.raises(BoardCapabilityError, match=why) as raised:
        LinuxHAL(
            chip_glob=str(tmp_path / "gpiochip*"),
            gpiod=fake,
            needs={"pwm": ["fan"], "where": "agent"},
            sysfs_root=sysfs,
            pwm_channels={"fan": CHANNEL},
        )
    assert "never" in raised.value.how or "mapping" in raised.value.how
    assert fake.requests == [] and fake.history == []


def test_a_mapping_for_a_pin_that_is_not_a_pwm_channel_is_refused(tmp_path, sysfs):
    chip = tmp_path / "gpiochip0"
    chip.write_text("")
    with pytest.raises(BoardCapabilityError, match="not a PWM channel"):
        LinuxHAL(
            chip_glob=str(tmp_path / "gpiochip*"),
            gpiod=FakeGpiod({str(chip): LINES}),
            sysfs_root=sysfs,
            pwm_channels={"door_lock": CHANNEL},
        )


@pytest.mark.parametrize("text", ["fan", "=pwmchip0/1", "fan="])
def test_a_malformed_channel_mapping_is_refused(text):
    with pytest.raises(BoardCapabilityError, match="is not pin=pwmchipN/channel"):
        parse_channels(text, "env")


@pytest.mark.parametrize("spec", ["pwm0", "chip0/1", "pwmchip0/x", "pwmchip0"])
def test_a_malformed_kernel_channel_is_refused(tmp_path, spec):
    with pytest.raises(BoardCapabilityError, match="not a kernel PWM channel"):
        SysfsPwm(tmp_path, {"fan": spec}, "test")


def test_a_controller_the_kernel_refuses_leaves_the_line_down_and_the_time_unspent(tmp_path, sysfs):
    channel = sysfs / "class" / "pwm" / "pwmchip0" / "pwm2"
    (channel / "period").unlink()
    (channel / "period").mkdir()  # writing it fails: EISDIR
    limits = EnvelopeLimits(
        window_s=100, max_on_ms_per_window=100, min_interval_ms=0, max_continuous_ms=100
    )
    hal, fake, events = make(
        tmp_path, sysfs, envelope=SafetyEnvelope({"fan": limits}, virtual=False)
    )
    with pytest.raises(BoardCapabilityError, match="kernel PWM refused"):
        fan(hal, duration_ms=100)
    assert enable_history(fake) in ([], [False]) and not hal.line_value("fan")
    assert hal.commanded_pwm("fan") is None and events.of_type("actuator_command") == []
    # the whole budget is still there: a refused command spends none of it
    (channel / "period").rmdir()
    (channel / "period").write_text("0\n")
    fan(hal, duration_ms=100)
    hal.close()


def test_an_unexported_channel_is_exported_and_one_that_never_appears_fails(
    tmp_path, sysfs, monkeypatch
):
    import shutil

    monkeypatch.setattr(pwm_module, "EXPORT_WAIT_S", 0.1)
    hal, fake, _ = make(tmp_path, sysfs)
    shutil.rmtree(sysfs / "class" / "pwm" / "pwmchip0" / "pwm2")
    with pytest.raises(BoardCapabilityError, match="kernel PWM refused"):
        fan(hal, duration_ms=5_000)
    assert (sysfs / "class" / "pwm" / "pwmchip0" / "export").read_text().strip() == "2"
    assert enable_history(fake) in ([], [False])
    hal.close()


# --- the envelope and the supervisor (§3d, §9.2, §9.11) --------------------------------------


def test_the_envelope_reserves_and_refuses_a_pwm_command_before_the_hardware(tmp_path, sysfs):
    limits = EnvelopeLimits(
        window_s=100, max_on_ms_per_window=10_000, min_interval_ms=0, max_continuous_ms=80
    )
    envelope = SafetyEnvelope({"fan": limits}, virtual=False)
    spent: list[str] = []
    hal, fake, events = make(
        tmp_path, sysfs, envelope=envelope, authorize=lambda *args: spent.append("token")
    )
    with pytest.raises(EnvelopeRefusedError) as raised:
        fan(hal, duration_ms=81)
    assert raised.value.reason == "max_continuous_ms"
    assert spent == [] and fake.history == [] and files(sysfs)["enable"] == 0
    fan(hal, duration_ms=80)
    assert envelope.live("fan") is not None
    wait_until(lambda: not hal.line_value("fan"))
    wait_until(lambda: envelope.live("fan") is None)
    hal.close()


def test_off_gives_the_unused_on_time_back(tmp_path, sysfs):
    limits = EnvelopeLimits(
        window_s=100, max_on_ms_per_window=200, min_interval_ms=0, max_continuous_ms=200
    )
    envelope = SafetyEnvelope({"fan": limits}, virtual=False)
    hal, *_ = make(tmp_path, sysfs, envelope=envelope)
    fan(hal, duration_ms=200)
    hal.digital_out("fan", "off")  # nearly all of it unused
    fan(hal, duration_ms=150)  # would not fit in 200 ms without the refund
    hal.close()


def test_the_enable_line_is_the_supervisors_and_has_the_on_time_as_its_deadline(
    tmp_path, sysfs, monkeypatch
):
    from .test_hal_linux_envelope import FakeSupervisor

    FakeSupervisor.started, FakeSupervisor.fail_with = [], None
    monkeypatch.setattr("neuroedge.hal.linux.SupervisorClient", FakeSupervisor)
    limits = EnvelopeLimits(
        window_s=100, max_on_ms_per_window=100_000, min_interval_ms=0, max_continuous_ms=60_000
    )
    envelope = SafetyEnvelope({"fan": limits}, virtual=False)
    hal, fake, _ = make(tmp_path, sysfs, envelope=envelope, supervise=True)
    (supervisor,) = FakeSupervisor.started
    assert "fan_en" in supervisor.lines, "the enable line is held outside the runtime"
    assert fake.history == []
    fan(hal, duration_ms=5_000)
    assert supervisor.on == {"fan_en": True} and hal.line_value("fan")
    assert fake.history == [], "the runtime itself never moved the line"
    hal.close()
    assert supervisor.on["fan_en"] is False and files(sysfs)["enable"] == 0


def test_a_frozen_runtime_loses_the_channel_when_the_supervisor_drops_the_enable_line(
    tmp_path, sysfs
):
    limits = EnvelopeLimits(
        window_s=100, max_on_ms_per_window=100_000, min_interval_ms=0, max_continuous_ms=60_000
    )
    envelope = SafetyEnvelope({"fan": limits}, virtual=False)
    hal, fake, events = make(tmp_path, sysfs, envelope=envelope)
    fan(hal, duration_ms=30_000)
    # What the client calls when the supervisor reports a drop it made on its own.
    hal._supervisor_dropped("fan_en", "heartbeat")
    assert envelope.live("fan") is None and hal.commanded_pwm("fan") is None
    assert files(sysfs)["enable"] == 0
    assert events.of_type("actuator_command")[-1] == {
        "pin": "fan",
        "operation": "off",
        "duration_ms": 0,
        "cause": "supervisor_heartbeat",
    }
    hal.close()


# --- state() and the controller's own read-back (§9.4, §9.12) ---------------------------------


def test_the_state_of_a_channel_with_no_declared_read_back_is_commanded(tmp_path, sysfs):
    hal, *_ = make(tmp_path, sysfs)
    fan(hal, frequency_hz=2_000, duty=0.25, duration_ms=5_000)
    state = hal.pin_state("fan", called_from="t")
    assert (state.source, state.duty, state.frequency_hz) == ("commanded", 0.25, 2_000.0)
    hal.close()


def test_a_declared_read_back_comes_from_the_controller_not_from_memory(
    tmp_path, sysfs, feedback_board
):
    hal, _, events = make(tmp_path, sysfs, board=_linux(feedback_board))
    fan(hal, frequency_hz=2_000, duty=0.25, duration_ms=5_000)
    channel = sysfs / "class" / "pwm" / "pwmchip0" / "pwm2"
    (channel / "duty_cycle").write_text(
        "100000\n"
    )  # the controller says 0.2 whatever was commanded
    state = hal.pin_state("fan")
    assert state.source == "measured"
    assert (state.duty, state.frequency_hz) == (0.2, 2_000.0)
    assert events.of_type("pin_state")[-1] == {
        "pin": "fan",
        "source": "measured",
        "duty": 0.2,
        "frequency_hz": 2_000.0,
    }
    hal.digital_out("fan", "off")
    assert hal.pin_state("fan").values == {"duty": 0.0, "frequency_hz": None}, "off reads as off"
    hal.close()


@pytest.mark.parametrize(
    ("damage", "why"),
    [
        (lambda c: (c / "duty_cycle").unlink(), "cannot be read back"),
        (lambda c: (c / "period").write_text("junk\n"), "cannot be read back"),
        (lambda c: (c / "duty_cycle").write_text("2000000\n"), "inconsistent PWM registers"),
        (lambda c: (c / "enable").write_text("7\n"), "inconsistent PWM registers"),
        (lambda c: (c / "duty_cycle").write_text("900000\n"), "outside what the board allows"),
        (lambda c: (c / "period").write_text("1000\n"), "inconsistent PWM registers"),
    ],
    ids=["missing", "garbage", "duty-over-period", "bad-enable", "over-max-duty", "wild-period"],
)
def test_a_read_back_that_is_not_believable_is_ne5001_never_the_commanded_value(
    tmp_path, sysfs, feedback_board, damage, why
):
    hal, _, events = make(tmp_path, sysfs, board=_linux(feedback_board))
    fan(hal, duty=0.25, duration_ms=5_000)
    damage(sysfs / "class" / "pwm" / "pwmchip0" / "pwm2")
    with pytest.raises(PerceptionUnavailableError, match=why) as raised:
        hal.pin_state("fan", called_from="t")
    assert raised.value.code == "NE5001"
    assert events.of_type("pin_state") == [{"pin": "fan", "reason": raised.value.why}]
    hal.close()


def _linux(board):
    """The `linux-rpi5` of the fixture boards dir: the same read-back declared on the linux board."""
    from neuroedge.hal.board import load_board_by_id

    text = Path(board.source).parent / "linux-rpi5.toml"
    path = text
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "[capabilities.digital_in]",
            '[capabilities.digital_out.feedback]\npins = ["fan"]\n\n[capabilities.digital_in]',
            1,
        ),
        encoding="utf-8",
    )
    return load_board_by_id("linux-rpi5")


# --- replay: no hardware at all ----------------------------------------------------------------


def test_replay_runs_a_pwm_command_in_the_model_and_never_opens_the_kernels_pwm(tmp_path):
    chip = tmp_path / "gpiochip0"
    chip.write_text("")
    fake = FakeGpiod({str(chip): LINES})
    events = EventLog(target="linux", board_id="linux-rpi5")
    hal = LinuxHAL(
        chip_glob=str(tmp_path / "gpiochip*"),
        gpiod=fake,
        events=events,
        authorize=lambda *_: None,
        sysfs_root=tmp_path / "no-such-sys",  # any access fails
        replay=True,
    )
    fan(hal, duration_ms=5_000)
    assert hal.commanded_pwm("fan") == (1000, 0.5)
    assert [name for name, _ in fake.history] == [], "no enable line is held, so none moved"
    with pytest.raises(PerceptionUnavailableError, match="never reads the machine"):
        hal._read_feedback("fan", None, "t")
    hal.digital_out("fan", "off")
    hal.close()
    assert not Path(tmp_path / "no-such-sys").exists()


def test_another_channel_owner_can_program_the_controller_in_its_own_units(tmp_path, sysfs):
    """`SysfsPwm` is not the fan's alone: a servo's 1.5 ms pulse at 50 Hz is `apply_ns`, `off`, `check`."""
    pwm = SysfsPwm(sysfs, {"gripper": CHANNEL}, "test")
    pwm.check("gripper")
    pwm.apply_ns("gripper", 20_000_000, 1_500_000)
    assert files(sysfs) == {"period": 20_000_000, "duty_cycle": 1_500_000, "enable": 1}
    pwm.off("gripper")
    assert files(sysfs) == {"period": 20_000_000, "duty_cycle": 0, "enable": 0}
