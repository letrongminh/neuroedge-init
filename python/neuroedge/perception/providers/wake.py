"""
Wake-word detectors — frames in, ``(word, score)`` out (TSK-I4-01, FR-PER-01, Q-7).

The contract: `detect(frame: AudioFrame) -> tuple[str, float] | None` — the word
and its score when this frame finished a detection at or above the configured
threshold, None otherwise. A detector reads frames and answers; it never opens a
turn itself (the conversation state machine does, on `wake_word_detected`), never
touches a gate or a pin. A failure it raises is turned into `wake_word_unavailable`
and the session keeps running: no turn opens from a detector nobody can trust.

Two providers, chosen in `[wake_word]` (`config.py`):

* ``provider = "openwakeword"`` — `OpenWakeWord`, the adapter below, with model
  files **of your own** (`model`, `melspectrogram`, `embedding`). openWakeWord's
  code is Apache-2.0, but every model it publishes is CC BY-NC-SA 4.0 or of
  unestablished licence, so NeuroEdge ships none and **never calls its model
  downloader** (Q-45): all three paths are files on this machine, and a missing
  one is a three-part error before any frame is read;
* ``provider = "python:pkg.mod:factory"`` — an adapter of your own, handed this
  config (FR-MDL-08).

`FakeWakeWordDetector` (`fake.py`) is scripted, model-free and deterministic: the
tests and a keyless trial use it.
"""

from __future__ import annotations

import math
import re
from typing import Any, Protocol

from ...errors import PerceptionUnavailableError
from ...hal.audio import SAMPLE_WIDTH, AudioFrame, resample
from .config import WakeWordConfig

# openWakeWord's models run at 16 kHz mono 16-bit, one 80 ms window (1280 samples)
# per `predict` call. The inference framework is fixed to onnx: `tflite-runtime`
# has no Linux wheels for the Python versions NeuroEdge supports (3.11–3.13).
WAKE_RATE_HZ = 16_000
WAKE_WINDOW = 1280
WAKE_FRAMEWORK = "onnx"


class WakeWordDetector(Protocol):
    """One frame in; ``(word, score)`` when the wake word was heard, else None."""

    def detect(self, frame: AudioFrame) -> tuple[str, float] | None: ...


def _numpy() -> Any:
    """numpy, which openWakeWord models take their samples as (its own dependency)."""
    try:
        import numpy
    except ImportError as exc:
        raise PerceptionUnavailableError(
            where="wake word -> model.predict()",
            why="numpy is not installed, and openWakeWord models take samples as a numpy array",
            how="pip install 'neuroedge[wake]' (it brings numpy and onnxruntime)",
        ) from exc
    return numpy


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


def _name(text: str) -> str:
    """A model name as a comparable word: ``hey_neuro`` and ``Hey Neuro`` are one."""
    return re.sub(r"[^0-9a-z]+", " ", text.lower()).strip()


class OpenWakeWord:
    """
    openWakeWord (`openwakeword.Model`) with model files you supply. Frames of any
    board rate are resampled to 16 kHz and fed in 80 ms windows as the int16 numpy
    arrays `predict` takes; a window whose **configured word's** score reaches
    `threshold` returns ``(word, score)``. Another class scoring high (a multi-class
    model, openWakeWord's own VAD) never opens a turn, and an answer that is not a
    name-to-score mapping, or names no class matching `word`, is an error — never a
    silent "not detected".
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
                how="pip install 'neuroedge[wake]' (Apache-2.0 code; every model file is yours), "
                'or write provider = "python:my_wake.adapter:make"',
            ) from exc
        # Checked here, before Model(): a missing path could send openWakeWord to
        # its downloader, which must never run (its models are CC BY-NC-SA 4.0 or
        # of unestablished licence — Q-45).
        missing = config.missing_models()
        if missing:
            field, path = missing[0]
            raise PerceptionUnavailableError(
                where=f"{config.where} {field}",
                why=f"no wake-word model file at {path}; openWakeWord ships none and its "
                "downloader must never run (every model it publishes is CC BY-NC-SA 4.0 or of "
                "unestablished licence — Q-45)",
                how=f"train or obtain your own {field} model and write {field} = "
                '"models/<file>.onnx" under [wake_word]; NeuroEdge never downloads one',
            )
        try:
            model = openwakeword.Model(
                wakeword_models=[str(config.path)],
                inference_framework=WAKE_FRAMEWORK,
                melspec_model_path=str(config.melspectrogram_path),
                embedding_model_path=str(config.embedding_path),
            )
        except Exception as exc:
            raise PerceptionUnavailableError(
                where=f"{config.where} model",
                why=f"openWakeWord could not load the model files: {type(exc).__name__}: {exc}",
                how="check the three files are complete openWakeWord .onnx models",
            ) from exc
        return cls(model, threshold=config.threshold, word=config.word)

    def _score_for_word(self, scores: dict[str, Any]) -> float:
        """
        The configured word's score — no other class may open a turn, however high
        it scores (another trained word, openWakeWord's own VAD). A model that names
        no class matching `word` is a configuration error, not a detection.
        """
        wanted = _name(self.word)
        names = {_name(str(key)): key for key in scores}
        if wanted in names:
            return _score(scores[names[wanted]])
        raise PerceptionUnavailableError(
            where="wake word -> model.predict()",
            why=f"the model reports {sorted(str(k) for k in scores)}; none is the configured word "
            f"{self.word!r}, so no class may open a turn",
            how="set word to one of those names (the file's name is the default)",
        )

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
            # `predict` takes a numpy int16 array; bytes raise ValueError there.
            scores = self.model.predict(_numpy().frombuffer(window, dtype="int16"))
            if not isinstance(scores, dict):
                raise PerceptionUnavailableError(
                    where="wake word -> model.predict()",
                    why=f"the model answered {type(scores).__name__}, not a name-to-score mapping",
                    how="fix the wake-word model or its adapter (perception/providers/wake.py)",
                )
            best = self._score_for_word(scores)
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
