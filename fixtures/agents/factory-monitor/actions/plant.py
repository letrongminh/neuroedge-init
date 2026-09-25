"""
The factory-monitor sample's four physical actions. Only `c.do()` runs them, after their gate.

On `sim-default` and `linux-rpi5`, `gate_relay` drives the fan contactor and
`porch_light` the alarm beacon.
"""

from neuroedge import action
from neuroedge.hal import digital


@action(name="vent_on", requires="digital.out:gate_relay", gate="vent_on")
def vent_on() -> None:
    """Start the ventilation fan."""
    digital.out("gate_relay").on()


@action(name="vent_off", requires="digital.out:gate_relay", gate="vent_off")
def vent_off() -> None:
    """Stop the ventilation fan."""
    digital.out("gate_relay").off()


@action(name="alarm_on", requires="digital.out:porch_light", gate="alarm_on")
def alarm_on() -> None:
    """Switch the alarm beacon on."""
    digital.out("porch_light").on()


@action(name="alarm_off", requires="digital.out:porch_light", gate="alarm_off")
def alarm_off() -> None:
    """Silence the alarm beacon."""
    digital.out("porch_light").off()
