"""
TSK-I4-01 — the wake-word detector: `[wake_word]` of agent.toml, the openWakeWord
adapter (a model of your own; none ships, Q-45), and how a turn opens on the word
instead of on VAD (docs/spec/voice_fsm.md §4 T01). No model file is loaded: the
adapter talks to a scripted model, and the tests use `FakeWakeWordDetector`.
"""

from __future__ import annotations

import shutil
import sys
import types

import pytest
from typer.testing import CliRunner

from neuroedge.cli.main import app
from neuroedge.engine.compiler import build
from neuroedge.errors import AgentManifestError, BuildFailed, PerceptionUnavailableError
from neuroedge.hal.audio import AudioFrame, energy_db
from neuroedge.perception import VirtualClock, VoiceParams, VoiceSession
from neuroedge.perception.providers import (
    FakeSpeechToText,
    FakeTextToSpeech,
    FakeWakeWordDetector,
    parse_wake_word,
)
from neuroedge.perception.providers.wake import WAKE_RATE_HZ, WAKE_WINDOW, OpenWakeWord
from neuroedge.sim import SimSession

from .test_voice_speech import RATE, silence, tone, write_wav

runner = CliRunner()
DOOR = "voice-door"


@pytest.fixture(scope="module")
def door(root):
    return root / "fixtures" / "agents" / DOOR / "agent.toml"


# --- `[wake_word]` validation -----------------------------------------------------------


def model_file(tmp_path, name="hey_neuro.onnx"):
    path = tmp_path / name
    path.write_bytes(b"a model of your own")
    return path


def test_a_valid_table_resolves_a_relative_model_path(tmp_path):
    (tmp_path / "models").mkdir()
    model_file(tmp_path / "models", "hey.tflite")
    config = parse_wake_word(
        {"model": "models/hey.tflite", "threshold": 0.7, "word": "hey"},
        source=tmp_path / "agent.toml",
        root=tmp_path,
    )
    assert config.path == tmp_path / "models" / "hey.tflite"
    assert config.word == "hey" and config.threshold == 0.7
    assert config.adapter is None and "hey.tflite" in config.label


def test_the_word_defaults_to_the_model_files_name(tmp_path):
    config = parse_wake_word({"model": str(model_file(tmp_path))}, root=tmp_path)
    assert config.word == "hey_neuro"


@pytest.mark.parametrize(
    ("table", "why"),
    [
        ({}, "needs the path to your own model file"),
        ({"model": "missing.onnx"}, "no model file at"),
        ({"model": "x.onnx", "threshold": 0}, "threshold must be"),
        ({"model": "x.onnx", "threshold": 1.5}, "threshold must be"),
        ({"model": "x.onnx", "threshold": True}, "threshold must be"),
        ({"model": "x.onnx", "extra": 1}, "not fields of [wake_word]"),
        ({"model": "x.onnx", "options": {"x": 1}}, "options"),
    ],
)
def test_a_bad_table_is_refused_with_where_why_how(tmp_path, table, why):
    if table.get("model") == "x.onnx":
        model_file(tmp_path, "x.onnx")
    if table.get("model") == "missing.onnx":
        pass
    with pytest.raises(AgentManifestError) as raised:
        parse_wake_word(table, source=tmp_path / "agent.toml", root=tmp_path)
    error = raised.value
    assert why in error.why or why in error.how, (why, error.why, error.how)
    assert error.where.startswith(str(tmp_path / "agent.toml")) and "[wake_word]" in error.where


def test_a_key_in_the_table_is_refused_and_never_echoed(tmp_path):
    with pytest.raises(AgentManifestError) as raised:
        parse_wake_word({"model": "x.onnx", "api_key": "sk-abcdefghijklmnopqrst"}, root=tmp_path)
    assert "sk-abcdefghijklmnopqrst" not in raised.value.render()
    assert "api_key" in raised.value.where and "leak" in raised.value.why


def test_an_adapter_needs_no_model_file():
    config = parse_wake_word({"provider": "python:my_wake.adapter:make"})
    assert config.adapter == "my_wake.adapter:make" and config.path is None
    assert config.word == "wake", "the adapter names the words it reports"


# --- the openWakeWord adapter ------------------------------------------------------------


class FakeModel:
    """Scripted `openwakeword.Model`: window byte lengths in, scores out."""

    def __init__(self, scores=(0.0,)):
        self.scores = list(scores)
        self.windows: list[int] = []

    def predict(self, window):
        self.windows.append(len(window))
        return {"hey_neuro": self.scores.pop(0) if self.scores else 0.0}


