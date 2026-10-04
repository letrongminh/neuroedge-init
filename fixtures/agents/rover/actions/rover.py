"""Hai action của agent rover. Chỉ `c.do()` chạy chúng, sau gate của mỗi action."""

from neuroedge import action, motion


@action(name="drive", requires="motion:wheel_left", gate="drive")
def drive(speed: float = 0.3) -> None:
    """Drive the left wheel forward at `speed` for one lease; call again to keep going."""
    motion.motor("wheel_left", speed=speed)


@action(name="grip", requires="motion:gripper", gate="grip")
def grip(angle: float = 45.0) -> None:
    """Close the gripper to `angle` degrees; it holds there briefly, then lets go."""
    motion.servo("gripper", target=angle)
