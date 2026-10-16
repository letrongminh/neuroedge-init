"""
The full fish tank's ten physical actions on the virtual board `sim-virtual`. Only `c.do()` runs
them, after their gate. Every name starts with `reef_`: action names are unique across all fixtures
(NE1001).
"""

from neuroedge import action, digital


@action(name="reef_heater_on", requires="digital.out:heater", gate="reef_heater_on")
def reef_heater_on() -> None:
    """Turn the heater on (refused while the water is warm or unmeasured)."""
    digital.out("heater").on()


@action(name="reef_heater_off", requires="digital.out:heater", gate="reef_heater_off")
def reef_heater_off() -> None:
    """Turn the heater off."""
    digital.out("heater").off()


@action(name="reef_air_pump_on", requires="digital.out:air_pump", gate="reef_air_pump_on")
def reef_air_pump_on() -> None:
    """Turn the air pump on."""
    digital.out("air_pump").on()


@action(name="reef_air_pump_off", requires="digital.out:air_pump", gate="reef_air_pump_off")
def reef_air_pump_off() -> None:
    """Turn the air pump off (asks the owner; refused on low oxygen or warm water)."""
    digital.out("air_pump").off()


@action(name="reef_filter_on", requires="digital.out:filter_pump", gate="reef_filter_on")
def reef_filter_on() -> None:
    """Turn the filter pump on (refused when the water level is low)."""
    digital.out("filter_pump").on()


@action(name="reef_filter_off", requires="digital.out:filter_pump", gate="reef_filter_off")
def reef_filter_off() -> None:
    """Turn the filter pump off (asks the owner)."""
    digital.out("filter_pump").off()


@action(name="reef_co2_on", requires="digital.out:co2_valve", gate="reef_co2_on")
def reef_co2_on() -> None:
    """Open the CO2 valve (refused on low pH or low oxygen)."""
    digital.out("co2_valve").on()


@action(name="reef_co2_off", requires="digital.out:co2_valve", gate="reef_co2_off")
def reef_co2_off() -> None:
    """Close the CO2 valve."""
    digital.out("co2_valve").off()


@action(name="reef_light_on", requires="digital.out:tank_light", gate="reef_light")
def reef_light_on() -> None:
    """Turn the tank light on."""
    digital.out("tank_light").on()


@action(name="reef_light_off", requires="digital.out:tank_light", gate="reef_light")
def reef_light_off() -> None:
    """Turn the tank light off."""
    digital.out("tank_light").off()
