"""
The contract of a vision model (TSK-V1b-03, FR-MDL-04, FR-MDL-07, RFC-0012 §3c).

One method, **frames in, detections out**: ``detect(frame) -> Sequence[Detection]``
(or an `Inference`, which also says how long it took on the session's clock). The
model is the only thing that changes when a person swaps one for another; the
camera (`vision.in`, TSK-V1b-01/02) and the gate know nothing of it.

What a model says is **untrusted input**, like a transcript (`providers/base.py`).
`sanitize` is the domain check that stands between it and everything else:

* a label outside the model's own label set, a score that is not a number, a box
  that is not a rectangle in [0, 1], a result that is not a list of `Detection`,
  or more than `MAX_DETECTIONS` of them ⇒ the **whole frame** is rejected
  (`Rejected`): no fact is read from it;
* a score that *is* a number but is NaN, infinite or outside [0, 1] is kept as it
  is — `facts.py` turns it into a fact the gate refuses as `value_out_of_range`
  (RFC-0012 §3e), never into a pass.

A model that cannot answer **raises** — `VisionUnavailable` for a failure it
understands, anything else is taken the same way — or answers later than
`timeout_ms` (`pipeline.py`). Both reject the frame: a missing model, a timeout and
garbage are never a default "nobody there" (RFC-0012 §3e; invariant #2).
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from ...errors import PerceptionUnavailableError

# RFC-0012 §3c: the score from which a detection counts as present. Pinned here, written into
# every `vision_fact` event, never declared by a maker: the safety threshold is the gate's.
PRESENT_SCORE_FLOOR = 0.5
# RFC-0012 §3d: the oldest a window may be, whatever `max_age_ms` the gate allows. In code, not
# configurable, written into every `vision_fact` event.
MAX_FRAME_AGE_MS = 1000
# More detections than this from one frame is a model looping, not a scene.
MAX_DETECTIONS = 1000

SHA256 = re.compile(r"^[0-9a-f]{64}$")

# Why a frame was rejected, as written in the trace (`frames[].rejected`). Closed.
REJECTED = ("garbage", "model_error", "model_unavailable", "timeout")

Box = tuple[float, float, float, float]


class VisionUnavailable(PerceptionUnavailableError):
    """
    A vision model could not answer. Same stable code as its parent (NE5001): a subclass,
    not a new error. `latency_ms` is for simulated models, as in `providers/base.py`.
    """

    def __init__(self, where: str, why: str, how: str, *, latency_ms: float | None = None) -> None:
        self.latency_ms = latency_ms
        super().__init__(where=where, why=why, how=how)


@dataclass(frozen=True)
class VisionRef:
    """A frame's identity — hash and size, never the image (NFR-PRIV-01, RFC-0012 §3d)."""

    sha256: str
    size: int

    def to_json(self) -> dict[str, Any]:
        return {"sha256": self.sha256, "size": self.size}


@dataclass(frozen=True)
class Frame:
    """
    One camera frame, as `vision.in` hands it over (the seam of docs/spec/vision.md §2).

    `seq` is the camera's own frame number: a jump means frames were lost. `captured_ms` is
    when the HAL read it, on the clock of the session's `EventLog` (the clock `Fact.read_ms`
    is on). `pixels` stay in memory: only `ref` ever reaches a trace.
    """

    seq: int
    captured_ms: float
    pixels: bytes
    width: int = 0
    height: int = 0
    pixel_format: str = ""

    def __post_init__(self) -> None:
        # The camera is trusted code, the model is not: a malformed frame is a bug to see.
        if isinstance(self.seq, bool) or not isinstance(self.seq, int):
            raise ValueError(f"frame seq must be a whole number, got {self.seq!r}")
        if not _real(self.captured_ms) or not math.isfinite(self.captured_ms):
            raise ValueError(f"frame captured_ms must be a finite number, got {self.captured_ms!r}")
        if not isinstance(self.pixels, bytes | bytearray | memoryview):
            raise ValueError("frame pixels must be bytes")

    @property
    def ref(self) -> VisionRef:
        return VisionRef(hashlib.sha256(self.pixels).hexdigest(), len(self.pixels))


