"""
Video4Linux2 capture in pure Python (TSK-V1b-01, RFC-0012 §3a, §3e).

`vision.in` on `linux` reads a camera through the kernel's V4L2 interface — `/dev/videoN` — with
**no dependency**: the structures are `ctypes`, the calls are `fcntl.ioctl`, the buffers are
`mmap`ped, as the kernel documents. Nothing is imported that the core does not already have, so
`import neuroedge` never needs OpenCV, GStreamer or `av`; a person who wants a heavier pipeline
writes it as a `VisionModel` adapter, which only ever sees decoded frames' bytes anyway.

What it does, in order (`V4L2Camera`):

1. `VIDIOC_QUERYCAP` — the node must be a video *capture* device that can stream;
2. `VIDIOC_S_FMT` / `VIDIOC_S_PARM` — the **declared mode** (width, height, pixel format, fps of the
   board's `vision_in.modes`) is asked for, and the driver's answer must *be* that mode. A driver
   that rounds the size, picks another format or runs at another rate is refused: the board
   declared a mode, and an agent that built against it must see it (target equivalence, RFC-0012
   §3f). A refusal is a three-part error, not a quiet "close enough";
3. four `mmap`ped buffers (`REQBUFS` / `QUERYBUF` / `QBUF`) and `VIDIOC_STREAMON`;
4. a capture thread dequeues every frame as it is ready, stamps it with the session's clock and
   keeps the newest 64; the session drains them with `read_available()` before each gate
   evaluation. Frame numbers are the driver's `sequence`, so a frame the kernel dropped is a jump
   the perception sees (it restarts the window, RFC-0012 §9.9).

Fail-closed (RFC-0012 §3e): the device vanishing, a read error, or **no frame for `stall_ms`** make
`read_available()` raise `CameraUnavailable` — a camera that stopped is never "nobody there". A
frame the driver flags as an error is dropped, not repaired; a raw frame whose size is not the mode's
is refused. `close()` stops the thread, turns the stream off and releases the buffers.

The structures assume the 64-bit LP64 layout of the kernel's UAPI (`sizeof(v4l2_buffer) == 88`),
which is what `linux-rpi5` (aarch64) and the CI runners (x86_64) are; on a 32-bit userspace the
module refuses to open a camera (`LAYOUT`) instead of passing the kernel structures of the wrong
size. The ioctl numbers are computed from those sizes, so a layout error is an `ENOTTY`, never a
silent misread. `scripts/setup_vivid.sh` creates a virtual capture device (`vivid`) so the whole
path runs against a real kernel in CI; the same code is exercised without a kernel by
`tests/test_v4l2.py` (a fake device behind the `io` seam).
"""

from __future__ import annotations

import contextlib
import ctypes
import errno
import fcntl
import mmap
import os
import select
import threading
from collections import deque
from collections.abc import Callable
from fractions import Fraction
from typing import Any, Protocol

from .vision import CameraFrame, CameraUnavailable, Mode

# -- UAPI (linux/videodev2.h) -------------------------------------------------------------

V4L2_BUF_TYPE_VIDEO_CAPTURE = 1
V4L2_MEMORY_MMAP = 1
V4L2_FIELD_NONE = 1
V4L2_CAP_VIDEO_CAPTURE = 0x00000001
V4L2_CAP_STREAMING = 0x04000000
V4L2_CAP_DEVICE_CAPS = 0x80000000
V4L2_BUF_FLAG_ERROR = 0x00000040


def fourcc(code: str) -> int:
    a, b, c, d = code.encode("ascii")
    return a | (b << 8) | (c << 16) | (d << 24)


# The board's closed `pixel_format` enum (RFC-0012 §9.1) → the kernel's four-character codes.
FOURCC = {
    "yuyv": fourcc("YUYV"),
    "mjpeg": fourcc("MJPG"),
    "rgb565": fourcc("RGBP"),
    "rgb888": fourcc("RGB3"),
    "gray8": fourcc("GREY"),
}


class v4l2_capability(ctypes.Structure):
    _fields_ = [
        ("driver", ctypes.c_char * 16),
        ("card", ctypes.c_char * 32),
        ("bus_info", ctypes.c_char * 32),
        ("version", ctypes.c_uint32),
        ("capabilities", ctypes.c_uint32),
        ("device_caps", ctypes.c_uint32),
        ("reserved", ctypes.c_uint32 * 3),
    ]


