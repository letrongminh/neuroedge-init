"""Hai action của agent blinds. Chỉ `c.do()` chạy chúng, sau gate của mỗi action."""

from neuroedge import action, motion


@action(name="blinds_open", requires="motion:gripper", gate="blinds_open")
def blinds_open() -> None:
    """Tilt the blinds fully open (90 degrees); the servo holds there briefly, then lets go."""
    motion.servo("gripper", target=90.0)


@action(name="blinds_close", requires="motion:gripper", gate="blinds_close")
def blinds_close() -> None:
    """Tilt the blinds shut (0 degrees); the servo holds there briefly, then lets go."""
    motion.servo("gripper", target=0.0)
