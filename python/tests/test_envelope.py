"""
TSK-N2-01, TSK-N2-02 — the per-pin safety envelope at run time (RFC-0007 §3d, §7, Q-62).

The numbers come from the board (`BoardProfile.envelope`); here they are set small and given
to a `SafetyEnvelope` directly, with a fake clock, so each rule is one assertion. The same
rules against real kernel lines are `tests_linux/test_gpio_envelope.py`; against the fake
gpiod, `test_hal_linux_envelope.py`.
"""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from neuroedge.actions.token import TokenLedger
from neuroedge.engine.trace_sink import EventLog
from neuroedge.errors import (
    ActionContractViolation,
    BoardCapabilityError,
    EnvelopeRefusedError,
    TokenReplayError,
)
from neuroedge.hal import HardwareAbstractionLayer, ensure_envelope
from neuroedge.hal.board import SIM_MIRRORS, load_board_by_id
from neuroedge.hal.envelope import (
    EnvelopeLimits,
    FileEnvelopeStore,
    SafetyEnvelope,
    default_state_dir,
)
from neuroedge.hal.sim import SimHAL

PIN = "door_lock"
LIMITS = EnvelopeLimits(
    window_s=100, max_on_ms_per_window=10_000, min_interval_ms=1_000, max_continuous_ms=4_000
)


class Clock:
    def __init__(self) -> None:
        self.now = 1_000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, ms: float) -> None:
        self.now += ms


def allow(signature, pin, called_from) -> None:
    """The authorizer of a test that is not about tokens."""


def make(clock: Clock | None = None, limits: EnvelopeLimits = LIMITS, **options):
    clock = clock or Clock()
    events = EventLog(clock)
    envelope = SafetyEnvelope({PIN: limits}, clock=clock, **options)
    hal = SimHAL(events=events, authorize=allow, envelope=envelope)
    return hal, envelope, events, clock


def refusal(hal: SimHAL, operation: str = "on", duration_ms: int = 0) -> EnvelopeRefusedError:
    with pytest.raises(EnvelopeRefusedError) as raised:
        hal.digital_out(PIN, operation, duration_ms, signature="x")
    return raised.value


# --- the hook: require_pin -> envelope -> authorize -> record ------------------------


def test_the_hook_runs_require_pin_then_the_envelope_then_authorize_then_record():
    order: list[str] = []
    clock = Clock()

    def authorize(signature, pin, called_from) -> None:
        order.append("authorize")
        assert hal.pin(PIN).never_pulsed(), "authorize runs before the command is recorded"

    hal = SimHAL(authorize=authorize, envelope=SafetyEnvelope({PIN: LIMITS}, clock=clock))
    real_reserve = hal.envelope.reserve

    def reserve(*args, **kwargs):
        order.append("envelope")
        return real_reserve(*args, **kwargs)

    hal.envelope.reserve = reserve
    hal.digital_out(PIN, "pulse", 1_000, signature="x")
    assert order == ["envelope", "authorize"]
    assert hal.pin(PIN).pulsed_once(1_000)

    with pytest.raises(BoardCapabilityError, match="no pin named 'nope'"):
        hal.digital_out("nope", "on", signature="x")
    assert order == ["envelope", "authorize"], (
        "a misspelt pin reaches neither the envelope nor authorize"
    )


def test_a_refused_command_never_reaches_authorize_nor_the_pin():
    calls: list[str] = []
    hal, _, events, clock = make()
    hal.authorize = lambda *_: calls.append("authorize")
    hal.digital_out(PIN, "pulse", 1_000, signature="x")
    clock.advance(10)
    error = refusal(hal, "pulse", 1_000)
    assert error.code == "NE1003" and isinstance(error, ActionContractViolation)
    assert calls == ["authorize"], "only the first command asked authorize"
    assert hal.pin(PIN).pulses == [1_000], "the refused pulse is not a command of the pin"
    assert len(events.of_type("actuator_command")) == 1


