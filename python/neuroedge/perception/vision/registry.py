"""
Which vision model, chosen by configuration alone (TSK-V1b-03, FR-MDL-04, FR-MDL-07).

The same shape as `perception/providers/` for speech: `[vision] provider = …` names a
built-in model (`BUILTIN`) or ``python:pkg.mod:factory`` — an adapter of your own, handed this
`VisionConfig` and its `[vision.options]` (FR-MDL-08). Swapping a model is changing that
line; nothing else — the camera, the facts, the gate — reads it.

Built in today: ``replay`` (`fake.py`, deterministic, for tests and `sim`). A real one — ONNX,
a cloud endpoint, an NPU behind `accel/` (TSK-V1b-05) — is an adapter: the interface is
`model.VisionModel`, and none ships with, or is downloaded by, NeuroEdge.
"""

from __future__ import annotations

import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ...errors import AgentManifestError
from ...models.providers.common import call_adapter
from . import fake
from .config import VisionConfig, parse_vision
from .model import VisionModel

BUILTIN: dict[str, Callable[[VisionConfig], VisionModel]] = {fake.NAME: fake.replay}


def _is_model(candidate: Any) -> bool:
    labels = getattr(candidate, "labels", None)
    return (
        callable(getattr(candidate, "detect", None))
        and hasattr(candidate, "identity")
        and isinstance(labels, (set, frozenset, list, tuple))
        and bool(labels)
        and all(isinstance(label, str) for label in labels)
    )


def make_vision_model(config: VisionConfig, root: Path | None = None) -> VisionModel:
    """The model `config` names; a custom adapter's factory is called with `config`."""
    if config.provider is None:
        raise AgentManifestError(
            where=f"{config.where} provider",
            why="[vision] does not say which model reads the frames",
            how=f'add provider = "replay" (a scripted model) or "python:my_vision.adapter:make" '
            f"for your own; built in: {sorted(BUILTIN)}",
        )
    if config.adapter is None:
        factory = BUILTIN.get(config.provider)
        if factory is None:
            raise AgentManifestError(
                where=f"{config.where} provider",
                why=f"no built-in vision model is named {config.provider!r}; built in: "
                f"{sorted(BUILTIN)}",
                how='use one of them, or provider = "python:pkg.mod:factory" for your own model',
            )
        try:
            made = factory(config)
        except Exception as exc:
            raise AgentManifestError(
                where=f"{config.where} options",
                why=f"the {config.provider!r} model cannot be built: {type(exc).__name__}: {exc}",
                how="check [vision.options] against perception/vision/fake.py",
            ) from exc
        if not _is_model(made):  # a built-in that is not one is a bug, said where it shows
            raise AgentManifestError(
                where=f"{config.where} provider",
                why=f"the built-in {config.provider!r} did not return a vision model",
                how="report this: perception/vision/registry.py",
            )
        return made
    return call_adapter(
        config,
        root,
        table="vision",
        accepts=_is_model,
        expected="a vision model: identity, a non-empty labels set, and detect(frame)",
        how="return an object with identity, labels and detect() (perception/vision/model.py)",
    )


def load_vision_config(manifest: Any) -> VisionConfig | None:
    """The agent's `[vision]`; None for an agent that declares none."""
    document = tomllib.loads(manifest.source.read_text(encoding="utf-8"))
    return parse_vision(document["vision"], manifest.source) if "vision" in document else None


def vision_model_for(manifest: Any) -> tuple[VisionConfig, VisionModel] | None:
    """The agent's `[vision]` and the model it names, or None (no camera facts)."""
    config = load_vision_config(manifest)
    return None if config is None else (config, make_vision_model(config, manifest.root))
