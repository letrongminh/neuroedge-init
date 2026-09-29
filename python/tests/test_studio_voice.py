"""
`neuroedge studio --mic` (TSK-I1-04, slice S2; docs/spec/studio.md §4 `/api/voice`): the
microphone session behind the page, with a scripted source in place of the microphone —
a spoken command reaches the gate, mute silences the room, a typed command and the voice
thread share the session without deadlock, stop closes the source, SSE hears of it all.
"""

from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from neuroedge.cli.main import app
from neuroedge.hal.audio import AudioFrame
from neuroedge.perception import VirtualClock
from neuroedge.sim import SimSession
from neuroedge.studio import StudioServer
from neuroedge.studio import voice as studio_voice

from .fake_sounddevice import FakeSounddevice
from .test_voice_live import FAKES, RATE, make_speech_pcm

runner = CliRunner()
FRAME_MS = 20
BLOCK = 2 * RATE * FRAME_MS // 1000
TIMEOUT = 10.0


class HeldSource:
    """
    A stand-in for the microphone: silence until `go` is set, then the script, then silence
    until closed (a microphone does not end). `script_end_ms` is where the script stops.
    """

    def __init__(self, pcm: bytes) -> None:
        self.pcm = pcm
        self.go = threading.Event()
        self.closed = False
        self.script_end_ms = 0

    def frames(self) -> Iterator[AudioFrame]:
        at_ms = 0
        offset = 0
        started = False
        while not self.closed:
            if not started and self.go.is_set():
                started = True
                self.script_end_ms = at_ms + len(self.pcm) // BLOCK * FRAME_MS
            if started and offset < len(self.pcm):
                chunk = self.pcm[offset : offset + BLOCK].ljust(BLOCK, b"\x00")
                offset += BLOCK
            else:
                chunk = bytes(BLOCK)
                time.sleep(0.002)  # a microphone is not faster than the room
            yield AudioFrame(chunk, at_ms, FRAME_MS, RATE)
            at_ms += FRAME_MS

    def close(self) -> None:
        self.closed = True


def wait_until(condition: Callable[[], bool], what: str) -> None:
    deadline = time.monotonic() + TIMEOUT
    while time.monotonic() < deadline:
        if condition():
            return
        time.sleep(0.01)
    raise AssertionError(f"timed out waiting for {what}")


def get(server: StudioServer, path: str) -> Any:
    with urllib.request.urlopen(server.url.rstrip("/") + path, timeout=5) as reply:
        return json.loads(reply.read())


