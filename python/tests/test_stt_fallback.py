"""
TSK-I4-01, Q-14 — `[stt.fallback]`: the local endpoint the driver calls when the
primary STT is unavailable, and how its transcript takes the very same path
(`stt_result` → command grammar or System 2 → `c.do()` → the gate). Fake providers
only: no network, exact virtual-time numbers.
"""

from __future__ import annotations

import asyncio
import shutil

import pytest
from typer.testing import CliRunner

from neuroedge.cli.main import app
from neuroedge.engine.compiler import build
from neuroedge.errors import AgentManifestError, BuildFailed
from neuroedge.perception import VirtualClock, VoiceParams, VoiceSession
from neuroedge.perception.providers import (
    FakeSpeechToText,
    FakeTextToSpeech,
    load_speech_configs,
    parse_speech,
)
from neuroedge.sim import SimSession
from neuroedge.trace import validate_trace

from .test_voice_speech import RATE, silence, tone, write_wav

runner = CliRunner()
DOOR = "voice-door"


@pytest.fixture(scope="module")
def door(root):
    return root / "fixtures" / "agents" / DOOR / "agent.toml"


# --- the table ---------------------------------------------------------------------------


def test_a_fallback_table_is_parsed_next_to_the_primary():
    config = parse_speech(
        "stt",
        {
            "base_url": "https://api.openai.com/v1",
            "model": "whisper-1",
            "api_key_env": "OPENAI_API_KEY",
            "fallback": {"base_url": "http://localhost:8000/v1", "model": "whisper-small"},
        },
    )
    assert config.fallback is not None
    assert config.fallback.base_url == "http://localhost:8000/v1"
    assert config.fallback.model == "whisper-small" and config.fallback.fallback is None
    assert "[stt.fallback]" in config.fallback.where
    assert config.table == "stt" and config.fallback.table == "stt.fallback"


def test_a_fallback_inside_a_fallback_is_refused():
    with pytest.raises(AgentManifestError) as raised:
        parse_speech(
            "stt",
            {
                "base_url": "http://localhost:8000/v1",
                "model": "small",
                "fallback": {
                    "base_url": "http://localhost:8001/v1",
                    "model": "smaller",
                    "fallback": {"base_url": "http://localhost:8002/v1", "model": "tiniest"},
                },
            },
        )
    assert "not fields of [stt.fallback]" in raised.value.why
    assert "fallback" in raised.value.why


def test_a_key_in_the_fallback_is_refused_and_never_echoed():
    with pytest.raises(AgentManifestError) as raised:
        parse_speech(
            "stt",
            {
                "base_url": "http://localhost:8000/v1",
                "model": "small",
                "fallback": {"api_key": "sk-abcdefghijklmnopqrst", "model": "smaller"},
            },
        )
    assert "sk-abcdefghijklmnopqrst" not in raised.value.render()
    assert "fallback.api_key" in raised.value.where


def test_a_fallback_carrying_a_key_to_another_machine_is_refused():
    with pytest.raises(AgentManifestError) as raised:
        parse_speech(
            "stt",
            {
                "base_url": "https://api.openai.com/v1",
                "model": "whisper-1",
                "api_key_env": "OPENAI_API_KEY",
                "fallback": {
                    "base_url": "http://192.168.1.9:8000/v1",
                    "model": "small",
                    "api_key_env": "LOCAL_KEY",
                },
            },
        )
    assert "plain http://" in raised.value.why and "clear text" in raised.value.why


def test_load_speech_configs_keeps_a_table_without_a_fallback_unchanged(door):
    from neuroedge.engine.compiler import load_agent_manifest

    manifest = load_agent_manifest(door)
    stt, _ = load_speech_configs(manifest)
    assert stt is None, "voice-door declares no [stt] at all"


# --- the driver --------------------------------------------------------------------------


def voice_on(door, tmp_path, *, stt, fallback, transcripts=("mở cửa",)):
    clock = VirtualClock()
    session = SimSession.load(door, clock=clock)
    voice = VoiceSession(
        session,
        clock=clock,
        params=VoiceParams(vad_activation=True, think_timeout_ms=5000),
        stt=stt,
        stt_fallback=fallback,
        stt_label="stt (fake/primary)",
        stt_fallback_label="stt.fallback (fake/local)",
        tts=FakeTextToSpeech(ms_per_char=10),
    )
    wav = write_wav(tmp_path / "turn.wav", silence(300) + tone(600, RATE) + silence(700), rate=RATE)
    source = session.hal.audio_file(wav, called_from="test")
    return voice, source


def at(voice, kind):
    return [(e["offset_ms"], e["data"]) for e in voice.events.events if e["type"] == kind]


def run(voice, source):
    asyncio.run(voice.play(source))


