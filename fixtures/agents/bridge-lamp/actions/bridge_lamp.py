"""Hai action của agent bridge-lamp. Chỉ `c.do()` chạy chúng, sau gate của mỗi action."""

from neuroedge import action, digital


@action(name="lamp_on", requires="digital.out:porch_light", gate="lamp_on")
def lamp_on() -> None:
    """Turn the lamp on."""
    digital.out("porch_light").on()


@action(name="lamp_off", requires="digital.out:porch_light", gate="lamp_off")
def lamp_off() -> None:
    """Turn the lamp off."""
    digital.out("porch_light").off()
