"""
Perception layer (L2) — the conversation state machine (TSK-S3-11).

`VoiceStateMachine` implements docs/spec/voice_fsm.md for `sim` and `linux`;
`VoiceSession` puts it in front of an agent. Both pass the language-independent
corpus `fixtures/compliance/voice/` (TSK-S3-10, `neuroedge.testing.voice_corpus`).
Audio, ASR/TTS and wake-word models arrive with TSK-S3-13, TSK-S5-08, TSK-I4-01.
"""

from .voice_fsm import TRIGGERS, VoiceParams, VoiceState, VoiceStateMachine
from .voice_session import VirtualClock, VoiceSession

__all__ = [
    "TRIGGERS",
    "VirtualClock",
    "VoiceParams",
    "VoiceSession",
    "VoiceState",
    "VoiceStateMachine",
]
