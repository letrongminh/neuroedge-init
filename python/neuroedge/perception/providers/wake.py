"""
Wake-word detectors — frames in, ``(word, score)`` out (TSK-I4-01, FR-PER-01, Q-7).

The contract: `detect(frame: AudioFrame) -> tuple[str, float] | None` — the word
and its score when this frame finished a detection at or above the configured
threshold, None otherwise. A detector reads frames and answers; it never opens a
turn itself (the conversation state machine does, on `wake_word_detected`), never
touches a gate or a pin.

Two providers, chosen in `[wake_word]` (`config.py`):

* ``provider = "openwakeword"`` — `OpenWakeWord` (Apache-2.0) with a model **of
  your own** (`openwakeword.py` holds the adapter). Every pre-trained model
  openWakeWord publishes is CC BY-NC-SA 4.0, so NeuroEdge ships none and never
  calls its downloader (Q-45): `model` is a path on this machine that must exist;
* ``provider = "python:pkg.mod:factory"`` — an adapter of your own, handed this
  config (FR-MDL-08).

`FakeWakeWordDetector` (`fake.py`) is scripted, model-free and deterministic: the
tests and a keyless trial use it.
"""

from __future__ import annotations

import math
from typing import Any, Protocol

from ...errors import PerceptionUnavailableError
from ...hal.audio import SAMPLE_WIDTH, AudioFrame, resample
from .config import WakeWordConfig

# openWakeWord's models run at 16 kHz mono 16-bit, one 80 ms window (1280 samples)
# per `predict` call.
WAKE_RATE_HZ = 16_000
WAKE_WINDOW = 1280


class WakeWordDetector(Protocol):
    """One frame in; ``(word, score)`` when the wake word was heard, else None."""

    def detect(self, frame: AudioFrame) -> tuple[str, float] | None: ...


def _score(value: Any) -> float:
    """A model's score as a finite float in [0, 1], or a three-part error."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = math.nan
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        raise PerceptionUnavailableError(
            where="wake word -> model.predict()",
            why=f"the detector returned score {value!r}, not a finite number in [0, 1]",
            how="fix the wake-word model: openWakeWord models return a confidence per model name",
        )
    return number


class OpenWakeWord:
    """
    openWakeWord (`openwakeword.Model`) with a user-supplied model file. Frames of
    any board rate are resampled to 16 kHz and fed in 80 ms windows; a window whose
    highest score reaches `threshold` returns ``(word, score)``. A score outside
    [0, 1] or an answer that is not a mapping of names to scores is an error, never
    a silent "not detected".
    """

    name = "openwakeword"

    def __init__(self, model: Any, *, threshold: float, word: str) -> None:
        self.model = model
        self.threshold = threshold
        self.word = word
        self._buffer = bytearray()

    @classmethod
    def from_config(cls, config: WakeWordConfig) -> OpenWakeWord:
        try:
            import openwakeword
        except ImportError as exc:
            raise PerceptionUnavailableError(
                where=f"{config.where} provider",
                why="the `openwakeword` package is not installed, and provider = "
                '"openwakeword" needs it',
                how="pip install 'neuroedge[wake]' (Apache-2.0 code; the model is yours), or "
                'write provider = "python:my_wake.adapter:make"',
            ) from exc
        path = config.path
        framework = "tflite" if str(path).endswith(".tflite") else "onnx"
        try:
            model = openwakeword.Model(wakeword_models=[str(path)], inference_framework=framework)
        except Exception as exc:
            raise PerceptionUnavailableError(
                where=f"{config.where} model",
                why=f"openWakeWord could not load {path}: {type(exc).__name__}: {exc}",
                how="check the model file is a complete openWakeWord model of that framework",
            ) from exc
        return cls(model, threshold=config.threshold, word=config.word)

    def detect(self, frame: AudioFrame) -> tuple[str, float] | None:
        pcm = frame.pcm
        if frame.sample_rate_hz != WAKE_RATE_HZ:
            try:
                pcm = resample(pcm, frame.sample_rate_hz, WAKE_RATE_HZ)
            except ValueError as exc:
                raise PerceptionUnavailableError(
                    where="wake word -> audio.in frame",
                    why=f"{exc} — the frame cannot be brought to openWakeWord's 16 kHz",
                    how="fix the source of frames: audio.in of a board runs in 8–96 kHz "
                    "(hal/audio.py)",
                ) from None
        self._buffer += pcm
        size = WAKE_WINDOW * SAMPLE_WIDTH
        hit: tuple[str, float] | None = None
        while len(self._buffer) >= size:
            window = bytes(self._buffer[:size])
            del self._buffer[:size]
            scores = self.model.predict(window)
            if not isinstance(scores, dict):
                raise PerceptionUnavailableError(
                    where="wake word -> model.predict()",
                    why=f"the model answered {type(scores).__name__}, not a name-to-score mapping",
                    how="fix the wake-word model or its adapter (perception/providers/wake.py)",
                )
            best = max((_score(value) for value in scores.values()), default=0.0)
            if best >= self.threshold:
                hit = (self.word, best)
        return hit


def make_wake_word(config: WakeWordConfig, root: Any = None) -> Any:
    """The detector `config` names — a custom adapter's factory is called with `config`."""
    if config.adapter is None:
        return OpenWakeWord.from_config(config)
    from ...models.providers.common import call_adapter

    return call_adapter(
        config,
        root,
        table="wake_word",
        accepts=lambda provider: callable(getattr(provider, "detect", None)),
        expected="an object with a detect() method",
        how="return an object with detect(frame) -> (word, score) | None "
        "(perception/providers/wake.py)",
    )
