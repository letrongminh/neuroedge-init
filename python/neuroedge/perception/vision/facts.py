"""
From detections to typed facts, and back from a trace (TSK-V1b-03, TSK-V1b-08, RFC-0012 §3c–§3e).

A *window* is the last `min_frames` consecutive camera frames. Each frame gives the fact a
value (`frame_value`); the gate then judges **every frame of the window and ANDs the answers**
(`engine_fact`), so a single noisy frame never opens anything and a single bad one always
blocks — in either direction of the comparison.

A window is *unavailable* — the fact is not read, the gate blocks `criterion_unavailable`,
nothing is interpolated from an earlier frame — when `read_fact` finds any of `UNAVAILABLE`.

This module is **pure** (no clock, no model, no I/O) and is the one definition both sides use:
the live `VisionPipeline` builds a `FactReading` from frames it just inferred, and replay
(`reading_from_event`) builds the same one from the `vision_fact` event a trace recorded —
so a verdict is recomputed from recorded labels and never from a model (FR-CI-02). The
event is the shape RFC-0012 §3d specifies; `docs/spec/vision.md` §4 lists its fields.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

from ...engine.decision_tree import walk
from ...engine.verdict import Fact, GateVerdict
from .config import KINDS, FactSpec
from .model import (
    MAX_FRAME_AGE_MS,
    PRESENT_SCORE_FLOOR,
    REJECTED,
    SHA256,
    ModelIdentity,
    VisionRef,
)

EVENT_TYPE = "vision_fact"
# Why a fact was not read, as written in `vision_fact.unavailable`. Closed.
UNAVAILABLE = (
    *REJECTED,  # a frame of the window the model could not (or would not) read
    "window_size",  # not `min_frames` frames: lost frames restart the window
    "frame_gap",  # the frames are not consecutive camera frame numbers
    "frozen",  # two neighbouring frames are byte-identical: the camera stopped
    "future",  # a frame was read after the instant it is judged at
    "stale",  # the oldest frame is older than MAX_FRAME_AGE_MS
    "unpaired",  # `present` / `count` without its numeric `confidence` in the gate
    "mismatch",  # replay: the recorded event does not add up
)
_NON_FINITE = {"nan": math.nan, "inf": math.inf, "-inf": -math.inf}


@dataclass(frozen=True)
class LabelRecord:
    """One detection as the trace keeps it: label, the zone it fell in, and its score."""

    label: str
    zone: str
    score: float


@dataclass(frozen=True)
class Observation:
    """
    One frame as the perception layer read it. `captured_ms` is on the trace timeline;
    `read_ms` is the same instant on the `EventLog` clock (live only: it is what the engine
    ages a reading from). `rejected` is one of `REJECTED` when no label could be read.
    """

    seq: int
    ref: VisionRef
    captured_ms: int
    labels: tuple[LabelRecord, ...] = ()
    rejected: str | None = None
    read_ms: float | None = None


def frame_value(kind: str, scores: Sequence[float]) -> bool | int | float | None:
    """
    The fact's value on one frame, from the scores of the detections of its label in its zone
    (RFC-0012 §3e, §9.13). `confidence` is the highest score, `0.0` when nothing was seen
    (absence is a score of zero, never "undecided"); `count` is how many reach
    `PRESENT_SCORE_FLOOR`; `present` is `count >= 1`.

    A score that is NaN, infinite or outside [0, 1] makes `confidence` and `count` NaN — the
    gate answers `value_out_of_range` whatever range it declared — and `present` ``None``
    (a bool has no out-of-range: the window is unavailable).
    """
    if any(not math.isfinite(s) or not 0.0 <= s <= 1.0 for s in scores):
        return None if kind == "present" else math.nan
    if kind == "confidence":
        return max(scores, default=0.0)
    count = sum(1 for s in scores if s >= PRESENT_SCORE_FLOOR)
    return count if kind == "count" else count >= 1


def _scores(spec: FactSpec, frame: Observation) -> list[float]:
    return [
        item.score for item in frame.labels if item.label == spec.label and item.zone == spec.zone
    ]


@dataclass(frozen=True)
class FactReading:
    """
    One fact over one window, at one instant: what the gate is given, and what a trace records.
    `unavailable` is None for a fact that was read, else one of `UNAVAILABLE`; `problems` is
    what replay found wrong with the recorded event (and then `unavailable` is "mismatch").
    """

    spec: FactSpec
    model: ModelIdentity
    frames: tuple[Observation, ...]
    eval_offset_ms: int
    unavailable: str | None
    values: tuple[Any, ...]
    problems: tuple[str, ...] = ()

    @property
    def age_ms(self) -> int | None:
        """Age of the window: of its oldest frame, at the instant it is judged (RFC-0012 §3d)."""
        if not self.frames:
            return None
        return self.eval_offset_ms - min(frame.captured_ms for frame in self.frames)

    @property
    def value(self) -> Any:
        """The latest frame's value; None when the fact was not read."""
        return None if self.unavailable else self.values[-1]


