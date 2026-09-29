"""
Capture thread and bounded queue for live audio sessions (TSK-I4-04).

`LiveAudioCapture` reads frames continuously from a live audio source (such as
`hal.LiveAudioIn`) in a daemon thread so PortAudio never overflows while the
event loop awaits an STT, TTS or System 2 call. If the queue fills (the session
is more than ~10 s behind), the session stops with a three-part error
(`PerceptionUnavailableError`) — never silently dropping captured audio.
"""

from __future__ import annotations

import asyncio
import contextlib
import queue
import threading
from typing import Any

from ..errors import PerceptionUnavailableError
from ..hal.audio import AudioFrame

QUEUE_MAX_FRAMES = 500  # 500 * 20 ms = 10,000 ms (10 s)


class LiveAudioCapture:
    """
    Capture thread reading frames from a live audio source into a bounded queue.

    Reads `source.frames()` continuously in a daemon thread so PortAudio does not
    overflow while the event loop awaits a provider. If the queue fills (the session
    falls more than ~10 s behind), the session stops with a three-part
    PerceptionUnavailableError — never dropping audio silently. An exception from
    `source.frames()` is preserved and re-raised in the loop.
    """

    def __init__(
        self,
        source: Any,
        *,
        stop: threading.Event | None = None,
        max_frames: int = QUEUE_MAX_FRAMES,
    ) -> None:
        self.source = source
        self._stop = stop if stop is not None else threading.Event()
        self._max_frames = max_frames
        self._queue: queue.Queue[AudioFrame] = queue.Queue(maxsize=max_frames)
        self._error: BaseException | None = None
        self._thread: threading.Thread | None = None
        self._done = threading.Event()

    def start(self) -> None:
        """Start the background capture thread."""
        if self._thread is not None:
            return
        self._thread = threading.Thread(
            target=self._worker, name="neuroedge-live-capture", daemon=True
        )
        self._thread.start()

    def _worker(self) -> None:
        try:
            for frame in self.source.frames():
                if self._stop.is_set():
                    break
                try:
                    self._queue.put_nowait(frame)
                except queue.Full:
                    raise PerceptionUnavailableError(
                        where="VoiceSession.play_live -> capture queue",
                        why=(
                            f"the audio capture queue filled ({self._max_frames} frames, "
                            "over 10 s behind); processing cannot keep up with real-time audio"
                        ),
                        how=(
                            "make STT and System 2 providers respond within their time bounds "
                            "or check system load; captured audio is never dropped silently"
                        ),
                    ) from None
        except BaseException as exc:
            if not self._stop.is_set() or isinstance(exc, PerceptionUnavailableError):
                self._error = exc
        finally:
            self._done.set()

    def _poll(self, timeout: float) -> AudioFrame | None:
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    async def next_frame(self, loop: asyncio.AbstractEventLoop) -> AudioFrame | None:
        """
        Get the next frame without blocking the event loop.

        Returns None when the capture has stopped or the source has ended and all
        buffered frames have been consumed. Raises any exception that occurred in
        the capture thread.
        """
        while True:
            if self._error is not None:
                err = self._error
                self._error = None
                raise err

            try:
                return self._queue.get_nowait()
            except queue.Empty:
                pass

            if self._stop.is_set():
                return None

            if self._done.is_set():
                if self._error is not None:
                    err = self._error
                    self._error = None
                    raise err
                return None

            try:
                frame = await loop.run_in_executor(None, self._poll, 0.05)
            except Exception:
                frame = None

            if frame is not None:
                return frame

    def close(self) -> None:
        """Stop capture, close source streams, and join the thread."""
        self._stop.set()
        close_fn = getattr(self.source, "close", None)
        if callable(close_fn):
            with contextlib.suppress(Exception):
                close_fn()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2.0)
