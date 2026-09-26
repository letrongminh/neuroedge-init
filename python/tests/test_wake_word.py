"""
TSK-I4-01 — the wake-word detector: `[wake_word]` of agent.toml, the openWakeWord
adapter (models of your own; none ships, Q-45), and how a turn opens on the word
instead of on VAD (docs/spec/voice_fsm.md §4 T01). No real model is loaded: the
adapter talks to a scripted model that enforces the same numpy int16 contract as
openWakeWord, and the driver tests use `FakeWakeWordDetector`.
"""

from __future__ import annotations

import shutil
import sys
import types

import numpy as np
import pytest
from typer.testing import CliRunner

import neuroedge.hal.linux as linux
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

from .test_hal_linux import LINES, FakeGpiod
from .test_voice_speech import RATE, silence, tone, write_wav

runner = CliRunner()
DOOR = "voice-door"
MODEL_FIELDS = ("model", "melspectrogram", "embedding")


@pytest.fixture(scope="module")
def door(root):
    return root / "fixtures" / "agents" / DOOR / "agent.toml"


@pytest.fixture
def gpio(monkeypatch, tmp_path):
    chip = tmp_path / "gpiochip0"
    chip.write_text("")
    fake = FakeGpiod({str(chip): LINES})
    monkeypatch.setattr(linux, "CHIP_GLOB", str(tmp_path / "gpiochip*"))
    monkeypatch.setattr(linux, "_import_gpiod", lambda: fake)
    return fake


# --- `[wake_word]` validation -----------------------------------------------------------


def model_files(tmp_path, names=MODEL_FIELDS):
    """The three files a user supplies, as tiny stand-ins (nothing loads them here)."""
    (tmp_path / "models").mkdir(exist_ok=True)
    for name in names:
        (tmp_path / "models" / f"{name}.onnx").write_bytes(b"a model of your own")
    return {name: f"models/{name}.onnx" for name in names}


def table(tmp_path, **overrides):
    return {**model_files(tmp_path), **overrides}


def test_a_valid_table_resolves_relative_model_paths(tmp_path):
    config = parse_wake_word(
        {**table(tmp_path), "threshold": 0.7, "word": "hey"},
        source=tmp_path / "agent.toml",
        root=tmp_path,
    )
    assert config.path == tmp_path / "models" / "model.onnx"
    assert config.melspectrogram_path == tmp_path / "models" / "melspectrogram.onnx"
    assert config.embedding_path == tmp_path / "models" / "embedding.onnx"
    assert config.word == "hey" and config.threshold == 0.7
    assert config.adapter is None and config.missing_models() == []
    assert "model.onnx" in config.label


def test_the_word_defaults_to_the_model_files_name(tmp_path):
    config = parse_wake_word(table(tmp_path), root=tmp_path)
    assert config.word == "model"


def test_the_shape_is_checked_without_the_files_and_the_files_on_demand(tmp_path):
    # The models may live on the device, not on this machine: `check_files=False`
    # (a build, a typed session) validates the table, and a voice session asks for
    # the files before it starts.
    missing_dir = tmp_path / "elsewhere"
    absent = {
        "model": str(missing_dir / "model.onnx"),
        "melspectrogram": str(missing_dir / "mel.onnx"),
        "embedding": str(missing_dir / "emb.onnx"),
    }
    parsed = parse_wake_word(absent, root=tmp_path)  # shape only: no error
    assert parsed.missing_models() == [
        ("model", missing_dir / "model.onnx"),
        ("melspectrogram", missing_dir / "mel.onnx"),
        ("embedding", missing_dir / "emb.onnx"),
    ]
    with pytest.raises(AgentManifestError, match="no model file at"):
        parse_wake_word(absent, root=tmp_path, check_files=True)


@pytest.mark.parametrize(
    ("table_update", "where", "why"),
    [
        ({"model": ""}, "model", "needs model"),
        ({"melspectrogram": ""}, "melspectrogram", "needs melspectrogram"),
        ({"embedding": ""}, "embedding", "needs embedding"),
        ({"threshold": 0}, "threshold", "threshold must be"),
        ({"threshold": 1.5}, "threshold", "threshold must be"),
        ({"threshold": True}, "threshold", "threshold must be"),
        ({"extra": 1}, "extra", "not fields of [wake_word]"),
        ({"options": {"x": 1}}, "options", "options"),
    ],
)
def test_a_bad_table_is_refused_with_where_why_how(tmp_path, table_update, where, why):
    with pytest.raises(AgentManifestError) as raised:
        parse_wake_word(
            {**table(tmp_path), **table_update}, source=tmp_path / "a.toml", root=tmp_path
        )
    error = raised.value
    assert where in error.where, (where, error.where)
    assert why in error.why or why in error.how, (why, error.why, error.how)
    assert error.where.startswith(str(tmp_path / "a.toml")) and "[wake_word]" in error.where


