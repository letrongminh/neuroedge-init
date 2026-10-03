"""
TSK-V1b-02 — the virtual camera of `sim` (RFC-0012 §3f, sim/vision/camera.py).

It replays a recording on the session's clock, in a mode of the board, no better than the
hardware it stands for: frames at the mode's rate and no faster, a driver-like queue whose
overwritten frames are a *jump in the numbers*, raw frames of exactly the mode's size, and a
camera that is gone when the recording is. A fake clock drives it: it never sleeps.
"""

from __future__ import annotations

import pytest

from neuroedge.errors import AgentManifestError, BoardCapabilityError, PerceptionUnavailableError
from neuroedge.hal import load_board_by_id
from neuroedge.hal.sim import SimHAL
from neuroedge.hal.vision import CameraUnavailable, Mode, modes_of
from neuroedge.sim.vision import (
    ImageSequence,
    SyntheticSequence,
    VirtualCamera,
    parse_sim_vision,
)

from .vision_support import FakeClock  # noqa: E402

TINY = Mode(4, 4, 10.0, "gray8")  # 100 ms per frame, 16-byte frames
PERIOD = 100.0


def raw(n: int) -> bytes:
    return bytes([n]) * TINY.frame_bytes


def camera(
    frames: int = 8, clock: FakeClock | None = None, **kw
) -> tuple[VirtualCamera, FakeClock]:
    clock = clock or FakeClock()
    source = ImageSequence(tuple(raw(i) for i in range(frames)))
    return VirtualCamera(source, TINY, clock, **kw), clock


def seqs(frames) -> list[int]:
    return [f.seq for f in frames]


def test_frames_become_ready_at_the_mode_rate_and_no_faster():
    cam, clock = camera()
    assert cam.read_available() == []  # streaming has just started: no frame yet
    clock.advance(PERIOD - 1)
    assert cam.read_available() == []
    clock.advance(1)
    first = cam.read_available()
    assert seqs(first) == [0] and first[0].captured_ms == 1000.0 + PERIOD
    clock.advance(PERIOD)
    assert seqs(cam.read_available()) == [1]
    assert cam.read_available() == []  # asking again before the next period gives nothing


def test_a_frame_carries_its_mode_and_the_bytes_of_the_recording():
    cam, clock = camera()
    clock.advance(PERIOD)
    (frame,) = cam.read_available()
    assert (frame.width, frame.height, frame.pixel_format) == (4, 4, "gray8")
    assert frame.pixels == raw(0)


def test_a_late_reader_finds_the_newest_frames_and_a_jump_in_the_numbers():
    cam, clock = camera(frames=20, depth=4)
    clock.advance(PERIOD * 2.5)
    assert seqs(cam.read_available()) == [0, 1]
    clock.advance(PERIOD * 10)  # the reader sleeps through ten frames
    got = seqs(cam.read_available())
    # a real driver's queue holds `depth` frames: the older ones were overwritten, and the
    # numbers say so — never the old frames presented as new
    assert got == [8, 9, 10, 11] and got[0] > 2


def test_frames_the_camera_loses_are_gaps_not_repeats():
    cam, clock = camera(drop={2, 3}, depth=8)
    clock.advance(PERIOD * 6)
    assert seqs(cam.read_available()) == [0, 1, 4, 5]


def test_a_camera_ends_with_its_recording_after_delivering_what_it_captured():
    cam, clock = camera(frames=3)
    clock.advance(PERIOD * 10)
    assert seqs(cam.read_available()) == [0, 1, 2]  # the queue still holds the last frames
    with pytest.raises(CameraUnavailable, match="recording ended after 3 frame"):
        cam.read_available()  # then it is gone: no frame is invented, nothing loops


def test_loop_repeats_the_recording_and_one_frame_is_a_frozen_camera():
    cam, clock = camera(frames=2, loop=True)
    clock.advance(PERIOD * 4)
    got = cam.read_available()
    assert seqs(got) == [0, 1, 2, 3]
    assert [f.pixels for f in got] == [raw(0), raw(1), raw(0), raw(1)]
    still, clock = camera(frames=1, loop=True)
    clock.advance(PERIOD * 3)
    assert len({f.pixels for f in still.read_available()}) == 1  # the perception refuses this


def test_a_raw_frame_of_the_wrong_size_is_not_a_frame_of_this_camera():
    clock = FakeClock()
    cam = VirtualCamera(ImageSequence((b"short",)), TINY, clock)
    clock.advance(PERIOD)
    with pytest.raises(CameraUnavailable, match="has 5 bytes; a 4x4 @ 10 fps gray8 frame has 16"):
        cam.read_available()


