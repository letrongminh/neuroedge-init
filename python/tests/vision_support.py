"""
Shared pieces of the vision tests (TSK-V1b-03, TSK-V1b-08): gates in the shape of RFC-0012 §3c,
a fake clock, frames, and a pipeline wired to a Gate Engine — no camera, no model, no network.
"""

from __future__ import annotations

from typing import Any

from neuroedge.engine import ActionContractEngine, EventLog, resolve_gate_document
from neuroedge.perception.vision import (
    Detection,
    Frame,
    ScriptedVisionModel,
    VisionConfig,
    VisionPipeline,
    parse_vision,
)

START = 1000.0  # the FakeClock starts here, so a clock reading is its offset + START
PERSON = "person"
INSIDE = (0.4, 0.5, 0.6, 0.9)  # centre (0.5, 0.7): inside gate_area
OUTSIDE = (0.0, 0.0, 0.2, 0.2)


class FakeClock:
    def __init__(self, start: float = START) -> None:
        self.now = float(start)

    def __call__(self) -> float:
        return self.now

    def advance(self, ms: float) -> None:
        self.now += ms


VISION_TABLE: dict[str, Any] = {
    "provider": "replay",
    "zones": {"gate_area": [0.25, 0.40, 0.75, 1.00]},
    "facts": {
        "person_at_gate": {"label": PERSON, "zone": "gate_area", "kind": "present"},
        "people_at_gate": {"label": PERSON, "zone": "gate_area", "kind": "count"},
        "person_confidence": {"label": PERSON, "zone": "gate_area", "kind": "confidence"},
    },
}


def config(**overrides: Any) -> VisionConfig:
    return parse_vision({**VISION_TABLE, **overrides})


def _numeric(unit: str, high: float, max_age_ms: int) -> dict[str, Any]:
    return {
        "type": "numeric",
        "unit": unit,
        "range": {"min": 0, "max": high},
        "max_age_ms": max_age_ms,
        "instructions": unit,
    }


def gate_document(name: str, allow_when: dict[str, Any], max_age_ms: int = 300) -> dict[str, Any]:
    """The gates of RFC-0012 §3c as a document: the criteria are those `allow_when` names."""
    catalogue = {
        "person_at_gate": {"type": "bool", "instructions": "a person is in the gate area"},
        "people_at_gate": _numeric("count", 50, max_age_ms),
        "person_confidence": _numeric("ratio", 1, max_age_ms),
    }
    return {
        "schema": "neuroedge.gate/v1",
        "name": name,
        "version": "1.0.0",
        "evaluate": {key: catalogue[key] for key in allow_when},
        "allow_when": allow_when,
        "on_block": {"action": "deny"},
        "budget": {"p95_latency_ms": 100, "fail": "closed"},
    }


def gate(name: str, allow_when: dict[str, Any], max_age_ms: int = 300):
    return resolve_gate_document(gate_document(name, allow_when, max_age_ms))


def open_gate(**kw: Any):
    return gate("open_gate", {"person_at_gate": True, "person_confidence": {"gte": 0.85}}, **kw)


def close_gate(**kw: Any):
    return gate(
        "close_gate",
        {
            "person_at_gate": False,
            "people_at_gate": {"lte": 0},
            "person_confidence": {"lte": 0.10},
        },
        **kw,
    )


def person(score: float, box: tuple[float, float, float, float] = INSIDE) -> Detection:
    return Detection(PERSON, score, box)


def frame(seq: int, at: float, tag: str = "") -> Frame:
    """Frame `seq`, read at clock reading `at`; the pixels differ per frame unless `tag` repeats."""
    return Frame(seq, at, f"pixels-{tag or seq}".encode(), 4, 4, "gray8")


class Rig:
    """A pipeline, an event log and an engine on one fake clock."""

    def __init__(self, script: dict[int, Any], gates=None, **model: Any) -> None:
        self.clock = FakeClock()
        self.events = EventLog(self.clock, agent_version="villa-concierge@0.1.0")
        self.model = ScriptedVisionModel(script, labels=[PERSON], name="person-det", **model)
        self.config = config()
        self.pipeline = VisionPipeline(self.config, self.model, events=self.events)
        self.engine = ActionContractEngine(
            gates or {"open": open_gate(), "close": close_gate()},
            events=self.events,
            clock=self.clock,
        )

    def feed(self, seq: int, ago: float = 0.0, tag: str = "") -> Any:
        """Push frame `seq`, read `ago` ms before now."""
        return self.pipeline.push(frame(seq, self.clock.now - ago, tag))

    def play(self, *seqs: int, step: float = 33.0) -> None:
        """Advance the clock `step` ms and push each frame number, as a camera at that rate."""
        for seq in seqs:
            self.clock.advance(step)
            self.feed(seq)

    async def decide(self, key: str = "open"):
        facts = self.pipeline.facts_for(self.engine.tree(key))
        return await self.engine.evaluate(key, facts)