def test_a_key_in_the_table_is_refused_and_never_echoed(tmp_path):
    with pytest.raises(AgentManifestError) as raised:
        parse_wake_word({**table(tmp_path), "api_key": "sk-abcdefghijklmnopqrst"}, root=tmp_path)
    assert "sk-abcdefghijklmnopqrst" not in raised.value.render()
    assert "api_key" in raised.value.where and "leak" in raised.value.why


def test_an_adapter_needs_no_model_files():
    config = parse_wake_word({"provider": "python:my_wake.adapter:make"})
    assert config.adapter == "my_wake.adapter:make" and config.path is None
    assert config.missing_models() == [], "an adapter owns its own files"
    assert config.word == "wake", "the adapter names the words it reports"


# --- the openWakeWord adapter ------------------------------------------------------------


class FakeModel:
    """
    Scripted `openwakeword.Model`, enforcing its contract: `predict` takes a numpy
    int16 array (bytes raise ValueError there), and it answers a name-to-score map.
    """

    def __init__(self, answers=({"model": 0.0},)):
        self.answers = list(answers)
        self.windows: list[tuple[int, str]] = []

    def predict(self, window):
        if isinstance(window, (bytes, bytearray, memoryview)) or not isinstance(window, np.ndarray):
            raise ValueError("Expected a numpy array of audio samples")
        if window.dtype != np.int16:
            raise ValueError(f"Expected dtype int16, got {window.dtype}")
        self.windows.append((window.size, str(window.dtype)))
        return self.answers.pop(0) if self.answers else {"model": 0.0}


def fake_openwakeword(answers=({"model": 0.9},)):
    """The slice of openwakeword `from_config` uses, plus a downloader that must not run."""
    module = types.SimpleNamespace()
    module.models: list[dict] = []

    def Model(**kwargs):  # noqa: N802 - mirrors openwakeword
        module.models.append(kwargs)
        return FakeModel(answers)

    def download_models(*args, **kwargs):
        raise AssertionError("NeuroEdge must never call openwakeword's downloader")

    module.Model = Model
    module.download_models = download_models
    return module


def openwakeword_config(tmp_path):
    return parse_wake_word(table(tmp_path), root=tmp_path)


def test_the_openwakeword_provider_loads_your_three_models(monkeypatch, tmp_path):
    module = fake_openwakeword()
    monkeypatch.setitem(sys.modules, "openwakeword", module)
    detector = OpenWakeWord.from_config(openwakeword_config(tmp_path))
    (kwargs,) = module.models
    assert kwargs == {
        "wakeword_models": [str(tmp_path / "models" / "model.onnx")],
        "inference_framework": "onnx",
        "melspec_model_path": str(tmp_path / "models" / "melspectrogram.onnx"),
        "embedding_model_path": str(tmp_path / "models" / "embedding.onnx"),
    }
    assert isinstance(detector, OpenWakeWord)


def test_a_missing_openwakeword_is_a_three_part_error(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "openwakeword", None)  # `import` raises ImportError
    with pytest.raises(PerceptionUnavailableError) as raised:
        OpenWakeWord.from_config(openwakeword_config(tmp_path))
    assert "openwakeword" in raised.value.why and "not installed" in raised.value.why
    assert "neuroedge[wake]" in raised.value.how


def test_a_missing_model_file_is_refused_before_the_library_loads_it(monkeypatch, tmp_path):
    module = fake_openwakeword()
    monkeypatch.setitem(sys.modules, "openwakeword", module)
    config = openwakeword_config(tmp_path)
    (tmp_path / "models" / "melspectrogram.onnx").unlink()
    with pytest.raises(PerceptionUnavailableError) as raised:
        OpenWakeWord.from_config(config)
    assert "melspectrogram" in raised.value.where and "no wake-word model file" in raised.value.why
    assert "never" in raised.value.how
    assert module.models == [], "Model() is never reached with a missing path"


def test_frames_of_any_rate_are_resampled_and_fed_as_int16_windows(monkeypatch, tmp_path):
    module = fake_openwakeword(answers=({"model": 0.4}, {"model": 0.8}))
    monkeypatch.setitem(sys.modules, "openwakeword", module)
    detector = OpenWakeWord.from_config(openwakeword_config(tmp_path))
    detector.threshold = 0.5
    assert detector.detect(AudioFrame(b"", 0, 20, 48000)) is None  # no samples, no window
    # 4 × 20 ms at 48 kHz = one 80 ms window at 16 kHz (640 bytes × 4 = 1280 samples).
    hits = [detector.detect(AudioFrame(tone(20, 48000), i * 20, 20, 48000)) for i in range(8)]
    assert hits[:4] == [None] * 4, "the first window scored 0.4, below the threshold"
    assert hits[7] == ("model", 0.8)
    assert detector.model.windows == [(WAKE_WINDOW, "int16"), (WAKE_WINDOW, "int16")]


