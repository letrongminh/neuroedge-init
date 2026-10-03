"""
Action CI for frames: record, replay and assert on the verdict sequence (TSK-V1b-04, FR-CI-01→04).

A *scene* is a directory of camera frames with what the model saw on each, the gate they are
judged by and the maker's `[vision]` facts — everything a camera-less CI needs:

    fixtures/vision/stranger-at-door/
        scene.toml           gate = "vision/entry-no-stranger@1.0.0", [context], [vision.zones/facts]
        0001.pgm 0001.json   a frame, and its sidecar: what the (scripted) model saw on it
        0002.pgm 0002.json   …

    from neuroedge.testing.vision import run_scene, record_scene, assert_verdicts

    run = run_scene("fixtures/vision/stranger-at-door")
    assert_verdicts(run, ["BLOCK", "BLOCK", "BLOCK", "BLOCK"], reason="criterion_unavailable")
    assert_replay_matches(run)          # the trace alone gives the same verdicts: no model, no frames

What this is, per component of FR-CI:

* **record** — `run_scene` runs the frames through `VisionPipeline` (the scripted model; no camera,
  no ML) and the Gate Engine, one evaluation per frame, on a virtual clock; `record_scene` writes
  the session as a `trace.v1` file. **No pixels** ever go in it: each frame is a `vision_ref`
  (SHA-256 and size). `raw=True` is the explicit opt-in (NFR-PRIV-03, as `--raw` for text): the
  frames are copied beside the trace, `metadata.raw_capture` is `true` and each `vision_ref` gets
  the `uri` of its copy.
* **replay** — `replay_verdicts` recomputes every verdict of a trace from its recorded `perception`
  events and `gate_facts`, with the gate and nothing else: no model, no frame, no agent. (With an
  agent, `neuroedge replay` / `TracePlayer` do the same and also drive the pins — `player.py`.)
* **assert** — `assert_verdicts`, `assert_replay_matches`; and the golden comparison of
  `golden.py` works on `VisionRun.trace` as on any trace (FR-CI-04).

Everything is a decision the gate made. What the model said is an input, never asserted on (L3).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..engine.decision_tree import compile_tree, walk
from ..engine.gate import ActionContractEngine, GateResult
from ..engine.gate_resolver import GateRegistry, ResolvedGate, resolve_gate_uri
from ..engine.verdict import Fact
from ..errors import AgentManifestError, ReplayError
from ..perception import VirtualClock
from ..perception.vision import (
    EVENT_TYPE,
    Detection,
    Frame,
    ScriptedVisionModel,
    VisionConfig,
    VisionPipeline,
    facts_for_tree,
    parse_vision,
    reading_from_event,
)
from .recorder import TraceRecorder

DEFAULT_STEP_MS = 33.0
SCENE_FILE = "scene.toml"
SCENE_KEYS = ("description", "gate", "action", "step_ms", "context", "vision")
RAW_DIR = "frames"


# --- scenes: frames from files ----------------------------------------------------------------


@dataclass(frozen=True)
class FrameSet:
    """The frames of a directory, and what the scripted model sees on each (by camera frame number)."""

    frames: tuple[Frame, ...]
    detections: dict[int, list[Detection]]


def _bad(where: Path | str, why: str, how: str) -> AgentManifestError:
    return AgentManifestError(where=str(where), why=why, how=how)


def _detections(path: Path) -> list[Detection]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return [Detection(d["label"], d["score"], tuple(d["box"])) for d in raw]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise _bad(
            path,
            f"not a list of {{label, score, box}}: {type(exc).__name__}: {exc}",
            'write [{"label": "person", "score": 0.93, "box": [0.4, 0.5, 0.6, 0.9]}], or [] for an '
            "empty scene",
        ) from exc


def load_frames(directory: str | Path, step_ms: float = DEFAULT_STEP_MS) -> FrameSet:
    """
    Frames from the files of `directory`, in name order (every file but `scene.toml` and `*.json`).
    A numeric stem (`0004.pgm`) is the camera frame number — a missing number is a lost frame — and
    the frame was read at `number × step_ms`; any other name takes the next number. `<stem>.json`
    says what the model saw. **A frame with no sidecar is a model that did not answer**, not an empty
    scene: write `[]` for that.
    """
    root = Path(directory)
    files = sorted(
        p for p in root.iterdir() if p.is_file() and p.name != SCENE_FILE and p.suffix != ".json"
    )
    if not files:
        raise _bad(root, "no frame files in this directory", "put the frames here, one file each")
    frames: list[Frame] = []
    seen: dict[int, list[Detection]] = {}
    seq = 0
    for path in files:
        seq = int(path.stem) if path.stem.isdigit() else seq + 1
        frames.append(Frame(seq, seq * step_ms, path.read_bytes(), pixel_format=path.suffix[1:]))
        sidecar = path.with_suffix(".json")
        if sidecar.is_file():
            seen[seq] = _detections(sidecar)
    return FrameSet(tuple(frames), seen)


@dataclass(frozen=True)
class Scene:
    """A directory of frames with its gate and facts (`scene.toml`)."""

    name: str
    directory: Path
    gate: str
    config: VisionConfig
    frameset: FrameSet
    context: dict[str, Any] = field(default_factory=dict)
    action: str | None = None
    step_ms: float = DEFAULT_STEP_MS
    description: str = ""


def load_scene(directory: str | Path) -> Scene:
    """
    A `Scene` from `directory`: `scene.toml` with `gate` (a `vision/…@x.y.z` of `gates/`), optional
    `action`, `step_ms`, `[context]` (facts that are not vision) and `[vision]` (`zones`, `facts`),
    plus the frame files (`load_frames`).
    """
    root = Path(directory)
    manifest = root / SCENE_FILE
    if not manifest.is_file():
        raise _bad(root, f"no {SCENE_FILE} in this directory", f"add {SCENE_FILE} with gate = …")
    table = tomllib.loads(manifest.read_text(encoding="utf-8"))
    unknown = sorted(set(table) - set(SCENE_KEYS))
    if unknown or not isinstance(table.get("gate"), str):
        raise _bad(
            manifest,
            f"unknown key(s) {unknown}" if unknown else "`gate` is missing",
            f"a scene takes {list(SCENE_KEYS)}; gate names a gate of gates/, e.g. "
            '"vision/entry-no-stranger@1.0.0"',
        )
    step = table.get("step_ms", DEFAULT_STEP_MS)
    if isinstance(step, bool) or not isinstance(step, int | float) or step <= 0:
        raise _bad(manifest, "step_ms must be a positive number", "write step_ms = 33")
    return Scene(
        name=root.name,
        directory=root,
        gate=table["gate"],
        config=parse_vision(table.get("vision", {}), manifest),
        frameset=load_frames(root, float(step)),
        context=dict(table.get("context", {})),
        action=table.get("action"),
        step_ms=float(step),
        description=str(table.get("description", "")),
    )


# --- record ------------------------------------------------------------------------------------


@dataclass
class VisionRun:
    """One scene run: the recorded session and the engine's answers, one per frame."""

    scene: str
    gate: ResolvedGate
    recorder: TraceRecorder
    results: list[GateResult]
    frames: tuple[Frame, ...]

    @property
    def trace(self) -> dict[str, Any]:
        return self.recorder.to_trace()

    @property
    def verdicts(self) -> list[str]:
        return [result.verdict.value for result in self.results]

    @property
    def reasons(self) -> list[str | None]:
        return [None if r.reason is None else r.reason.value for r in self.results]

    def save(self, path: str | Path, *, raw: bool = False) -> dict[str, Any]:
        """
        Validate (the vision lint included) and write the trace to `path`. By default the file holds
        `vision_ref`s only. `raw=True` also copies each frame to `frames/<sha256>.bin` beside the
        trace and records its `uri` — `metadata.raw_capture` says so, so a reader knows.
        """
        target = Path(path)
        if raw:
            folder = target.parent / RAW_DIR
            folder.mkdir(parents=True, exist_ok=True)
            by_hash = {frame.ref.sha256: bytes(frame.pixels) for frame in self.frames}
            for digest, pixels in by_hash.items():
                (folder / f"{digest}.bin").write_bytes(pixels)
            self.recorder.metadata["raw_capture"] = True
            for event in self.recorder.events:
                if event["type"] == EVENT_TYPE:
                    for item in event["data"]["frames"]:
                        item["vision_ref"]["uri"] = f"{RAW_DIR}/{item['vision_ref']['sha256']}.bin"
        return self.recorder.save(target)


