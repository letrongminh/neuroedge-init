"""
The aquarium sample's five physical actions. Only `c.do()` runs them, after their gate.

`gate_relay` drives the heater, `door_lock` the air pump and `porch_light` the tank light.
"""

from neuroedge import action, digital


@action(name="tank_heater_on", requires="digital.out:gate_relay", gate="heater_on")
def tank_heater_on() -> None:
    """Turn the tank heater on (refused while the water is already warm)."""
    digital.out("gate_relay").on()


@action(name="tank_heater_off", requires="digital.out:gate_relay", gate="heater_off")
def tank_heater_off() -> None:
    """Turn the tank heater off."""
    digital.out("gate_relay").off()


@action(name="tank_aerator_on", requires="digital.out:door_lock", gate="aerator_on")
def tank_aerator_on() -> None:
    """Turn the air pump on."""
    digital.out("door_lock").on()


@action(name="tank_aerator_off", requires="digital.out:door_lock", gate="aerator_off")
def tank_aerator_off() -> None:
    """Turn the air pump off (asks the owner; refused while the water is warm)."""
    digital.out("door_lock").off()


@action(name="tank_light_on", requires="digital.out:porch_light", gate="light")
def tank_light_on() -> None:
    """Turn the tank light on."""
    digital.out("porch_light").on()


@action(name="tank_light_off", requires="digital.out:porch_light", gate="light")
def tank_light_off() -> None:
    """Turn the tank light off."""
    digital.out("porch_light").off()