def _token(ledger: TokenLedger):
    return ledger.issue(
        gate="g", gate_digest="d", action="a", pins=frozenset({PIN}), session_id="s", p95_ms=1e9
    )


def test_a_refused_command_does_not_consume_the_verdict_token():
    hal, envelope, _, clock = make()
    ledger = TokenLedger(clock)
    hal.authorize = ledger.authorize
    first, fresh = _token(ledger), _token(ledger)
    hal.digital_out(PIN, "pulse", 1_000, signature=first)
    clock.advance(10)  # the pulse is still going
    with pytest.raises(EnvelopeRefusedError) as raised:
        hal.digital_out(PIN, "pulse", 1_000, signature=fresh)
    assert raised.value.reason == "already_on"
    assert ledger._consumed[fresh.nonce] == set(), "the envelope refused first: the token is whole"
    clock.advance(10_000)  # the pulse is long over: the same token now works
    hal.digital_out(PIN, "pulse", 1_000, signature=fresh)
    clock.advance(10_000)
    with pytest.raises(TokenReplayError):  # a replay the envelope lets through, authorize stops
        hal.digital_out(PIN, "pulse", 1_000, signature=fresh)
    assert envelope.live(PIN) is None, "and its reservation went back"


def test_a_command_authorize_refuses_gives_back_every_millisecond_it_reserved():
    hal, envelope, _, clock = make()
    hal.authorize = lambda *_: (_ for _ in ()).throw(ActionContractViolation("w", "y", "h"))
    for _ in range(5):  # five refused 4 s commands would be 20 s, over the 10 s budget
        with pytest.raises(ActionContractViolation):
            hal.digital_out(PIN, "on", signature="x")
        assert envelope.live(PIN) is None
        clock.advance(2_000)
    hal.authorize = allow
    hal.digital_out(PIN, "on", signature="x")  # the whole budget and the interval are intact
    assert hal.pin(PIN).commands == [("on", 0)], "only the command that passed is recorded"


# --- toward the safe state: never blocked ------------------------------------------


def test_off_needs_no_envelope_no_proof_and_no_waiting():
    hal, envelope, events, clock = make()
    hal.digital_out(PIN, "on", signature="x")
    hal.authorize = lambda *_: pytest.fail("off asked authorize for a token")
    hal.digital_out(PIN, "off", signature="")  # no proof at all, 0 ms after the on
    assert envelope.live(PIN) is None
    assert [e["operation"] for e in events.of_type("actuator_command")] == ["on", "off"]
    hal.digital_out(PIN, "off", signature="")  # an off with nothing on is just as welcome
    assert events.of_type("envelope_refused") == []


def test_min_interval_refuses_only_the_next_on_and_runs_from_the_end_of_the_previous_on():
    hal, _, events, clock = make()
    hal.digital_out(PIN, "on", signature="x")
    clock.advance(500)
    hal.digital_out(PIN, "off", signature="x")  # 500 ms after the on: never refused
    clock.advance(400)  # 400 ms after the end
    error = refusal(hal)
    assert error.reason == "min_interval_ms"
    assert error.event == {
        "pin": PIN,
        "operation": "on",
        "reason": "min_interval_ms",
        "limit_ms": 1_000,
        "wait_ms": 600,
    }
    hal.digital_out(PIN, "off", signature="x")  # off during the wait: still never refused
    clock.advance(600)
    hal.digital_out(PIN, "on", signature="x")
    assert len(events.of_type("envelope_refused")) == 1


def test_an_off_on_a_pin_with_an_unreadable_record_still_works(tmp_path):
    hal, _, events, _ = make(store=FileEnvelopeStore(tmp_path / "state"))
    assert refusal(hal).reason == "window_unreadable"
    hal.digital_out(PIN, "off", signature="")
    assert events.of_type("actuator_command") == [
        {"pin": PIN, "operation": "off", "duration_ms": 0}
    ]