def scene_model(scene: Scene) -> ScriptedVisionModel:
    """The scripted model of a scene: what its sidecars say, under the scene's name."""
    labels = {s.label for s in scene.config.facts.values()}
    labels |= {d.label for seen in scene.frameset.detections.values() for d in seen}
    return ScriptedVisionModel(
        scene.frameset.detections, labels=sorted(labels), name=scene.name, latency_ms=10.0
    )


async def arun_scene(
    scene: Scene | str | Path,
    *,
    registry: GateRegistry | None = None,
    session_id: str | None = None,
) -> VisionRun:
    """Run a scene's frames through the pipeline and the gate, one evaluation per frame."""
    scene = scene if isinstance(scene, Scene) else load_scene(scene)
    gate = resolve_gate_uri(f"neuroedge://gates/{scene.gate}", registry=registry)
    frames = scene.frameset.frames
    model = scene_model(scene)
    clock = VirtualClock(frames[0].captured_ms)
    recorder = TraceRecorder(
        clock=clock,
        session_id=session_id or "sess_" + hashlib.sha256(scene.name.encode()).hexdigest()[:8],
        agent_version=f"{scene.name}@0.0.0",
    )
    key = f"{gate.name}"
    engine = ActionContractEngine({key: gate}, events=recorder, clock=clock)
    pipeline = VisionPipeline(scene.config, model, events=recorder)
    results: list[GateResult] = []
    for frame in frames:
        clock.now = max(clock.now, frame.captured_ms)
        pipeline.push(frame)
        if scene.action is not None:
            recorder.emit("action_requested", {"action": scene.action, "arguments": {}})
        facts = pipeline.facts_for(engine.tree(key))
        results.append(await engine.evaluate(key, {**scene.context, **facts}))
    return VisionRun(scene.name, gate, recorder, results, frames)


