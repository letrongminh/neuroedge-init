"""
Vision perception (TSK-V1b-03, TSK-V1b-08, FR-MDL-04, FR-MDL-07, RFC-0012 §3c–§3e).

A camera's frames go in; typed facts for the gate come out — and the model between them is
**untrusted**: its labels are domain-checked, its confidence is the gate's to threshold
(a `numeric` criterion, Q-54), and anything it fails to give is a fact that is not there, which
blocks. The seam for the camera (`vision.in`) and the whole contract: `docs/spec/vision.md`.

* `model.py` — `VisionModel`, `Frame`, `Detection`, the domain check (`sanitize`)
* `config.py` — `[vision]` of `agent.toml`: model, zones, which label is which fact
* `registry.py` / `fake.py` — the model chosen by configuration alone; a scripted one for CI
* `pipeline.py` — `VisionPipeline`: frames in, `vision_fact` events and engine facts out
* `facts.py` — frame values, the window, the trace event, and its recomputation for replay
"""

from .config import FactSpec, VisionConfig, Zone, parse_vision
from .facts import (
    EVENT_TYPE,
    UNAVAILABLE,
    FactReading,
    LabelRecord,
    Observation,
    engine_fact,
    facts_for_tree,
    frame_value,
    read_fact,
    reading_from_event,
    rebased,
    to_event,
    unpaired,
)
from .fake import ScriptedVisionModel
from .model import (
    MAX_FRAME_AGE_MS,
    PRESENT_SCORE_FLOOR,
    Detection,
    Frame,
    Inference,
    ModelIdentity,
    Rejected,
    VisionModel,
    VisionRef,
    VisionUnavailable,
    identity_of_file,
    sanitize,
)
from .pipeline import VisionPipeline
from .registry import BUILTIN, load_vision_config, make_vision_model, vision_model_for

__all__ = [
    "BUILTIN",
    "EVENT_TYPE",
    "MAX_FRAME_AGE_MS",
    "PRESENT_SCORE_FLOOR",
    "UNAVAILABLE",
    "Detection",
    "FactReading",
    "FactSpec",
    "Frame",
    "Inference",
    "LabelRecord",
    "ModelIdentity",
    "Observation",
    "Rejected",
    "ScriptedVisionModel",
    "VisionConfig",
    "VisionModel",
    "VisionPipeline",
    "VisionRef",
    "VisionUnavailable",
    "Zone",
    "engine_fact",
    "facts_for_tree",
    "frame_value",
    "identity_of_file",
    "load_vision_config",
    "make_vision_model",
    "parse_vision",
    "read_fact",
    "reading_from_event",
    "rebased",
    "sanitize",
    "to_event",
    "unpaired",
    "vision_model_for",
]