# --- the mandatory auto-off and the reservation ------------------------------------


def test_an_on_without_a_duration_turns_off_at_max_continuous_ms():
    hal, envelope, events, clock = make()
    hal.digital_out(PIN, "on", signature="x")
    reservation = envelope.live(PIN)
    assert reservation.reserved_ms == 4_000 and reservation.deadline_ms == clock.now + 4_000
    clock.advance(3_999)
    assert envelope.live(PIN) is reservation, "still on one millisecond before the deadline"
    clock.advance(1)
    hal.run_due()  # the clock ticked: the pin goes off by itself
    assert envelope.live(PIN) is None
    assert events.of_type("actuator_command")[-1] == {
        "pin": PIN,
        "operation": "off",
        "duration_ms": 0,
        "cause": "max_continuous_ms",
    }
    assert events.of_type("envelope_refused") == []


@pytest.mark.parametrize(
    ("operation", "duration", "reserved"),
    [("on", 1_500, 1_500), ("on", 9_000, 4_000), ("pulse", 2_000, 2_000), ("pulse", 90_000, 4_000)],
)
def test_the_reservation_is_min_of_the_duration_and_max_continuous_ms(
    operation, duration, reserved
):
    hal, envelope, events, _ = make()
    hal.digital_out(PIN, operation, duration, signature="x")
    assert envelope.live(PIN).reserved_ms == reserved
    assert events.of_type("actuator_command") == [
        {"pin": PIN, "operation": operation, "duration_ms": duration}
    ]


def test_a_command_cut_short_says_why_when_its_pin_goes_off_and_one_that_ended_itself_does_not():
    hal, _, events, clock = make()
    hal.digital_out(PIN, "pulse", 2_000, signature="x")  # ends by its own duration
    clock.advance(3_000)
    hal.run_due()
    assert [e["operation"] for e in events.of_type("actuator_command")] == ["pulse"]
    hal.digital_out(PIN, "pulse", 90_000, signature="x")  # cut at 4 s by the envelope
    clock.advance(4_000)
    hal.run_due()
    assert events.of_type("actuator_command")[-1]["cause"] == "max_continuous_ms"


def test_the_budget_holds_exactly_the_reserved_time_and_an_early_off_refunds_the_rest():
    limits = EnvelopeLimits(
        window_s=100, max_on_ms_per_window=5_000, min_interval_ms=0, max_continuous_ms=4_000
    )
    hal, envelope, _, clock = make(limits=limits)
    hal.digital_out(PIN, "on", signature="x")  # 4 s reserved of 5 s
    clock.advance(1_000)
    hal.digital_out(PIN, "off", signature="x")  # used 1 s: 3 s go back, 4 s left
    hal.digital_out(PIN, "on", signature="x")  # 4 s again: the window now holds 5 s
    clock.advance(4_000)
    hal.run_due()
    error = refusal(hal, "on")  # nothing is left
    assert error.reason == "window_budget"
    assert error.event["limit_ms"] == 5_000 and error.event["used_ms"] == 5_000
    assert error.event["requested_ms"] == 4_000
    assert envelope.live(PIN) is None


def test_the_window_slides():
    limits = EnvelopeLimits(
        window_s=10, max_on_ms_per_window=4_000, min_interval_ms=0, max_continuous_ms=4_000
    )
    hal, _, _, clock = make(limits=limits)
    hal.digital_out(PIN, "on", signature="x")
    clock.advance(4_000)
    hal.run_due()
    clock.advance(1_000)
    assert refusal(hal).reason == "window_budget"
    clock.advance(8_999)  # 1 ms of the 4 s on is still inside the 10 s window
    assert refusal(hal).event["used_ms"] == 1
    clock.advance(1)  # now the whole of it has left
    hal.digital_out(PIN, "on", signature="x")


