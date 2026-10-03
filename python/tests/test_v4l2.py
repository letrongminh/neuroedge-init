"""
TSK-V1b-01 — V4L2 capture in pure Python (hal/v4l2.py), without a kernel.

The real device is tested in CI against `vivid` (`tests_linux/test_camera_v4l2.py`,
`scripts/setup_vivid.sh`); this file runs the same code against a *fake kernel* behind the `io`
seam, so the protocol — which ioctl, in which order, with what — is checked on every machine:
the structure sizes and request numbers the kernel documents, the declared mode being the mode
the camera runs, frame numbers that are the driver's, and a camera that stops, vanishes or
corrupts a frame making `read_available()` raise instead of invent.
"""

from __future__ import annotations

import ctypes
import errno

import pytest

from neuroedge.hal import v4l2
from neuroedge.hal.v4l2 import V4L2Camera
from neuroedge.hal.vision import CameraUnavailable, Mode

from .vision_support import FakeClock

MODE = Mode(4, 2, 30.0, "gray8")  # 8-byte frames
FOURCC_GREY = v4l2.FOURCC["gray8"]


class FakeMap:
    """What `mmap` returns: sliceable bytes with a `close()`."""

    def __init__(self, size: int) -> None:
        self.data = bytearray(size)
        self.closed = False

    def __getitem__(self, key):
        return self.data[key]

    def close(self) -> None:
        self.closed = True


class FakeKernel:
    """A V4L2 capture driver: answers the ioctls of `hal/v4l2.py`, and queues what a test puts."""

    def __init__(self, *, fps: float = 30.0) -> None:
        self.fps = fps
        self.calls: list[str] = []
        self.caps = (
            v4l2.V4L2_CAP_VIDEO_CAPTURE | v4l2.V4L2_CAP_STREAMING | v4l2.V4L2_CAP_DEVICE_CAPS
        )
        self.round_size_to: tuple[int, int] | None = None
        self.answer_format: int | None = None
        self.buffer_count = 4
        self.maps: list[FakeMap] = []
        self.ready: list[tuple[int, bytes, int]] = []  # (sequence, pixels, flags)
        self.in_flight: set[int] = set()
        self.streaming = False
        self.dead: OSError | None = None
        self.open_fds: set[int] = set()
        self.refuse: dict[int, int] = {}  # request → errno

    # -- the seam ------------------------------------------------------------------
    def open(self, path: str) -> int:
        if path != "/dev/video9":
            raise FileNotFoundError(errno.ENOENT, "No such file or directory", path)
        self.calls.append("open")
        fd = 40 + len(self.open_fds)
        self.open_fds.add(fd)
        return fd

    def close(self, fd: int) -> None:
        self.calls.append("close")
        self.open_fds.discard(fd)

    def mmap(self, fd: int, length: int, offset: int) -> FakeMap:
        self.calls.append(f"mmap {offset}")
        fake = FakeMap(length)
        self.maps.append(fake)
        return fake

    def wait(self, fd: int, timeout_s: float) -> bool:
        if self.dead is not None:
            raise self.dead
        return bool(self.ready)

    def ioctl(self, fd: int, request: int, arg) -> None:
        if request in self.refuse:
            raise OSError(self.refuse[request], "refused")
        if request == v4l2.VIDIOC_QUERYCAP:
            self.calls.append("QUERYCAP")
            arg.card = b"Fake Camera"
            arg.capabilities = self.caps | v4l2.V4L2_CAP_DEVICE_CAPS
            arg.device_caps = self.caps
        elif request == v4l2.VIDIOC_S_FMT:
            self.calls.append("S_FMT")
            assert arg.type == v4l2.V4L2_BUF_TYPE_VIDEO_CAPTURE
            if self.round_size_to:
                arg.pix.width, arg.pix.height = self.round_size_to
            if self.answer_format is not None:
                arg.pix.pixelformat = self.answer_format
            self.format = (arg.pix.width, arg.pix.height, arg.pix.pixelformat)
        elif request == v4l2.VIDIOC_S_PARM:
            self.calls.append("S_PARM")
            from fractions import Fraction

            tpf = (1 / Fraction(self.fps)).limit_denominator(10_000)
            arg.capture.timeperframe.numerator, arg.capture.timeperframe.denominator = (
                tpf.numerator,
                tpf.denominator,
            )
        elif request == v4l2.VIDIOC_REQBUFS:
            self.calls.append("REQBUFS")
            arg.count = self.buffer_count
        elif request == v4l2.VIDIOC_QUERYBUF:
            self.calls.append("QUERYBUF")
            arg.length, arg.m = 4096, 4096 * (arg.index + 1)
        elif request == v4l2.VIDIOC_QBUF:
            self.calls.append("QBUF")
            self.in_flight.add(arg.index)
        elif request == v4l2.VIDIOC_STREAMON:
            self.calls.append("STREAMON")
            self.streaming = True
        elif request == v4l2.VIDIOC_STREAMOFF:
            self.calls.append("STREAMOFF")
            self.streaming = False
        elif request == v4l2.VIDIOC_DQBUF:
            if self.dead is not None:
                raise self.dead
            if not self.ready:
                raise BlockingIOError(errno.EAGAIN, "try again")
            sequence, pixels, flags = self.ready.pop(0)
            index = min(self.in_flight)
            self.in_flight.discard(index)
            self.maps[index].data[: len(pixels)] = pixels
            arg.index, arg.bytesused, arg.sequence, arg.flags = index, len(pixels), sequence, flags
            self.calls.append(f"DQBUF {sequence}")
        else:  # pragma: no cover - a request the module should never send
            raise AssertionError(f"unexpected ioctl {request:#x}")

    def put(self, sequence: int, fill: int, *, flags: int = 0, size: int | None = None) -> None:
        self.ready.append((sequence, bytes([fill]) * (size or MODE.frame_bytes), flags))


