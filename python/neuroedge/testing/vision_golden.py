"""
The inference golden: "the model sees the same on every target" (TSK-V1b-04, RFC-0012 §3f clause 2, §9.6).

Two claims make a vision gate equivalent across targets, and they are proved apart. That the
**gate** decides alike from the same `perception` events is the replay of `verify`. That the
**model** sees alike is this module: for each model SHA-256, what it detected on each frame on the
host — the *golden* — and a check that what a target's inference gives is the same within the
board's `vision_in.tolerance = {score_abs, box_iou_min}` (`board.v1`, hard-capped at 0.05 / 0.8 so
a board cannot declare its way out of the check).

    golden = record_golden(model, frames)            # on the host, once
    golden.save("fixtures/vision/golden/scene.json")
    ...
    assert_inference_matches(golden, model.identity, observed, tolerance_of(board))

Format (`neuroedge.vision-golden/v1`, JSON): the model's identity and, per frame **content hash**
(`vision_ref.sha256`, never pixels), the detections `{label, score, box}` it produced. A golden
belongs to one model: comparing another model's inference against it is refused
(`VerificationError`), not silently done.

**The matching rule.** Per frame, the target's detections are paired one-to-one with the golden's:

1. only detections of the **same label** can pair, and only when their boxes overlap with
   IoU ≥ `box_iou_min`;
2. all such candidate pairs are taken in order of highest IoU, then smallest score difference,
   then position, each detection used at most once (a deterministic greedy matching);
3. every paired detection must then satisfy |score − golden score| ≤ `score_abs` (both bounds
   inclusive, up to 1e-9 of float noise);
4. a golden detection left unpaired is **missing**, a target detection left unpaired is **extra**.

Any of these — a missing detection, an extra one, a score or box outside tolerance, a frame the
target did not infer or a frame the golden does not know — is a difference, and the first one
raises `SafetyRegressionError` (NE4002) naming the frame and the detection. An extra detection is
a difference even with a low score: a target that sees something the host does not changes the
`confidence` fact the gate reads. The comparison is strict; there is no score floor.

What this does **not** do: it runs no model. On `sim` and `linux` the model runs on the host CPU, so
the check there proves the frames and the machinery agree; it bites when a target runs the model
with another runtime or on other silicon (an NPU, TSK-V1b-05; `esp32s3`, TSK-I3a) and hands its
detections over in this format (`InferenceGolden.load`).
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..errors import BoardCapabilityError, SafetyRegressionError, VerificationError
from ..perception.vision import (
    Detection,
    Frame,
    Inference,
    ModelIdentity,
    VisionModel,
    VisionUnavailable,
    sanitize,
)
from ..perception.vision.model import SHA256

GOLDEN_FORMAT = "neuroedge.vision-golden/v1"
# The hard ceiling `board.v1` puts on `vision_in.tolerance` (RFC-0012 §3a); the check refuses a
# looser one even if a board somehow carried it, so the equivalence cannot be emptied.
MAX_SCORE_ABS = 0.05
MIN_BOX_IOU = 0.8

Box = tuple[float, float, float, float]
# Float noise only: 0.9 - 0.87 is 0.030000000000000027, and a difference of exactly score_abs passes.
_EPS = 1e-9


@dataclass(frozen=True)
class Tolerance:
    """How far a target's inference may differ from the golden: `board.v1` `vision_in.tolerance`."""

    score_abs: float
    box_iou_min: float

    def __post_init__(self) -> None:
        for name, value in (("score_abs", self.score_abs), ("box_iou_min", self.box_iou_min)):
            if (
                isinstance(value, bool)
                or not isinstance(value, int | float)
                or not math.isfinite(value)
            ):
                raise ValueError(f"tolerance {name} must be a finite number, got {value!r}")
        if not 0.0 <= self.score_abs <= MAX_SCORE_ABS or not MIN_BOX_IOU <= self.box_iou_min <= 1.0:
            raise ValueError(
                f"tolerance {self!r} is outside the hard ceiling of board.v1 "
                f"(score_abs <= {MAX_SCORE_ABS}, box_iou_min >= {MIN_BOX_IOU})"
            )