def test_a_pin_that_is_on_refuses_another_on_or_pulse_instead_of_restarting_its_limit():
    hal, _, events, clock = make()
    hal.digital_out(PIN, "on", signature="x")
    clock.advance(3_000)
    for operation in ("on", "pulse"):
        error = refusal(hal, operation, 1_000)
        assert error.reason == "already_on" and error.event["remaining_ms"] == 1_000
    assert len(events.of_type("envelope_refused")) == 2


def test_a_scheduled_command_reserves_its_on_time_when_it_is_asked_and_gives_it_back_when_cancelled():
    limits = EnvelopeLimits(
        window_s=100, max_on_ms_per_window=4_000, min_interval_ms=0, max_continuous_ms=4_000
    )
    hal, envelope, _, clock = make(limits=limits)
    hal.enable_scheduling(clock)
    pending = hal.digital_out(PIN, "on", signature="x", delay_ms=5_000)
    assert envelope.live(PIN).start_ms == clock.now + 5_000
    assert refusal(hal).reason == "already_on", "a waiting command holds the pin"
    pending.cancel()
    assert envelope.live(PIN) is None
    hal.digital_out(PIN, "on", signature="x")  # the whole 4 s budget is back


def test_a_pin_without_an_envelope_behaves_as_it_always_did():
    """RFC-0007 §7.1 (1): no envelope, no change — same order of errors, a typo spends no token."""
    ledger_calls: list[str] = []
    hal = SimHAL(authorize=lambda *_: ledger_calls.append("authorize"))
    assert hal.envelope is None
    for _ in range(3):
        hal.digital_out(PIN, "pulse", 30_000, signature="x")
    hal.digital_out(PIN, "on", signature="x")
    assert ledger_calls == ["authorize"] * 4
    with pytest.raises(BoardCapabilityError):
        hal.digital_out("nope", "on", signature="x")
    assert ledger_calls == ["authorize"] * 4
    base = HardwareAbstractionLayer(board=load_board_by_id("sim-default"), authorize=allow)
    base.digital_out(PIN, "on", signature="x")  # the base class has none either
    base.digital_out(PIN, "on", signature="x")


# --- two commands at once, both orders -----------------------------------------------


def _race(breakpoint_in: str, first: str, second: str) -> tuple[list[str], int]:
    """
    Two threads command the same pin; `first` is held at a breakpoint while `second` runs.
    `breakpoint_in` is where: ``"envelope"`` — inside the check-and-reserve, with the pin's
    lock held (the clock is read there) — or ``"authorize"`` — after the reservation was made.
    """
    limits = EnvelopeLimits(
        window_s=100, max_on_ms_per_window=4_000, min_interval_ms=0, max_continuous_ms=4_000
    )
    reached, release = threading.Event(), threading.Event()
    state = {"armed": False}
    clock = Clock()

    def hold() -> None:
        if state["armed"] and threading.current_thread().name == first:
            state["armed"] = False
            reached.set()
            assert release.wait(5), "the test never released the held command"

    def timed() -> float:
        if breakpoint_in == "envelope":
            hold()
        return clock()

    def authorize(signature, pin, called_from) -> None:
        if breakpoint_in == "authorize":
            hold()

    events = EventLog(clock)
    envelope = SafetyEnvelope({PIN: limits}, clock=timed)
    hal = SimHAL(events=events, authorize=authorize, envelope=envelope)
    outcome: dict[str, str] = {}

    def command(label: str) -> None:
        try:
            hal.digital_out(PIN, "on", signature=label)
            outcome[label] = "passed"
        except EnvelopeRefusedError as error:
            outcome[label] = error.reason

    state["armed"] = True
    held = threading.Thread(target=command, args=(first,), name=first)
    held.start()
    assert reached.wait(5)
    other = threading.Thread(target=command, args=(second,), name=second)
    other.start()
    if breakpoint_in == "authorize":
        other.join(5)  # the reservation is made: the second command is refused at once
        assert not other.is_alive()
    release.set()
    held.join(5)
    other.join(5)
    assert not held.is_alive() and not other.is_alive()
    refused = [label for label, result in outcome.items() if result != "passed"]
    return refused, len(events.of_type("envelope_refused"))