def open_camera(kernel: FakeKernel | None = None, clock: FakeClock | None = None, **kw):
    kernel = kernel or FakeKernel()
    clock = clock or FakeClock()
    camera = V4L2Camera("/dev/video9", MODE, clock, io=kernel, start_thread=False, **kw)
    return camera, kernel, clock


# -- the kernel's own numbers --------------------------------------------------------------


def test_the_structures_are_the_size_the_kernel_documents():
    assert v4l2.layout_problem() is None
    assert {name: ctypes.sizeof(getattr(v4l2, name)) for name in v4l2.LAYOUT} == v4l2.LAYOUT
    assert ctypes.sizeof(v4l2.v4l2_pix_format) == 48


def test_the_ioctl_numbers_are_the_ones_of_videodev2_h():
    # Quoted from <linux/videodev2.h> on a 64-bit kernel.
    assert v4l2.VIDIOC_QUERYCAP == 0x80685600
    assert v4l2.VIDIOC_S_FMT == 0xC0D05605
    assert v4l2.VIDIOC_REQBUFS == 0xC0145608
    assert v4l2.VIDIOC_QUERYBUF == 0xC0585609
    assert v4l2.VIDIOC_QBUF == 0xC058560F
    assert v4l2.VIDIOC_DQBUF == 0xC0585611
    assert v4l2.VIDIOC_STREAMON == 0x40045612
    assert v4l2.VIDIOC_STREAMOFF == 0x40045613
    assert v4l2.VIDIOC_S_PARM == 0xC0CC5616


def test_the_board_pixel_formats_are_the_kernels_fourccs():
    assert set(v4l2.FOURCC) == {"yuyv", "mjpeg", "rgb565", "rgb888", "gray8"}  # RFC-0012 §9.1
    assert v4l2.FOURCC["yuyv"] == 0x56595559  # 'YUYV'
    assert v4l2.FOURCC["gray8"] == 0x59455247  # 'GREY'


# -- opening: the declared mode is the mode the camera runs --------------------------------