def read_fact(
    spec: FactSpec, model: ModelIdentity, frames: Iterable[Observation], eval_offset_ms: int
) -> FactReading:
    """The reading of `spec` over `frames` (oldest first), judged at `eval_offset_ms`."""
    window = tuple(frames)
    values = tuple(None if f.rejected else frame_value(spec.kind, _scores(spec, f)) for f in window)
    reading = FactReading(spec, model, window, eval_offset_ms, None, values)
    why = _unavailable(reading)
    return reading if why is None else _with(reading, why)


def _with(reading: FactReading, why: str, problems: tuple[str, ...] = ()) -> FactReading:
    return FactReading(
        reading.spec,
        reading.model,
        reading.frames,
        reading.eval_offset_ms,
        why,
        reading.values,
        problems or reading.problems,
    )


def _unavailable(reading: FactReading) -> str | None:
    frames, spec = reading.frames, reading.spec
    if len(frames) != spec.min_frames:
        return "window_size"
    for frame in frames:
        if frame.rejected:
            return frame.rejected if frame.rejected in REJECTED else "garbage"
    if any(b.seq != a.seq + 1 for a, b in zip(frames, frames[1:], strict=False)):
        return "frame_gap"
    if any(a.ref.sha256 == b.ref.sha256 for a, b in zip(frames, frames[1:], strict=False)):
        return "frozen"
    if any(frame.captured_ms > reading.eval_offset_ms for frame in frames):
        return "future"
    if reading.age_ms is not None and reading.age_ms > MAX_FRAME_AGE_MS:
        return "stale"
    if any(value is None for value in reading.values):
        return "garbage"
    return None


# --- to the gate -----------------------------------------------------------------------


def engine_fact(node: Mapping[str, Any], reading: FactReading) -> Fact | None:
    """
    The one `Fact` the Gate Engine is given for criterion `node` of the tree: the value of the
    first frame of the window the criterion refuses, else the latest frame's — judged frame by
    frame and ANDed (RFC-0012 §3c, §9.2). ``None`` when the fact was not read (the engine then
    blocks `criterion_unavailable`).

    A criterion satisfied by every frame is satisfied by the one fact returned, and one refused
    on any frame is refused with the reason of the first such frame, so the engine's own walk
    decides — and records — exactly the AND. The age is the window's, so `max_age_ms` and the
    1000 ms ceiling apply to its oldest frame.
    """
    if reading.unavailable is not None or reading.age_ms is None:
        return None
    oldest = min(reading.frames, key=lambda frame: frame.captured_ms)
    chosen = reading.values[-1]
    for value in reading.values:
        probe = Fact(value, source="vision", age_ms=reading.age_ms)
        if walk({"nodes": [node]}, {node["criterion"]: probe}).verdict is not GateVerdict.ALLOW:
            chosen = value
            break
    return Fact(chosen, source="vision", read_ms=oldest.read_ms, age_ms=reading.age_ms)