def post(server: StudioServer, path: str, body: dict[str, Any]) -> tuple[int, Any]:
    request = urllib.request.Request(
        server.url.rstrip("/") + path, data=json.dumps(body).encode(), method="POST"
    )
    request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=5) as reply:
            return reply.status, json.loads(reply.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


@pytest.fixture
def studio(copy_agent: Callable[..., Path]):
    """`make(source, half_duplex=False)`: a studio on voice-door with the microphone started."""
    made: list[tuple[StudioServer, SimSession]] = []

    def make(source: HeldSource, *, half_duplex: bool = False) -> StudioServer:
        agent = copy_agent("voice-door", FAKES)
        session = SimSession.load(
            agent,
            clock=VirtualClock(),
            target_options={"audio": "live", "sounddevice": FakeSounddevice()},
        )
        server = StudioServer(session, agent_path=agent).start()
        made.append((server, session))
        studio_voice.start(server, half_duplex=half_duplex, source=source)
        return server

    yield make
    for server, session in made:
        if server.voice is not None:
            server.voice.stop()
        server.stop()
        session.close()


SPOKEN = make_speech_pcm(500, 900, 3000)


def event_types(server: StudioServer) -> list[str]:
    return [event["type"] for event in get(server, "/state")["events"]]


def test_a_spoken_command_reaches_the_gate_and_the_page(studio) -> None:
    source = HeldSource(SPOKEN)
    server = studio(source)
    version = server.version
    source.go.set()
    wait_until(lambda: get(server, "/api/voice")["counters"]["turns"] == 1, "one turn")
    types = event_types(server)
    assert "stt_result" in types and "gate_evaluation_result" in types
    assert server.session.hal.pin("door_lock").pulsed_once(30000)
    assert server.version > version  # the SSE stream was woken by the voice events


def test_api_voice_reports_the_running_session(studio) -> None:
    source = HeldSource(SPOKEN)
    server = studio(source, half_duplex=True)
    status = get(server, "/api/voice")
    assert status["ok"] and status["enabled"] and status["running"]
    assert status["muted"] is False and status["half_duplex"] is True
    assert status["state"] == "IDLE"
    assert status["counters"] == {"turns": 0, "barge_in": 0, "stt_unavailable": 0, "cancelled": 0}
    assert set(status["devices"]) == {"input", "output"}
    source.go.set()
    wait_until(lambda: get(server, "/api/voice")["counters"]["turns"] == 1, "one turn")


def test_mute_silences_the_room_and_unmute_hears_it_again(studio) -> None:
    source = HeldSource(SPOKEN)
    server = studio(source)
    code, reply = post(server, "/api/voice/mute", {"muted": True})
    assert code == 200 and reply["ok"] and reply["muted"] is True
    source.go.set()
    wait_until(lambda: server.voice.voice.clock.now > source.script_end_ms + 1500, "the script")
    assert get(server, "/api/voice")["counters"]["turns"] == 0
    assert "audio_in_vad_start" not in event_types(server)
    assert get(server, "/api/voice")["running"]  # the stream stayed open
    _, reply = post(server, "/api/voice/mute", {"muted": False})
    assert reply["muted"] is False


def test_mute_validates_its_body(studio) -> None:
    server = studio(HeldSource(SPOKEN))
    for body in ({}, {"muted": "yes"}, {"muted": 1}):
        code, reply = post(server, "/api/voice/mute", body)
        assert code == 400 and reply["ok"] is False


def test_without_a_microphone_the_page_is_told_so(copy_agent) -> None:
    agent = copy_agent("voice-door", FAKES)
    session = SimSession.load(agent)
    server = StudioServer(session, agent_path=agent).start()
    try:
        assert get(server, "/api/voice") == {"ok": True, "enabled": False, "running": False}
        code, reply = post(server, "/api/voice/mute", {"muted": True})
        assert code == 200 and reply["ok"] is False and "--mic" in reply["error"]["how"]
    finally:
        server.stop()
        session.close()


def test_a_typed_command_works_while_the_voice_thread_runs(studio) -> None:
    source = HeldSource(SPOKEN)
    server = studio(source)
    source.go.set()
    replies: list[dict[str, Any]] = []
    typed = threading.Thread(
        target=lambda: [replies.append(server.command("tắt đèn")) for _ in range(5)]
    )
    typed.start()
    typed.join(TIMEOUT)
    assert not typed.is_alive(), "the typed command deadlocked with the voice thread"
    assert all(reply["ok"] for reply in replies)
    wait_until(lambda: get(server, "/api/voice")["counters"]["turns"] == 1, "one turn")


def test_stop_ends_the_thread_and_closes_the_source(studio) -> None:
    source = HeldSource(SPOKEN)
    server = studio(source)
    assert server.voice.running
    server.voice.stop()
    assert not server.voice.running
    assert source.closed
    assert get(server, "/api/voice")["running"] is False


def test_cli_studio_mic_without_stt_exits_1(copy_agent) -> None:
    agent = copy_agent("voice-door")
    result = runner.invoke(app, ["studio", "--mic", "--agent", str(agent), "--no-browser"])
    assert result.exit_code == 1
    assert "[stt]" in result.output and "Q-15" in result.output


def test_cli_studio_half_duplex_needs_mic(copy_agent) -> None:
    agent = copy_agent("voice-door", FAKES)
    result = runner.invoke(app, ["studio", "--half-duplex", "--agent", str(agent), "--no-browser"])
    assert result.exit_code == 1
    assert "--mic" in result.output