def test_the_primary_failing_switches_to_the_fallback_and_keeps_the_turn(door, tmp_path):
    primary = FakeSpeechToText(fail=True, latency_ms=100)
    fallback = FakeSpeechToText(["mở cửa"], latency_ms=200)
    voice, source = voice_on(door, tmp_path, stt=primary, fallback=fallback)
    run(voice, source)
    # T04 at 1800 (300 silence + 600 tone; VAD end 200 ms after the tone ends at 900).
    (failed,) = at(voice, "stt_unavailable")
    assert failed[0] == 1900, "the primary's declared 100 ms latency"
    (switched,) = at(voice, "stt_fallback")
    assert switched[0] == 1900, "the switch is recorded where the primary failed"
    assert switched[1]["from"] == "stt (fake/primary)"
    assert switched[1]["to"] == "stt.fallback (fake/local)"
    assert "fake provider is set to fail" in switched[1]["reason"]
    (heard,) = at(voice, "stt_result")
    assert heard == (2100, {"turn": 1, "text": "mở cửa"}), "primary latency 100 + fallback 200"
    assert [t.heard for t in voice.turns] == ["mở cửa"]
    assert voice.hal.pin("door_lock").pulsed, "the fallback transcript went through the gate"
    validate_trace(voice.session.events.to_trace(), label="fallback case")


def test_a_healthy_primary_never_calls_the_fallback(door, tmp_path):
    primary = FakeSpeechToText(["mở cửa"], latency_ms=100)
    fallback = FakeSpeechToText(["sai"], latency_ms=200)
    voice, source = voice_on(door, tmp_path, stt=primary, fallback=fallback)
    run(voice, source)
    assert voice.events.of_type("stt_fallback") == []
    assert fallback.clips == [], "the fallback was never asked"
    assert [t.heard for t in voice.turns] == ["mở cửa"]


def test_both_unavailable_takes_the_existing_offline_path(door, tmp_path):
    primary = FakeSpeechToText(fail=True, latency_ms=100)
    fallback = FakeSpeechToText(fail=True, latency_ms=50)
    voice, source = voice_on(door, tmp_path, stt=primary, fallback=fallback)
    run(voice, source)
    (switched,) = at(voice, "stt_fallback")
    assert switched[0] == 1900
    primary_failed, fallback_failed = at(voice, "stt_unavailable")
    assert primary_failed[0] == 1900 and fallback_failed[0] == 1950, "50 ms fallback latency"
    assert "fallback STT also failed" in fallback_failed[1]["reason"]
    assert voice.hal.pin("door_lock").never_pulsed()
    assert [t.stt_failure for t in voice.turns] and voice.turns[0].heard is None
    assert voice.fsm.state.value == "IDLE"


def test_a_fallback_transcript_that_is_garbled_is_still_a_failure(door, tmp_path):
    primary = FakeSpeechToText(fail=True, latency_ms=100)
    fallback = FakeSpeechToText(["mở\u202ecửa"], latency_ms=50)  # bidi override
    voice, source = voice_on(door, tmp_path, stt=primary, fallback=fallback)
    run(voice, source)
    (_primary_failed, fallback_failed) = at(voice, "stt_unavailable")
    assert "fallback STT also failed" in fallback_failed[1]["reason"]
    assert "bidi overrides" in fallback_failed[1]["reason"]
    assert voice.hal.pin("door_lock").never_pulsed()


def test_a_primary_slower_than_the_think_timeout_cannot_drive_the_turn(door, tmp_path):
    # The primary would open the door, but only long after the switch: its pending
    # answer is dropped (recorded) when the fallback takes the turn, and only the
    # fallback's transcript acts.
    primary = FakeSpeechToText(["mở cửa"], latency_ms=30000)
    fallback = FakeSpeechToText(["mở cửa"], latency_ms=3000)
    voice, source = voice_on(door, tmp_path, stt=primary, fallback=fallback)
    run(voice, source)
    # T04 at 1800, think timeout 5000 ⇒ the switch at 6800; fallback answers at 9800.
    (dropped,) = at(voice, "voice_late_result_dropped")
    assert dropped == (6800, {"turn": 1, "input": "stt_result"})
    (switched,) = at(voice, "stt_fallback")
    assert switched[0] == 6800 and switched[1]["to"] == "stt.fallback (fake/local)"
    (heard,) = at(voice, "stt_result")
    assert heard == (9800, {"turn": 1, "text": "mở cửa"})
    assert [t.heard for t in voice.turns] == ["mở cửa"]
    # One pulse only, at the fallback's time: the primary's 31800 answer never acted.
    assert voice.hal.pin("door_lock").commands == [("pulse", 30000)]
    (command,) = [e for e in voice.events.events if e["type"] == "actuator_command"]
    assert command["offset_ms"] == 9800


