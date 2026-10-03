"""
Frames in, typed facts out: the live half of the vision seam (TSK-V1b-03, docs/spec/vision.md §2).

`VisionPipeline` sits between a camera (`vision.in`, TSK-V1b-01/02 hand it `Frame`s) and the
Gate Engine:

    pipeline.push(frame)                    # every frame: the model reads it, untrusted
    facts = pipeline.facts_for(engine.tree(key))
    await engine.evaluate(key, facts)       # the gate decides; a missing fact blocks

`push` runs the model and the domain check (`model.sanitize`), assigns each detection to the
zones its box centre falls in, and keeps the last frames. A frame that follows a gap in the
camera's frame numbers **restarts** the window; a model that raises, answers later than
`timeout_ms`, or returns garbage rejects the frame — and a rejected frame in a window makes
every fact over it unavailable until it ages out. Nothing is carried over from an earlier
frame to cover a failure (RFC-0012 §3e).

`facts_for` reads each fact the gate's tree names, writes one `vision_fact` event for it
(`facts.to_event`: labels and `vision_ref`, never pixels) and returns the engine-ready facts.
The thresholds are the tree's; this layer has none (Q-54).
"""

from __future__ import annotations

import inspect
import math
import time
from collections.abc import Mapping
from typing import Any

from ...engine.trace_sink import EventLog
from ...engine.verdict import Fact
from ...errors import AgentManifestError
from .config import VisionConfig
from .facts import EVENT_TYPE, LabelRecord, Observation, facts_for_tree, read_fact, to_event
from .model import (
    Detection,
    Frame,
    Inference,
    ModelIdentity,
    Rejected,
    VisionModel,
    VisionUnavailable,
    sanitize,
)

MODELS_KEY = "vision_models"  # metadata: every model the session used (RFC-0012 §3d)


def _slower(reported: Any, measured: float) -> Any:
    """The larger of a reported latency and the measured one; a report that is no number stays."""
    if isinstance(reported, bool) or not isinstance(reported, int | float):
        return reported
    return max(reported, measured) if not math.isnan(reported) else reported


class VisionPipeline:
    def __init__(self, config: VisionConfig, model: VisionModel, *, events: EventLog) -> None:
        self.config = config
        self.events = events
        self._buffer: list[Observation] = []
        self.model = model
        self._adopt(model)

    def _adopt(self, model: VisionModel) -> None:
        missing = sorted({s.label for s in self.config.facts.values()} - set(model.labels))
        if missing:
            raise AgentManifestError(
                where=f"{self.config.where} facts",
                why=f"a fact reads label(s) {missing} that model {model.identity.name!r} "
                "cannot say, so it could never be true",
                how=f"fix the label, or use a model that says it: {sorted(model.labels)}",
            )
        self.model = model
        known: list[dict[str, str]] = self.events.metadata.setdefault(MODELS_KEY, [])
        entry = model.identity.to_json()
        if entry not in known:
            known.append(entry)

    def set_model(self, model: VisionModel) -> None:
        """Swap the model. The window restarts: no window mixes two models' readings."""
        self._adopt(model)
        self._buffer = []

    @property
    def identity(self) -> ModelIdentity:
        return self.model.identity

    # -- frames in ---------------------------------------------------------------
    def push(self, frame: Frame) -> Observation:
        """Read one frame. Never raises for what the model does; a failure rejects the frame."""
        detections, rejected = self._infer(frame)
        captured = self.events.offset_of(frame.captured_ms)
        observation = Observation(
            frame.seq,
            frame.ref,
            0 if captured is None else captured,
            () if rejected else self._zoned(detections),
            "garbage" if captured is None else (rejected.reason if rejected else None),
            frame.captured_ms,
        )
        if self._buffer and frame.seq != self._buffer[-1].seq + 1:
            self._buffer = []  # frames were lost (or repeated out of order): start again
        self._buffer.append(observation)
        del self._buffer[: -max(self.config.window, 1)]
        return observation

    def _infer(self, frame: Frame) -> tuple[tuple[Detection, ...], Rejected | None]:
        started = time.perf_counter()
        try:
            raw = self.model.detect(frame)
        except VisionUnavailable as exc:
            return (), Rejected("model_unavailable", exc.why)
        except Exception as exc:  # a model failure is a rejected frame, not a crash
            return (), Rejected("model_error", type(exc).__name__)
        if inspect.isawaitable(raw):
            if inspect.iscoroutine(raw):
                raw.close()
            return (), Rejected(
                "model_error", "detect() is async; wrap it (docs/spec/vision.md §3)"
            )
        measured = (time.perf_counter() - started) * 1000.0
        reported = raw.latency_ms if isinstance(raw, Inference) else None
        # A model that reports its own latency (a simulated one) is believed only upward: the
        # real time the call took is never less than what it cost.
        latency = measured if reported is None else _slower(reported, measured)
        if (
            isinstance(latency, bool)
            or not isinstance(latency, int | float)
            or not math.isfinite(latency)
            or not 0 <= latency <= self.config.timeout_ms
        ):
            return (), Rejected("timeout", "the model answered after timeout_ms (or not at all)")
        return sanitize(self.model.labels, raw)

    def _zoned(self, detections: tuple[Detection, ...]) -> tuple[LabelRecord, ...]:
        return tuple(
            LabelRecord(d.label, zone.name, float(d.score))
            for d in detections
            for zone in self.config.zones.values()
            if zone.contains(d.box)
        )

    # -- facts out ---------------------------------------------------------------
    def facts_for(self, tree: Mapping[str, Any]) -> dict[str, Fact]:
        """
        The facts of `tree`'s criteria that this config declares, read from the latest window
        (one `vision_fact` event each); pass them to `engine.evaluate` as its context. A fact
        that cannot be read is absent, so the engine blocks it `criterion_unavailable`.
        """
        now = self.events.elapsed_ms()
        criteria = {node["criterion"] for node in tree["nodes"]}
        readings = {
            name: read_fact(spec, self.identity, self._buffer[-spec.min_frames :], now)
            for name, spec in self.config.facts.items()
            if name in criteria
        }
        facts, judged = facts_for_tree(readings, tree)
        for reading in judged.values():
            self.events.emit(EVENT_TYPE, to_event(reading), offset_ms=now)
        return facts
