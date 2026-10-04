"""
NeuroEdge — Typed Action Contract Platform for Physical AI.

The public surface is `__all__` below, and nothing else: what each name promises, and
what SemVer promises about it, is `docs/spec/python_api.md`. `tests/test_public_api.py`
pins the list, so a change to it turns CI red.
"""

__version__ = "0.1.0"

from .actions import ActionResult, Conversation, action, spec_of
from .actions.tools import ToolCall, ToolResult, ToolSet, dispatch
from .engine import (
    ActionContractEngine,
    Fact,
    Gate,
    GateRegistry,
    GateResult,
    GateVerdict,
    Reason,
    ResolvedGate,
    TreeResult,
    compile_tree,
    resolve_gate_file,
    resolve_gate_uri,
    walk,
)
from .errors import (
    ActionContractViolation,
    AgentManifestError,
    BoardCapabilityError,
    BuildFailed,
    EnvelopeRefusedError,
    GateError,
    GateInheritanceError,
    GateNotFoundError,
    GateSchemaError,
    NeuroEdgeError,
    PerceptionUnavailableError,
    ReplayError,
    SafetyRegressionError,
    TokenReplayError,
    ToolCallError,
    TraceValidationError,
    VerificationError,
)
from .hal import (
    BoardProfile,
    HardwareAbstractionLayer,
    PinAssertion,
    digital,
    load_board_by_id,
    motion,
)
from .hal.linux import LinuxHAL
from .hal.sim import SimHAL
from .models import SystemOne, SystemTwo
from .sim import SimSession, Turn
from .sim.serve import serve_mcp
from .testing import TraceRecorder, replay, scenario
from .trace import load_trace, validate_trace

__all__ = [
    "__version__",
    "ActionContractEngine",
    "ActionContractViolation",
    "ActionResult",
    "AgentManifestError",
    "BoardCapabilityError",
    "BoardProfile",
    "BuildFailed",
    "Conversation",
    "EnvelopeRefusedError",
    "Fact",
    "Gate",
    "GateError",
    "GateInheritanceError",
    "GateNotFoundError",
    "GateRegistry",
    "GateResult",
    "GateSchemaError",
    "GateVerdict",
    "HardwareAbstractionLayer",
    "LinuxHAL",
    "NeuroEdgeError",
    "PerceptionUnavailableError",
    "PinAssertion",
    "Reason",
    "ReplayError",
    "ResolvedGate",
    "SafetyRegressionError",
    "SimHAL",
    "SimSession",
    "SystemOne",
    "SystemTwo",
    "TokenReplayError",
    "ToolCall",
    "ToolCallError",
    "ToolResult",
    "ToolSet",
    "TraceRecorder",
    "TraceValidationError",
    "TreeResult",
    "Turn",
    "VerificationError",
    "action",
    "compile_tree",
    "digital",
    "dispatch",
    "load_board_by_id",
    "load_trace",
    "motion",
    "replay",
    "resolve_gate_file",
    "resolve_gate_uri",
    "scenario",
    "serve_mcp",
    "spec_of",
    "validate_trace",
    "walk",
]
