"""
`[vision]` of `agent.toml` — which model sees, and which of its labels become which facts
(TSK-V1b-03, FR-MDL-04, RFC-0012 §3c, Q-54).

    [vision]
    provider = "replay"                     # or "python:pkg.mod:factory"; swap the model here only
    model    = "models/person-det.tflite"   # YOUR model file; the adapter reads it, NeuroEdge ships none
    timeout_ms = 200                        # a model that answers later answers nothing

    [vision.zones]
    gate_area = [0.25, 0.40, 0.75, 1.00]    # [x0, y0, x1, y1] normalised in [0, 1], x0 < x1, y0 < y1

    [vision.facts.person_at_gate]
    label = "person"
    zone  = "gate_area"
    kind  = "present"                       # → a bool criterion; "count" and "confidence" → numeric
    min_frames = 3                          # default 3, at least 2

    [vision.options]                        # for an adapter of your own

**There is no threshold in this file.** The maker picks which label becomes which fact;
the confidence and count thresholds are the gate's `numeric` criteria (Q-54, RFC-0009), and
`bands` is refused as an unknown key. This module validates the *table*; the checks that
need the gate (`confidence_gte` on a vision fact, `present` without its `confidence`) are
`facts.unpaired` and the compiler's, which are the only places a gate and a manifest meet.

Every refusal is an `AgentManifestError` (NE3002) with where / why / how.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ...errors import AgentManifestError
from ...models.providers.common import (
    PYTHON_PREFIX,
    bounded,
    is_adapter,
    options,
    refuse_secrets,
    refuse_unknown,
)

KINDS = ("present", "count", "confidence")
# What each kind is to the gate (RFC-0012 §3c).
CRITERION_TYPE = {"present": "bool", "count": "numeric", "confidence": "numeric"}
DEFAULT_MIN_FRAMES = 3
MIN_FRAMES = 2
# A window longer than this is a configuration mistake: the 1000 ms age ceiling would refuse it.
MAX_MIN_FRAMES = 64
DEFAULT_TIMEOUT_MS = 200.0
MAX_TIMEOUT_MS = 10_000.0
KEYS = ("provider", "model", "timeout_ms", "zones", "facts", "options")
FACT_KEYS = ("label", "zone", "kind", "min_frames")
NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
LABEL = re.compile(r"^[^\x00-\x1f\x7f]{1,64}$")

Rect = tuple[float, float, float, float]


@dataclass(frozen=True)
class Zone:
    """A normalised rectangle. A detection is in it when the centre of its box is (edges count)."""

    name: str
    rect: Rect

    def contains(self, box: Rect) -> bool:
        x0, y0, x1, y1 = self.rect
        cx, cy = (box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0
        return x0 <= cx <= x1 and y0 <= cy <= y1


@dataclass(frozen=True)
class FactSpec:
    """One `[vision.facts.<name>]`: `name` is the gate criterion it feeds."""

    name: str
    label: str
    zone: str
    kind: str
    min_frames: int = DEFAULT_MIN_FRAMES

    @property
    def criterion_type(self) -> str:
        return CRITERION_TYPE[self.kind]


@dataclass(frozen=True)
class VisionConfig:
    provider: str | None = None
    model: str | None = None
    timeout_ms: float = DEFAULT_TIMEOUT_MS
    zones: dict[str, Zone] = field(default_factory=dict)
    facts: dict[str, FactSpec] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)
    source: Path | None = None

    @property
    def where(self) -> str:
        return f"{self.source} -> [vision]" if self.source else "[vision]"

    @property
    def adapter(self) -> str | None:
        """``pkg.mod:factory`` for a custom adapter, else None."""
        if self.provider is not None and self.provider.startswith(PYTHON_PREFIX):
            return self.provider[len(PYTHON_PREFIX) :]
        return None

    @property
    def window(self) -> int:
        """How many frames the longest fact looks at."""
        return max((spec.min_frames for spec in self.facts.values()), default=MIN_FRAMES)


def _bad(where: str, why: str, how: str) -> AgentManifestError:
    return AgentManifestError(where=where, why=why, how=how)


def _zone(name: str, value: Any, where: str) -> Zone:
    at = f"{where}.zones.{name}"
    if not isinstance(value, list) or not value or any(isinstance(v, list | dict) for v in value):
        why = (
            "a zone is a rectangle [x0, y0, x1, y1]; polygons are not supported in this version"
            if isinstance(value, list) and any(isinstance(v, list) for v in value)
            else "a zone is a list of four numbers [x0, y0, x1, y1]"
        )
        raise _bad(at, why, f"write {name} = [0.25, 0.40, 0.75, 1.00] (RFC-0012 §3c)")
    if len(value) != 4 or not all(
        isinstance(v, int | float) and not isinstance(v, bool) for v in value
    ):
        raise _bad(
            at,
            "a zone is exactly four numbers [x0, y0, x1, y1]",
            f"write {name} = [0.25, 0.40, 0.75, 1.00]",
        )
    x0, y0, x1, y1 = (float(v) for v in value)
    if not all(math.isfinite(v) and 0.0 <= v <= 1.0 for v in (x0, y0, x1, y1)):
        raise _bad(
            at,
            f"every coordinate must be in [0, 1], got {value}",
            "write coordinates normalised to the frame: 0 is the left/top edge, 1 the right/bottom",
        )
    if not (x0 < x1 and y0 < y1):
        raise _bad(
            at,
            f"x0 must be below x1 and y0 below y1, got {value}",
            "write [x0, y0, x1, y1] with the top-left corner first",
        )
    return Zone(name, (x0, y0, x1, y1))


def _fact(name: str, table: Any, zones: dict[str, Zone], where: str) -> FactSpec:
    at = f"{where}.facts.{name}"
    if not NAME.match(name):
        raise _bad(
            at,
            "a fact name is a gate criterion name: letters, digits and _, starting with a letter",
            "rename it to the criterion it feeds, e.g. person_at_gate",
        )
    if not isinstance(table, dict):
        raise _bad(at, "a fact must be a table", f"write [vision.facts.{name}]")
    refuse_unknown(
        table,
        at,
        f"vision.facts.{name}",
        FACT_KEYS,
        "there are no thresholds or bands here: the confidence and count thresholds are the "
        "gate's numeric criteria (Q-54, RFC-0012 §3c)",
    )
    label = table.get("label")
    if not isinstance(label, str) or not LABEL.match(label):
        raise _bad(
            at + " label",
            "label must be the model's label, a short plain string",
            'write label = "person"',
        )
    kind = table.get("kind")
    if kind not in KINDS:
        raise _bad(
            at + " kind",
            f"kind must be one of {list(KINDS)}",
            'write kind = "present" (bool), "count" or "confidence" (numeric)',
        )
    zone = table.get("zone")
    if not isinstance(zone, str) or zone not in zones:
        raise _bad(
            at + " zone",
            "zone must name a zone declared in [vision.zones]",
            f"declare it under [vision.zones], known: {sorted(zones)}",
        )
    frames = table.get("min_frames", DEFAULT_MIN_FRAMES)
    if (
        isinstance(frames, bool)
        or not isinstance(frames, int)
        or not MIN_FRAMES <= frames <= MAX_MIN_FRAMES
    ):
        raise _bad(
            at + " min_frames",
            f"min_frames must be a whole number from {MIN_FRAMES} to {MAX_MIN_FRAMES}: one noisy "
            "frame must not open a door",
            f"write min_frames = {DEFAULT_MIN_FRAMES} (the default), or remove it",
        )
    return FactSpec(name, label, zone, kind, frames)


def parse_vision(table: Any, source: Path | None = None) -> VisionConfig:
    """A validated `VisionConfig`; `AgentManifestError` naming the first bad field."""
    where = f"{source} -> [vision]" if source else "[vision]"
    if not isinstance(table, dict):
        raise _bad(where, "[vision] must be a table", "write [vision]")
    refuse_secrets(table, where, "VISION_API_KEY")
    refuse_unknown(
        table,
        where,
        "vision",
        KEYS,
        "put adapter settings under [vision.options]; thresholds belong to the gate",
    )
    provider = table.get("provider")
    if provider is not None and not (
        isinstance(provider, str)
        and (is_adapter(provider) or re.fullmatch(r"[a-z][a-z0-9_-]*", provider))
    ):
        raise _bad(
            where + " provider",
            f'provider must be a built-in name (e.g. "replay") or "{PYTHON_PREFIX}<module>:<factory>"; '
            "the value given is neither (not repeated here: it may be a key)",
            'write provider = "replay", or provider = "python:my_vision.adapter:make" (FR-MDL-08)',
        )
    model = table.get("model")
    if model is not None and (
        not isinstance(model, str) or not model.strip() or any(ord(c) < 32 for c in model)
    ):
        raise _bad(
            where + " model",
            "model must be the path of your model file, a plain string",
            'write model = "models/person-det.tflite"',
        )
    timeout = bounded(
        table,
        where,
        "timeout_ms",
        default=DEFAULT_TIMEOUT_MS,
        low=0,
        high=MAX_TIMEOUT_MS,
        unit="a number of milliseconds",
    )
    raw_zones = table.get("zones", {})
    if not isinstance(raw_zones, dict):
        raise _bad(where + " zones", "zones must be a table", "write [vision.zones]")
    zones = {name: _zone(name, value, where) for name, value in raw_zones.items()}
    raw_facts = table.get("facts", {})
    if not isinstance(raw_facts, dict):
        raise _bad(where + " facts", "facts must be a table", "write [vision.facts.<name>]")
    facts = {name: _fact(name, value, zones, where) for name, value in raw_facts.items()}
    return VisionConfig(
        provider=provider,
        model=model,
        timeout_ms=timeout,
        zones=zones,
        facts=facts,
        options=options(table, where, "vision", None),
        source=source,
    )
