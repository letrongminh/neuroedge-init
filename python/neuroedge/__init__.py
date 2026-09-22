"""
NeuroEdge — Typed Action Contract Platform for Physical AI.
"""

__version__ = "0.1.0"

from .engine import (
    ActionContractEngine,
    Gate,
    GateRegistry,
    GateVerdict,
    ResolvedGate,
    resolve_gate_file,
    resolve_gate_uri,
)
from .errors import (
    ActionContractViolation,
    BoardCapabilityError,
    GateInheritanceError,
    GateNotFoundError,
    GateSchemaError,
    NeuroEdgeError,
    TraceValidationError,
)
from .hal import BoardProfile, HardwareAbstractionLayer, load_board_by_id
from .testing import replay, scenario
from .trace import load_trace, validate_trace

__all__ = [
    "__version__",
    "ActionContractEngine",
    "ActionContractViolation",
    "BoardCapabilityError",
    "BoardProfile",
    "Gate",
    "GateInheritanceError",
    "GateNotFoundError",
    "GateRegistry",
    "GateSchemaError",
    "GateVerdict",
    "HardwareAbstractionLayer",
    "NeuroEdgeError",
    "ResolvedGate",
    "TraceValidationError",
    "load_board_by_id",
    "load_trace",
    "replay",
    "resolve_gate_file",
    "resolve_gate_uri",
    "scenario",
    "validate_trace",
]
