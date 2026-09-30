"""
`/api/voice…` — the microphone session behind the studio page (docs/spec/studio.md
§1, §4; TSK-I4-04, Q-50). Slice S2.

`studio --mic` runs `VoiceSession.play_live` in a daemon thread with its own event
loop. The page and the microphone share one session, so each captured frame's work
runs under `server.lock` (never held across frames) and wakes the SSE stream when it
added events. Mute silences the frames at the source: the stream stays open, the
timestamps stay the microphone's, and nothing the room says opens a turn.
"""

from __future__ import annotations

import asyncio
import contextlib
import threading
from collections.abc import Awaitable, Callable, Iterator
from typing import Any

from ..errors import NeuroEdgeError
from ..hal.audio import AudioFrame
from ..perception.live_voice import build_live_voice, count_events

STOP_JOIN_S = 3.0


class _MutableSource:
    """A live source whose frames turn to silence (same length, same stamps) while muted."""

    def __init__(self, source: Any) -> None:
        self.source = source
        self.muted = False

    def frames(self) -> Iterator[AudioFrame]:
        for frame in self.source.frames():
            if self.muted:
                frame = AudioFrame(
                    bytes(len(frame.pcm)), frame.start_ms, frame.duration_ms, frame.sample_rate_hz
                )
            yield frame

    def close(self) -> None:
        close = getattr(self.source, "close", None)
        if callable(close):
            close()


class StudioVoice:
    """The running microphone session of a studio: status, mute and stop."""

    def __init__(
        self,
        server: Any,
        voice: Any,
        source: _MutableSource,
        sink: Any,
        *,
        half_duplex: bool,
    ) -> None:
        self.server = server
        self.voice = voice
        self.half_duplex = half_duplex
        self._source = source
        self._sink = sink
        self._stop = threading.Event()
        self._error: NeuroEdgeError | None = None
        self._thread = threading.Thread(
            target=self._run, name="neuroedge-studio-voice", daemon=True
        )

    @property
    def muted(self) -> bool:
        return self._source.muted

    @property
    def running(self) -> bool:
        return self._thread.is_alive()

    def start(self) -> None:
        self._thread.start()

    def set_muted(self, muted: bool) -> None:
        self._source.muted = muted

    def _run(self) -> None:
        try:
            asyncio.run(
                self.voice.play_live(
                    self._source,
                    half_duplex=self.half_duplex,
                    stop=self._stop,
                    step=self._step,
                )
            )
        except NeuroEdgeError as error:  # the device went away, or the session fell behind
            self._error = error
        finally:
            self.server.notify()

    async def _step(self, work: Callable[[], Awaitable[None]]) -> None:
        """One frame's work, under the server's lock; the page hears of what it added."""
        server = self.server
        events = server.session.events.events
        with server.lock:
            before = len(events)
            await work()
            grew = len(events) != before
        if grew:
            server.notify()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=STOP_JOIN_S)
        for closer in (self._source, self._sink):
            close = getattr(closer, "close", None)
            if callable(close):
                with contextlib.suppress(Exception):
                    close()

    def status(self) -> dict[str, Any]:
        counts = count_events(self.voice)
        reply: dict[str, Any] = {
            "ok": True,
            "enabled": True,
            "running": self.running,
            "muted": self.muted,
            "half_duplex": self.half_duplex,
            "state": self.voice.fsm.state.name,
            "counters": {
                "turns": counts["turns"],
                "barge_in": counts["barge-in"],
                "stt_unavailable": counts["STT unavailable"],
                "cancelled": counts["cancelled commands"],
            },
            "devices": {
                "input": _device_name(self._source.source, "input"),
                "output": _device_name(self._sink, "output"),
            },
        }
        if self._error is not None:
            reply["error"] = self._error.as_dict()
        return reply


def _device_name(device: Any, kind: str) -> str:
    return str(getattr(device, "device", None) or f"default {kind}")


def status(server: Any) -> dict[str, Any]:
    if server.voice is None:
        return {"ok": True, "enabled": False, "running": False}
    return server.voice.status()


def mute(server: Any, body: dict[str, Any]) -> dict[str, Any]:
    if server.voice is None:
        raise NeuroEdgeError(
            where="POST /api/voice/mute",
            why="the studio runs without a microphone",
            how="restart it with neuroedge studio --mic",
        )
    muted = body.get("muted")
    if not isinstance(muted, bool):
        raise ValueError('expected {"muted": true|false}')
    server.voice.set_muted(muted)
    return server.voice.status()


def start(server: Any, *, half_duplex: bool = False, source: Any = None) -> None:
    """
    Open the microphone behind the page (`studio --mic`); sets `server.voice`.
    `source`: a stand-in for the microphone (tests); default the HAL's `audio.in`.
    """
    session = server.session
    voice, _, _, _ = build_live_voice(session, session.conversation.ledger.clock)
    if source is None:
        source = session.hal.audio_source(called_from="neuroedge studio --mic")
    sink = session.hal.audio_sink(called_from="neuroedge studio --mic")
    running = StudioVoice(server, voice, _MutableSource(source), sink, half_duplex=half_duplex)
    server.voice = running
    running.start()