def test_the_openwakeword_provider_loads_the_model_you_point_at(monkeypatch, tmp_path):
    path = model_file(tmp_path, "hey_neuro.tflite")
    built = []

    def Model(wakeword_models, inference_framework):  # noqa: N802 - mirrors openwakeword
        built.append((wakeword_models, inference_framework))
        return FakeModel()

    monkeypatch.setitem(sys.modules, "openwakeword", types.SimpleNamespace(Model=Model))
    detector = OpenWakeWord.from_config(
        parse_wake_word({"model": str(path), "threshold": 0.5}, root=tmp_path)
    )
    assert built == [([str(path)], "tflite")]
    assert isinstance(detector, OpenWakeWord)


def test_a_missing_openwakeword_is_a_three_part_error(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "openwakeword", None)  # `import` raises ImportError
    config = parse_wake_word({"model": str(model_file(tmp_path))}, root=tmp_path)
    with pytest.raises(PerceptionUnavailableError) as raised:
        OpenWakeWord.from_config(config)
    assert "openwakeword" in raised.value.why and "not installed" in raised.value.why
    assert "neuroedge[wake]" in raised.value.how


def test_frames_of_any_rate_are_resampled_and_fed_in_80ms_windows():
    model = FakeModel([0.4, 0.8])
    detector = OpenWakeWord(model, threshold=0.5, word="hey neuro")
    assert detector.detect(AudioFrame(b"", 0, 20, 48000)) is None  # no samples, no window
    # 4 × 20 ms at 48 kHz = one 80 ms window at 16 kHz (640 bytes × 4 = 1280 samples).
    hits = [detector.detect(AudioFrame(tone(20, 48000), i * 20, 20, 48000)) for i in range(8)]
    assert hits[:4] == [None] * 4, "the first window scored 0.4, below the threshold"
    assert hits[7] == ("hey neuro", 0.8)
    assert model.windows == [WAKE_WINDOW * 2, WAKE_WINDOW * 2]


def test_a_frame_the_adapter_cannot_resample_fails_closed():
    detector = OpenWakeWord(FakeModel(), threshold=0.5, word="hey")
    with pytest.raises(PerceptionUnavailableError) as raised:
        detector.detect(AudioFrame(b"\x00\x00" * 100, 0, 20, 1000))  # 1 kHz: outside 8–96 kHz
    assert "16 kHz" in raised.value.why and "8–96 kHz" in raised.value.how


def test_a_score_below_the_threshold_never_opens_a_turn():
    detector = OpenWakeWord(FakeModel([0.2]), threshold=0.5, word="hey")
    frames = [AudioFrame(tone(20, WAKE_RATE_HZ), i * 20, 20, WAKE_RATE_HZ) for i in range(4)]
    assert [detector.detect(f) for f in frames] == [None, None, None, None]


@pytest.mark.parametrize("answer", [[1], "scores", None, {"hey": float("nan")}, {"hey": 2.0}])
def test_a_model_that_answers_nonsense_fails_closed(answer):
    class Bad(FakeModel):
        def predict(self, window):
            return answer

    detector = OpenWakeWord(Bad(), threshold=0.5, word="hey")
    with pytest.raises(PerceptionUnavailableError) as raised:
        for i in range(4):
            detector.detect(AudioFrame(tone(20, WAKE_RATE_HZ), i * 20, 20, WAKE_RATE_HZ))
    assert "wake word" in raised.value.where
    assert raised.value.how


# --- a turn opens on the wake word, not on VAD (T01) -------------------------------------


def voice_on(door, tmp_path, *, wake=None, params=None, transcripts=("mở cửa",)):
    clock = VirtualClock()
    session = SimSession.load(door, clock=clock)
    stt = FakeSpeechToText(transcripts, latency_ms=100)
    voice = VoiceSession(
        session,
        clock=clock,
        params=params,
        wake_word=wake,
        stt=stt,
        tts=FakeTextToSpeech(ms_per_char=10),
    )
    wav = write_wav(tmp_path / "turn.wav", silence(300) + tone(600, RATE) + silence(700), rate=RATE)
    source = session.hal.audio_file(wav, called_from="test")
    return voice, source, stt


def run(voice, source):
    import asyncio

    asyncio.run(voice.play(source))
    return [
        (e["from"], e["to"], e["trigger"], e["turn"])
        for e in voice.events.of_type("voice_state_changed")
    ]


def test_the_wake_word_opens_the_turn(door, tmp_path):
    wake = FakeWakeWordDetector([15], word="hey neuro", score=0.93)
    voice, source, stt = voice_on(door, tmp_path, wake=wake)
    states = run(voice, source)
    assert states[0] == ("IDLE", "LISTENING", "wake_word", 1)
    assert [t.heard for t in voice.turns] == ["mở cửa"]
    (detected,) = voice.events.of_type("wake_word_detected")
    assert detected == {"word": "hey neuro", "score": 0.93}
    assert voice.hal.pin("door_lock").pulsed, "the transcript went through the gate"
    # The pre-roll of the spec is kept: the clip starts before the wake word's frame.
    clip = stt.clips[0]
    assert clip.duration_ms >= 400 and energy_db(clip.pcm) > -40


