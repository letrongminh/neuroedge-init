"""
Voice Pipeline and Perception Layer (L2).
Port of Pipecat frame-based audio pipeline, microWakeWord, and Silero VAD.
"""

__all__ = ["VoicePipeline"]


class VoicePipeline:
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
