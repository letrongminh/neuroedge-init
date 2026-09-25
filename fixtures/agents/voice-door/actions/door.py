"""Các action của agent voice-door. Chỉ `c.do()` chạy chúng, sau gate của mỗi action."""

from neuroedge import action
from neuroedge.hal import digital


@action(name="open_door", requires="digital.out:door_lock", gate="unlock_door")
def open_door() -> None:
    """Open the door lock for 30 seconds, now."""
    digital.out("door_lock").pulse(seconds=30)


@action(name="open_door_later", requires="digital.out:door_lock", gate="unlock_door")
def open_door_later() -> None:
    """Open the door lock for 30 seconds, two seconds from now (a scheduled command)."""
    digital.out("door_lock").pulse(seconds=30, after_ms=2000)


@action(name="lights_out", requires="digital.out:porch_light", gate="light_off")
def lights_out() -> None:
    """Turn the porch light off."""
    digital.out("porch_light").off()
