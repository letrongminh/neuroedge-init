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
import subprocess
import time
from pathlib import Path

import pytest

from neuroedge.actions.tools import ToolCall
from neuroedge.engine.trace_sink import EventLog
from neuroedge.errors import BoardCapabilityError
from neuroedge.hal.linux import CAMERA_ENV, LinuxHAL
from neuroedge.hal.v4l2 import DEFAULT_STALL_MS, V4L2Camera, probe
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


@pytest.mark.usefixtures("fresh_actions")
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


VIVID_DRIVER = Path("/sys/bus/platform/drivers/vivid")


def vivid_device() -> str:
    """The platform device `vivid` was loaded as (`n_devs=1`: `vivid.0`), found, not assumed."""
    assert VIVID_DRIVER.is_dir(), f"{VIVID_DRIVER} is missing: is vivid loaded (setup_vivid.sh)?"
    names = sorted(
        entry.name for entry in VIVID_DRIVER.iterdir() if entry.is_symlink() and "." in entry.name
    )
    assert len(names) == 1, f"expected the one vivid device of setup_vivid.sh, found {names}"
    return names[0]


def sudo(*command: str, text: str | None = None, timeout: float = 20.0) -> None:
    """`sudo -n`: the runner has passwordless sudo, as `scripts/setup_*.sh` rely on."""
    done = subprocess.run(
        ["sudo", "-n", *command],
        input=text, text=True, capture_output=True, check=False, timeout=timeout,
    )  # fmt: skip
    assert done.returncode == 0, f"sudo {' '.join(command)}: {done.stdout}{done.stderr}"


def vivid_driver(action: str, device: str) -> None:
    """Unbind or bind the vivid driver from its device: the camera goes away, or comes back."""
    sudo("tee", f"{VIVID_DRIVER}/{action}", text=device)


def restore_the_camera(device: str, path: str) -> None:
    """
    Bind vivid again and make the node usable as `scripts/setup_vivid.sh` leaves it: the node
    comes back under the same number (`vid_cap_nr=42`), udev resets its mode a moment after it
    appears (0660, group video), so settle first and open it up until this user can read it.
    """
    vivid_driver("bind", device)
    deadline = time.monotonic() + 10
    while not Path(path).exists() and time.monotonic() < deadline:
        time.sleep(0.1)
    assert Path(path).exists(), f"{path} did not come back after binding {device}"
    subprocess.run(["sudo", "-n", "udevadm", "settle", "--timeout=10"], check=False, timeout=30)
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        sudo("chmod", "a+rw", path)
        if os.access(path, os.R_OK | os.W_OK):
            break
        time.sleep(0.1)
    assert os.access(path, os.R_OK | os.W_OK), f"{path} is not usable by this user again"
    assert probe(path).lower().startswith("vivid")  # the same device, for the tests that follow


@pytest.mark.usefixtures("fresh_actions")
def test_a_camera_that_disappears_mid_session_blocks_fail_closed_and_does_not_hang(tmp_path):
    """
    Last in the file: it removes the camera. A `linux` session reads frames from vivid and the
    gate ALLOWs; then the vivid platform device is unbound through sysfs (`sudo tee .../unbind`),
    which makes the kernel unregister the video node under the session's open stream — the closest
    CI has to pulling the cable. The next evaluations must BLOCK `criterion_unavailable` (RFC-0012
    §3e: mất camera ⇒ `criterion_unavailable`), within the reader's stall bound plus a margin,
    and no call may hang. The loss is in the trace, and the trace replays. The device is bound
    again in `finally` — after the session has released the node, so the number is free — and
    the node is made usable again, so the tests that follow still have `NEUROEDGE_LINUX_CAMERA`.
    """
    device, path = vivid_device(), node()
    project = tmp_path / "gate-watch"
    shutil.copytree(AGENT, project, ignore=shutil.ignore_patterns("__pycache__"))
    toml = person_everywhere(project)
    bound = True
    try:
        session = SimSession.load(toml, target="linux")
        try:

            def ask() -> dict:
                result = asyncio.run(
                    session.call_tool(ToolCall("watch_open_gate", {}, source="local_grammar"))
                )
                return result.content()

            status, deadline = "", time.monotonic() + 8
            while status != "ALLOW" and time.monotonic() < deadline:
                time.sleep(0.1)
                content = ask()
                status = content["status"]
            assert status == "ALLOW", content  # the camera works, so the loss below is the cause

            vivid_driver("unbind", device)
            bound = False
            gone_at = time.monotonic()
            bound_s = DEFAULT_STALL_MS / 1000.0 + 3.0  # the stall limit, and a margin
            answers = []
            while time.monotonic() - gone_at < bound_s:
                asked = time.monotonic()
                content = ask()
                assert time.monotonic() - asked < 2.0, "a call hung on the lost camera"
                answers.append(content)
                if content["status"] == "BLOCK" and session.events.of_type("camera_unavailable"):
                    break  # blocked, and the session knows why: the camera is the cause
                time.sleep(0.1)
            blocked_after = time.monotonic() - gone_at
            assert answers and answers[-1]["status"] == "BLOCK", (
                f"still {answers[-1:]!r} {blocked_after:.1f} s after the camera was gone"
            )
            assert answers[-1].get("reason") == "criterion_unavailable", answers[-1]
            assert blocked_after < bound_s
            assert session.events.of_type("camera_unavailable"), "BLOCK without a recorded loss"
            for _ in range(3):  # and it stays blocked: nothing carries a last good frame over
                time.sleep(0.1)
                again = ask()
                assert again["status"] == "BLOCK" and again.get("reason") == "criterion_unavailable"
            trace = session.trace()
        finally:
            session.close()  # releases the node: its number is free for the bind below
    finally:
        if not bound:
            restore_the_camera(device, path)
    validate_trace(trace)
    lost = [e["data"] for e in trace["events"] if e["type"] == "camera_unavailable"]
    assert lost and all(entry["reason"] for entry in lost), "the trace says the camera was lost"
    verdicts = [
        e["data"]["verdict"] for e in trace["events"] if e["type"] == "gate_evaluation_result"
    ]
    assert "ALLOW" in verdicts and verdicts[-1] == "BLOCK"
    for target, board in (("sim", "sim-rpi5"), ("linux", "linux-rpi5")):
        assert replay(trace, agent=toml, target=target, board_id=board).verdicts == verdicts