def run_scene(scene: Scene | str | Path, **kwargs: Any) -> VisionRun:
    """`arun_scene` for synchronous callers (pytest functions, the CLI)."""
    return asyncio.run(arun_scene(scene, **kwargs))


def record_scene(
    scene: Scene | str | Path, out: str | Path, *, raw: bool = False, **kwargs: Any
) -> VisionRun:
    """Run a scene and write its trace to `out` (FR-CI-01). `raw=True` is the explicit opt-in."""
    run = run_scene(scene, **kwargs)
    run.save(out, raw=raw)
    return run


# --- replay ------------------------------------------------------------------------------------


def replay_verdicts(
    trace: Mapping[str, Any], gates: Mapping[str, ResolvedGate] | Sequence[ResolvedGate]
) -> list[tuple[str, str | None]]:
    """
    ``(verdict, reason)`` of every evaluation of `trace`, **recomputed** from its `vision_fact` events
    (labels and frame identities) and the other facts it recorded (`gate_facts`), with `gates` —
    never from a recorded verdict, a frame or a model (FR-CI-02). A vision fact its own labels do not
    support, or that the gate may not use alone, is unavailable, so the recomputed verdict blocks.
    """
    held = list(gates.values()) if isinstance(gates, Mapping) else list(gates)
    by_label = {f"{g.name}@{g.version}": g for g in held}
    out: list[tuple[str, str | None]] = []
    vision: list[tuple[int, dict[str, Any]]] = []
    label: str | None = None
    recorded: dict[str, Any] = {}
    for event in trace.get("events", []):
        kind, data = event["type"], event.get("data", {})
        if kind == EVENT_TYPE:
            vision.append((event["offset_ms"], data))
        elif kind == "gate_evaluation_begin":
            label, recorded = data.get("gate"), {}
        elif kind == "gate_facts":
            recorded = data
        elif kind == "gate_evaluation_result":
            gate = by_label.get(label or "")
            if gate is None:
                raise ReplayError(
                    where=f"trace event gate_evaluation_begin ({label})",
                    why="the trace was decided by a gate that was not given to replay",
                    how="pass every gate the scene uses",
                )
            tree = compile_tree(gate)
            readings = {}
            for offset, vdata in vision:
                reading = reading_from_event(offset, vdata)
                readings[reading.spec.name] = reading
            vision_facts, judged = facts_for_tree(readings, tree)
            facts = {
                name: Fact(
                    entry.get("value"), entry.get("confidence"), entry.get("source", "trace")
                )
                for name, entry in recorded.items()
                if name not in judged and isinstance(entry, dict)
            }
            walked = walk(tree, {**facts, **vision_facts})
            out.append(
                (walked.verdict.value, None if walked.reason is None else walked.reason.value)
            )
            vision, label, recorded = [], None, {}
    return out


