"""The contract bench: one action per kind of block. Only `c.do()` runs them, after each gate."""

from neuroedge import action, digital


@action(name="heater_on", requires="digital.out:gate_relay", gate="heat")
def heater_on(level: int = 1, temperature: float = 0.0) -> None:
    """Run the heater at `level`."""
    digital.out("gate_relay").on()


@action(name="guest_unlock", requires="digital.out:door_lock", gate="guest")
def guest_unlock() -> None:
    """Unlock the door for a guest."""
    digital.out("door_lock").on()


@action(name="siren_on", requires="digital.out:gate_relay", gate="siren")
def siren_on() -> None:
    """Sound the siren."""
    digital.out("gate_relay").on()


@action(name="porch_lamp_on", requires="digital.out:porch_light", gate="lamp")
def porch_lamp_on() -> None:
    """Turn the porch lamp on."""
    digital.out("porch_light").on()


@action(name="arm_zone", requires="digital.out:porch_light", gate="lamp")
def arm_zone(code: str, zone: int, force: bool = False) -> None:
    """Arm a zone."""
    digital.out("porch_light").on()
