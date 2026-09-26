"""
Speech providers — STT and TTS (TSK-S3-13, FR-MDL-09, FR-PER-07, Q-12).

The only place a speech endpoint is named. Chosen in `agent.toml` `[stt]` /
`[tts]` (`config.py`), swapped by configuration alone:

* ``provider = "openai"`` (default) — the OpenAI audio API (`openai_audio.py`):
  OpenAI, Groq, faster-whisper, Kokoro… by `base_url`. Standard library only.
* ``provider = "python:pkg.mod:factory"`` — an adapter of your own:
  ``factory(config)`` returns an object with ``transcribe`` (STT) or
  ``synthesize`` (TTS). `fake.py` is one, for tests and for trying voice keyless.

The contract every provider meets, and what a failure becomes: `base.py`.
No SDK and no network until a voice session runs an agent that declares
`[stt]` or `[tts]`: without them `sim` stays on typed input (Q-15, FR-DX-02).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ...models.providers.common import call_adapter
from .base import (
    AudioClip,
    Speech,
    SpeechToText,
    SpeechUnavailable,
    TextToSpeech,
    Transcript,
    clean_transcript,
)
from .config import OPENAI, SpeechConfig, load_speech_configs, parse_speech
from .fake import FakeSpeechToText, FakeTextToSpeech
from .openai_audio import OpenAISpeaker, OpenAITranscriber

__all__ = [
    "OPENAI",
    "AudioClip",
    "FakeSpeechToText",
    "FakeTextToSpeech",
    "OpenAISpeaker",
    "OpenAITranscriber",
    "Speech",
    "SpeechConfig",
    "SpeechToText",
    "SpeechUnavailable",
    "TextToSpeech",
    "Transcript",
    "clean_transcript",
    "load_speech_configs",
    "make_speech",
    "parse_speech",
    "speech_for",
]

METHOD = {"stt": "transcribe", "tts": "synthesize"}


def make_speech(config: SpeechConfig, root: Path | None = None) -> Any:
    """The provider `config` names; a custom adapter's factory is called with `config`."""
    if config.adapter is None:
        return OpenAITranscriber(config) if config.role == "stt" else OpenAISpeaker(config)
    method = METHOD[config.role]
    return call_adapter(
        config,
        root,
        table=config.role,
        accepts=lambda provider: callable(getattr(provider, method, None)),
        expected=f"an object with a {method}() method",
        how=f"return an object with {method}() (perception/providers/base.py)",
    )


def speech_for(manifest: Any) -> tuple[Any, Any]:
    """The agent's (STT, TTS) providers from `[stt]` / `[tts]`; None where it declares none."""
    stt_config, tts_config = load_speech_configs(manifest)
    return tuple(  # type: ignore[return-value]
        None if config is None else make_speech(config, manifest.root)
        for config in (stt_config, tts_config)
    )
