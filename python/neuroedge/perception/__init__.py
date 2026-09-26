"""
Perception layer (L2) — the conversation state machine (TSK-S3-11) and speech
providers (TSK-S3-13).

`VoiceStateMachine` implements docs/spec/voice_fsm.md and depends on no target;
`VoiceSession` puts it in front of an agent on `sim` and `linux` (TSK-S5-08
brings audio there). Both pass the language-independent corpus
`fixtures/compliance/voice/` (TSK-S3-10, `neuroedge.testing.voice_corpus`), with
scripted events and through fake speech providers. `providers/` holds STT and TTS
behind `[stt]` / `[tts]` of agent.toml, and the wake-word detector behind
`[wake_word]` (TSK-I4-01: a model of your own; none ships, Q-45).
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
