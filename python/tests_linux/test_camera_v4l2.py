"""
`vision.in` on `linux` against a real kernel (TSK-V1b-01, RFC-0012 §3a, §3e).

Run by the `linux-hal` CI job after `scripts/setup_vivid.sh`, which loads the kernel's virtual
video driver and exports `NEUROEDGE_LINUX_CAMERA` — the node `LinuxHAL` reads, never guessed:

    cd python && python -m pytest -q tests_linux

`vivid` answers the ioctls of a real capture device and streams mmap buffers, so `hal/v4l2.py`
runs here exactly as it will on a Pi's camera: the declared mode asked for and verified, frames
numbered by the driver, a stream that stops cleanly. Its test pattern carries a time stamp and a
frame counter, so no two frames are alike (a frozen camera is what the perception refuses). A
missing device is a failure, never a skip.

NOTE: written without a kernel at hand (the author's machine is not Linux); the protocol itself is
checked on every machine by `tests/test_v4l2.py` against a fake driver. If a vivid detail differs
(a format it does not offer, a rate it rounds), this file is where CI shows it.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import time
from pathlib import Path

import pytest

from neuroedge.actions.tools import ToolCall
from neuroedge.engine.trace_sink import EventLog
from neuroedge.errors import BoardCapabilityError
from neuroedge.hal.linux import CAMERA_ENV, LinuxHAL
from neuroedge.hal.v4l2 import V4L2Camera, probe
from neuroedge.hal.vision import CameraUnavailable, Mode, modes_of
from neuroedge.paths import fixtures_dir
from neuroedge.sim import SimSession
from neuroedge.testing import replay
from neuroedge.trace import validate_trace

AGENT = fixtures_dir() / "agents" / "gate-watch"
RIG = (  # the modes of linux-rpi5's camera: what the board declares is what is asked of the kernel
    Mode(640, 480, 30.0, "rgb888"),
    Mode(1280, 720, 30.0, "yuyv"),
)


def now_ms() -> float:
    return time.monotonic() * 1000.0


def node() -> str:
    value = os.environ.get(CAMERA_ENV)
    assert value, f"{CAMERA_ENV} is not set; run scripts/setup_vivid.sh first"
    return value


def collect(camera: V4L2Camera, count: int, timeout_s: float = 5.0) -> list:
    """At least `count` frames, polling as a session does."""
    frames: list = []
    deadline = time.monotonic() + timeout_s
    while len(frames) < count and time.monotonic() < deadline:
        frames += camera.read_available()
        time.sleep(0.02)
    return frames


def test_the_kernel_names_the_virtual_capture_device():
    assert probe(node()).lower().startswith("vivid")


@pytest.mark.parametrize("mode", RIG, ids=str)
def test_the_camera_runs_exactly_the_mode_the_board_declares(mode):
    camera = V4L2Camera(node(), mode, now_ms)
    try:
        frames = collect(camera, 12)
    finally:
        camera.close()
    assert len(frames) >= 12
    assert {len(f.pixels) for f in frames} == {mode.frame_bytes}
    assert all(
        (f.width, f.height, f.pixel_format) == (mode.width, mode.height, mode.pixel_format)
        for f in frames
    )
    # the driver numbers its frames; a Python reader keeps up with 30 fps, so none may repeat
    seqs = [f.seq for f in frames]
    assert seqs == sorted(set(seqs))
    stamps = [f.captured_ms for f in frames]
    assert stamps == sorted(stamps)
    rate = (seqs[-1] - seqs[0]) / ((stamps[-1] - stamps[0]) / 1000.0)
    assert 0.6 * mode.fps <= rate <= 1.4 * mode.fps  # the declared rate, as vivid paces it
    # a live scene never repeats a frame byte for byte (vivid draws a time stamp)
    assert len({f.pixels for f in frames}) == len(frames)


def test_a_mode_the_driver_will_round_is_refused_not_taken_as_close_enough():
    with pytest.raises(CameraUnavailable, match="the declared mode is not what the camera does"):
        V4L2Camera(node(), Mode(10_000, 10_000, 30.0, "rgb888"), now_ms)


def test_a_node_that_is_not_there_is_a_three_part_error():
    with pytest.raises(CameraUnavailable) as refused:
        V4L2Camera("/dev/video199", RIG[0], now_ms)
    assert refused.value.where == "/dev/video199" and refused.value.how


def test_the_camera_can_be_closed_and_opened_again():
    for _ in range(3):  # a stream left running would answer EBUSY the second time
        camera = V4L2Camera(node(), RIG[0], now_ms)
        assert collect(camera, 3)
        camera.close()


def test_the_hal_opens_the_chosen_node_in_a_mode_of_its_board():
    hal = LinuxHAL(events=EventLog(target="linux", board_id="linux-rpi5"))
    try:
        board_modes = modes_of(hal.board.vision_modes)
        assert board_modes == RIG
        camera = hal.vision_in(RIG[0], called_from="test")
        assert collect(camera, 3)
        with pytest.raises(BoardCapabilityError, match="declares no camera mode"):
            hal.vision_in(Mode(800, 600, 30.0, "rgb888"), called_from="test")
    finally:
        hal.close()
    assert camera.closed  # closing the HAL turns the stream off


def person_everywhere(project: Path) -> Path:
    """A copy of the sample agent whose scripted model sees a person in frames 0-4000."""
    toml = project / "agent.toml"
    text = toml.read_text(encoding="utf-8")
    head = text.split("[vision.options.script]")[0]
    tail = "# Camera ảo của `sim`" + text.split("# Camera ảo của `sim`")[1]
    person = '[{ label = "person", score = 0.93, box = [0.4, 0.5, 0.6, 0.9] }]'
    script = "\n".join(f"{n} = {person}" for n in range(4001))
    toml.write_text(f"{head}[vision.options.script]\n{script}\n\n{tail}", encoding="utf-8")
    return toml


def test_a_session_on_linux_reads_the_camera_and_the_gate_decides(tmp_path):
    project = tmp_path / "gate-watch"
    shutil.copytree(AGENT, project, ignore=shutil.ignore_patterns("__pycache__"))
    toml = person_everywhere(project)
    session = SimSession.load(toml, target="linux")
    try:
        status, deadline = "", time.monotonic() + 8
        while status != "ALLOW" and time.monotonic() < deadline:
            time.sleep(0.1)
            result = asyncio.run(
                session.call_tool(ToolCall("watch_open_gate", {}, source="local_grammar"))
            )
            status = result.content()["status"]
        assert status == "ALLOW", result.content()
        assert session.hal.line_value("gate_relay")  # the kernel line is driven
        trace = session.trace()
    finally:
        session.close()
    validate_trace(trace)
    text = json.dumps(trace)
    assert not re.search(r"[A-Za-z0-9+/]{200,}", text)  # no image bytes, base64 or otherwise
    readings = [
        e["data"] for e in trace["events"] if e["type"] == "vision_fact" and e["data"]["frames"]
    ]
    assert readings and all(
        f["vision_ref"]["size"] == RIG[0].frame_bytes for r in readings for f in r["frames"]
    )
    # what the kernel camera decided, replayed with no camera and no kernel: the labels carry it
    for target, board in (("sim", "sim-rpi5"), ("linux", "linux-rpi5")):
        replayed = replay(trace, agent=toml, target=target, board_id=board)
        assert replayed.verdicts == [
            e["data"]["verdict"] for e in trace["events"] if e["type"] == "gate_evaluation_result"
        ]