class v4l2_pix_format(ctypes.Structure):
    _fields_ = [
        ("width", ctypes.c_uint32),
        ("height", ctypes.c_uint32),
        ("pixelformat", ctypes.c_uint32),
        ("field", ctypes.c_uint32),
        ("bytesperline", ctypes.c_uint32),
        ("sizeimage", ctypes.c_uint32),
        ("colorspace", ctypes.c_uint32),
        ("priv", ctypes.c_uint32),
        ("flags", ctypes.c_uint32),
        ("ycbcr_enc", ctypes.c_uint32),
        ("quantization", ctypes.c_uint32),
        ("xfer_func", ctypes.c_uint32),
    ]


class v4l2_format(ctypes.Structure):
    # The kernel's union holds pointers (v4l2_window), so it starts on an 8-byte boundary.
    _fields_ = [
        ("type", ctypes.c_uint32),
        ("_pad", ctypes.c_uint32),
        ("pix", v4l2_pix_format),
        ("_union", ctypes.c_ubyte * (200 - ctypes.sizeof(v4l2_pix_format))),
    ]


class v4l2_fract(ctypes.Structure):
    _fields_ = [("numerator", ctypes.c_uint32), ("denominator", ctypes.c_uint32)]


class v4l2_captureparm(ctypes.Structure):
    _fields_ = [
        ("capability", ctypes.c_uint32),
        ("capturemode", ctypes.c_uint32),
        ("timeperframe", v4l2_fract),
        ("extendedmode", ctypes.c_uint32),
        ("readbuffers", ctypes.c_uint32),
        ("reserved", ctypes.c_uint32 * 4),
    ]


class v4l2_streamparm(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_uint32),
        ("capture", v4l2_captureparm),
        ("_union", ctypes.c_ubyte * (200 - ctypes.sizeof(v4l2_captureparm))),
    ]


class v4l2_requestbuffers(ctypes.Structure):
    _fields_ = [
        ("count", ctypes.c_uint32),
        ("type", ctypes.c_uint32),
        ("memory", ctypes.c_uint32),
        ("capabilities", ctypes.c_uint32),
        ("flags", ctypes.c_uint8),
        ("reserved", ctypes.c_uint8 * 3),
    ]


class v4l2_timecode(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_uint32),
        ("flags", ctypes.c_uint32),
        ("frames", ctypes.c_uint8),
        ("seconds", ctypes.c_uint8),
        ("minutes", ctypes.c_uint8),
        ("hours", ctypes.c_uint8),
        ("userbits", ctypes.c_uint8 * 4),
    ]


class v4l2_buffer(ctypes.Structure):
    _fields_ = [
        ("index", ctypes.c_uint32),
        ("type", ctypes.c_uint32),
        ("bytesused", ctypes.c_uint32),
        ("flags", ctypes.c_uint32),
        ("field", ctypes.c_uint32),
        ("tv_sec", ctypes.c_long),
        ("tv_usec", ctypes.c_long),
        ("timecode", v4l2_timecode),
        ("sequence", ctypes.c_uint32),
        ("memory", ctypes.c_uint32),
        ("m", ctypes.c_ulong),  # the union: `offset` is its low 32 bits (little endian)
        ("length", ctypes.c_uint32),
        ("reserved2", ctypes.c_uint32),
        ("request_fd", ctypes.c_uint32),
    ]


def _ioc(direction: int, number: int, size: int) -> int:
    return (direction << 30) | (size << 16) | (ord("V") << 8) | number


_READ, _WRITE = 2, 1
VIDIOC_QUERYCAP = _ioc(_READ, 0, ctypes.sizeof(v4l2_capability))
VIDIOC_S_FMT = _ioc(_READ | _WRITE, 5, ctypes.sizeof(v4l2_format))
VIDIOC_REQBUFS = _ioc(_READ | _WRITE, 8, ctypes.sizeof(v4l2_requestbuffers))
VIDIOC_QUERYBUF = _ioc(_READ | _WRITE, 9, ctypes.sizeof(v4l2_buffer))
VIDIOC_QBUF = _ioc(_READ | _WRITE, 15, ctypes.sizeof(v4l2_buffer))
VIDIOC_DQBUF = _ioc(_READ | _WRITE, 17, ctypes.sizeof(v4l2_buffer))
VIDIOC_STREAMON = _ioc(_WRITE, 18, ctypes.sizeof(ctypes.c_int))
VIDIOC_STREAMOFF = _ioc(_WRITE, 19, ctypes.sizeof(ctypes.c_int))
VIDIOC_S_PARM = _ioc(_READ | _WRITE, 22, ctypes.sizeof(v4l2_streamparm))

