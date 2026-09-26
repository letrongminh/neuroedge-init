"""The fixture agent's actions (tests/test_firmware_build.py). Only `c.do()` runs them."""

from neuroedge import action
from neuroedge.hal import digital


@action(
    name="fixture_open_door",
    requires=["digital.out:door_lock", "digital.out:gate_relay"],
    gate="open_door",
)
def fixture_open_door() -> None:
    digital.out("door_lock").pulse(seconds=5)
    digital.out("gate_relay").pulse(seconds=5)


@action(name="fixture_buzz", requires="digital.out:gate_relay", gate="buzz")
def fixture_buzz(zone: str = "front", seconds: int = 2) -> None:
    digital.out("gate_relay").pulse(seconds=seconds)


@action(name="fixture_announce", requires="audio.out", gate="announce")
def fixture_announce() -> None:
    """Speech only: no pin."""
