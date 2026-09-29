"""
The live (`--mic`) voice session, built once for `run --mic` and `studio --mic` (TSK-I4-04):
its providers from the agent's `[stt]`, `[tts]` and `[wake_word]`, and its counters.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..errors import AgentManifestError
from ..sim import SimSession
from .providers import load_speech_configs, load_wake_word_config, make_speech, make_wake_word
from .providers.base import NoSpeech
from .voice_session import VirtualClock, VoiceParams, VoiceSession, VoiceTurn


def build_live_voice(
    session: SimSession,
    clock: VirtualClock,
    *,
    on_turn: Callable[[VoiceTurn], None] | None = None,
) -> tuple[VoiceSession, Any, Any, Any]:
    """
    The `VoiceSession` of a live (`--mic`) session and the `[stt]`, `[tts]` and `[wake_word]`
    configs it was built from (the last two may be None). Raises the three-part error when the
    agent declares no `[stt]` (Q-15). Shared by `run --mic` and `studio --mic`.
    """
    manifest = session.manifest
    stt_config, tts_config = load_speech_configs(manifest)
    if stt_config is None:
        raise AgentManifestError(
            where=f"{manifest.source} -> [stt]",
            why="--mic needs a speech-to-text provider, and the agent declares none",
            how="add [stt] with model and api_key_env, or the base_url of a local server "
            '(docs/user/huong-dan.md); or type the command: neuroedge run -c "…" (Q-15)',
        )
    stt = make_speech(stt_config, manifest.root)
    stt_fallback = (
        None if stt_config.fallback is None else make_speech(stt_config.fallback, manifest.root)
    )
    tts = None if tts_config is None else make_speech(tts_config, manifest.root)
    wake_config = load_wake_word_config(manifest)
    wake = None if wake_config is None else make_wake_word(wake_config, manifest.root)
    voice = VoiceSession(
        session,
        clock=clock,
        params=VoiceParams(vad_activation=wake is None),
        stt=stt,
        stt_fallback=stt_fallback,
        stt_label=f"stt ({stt_config.label})",
        stt_fallback_label=(
            f"stt.fallback ({stt_config.fallback.label})"
            if stt_config.fallback is not None
            else "stt.fallback"
        ),
        tts=tts if tts is not None else NoSpeech(),
        wake_word=wake,
        on_turn=on_turn,
    )
    return voice, stt_config, tts_config, wake_config


def count_events(voice: VoiceSession) -> dict[str, int]:
    """The counters of a voice session, from its events (`_summary` and the studio)."""
    events = voice.events
    return {
        "turns": len(voice.turns),
        "barge-in": sum(
            1 for e in events.of_type("tts_stream_end") if e.get("reason") == "barge_in"
        )
        + sum(
            1
            for e in events.of_type("voice_state_changed")
            if e["to"] == "BARGE_IN" and e["from"] == "THINKING"
        ),
        "STT unavailable": len(events.of_type("stt_unavailable")),
        "STT fallback": len(events.of_type("stt_fallback")),
        "TTS unavailable": len(events.of_type("tts_unavailable")),
        "wake word unavailable": len(events.of_type("wake_word_unavailable")),
        "cancelled commands": len(events.of_type("actuator_aborted")),
    }
