"""
NeuroEdge - Typed Action Contract Platform for Physical AI.
"""

__version__ = "0.1.0"

from .engine import ActionContractEngine, Gate, GateVerdict
from .hal import HardwareAbstractionLayer
from .testing import replay, scenario

__all__ = [
    "__version__",
    "ActionContractEngine",
    "Gate",
    "GateVerdict",
    "HardwareAbstractionLayer",
    "replay",
    "scenario",
]
