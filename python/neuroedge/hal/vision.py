"""
`vision.in` — the camera primitive of the HAL (TSK-V1b-01, TSK-V1b-02, RFC-0012 §3a–§3b).

A board declares what its camera can do as `modes`: width, height, fps and pixel format
(`board.v1`, `vision_in`). An agent declares what it needs in `[requires]`:

    "vision.in" = { min_width = 640, min_height = 480, min_fps = 10.0, pixel_formats = ["yuyv", "mjpeg"] }

and the board meets it when **at least one mode** satisfies every bound (RFC-0012 §3b). The
matching is deterministic because `pixel_format` is a closed enum, and it is one function —
`Requirement.failures` — used by the build (`engine/compiler.py`) and by the session that opens
the camera, so what the build accepted is the mode the camera is opened in.

This module is the L1 half of the seam of `docs/spec/vision.md` §2: a `Camera` hands over
`CameraFrame`s — the camera's own frame number, the instant the HAL read it on the session's
clock, the bytes. It knows nothing of models or facts (`perception/vision/` turns a
`CameraFrame` into a `Frame` and reads it). A camera that cannot deliver raises
`CameraUnavailable` (`NE5001`, the code of "an input the perception cannot read": the gate then
blocks `criterion_unavailable`, invariant #2); it never invents a frame.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from ..errors import AgentManifestError, PerceptionUnavailableError

# RFC-0012 §9.1: a closed enum — adding a value needs an RFC. Order is the board schema's.
PIXEL_FORMATS = ("yuyv", "mjpeg", "rgb565", "rgb888", "gray8")
# Bytes per pixel of the raw formats; a compressed one (`mjpeg`) has no fixed frame size.
BYTES_PER_PIXEL: dict[str, int] = {"yuyv": 2, "rgb565": 2, "rgb888": 3, "gray8": 1}
REQUIREMENT_KEYS = ("min_width", "min_height", "min_fps", "pixel_formats")


class CameraUnavailable(PerceptionUnavailableError):
    """
    The camera cannot deliver: gone, stalled, out of frames, or a frame that is not what its
    mode says. Same stable code as its parent (`NE5001`): a subclass, not a new error. The
    session turns it into "no fact", and the gate blocks `criterion_unavailable`.
    """


@dataclass(frozen=True)
class Mode:
    """One way a camera runs: what the board declares in `vision_in.modes`."""

    width: int
    height: int
    fps: float
    pixel_format: str

    @classmethod
    def of(cls, declared: Mapping[str, Any]) -> Mode:
        return cls(
            int(declared["width"]),
            int(declared["height"]),
            float(declared["fps"]),
            str(declared["pixel_format"]),
        )

    @property
    def frame_bytes(self) -> int | None:
        """The exact size of one frame, or None for a compressed format."""
        per = BYTES_PER_PIXEL.get(self.pixel_format)
        return None if per is None else self.width * self.height * per

    @property
    def period_ms(self) -> float:
        return 1000.0 / self.fps

    def __str__(self) -> str:
        return f"{self.width}x{self.height} @ {self.fps:g} fps {self.pixel_format}"


@dataclass(frozen=True)
class CameraFrame:
    """
    One frame as the HAL hands it over. `seq` is the camera's own number (a jump means frames
    were lost); `captured_ms` the instant the HAL read it, on the session's clock.
    """

    seq: int
    captured_ms: float
    pixels: bytes
    width: int
    height: int
    pixel_format: str


class Camera(Protocol):
    """What `HardwareAbstractionLayer.vision_in` returns: a running camera."""

    mode: Mode

    def read_available(self) -> list[CameraFrame]:
        """
        Every frame that arrived since the last call, oldest first — possibly none. Raises
        `CameraUnavailable` when the camera is gone or stalled. Never blocks.
        """
        ...

    def close(self) -> None: ...


def monotonic_ms() -> float:
    """The default clock of a camera: the same one `engine/trace_sink.py` defaults to."""
    return time.monotonic() * 1000.0


# A way to open a camera in a mode, on a clock, handed to a HAL by whoever owns the machine's
# wiring (the session on `sim`; the environment on `linux`).
Clock = Callable[[], float]
CameraFactory = Callable[[Mode, Clock], Camera]


def modes_of(declared: Iterable[Mapping[str, Any]]) -> tuple[Mode, ...]:
    return tuple(Mode.of(entry) for entry in declared)


def _bad(where: str, why: str, how: str) -> AgentManifestError:
    return AgentManifestError(where=where, why=why, how=how)


@dataclass(frozen=True)
class Requirement:
    """The `[requires] "vision.in"` entry of an agent. Every bound is optional."""

    min_width: int = 0
    min_height: int = 0
    min_fps: float = 0.0
    pixel_formats: tuple[str, ...] = ()

    @classmethod
    def parse(cls, need: Any, where: str = '[requires] "vision.in"') -> Requirement:
        """A validated requirement; an unknown key or a bad value is refused, never ignored."""
        if not isinstance(need, Mapping):
            raise _bad(
                where,
                f"must be a table, found {need!r}",
                'write "vision.in" = { min_width = 640, min_height = 480 }',
            )
        unknown = sorted(set(need) - set(REQUIREMENT_KEYS))
        if unknown:
            # A misspelt bound would be a bound that is not there: the build would pass an
            # agent that asked for more than the board has.
            raise _bad(
                where,
                f"unknown key(s) {unknown}",
                f"the keys of vision.in are {list(REQUIREMENT_KEYS)} (RFC-0012 §3b)",
            )
        sizes: dict[str, int] = {}
        for key in ("min_width", "min_height"):
            value = need.get(key, 0)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise _bad(
                    where,
                    f"{key} must be a whole number of pixels, found {value!r}",
                    f"write {key} = 640",
                )
            sizes[key] = value
        fps = need.get("min_fps", 0.0)
        if (
            isinstance(fps, bool)
            or not isinstance(fps, int | float)
            or not math.isfinite(fps)
            or fps < 0
        ):
            raise _bad(
                where,
                f"min_fps must be a number of frames per second, found {fps!r}",
                "write min_fps = 10.0",
            )
        formats = need.get("pixel_formats", ())
        if not isinstance(formats, Sequence) or isinstance(formats, str):
            raise _bad(
                where,
                f"pixel_formats must be a list, found {formats!r}",
                'write pixel_formats = ["yuyv", "mjpeg"]',
            )
        lost = [f for f in formats if f not in PIXEL_FORMATS]
        if lost:
            raise _bad(
                where,
                f"pixel_formats {lost} are not pixel formats; the closed set is {list(PIXEL_FORMATS)} (RFC-0012 §9.1)",
                "use only those",
            )
        return cls(sizes["min_width"], sizes["min_height"], float(fps), tuple(formats))

    def failures(self, mode: Mode) -> list[str]:
        """Why `mode` does not meet this requirement; empty means it does."""
        out = []
        if mode.width < self.min_width:
            out.append(f"min_width {self.min_width} > {mode.width}")
        if mode.height < self.min_height:
            out.append(f"min_height {self.min_height} > {mode.height}")
        if mode.fps < self.min_fps:
            out.append(f"min_fps {self.min_fps:g} > {mode.fps:g}")
        if self.pixel_formats and mode.pixel_format not in self.pixel_formats:
            out.append(f"pixel_format {mode.pixel_format!r} not in {list(self.pixel_formats)}")
        return out


def select_mode(modes: Sequence[Mode], need: Requirement) -> Mode | None:
    """The first mode, in the board's order, that meets `need`; None when there is none."""
    return next((mode for mode in modes if not need.failures(mode)), None)


def nearest_mode(modes: Sequence[Mode], need: Requirement) -> tuple[Mode, list[str]] | None:
    """The mode that misses `need` by the fewest bounds, and what it misses (for the error)."""
    scored = [
        (len(failed), index, mode, failed)
        for index, mode in enumerate(modes)
        if (failed := need.failures(mode))
    ]
    if not scored:
        return None
    _, _, mode, failed = min(scored, key=lambda item: item[:2])
    return mode, failed
