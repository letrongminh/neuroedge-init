"""
The contract of a speech provider (TSK-S3-13, FR-MDL-09, Q-12).

Two roles, each any object with one method, sync or async:

* **STT** — ``transcribe(clip: AudioClip) -> str | Transcript``: the words of
  one turn's audio. ``""`` means the provider heard nothing (T06 of
  docs/spec/voice_fsm.md §4: no action, at most `max_reprompts` reprompts).
* **TTS** — ``synthesize(text: str) -> Speech``: the audio of one sentence the
  device says.

A provider that cannot answer **raises** — `SpeechUnavailable` for a failure it
understands; any other exception is taken the same way. The voice driver turns
every failure into the degraded path of voice_fsm.md §7: the offline line for
STT, a stream that ends with ``error`` for TTS. It never crashes the session,
never invents a transcript, and a transcript only ever reaches a pin the way a
typed line does — command grammar or System 2, `c.do()`, the gate.

`latency_ms` on a result (or on `SpeechUnavailable`) is for simulated providers:
how long the call took on the session's clock. Unset, the driver times the call.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Awaitable
from dataclasses import dataclass
from typing import Protocol

from ...errors import PerceptionUnavailableError
from ...hal.audio import SAMPLE_WIDTH, duration_ms, pcm_digest, wav_bytes

# A transcript is words. More than this from one turn (≤ 120 s of audio) is a
# provider looping, not speech (Whisper does this on noise).
MAX_TRANSCRIPT_CHARS = 4000


@dataclass(frozen=True)
class AudioClip:
    """One turn's audio, sent to STT when the turn ends (T04). Mono 16-bit PCM."""

    pcm: bytes
    sample_rate_hz: int
    turn: int

    @property
    def duration_ms(self) -> int:
        return duration_ms(self.pcm, self.sample_rate_hz)

    @property
    def sha256(self) -> str:
        return pcm_digest(self.pcm)

    def wav(self) -> bytes:
        return wav_bytes(self.pcm, self.sample_rate_hz)


@dataclass(frozen=True)
class Transcript:
    text: str
    latency_ms: float | None = None


@dataclass(frozen=True)
class Speech:
    """Synthesised audio: 16-bit PCM, `channels` interleaved, at `sample_rate_hz`."""

    pcm: bytes
    sample_rate_hz: int
    channels: int = 1
    sample_width: int = SAMPLE_WIDTH
    latency_ms: float | None = None


class SpeechToText(Protocol):
    def transcribe(self, clip: AudioClip) -> str | Transcript | Awaitable[str | Transcript]: ...


class TextToSpeech(Protocol):
    def synthesize(self, text: str) -> Speech | Awaitable[Speech]: ...


class SpeechUnavailable(PerceptionUnavailableError):
    """
    A speech provider could not answer. `role` is ``"stt"`` or ``"tts"``;
    `called` is False when it gave up before any network call (key not set).
    Same stable code as its parent (NE5001): a subclass, not a new error.
    """

    def __init__(
        self,
        where: str,
        why: str,
        how: str,
        *,
        role: str,
        called: bool = True,
        latency_ms: float | None = None,
    ) -> None:
        self.role = role
        self.called = called
        self.latency_ms = latency_ms
        super().__init__(where=where, why=why, how=how)


# Invisible format characters a transcript may keep: the joiners some scripts and
# emoji need. These four are dropped (soft hyphen, zero-width space, word joiner,
# BOM). Every other format character — bidi overrides that make a console show text
# other than what it holds (U+202E), tag characters that hide text from a person but
# not from a model (U+E0000–U+E007F) — means the transcript is not plain speech.
KEPT_FORMAT = frozenset("\u200c\u200d")
DROPPED_FORMAT = frozenset("\u00ad\u200b\u2060\ufeff")
_REFUSED = {
    "Cc": "control characters",
    "Cs": "a lone surrogate — not a character, and not encodable as UTF-8",
    "Co": "private-use characters",
    "Cn": "unassigned code points",
    "Cf": "invisible format characters (bidi overrides, tags)",
}


def clean_transcript(text: object, where: str) -> str:
    """
    The transcript as the session may use it, or `SpeechUnavailable` when what
    came back is not one: not text; U+FFFD (bytes that were not text); control
    characters but tab and newlines; lone surrogates, which the trace (and
    `--anonymize`'s digest) could not even encode; private-use or unassigned code
    points; format characters but the joiners (`KEPT_FORMAT`); or longer than any
    turn. Whitespace is collapsed; an empty result is a valid answer — nothing was
    heard.
    """

    def garbled(why: str) -> SpeechUnavailable:
        how = "check the STT model and `language` in [stt]"
        return SpeechUnavailable(
            where=where,
            why=f"the transcript is garbled: {why}; the turn was not used — {how}",
            how=how,
            role="stt",
        )

    if not isinstance(text, str):
        raise garbled(f"a {type(text).__name__}, not text")
    if "\ufffd" in text:
        raise garbled("it holds U+FFFD, bytes that were not text")
    for ch in text:
        category = unicodedata.category(ch)
        if category not in _REFUSED or ch in "\t\n\r" or ch in KEPT_FORMAT:
            continue
        if ch in DROPPED_FORMAT:
            continue
        # The character is named by its code point only: never the text around it.
        raise garbled(f"it holds {_REFUSED[category]} (U+{ord(ch):04X})")
    text = "".join(ch for ch in text if ch not in DROPPED_FORMAT)
    text = " ".join(unicodedata.normalize("NFC", text).split())
    if len(text) > MAX_TRANSCRIPT_CHARS:
        raise garbled(f"{len(text)} characters, more than any turn ({MAX_TRANSCRIPT_CHARS})")
    return text


class NoSpeech:
    """
    No `[tts]`: each reply is shown (`tts_stream_start`) and not heard — a stream
    with no audio, which ends at once (`tts_stream_end` ``done``, 0 ms).
    """

    name = "none"
    model = "none"

    def synthesize(self, text: str) -> Speech:
        return Speech(b"", 16000, latency_ms=0.0)