def test_vad_alone_does_not_open_a_turn_with_a_wake_word_configured(door, tmp_path):
    voice, source, stt = voice_on(door, tmp_path)  # no detector, vad_activation off (default)
    states = run(voice, source)
    assert states == [] and voice.turns == [] and stt.clips == []
    assert voice.events.of_type("audio_in_vad_start"), "the VAD still ran"


def test_without_a_wake_word_vad_still_opens_the_turn(door, tmp_path):
    voice, source, _ = voice_on(door, tmp_path, params=VoiceParams(vad_activation=True))
    states = run(voice, source)
    assert states[0] == ("IDLE", "LISTENING", "speech_start", 1)
    assert [t.heard for t in voice.turns] == ["mở cửa"]


def test_a_wake_word_and_vad_activation_together_are_refused(door, tmp_path):
    clock = VirtualClock()
    session = SimSession.load(door, clock=clock)
    with pytest.raises(ValueError, match="wake word is configured and vad_activation is on"):
        VoiceSession(
            session,
            clock=clock,
            params=VoiceParams(vad_activation=True),
            wake_word=FakeWakeWordDetector([1]),
        )
    session.close()


@pytest.mark.parametrize("answer", [("", 0.5), ("hey", 2.0), ("hey", float("nan")), "hey", 0.5])
def test_a_detector_that_answers_nonsense_never_opens_a_turn(door, tmp_path, answer):
    class Bad(FakeWakeWordDetector):
        def detect(self, frame):
            return answer

    voice, source, _ = voice_on(door, tmp_path, wake=Bad([0]))
    with pytest.raises(PerceptionUnavailableError) as raised:
        run(voice, source)
    assert "turn was not opened" in raised.value.why
    assert voice.turns == []


# --- the build and the CLI ----------------------------------------------------------------


EXTRA = """
[stt]
provider = "python:neuroedge.perception.providers.fake:stt"
[stt.options]
transcripts = ["mở cửa"]

[tts]
provider = "python:neuroedge.perception.providers.fake:tts"
[tts.options]
ms_per_char = 10

[wake_word]
provider = "python:neuroedge.perception.providers.fake:wake"
[wake_word.options]
frames = [15]
word   = "hey neuro"
score  = 0.93
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


def test_the_build_checks_the_wake_word_table(project, tmp_path):
    agent, _ = project(
        """
[wake_word]
model = "models/missing.onnx"
"""
    )
    with pytest.raises(BuildFailed) as raised:
        build(agent, target="sim", board_id="sim-default")
    whys = " ".join(p.why for p in raised.value.problems)
    assert "model file" in whys


def test_the_build_refuses_a_wake_word_without_audio_in(project):
    agent, _ = project(
        """
[wake_word]
provider = "python:neuroedge.perception.providers.fake:wake"
"""
    )
    text = agent.read_text(encoding="utf-8").replace(
        '"audio.in"    = { sample_rate_hz = 16000 }\n', ""
    )
    agent.write_text(text, encoding="utf-8")
    with pytest.raises(BuildFailed) as raised:
        build(agent, target="sim", board_id="sim-default")
    assert any("[wake_word] hears frames through audio.in" in p.why for p in raised.value.problems)


def test_the_build_refuses_a_wake_word_for_esp32s3_where_none_runs(project):
    agent, _ = project()
    with pytest.raises(BuildFailed) as raised:
        build(agent, target="esp32s3", board_id="esp32s3-box-3")
    assert any("no wake-word detector yet" in p.why for p in raised.value.problems)


def test_the_voice_cli_opens_the_turn_on_the_wake_word(project, tmp_path):
    agent, wav = project()
    result = runner.invoke(app, ["run", "--agent", str(agent), "--voice-file", str(wav)], input="")
    assert result.exit_code == 0, result.output
    assert "wake word: adapter neuroedge.perception.providers.fake:wake" in result.output
    assert "heard: “mở cửa”" in result.output and "ALLOW" in result.output


def test_the_voice_cli_without_a_wake_word_says_so(project, tmp_path):
    agent, wav = project("")
    result = runner.invoke(app, ["run", "--agent", str(agent), "--voice-file", str(wav)], input="")
    # No [stt] either: the CLI exits 1 with the Q-15 hint before any wake-word question.
    assert result.exit_code == 1 and "[stt]" in result.output
