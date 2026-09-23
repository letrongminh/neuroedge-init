"""Sample physical action for the villa-concierge agent (proposal §4.4)."""

from neuroedge import action
from neuroedge.hal import digital


@action(name="unlock_door", requires="digital.out:door_lock", gate="unlock_door")
def unlock_door(guest_id: str = "", duration_s: int = 30) -> None:
    """Pulse the guest's door lock once the gate has allowed it."""
    digital.out("door_lock").pulse(seconds=duration_s)
