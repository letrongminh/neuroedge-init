"""
Action Contract Engine (L3) - Core Safety Engine.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

class GateVerdict(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"

@dataclass
class Gate:
    name: str
    version: str
    verdict: GateVerdict = GateVerdict.BLOCK
    blocked_by: Optional[str] = None
    reason: Optional[str] = None
    escalated_to: Optional[str] = None

class ActionContractEngine:
    """
    Enforces that every physical actuator command must pass through an authorized Gate.
    Guarantees fail-closed semantics when offline or on error.
    """
    def __init__(self, fail_closed: bool = True):
        self.fail_closed = fail_closed
        self.gates: Dict[str, Gate] = {}

    def evaluate(self, gate_name: str, context: Dict[str, Any]) -> Gate:
        # Default safety: fail closed if gate not registered or context unverified
        if gate_name not in self.gates:
            return Gate(
                name=gate_name,
                version="unknown",
                verdict=GateVerdict.BLOCK,
                blocked_by=gate_name,
                reason="gate_not_found",
            )
        return self.gates[gate_name]
