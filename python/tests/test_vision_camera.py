"""
TSK-V1b-01 / TSK-V1b-02 — a camera, from `vision.in` to the gate, on the sample agent `gate-watch`.

What the camera slice promises, each by name here:

  * an agent that requires `vision.in` is refused at build on a board without a camera
    (`sim-default`, FR-HAL-05, I2a exit criterion 7) and builds on `sim-rpi5` / `linux-rpi5`;
  * `[requires] "vision.in"` is matched against the board's modes by RFC-0012 §3b, precisely:
    a bound the board cannot meet is refused naming the closest mode, a misspelt key is refused;
  * on `sim` the virtual camera feeds the perception; the gate allows what a window of frames
    supports and blocks everything else — no camera, a camera that ends, a frozen one, lost
    frames, a window not yet full — with `criterion_unavailable`, never an ALLOW (RFC-0012 §3e);
  * the trace holds `vision_ref`s and labels, never pixels, and replays on `sim-rpi5` without a
    camera (RFC-0012 §3d, FR-CI-02);
  * on `linux` the same session reads the camera the machine chose.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from neuroedge.actions.tools import ToolCall
from neuroedge.engine.compiler import build, load_agent_manifest
from neuroedge.errors import (
    AgentManifestError,
    BoardCapabilityError,
    BuildFailed,
    NeuroEdgeError,
)
from neuroedge.hal.vision import CameraFrame, CameraUnavailable, Mode, Requirement, modes_of
from neuroedge.sim import SimSession
from neuroedge.testing import assert_matches_golden, replay
from neuroedge.testing.recorder import TraceRecorder
from neuroedge.trace import validate_trace

from .vision_support import FakeClock

FRAME_MS = 1000.0 / 30.0  # the 640x480 @ 30 fps mode, the first of the rig


@pytest.fixture
def agent(root):
    return root / "fixtures" / "agents" / "gate-watch"


class Project(SimpleNamespace):
    """A copy of the sample agent: `root`, and `tag`, the suffix its tools and gates carry."""

    @property
    def toml(self) -> Path:
        return self.root / "agent.toml"

    def tool(self, name: str) -> str:
        return f"{name}_{self.tag}"


@pytest.fixture
def project(agent, tmp_path):
    """
    A writable copy of the sample agent, for variants. The action registry is global by name, so
    the copy's actions and gates are renamed with a suffix of its own: two copies (two tests)
    never define the same action.
    """
    target = tmp_path / "gate-watch"
    shutil.copytree(agent, target, ignore=shutil.ignore_patterns("__pycache__"))
    tag = hashlib.sha256(str(tmp_path).encode()).hexdigest()[:6]
    names = "watch_open_gate|watch_lights_off"
    rewrites = {
        "actions/gate_watch.py": [
            (rf'name="({names})"', rf'name="\1_{tag}"'),
            (rf'gate="({names})"', rf'gate="\1_{tag}"'),
            (rf"def ({names})\(", rf"def \1_{tag}("),
        ],
        "agent.toml": [(rf'^({names})(\s*)= "gates/', rf'\1_{tag}\2= "gates/')],
        "commands.toml": [(rf'tool(\s*)= "({names})"', rf'tool\1= "\2_{tag}"')],
    }
    for relative, rules in rewrites.items():
        path = target / relative
        text = path.read_text(encoding="utf-8")
        for pattern, replacement in rules:
            text = re.sub(pattern, replacement, text, flags=re.MULTILINE)
        path.write_text(text, encoding="utf-8")
    return Project(root=target, tag=tag)


def patched(project: Project, old: str, new: str) -> Path:
    toml = project.toml
    text = toml.read_text(encoding="utf-8")
    assert old in text, old
    toml.write_text(text.replace(old, new, 1), encoding="utf-8")
    return toml


def load(toml: Path, **kw) -> tuple[SimSession, FakeClock]:
    clock = FakeClock()
    return SimSession.load(toml, board_id="sim-rpi5", clock=clock, **kw), clock


def call(session: SimSession, name: str = "watch_open_gate"):
    return asyncio.run(session.call_tool(ToolCall(name, {}, source="local_grammar")))


def verdict(session: SimSession, clock: FakeClock, frames: float, name: str = "watch_open_gate"):
    """Let `frames` frame periods pass, then ask: `(status, reason)`."""
    clock.advance(frames * FRAME_MS)
    content = call(session, name).content()
    return content["status"], content.get("reason")


def facts(session: SimSession, last: int = 1) -> list[dict]:
    return session.events.of_type("vision_fact")[-last:]


# -- the board decides ----------------------------------------------------------------------


@pytest.mark.parametrize(("target", "board"), [("sim", "sim-rpi5"), ("linux", "linux-rpi5")])
def test_the_sample_builds_on_the_boards_that_have_a_camera(agent, target, board):
    report = build(agent / "agent.toml", target=target, board_id=board)
    assert report.board == board


@pytest.mark.parametrize("board", ["sim-default"])
def test_an_agent_that_needs_a_camera_is_refused_at_build_on_a_board_without_one(agent, board):
    with pytest.raises(BuildFailed) as refused:
        build(agent / "agent.toml", target="sim", board_id=board)
    (problem,) = refused.value.problems
    assert isinstance(problem, BoardCapabilityError)
    assert "vision.in" in problem.where and problem.why and problem.how  # three parts
    assert "sim-default" in problem.why


def test_the_default_board_hint_names_the_board_that_has_the_camera(agent):
    with pytest.raises(BuildFailed) as refused:
        build(agent / "agent.toml", target="sim")  # no --board: sim-default, never swapped
    hint = refused.value.problems[-1]
    assert "sim-rpi5" in hint.how


def test_a_session_on_a_board_without_a_camera_does_not_start(agent):
    with pytest.raises(BuildFailed):
        SimSession.load(agent / "agent.toml", board_id="sim-default")


# -- [requires] "vision.in": the RFC-0012 §3b match -----------------------------------------

RIG = modes_of(
    [
        {"width": 640, "height": 480, "fps": 30.0, "pixel_format": "rgb888"},
        {"width": 1280, "height": 720, "fps": 30.0, "pixel_format": "yuyv"},
    ]
)


@pytest.mark.parametrize(
    ("need", "chosen"),
    [
        ({}, RIG[0]),
        ({"min_width": 640, "min_height": 480}, RIG[0]),
        ({"min_width": 1280}, RIG[1]),  # only the second mode is wide enough
        ({"pixel_formats": ["yuyv", "mjpeg"]}, RIG[1]),
        ({"min_fps": 30}, RIG[0]),
        ({"min_width": 640, "pixel_formats": ["rgb888", "yuyv"]}, RIG[0]),  # board order decides
    ],
)
def test_the_mode_is_the_first_one_that_meets_every_bound(need, chosen):
    from neuroedge.hal.vision import select_mode

    assert select_mode(RIG, Requirement.parse(need)) == chosen


@pytest.mark.parametrize(
    ("need", "misses"),
    [
        ({"min_width": 1920}, "min_width 1920 >"),
        ({"min_fps": 60}, "min_fps 60 >"),
        ({"min_width": 1280, "pixel_formats": ["rgb888"]}, "pixel_format"),
        ({"pixel_formats": ["gray8"]}, "pixel_format"),
    ],
)
def test_a_bound_no_mode_meets_is_refused_naming_the_closest_mode(agent, project, need, misses):
    table = ", ".join(f"{k} = {json.dumps(v)}" for k, v in need.items())
    toml = patched(
        project,
        '"vision.in"   = { min_width = 640, min_height = 480, min_fps = 10.0 }',
        f'"vision.in"   = {{ {table} }}',
    )
    with pytest.raises(BuildFailed) as refused:
        build(toml, target="sim", board_id="sim-rpi5")
    (problem,) = refused.value.problems
    assert isinstance(problem, BoardCapabilityError)
    assert "the closest mode" in problem.why and misses in problem.why
    assert "vision_in.modes" in problem.how


@pytest.mark.parametrize(
    "need",
    [
        "{ min_widht = 640 }",  # a misspelt bound is a bound that is not there
        '{ min_width = "wide" }',
        "{ min_width = -1 }",
        "{ min_fps = true }",
        '{ pixel_formats = "yuyv" }',
        '{ pixel_formats = ["bmp"] }',
    ],
)
def test_a_malformed_vision_requirement_is_refused_not_ignored(project, need):
    toml = patched(
        project,
        '"vision.in"   = { min_width = 640, min_height = 480, min_fps = 10.0 }',
        f'"vision.in"   = {need}',
    )
    with pytest.raises(BuildFailed) as refused:
        build(toml, target="sim", board_id="sim-rpi5")
    assert all(isinstance(p, AgentManifestError) for p in refused.value.problems)


def test_an_unknown_primitive_is_still_refused(project):
    toml = patched(project, '"vision.in"   = {', '"audio.vision" = {')
    with pytest.raises(AgentManifestError, match="not HAL primitives"):
        load_agent_manifest(toml)


# -- [vision] against the agent's gates ------------------------------------------------------


def build_problems(toml: Path) -> list[NeuroEdgeError]:
    with pytest.raises(BuildFailed) as refused:
        build(toml, target="sim", board_id="sim-rpi5")
    return refused.value.problems


def test_vision_without_the_primitive_is_refused(project):
    toml = patched(
        project, '"vision.in"   = { min_width = 640, min_height = 480, min_fps = 10.0 }\n', ""
    )
    (problem,) = build_problems(toml)
    assert "reads frames through vision.in" in problem.why


def test_a_vision_fact_nothing_reads_is_a_typo_not_a_silent_block(project):
    toml = patched(project, "[vision.facts.people_at_gate]", "[vision.facts.peple_at_gate]")
    problems = build_problems(toml)
    assert any("no gate of this agent evaluates 'peple_at_gate'" in p.why for p in problems)


def test_a_fact_kind_must_match_the_type_of_the_criterion(project):
    toml = patched(
        project,
        '[vision.facts.person_at_gate]\nlabel = "person"\nzone  = "gate_area"\nkind  = "present"',
        '[vision.facts.person_at_gate]\nlabel = "person"\nzone  = "gate_area"\nkind  = "count"',
    )
    problems = build_problems(toml)
    assert any("'person_at_gate' as 'bool', and kind 'count'" in p.why for p in problems)


def test_confidence_gte_on_a_vision_fact_is_refused_one_road_for_confidence(project):
    gate = project.root / "gates" / "watch_open_gate@1.0.0.yaml"
    text = gate.read_text(encoding="utf-8")
    gate.write_text(
        text.replace("person_at_gate:    true", "person_at_gate:    { confidence_gte: 0.9 }")
    )
    problems = build_problems(project.toml)
    assert any("`confidence_gte`" in p.why and "person_at_gate" in p.where for p in problems)


def test_present_without_its_confidence_pair_is_refused_a_bool_has_no_age(project):
    gate = project.root / "gates" / "watch_lights_off@1.0.0.yaml"
    text = gate.read_text(encoding="utf-8")
    gate.write_text(text.replace("  person_confidence: { lte: 0.10 }\n", ""))
    problems = build_problems(project.toml)
    assert any("no numeric `confidence` criterion" in p.why for p in problems)


def test_a_vision_fact_may_not_be_decided_by_a_model_that_reads_words(project):
    with (project.toml).open("a") as handle:
        handle.write(
            '\n[system_one]\nprovider = "python:nope:make"\ncriteria = ["person_at_gate"]\n'
        )
    problems = build_problems(project.toml)
    assert problems  # the adapter is not importable, or the criterion is computed by the camera


def test_without_a_model_the_agent_does_not_build(project):
    toml = patched(project, 'provider   = "replay"\n', "")
    problems = build_problems(toml)
    assert any("does not name a model" in p.why for p in problems)


def test_a_session_fact_may_not_shadow_a_vision_fact(project):
    toml = patched(project, "[sim.vision]", "[sim.facts]\nperson_at_gate = true\n\n[sim.vision]")
    with pytest.raises(AgentManifestError, match="decided by the camera, and also by another"):
        SimSession.load(toml, board_id="sim-rpi5", clock=FakeClock())


# -- on sim: frames in, a verdict out --------------------------------------------------------


def test_the_gate_allows_what_a_full_window_of_a_present_person_supports(agent):
    session, clock = load(agent / "agent.toml")
    # frame k is ready after k + 1 periods, so 8.5 periods in, frames 0-7 exist and the window of
    # three is 5, 6, 7 — all of them frames of the person (the script says frames 5-12)
    assert verdict(session, clock, 8.5) == ("ALLOW", None)
    open_reading = facts(session, 2)[0]
    assert open_reading["value"] is True and [f["frame_seq"] for f in open_reading["frames"]] == [
        5,
        6,
        7,
    ]
    assert session.hal.pins["gate_relay"].pulsed


def test_the_gate_blocks_an_empty_scene_without_a_pulse(agent):
    session, clock = load(agent / "agent.toml")
    assert verdict(session, clock, 4.5) == ("BLOCK", "condition_not_met")  # frames 0-3: nobody
    assert not session.hal.pins.get("gate_relay")


def test_lights_off_needs_an_empty_gate_and_blocks_while_a_person_stands_there(agent):
    session, clock = load(agent / "agent.toml")
    assert verdict(session, clock, 8.5, "watch_lights_off")[0] == "BLOCK"  # a person at the gate
    assert verdict(session, clock, 8.0, "watch_lights_off") == (
        "ALLOW",
        None,
    )  # frames 14-16: empty again


def test_a_window_that_is_not_yet_full_blocks_criterion_unavailable(agent):
    session, clock = load(agent / "agent.toml")
    assert verdict(session, clock, 1.5) == ("BLOCK", "criterion_unavailable")  # one frame so far
    assert facts(session, 2)[0]["unavailable"] == "window_size"


def test_a_camera_that_ends_blocks_and_says_so(agent):
    session, clock = load(agent / "agent.toml")
    assert verdict(session, clock, 8.5) == ("ALLOW", None)  # the person is there
    clock.advance(FRAME_MS * 200)  # the 60-frame recording is long over
    call(session)  # delivers the last frames it captured: a late reader's newest four
    assert verdict(session, clock, 5) == ("BLOCK", "criterion_unavailable")
    unavailable = session.events.of_type("camera_unavailable")
    assert unavailable and "recording ended" in unavailable[-1]["reason"]


def test_a_gone_camera_empties_the_window_so_old_frames_cannot_be_reused(agent):
    session, clock = load(agent / "agent.toml")
    verdict(session, clock, 8.5)  # a good window is in the pipeline
    session.vision.camera.close()  # the camera is lost
    assert verdict(session, clock, 1) == ("BLOCK", "criterion_unavailable")
    assert facts(session, 2)[0]["unavailable"] in ("window_size", "stale")
    assert session.events.of_type("camera_unavailable")


def test_a_frozen_camera_blocks_even_when_the_driver_stamps_new_times(project):
    frames = project.root / "camera"
    frames.mkdir()
    for i in range(30):  # 640x480 rgb888: the same bytes, thirty times
        (frames / f"{i:03}.raw").write_bytes(b"\x07" * (640 * 480 * 3))
    toml = patched(project, 'source = "synthetic"\nframes = 60', 'source = "camera"')
    session, clock = load(toml)
    assert verdict(session, clock, 8.5, project.tool("watch_open_gate")) == (
        "BLOCK",
        "criterion_unavailable",
    )
    assert facts(session, 2)[0]["unavailable"] == "frozen"


def test_lost_frames_restart_the_window(project):
    toml = patched(project, "frames = 60", "frames = 60\ndrop = [7]")
    session, clock = load(toml)
    # frames 6, 8, 9 are delivered: 7 is a hole, so the newest consecutive run is 8, 9 — too few
    open_gate = project.tool("watch_open_gate")
    assert verdict(session, clock, 9.5, open_gate) == ("BLOCK", "criterion_unavailable")
    assert verdict(session, clock, 2.0, open_gate) == (
        "ALLOW",
        None,
    )  # 8, 9, 10 are consecutive again


def test_the_frames_of_a_recording_are_the_cameras_even_when_the_reader_is_late(agent):
    session, clock = load(agent / "agent.toml")
    clock.advance(FRAME_MS * 100)  # nobody asked for 100 frames
    call(session)
    seqs = [f["frame_seq"] for f in facts(session, 2)[0].get("frames", [])]
    assert seqs == sorted(seqs) and seqs[-1] - seqs[0] == len(seqs) - 1  # a consecutive run


def test_a_model_that_says_yes_to_anything_cannot_answer_for_a_missing_camera(agent):
    """An unavailable vision fact is given to the engine as *not there*, so no other source —
    here one that would say True to every criterion — is asked in its place."""
    session, clock = load(agent / "agent.toml")

    class SaysYes:
        async def adjudicate(self, criterion, definition, state, *, deadline_ms):
            return True

    session.conversation.engine.facts_source = SaysYes()
    assert verdict(session, clock, 1.5) == ("BLOCK", "criterion_unavailable")


def test_an_agent_with_vision_reads_no_frame_for_a_gate_that_asks_nothing_of_it(project):
    toml = project.toml
    session, clock = load(toml)
    clock.advance(FRAME_MS * 3)
    # a gate that does not name a vision criterion must not run the model (no wasted inference)
    tree = session.conversation.engine.tree(project.tool("watch_open_gate"))
    assert {"person_at_gate", "person_confidence"} <= {n["criterion"] for n in tree["nodes"]}
    assert session.vision.facts({"nodes": [{"criterion": "something_else"}]}) == {}
    assert session.vision.pipeline._buffer == []


def test_the_simulator_without_a_recording_does_not_start_an_agent_that_needs_eyes(project):
    text = (project.toml).read_text(encoding="utf-8")
    (project.toml).write_text(text.split("# Camera ảo của `sim`")[0], encoding="utf-8")
    with pytest.raises(CameraUnavailable, match="no recording to play"):
        SimSession.load(project.toml, board_id="sim-rpi5", clock=FakeClock())


# -- the trace -------------------------------------------------------------------------------


def recorded(agent: Path) -> tuple[SimSession, FakeClock, TraceRecorder]:
    clock = FakeClock()
    recorder = TraceRecorder(clock=clock, target="sim", board_id="sim-rpi5")
    session = SimSession.load(
        agent / "agent.toml", board_id="sim-rpi5", clock=clock, events=recorder
    )
    return session, clock, recorder


def test_the_trace_holds_frame_identities_and_labels_never_pixels(agent):
    session, clock, recorder = recorded(agent)
    verdict(session, clock, 8.5)
    trace = recorder.to_trace()
    validate_trace(trace)
    text = json.dumps(trace)
    pixels = session.vision.camera.source.frame(6)
    assert pixels.hex() not in text and "uri" not in text
    assert "raw_capture" not in trace["metadata"]  # never opted in
    reading = next(e["data"] for e in trace["events"] if e["type"] == "vision_fact")
    for frame in reading["frames"]:
        assert (
            set(frame["vision_ref"]) == {"sha256", "size"}
            and frame["vision_ref"]["size"] == 640 * 480 * 3
        )
        assert set(frame) <= {"frame_seq", "vision_ref", "captured_ms", "labels", "rejected"}
    assert trace["metadata"]["vision_models"][0]["name"] == "person-det"


def test_a_recorded_vision_session_replays_without_a_camera(agent):
    session, clock, recorder = recorded(agent)
    verdict(session, clock, 4.5)  # BLOCK: nobody
    verdict(session, clock, 4.0)  # ALLOW: the person is there
    verdict(session, clock, 6.0, "watch_lights_off")
    trace = recorder.to_trace()
    result = replay(trace, agent=agent / "agent.toml", target="sim", board_id="sim-rpi5")
    recorded_verdicts = [
        e["data"]["verdict"] for e in trace["events"] if e["type"] == "gate_evaluation_result"
    ]
    assert result.verdicts == recorded_verdicts
    assert "ALLOW" in recorded_verdicts and "BLOCK" in recorded_verdicts
    assert result.warnings == [] and result.divergences == []
    assert_matches_golden(result, trace)  # the verdicts and the pin commands, from the labels alone


# -- linux: the same session over the machine's camera --------------------------------------


class StubCamera:
    """A camera on `linux` for the session test: frames handed over as the test queues them."""

    def __init__(self, mode: Mode, clock) -> None:
        self.mode, self.clock = mode, clock
        self.queue: list[CameraFrame] = []
        self.closed = False
        self.lost: str | None = None
        self.seq = 0

    def push(self, fill: int) -> None:
        self.queue.append(
            CameraFrame(
                self.seq,
                self.clock(),
                bytes([fill]) * 64,
                self.mode.width,
                self.mode.height,
                self.mode.pixel_format,
            )
        )
        self.seq += 1

    def read_available(self):
        if self.lost:
            raise CameraUnavailable(where="stub", why=self.lost, how="reconnect")
        frames, self.queue = self.queue, []
        return frames

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def linux_camera(monkeypatch, tmp_path):
    import neuroedge.hal.linux as linux

    from .test_hal_linux import LINES, FakeGpiod

    chip = tmp_path / "gpiochip0"
    chip.write_text("")
    monkeypatch.setattr(linux, "CHIP_GLOB", str(tmp_path / "gpiochip*"))
    monkeypatch.setattr(linux, "_import_gpiod", lambda: FakeGpiod({str(chip): LINES}))
    cameras: list[StubCamera] = []

    def make(node, mode, clock):
        cameras.append(StubCamera(mode, clock))
        return cameras[-1]

    monkeypatch.setattr(linux, "V4L2Camera", make)
    monkeypatch.setattr(linux, "probe", lambda node: "Stub Camera")
    monkeypatch.setenv(linux.CAMERA_ENV, "/dev/video0")
    return cameras


def linux_session(agent, clock):
    return SimSession.load(agent / "agent.toml", target="linux", clock=clock)


def test_on_linux_the_session_reads_the_camera_the_machine_chose(agent, linux_camera):
    clock = FakeClock()
    session = linux_session(agent, clock)
    try:
        (camera,) = linux_camera
        assert camera.mode == modes_of(session.hal.board.vision_modes)[0]
        camera.seq = 5  # frames 5, 6, 7 are the person in the model's script
        for fill in (1, 2, 3):
            clock.advance(33.0)
            camera.push(fill)
        assert call(session).content()["status"] == "ALLOW"
    finally:
        session.close()
    assert camera.closed  # the session closed the HAL, and the HAL its camera


def test_on_linux_a_camera_that_stops_blocks_the_gate(agent, linux_camera):
    clock = FakeClock()
    session = linux_session(agent, clock)
    try:
        (camera,) = linux_camera
        camera.seq = 5
        for fill in (1, 2, 3):
            clock.advance(33.0)
            camera.push(fill)
        assert call(session).content()["status"] == "ALLOW"
        camera.lost = "no frame for 1200 ms (stall limit 1000 ms): the camera has stopped"
        clock.advance(33.0)
        content = call(session).content()
        assert (content["status"], content["reason"]) == ("BLOCK", "criterion_unavailable")
        assert "stopped" in session.events.of_type("camera_unavailable")[-1]["reason"]
    finally:
        session.close()


def test_on_linux_no_chosen_camera_means_no_session(agent, linux_camera, monkeypatch):
    import neuroedge.hal.linux as linux

    monkeypatch.delenv(linux.CAMERA_ENV)
    with pytest.raises(CameraUnavailable, match="no camera node is chosen"):
        linux_session(agent, FakeClock())


def test_a_replay_on_linux_opens_no_camera(linux_camera):
    from neuroedge.hal.linux import LinuxHAL

    hal = LinuxHAL(replay=True)
    mode = modes_of(hal.board.vision_modes)[0]
    with pytest.raises(CameraUnavailable, match="opens no camera"):
        hal.vision_in(mode)
    assert linux_camera == []
    hal.close()


def test_linux_refuses_a_mode_the_board_does_not_declare(linux_camera):
    from neuroedge.hal.linux import LinuxHAL

    hal = LinuxHAL()
    with pytest.raises(BoardCapabilityError, match="declares no camera mode 800x600"):
        hal.vision_in(Mode(800, 600, 30.0, "rgb888"))
    hal.close()


# -- the corpus of vision.in and `verify` (RFC-0013 §3f item 7) -------------------------------


def corpus(root: Path) -> list[Path]:
    return sorted((root / "fixtures" / "traces" / "vision").glob("*.json"))


def test_the_vision_corpus_is_what_the_sample_agent_records(root):
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "gen_vision_traces.py"), "--check"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr


def test_the_vision_corpus_holds_an_allow_a_block_and_a_lost_camera(root):
    outcomes = {
        path.stem: [
            (e["data"]["verdict"], e["data"].get("reason"))
            for e in json.loads(path.read_text())["events"]
            if e["type"] == "gate_evaluation_result"
        ]
        for path in corpus(root)
    }
    assert outcomes == {
        "gate-watch-allow": [("ALLOW", None)],
        "gate-watch-block": [("BLOCK", "condition_not_met")],
        "gate-watch-camera-lost": [("ALLOW", None), ("BLOCK", "criterion_unavailable")],
    }


def test_the_corpus_holds_frame_identities_never_pixels_or_a_raw_capture_flag(root):
    for path in corpus(root):
        trace = json.loads(path.read_text())
        validate_trace(trace)
        text = path.read_text()
        assert "raw_capture" not in trace["metadata"] and '"uri"' not in text
        for event in trace["events"]:
            if event["type"] == "vision_fact" and event["data"]["frames"]:
                assert all(
                    set(f["vision_ref"]) == {"sha256", "size"} for f in event["data"]["frames"]
                )


@pytest.mark.parametrize(("target", "board"), [("sim", "sim-rpi5"), ("linux", "linux-rpi5")])
def test_the_vision_corpus_replays_to_what_it_recorded_on_every_board_with_a_camera(
    root, agent, linux_camera, target, board
):
    for path in corpus(root):
        recorded = json.loads(path.read_text())
        result = replay(path, agent=agent / "agent.toml", target=target, board_id=board)
        assert result.verdicts == [
            e["data"]["verdict"]
            for e in recorded["events"]
            if e["type"] == "gate_evaluation_result"
        ], path.name
        assert result.warnings == [] and result.divergences == []
        assert_matches_golden(result, recorded)
    assert linux_camera == []  # a replay opened no camera


def test_a_board_without_a_camera_skips_the_vision_corpus_without_failing_verify():
    from typer.testing import CliRunner

    from neuroedge.cli.main import app

    result = CliRunner().invoke(app, ["verify", "--targets", "sim"])
    assert result.exit_code == 0, result.output
    assert "vision/gate-watch-allow.json" in result.output
    assert "sim/sim-rpi5" in result.output


def test_a_camera_that_breaks_blocks_the_gate_instead_of_crashing_the_call(agent):
    session, clock = load(agent / "agent.toml")
    assert verdict(session, clock, 8.5) == ("ALLOW", None)

    def broken():
        raise RuntimeError("driver bug")

    session.vision.camera.read_available = broken  # type: ignore[method-assign]
    assert verdict(session, clock, 1) == ("BLOCK", "criterion_unavailable")
    assert "RuntimeError" in session.events.of_type("camera_unavailable")[-1]["reason"]
