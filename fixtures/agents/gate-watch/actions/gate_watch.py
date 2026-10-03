"""Hai action của agent gate-watch. Chỉ `c.do()` chạy chúng, sau gate của mỗi action."""

from neuroedge import action, digital


@action(name="watch_open_gate", requires="digital.out:gate_relay", gate="watch_open_gate")
def watch_open_gate() -> None:
    """Open the gate for a person the camera sees standing at it."""
    digital.out("gate_relay").pulse(seconds=20)


@action(name="watch_lights_off", requires="digital.out:porch_light", gate="watch_lights_off")
def watch_lights_off() -> None:
    """Turn the porch light off once the camera sees nobody at the gate."""
    digital.out("porch_light").off()