def unpaired(readings: Mapping[str, FactReading], tree: Mapping[str, Any]) -> set[str]:
    """
    The facts of `readings` the gate of `tree` may not use alone (RFC-0012 §3c, §9.10): a
    `present` or `count` of a label and zone whose numeric `confidence` of the same label and
    zone is not an `allow_when` criterion of the gate. A bool has no `max_age_ms`: without that
    criterion a camera repeating "nobody there" would pass `present: false`. The build refuses
    such a gate; this is the same rule at run time and in replay, so a gate that slipped past
    cannot be argued past it.
    """
    numeric = {node["criterion"] for node in tree["nodes"] if node["kind"] == "numeric"}
    paired = {
        (r.spec.label, r.spec.zone)
        for name, r in readings.items()
        if r.spec.kind == "confidence" and name in numeric
    }
    return {
        name
        for name, r in readings.items()
        if r.spec.kind in ("present", "count") and (r.spec.label, r.spec.zone) not in paired
    }


def facts_for_tree(
    readings: Mapping[str, FactReading], tree: Mapping[str, Any]
) -> tuple[dict[str, Fact], dict[str, FactReading]]:
    """
    ``(facts, readings)`` for the criteria of `tree` that `readings` can speak for: the
    `Fact` per available criterion (an unavailable one is simply absent), and the readings as
    judged here — a reading that is `unpaired` comes back unavailable with that reason. Used
    by the live pipeline and by replay alike.
    """
    nodes = {node["criterion"]: node for node in tree["nodes"]}
    used = {name: r for name, r in readings.items() if name in nodes}
    lonely = unpaired(used, tree)
    judged = {
        name: _with(r, "unpaired") if name in lonely and r.unavailable is None else r
        for name, r in used.items()
    }
    facts: dict[str, Fact] = {}
    for name, reading in judged.items():
        fact = engine_fact(nodes[name], reading)
        if fact is not None:
            facts[name] = fact
    return facts, judged


# --- the trace event (RFC-0012 §3d) ------------------------------------------------------


def to_event(reading: FactReading) -> dict[str, Any]:
    """The `data` of the `vision_fact` event of `reading`. No pixels: `vision_ref` only."""
    spec = reading.spec
    return {
        "fact": spec.name,
        "kind": spec.kind,
        "label": spec.label,
        "zone": spec.zone,
        "min_frames": spec.min_frames,
        "value": reading.value,
        "values": list(reading.values),
        **({"unavailable": reading.unavailable} if reading.unavailable else {}),
        "age_ms": reading.age_ms,
        "max_frame_age_ms": MAX_FRAME_AGE_MS,
        "present_score_floor": PRESENT_SCORE_FLOOR,
        "model": reading.model.to_json(),
        "frames": [_frame_json(spec, frame) for frame in reading.frames],
    }


def _frame_json(spec: FactSpec, frame: Observation) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "frame_seq": frame.seq,
        "vision_ref": frame.ref.to_json(),
        "captured_ms": frame.captured_ms,
        "labels": [
            {"label": item.label, "zone": item.zone, "score": item.score}
            for item in frame.labels
            if item.label == spec.label and item.zone == spec.zone
        ],
    }
    if frame.rejected:
        entry["rejected"] = frame.rejected
    return entry


def _number(value: Any) -> Any:
    """A recorded number: the strings "nan", "inf", "-inf" are how a trace holds the others."""
    if isinstance(value, str) and value in _NON_FINITE:
        return _NON_FINITE[value]
    return value


