"""
Live audio backend through `sounddevice` (PortAudio, TSK-S5-08, TSK-I4-04).

`audio.in` / `audio.out` on physical devices: `LiveAudioIn` captures frames as 20 ms
mono `AudioFrame`s, and `LiveAudioOut` writes replies in a background thread so the
session never waits for playback. `LiveSpeaker` joins live output with the
timeline `Speaker` (`hal/audio.py`), so `--voice-out` still writes a WAV recording.

`sounddevice` is an optional extra (`pip install 'neuroedge[audio]'`, NOTICE §B),
imported lazily only when a live device is opened. Neither this module nor `sim`
depends on `gpiod`.
"""

from __future__ import annotations

import contextlib
import os
import threading
from array import array
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Protocol, overload

from ..errors import BoardCapabilityError
from .audio import (
    FRAME_MS,
    SAMPLE_WIDTH,
    AudioFrame,
    Speaker,
    duration_ms,
    pcm_samples,
    samples_pcm,
    to_mono,
)

__all__ = [
    "EventSink",
    "LiveAudioIn",
    "LiveAudioOut",
    "LiveSpeaker",
    "_LiveAudio",
    "_NullSink",
    "_audio_node",
    "_import_sounddevice",
    "_interleave",
]


class EventSink(Protocol):
    def emit(self, type: str, data: dict[str, Any]) -> None: ...


class _NullSink:
    def emit(self, type: str, data: dict[str, Any]) -> None:
        return None


def _import_sounddevice(where: str = "LinuxHAL -> audio.in/audio.out") -> Any:
    try:
        import sounddevice
    except ImportError as exc:
        raise BoardCapabilityError(
            where=where,
            why="the `sounddevice` package (PortAudio) is not installed, and live audio needs it",
            how=(
                "pip install 'neuroedge[audio]' (MIT, optional; see NOTICE §B), or use a WAV "
                "file session: neuroedge run --voice-file x.wav"
            ),
        ) from exc
    return sounddevice


@overload
def _audio_node(argument: str | None, env: str, default: str) -> str: ...


@overload
def _audio_node(argument: str | None, env: str, default: str | None = None) -> str | None: ...


def _audio_node(argument: str | None, env: str, default: str | None = None) -> str | None:
    """The device name, in order: the argument, the environment, the default node."""
    if argument is not None and argument.strip():
        return argument
    from_env = (os.environ.get(env) or "").strip()
    return from_env or default


def _interleave(pcm: bytes, channels: int) -> bytes:
    """Mono 16-bit PCM as `channels` interleaved copies — a mono reply on a stereo device."""
    if channels == 1:
        return pcm
    samples = pcm_samples(pcm)
    out = array("h")
    for sample in samples:
        out.extend((sample,) * channels)
    return samples_pcm(out)