@pytest.mark.parametrize("breakpoint_in", ["envelope", "authorize"])
@pytest.mark.parametrize(("first", "second"), [("A", "B"), ("B", "A")])
def test_two_concurrent_commands_on_one_pin_give_exactly_one_envelope_refused(
    breakpoint_in, first, second
):
    """RFC-0007 §7, TSK-N2-02, exit criterion N2.1: the budget that is left fits one of them."""
    refused, recorded = _race(breakpoint_in, first, second)
    assert recorded == 1
    assert len(refused) == 1
    # whichever got to the lock first won; the other waited for it or was refused at once
    assert refused == [second]


# --- the restart rule ----------------------------------------------------------------


def boot(tmp_path: Path, clock: Clock, **options):
    store = FileEnvelopeStore(tmp_path / "envelope")
    envelope = SafetyEnvelope({PIN: LIMITS}, clock=clock, store=store, **options)
    hal = SimHAL(events=EventLog(clock), authorize=allow, envelope=envelope)
    return hal, envelope, store


def test_the_on_time_is_written_before_the_pin_is_turned_on(tmp_path):
    clock = Clock()
    hal, envelope, store = boot(tmp_path, clock, init_store=True)
    seen: list[list[float]] = []
    real = hal.authorize

    def authorize(signature, pin, called_from) -> None:
        seen.append(store.load(PIN))  # the pin has not moved yet: authorize is the last gate
        real(signature, pin, called_from)

    hal.authorize = authorize
    hal.digital_out(PIN, "on", signature="x")
    assert seen == [[4_000.0]], "the 4 s reservation is on disk before the command is accepted"
    clock.advance(1_000)
    hal.digital_out(PIN, "off", signature="x")
    assert store.load(PIN) == [1_000.0], "an early off lowers the record to what was used"


def test_a_command_authorize_refused_leaves_no_trace_on_disk(tmp_path):
    hal, _, store = boot(tmp_path, Clock(), init_store=True)
    hal.authorize = lambda *_: (_ for _ in ()).throw(ActionContractViolation("w", "y", "h"))
    with pytest.raises(ActionContractViolation):
        hal.digital_out(PIN, "on", signature="x")
    assert store.load(PIN) == []


def test_after_a_restart_what_was_recorded_counts_against_the_window_and_the_pin_waits(tmp_path):
    clock = Clock()
    hal, _, _ = boot(tmp_path, clock, init_store=True)
    for _ in range(2):  # 8 s of the 10 s budget, recorded
        hal.digital_out(PIN, "on", signature="x")
        clock.advance(4_000)
        hal.run_due()
        clock.advance(1_000)
    # the process is gone; a new one starts a day later on a clock that means nothing
    clock2 = Clock()
    clock2.now = 5.0
    hal2, envelope2, _ = boot(tmp_path, clock2)
    error = refusal(hal2)
    assert error.reason == "min_interval_ms", "every pin waits min_interval_ms after a start"
    clock2.advance(1_000)
    error = refusal(hal2)  # 4 s asked, 8 s recorded, 10 s allowed
    assert error.reason == "window_budget" and error.event["used_ms"] == 8_000
    hal2.digital_out(PIN, "pulse", 2_000, signature="x")  # exactly 2 s fit
    clock2.advance(100_000)  # window_s after the start: the recorded on-time is gone
    hal2.run_due()
    hal2.digital_out(PIN, "on", signature="x")


def test_an_off_straight_after_a_restart_does_not_wait_for_min_interval(tmp_path):
    clock = Clock()
    hal, _, _ = boot(tmp_path, clock, init_store=True)
    hal.digital_out(PIN, "on", signature="x")
    restarted, _, _ = boot(tmp_path, Clock())
    assert refusal(restarted).reason == "min_interval_ms", "an on waits"
    restarted.digital_out(PIN, "off", signature="")  # the same instant: an off never does
    assert restarted.events.of_type("actuator_command") == [
        {"pin": PIN, "operation": "off", "duration_ms": 0}
    ]


