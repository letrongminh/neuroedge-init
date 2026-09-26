"""
Fake speech providers — no network, no key, deterministic (TSK-S3-13).

CI never calls a real STT or TTS: the tests use these. So can a person trying
the voice path without a key, through the adapter mechanism of `[stt]` / `[tts]`:

    [stt]
    provider = "python:neuroedge.perception.providers.fake:stt"
    [stt.options]
    transcripts = ["mở cửa", ""]   # what turn 1, turn 2, … said ("" = heard nothing)
    latency_ms  = 300              # how long each answer takes, on the session's clock

    [tts]
    provider = "python:neuroedge.perception.providers.fake:tts"
    [tts.options]
    ms_per_char = 60               # how long a sentence plays

`latency_ms` is simulated time (`base.py`): the fake never sleeps.
"""

from __future__ import annotations

import math
from array import array
from collections.abc import Callable, Collection, Mapping, Sequence
from typing import Any

from ...hal.audio import MAX_REPLY_MS, rate_ok, samples_pcm
from .base import AudioClip, Speech, SpeechUnavailable, Transcript

MAX_MS_PER_CHAR = 1000.0


def _ms(value: Any, name: str, *, most: float = math.inf) -> float:
    """`value` as a finite number of ms in [0, most], or `ValueError` naming `name`."""
    if (
        isinstance(value, bool)
        or not isinstance(value, int | float)
        or not math.isfinite(value)
        or not 0 <= value <= most
    ):
        bound = "" if most == math.inf else f" and at most {most:g}"
        raise ValueError(f"{name} must be a finite number of ms ≥ 0{bound}, not {value!r}")
    return float(value)


class FakeSpeechToText:
    """
    `transcripts`: a list (the n-th request gets the n-th, then ``""``), a mapping
    turn → text, or a function of the clip. `fail`: True, or the turns whose
    request fails as an unreachable provider would.
    """

    name = "fake"
    model = "fake-stt"

    def __init__(
        self,
        transcripts: Sequence[str] | Mapping[int, str] | Callable[[AudioClip], str] = (),
        *,
        latency_ms: float = 100.0,
        fail: bool | Collection[int] = False,
    ) -> None:
        self.transcripts = transcripts
        self.latency_ms = _ms(latency_ms, "latency_ms")
        self.fail = fail
        self.clips: list[AudioClip] = []

    def _failing(self, turn: int) -> bool:
        return self.fail is True or (not isinstance(self.fail, bool) and turn in self.fail)

    def transcribe(self, clip: AudioClip) -> Transcript:
        self.clips.append(clip)
        if self._failing(clip.turn):
            raise SpeechUnavailable(
                where="STT(fake)",
                why="the fake provider is set to fail — check the network and base_url",
                how="check the network and base_url",
                role="stt",
                latency_ms=self.latency_ms,
            )
        source = self.transcripts
        if callable(source):
            text = source(clip)
        elif isinstance(source, Mapping):
            text = source.get(clip.turn, "")
        else:
            index = len(self.clips) - 1
            text = source[index] if index < len(source) else ""
        return Transcript(text, latency_ms=self.latency_ms)


class FakeTextToSpeech:
    """A quiet tone, `ms_per_char` per character of the sentence, at `sample_rate_hz`."""

    name = "fake"
    model = "fake-tts"

    def __init__(
        self,
        *,
        ms_per_char: float = 60.0,
        sample_rate_hz: int = 16000,
        latency_ms: float = 0.0,
        fail: bool = False,
    ) -> None:
        self.ms_per_char = _ms(ms_per_char, "ms_per_char", most=MAX_MS_PER_CHAR)
        if not rate_ok(sample_rate_hz):
            raise ValueError(f"sample_rate_hz must be 8000–96000, not {sample_rate_hz!r}")
        self.sample_rate_hz = sample_rate_hz
        self.latency_ms = _ms(latency_ms, "latency_ms")
        self.fail = fail
        self.texts: list[str] = []

    def synthesize(self, text: str) -> Speech:
        self.texts.append(text)
        if self.fail:
            raise SpeechUnavailable(
                where="TTS(fake)",
                why="the fake provider is set to fail — check the network and base_url",
                how="check the network and base_url",
                role="tts",
                latency_ms=self.latency_ms,
            )
        # Never more than a reply may hold (plus a frame, so the session's cap still shows).
        length = min(len(text) * self.ms_per_char, MAX_REPLY_MS + 20)
        return Speech(
            tone(length, self.sample_rate_hz), self.sample_rate_hz, latency_ms=self.latency_ms
        )


def tone(ms: float, sample_rate_hz: int, hz: float = 440.0, dbfs: float = -20.0) -> bytes:
    """`ms` of a sine at `dbfs`: audible in the output WAV, the same bytes every run."""
    count = int(ms * sample_rate_hz / 1000)
    amplitude = 32767 * 10 ** (dbfs / 20)
    step = 2 * math.pi * hz / sample_rate_hz
    return samples_pcm(array("h", (int(amplitude * math.sin(step * i)) for i in range(count))))


def _options(config: Any, allowed: dict[str, type | tuple[type, ...]]) -> dict[str, Any]:
    options = dict(config.options)
    unknown = sorted(set(options) - set(allowed))
    if unknown:
        raise ValueError(f"unknown options {unknown}; the fake takes {sorted(allowed)}")
    for key, kinds in allowed.items():
        if key in options and (
            isinstance(options[key], bool) != (kinds is bool) or not isinstance(options[key], kinds)
        ):
            raise ValueError(f"option {key!r} must be {kinds}, not {options[key]!r}")
    return options


def stt(config: Any) -> FakeSpeechToText:
    """Factory for ``provider = "python:neuroedge.perception.providers.fake:stt"``."""
    options = _options(config, {"transcripts": list, "latency_ms": (int, float), "fail": bool})
    transcripts = options.get("transcripts", [])
    if not all(isinstance(text, str) for text in transcripts):
        raise ValueError("option 'transcripts' must be a list of strings")
    return FakeSpeechToText(
        transcripts, latency_ms=options.get("latency_ms", 100.0), fail=options.get("fail", False)
    )


def tts(config: Any) -> FakeTextToSpeech:
    """Factory for ``provider = "python:neuroedge.perception.providers.fake:tts"``."""
    options = _options(
        config,
        {"ms_per_char": (int, float), "latency_ms": (int, float), "fail": bool},
    )
    return FakeTextToSpeech(
        ms_per_char=options.get("ms_per_char", 60.0),
        latency_ms=options.get("latency_ms", 0.0),
        fail=options.get("fail", False),
    )
