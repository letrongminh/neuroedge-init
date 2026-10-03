"""
`vision.in` on `sim`: the virtual camera and its path to the gate (TSK-V1b-02).

* `camera.py` — `VirtualCamera`, the recordings it plays, and `[sim.vision]` of `agent.toml`
* `feed.py` — `VisionFeed`: camera frames in, gate facts out, fail-closed
"""

from .camera import (
    ImageSequence,
    SimVision,
    SyntheticSequence,
    VirtualCamera,
    parse_sim_vision,
)
from .feed import VisionFeed

__all__ = [
    "ImageSequence",
    "SimVision",
    "SyntheticSequence",
    "VirtualCamera",
    "VisionFeed",
    "parse_sim_vision",
]