@pytest.mark.parametrize(
    "damage",
    [
        "",
        "{",
        "[]",
        '{"version": 2}',
        '{"version": 1, "name": "x", "on_ms": []}',
        '{"version": 1, "name": "door_lock", "on_ms": [-1]}',
        '{"version": 1, "name": "door_lock", "on_ms": ["a"]}',
        '{"version": 1, "name": "door_lock", "on_ms": [true]}',
    ],
)
def test_a_corrupt_record_makes_the_pin_refuse_every_on(tmp_path, damage):
    clock = Clock()
    boot(tmp_path, clock, init_store=True)
    (tmp_path / "envelope" / f"{PIN}.json").write_text(damage, encoding="utf-8")
    hal, _, _ = boot(tmp_path, clock)
    error = refusal(hal)
    assert error.reason == "window_unreadable" and "window" in error.why
    assert hal.pin(PIN).never_pulsed()


def test_a_missing_record_is_refused_unless_this_is_declared_a_new_rig(tmp_path):
    clock = Clock()
    hal, _, _ = boot(tmp_path, clock)
    error = refusal(hal)
    assert error.reason == "window_unreadable" and "does not exist" in error.why
    assert "ENVELOPE_INIT" in error.how
    hal, _, store = boot(tmp_path, clock, init_store=True)
    hal.digital_out(PIN, "on", signature="x")  # a new rig starts empty, and needs no wait
    assert store.load(PIN) == [4_000.0]
    # init never overwrites: a second boot with the flag keeps what is recorded
    clock.advance(10_000)
    hal2, _, _ = boot(tmp_path, clock, init_store=True)
    assert refusal(hal2).reason == "min_interval_ms"


def test_a_record_that_cannot_be_written_refuses_the_command_and_holds_nothing(tmp_path):
    hal, envelope, store = boot(tmp_path, Clock(), init_store=True)

    def broken(name, on_ms):
        raise OSError(28, "No space left on device")

    store.save = broken
    error = refusal(hal)
    assert error.reason == "window_unreadable" and "recorded before" in error.why
    assert envelope.live(PIN) is None and hal.pin(PIN).never_pulsed()
    hal.digital_out(PIN, "off", signature="")  # and off still goes through


def test_the_state_directory_is_per_board_and_overridable(tmp_path, monkeypatch):
    monkeypatch.delenv("NEUROEDGE_LINUX_ENVELOPE_STATE", raising=False)
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    assert default_state_dir("linux-rpi5") == tmp_path / "neuroedge" / "envelope" / "linux-rpi5"
    monkeypatch.setenv("NEUROEDGE_LINUX_ENVELOPE_STATE", str(tmp_path / "x"))
    assert default_state_dir("linux-rpi5") == tmp_path / "x"


# --- sim is not richer than the board it mirrors (invariant #7) -------------------------


def test_a_sim_board_has_exactly_the_envelope_numbers_of_the_board_it_mirrors():
    for sim_id, linux_id in SIM_MIRRORS.items():
        mirrored = SafetyEnvelope.for_board(load_board_by_id(linux_id))
        simulated = SafetyEnvelope.for_board(load_board_by_id(sim_id))
        assert simulated.names == mirrored.names
        for name in mirrored.names:
            assert simulated.limits(name) == mirrored.limits(name), name


def test_ensure_envelope_gives_a_conversation_hal_the_envelope_of_its_board():
    hal = SimHAL()
    clock = Clock()
    ensure_envelope(hal, clock)
    assert hal.envelope is not None and hal.envelope.names == (
        "door_lock",
        "porch_light",
        "gate_relay",
    )
    own = hal.envelope
    ensure_envelope(hal, clock)
    assert hal.envelope is own, "an envelope that is installed is never replaced"
