"""
The greenhouse sample's physical actions. Only `c.do()` runs them, after their gate.

Four relays (`exhaust_fan`, `heater`, `mist_pump`, `grow_light`) and one servo (`roof_vent`) of
the virtual board `sim-virtual`.
"""

from neuroedge import action, digital, motion


@action(name="gh_heater_on", requires="digital.out:heater", gate="gh_heater_on")
def gh_heater_on() -> None:
    """Turn the heater on (refused when the air is hot or unread)."""
    digital.out("heater").on()


@action(name="gh_heater_off", requires="digital.out:heater", gate="gh_heater_off")
def gh_heater_off() -> None:
    """Turn the heater off."""
    digital.out("heater").off()


@action(name="gh_fan_on", requires="digital.out:exhaust_fan", gate="gh_fan_on")
def gh_fan_on() -> None:
    """Turn the exhaust fan on."""
    digital.out("exhaust_fan").on()


@action(name="gh_fan_off", requires="digital.out:exhaust_fan", gate="gh_fan_off")
def gh_fan_off() -> None:
    """Turn the exhaust fan off (refused while very hot or unread)."""
    digital.out("exhaust_fan").off()


@action(name="gh_mist_on", requires="digital.out:mist_pump", gate="gh_mist_on")
def gh_mist_on() -> None:
    """Turn the misting pump on (refused when the air is already humid or unread)."""
    digital.out("mist_pump").on()


@action(name="gh_mist_off", requires="digital.out:mist_pump", gate="gh_mist_off")
def gh_mist_off() -> None:
    """Turn the misting pump off."""
    digital.out("mist_pump").off()


@action(name="gh_vent_open", requires="motion:roof_vent", gate="gh_vent_open")
def gh_vent_open() -> None:
    """Open the roof vent fully (90 degrees)."""
    motion.servo("roof_vent", target=90.0)


@action(name="gh_vent_close", requires="motion:roof_vent", gate="gh_vent_close")
def gh_vent_close() -> None:
    """Close the roof vent (0 degrees); refused while very hot or unread."""
    motion.servo("roof_vent", target=0.0)


@action(name="gh_light_on", requires="digital.out:grow_light", gate="gh_light")
def gh_light_on() -> None:
    """Turn the grow light on."""
    digital.out("grow_light").on()


@action(name="gh_light_off", requires="digital.out:grow_light", gate="gh_light")
def gh_light_off() -> None:
    """Turn the grow light off."""
    digital.out("grow_light").off()
