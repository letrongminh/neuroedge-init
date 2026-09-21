"""
Action CI Testing Framework.
Implements replay() and scenario() for bit-for-bit regression tests.
"""

import json
from pathlib import Path
from typing import Any

from ..hal import PinAssertion


class ActionState:
    def __init__(self, action_name: str, blocked: bool = True):
        self.action_name = action_name
        self.blocked = blocked


class GateState:
    def __init__(self, name: str, verdict: str = "BLOCK"):
        self.name = name
        self.verdict = verdict


class ReplaySession:
    """
    Session object returned by replay() and scenario().
    Allows asserting gate verdicts and physical pin states.
    """

    def __init__(
        self,
        trace_data: dict[str, Any],
        network: str = "online",
        slow: str | None = None,
        target: str = "sim",
    ):
        self.trace_data = trace_data
        self.network = network
        self.slow_model = slow
        self.target = target

        # Analyze events
        self.blocked_by: str | None = None
        self.escalated_to: str | None = None
        self.reason: str | None = None
        self._actions: dict[str, ActionState] = {}
        self._gates: dict[str, GateState] = {}
        self._pins: dict[str, PinAssertion] = {}

        self._parse_events()

    def _parse_events(self):
        events = self.trace_data.get("events", [])
        for ev in events:
            ev_type = ev.get("type")
            data = ev.get("data", {})

            if ev_type == "gate_evaluation_result":
                verdict = data.get("verdict", "BLOCK")
                gate_id = data.get("blocked_by", "unknown_gate")
                self.blocked_by = gate_id
                self.escalated_to = data.get("escalated_to")
                self.reason = data.get("reason")
                self._gates["unlock_door"] = GateState("unlock_door", verdict=verdict)
                self._actions["unlock_door"] = ActionState(
                    "unlock_door", blocked=(verdict == "BLOCK")
                )

            elif ev_type == "actuator_command":
                pin = data.get("pin")
                op = data.get("operation")
                dur = data.get("duration_ms", 0)
                self._pins[pin] = PinAssertion(pin, pulsed=(op == "pulse"), duration_ms=dur)

    def action(self, name: str) -> ActionState:
        return self._actions.get(name, ActionState(name, blocked=True))

    def gate(self, name: str) -> GateState:
        return self._gates.get(name, GateState(name, verdict="BLOCK"))

    def pin(self, name: str) -> PinAssertion:
        return self._pins.get(name, PinAssertion(name, pulsed=False))


def replay(trace_path: str, slow: str | None = None, target: str = "sim") -> ReplaySession:
    p = Path(trace_path)
    if not p.exists():
        # Check in fixtures/traces/
        fixture_p = Path(__file__).parents[3] / "fixtures" / "traces" / p.name
        if fixture_p.exists():
            p = fixture_p
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    return ReplaySession(data, slow=slow, target=target)


def scenario(trace_path: str, network: str = "online", target: str = "sim") -> ReplaySession:
    p = Path(trace_path)
    if not p.exists():
        fixture_p = Path(__file__).parents[3] / "fixtures" / "traces" / p.name
        if fixture_p.exists():
            p = fixture_p
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    return ReplaySession(data, network=network, target=target)