class _LiveAudio:
    """
    What the two live roles share: the device name, the board's format, the failure
    shape (one helper), and opening a stream atomically — a stream whose `start()`
    fails is closed, never left half-open behind a dropped reference.
    """

    # What `query_devices`/`check_*_settings`/`Raw*Stream` are asked for, per role.
    kind = ""
    node_hint = ""

    def __init__(
        self,
        sd: Any,
        *,
        sample_rate_hz: int,
        channels: int,
        device: str | None,
        frame_ms: int = FRAME_MS,
    ) -> None:
        self.sd = sd
        self.sample_rate_hz = sample_rate_hz
        self.channels = channels
        self.device = device
        self._frames_per_block = max(1, sample_rate_hz * frame_ms // 1000)
        self._stream: Any = None

    @property
    def where(self) -> str:
        raise NotImplementedError

    def _fail(self, why: str, how: str) -> BoardCapabilityError:
        return BoardCapabilityError(where=self.where, why=why, how=how)

    def _open(self) -> Any:
        if self._stream is not None:
            return self._stream
        try:
            self.sd.query_devices(self.device, self.kind)
        except Exception as exc:
            hint = self.node_hint
            if "PipeWire" in hint and "docs/spec/simulation_coverage.md" not in hint:
                hint = (
                    f"{hint} — how PortAudio sees the PipeWire node is in "
                    "docs/spec/simulation_coverage.md §6.1 (not yet verified on hardware)"
                )
            raise self._fail(
                f"no {self.kind} device named {self.device!r}: {exc}",
                hint,
            ) from exc
        stream = None
        try:
            check = (
                self.sd.check_input_settings
                if self.kind == "input"
                else self.sd.check_output_settings
            )
            check(
                device=self.device,
                samplerate=self.sample_rate_hz,
                channels=self.channels,
                dtype="int16",
            )
            factory = self.sd.RawInputStream if self.kind == "input" else self.sd.RawOutputStream
            stream = factory(
                samplerate=self.sample_rate_hz,
                channels=self.channels,
                dtype="int16",
                device=self.device,
                blocksize=self._frames_per_block,
            )
            stream.start()
        except Exception as exc:
            if stream is not None:  # never leave it half-open
                with contextlib.suppress(Exception):
                    stream.close()
            how = (
                "fix the board profile or the device (Q-22's nodes carry the board's format)"
                if getattr(self, "_caller", "LinuxHAL") == "LinuxHAL"
                else "fix the board profile or the device"
            )
            raise self._fail(
                f"device {self.device!r} refuses {self.sample_rate_hz} Hz, "
                f"{self.channels} channel(s), 16-bit: {exc}",
                how,
            ) from exc
        self._stream = stream
        return stream

    def open(self) -> None:
        """Open the device now: a missing one fails before a session asks for a line."""
        self._open()


class LiveAudioIn(_LiveAudio):
    """
    `audio.in` from a live device (`sounddevice`, PortAudio) — by default the
    PipeWire echo-cancel node `neuroedge.ec.source` (Q-22) on Linux, so what a
    session hears is already echo-cancelled. `frames()` reads the board's rate
    and channel count as 20 ms mono `AudioFrame`s.

    Opening is explicit and checked (`query_devices`, `check_input_settings`); a
    device that is missing, refuses the board's format, or stops answering raises a
    three-part `BoardCapabilityError` — never an empty frame, never silence read as
    if it were the room. An input overflow (PortAudio dropped captured audio because
    the reader fell behind) is recorded (`audio_in_overflow`) and stops the frames:
    the sample clock is no longer the room's, and a shrunken timeline is not passed
    on as if nothing were lost. Real-time driving is `TODOS.md` #45.
    """

    kind = "input"

    def __init__(
        self,
        *args: Any,
        events: EventSink | None = None,
        caller: str = "LinuxHAL",
        env_var: str = "NEUROEDGE_LINUX_AUDIO_IN",
        node_hint: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.events: EventSink = events if events is not None else _NullSink()
        self._closed = False
        self._at_ms = 0
        self._caller = caller
        self._env_var = env_var
        self._node_hint = node_hint

    @property
    def where(self) -> str:
        return f"{self._caller} -> audio.in ({self.device!r})"

    @property
    def node_hint(self) -> str:
        if self._node_hint is not None:
            return self._node_hint
        if self._caller == "LinuxHAL":
            return (
                "check PipeWire runs the echo-cancel module (pipewire/neuroedge-echo-cancel.conf, Q-22), "
                f"or set {self._env_var} to the device that should be read"
            )
        return (
            "check the microphone is connected and recognised by PortAudio, "
            f"or set {self._env_var} to the device name"
        )

    def frames(self) -> Iterator[AudioFrame]:
        """20 ms frames, mono at the board's rate, from now until `close()`."""
        stream = self._open()
        while not self._closed:
            try:
                data, overflowed = stream.read(self._frames_per_block)
            except Exception as exc:
                if self._closed:
                    return
                how = (
                    "check the microphone and the PipeWire node are still there; reconnect, then "
                    "restart the session"
                    if self._caller == "LinuxHAL"
                    else "check the microphone is still connected; reconnect, then restart the session"
                )
                raise self._fail(
                    f"the input device stopped answering: {exc}",
                    how,
                ) from exc
            if overflowed:
                self.events.emit("audio_in_overflow", {})
                raise self._fail(
                    f"the input device {self.device!r} overflowed: captured audio was dropped and "
                    "the frames' timeline cannot be trusted",
                    "make the reader keep up (a real-time session is TODOS.md #45); the session "
                    "stops rather than passing on a timeline that silently shrank",
                )
            pcm = bytes(data)
            if not pcm:
                # A blocking read of a started stream returns a full block; an empty one
                # means the device stopped without raising — never read as silence.
                how = (
                    "check the device and the PipeWire node, then start the session again"
                    if self._caller == "LinuxHAL"
                    else "check the device, then start the session again"
                )
                raise self._fail(
                    "the input device returned an empty block, so it is no longer running; "
                    "silence is never passed off as input",
                    how,
                )
            mono = to_mono(pcm, self.channels) if self.channels > 1 else pcm
            frame = AudioFrame(
                mono, self._at_ms, duration_ms(mono, self.sample_rate_hz), self.sample_rate_hz
            )
            self._at_ms = frame.end_ms
            yield frame

    def close(self) -> None:
        self._closed = True
        stream, self._stream = self._stream, None
        if stream is None:
            return
        with contextlib.suppress(Exception):  # a stop that fails changes nothing here
            stream.abort()
        with contextlib.suppress(Exception):
            stream.close()


class LiveAudioOut(_LiveAudio):
    """
    `audio.out` on a live device (`sounddevice`, PortAudio) — by default the
    PipeWire echo-cancel node `neuroedge.ec.sink` (Q-22) on Linux, so a reply is
    also the reference signal the AEC subtracts from the microphone.

    `play()` returns at once: a daemon thread writes the reply, because a session
    must never wait for the loudspeaker. `stop()` drops what has not played yet
    (barge-in, `voice_fsm.md` §5.2 step 3). A device that fails mid-reply is
    remembered — the next `play()` refuses and `close()` raises — so a dead
    speaker is never just quiet. Real-time driving is `TODOS.md` #45.
    """

    kind = "output"

    def __init__(
        self,
        *args: Any,
        caller: str = "LinuxHAL",
        env_var: str = "NEUROEDGE_LINUX_AUDIO_OUT",
        node_hint: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._caller = caller
        self._env_var = env_var
        self._node_hint = node_hint
        self._block = self._frames_per_block * self.channels * SAMPLE_WIDTH
        self._thread: threading.Thread | None = None
        self._generation = 0
        self._lock = threading.Lock()
        self._error: str | None = None
        self._reported = False

    @property
    def where(self) -> str:
        return f"{self._caller} -> audio.out ({self.device!r})"

    @property
    def node_hint(self) -> str:
        if self._node_hint is not None:
            return self._node_hint
        if self._caller == "LinuxHAL":
            return (
                "check PipeWire runs the echo-cancel module (pipewire/neuroedge-echo-cancel.conf, Q-22), "
                f"or set {self._env_var} to the device that should be played to"
            )
        return (
            "check the speaker is connected and recognised by PortAudio, "
            f"or set {self._env_var} to the device name"
        )

    def play(self, pcm: bytes) -> None:
        """Write one reply; the previous one is dropped, as `Playback.stop` does."""
        if self._error is not None:
            raise self._fail(
                f"the previous reply failed and the device was not reopened: {self._error}",
                "fix the output device, then start the session again",
            )
        with self._lock:
            stream = self._open()
            self._generation += 1
            generation = self._generation
            # `abort()` leaves the stream stopped; a writer needs it started again
            # (PortAudioError "Stream is stopped" otherwise). The reply being replaced
            # is dropped here.
            with contextlib.suppress(Exception):
                stream.abort()
            try:
                stream.start()
            except Exception as exc:
                how = (
                    "check the speaker and the PipeWire node, then start the session again"
                    if self._caller == "LinuxHAL"
                    else "check the speaker, then start the session again"
                )
                raise self._fail(
                    f"the output device {self.device!r} will not play: {exc}",
                    how,
                ) from exc
            thread = threading.Thread(
                target=self._write,
                args=(stream, pcm, generation),
                name="neuroedge-audio-out",
                daemon=True,
            )
            self._thread = thread
            thread.start()

    def wait(self, timeout: float = 2.0) -> bool:
        """
        Wait for the writer thread to finish the reply it was given (tests, orderly
        shutdown). True when nothing is being written any more.
        """
        with self._lock:
            thread = self._thread
        if thread is None:
            return True
        thread.join(timeout)
        return not thread.is_alive()

    def _write(self, stream: Any, pcm: bytes, generation: int) -> None:
        try:
            payload = _interleave(pcm, self.channels)
            for offset in range(0, len(payload), self._block):
                with self._lock:
                    if generation != self._generation:
                        return
                stream.write(payload[offset : offset + self._block])
        except Exception as exc:
            with self._lock:
                if generation != self._generation:
                    return  # dropped by stop() or replaced: not a device failure
            self._error = f"{type(exc).__name__}: {exc}"

    def stop(self) -> None:
        """Drop what has not played. Never raises: barge-in has a 300 ms budget (§5.2)."""
        with self._lock:
            self._generation += 1
            stream = self._stream
        if stream is not None:
            with contextlib.suppress(Exception):
                stream.abort()

    def close(self) -> None:
        """Release the device. A failure noticed while playing is raised once, here."""
        self.stop()
        with self._lock:
            stream, self._stream = self._stream, None
            thread, self._thread = self._thread, None
            failure = self._error
        if thread is not None and thread.is_alive():
            thread.join(timeout=2.0)
        if stream is not None:
            with contextlib.suppress(Exception):
                stream.close()
        # Reported once: `close()` stays idempotent, and `play()` keeps refusing.
        if failure is not None and not self._reported:
            self._reported = True
            how = (
                "check the speaker and the PipeWire node; the reply was not heard in full"
                if self._caller == "LinuxHAL"
                else "check the speaker; the reply was not heard in full"
            )
            raise BoardCapabilityError(
                where=self.where,
                why=f"the output device failed while playing: {failure}",
                how=how,
            )


class LiveSpeaker:
    """
    `audio.out` on a live device with the `Speaker` timeline on the side (`--voice-out`
    still writes the session as WAV). `play()` starts the reply on the device and
    records it; `stop()` flushes both. Real-time session driving is `TODOS.md` #45;
    this is the HAL primitive it will use.
    """

    def __init__(self, sink: LiveAudioOut, sample_rate_hz: int) -> None:
        self._timeline = Speaker(sample_rate_hz)
        self._sink = sink
        self.sample_rate_hz = sample_rate_hz

    @property
    def playbacks(self) -> list[Any]:
        return self._timeline.playbacks

    def play(self, pcm: bytes, start_ms: float) -> Any:
        playback = self._timeline.play(pcm, start_ms)
        self._sink.play(pcm)
        return playback

    def stop(self, at_ms: float) -> None:
        self._timeline.stop(at_ms)
        self._sink.stop()

    def render(self) -> bytes:
        return self._timeline.render()

    def write(self, path: str | Path) -> Path:
        return self._timeline.write(path)

    def close(self) -> None:
        self._sink.close()