def test_opening_runs_the_protocol_in_order_and_streams():
    camera, kernel, _ = open_camera()
    order = [c for c in kernel.calls if c not in ("open", "close") and not c.startswith("mmap")]
    assert order == [
        "QUERYCAP",
        "S_FMT",
        "S_PARM",
        "REQBUFS",
        *["QUERYBUF", "QBUF"] * 4,
        "STREAMON",
    ]
    assert order[-1] == "STREAMON" and kernel.streaming
    assert kernel.format == (4, 2, FOURCC_GREY)
    assert camera.card == "Fake Camera" and len(kernel.maps) == 4
    camera.close()


def test_a_node_that_does_not_exist_is_a_three_part_error(tmp_path):
    with pytest.raises(CameraUnavailable) as refused:
        V4L2Camera("/dev/video0", MODE, FakeClock(), io=FakeKernel(), start_thread=False)
    error = refused.value
    assert "cannot open the camera" in error.why and error.how and error.where == "/dev/video0"


def test_a_node_that_does_not_capture_is_refused():
    kernel = FakeKernel()
    kernel.caps = v4l2.V4L2_CAP_STREAMING  # a metadata node of a camera
    with pytest.raises(CameraUnavailable, match="does not stream video capture"):
        open_camera(kernel)


def test_a_driver_that_rounds_the_size_is_refused_not_accepted_as_close_enough():
    kernel = FakeKernel()
    kernel.round_size_to = (640, 480)
    with pytest.raises(CameraUnavailable, match="the declared mode is not what the camera does"):
        open_camera(kernel)
    assert not kernel.streaming and not kernel.open_fds  # nothing is left held


def test_a_driver_that_picks_another_format_is_refused():
    kernel = FakeKernel()
    kernel.answer_format = v4l2.FOURCC["yuyv"]
    with pytest.raises(CameraUnavailable, match="the declared mode is not what the camera does"):
        open_camera(kernel)


def test_a_driver_at_another_frame_rate_is_refused_but_a_rounding_is_not():
    with pytest.raises(CameraUnavailable, match="runs at 15 fps, and the board declares 30 fps"):
        open_camera(FakeKernel(fps=15.0))
    camera, _, _ = open_camera(FakeKernel(fps=29.97))  # NTSC 30 within 2 %
    camera.close()


def test_a_fractional_rate_is_asked_as_an_exact_fraction():
    mode = Mode(4, 2, 7.5, "gray8")
    kernel = FakeKernel(fps=7.5)
    V4L2Camera("/dev/video9", mode, FakeClock(), io=kernel, start_thread=False).close()


def test_an_ioctl_that_fails_while_opening_releases_everything():
    kernel = FakeKernel()
    kernel.refuse[v4l2.VIDIOC_REQBUFS] = errno.EINVAL
    with pytest.raises(CameraUnavailable, match="VIDIOC_REQBUFS failed"):
        open_camera(kernel)
    assert not kernel.open_fds and not kernel.streaming


def test_too_few_buffers_cannot_stream():
    kernel = FakeKernel()
    kernel.buffer_count = 1
    with pytest.raises(CameraUnavailable, match="streaming needs two"):
        open_camera(kernel)


# -- capturing ----------------------------------------------------------------------------


def test_frames_carry_the_drivers_sequence_the_sessions_clock_and_the_bytes():
    camera, kernel, clock = open_camera()
    kernel.put(7, 0xAA)
    kernel.put(8, 0xBB)
    clock.advance(10)
    camera._step(0)
    clock.advance(33)
    camera._step(0)
    frames = camera.read_available()
    assert [f.seq for f in frames] == [7, 8]
    assert [f.captured_ms for f in frames] == [1010.0, 1043.0]
    assert frames[0].pixels == b"\xaa" * 8 and frames[1].pixels == b"\xbb" * 8
    assert (frames[0].width, frames[0].height, frames[0].pixel_format) == (4, 2, "gray8")
    assert camera.read_available() == []  # drained


def test_a_frame_the_driver_dropped_is_a_jump_in_the_numbers():
    camera, kernel, _ = open_camera()
    for seq in (1, 2, 5):  # 3 and 4 never came
        kernel.put(seq, seq)
        camera._step(0)
    assert [f.seq for f in camera.read_available()] == [1, 2, 5]


