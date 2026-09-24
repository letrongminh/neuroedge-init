"""Ba action của agent driveway. Chỉ `c.do()` chạy chúng, sau gate của mỗi action."""

from neuroedge import action
from neuroedge.hal import digital


@action(name="buzz_in", requires="digital.out:door_lock", gate="buzz_in")
def buzz_in(zone: str, seconds: int = 5, note: str = "") -> None:
    """Buzz a visitor in through the front or side door for a few seconds."""
    digital.out("door_lock").pulse(seconds=seconds)


@action(name="open_gate", requires="digital.out:gate_relay", gate="open_gate")
def open_gate() -> None:
    """Open the driveway gate for an expected visitor."""
    digital.out("gate_relay").pulse(seconds=20)


@action(name="porch_light_on", requires="digital.out:porch_light", gate="porch_light_on")
def porch_light_on() -> None:
    """Turn the porch light on."""
    digital.out("porch_light").on()
