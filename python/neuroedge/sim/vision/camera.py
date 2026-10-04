"""
The virtual camera of `sim` (TSK-V1b-02, RFC-0012 §3f, FR-TGT-01, FR-TGT-06).

`sim` reads no camera. It **replays** one: a recorded sequence of frames — a directory of image
files, or a deterministic synthetic sequence — played on the session's clock, in a mode the
board declares. The camera is built to be *no better than the hardware it stands for*:

* it runs only in a mode of the board (`SimHAL.vision_in` refuses any other), at that mode's
  fps — frames become ready every `1000 / fps` ms of the session clock and no faster;
* a raw mode (`yuyv`, `rgb565`, `rgb888`, `gray8`) delivers frames of exactly
  `width × height × bytes-per-pixel` bytes; a frame of any other size is not a frame of this
  camera, and the camera is unavailable rather than hand it over;
* it keeps a driver-like queue of `depth` frames. A reader that is late finds the newest
  `depth` frames and a **jump in the frame numbers** for the ones overwritten — what a real
  driver does, and what restarts a vision window (RFC-0012 §9.9) — never the old frames
  quietly presented as new;
* it has frames only while the sequence has: when the recording ends the camera is gone, and
  it says so (`CameraUnavailable`) once what it already captured is delivered. It never loops
  unless asked (`loop = true`: then a short recording repeats, and a recording of one frame is a
  frozen camera, which the perception refuses).

Time is the session's clock — virtual in a test, `monotonic_ms` in a live session — so a
replay is deterministic and a camera on a fake clock never sleeps. The labels a model finds in
the frames are a different thing, replayed from what was recorded (`provider = "replay"`,
`perception/vision/fake.py`); this module supplies frames, and the equivalence of RFC-0012 §3f
holds because both targets feed the same perception with the same events.

`[sim.vision]` of `agent.toml` (`parse_sim_vision`):

    [sim.vision]
    source = "synthetic"          # or a directory of frames, relative to agent.toml
    frames = 90                   # synthetic only: how many frames the recording has
    loop   = false                # repeat the recording (default false: the camera ends with it)
    depth  = 4                    # the driver queue: how many frames a late reader still finds
    drop   = [7, 8]               # frame numbers the camera loses (the numbers jump over them)
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ...errors import AgentManifestError
from ...hal.vision import Camera, CameraFactory, CameraFrame, CameraUnavailable, Mode

DEFAULT_DEPTH = 4
MAX_DEPTH = 64
MAX_SYNTHETIC_FRAMES = 100_000
SYNTHETIC = "synthetic"
KEYS = ("source", "frames", "loop", "depth", "drop")


# -- frame sources ------------------------------------------------------------------------


class FrameSource:
    """A recording: `len(source)` frames, `source.frame(i)` the bytes of frame `i`."""

    def __len__(self) -> int:  # pragma: no cover - interface
        raise NotImplementedError

    def frame(self, index: int) -> bytes:  # pragma: no cover - interface
        raise NotImplementedError


@dataclass(frozen=True)
class ImageSequence(FrameSource):
    """Frames held in memory, in order."""

    frames: tuple[bytes, ...]

    def __len__(self) -> int:
        return len(self.frames)

    def frame(self, index: int) -> bytes:
        return self.frames[index]

    @classmethod
    def from_directory(cls, path: Path, where: str = "[sim.vision] source") -> ImageSequence:
        """
        Every regular file of `path`, in natural order of the names (`2.raw` before `10.raw`),
        as one frame each. The extension is not read: a frame is its bytes (the camera checks
        them against the mode).
        """
        if not path.is_dir():
            raise AgentManifestError(
                where=where,
                why=f"{path} is not a directory of frames",
                how='point source at a directory of recorded frames, or write source = "synthetic"',
            )
        names = sorted(
            (p for p in path.iterdir() if p.is_file() and not p.name.startswith(".")),
            key=lambda p: [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", p.name)],
        )
        if not names:
            raise AgentManifestError(
                where=where,
                why=f"{path} holds no frame",
                how='record frames into it, or write source = "synthetic"',
            )
        return cls(tuple(p.read_bytes() for p in names))


@dataclass(frozen=True)
class SyntheticSequence(FrameSource):
    """
    `count` deterministic frames of exactly the mode's size, every one different (so none is a
    repeat of another). A compressed mode has no fixed size: a frame is 4 KiB.
    """

    mode: Mode
    count: int
    seed: str = "neuroedge"

    def __len__(self) -> int:
        return self.count

    def frame(self, index: int) -> bytes:
        size = self.mode.frame_bytes or 4096
        block = hashlib.blake2b(f"{self.seed}:{index}".encode(), digest_size=64).digest()
        return (block * (size // len(block) + 1))[:size]


# -- the camera ---------------------------------------------------------------------------


class VirtualCamera:
    """A recording played on `clock` as the camera of `mode`. See the module docstring."""

    def __init__(
        self,
        source: FrameSource,
        mode: Mode,
        clock: Callable[[], float],
        *,
        depth: int = DEFAULT_DEPTH,
        loop: bool = False,
        drop: Collection[int] = (),
    ) -> None:
        if not 1 <= depth <= MAX_DEPTH or mode.fps <= 0 or not math.isfinite(mode.fps):
            raise ValueError(f"a camera needs 1 <= depth <= {MAX_DEPTH} and a positive fps")
        if len(source) == 0:
            raise ValueError("a recording with no frame is no camera")
        self.source, self.mode, self.clock = source, mode, clock
        self.depth, self.loop, self.drop = depth, loop, frozenset(drop)
        self._t0 = clock()  # streaming starts now: frame k is ready (k + 1) periods later
        self._next = 0  # the next frame number the reader has not seen
        self.closed = False

    @property
    def frames_in_recording(self) -> int | None:
        return None if self.loop else len(self.source)

    def _ready(self, now: float) -> int:
        """How many frames the sensor has produced by `now`: numbers 0 … n - 1."""
        n = math.floor((now - self._t0) / self.mode.period_ms + 1e-9)
        return max(0, n if self.loop else min(n, len(self.source)))

    def read_available(self) -> list[CameraFrame]:
        if self.closed:
            raise CameraUnavailable(
                where="virtual camera",
                why="the camera is closed",
                how="open it again with hal.vision_in(mode)",
            )
        now = self.clock()
        ready = self._ready(now)
        first = max(self._next, ready - self.depth)  # a late reader: the older ones are gone
        out: list[CameraFrame] = []
        for number in range(first, ready):
            if number in self.drop:
                continue
            pixels = self.source.frame(number % len(self.source))
            expected = self.mode.frame_bytes
            if expected is not None and len(pixels) != expected:
                raise CameraUnavailable(
                    where=f"virtual camera frame {number}",
                    why=f"the frame has {len(pixels)} bytes; a {self.mode} frame has {expected}",
                    how="record frames in the mode the camera runs in (or a compressed mode)",
                )
            out.append(
                CameraFrame(
                    number,
                    self._t0 + (number + 1) * self.mode.period_ms,
                    bytes(pixels),
                    self.mode.width,
                    self.mode.height,
                    self.mode.pixel_format,
                )
            )
        self._next = max(self._next, ready)
        if not out and not self.loop and self._next >= len(self.source):
            # Everything the camera had has been delivered, and it has no more: it is gone.
            raise CameraUnavailable(
                where="virtual camera",
                why=f"the recording ended after {len(self.source)} frame(s)",
                how="record a longer sequence, or set loop = true to repeat it",
            )
        return out

    def close(self) -> None:
        self.closed = True


# -- [sim.vision] of agent.toml -----------------------------------------------------------


@dataclass(frozen=True)
class SimVision:
    """A validated `[sim.vision]`: how the session builds the camera of a mode."""

    source: str = SYNTHETIC
    frames: int = 90
    loop: bool = False
    depth: int = DEFAULT_DEPTH
    drop: tuple[int, ...] = ()
    root: Path = Path(".")
    where: str = "[sim.vision]"

    def factory(self) -> CameraFactory:
        """What `SimHAL.attach_camera` takes: a mode and a clock in, a camera out."""

        def make(mode: Mode, clock: Callable[[], float]) -> Camera:
            if self.source == SYNTHETIC:
                source: FrameSource = SyntheticSequence(mode, self.frames)
            else:
                source = ImageSequence.from_directory(
                    self.root / self.source, f"{self.where} source"
                )
            return VirtualCamera(
                source, mode, clock, depth=self.depth, loop=self.loop, drop=self.drop
            )

        return make


def _bad(where: str, why: str, how: str) -> AgentManifestError:
    return AgentManifestError(where=where, why=why, how=how)


def _whole(
    table: Mapping[str, Any], key: str, default: int, low: int, high: int, where: str
) -> int:
    value = table.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise _bad(
            f"{where} {key}",
            f"{key} must be a whole number from {low} to {high}, found {value!r}",
            f"write {key} = {default}, or remove it",
        )
    return value


def parse_sim_vision(table: Any, root: Path, source: Path | None = None) -> SimVision:
    """A validated `[sim.vision]`; `AgentManifestError` naming the first bad field."""
    where = f"{source} -> [sim.vision]" if source else "[sim.vision]"
    if not isinstance(table, Mapping):
        raise _bad(where, "[sim.vision] must be a table", 'write source = "synthetic"')
    unknown = sorted(set(table) - set(KEYS))
    if unknown:
        raise _bad(where, f"unknown key(s) {unknown}", f"the keys are {list(KEYS)}")
    origin = table.get("source", SYNTHETIC)
    if not isinstance(origin, str) or not origin.strip():
        raise _bad(
            f"{where} source",
            f'source must be "{SYNTHETIC}" or a directory of frames, found {origin!r}',
            'write source = "synthetic", or source = "camera/frames"',
        )
    loop = table.get("loop", False)
    if not isinstance(loop, bool):
        raise _bad(
            f"{where} loop", f"loop must be true or false, found {loop!r}", "write loop = false"
        )
    drop = table.get("drop", ())
    if (
        not isinstance(drop, Sequence)
        or isinstance(drop, str)
        or any(isinstance(n, bool) or not isinstance(n, int) or n < 0 for n in drop)
    ):
        raise _bad(
            f"{where} drop",
            f"drop must be a list of frame numbers, found {drop!r}",
            "write drop = [7, 8]",
        )
    return SimVision(
        source=origin,
        frames=_whole(table, "frames", 90, 1, MAX_SYNTHETIC_FRAMES, where),
        loop=loop,
        depth=_whole(table, "depth", DEFAULT_DEPTH, 1, MAX_DEPTH, where),
        drop=tuple(sorted(set(drop))),
        root=root,
        where=where,
    )
