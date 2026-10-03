"""
A scripted vision model — no ML, no network, deterministic (TSK-V1b-03).

CI never runs a real model: the tests, `sim` and the frame-replay Action CI use this. So can a
person trying the vision path without one, through the adapter mechanism of `[vision]`:

    [vision]
    provider = "replay"
    [vision.options]
    name   = "person-det"                      # the identity of the model it stands for
    labels = ["person"]                        # its closed label set (more are read off the script)
    script = { 101 = [ { label = "person", score = 0.93, box = [0.3, 0.5, 0.6, 0.9] } ] }
    latency_ms = 20                            # how long each answer takes, on the session's clock

`script` says what the model sees on the frame with that camera frame number. A frame the
script does not name is **not** "nobody there": the model is unavailable for it, unless
`default = []` says an empty scene is what it should answer. `fail` lists the frame numbers on
which the model raises, as an unreachable one would.

`latency_ms` is simulated time (`model.py`): the fake never sleeps.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable, Collection, Mapping, Sequence
from typing import Any

from .config import VisionConfig
from .model import Detection, Frame, Inference, ModelIdentity, VisionUnavailable

NAME = "replay"


def _detection(item: Any) -> Any:
    """A script entry as a `Detection`: a mapping `{label, score, box}` or one already."""
    if isinstance(item, Mapping):
        return Detection(item["label"], item["score"], tuple(item["box"]))
    return item


class ScriptedVisionModel:
    """
    `script`: a mapping frame number → detections, or a function of the `Frame`. What it holds
    is returned as it is — a test hands it garbage on purpose, `sanitize` is what refuses it.
    `fail`: True, or the frame numbers on which `detect` raises `VisionUnavailable`.
    `default`: what a frame the script does not name sees; None means the model is unavailable.
    """

    def __init__(
        self,
        script: Mapping[int, Any] | Callable[[Frame], Any] = (),  # type: ignore[assignment]
        *,
        labels: Collection[str] = (),
        name: str = "replay",
        sha256: str | None = None,
        latency_ms: float = 10.0,
        fail: bool | Collection[int] = False,
        default: Sequence[Detection] | None = None,
    ) -> None:
        if not isinstance(latency_ms, int | float) or isinstance(latency_ms, bool):
            raise ValueError(f"latency_ms must be a number of ms, not {latency_ms!r}")
        self.script = script if callable(script) else dict(script)
        self.latency_ms = float(latency_ms)
        self.fail = fail
        self.default = default
        seen: set[str] = set()
        if not callable(self.script):
            for value in self.script.values():
                if isinstance(value, list | tuple):
                    seen |= {
                        d["label"] if isinstance(d, Mapping) else getattr(d, "label", "")
                        for d in value
                    }
        self.labels = frozenset(labels) | {s for s in seen if isinstance(s, str) and s}
        digest = sha256 or hashlib.sha256(self._canonical().encode()).hexdigest()
        self.identity = ModelIdentity(name, digest)
        self.frames: list[Frame] = []

    def _canonical(self) -> str:
        """What the model *is*, for an identity when no file gives one."""
        body = (
            "<function>"
            if callable(self.script)
            else {
                str(k): self.script[k]
                if not isinstance(self.script[k], list | tuple)
                else [_detection_json(d) for d in self.script[k]]
                for k in sorted(self.script)
            }
        )
        return json.dumps(
            {"labels": sorted(self.labels), "script": body}, sort_keys=True, default=str
        )

    def _failing(self, seq: int) -> bool:
        return self.fail is True or (not isinstance(self.fail, bool) and seq in self.fail)

    def detect(self, frame: Frame) -> Inference:
        self.frames.append(frame)
        if self._failing(frame.seq):
            raise VisionUnavailable(
                where="vision model (replay)",
                why="the scripted model is set to fail on this frame",
                how="check the model, or remove the frame number from `fail`",
                latency_ms=self.latency_ms,
            )
        if callable(self.script):
            raw = self.script(frame)
        elif frame.seq in self.script:
            raw = self.script[frame.seq]
        elif self.default is not None:
            raw = self.default
        else:
            raise VisionUnavailable(
                where="vision model (replay)",
                why=f"the script has nothing for frame {frame.seq}, and no `default` says an "
                "empty scene is what to answer",
                how="add the frame to `script`, or set `default = []` for an empty scene",
                latency_ms=self.latency_ms,
            )
        return Inference(raw, self.latency_ms)


def _detection_json(item: Any) -> Any:
    if isinstance(item, Mapping):
        return {k: item[k] for k in sorted(item)}
    return {"label": item.label, "score": item.score, "box": list(item.box)}


def replay(config: VisionConfig) -> ScriptedVisionModel:
    """`provider = "replay"`: the model of `[vision.options]` — what the registry calls."""
    opts = config.options
    script = opts.get("script", {})
    if not isinstance(script, Mapping):
        raise ValueError("[vision.options] script must be a table of frame number → detections")
    keyed: dict[int, Any] = {}
    for key, value in script.items():
        try:
            keyed[int(key)] = (
                [_detection(item) for item in value] if isinstance(value, list | tuple) else value
            )
        except (TypeError, ValueError):
            raise ValueError(f"script key {key!r} is not a frame number") from None
    latency = opts.get("latency_ms", 10.0)
    if (
        not isinstance(latency, int | float)
        or isinstance(latency, bool)
        or not math.isfinite(latency)
    ):
        raise ValueError("[vision.options] latency_ms must be a number of ms")
    return ScriptedVisionModel(
        keyed,
        labels=tuple(opts.get("labels", ())),
        name=str(opts.get("name", "replay")),
        sha256=opts.get("sha256"),
        latency_ms=latency,
        fail=tuple(opts.get("fail", ())),
        default=opts.get("default"),
    )
