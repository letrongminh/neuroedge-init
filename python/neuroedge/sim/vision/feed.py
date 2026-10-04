"""
Camera to gate: the glue between `vision.in` and the Gate Engine (docs/spec/vision.md §2).

`VisionFeed` owns the camera of a session and the `VisionPipeline` that reads its frames. The
session calls `facts(tree)` just before it evaluates a gate (`Conversation.fact_sources`):

    1. every frame the camera has delivered since the last call goes into the pipeline, in order
       — the model reads it, untrusted, and a jump in the frame numbers restarts the window;
    2. the pipeline judges the facts the gate's tree names, one `vision_fact` event each (labels
       and `vision_ref`, never pixels), and returns the ones it could read;
    3. every vision criterion of the tree that it could **not** read is returned as `None` — a
       fact that is not there. The engine blocks it `criterion_unavailable` instead of asking
       another source (System One would otherwise be asked, and could answer from the person's
       words what only the camera may say).

A camera that cannot deliver (`CameraUnavailable`: gone, stalled, the recording over) writes
`camera_unavailable` and **empties the window**: the facts are unavailable at once, not after the
last good frames age out (RFC-0012 §3e: mất camera ⇒ `criterion_unavailable`). Nothing is carried
over from an earlier frame to cover the failure.

The perception layer is imported inside the methods: `perception` sits above `sim` in the layer
table (`perception/voice_session.py` wraps a `SimSession`), so `sim` may not import it at module
level (`tests/test_architecture_layers.py`).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ...engine.trace_sink import EventLog
from ...engine.verdict import Fact
from ...hal.vision import Camera, CameraUnavailable

EVENT_CAMERA_UNAVAILABLE = "camera_unavailable"


class VisionFeed:
    def __init__(self, camera: Camera, config: Any, model: Any, events: EventLog) -> None:
        from ...perception.vision import VisionPipeline

        self.camera = camera
        self.events = events
        self.pipeline = VisionPipeline(config, model, events=events)
        self.names = frozenset(config.facts)

    def pump(self) -> int:
        """Hand the camera's new frames to the pipeline; how many there were."""
        from ...perception.vision import Frame

        try:
            frames = [
                Frame(f.seq, f.captured_ms, f.pixels, f.width, f.height, f.pixel_format)
                for f in self.camera.read_available()
            ]
        except Exception as error:
            # `CameraUnavailable` is the camera saying so; anything else is a camera that is
            # broken. Both end the same way — no fact, the gate blocks — never a crash that
            # leaves the question of what the last good frames still say.
            why = (
                error.why
                if isinstance(error, CameraUnavailable)
                else (f"the camera failed: {type(error).__name__}")
            )
            self.events.emit(EVENT_CAMERA_UNAVAILABLE, {"reason": why})
            # No window mixes frames from before the camera was lost with ones after it.
            self.pipeline.set_model(self.pipeline.model)
            return 0
        for frame in frames:
            self.pipeline.push(frame)
        return len(frames)

    def facts(self, tree: Mapping[str, Any]) -> dict[str, Fact | None]:
        """The vision facts of `tree`: a `Fact` where read, `None` where not (see the module)."""
        wanted = self.names & {node["criterion"] for node in tree["nodes"]}
        if not wanted:
            return {}  # a gate that asks the camera nothing does not run a model
        self.pump()
        read = self.pipeline.facts_for(tree)
        return {name: read.get(name) for name in sorted(wanted)}

    def close(self) -> None:
        self.camera.close()