def tolerance_of(board: Any) -> Tolerance | None:
    """The tolerance of a `BoardProfile`'s `vision_in`, or None for a board with no camera."""
    declared = board.capabilities.get("vision_in")
    if declared is None:
        return None
    try:
        return Tolerance(
            float(declared["tolerance"]["score_abs"]), float(declared["tolerance"]["box_iou_min"])
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise BoardCapabilityError(
            where=f"board {board.id} vision_in.tolerance",
            why=f"the camera's tolerance is missing or beyond the hard ceiling: {exc}",
            how="declare tolerance = { score_abs <= 0.05, box_iou_min >= 0.8 } (RFC-0012 §3a)",
        ) from exc


# --- the golden ------------------------------------------------------------------------------


def _detection_json(d: Detection) -> dict[str, Any]:
    return {"label": d.label, "score": d.score, "box": list(d.box)}


def _detection_of(item: Mapping[str, Any]) -> Detection:
    return Detection(item["label"], item["score"], tuple(item["box"]))


@dataclass(frozen=True)
class InferenceGolden:
    """What `model` detected on the host, per frame content hash."""

    model: ModelIdentity
    frames: Mapping[str, tuple[Detection, ...]]

    def to_document(self) -> dict[str, Any]:
        return {
            "$format": GOLDEN_FORMAT,
            "model": self.model.to_json(),
            "frames": {
                digest: [_detection_json(d) for d in self.frames[digest]]
                for digest in sorted(self.frames)
            },
        }

    def save(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_document(), indent=2) + "\n", encoding="utf-8")

    @classmethod
    def from_document(cls, document: Any, where: str = "<golden>") -> InferenceGolden:
        def bad(why: str) -> VerificationError:
            return VerificationError(
                where=where,
                why=f"not an inference golden: {why}",
                how=f'a golden is {{"$format": "{GOLDEN_FORMAT}", "model": {{name, sha256}}, '
                '"frames": {<frame sha256>: [{label, score, box}]}}',
            )

        if not isinstance(document, dict) or document.get("$format") != GOLDEN_FORMAT:
            raise bad(f"$format must be {GOLDEN_FORMAT!r}")
        try:
            model = ModelIdentity(document["model"]["name"], document["model"]["sha256"])
            frames: dict[str, tuple[Detection, ...]] = {}
            for digest, items in document["frames"].items():
                if not SHA256.fullmatch(digest) or not isinstance(items, list):
                    raise bad(f"frame key {digest!r} is not a lowercase SHA-256 of a list")
                detections = tuple(_detection_of(item) for item in items)
                _, rejected = sanitize({d.label for d in detections}, list(detections))
                if rejected is not None or any(
                    not math.isfinite(d.score) or not 0.0 <= d.score <= 1.0 for d in detections
                ):
                    raise bad(
                        f"frame {digest[:12]}: {rejected.detail if rejected else 'a score outside [0, 1]'}"
                    )
                frames[digest] = detections
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise bad(f"{type(exc).__name__}: {exc}") from exc
        if not frames:
            raise bad("it has no frame")
        return cls(model, frames)

    @classmethod
    def load(cls, path: str | Path) -> InferenceGolden:
        target = Path(path)
        try:
            document = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise VerificationError(
                where=str(target),
                why=f"cannot read the golden: {type(exc).__name__}: {exc}",
                how="record it with record_golden(model, frames).save(path)",
            ) from exc
        return cls.from_document(document, str(target))


def infer(model: VisionModel, frames: Sequence[Frame]) -> dict[str, tuple[Detection, ...]]:
    """
    Run `model` on `frames`: detections per frame content hash. A frame the model cannot read —
    it raises, answers garbage — is `VisionUnavailable`: an inference with a hole in it is not
    an inference. Two frames with the same bytes must get the same answer.
    """
    seen: dict[str, tuple[Detection, ...]] = {}
    for frame in frames:
        try:
            raw = model.detect(frame)
        except VisionUnavailable:
            raise
        except Exception as exc:
            raise VisionUnavailable(
                where=f"vision model {model.identity.name} on frame {frame.seq}",
                why=f"the model failed: {type(exc).__name__}",
                how="an inference cannot be recorded or compared with a hole in it",
            ) from exc
        detections, rejected = sanitize(
            model.labels, raw.detections if isinstance(raw, Inference) else raw
        )
        if rejected is not None:
            raise VisionUnavailable(
                where=f"vision model {model.identity.name} on frame {frame.seq}",
                why=f"the model's answer is not well formed: {rejected.detail}",
                how="an inference cannot be recorded or compared with a hole in it",
            )
        digest = frame.ref.sha256
        if digest in seen and seen[digest] != detections:
            raise VisionUnavailable(
                where=f"vision model {model.identity.name} on frame {frame.seq}",
                why="two frames with the same bytes got different detections: the model is not deterministic",
                how="a golden needs a model that answers the same on the same frame",
            )
        seen[digest] = detections
    return seen


def record_golden(model: VisionModel, frames: Sequence[Frame]) -> InferenceGolden:
    """The golden of `model` on `frames`, recorded on this host."""
    observed = infer(model, frames)
    if not observed:
        raise VisionUnavailable(
            where=f"vision model {model.identity.name}",
            why="no frame to record a golden from",
            how="pass the frames of a scene",
        )
    for detections in observed.values():
        if any(not math.isfinite(d.score) or not 0.0 <= d.score <= 1.0 for d in detections):
            raise VisionUnavailable(
                where=f"vision model {model.identity.name}",
                why="a score outside [0, 1] cannot be a golden",
                how="fix the model: a golden is the reference every target is held to",
            )
    return InferenceGolden(model.identity, observed)


# --- the comparison --------------------------------------------------------------------------


def iou(a: Box, b: Box) -> float:
    """Intersection over union of two `(x0, y0, x1, y1)` boxes; 0 when they do not overlap."""
    width = min(a[2], b[2]) - max(a[0], b[0])
    height = min(a[3], b[3]) - max(a[1], b[1])
    if width <= 0 or height <= 0:
        return 0.0
    inter = width * height
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