def test_only_the_configured_words_score_may_open_a_turn(monkeypatch, tmp_path):
    module = fake_openwakeword(
        answers=(
            {"silero_vad": 0.99},  # openWakeWord's own VAD: never a wake word
            {"other_model": 0.99},  # another trained word: not the configured one
            {"hey_neuro": 0.9, "other_model": 0.99},
        )
    )
    monkeypatch.setitem(sys.modules, "openwakeword", module)
    config = parse_wake_word({**table(tmp_path), "word": "hey_neuro"}, root=tmp_path)
    detector = OpenWakeWord.from_config(config)
    window = AudioFrame(tone(20, WAKE_RATE_HZ), 0, 20, WAKE_RATE_HZ)

    def one_window():
        return [detector.detect(window) for _ in range(4)]

    for _ in range(2):
        with pytest.raises(PerceptionUnavailableError, match="none is the configured word"):
            one_window()  # only silero_vad / only another word
    # A multi-class model with the configured word present: its own score acts,
    # never the higher score of another class.
    assert one_window()[-1] == ("hey_neuro", 0.9)


def test_a_models_class_name_matches_the_word_up_to_separators(monkeypatch, tmp_path):
    module = fake_openwakeword(answers=({"hey_neuro": 0.9},))
    monkeypatch.setitem(sys.modules, "openwakeword", module)
    config = parse_wake_word({**table(tmp_path), "word": "Hey Neuro"}, root=tmp_path)
    detector = OpenWakeWord.from_config(config)
    window = AudioFrame(tone(20, WAKE_RATE_HZ), 0, 20, WAKE_RATE_HZ)
    assert [detector.detect(window) for _ in range(4)][-1] == ("Hey Neuro", 0.9)


def test_a_frame_the_adapter_cannot_resample_fails_closed(monkeypatch, tmp_path):
    module = fake_openwakeword()
    monkeypatch.setitem(sys.modules, "openwakeword", module)
    detector = OpenWakeWord.from_config(openwakeword_config(tmp_path))
    with pytest.raises(PerceptionUnavailableError) as raised:
        detector.detect(AudioFrame(b"\x00\x00" * 100, 0, 20, 1000))  # 1 kHz: outside 8–96 kHz
    assert "16 kHz" in raised.value.why and "8–96 kHz" in raised.value.how


@pytest.mark.parametrize("answer", [[1], "scores", None, {"model": float("nan")}, {"model": 2.0}])
def test_a_model_that_answers_nonsense_fails_closed(answer):
    detector = OpenWakeWord(FakeModel([answer] * 4), threshold=0.5, word="model")
    with pytest.raises(PerceptionUnavailableError):
        for i in range(4):
            detector.detect(AudioFrame(tone(20, WAKE_RATE_HZ), i * 20, 20, WAKE_RATE_HZ))


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
    # A detector IS configured (it just never fires): VAD may not open a turn (T01).
    voice, source, stt = voice_on(door, tmp_path, wake=FakeWakeWordDetector([]))
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


def test_a_detector_that_raises_degrades_the_session_not_a_crash(door, tmp_path):
    class Broken:
        def detect(self, frame):
            raise RuntimeError("the adapter's own bug")

    voice, source, _ = voice_on(door, tmp_path, wake=Broken())
    states = run(voice, source)  # the session ran to the end of the file
    assert states == [] and voice.turns == [], "no turn opens from a broken detector"
    (unavailable,) = voice.events.of_type("wake_word_unavailable")
    assert "RuntimeError" in unavailable["reason"] and "fix it" in unavailable["reason"]
    assert voice.wake_failures > 1, "every frame was tried"
    assert len(voice.events.of_type("wake_word_unavailable")) == 1, "recorded once"


@pytest.mark.parametrize("answer", [("", 0.5), ("hey", 2.0), ("hey", float("nan")), "hey", 0.5])
def test_a_detector_that_answers_nonsense_never_opens_a_turn(door, tmp_path, answer):
    class Bad(FakeWakeWordDetector):
        def detect(self, frame):
            return answer

    voice, source, _ = voice_on(door, tmp_path, wake=Bad([0]))
    states = run(voice, source)
    assert states == [] and voice.turns == []
    (unavailable,) = voice.events.of_type("wake_word_unavailable")
    assert "turn was not opened" in unavailable["reason"]


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