@dataclass(frozen=True)
class ModelIdentity:
    """A model's name and the SHA-256 of its file: who said what (RFC-0012 §3d, §9.4)."""

    name: str
    sha256: str

    def __post_init__(self) -> None:
        if not self.name or not SHA256.fullmatch(self.sha256):
            raise ValueError(
                f"a model identity is a name and a lowercase SHA-256, got {self.name!r}, "
                f"{self.sha256!r}"
            )

    def to_json(self) -> dict[str, str]:
        return {"name": self.name, "sha256": self.sha256}


def identity_of_file(path: str | Path, name: str | None = None) -> ModelIdentity:
    """The identity of a model file: its stem (or `name`) and the SHA-256 of its bytes."""
    path = Path(path)
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return ModelIdentity(name or path.stem, digest.hexdigest())


@dataclass(frozen=True)
class Detection:
    """
    One thing the model saw: a `label` from its label set, a `score` in [0, 1] and the `box`
    around it, normalised ``(x0, y0, x1, y1)`` in [0, 1] with x0 < x1 and y0 < y1.
    """

    label: str
    score: float
    box: Box


@dataclass(frozen=True)
class Inference:
    """What `detect` may return instead of a bare sequence: `latency_ms` for a simulated model."""

    detections: Sequence[Detection]
    latency_ms: float | None = None


class VisionModel(Protocol):
    """
    Any object with these, sync: `identity`, the closed set `labels` the model can say, and
    ``detect(frame) -> Sequence[Detection] | Inference``. A cloud or NPU adapter that is
    asynchronous wraps its call (`docs/spec/vision.md` §3).
    """

    identity: ModelIdentity
    labels: Collection[str]

    def detect(self, frame: Frame) -> Sequence[Detection] | Inference: ...


@dataclass(frozen=True)
class Rejected:
    """A frame the perception layer refused: `reason` is one of `REJECTED`; `detail` is for people."""

    reason: str
    detail: str = ""


def _real(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _box_problem(box: Any) -> str | None:
    if not isinstance(box, tuple | list) or len(box) != 4 or not all(_real(v) for v in box):
        return f"box must be four numbers (x0, y0, x1, y1), got {box!r}"
    x0, y0, x1, y1 = box
    if not all(math.isfinite(v) and 0.0 <= v <= 1.0 for v in box):
        return f"box {tuple(box)!r} has a coordinate outside [0, 1]"
    if not (x0 < x1 and y0 < y1):
        return f"box {tuple(box)!r} is not a rectangle (needs x0 < x1 and y0 < y1)"
    return None


def sanitize(labels: Collection[str], raw: Any) -> tuple[tuple[Detection, ...], Rejected | None]:
    """
    The domain check on a model's answer: ``(detections, None)`` when it is well formed,
    ``((), Rejected("garbage", why))`` when any part of it is not.

    A NaN, infinite or out-of-[0, 1] score is *well formed*: it is kept, and the fact built
    from it is one the gate refuses (`facts.frame_value`). Everything else that is not a
    `Detection` of a known label with a real score and a proper box rejects the frame.
    """
    if isinstance(raw, Inference):
        raw = raw.detections
    if not isinstance(raw, list | tuple):
        return (), Rejected("garbage", f"the model returned {type(raw).__name__}, not a list")
    if len(raw) > MAX_DETECTIONS:
        return (), Rejected("garbage", f"{len(raw)} detections in one frame (> {MAX_DETECTIONS})")
    kept: list[Detection] = []
    for index, item in enumerate(raw):
        where = f"detection {index}"
        if not isinstance(item, Detection):
            return (), Rejected("garbage", f"{where} is a {type(item).__name__}, not a Detection")
        if not isinstance(item.label, str) or item.label not in labels:
            return (), Rejected("garbage", f"{where} has a label outside the model's label set")
        if not _real(item.score):
            return (), Rejected("garbage", f"{where} has a score that is not a number")
        problem = _box_problem(item.box)
        if problem is not None:
            return (), Rejected("garbage", f"{where}: {problem}")
        kept.append(item)
    return tuple(kept), None