def test_the_fallback_wait_has_its_own_bounded_deadline(door, tmp_path):
    # The fallback is given `think_timeout_ms` from the switch, not its transport
    # bound (here 30 s): the offline line runs at 11800, and its late answer is dropped.
    primary = FakeSpeechToText(fail=True, latency_ms=100)
    fallback = FakeSpeechToText(["mở cửa"], latency_ms=30000)
    voice, source = voice_on(door, tmp_path, stt=primary, fallback=fallback)
    run(voice, source)
    (switched,) = at(voice, "stt_fallback")
    assert switched[0] == 1900
    # The offline line at 1900 + 5000; the fallback's answer at 31900 is dropped.
    (dropped,) = at(voice, "voice_late_result_dropped")
    assert dropped == (31900, {"turn": 1, "input": "stt_result"})
    started = [e["offset_ms"] for e in voice.events.events if e["type"] == "tts_stream_start"]
    assert started == [6900], "the turn concluded with the offline line, not 30 s later"
    assert voice.hal.pin("door_lock").never_pulsed()


def test_a_fallback_that_hears_nothing_reprompts_like_the_primary(door, tmp_path):
    primary = FakeSpeechToText(fail=True, latency_ms=100)
    fallback = FakeSpeechToText([""], latency_ms=50)
    voice, source = voice_on(door, tmp_path, stt=primary, fallback=fallback)
    run(voice, source)
    assert voice.events.of_type("stt_fallback")
    (reprompt,) = at(voice, "voice_reprompt")
    assert reprompt[1] == {"turn": 1, "count": 1}
    assert voice.hal.pin("door_lock").never_pulsed()


# --- the build and the CLI ----------------------------------------------------------------


EXTRA = """
[stt]
provider = "python:neuroedge.perception.providers.fake:stt"
[stt.options]
fail = true
latency_ms = 100

[stt.fallback]
provider = "python:neuroedge.perception.providers.fake:stt"
[stt.fallback.options]
transcripts = ["mở cửa"]
latency_ms = 200

[tts]
provider = "python:neuroedge.perception.providers.fake:tts"
[tts.options]
ms_per_char = 10
"""


@pytest.fixture
def fresh_actions():
    from neuroedge.actions import spec

    saved = dict(spec.REGISTRY)
    spec.REGISTRY.clear()
    yield
    spec.REGISTRY.clear()
    spec.REGISTRY.update(saved)


@pytest.fixture
def project(root, tmp_path, fresh_actions):
    folder = tmp_path / DOOR
    shutil.copytree(root / "fixtures" / "agents" / DOOR, folder)
    agent = folder / "agent.toml"
    base = agent.read_text(encoding="utf-8")
    wav = write_wav(tmp_path / "turn.wav", silence(300) + tone(600, RATE) + silence(700), rate=RATE)

    def make(extra: str = EXTRA):
        agent.write_text(base + extra, encoding="utf-8")
        return agent, wav

    return make


def test_the_build_refuses_a_key_in_the_fallback(project):
    agent, _ = project(
        """
[stt]
base_url = "http://localhost:8000/v1"
model    = "small"
[stt.fallback]
base_url = "http://localhost:8001/v1"
model    = "smaller"
api_key  = "sk-abcdefghijklmnop"
"""
    )
    with pytest.raises(BuildFailed) as raised:
        build(agent, target="sim", board_id="sim-default")
    rendered = " ".join(p.render() for p in raised.value.problems)
    assert "fallback.api_key" in rendered and "sk-abcdefghijklmnop" not in rendered


def test_the_build_import_checks_the_fallback_adapter(project):
    agent, _ = project(
        """
[stt]
base_url = "http://localhost:8000/v1"
model    = "small"
[stt.fallback]
provider = "python:no_such_module.adapter:make"
"""
    )
    with pytest.raises(BuildFailed) as raised:
        build(agent, target="sim", board_id="sim-default")
    rendered = " ".join(p.render() for p in raised.value.problems)
    assert "cannot import the adapter module" in rendered and "no_such_module" in rendered


def test_the_voice_cli_uses_the_fallback_and_records_the_switch(project, tmp_path):
    agent, wav = project()
    trace = tmp_path / "fallback.json"
    result = runner.invoke(
        app,
        ["record", "--agent", str(agent), "--voice-file", str(wav), "--out", str(trace)],
        input="",
    )
    assert result.exit_code == 0, result.output
    assert "stt fallback: adapter neuroedge.perception.providers.fake:stt" in result.output
    assert "1 STT fallback" in result.output
    assert "ALLOW" in result.output
    from neuroedge.trace import load_trace

    document = load_trace(trace)
    (switched,) = [e for e in document["events"] if e["type"] == "stt_fallback"]
    assert switched["data"]["to"].startswith("stt.fallback") and switched["data"]["reason"]
    assert [e for e in document["events"] if e["type"] == "stt_result"][0]["data"]["text"] == (
        "mở cửa"
    )