DETECTORLESS = """
[wake_word]
model         = "models/hey_neuro.onnx"
melspectrogram = "models/melspectrogram.onnx"
embedding     = "models/embedding_model.onnx"
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


def test_the_build_checks_the_shape_not_the_files(project):
    # The three files are absent here, and the build passes: they may live on the
    # device. A typed session (`-c`, `mcp serve`) needs none either.
    agent, _ = project(DETECTORLESS)
    report = build(agent, target="sim", board_id="sim-default")
    assert report.agent.startswith("voice-door")
    session = SimSession.load(agent)
    try:
        assert session.manifest.label.startswith("voice-door")
    finally:
        session.close()


def test_the_build_refuses_a_bad_wake_word_table(project):
    agent, _ = project(DETECTORLESS.replace('embedding     = "models/embedding_model.onnx"\n', ""))
    with pytest.raises(BuildFailed) as raised:
        build(agent, target="sim", board_id="sim-default")
    assert any("needs embedding" in p.why for p in raised.value.problems)


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


def test_the_build_checks_the_boards_audio_in_rate(project):
    from neuroedge.engine.compiler import check_wake_word, load_agent_manifest
    from neuroedge.hal.board import load_board_by_id

    agent, _ = project()
    manifest = load_agent_manifest(agent)
    board = load_board_by_id("linux-rpi5")
    bare = type(board)(
        id="bare",
        target="linux",
        mcu="x",
        capabilities={**board.capabilities, "audio_in": {"channels": 2}},  # no sample_rate_hz
    )
    (problem,) = check_wake_word(manifest, bare)
    assert "no sample_rate_hz" in problem.why and "audio.in" in problem.where


def test_the_build_refuses_a_wake_word_for_esp32s3_where_none_runs(project):
    agent, _ = project()
    with pytest.raises(BuildFailed) as raised:
        build(agent, target="esp32s3", board_id="esp32s3-box-3")
    assert any("no wake-word detector yet" in p.why for p in raised.value.problems)


def test_the_voice_cli_checks_the_model_files_before_any_line(project, gpio, tmp_path):
    agent, wav = project(DETECTORLESS)  # paths do not exist anywhere
    result = runner.invoke(
        app, ["run", "--target", "linux", "--agent", str(agent), "--voice-file", str(wav)], input=""
    )
    assert result.exit_code == 1, result.output
    assert "no model file at" in result.output and "hey_neuro.onnx" in result.output
    assert gpio.requests == [], "no GPIO line is requested before the models are checked"


def test_the_voice_cli_checks_the_detector_library_before_any_line(project, gpio, monkeypatch):
    agent, wav = project(DETECTORLESS)
    (agent.parent / "models").mkdir()
    for name in ("hey_neuro.onnx", "melspectrogram.onnx", "embedding_model.onnx"):
        (agent.parent / "models" / name).write_bytes(b"a model of your own")
    monkeypatch.setitem(sys.modules, "openwakeword", None)  # `import` raises ImportError
    result = runner.invoke(
        app, ["run", "--target", "linux", "--agent", str(agent), "--voice-file", str(wav)], input=""
    )
    assert result.exit_code == 1, result.output
    assert "openwakeword" in result.output and "not installed" in result.output
    assert gpio.requests == [], "no GPIO line is requested before the detector is available"


def test_the_voice_cli_opens_the_turn_on_the_wake_word(project, tmp_path):
    agent, wav = project()
    result = runner.invoke(app, ["run", "--agent", str(agent), "--voice-file", str(wav)], input="")
    assert result.exit_code == 0, result.output
    assert "wake word: adapter neuroedge.perception.providers.fake:wake" in result.output
    assert "heard: “mở cửa”" in result.output and "ALLOW" in result.output


def test_the_voice_cli_degrades_on_a_broken_detector_and_keeps_going(project, tmp_path):
    agent, wav = project(EXTRA.replace("score  = 0.93", "score  = 2.0"))
    trace = tmp_path / "broken.json"
    result = runner.invoke(
        app,
        ["run", "--agent", str(agent), "--voice-file", str(wav), "--trace-out", str(trace)],
        input="",
    )
    assert result.exit_code == 0, result.output
    assert "0 turns" in result.output and "1 wake word unavailable" in result.output
    from neuroedge.trace import load_trace

    document = load_trace(trace)
    (unavailable,) = [e for e in document["events"] if e["type"] == "wake_word_unavailable"]
    assert "turn was not opened" in unavailable["data"]["reason"]