def test_every_buffer_goes_back_to_the_driver():
    camera, kernel, _ = open_camera()
    for seq in range(10):
        kernel.put(seq, seq)
        camera._step(0)
    assert len(kernel.in_flight) == 4  # none leaked: the driver never starves


def test_a_frame_flagged_as_an_error_is_dropped_not_repaired():
    camera, kernel, _ = open_camera()
    kernel.put(1, 1)
    kernel.put(2, 2, flags=v4l2.V4L2_BUF_FLAG_ERROR)
    kernel.put(3, 3)
    for _ in range(3):
        camera._step(0)
    assert [f.seq for f in camera.read_available()] == [1, 3] and camera.dropped == 1


def test_a_raw_frame_of_the_wrong_size_ends_the_camera():
    camera, kernel, _ = open_camera()
    kernel.put(1, 1, size=5)
    camera._step(0)
    with pytest.raises(
        CameraUnavailable, match="a frame has 5 bytes; a 4x2 @ 30 fps gray8 frame has 8"
    ):
        camera.read_available()


def test_the_camera_is_unavailable_when_the_device_vanishes():
    camera, kernel, _ = open_camera()
    kernel.dead = OSError(errno.ENODEV, "No such device")
    camera._step(0)
    with pytest.raises(CameraUnavailable, match="stopped answering"):
        camera.read_available()


def test_a_camera_that_goes_quiet_is_unavailable_after_the_stall_limit():
    camera, kernel, clock = open_camera(stall_ms=1000)
    clock.advance(999)
    assert camera.read_available() == []  # slow is not gone
    clock.advance(2)
    with pytest.raises(CameraUnavailable, match="no frame for 1001 ms"):
        camera.read_available()


def test_a_frame_resets_the_stall_clock():
    camera, kernel, clock = open_camera(stall_ms=1000)
    clock.advance(900)
    kernel.put(1, 1)
    camera._step(0)
    clock.advance(900)
    assert [f.seq for f in camera.read_available()] == [1]


def test_close_stops_the_stream_releases_the_buffers_and_is_idempotent():
    camera, kernel, _ = open_camera()
    camera.close()
    camera.close()
    assert not kernel.streaming and not kernel.open_fds
    assert all(m.closed for m in kernel.maps)
    with pytest.raises(CameraUnavailable, match="closed"):
        camera.read_available()


def test_the_capture_thread_delivers_and_stops_on_close():
    kernel = FakeKernel()
    clock = FakeClock()
    camera = V4L2Camera("/dev/video9", MODE, clock, io=kernel)
    try:
        kernel.put(1, 9)
        deadline = __import__("time").monotonic() + 5
        frames: list = []
        while not frames and __import__("time").monotonic() < deadline:
            frames = camera.read_available()
        assert [f.seq for f in frames] == [1]
    finally:
        camera.close()
    assert camera._thread is not None and not camera._thread.is_alive()


def test_probe_names_a_capture_node_and_refuses_anything_else():
    assert v4l2.probe("/dev/video9", io=FakeKernel()) == "Fake Camera"
    with pytest.raises(CameraUnavailable, match="cannot open the camera"):
        v4l2.probe("/dev/video0", io=FakeKernel())
    metadata = FakeKernel()
    metadata.caps = 0
    with pytest.raises(CameraUnavailable, match="does not stream video capture"):
        v4l2.probe("/dev/video9", io=metadata)


def test_a_buffer_index_the_driver_never_queued_ends_the_camera():
    camera, kernel, _ = open_camera()
    kernel.put(1, 1)
    real = kernel.ioctl

    def lying(fd, request, arg):
        real(fd, request, arg)
        if request == v4l2.VIDIOC_DQBUF:
            arg.index = 99

    kernel.ioctl = lying  # type: ignore[method-assign]
    camera._step(0)
    with pytest.raises(CameraUnavailable, match="returned buffer 99"):
        camera.read_available()