# What the numbers above come out as on the LP64 layout the kernel documents; the module
# refuses another one rather than pass the kernel a structure of the wrong size.
LAYOUT = {
    "v4l2_capability": 104,
    "v4l2_format": 208,
    "v4l2_requestbuffers": 20,
    "v4l2_buffer": 88,
    "v4l2_streamparm": 204,
}

DEFAULT_BUFFERS = 4
KEEP_FRAMES = 64  # the newest frames the capture thread holds for the session
DEFAULT_STALL_MS = 1000.0
FPS_TOLERANCE = 0.02  # the driver's frame rate may differ from the declared one by 2 %


def layout_problem() -> str | None:
    """Why this process cannot talk V4L2 (a structure of another size than the kernel's)."""
    sizes = {
        "v4l2_capability": ctypes.sizeof(v4l2_capability),
        "v4l2_format": ctypes.sizeof(v4l2_format),
        "v4l2_requestbuffers": ctypes.sizeof(v4l2_requestbuffers),
        "v4l2_buffer": ctypes.sizeof(v4l2_buffer),
        "v4l2_streamparm": ctypes.sizeof(v4l2_streamparm),
    }
    wrong = {name: (got, LAYOUT[name]) for name, got in sizes.items() if got != LAYOUT[name]}
    if not wrong:
        return None
    return "; ".join(
        f"{name} is {got} bytes here, {want} in the kernel" for name, (got, want) in wrong.items()
    )


# -- the seam to the kernel ---------------------------------------------------------------


class KernelIO(Protocol):
    """What the camera needs of the kernel; `tests/test_v4l2.py` supplies a fake one."""

    def open(self, path: str) -> int: ...
    def close(self, fd: int) -> None: ...
    def ioctl(self, fd: int, request: int, arg: Any) -> None: ...
    def mmap(self, fd: int, length: int, offset: int) -> Any: ...
    def wait(self, fd: int, timeout_s: float) -> bool: ...


class SystemIO:
    """The real kernel: `os`, `fcntl`, `mmap`, `select`."""

    def open(self, path: str) -> int:
        return os.open(path, os.O_RDWR | os.O_NONBLOCK)

    def close(self, fd: int) -> None:
        os.close(fd)

    def ioctl(self, fd: int, request: int, arg: Any) -> None:
        while True:
            try:
                fcntl.ioctl(fd, request, arg)
                return
            except InterruptedError:
                continue

    def mmap(self, fd: int, length: int, offset: int) -> Any:
        return mmap.mmap(fd, length, mmap.MAP_SHARED, mmap.PROT_READ, offset=offset)

    def wait(self, fd: int, timeout_s: float) -> bool:
        readable, _, _ = select.select([fd], [], [], timeout_s)
        return bool(readable)


def _error(where: str, why: str, how: str) -> CameraUnavailable:
    return CameraUnavailable(where=where, why=why, how=how)


SETUP_HINT = (
    "connect a camera, or create a virtual one with scripts/setup_vivid.sh (kernel module `vivid`)"
)


def _tpf(fps: float) -> Fraction:
    """The seconds per frame of `fps`, as the kernel's `timeperframe` fraction."""
    return (1 / Fraction(fps)).limit_denominator(10_000)


def probe(path: str, *, io: KernelIO | None = None) -> str:
    """
    Check that `path` is a V4L2 video-capture node that can stream, and name it (the driver's
    card). Opens and closes it; starts nothing. `CameraUnavailable` otherwise — before a session
    holds a line (Q-16).
    """
    io = io or SystemIO()
    problem = layout_problem()
    if problem is not None:
        raise _error(path, f"this process cannot speak V4L2: {problem}", "use a 64-bit userspace")
    try:
        fd = io.open(path)
    except OSError as exc:
        raise _error(
            path,
            f"cannot open the camera: {exc.strerror or exc}",
            f"{SETUP_HINT}; check the user may read and write the node (group `video`)",
        ) from exc
    try:
        cap = v4l2_capability()
        try:
            io.ioctl(fd, VIDIOC_QUERYCAP, cap)
        except OSError as exc:
            raise _error(
                path,
                f"VIDIOC_QUERYCAP failed ({exc.strerror or exc}): not a V4L2 device",
                SETUP_HINT,
            ) from exc
        caps = cap.device_caps if cap.capabilities & V4L2_CAP_DEVICE_CAPS else cap.capabilities
        if not caps & V4L2_CAP_VIDEO_CAPTURE or not caps & V4L2_CAP_STREAMING:
            raise _error(
                path,
                f"{cap.card.decode(errors='replace')!r} does not stream video capture "
                f"(capabilities {caps:#x})",
                "name a capture node: `v4l2-ctl --list-devices` shows them (a metadata node of the "
                "same camera is not one)",
            )
        return cap.card.decode(errors="replace")
    finally:
        io.close(fd)


