"""
Q-83 Profile B — what an @action does to its pins, recorded at build time for the chip
(`engine/chip_actions.py`, `ne_agent_pin_op`). A body the chip cannot replay exactly is
`unsupported`, so the chip refuses to drive it instead of guessing.
"""

from __future__ import annotations

from neuroedge import digital
from neuroedge.actions.spec import ActionSpec, Requirement
from neuroedge.engine.chip_actions import OFF, ON, PULSE, UNSUPPORTED, PinOp, pin_operations


def spec(fn, *pins: str) -> ActionSpec:
    requires = tuple(Requirement.parse(f"digital.out:{pin}", "test") for pin in pins)
    return ActionSpec(fn.__name__, requires, "g", fn, "test.py", 1)


def test_on_off_and_a_constant_pulse():
    def light_on():
        digital.out("lamp").on()

    def light_off():
        digital.out("lamp").off()

    def chime():
        digital.out("bell").pulse(ms=250)

    assert pin_operations(spec(light_on, "lamp")) == (PinOp("lamp", ON, 0),)
    assert pin_operations(spec(light_off, "lamp")) == (PinOp("lamp", OFF, 0),)
    assert pin_operations(spec(chime, "bell")) == (PinOp("bell", PULSE, 250),)


def test_a_pulse_that_follows_one_argument():
    def unlock(duration_s: int = 30, note: str = "x"):
        digital.out("door").pulse(seconds=duration_s)

    def drip(ms: int = 100):
        digital.out("valve").pulse(ms=ms)

    assert pin_operations(spec(unlock, "door")) == (PinOp("door", PULSE, 1000, "duration_s"),)
    assert pin_operations(spec(drip, "valve")) == (PinOp("valve", PULSE, 1, "ms"),)


def test_what_the_chip_cannot_replay_exactly_is_unsupported():
    def offset(duration_s: int = 5):
        digital.out("door").pulse(seconds=duration_s + 1)  # not in proportion

    def two(a: int = 1, b: int = 1):
        digital.out("door").pulse(ms=a * b)  # follows two arguments

    def fan(duty: float = 0.5):
        digital.out("fan").pwm(frequency_hz=1000, duty=duty, ms=100)

    def later():
        digital.out("lamp").on(after_ms=100)  # a scheduled command

    def reads():
        if digital.input("button").level():
            digital.out("lamp").on()

    for fn, pin in (
        (offset, "door"),
        (two, "door"),
        (fan, "fan"),
        (later, "lamp"),
        (reads, "lamp"),
    ):
        assert pin_operations(spec(fn, pin)) == (PinOp(pin, UNSUPPORTED, 0),), fn.__name__


def test_the_demo_agent_as_the_chip_runs_it(root):
    from neuroedge.actions.spec import REGISTRY
    from neuroedge.sim import SimSession

    SimSession.load(root / "fixtures" / "agents" / "chat-den-cua" / "agent.toml")
    assert pin_operations(REGISTRY["living_light_off"]) == (PinOp("porch_light", OFF, 0),)
    assert pin_operations(REGISTRY["front_door_unlock"]) == (
        PinOp("door_lock", PULSE, 1000, "duration_s"),
    )