@dataclass(frozen=True)
class InferenceDifference:
    frame: str  # the frame's content hash
    where: str
    why: str

    def __str__(self) -> str:
        return f"frame {self.frame[:12]} {self.where}: {self.why}"


def _describe(d: Detection) -> str:
    return f"{d.label} {d.score:.4f} at {tuple(round(v, 4) for v in d.box)}"


def match_detections(
    golden: Sequence[Detection], observed: Sequence[Detection], tolerance: Tolerance
) -> tuple[list[tuple[int, int]], list[int], list[int]]:
    """
    ``(pairs, missing, extra)`` of indices into `golden` and `observed`: the one-to-one matching
    of the module docstring. Pairing looks at label and box only; the score is judged after.
    """
    candidates = sorted(
        (-overlap, abs(g.score - o.score), gi, oi)
        for gi, g in enumerate(golden)
        for oi, o in enumerate(observed)
        if g.label == o.label and (overlap := iou(g.box, o.box)) >= tolerance.box_iou_min - _EPS
    )
    used_g: set[int] = set()
    used_o: set[int] = set()
    pairs: list[tuple[int, int]] = []
    for _, _, gi, oi in candidates:
        if gi not in used_g and oi not in used_o:
            used_g.add(gi)
            used_o.add(oi)
            pairs.append((gi, oi))
    missing = [gi for gi in range(len(golden)) if gi not in used_g]
    extra = [oi for oi in range(len(observed)) if oi not in used_o]
    return sorted(pairs), missing, extra


def compare_inference(
    golden: InferenceGolden,
    model: ModelIdentity,
    observed: Mapping[str, Sequence[Detection]],
    tolerance: Tolerance,
) -> list[InferenceDifference]:
    """
    Every difference between a target's inference and the golden, in frame-hash order. Refused
    (`VerificationError`) when `model` is not the model the golden was recorded for.
    """
    if model != golden.model:
        raise VerificationError(
            where=f"inference of {model.name} ({model.sha256[:12]})",
            why=f"the golden is for {golden.model.name} ({golden.model.sha256[:12]}): another "
            "model's detections are not evidence about this one",
            how="record a golden for this model's SHA-256 on the host, and compare against that",
        )
    found: list[InferenceDifference] = []
    for digest in sorted(set(golden.frames) | set(observed)):
        if digest not in observed:
            found.append(InferenceDifference(digest, "frame", "the target did not infer it"))
            continue
        if digest not in golden.frames:
            found.append(InferenceDifference(digest, "frame", "the golden has no such frame"))
            continue
        want, got = golden.frames[digest], tuple(observed[digest])
        pairs, missing, extra = match_detections(want, got, tolerance)
        for gi, oi in pairs:
            diff = abs(want[gi].score - got[oi].score)
            if not diff <= tolerance.score_abs + _EPS:
                found.append(
                    InferenceDifference(
                        digest,
                        f"detection {gi} ({want[gi].label})",
                        f"score {got[oi].score:.4f} differs from the golden {want[gi].score:.4f} "
                        f"by {diff:.4f} > score_abs {tolerance.score_abs}",
                    )
                )
        for gi in missing:
            near = max(
                (iou(want[gi].box, o.box) for o in got if o.label == want[gi].label), default=0.0
            )
            found.append(
                InferenceDifference(
                    digest,
                    f"detection {gi} ({want[gi].label})",
                    f"missing: {_describe(want[gi])} has no detection of the same label with "
                    f"IoU >= {tolerance.box_iou_min} (best IoU {near:.4f})",
                )
            )
        for oi in extra:
            found.append(
                InferenceDifference(
                    digest,
                    f"extra detection {oi}",
                    f"the golden has nothing for {_describe(got[oi])}",
                )
            )
    return found


def assert_inference_matches(
    golden: InferenceGolden,
    model: ModelIdentity,
    observed: Mapping[str, Sequence[Detection]],
    tolerance: Tolerance,
    label: str = "target",
) -> None:
    """Raise `SafetyRegressionError` (NE4002) naming the first difference; return when none."""
    found = compare_inference(golden, model, observed, tolerance)
    if found:
        more = f" (+{len(found) - 1} more)" if len(found) > 1 else ""
        raise SafetyRegressionError(
            where=f"inference of {model.name} ({model.sha256[:12]}) on {label}",
            why=f"{found[0]}{more}",
            how="the model sees differently on this target than on the host: fix the conversion or "
            f"runtime, or — if the board really needs more room — its vision_in.tolerance "
            f"(score_abs <= {MAX_SCORE_ABS}, box_iou_min >= {MIN_BOX_IOU}, RFC-0012 §3a)",
        )


def check_model(
    golden: InferenceGolden,
    model: VisionModel,
    frames: Sequence[Frame],
    tolerance: Tolerance,
    label: str = "target",
) -> None:
    """Run `model` on `frames` and `assert_inference_matches` against the golden."""
    assert_inference_matches(golden, model.identity, infer(model, frames), tolerance, label)
