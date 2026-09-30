"""
Fake `sounddevice` module for testing `hal/linux.py` and `hal/sim.py` live audio.

Avoids PortAudio / physical audio hardware dependencies in tests.
"""

from __future__ import annotations

import threading
from array import array
from typing import Any

DEFAULT_DEVICES = {"neuroedge.ec.source", "neuroedge.ec.sink", None}


class FakeInputStream:
    def __init__(self, world: Any, device: Any, channels: int, rate: int) -> None:
        self.world, self.device, self.channels, self.rate = world, device, channels, rate
        self.started = False
        self.aborted = False
        self.closed = False
        self.wake = threading.Event()

    def start(self) -> None:
        # PortAudio refuses to start an already-started stream; model that too.
        if self.started:
            raise RuntimeError("Stream is already started")
        self.started = True

    def read(self, frames: int) -> tuple[bytes, bool]:
        if not self.started:
            raise RuntimeError("Stream is stopped")  # PortAudioError, reproduced
        if self.world.mode == "gone":
            raise OSError(19, "No such device")
        if self.world.mode == "empty":
            return b"", False
        if self.world.mode == "overflow":
            return b"\x00\x00" * frames * self.channels, True
        if self.world.blocks:
            return self.world.blocks.pop(0), False
        if self.world.blocking:  # a real device waits; abort() wakes the reader
            self.wake.wait(2.0)
            raise OSError(19, "No such device")
        raise OSError(19, "No such device")

    def abort(self) -> None:
        # PortAudio: abort() stops the stream; writing/reading needs start() again.
        self.started = False
        self.aborted = True
        self.wake.set()

    def close(self) -> None:
        self.closed = True


class FakeOutputStream(FakeInputStream):
    def __init__(self, world: Any, device: Any, channels: int, rate: int) -> None:
        super().__init__(world, device, channels, rate)
        self.written: list[bytes] = []
        self.fail_after: int | None = None

    def write(self, payload: bytes) -> None:
        if not self.started:
            raise RuntimeError("Stream is stopped")  # PortAudioError, reproduced
        if self.fail_after is not None and len(self.written) >= self.fail_after:
            raise OSError(5, "Input/output error")
        self.written.append(bytes(payload))


class FakeSounddevice:
    """The slice of sounddevice `LiveAudioIn` / `LiveAudioOut` use."""

    def __init__(
        self,
        blocks: Any = (),
        *,
        mode: str = "ok",
        devices: Any = None,
        fail_format: bool = False,
        blocking: bool = False,
    ) -> None:
        self.blocks = list(blocks)
        self.mode = mode
        self.devices = set(devices) if devices is not None else set(DEFAULT_DEVICES)
        self.fail_format = fail_format
        self.blocking = blocking
        self.inputs: list[FakeInputStream] = []
        self.outputs: list[FakeOutputStream] = []

    def query_devices(self, device: Any, kind: str) -> dict[str, Any]:
        if device not in self.devices:
            raise ValueError(f"No device matching {device!r}")
        return {"name": device or "default", "max_input_channels": 2, "max_output_channels": 2}

    def check_input_settings(
        self, *, device: Any, samplerate: int, channels: int, dtype: str
    ) -> None:
        if self.fail_format:
            raise ValueError(f"device {device!r} does not support {samplerate} Hz")

    def check_output_settings(
        self, *, device: Any, samplerate: int, channels: int, dtype: str
    ) -> None:
        if self.fail_format:
            raise ValueError(f"device {device!r} does not support {samplerate} Hz")

    def RawInputStream(  # noqa: N802
        self, *, samplerate: int, channels: int, dtype: str, device: Any, blocksize: int
    ) -> FakeInputStream:
        stream = FakeInputStream(self, device, channels, samplerate)
        self.inputs.append(stream)
        return stream

    def RawOutputStream(  # noqa: N802
        self, *, samplerate: int, channels: int, dtype: str, device: Any, blocksize: int
    ) -> FakeOutputStream:
        stream = FakeOutputStream(self, device, channels, samplerate)
        self.outputs.append(stream)
        return stream


def stereo(pcm: bytes) -> bytes:
    samples = array("h")
    samples.frombytes(pcm)
    out = array("h")
    for sample in samples:
        out.extend((sample, sample))
    return out.tobytes()
