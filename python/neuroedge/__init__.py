"""
NeuroEdge — Typed Action Contract Platform for Physical AI.
"""

__version__ = "0.1.0"

from .actions import Conversation, action
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
from .models import SystemOne, SystemTwo
from .testing import replay, scenario
from .trace import load_trace, validate_trace

__all__ = [
    "__version__",
    "ActionContractEngine",
    "ActionContractViolation",
    "BoardCapabilityError",
    "BoardProfile",
    "Conversation",
    "Gate",
    "GateInheritanceError",
    "GateNotFoundError",
    "GateRegistry",
    "GateSchemaError",
    "GateVerdict",
    "HardwareAbstractionLayer",
    "NeuroEdgeError",
    "ResolvedGate",
    "SystemOne",
    "SystemTwo",
    "TraceValidationError",
    "action",
    "load_board_by_id",
    "load_trace",
    "replay",
    "resolve_gate_file",
    "resolve_gate_uri",
    "scenario",
    "validate_trace",
]
