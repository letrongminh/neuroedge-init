"""
Target `sim` (L0): an agent run against `SimHAL` with typed-text input (Q-15).

The browser simulator (Wokwi elements, audio over WebSocket) is later work; the
terminal session behind `neuroedge run --target sim` is what exists.
"""

from .session import SimSession, Turn

__all__ = ["SimSession", "Turn"]