# --- assert ------------------------------------------------------------------------------------


def assert_verdicts(
    run: VisionRun, verdicts: Sequence[str], *, reason: str | Sequence[str | None] | None = None
) -> None:
    """
    The verdict sequence of `run` is `verdicts` (one per frame). `reason` — one reason for every
    BLOCK, or a sequence aligned with `verdicts` (None for an ALLOW) — is checked when given.
    """
    if run.verdicts != list(verdicts):
        raise AssertionError(
            f"scene {run.scene!r}: verdicts {run.verdicts}, expected {list(verdicts)}"
        )
    if reason is None:
        return
    expected = (
        [reason if v == "BLOCK" else None for v in verdicts]
        if isinstance(reason, str)
        else list(reason)
    )
    if run.reasons != expected:
        raise AssertionError(f"scene {run.scene!r}: reasons {run.reasons}, expected {expected}")


def assert_replay_matches(run: VisionRun) -> None:
    """
    Replaying `run`'s trace from its perception events gives the verdicts it had live: the FR-CI-02
    promise, without a model or a frame. Raises `AssertionError` naming the first evaluation that differs.
    """
    live = list(zip(run.verdicts, run.reasons, strict=True))
    again = replay_verdicts(run.trace, [run.gate])
    if again != live:
        first = next((i for i, (a, b) in enumerate(zip(live, again, strict=False)) if a != b), 0)
        raise AssertionError(
            f"scene {run.scene!r}: evaluation {first} was {live[first : first + 1]} live and "
            f"{again[first : first + 1]} on replay (of {len(live)} and {len(again)})"
        )


# --- inference golden (TSK-V1b-04, RFC-0012 §3f clause 2) -------------------------------------


def record_scene_golden(scene: Scene | str | Path, out: str | Path | None = None):
    """
    The inference golden of a scene's model on its frames, recorded on this host
    (`vision_golden.py`); written to `out` when given. A scene with a frame the model does not
    answer (no sidecar) has no golden: `VisionUnavailable`.
    """
    from .vision_golden import record_golden

    scene = scene if isinstance(scene, Scene) else load_scene(scene)
    golden = record_golden(scene_model(scene), scene.frameset.frames)
    if out is not None:
        golden.save(out)
    return golden


def check_scene_inference(
    scene: Scene | str | Path, golden: Any, tolerance: Any, label: str = "target"
) -> None:
    """
    Run the scene's model on its frames and hold the result to `golden` within `tolerance` — the
    inference check of one target (`SafetyRegressionError` NE4002 on the first difference).
    `golden` is an `InferenceGolden` or the path of one.
    """
    from .vision_golden import InferenceGolden, check_model

    scene = scene if isinstance(scene, Scene) else load_scene(scene)
    if not isinstance(golden, InferenceGolden):
        golden = InferenceGolden.load(golden)
    check_model(golden, scene_model(scene), scene.frameset.frames, tolerance, label)
