"""Hai action của agent gate-camera. Chỉ `c.do()` chạy chúng, sau gate của mỗi action."""

from neuroedge import action, digital


@action(name="stranger_light", requires="digital.out:porch_light", gate="stranger_light")
def stranger_light() -> None:
    """Turn the porch light on for a stranger the camera sees at the gate."""
    digital.out("porch_light").on()


@action(name="stranger_lock", requires="digital.out:gate_relay", gate="stranger_lock")
def stranger_lock() -> None:
    """Engage the gate lock for a stranger the camera sees at the gate."""
    digital.out("gate_relay").pulse(seconds=30)