def test_a_compressed_mode_takes_any_frame_size():
    mjpeg = Mode(4, 4, 10.0, "mjpeg")
    clock = FakeClock()
    cam = VirtualCamera(ImageSequence((b"\xff\xd8abc", b"\xff\xd8abcdef")), mjpeg, clock)
    clock.advance(PERIOD * 2)
    assert [len(f.pixels) for f in cam.read_available()] == [5, 8]


def test_a_closed_camera_is_unavailable():
    cam, clock = camera()
    cam.close()
    with pytest.raises(CameraUnavailable, match="closed"):
        cam.read_available()


def test_camera_unavailable_is_the_perception_error_ne5001():
    assert issubclass(CameraUnavailable, PerceptionUnavailableError)
    assert CameraUnavailable.code == "NE5001"


def test_the_synthetic_recording_is_deterministic_exact_sized_and_never_repeats():
    mode = Mode(16, 8, 30.0, "rgb888")
    source = SyntheticSequence(mode, 5)
    frames = [source.frame(i) for i in range(5)]
    assert {len(f) for f in frames} == {16 * 8 * 3}
    assert len(set(frames)) == 5
    assert frames == [SyntheticSequence(mode, 5).frame(i) for i in range(5)]


def test_a_directory_of_frames_is_read_in_natural_order(tmp_path):
    for name, byte in (("frame10.raw", 10), ("frame2.raw", 2), ("frame1.raw", 1), (".hidden", 99)):
        (tmp_path / name).write_bytes(bytes([byte]) * 16)
    source = ImageSequence.from_directory(tmp_path)
    assert [f[0] for f in source.frames] == [1, 2, 10]


def test_an_empty_or_missing_directory_is_refused_with_three_parts(tmp_path):
    for path in (tmp_path, tmp_path / "nope"):
        with pytest.raises(AgentManifestError) as refused:
            ImageSequence.from_directory(path)
        assert refused.value.where and refused.value.why and refused.value.how


@pytest.mark.parametrize(
    "table",
    [
        {"source": ""},
        {"frames": 0},
        {"frames": "ten"},
        {"depth": 0},
        {"depth": 1000},
        {"loop": "yes"},
        {"drop": [1, -2]},
        {"drop": "7"},
        {"colour": "red"},
        ["not", "a", "table"],
    ],
)
def test_a_bad_sim_vision_table_is_refused(table, tmp_path):
    with pytest.raises(AgentManifestError):
        parse_sim_vision(table, tmp_path)


# -- the HAL seam: `sim` is never richer than the board it mirrors ------------------------


@pytest.fixture
def rpi5():
    board = load_board_by_id("sim-rpi5")
    hal = SimHAL(board)
    hal.attach_camera(parse_sim_vision({"source": "synthetic", "frames": 12}, ".").factory())
    return hal, modes_of(board.vision_modes)


def test_the_hal_opens_a_camera_only_in_a_mode_the_board_declares(rpi5):
    hal, modes = rpi5
    clock = FakeClock()
    camera = hal.vision_in(modes[0], clock=clock)
    assert camera.mode == modes[0]
    with pytest.raises(BoardCapabilityError, match="declares no camera mode 800x600"):
        hal.vision_in(Mode(800, 600, 30.0, "rgb888"), clock=clock)  # richer than the board


def test_a_board_without_a_camera_refuses_vision_in():
    hal = SimHAL(load_board_by_id("sim-default"))  # mirrors the Box-3: no camera (invariant #7)
    with pytest.raises(BoardCapabilityError, match="does not declare the 'vision.in' primitive"):
        hal.vision_in(Mode(640, 480, 30.0, "rgb888"))


def test_with_no_recording_attached_the_simulator_has_no_camera():
    board = load_board_by_id("sim-rpi5")
    hal = SimHAL(board)
    with pytest.raises(CameraUnavailable, match="reads no camera of its own"):
        hal.vision_in(modes_of(board.vision_modes)[0])


def test_a_hal_without_the_primitive_says_where_to_look():
    from neuroedge.hal import HardwareAbstractionLayer

    with pytest.raises(BoardCapabilityError, match="vision.in is not implemented"):
        HardwareAbstractionLayer("sim").vision_in(TINY)


def test_closing_the_hal_closes_its_cameras(rpi5):
    hal, modes = rpi5
    camera = hal.vision_in(modes[0], clock=FakeClock())
    hal.close()
    assert camera.closed
