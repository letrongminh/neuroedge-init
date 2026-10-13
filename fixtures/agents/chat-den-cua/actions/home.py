"""Ba thiết bị của demo chat-den-cua. Chỉ `c.do()` chạy chúng, sau gate của mỗi action."""

from neuroedge import action, digital


@action(name="living_light_on", requires="digital.out:porch_light", gate="light")
def living_light_on() -> None:
    """Turn the living-room light on."""
    digital.out("porch_light").on()


@action(name="living_light_off", requires="digital.out:porch_light", gate="light")
def living_light_off() -> None:
    """Turn the living-room light off."""
    digital.out("porch_light").off()


@action(name="front_door_unlock", requires="digital.out:door_lock", gate="door")
def front_door_unlock(duration_s: int = 30) -> None:
    """Unlock the front door for `duration_s` seconds (1–30), then it locks again by itself."""
    digital.out("door_lock").pulse(seconds=duration_s)
