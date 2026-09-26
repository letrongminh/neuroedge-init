"""
Perception layer (L2) — the conversation state machine (TSK-S3-11) and speech
providers (TSK-S3-13).

`VoiceStateMachine` implements docs/spec/voice_fsm.md and depends on no target;
`VoiceSession` puts it in front of an agent on `sim` (on `linux` with TSK-S5-08,
which brings audio and scheduled commands there). Both pass the
language-independent corpus `fixtures/compliance/voice/` (TSK-S3-10,
`neuroedge.testing.voice_corpus`), with scripted events and through fake speech
providers. `providers/` holds STT and TTS behind `[stt]` / `[tts]` of agent.toml;
wake-word models arrive with TSK-I4-01.
"""

from .voice_fsm import TRIGGERS, VoiceParams, VoiceState, VoiceStateMachine
from .voice_session import VirtualClock, VoiceSession, VoiceTurn

__all__ = [
    "TRIGGERS",
    "VirtualClock",
    "VoiceParams",
    "VoiceSession",
    "VoiceState",
    "VoiceStateMachine",
    "VoiceTurn",
]