def reading_from_event(offset_ms: int, data: Mapping[str, Any]) -> FactReading:
    """
    The reading a recorded `vision_fact` event stands for, **recomputed** from its recorded
    labels at the instant it was judged (`offset_ms`) — no model, no frame (FR-CI-02).

    What the event claims (`value`, `values`, `unavailable`, `age_ms`, the two pinned constants)
    is compared with what the labels give. Anything that does not add up is listed in
    `problems` and the reading is unavailable ("mismatch"): a replay never trusts an event over
    its own evidence, and an altered trace can only block more, never allow.
    """
    problems: list[str] = []
    try:
        spec = FactSpec(
            str(data["fact"]),
            str(data["label"]),
            str(data["zone"]),
            str(data["kind"]),
            data["min_frames"],
        )
        model = ModelIdentity(data["model"]["name"], data["model"]["sha256"])
        frames = tuple(_observation(item) for item in data["frames"])
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        placeholder = FactSpec("?", "?", "?", "present", 2)
        digest = "0" * 64
        return FactReading(
            placeholder,
            ModelIdentity("?", digest),
            (),
            offset_ms,
            "mismatch",
            (),
            (f"the vision_fact event is malformed: {type(exc).__name__}: {exc}",),
        )
    if (
        spec.kind not in KINDS
        or isinstance(spec.min_frames, bool)
        or not isinstance(spec.min_frames, int)
    ):
        return FactReading(
            spec,
            model,
            frames,
            offset_ms,
            "mismatch",
            (),
            (f"kind {spec.kind!r} or min_frames {spec.min_frames!r} is not valid",),
        )
    try:
        reading = read_fact(spec, model, frames, offset_ms)
    except (TypeError, ValueError, OverflowError) as exc:  # a recorded score that is no number
        return FactReading(
            spec,
            model,
            frames,
            offset_ms,
            "mismatch",
            (),
            (f"the labels cannot be read: {type(exc).__name__}: {exc}",),
        )

    def claim(name: str, recorded: Any, recomputed: Any) -> None:
        if _number(recorded) != recomputed and not (
            isinstance(recomputed, float)
            and math.isnan(recomputed)
            and isinstance(_number(recorded), float)
            and math.isnan(_number(recorded))
        ):
            problems.append(f"recorded {name}={recorded!r}, the labels give {recomputed!r}")

    claim("age_ms", data.get("age_ms"), reading.age_ms)
    claim("unavailable", data.get("unavailable"), reading.unavailable)
    claim("value", data.get("value"), reading.value)
    recorded_values = data.get("values")
    if isinstance(recorded_values, list) and len(recorded_values) == len(reading.values):
        for index, (was, now) in enumerate(zip(recorded_values, reading.values, strict=True)):
            claim(f"values[{index}]", was, now)
    else:
        problems.append("recorded values do not match the frames")
    if data.get("max_frame_age_ms") != MAX_FRAME_AGE_MS:
        problems.append(
            f"recorded max_frame_age_ms={data.get('max_frame_age_ms')!r}, "
            f"this code pins {MAX_FRAME_AGE_MS}"
        )
    if data.get("present_score_floor") != PRESENT_SCORE_FLOOR:
        problems.append(
            f"recorded present_score_floor={data.get('present_score_floor')!r}, "
            f"this code pins {PRESENT_SCORE_FLOOR}"
        )
    return _with(reading, "mismatch", tuple(problems)) if problems else reading


def rebased(reading: FactReading, eval_offset_ms: int) -> FactReading:
    """
    `reading` judged at another instant of another timeline, its frames moved with it: replay
    writes the event again on its own clock, with the same ages (`age_ms` is a distance).
    """
    shift = eval_offset_ms - reading.eval_offset_ms
    frames = tuple(replace(f, captured_ms=f.captured_ms + shift) for f in reading.frames)
    return replace(reading, frames=frames, eval_offset_ms=eval_offset_ms)


def _observation(item: Mapping[str, Any]) -> Observation:
    ref = item["vision_ref"]
    if not SHA256.fullmatch(ref["sha256"]) or isinstance(ref["size"], bool):
        raise ValueError("vision_ref is not a SHA-256 and a size")
    seq, captured = item["frame_seq"], item["captured_ms"]
    if any(isinstance(n, bool) or not isinstance(n, int) for n in (seq, captured)):
        raise ValueError("frame_seq and captured_ms must be whole numbers")
    return Observation(
        seq,
        VisionRef(ref["sha256"], ref["size"]),
        captured,
        tuple(
            LabelRecord(entry["label"], entry["zone"], _number(entry["score"]))
            for entry in item["labels"]
        ),
        item.get("rejected"),
    )