class V4L2Camera:
    """A `Camera` (`hal/vision.py`) over a V4L2 capture node. See the module docstring."""

    def __init__(
        self,
        path: str,
        mode: Mode,
        clock: Callable[[], float],
        *,
        io: KernelIO | None = None,
        buffers: int = DEFAULT_BUFFERS,
        stall_ms: float = DEFAULT_STALL_MS,
        start_thread: bool = True,
    ) -> None:
        self.path, self.mode, self.clock = path, mode, clock
        self.io = io or SystemIO()
        self.stall_ms = stall_ms
        self.card = ""
        self._fd = -1
        self._maps: list[Any] = []
        self._queued: deque[CameraFrame] = deque(maxlen=KEEP_FRAMES)
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._failure: CameraUnavailable | None = None
        self._streaming = False
        self.closed = False
        self.dropped = 0  # frames the driver flagged as errors
        try:
            self._open(buffers)
        except BaseException:
            self._release()
            raise
        self._last_ms = clock()  # the camera is expected to deliver within stall_ms of now
        if start_thread:
            self._thread = threading.Thread(
                target=self._capture, name="neuroedge-v4l2", daemon=True
            )
            self._thread.start()

    # -- opening ---------------------------------------------------------------------
    def _open(self, buffers: int) -> None:
        path, mode, io = self.path, self.mode, self.io
        format_code = FOURCC.get(mode.pixel_format)
        if format_code is None:
            raise _error(
                path, f"no V4L2 format for pixel_format {mode.pixel_format!r}", "use a board mode"
            )
        self.card = probe(path, io=io)
        try:
            self._fd = io.open(path)
        except OSError as exc:
            raise _error(
                path, f"cannot open the camera: {exc.strerror or exc}", SETUP_HINT
            ) from exc
        fmt = v4l2_format()
        fmt.type = V4L2_BUF_TYPE_VIDEO_CAPTURE
        fmt.pix.width, fmt.pix.height = mode.width, mode.height
        fmt.pix.pixelformat, fmt.pix.field = format_code, V4L2_FIELD_NONE
        self._call(VIDIOC_S_FMT, fmt, "VIDIOC_S_FMT", f"the camera cannot run {mode}")
        got = (fmt.pix.width, fmt.pix.height, fmt.pix.pixelformat)
        if got != (mode.width, mode.height, format_code):
            raise _error(
                path,
                f"{self.card!r} answered {fmt.pix.width}x{fmt.pix.height} format "
                f"{fmt.pix.pixelformat:#x} to a request for {mode}: the declared mode is not "
                "what the camera does",
                "fix the board's vision_in.modes to what this camera runs, or use another camera",
            )
        parm = v4l2_streamparm()
        parm.type = V4L2_BUF_TYPE_VIDEO_CAPTURE
        wanted = _tpf(mode.fps)
        parm.capture.timeperframe.numerator = wanted.numerator
        parm.capture.timeperframe.denominator = wanted.denominator
        self._call(VIDIOC_S_PARM, parm, "VIDIOC_S_PARM", f"the camera cannot set {mode.fps:g} fps")
        tpf = parm.capture.timeperframe
        if tpf.numerator == 0 or tpf.denominator == 0:
            raise _error(
                path, "the camera reported no frame rate", "use a camera that reports its rate"
            )
        actual = tpf.denominator / tpf.numerator
        if abs(actual - mode.fps) > FPS_TOLERANCE * mode.fps:
            raise _error(
                path,
                f"{self.card!r} runs at {actual:g} fps, and the board declares {mode.fps:g} fps for {mode}",
                "fix the board's vision_in.modes to the rate this camera runs",
            )
        request = v4l2_requestbuffers()
        request.count, request.type, request.memory = (
            buffers,
            V4L2_BUF_TYPE_VIDEO_CAPTURE,
            V4L2_MEMORY_MMAP,
        )
        self._call(
            VIDIOC_REQBUFS, request, "VIDIOC_REQBUFS", "the camera cannot stream into mmap buffers"
        )
        if request.count < 2:
            raise _error(
                path,
                f"the driver gave {request.count} buffer(s); streaming needs two",
                "use another camera",
            )
        for index in range(request.count):
            buf = v4l2_buffer()
            buf.type, buf.memory, buf.index = V4L2_BUF_TYPE_VIDEO_CAPTURE, V4L2_MEMORY_MMAP, index
            self._call(
                VIDIOC_QUERYBUF, buf, "VIDIOC_QUERYBUF", "the camera cannot describe its buffers"
            )
            self._maps.append(io.mmap(self._fd, buf.length, buf.m & 0xFFFFFFFF))
            self._call(VIDIOC_QBUF, buf, "VIDIOC_QBUF", "the camera cannot queue its buffers")
        kind = ctypes.c_int(V4L2_BUF_TYPE_VIDEO_CAPTURE)
        self._call(VIDIOC_STREAMON, kind, "VIDIOC_STREAMON", "the camera cannot start streaming")
        self._streaming = True

    def _call(self, request: int, arg: Any, name: str, what: str) -> None:
        try:
            self.io.ioctl(self._fd, request, arg)
        except OSError as exc:
            raise _error(
                self.path,
                f"{what}: {name} failed ({errno.errorcode.get(exc.errno or 0, exc.errno)}: {exc.strerror})",
                SETUP_HINT,
            ) from exc

    # -- capturing -------------------------------------------------------------------
    def _capture(self) -> None:
        """The capture thread: step until stopped; any failure ends the camera, loudly."""
        while not self._stop.is_set() and self._failure is None:
            self._step(0.1)

    def _step(self, timeout_s: float) -> None:
        """Wait for a frame, dequeue it and keep it; a failure is remembered, not raised."""
        try:
            if not self.io.wait(self._fd, timeout_s):
                return
            frame = self._dequeue()
        except CameraUnavailable as error:
            self._failure = error
            return
        except OSError as exc:
            self._failure = _error(
                self.path,
                f"the camera stopped answering ({errno.errorcode.get(exc.errno or 0, exc.errno)}: {exc.strerror})",
                f"check the cable and the node; {SETUP_HINT}",
            )
            return
        if frame is not None:
            with self._lock:
                self._queued.append(frame)
                self._last_ms = frame.captured_ms

    def _dequeue(self) -> CameraFrame | None:
        buf = v4l2_buffer()
        buf.type, buf.memory = V4L2_BUF_TYPE_VIDEO_CAPTURE, V4L2_MEMORY_MMAP
        try:
            self.io.ioctl(self._fd, VIDIOC_DQBUF, buf)
        except BlockingIOError:
            return None
        captured = self.clock()  # when the HAL read it: on the session's clock
        if buf.index >= len(self._maps):
            raise _error(
                self.path,
                f"the driver returned buffer {buf.index}, and only {len(self._maps)} were queued",
                "the stream is out of step with the driver: reopen the camera",
            )
        try:
            if buf.flags & V4L2_BUF_FLAG_ERROR:
                self.dropped += 1  # a corrupt frame is a frame that never came
                return None
            used = buf.bytesused
            expected = self.mode.frame_bytes
            if expected is not None and used != expected:
                raise _error(
                    self.path,
                    f"a frame has {used} bytes; a {self.mode} frame has {expected}",
                    "the driver changed the format under the stream: reopen the camera",
                )
            pixels = bytes(self._maps[buf.index][:used])
        finally:
            self.io.ioctl(self._fd, VIDIOC_QBUF, buf)  # always hand the buffer back
        return CameraFrame(
            buf.sequence,
            captured,
            pixels,
            self.mode.width,
            self.mode.height,
            self.mode.pixel_format,
        )

    def read_available(self) -> list[CameraFrame]:
        if self.closed:
            raise _error(
                self.path, "the camera is closed", "open it again with hal.vision_in(mode)"
            )
        if self._failure is not None:
            raise self._failure
        with self._lock:
            frames = list(self._queued)
            self._queued.clear()
            last = self._last_ms
        if not frames and self.clock() - last > self.stall_ms:
            raise _error(
                self.path,
                f"no frame for {self.clock() - last:.0f} ms (stall limit {self.stall_ms:g} ms): "
                "the camera has stopped",
                f"check the cable and the node; {SETUP_HINT}",
            )
        return frames

    # -- closing ---------------------------------------------------------------------
    def _release(self) -> None:
        if self._streaming:
            with contextlib.suppress(OSError):
                self.io.ioctl(self._fd, VIDIOC_STREAMOFF, ctypes.c_int(V4L2_BUF_TYPE_VIDEO_CAPTURE))
            self._streaming = False
        for view in self._maps:
            with contextlib.suppress(Exception):
                view.close()
        self._maps = []
        if self._fd >= 0:
            with contextlib.suppress(OSError):
                self.io.close(self._fd)
            self._fd = -1

    def close(self) -> None:
        """Stop the thread, turn the stream off, release the buffers and the node. Idempotent."""
        if self.closed:
            return
        self.closed = True
        self._stop.set()
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join(timeout=2.0)
        self._release()
