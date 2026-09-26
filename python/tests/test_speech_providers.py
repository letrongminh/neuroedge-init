"""
TSK-S3-13 — speech providers: `[stt]` / `[tts]` of agent.toml (FR-MDL-09, Q-12) and
the OpenAI audio adapter, with no network: a fake opener stands in for urllib's,
and the few tests that need a real HTTP stack talk to a server on 127.0.0.1.
"""

from __future__ import annotations

import asyncio
import http.client
import io
import json
import shutil
import subprocess
import sys
import threading
import urllib.error
import wave
from email.parser import BytesParser
from email.policy import default as email_policy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from neuroedge.engine.compiler import build, check_speech, load_agent_manifest
from neuroedge.errors import AgentManifestError, BuildFailed
from neuroedge.hal.audio import read_wav_bytes, wav_bytes
from neuroedge.perception.providers import (
    AudioClip,
    FakeSpeechToText,
    FakeTextToSpeech,
    OpenAISpeaker,
    OpenAITranscriber,
    SpeechUnavailable,
    clean_transcript,
    load_speech_configs,
    make_speech,
    parse_speech,
)
from neuroedge.perception.providers.fake import tone

KEY = "sk-test-DO-NOT-LEAK-0123456789abcdef"
ENV = "NEUROEDGE_TEST_SPEECH_KEY"
SPEECH = "SECRET-WORDS-mở-cửa-kho"  # what a person said: never in an error


def stt(**table):
    return parse_speech("stt", {"model": "whisper-1", "api_key_env": ENV, **table})


def tts(**table):
    return parse_speech("tts", {"model": "tts-1", "voice": "alloy", "api_key_env": ENV, **table})


def clip(ms=1000, turn=1):
    return AudioClip(tone(ms, 16000), 16000, turn)


# --- [stt] / [tts] ----------------------------------------------------------------------------


def test_a_minimal_table_takes_the_openai_defaults():
    config = stt(language="vi")
    assert (config.provider, config.base_url, config.model, config.language) == (
        "openai",
        "https://api.openai.com/v1",
        "whisper-1",
        "vi",
    )
    assert config.timeout_s == 15.0 and config.adapter is None
    assert "key from $" + ENV in config.label and KEY not in config.label
    groq = stt(base_url="https://api.groq.com/openai/v1/", model="whisper-large-v3")
    assert groq.base_url == "https://api.groq.com/openai/v1"  # one trailing slash dropped


def test_a_local_server_needs_no_key():
    config = parse_speech(
        "tts", {"base_url": "http://localhost:8880/v1", "model": "kokoro", "voice": "af_heart"}
    )
    assert config.api_key_env is None and "no key" in config.label


def _refused(role, table):
    with pytest.raises(AgentManifestError) as caught:
        parse_speech(role, table)
    error = caught.value
    assert error.where and error.why and error.how  # FR-DX-04
    return error


@pytest.mark.parametrize(
    "table",
    [
        {"model": "whisper-1", "api_key": KEY},
        {"model": "whisper-1", "api_key_env": ENV, "token": KEY},
        {"provider": "python:x.y:z", "options": {"nested": {"secret": KEY}}},
    ],
)
def test_a_key_in_agent_toml_is_refused_without_repeating_it(table):
    error = _refused("stt", table)
    assert "never be written in agent.toml" in error.why
    assert KEY not in error.render()


def test_an_api_key_env_that_is_not_a_variable_name_is_not_echoed():
    error = _refused("stt", {"model": "whisper-1", "api_key_env": KEY + "!"})
    assert "revoke it" in error.why and KEY not in error.render()


@pytest.mark.parametrize(
    "url",
    [
        f"https://user:{KEY}@api.example.com/v1",
        f"https://api.example.com/v1?key={KEY}",
        "https://api.example.com/v1#x",
    ],
)
def test_a_base_url_carrying_credentials_is_refused_without_repeating_it(url):
    error = _refused("stt", {"model": "whisper-1", "base_url": url})
    assert "credentials" in error.why and KEY not in error.render()


def test_a_key_never_crosses_the_network_in_clear_text():
    error = _refused(
        "stt", {"model": "m", "base_url": "http://192.168.1.10:8000/v1", "api_key_env": ENV}
    )
    assert "clear text" in error.why and "192.168.1.10" in error.why
    # This machine is fine, and so is a keyless server on the LAN.
    parse_speech("stt", {"model": "m", "base_url": "http://127.0.0.1:8000/v1", "api_key_env": ENV})
    parse_speech("stt", {"model": "m", "base_url": "http://192.168.1.10:8000/v1"})


@pytest.mark.parametrize(
    "role, table, where, fragment",
    [
        ("stt", {"model": "whisper-1"}, "api_key_env", "needs a key"),
        ("stt", {"api_key_env": ENV}, "model", "model"),
        ("tts", {"model": "tts-1", "api_key_env": ENV}, "voice", "voice"),
        (
            "stt",
            {"model": "m", "api_key_env": ENV, "language": "Vietnamese"},
            "language",
            "ISO-639-1",
        ),
        ("stt", {"model": "m", "api_key_env": ENV, "timeout_s": 0}, "timeout_s", "timeout_s"),
        ("stt", {"model": "m", "api_key_env": ENV, "timeout_s": 999}, "timeout_s", "timeout_s"),
        ("stt", {"model": "m", "api_key_env": ENV, "base_url": "ftp://x"}, "base_url", "http(s)"),
        ("stt", {"model": "m", "api_key_env": ENV, "provider": "whisper"}, "provider", "provider"),
        ("stt", {"model": "m", "api_key_env": ENV, "voice": "alloy"}, "voice", "not fields"),
        (
            "stt",
            {"model": "m", "api_key_env": ENV, "options": {"x": 1}},
            "options",
            "custom adapter",
        ),
    ],
)
def test_bad_fields_are_refused_where_they_are(role, table, where, fragment):
    error = _refused(role, table)
    assert error.where.endswith(where), error.where
    assert fragment in error.why


def test_language_in_tts_says_the_speech_api_has_none():
    error = _refused(
        "tts", {"model": "tts-1", "voice": "alloy", "api_key_env": ENV, "language": "vi"}
    )
    assert "no language field" in error.how


def test_a_custom_adapter_needs_no_model_and_gets_its_options():
    config = parse_speech(
        "stt",
        {
            "provider": "python:neuroedge.perception.providers.fake:stt",
            "options": {"transcripts": ["a"]},
        },
    )
    provider = make_speech(config)
    assert isinstance(provider, FakeSpeechToText) and provider.transcripts == ["a"]


def test_an_adapter_without_the_method_is_refused():
    config = parse_speech("tts", {"provider": "python:neuroedge.perception.providers.fake:stt"})
    with pytest.raises(AgentManifestError, match="no synthesize"):
        make_speech(config)


def test_an_adapter_factory_that_raises_is_a_manifest_error():
    config = parse_speech(
        "stt",
        {"provider": "python:neuroedge.perception.providers.fake:stt", "options": {"latency": 1}},
    )
    with pytest.raises(AgentManifestError, match="unknown options"):
        make_speech(config)


# --- the build ------------------------------------------------------------------------------------


@pytest.fixture
def agent(root, tmp_path):
    """A copy of voice-door; `agent(extra)` appends TOML to its agent.toml."""
    folder = tmp_path / "voice-door"
    shutil.copytree(root / "fixtures" / "agents" / "voice-door", folder)
    path = folder / "agent.toml"
    base = path.read_text(encoding="utf-8")

    def write(extra: str = ""):
        path.write_text(base + extra, encoding="utf-8")
        return path

    return write


@pytest.fixture
def fresh_actions():
    from neuroedge.actions import spec

    saved = dict(spec.REGISTRY)
    spec.REGISTRY.clear()
    yield
    spec.REGISTRY.clear()
    spec.REGISTRY.update(saved)


def test_no_speech_tables_is_exactly_as_before(agent, fresh_actions):
    path = agent()
    assert load_speech_configs(load_agent_manifest(path)) == (None, None)
    assert check_speech(load_agent_manifest(path)) == []
    build(path, target="sim", board_id="sim-default")


def test_the_build_reports_every_bad_speech_table(agent, fresh_actions):
    path = agent(f'\n[stt]\nmodel = "whisper-1"\napi_key = "{KEY}"\n\n[tts]\nmodel = "tts-1"\n')
    with pytest.raises(BuildFailed) as caught:
        build(path, target="sim", board_id="sim-default")
    wheres = [problem.where for problem in caught.value.problems]
    assert any("[stt] api_key" in w for w in wheres) and any("[tts]" in w for w in wheres)
    assert KEY not in "\n".join(problem.render() for problem in caught.value.problems)


def test_speech_needs_the_audio_primitives_declared(agent, fresh_actions):
    path = agent(f'\n[stt]\nmodel = "whisper-1"\napi_key_env = "{ENV}"\n')
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text.replace('"audio.in"    = { sample_rate_hz = 16000 }\n', ""), encoding="utf-8"
    )
    with pytest.raises(BuildFailed) as caught:
        build(path, target="sim", board_id="sim-default")
    (problem,) = caught.value.problems
    assert problem.where.endswith("[requires]") and "[stt] needs audio.in" in problem.why
    assert '"audio.in" = { sample_rate_hz = 16000 }' in problem.how


def test_the_build_imports_a_custom_adapter(agent, fresh_actions):
    path = agent('\n[stt]\nprovider = "python:no_such_speech_module:make"\n')
    with pytest.raises(BuildFailed) as caught:
        build(path, target="sim", board_id="sim-default")
    assert any("cannot import" in p.why for p in caught.value.problems)


def test_the_build_accepts_a_good_pair(agent, fresh_actions):
    path = agent(
        f'\n[stt]\nmodel = "whisper-1"\nlanguage = "vi"\napi_key_env = "{ENV}"\n'
        f'\n[tts]\nbase_url = "http://localhost:8880/v1"\nmodel = "kokoro"\nvoice = "af_heart"\n'
    )
    build(path, target="sim", board_id="sim-default")
    stt_config, tts_config = load_speech_configs(load_agent_manifest(path))
    assert stt_config.language == "vi" and tts_config.voice == "af_heart"


# --- the OpenAI audio adapter ---------------------------------------------------------------------


class FakeResponse:
    def __init__(self, body: bytes) -> None:
        self.body = body
        self.headers: dict[str, str] = {}

    def read(self, limit: int = -1) -> bytes:
        return self.body if limit < 0 else self.body[:limit]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeOpener:
    def __init__(self, *answers) -> None:
        self.answers = list(answers)
        self.requests: list = []

    def open(self, request, timeout=None):
        self.requests.append((request, timeout))
        answer = self.answers.pop(0)
        if isinstance(answer, BaseException):
            raise answer
        return FakeResponse(answer)


def http_error(code: int, body: bytes = b"") -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://x/v1", code, "err", {}, io.BytesIO(body))


def run(awaitable):
    return asyncio.run(awaitable)


def form(request) -> dict:
    content_type = request.get_header("Content-type")
    message = BytesParser(policy=email_policy).parsebytes(
        b"Content-Type: " + content_type.encode() + b"\r\n\r\n" + request.data
    )
    return {
        part.get_param("name", header="content-disposition"): part.get_payload(decode=True)
        for part in message.iter_parts()
    }


def test_transcribe_posts_the_openai_multipart_request():
    opener = FakeOpener(json.dumps({"text": "  mở   cửa "}).encode())
    provider = OpenAITranscriber(stt(language="vi"), environ={ENV: KEY}, opener=opener)
    audio = clip(800, turn=3)
    transcript = run(provider.transcribe(audio))
    assert transcript.text == "mở cửa" and transcript.latency_ms is None  # the driver times it
    ((request, timeout),) = opener.requests
    assert request.full_url == "https://api.openai.com/v1/audio/transcriptions"
    assert request.get_method() == "POST" and timeout == 15.0
    assert request.get_header("Authorization") == f"Bearer {KEY}"
    fields = form(request)
    assert fields["model"] == b"whisper-1" and fields["language"] == b"vi"
    assert fields["response_format"] == b"json"
    assert read_wav_bytes(fields["file"]) == (audio.pcm, 16000, 1, 2)


def test_an_empty_transcript_is_heard_nothing_not_a_failure():
    provider = OpenAITranscriber(stt(), environ={ENV: KEY}, opener=FakeOpener(b'{"text": ""}'))
    assert run(provider.transcribe(clip())).text == ""


def test_a_clip_too_short_for_words_is_never_sent():
    opener = FakeOpener()
    provider = OpenAITranscriber(stt(), environ={ENV: KEY}, opener=opener)
    assert run(provider.transcribe(clip(60))).text == "" and opener.requests == []


def test_no_key_in_the_environment_sends_nothing():
    opener = FakeOpener()
    provider = OpenAITranscriber(stt(), environ={}, opener=opener)
    with pytest.raises(SpeechUnavailable) as caught:
        run(provider.transcribe(clip()))
    assert caught.value.called is False and ENV in caught.value.why
    assert opener.requests == []


@pytest.mark.parametrize(
    "answer, fragment",
    [
        (http_error(401, f"bad key {KEY}, you said {SPEECH}".encode()), "rejected the API key"),
        (http_error(404), "no such endpoint or model"),
        (http_error(429), "rate limiting"),
        (http_error(500, SPEECH.encode()), "failed (HTTP 500)"),
        (http_error(302), "never follows a redirect"),
        (
            urllib.error.URLError(ConnectionRefusedError(61, "Connection refused")),
            "could not be reached",
        ),
        (urllib.error.URLError(TimeoutError("timed out")), "did not answer within"),
        (TimeoutError("timed out"), "did not answer within"),
        (http.client.IncompleteRead(b"x"), "could not be reached"),
        (b"<html>gateway</html>", "not JSON"),
        (b'{"transcript": "x"}', "no `text`"),
        (json.dumps({"text": "m\ufffdc"}).encode(), "garbled"),
        (json.dumps({"text": "a\x00b"}).encode(), "garbled"),
        (json.dumps({"text": ["a"]}).encode(), "garbled"),
        (json.dumps({"text": "x" * 5000}).encode(), "garbled"),
    ],
)
def test_every_failure_is_unavailable_and_carries_no_key_and_no_body(answer, fragment):
    provider = OpenAITranscriber(stt(), environ={ENV: KEY}, opener=FakeOpener(answer))
    with pytest.raises(SpeechUnavailable) as caught:
        run(provider.transcribe(clip()))
    error = caught.value
    assert fragment in error.why and error.role == "stt"
    assert KEY not in error.render() and SPEECH not in error.render()
    assert error.how in error.why  # the trace records `why`: it says what to do too


def test_an_answer_larger_than_any_transcript_is_refused():
    provider = OpenAITranscriber(stt(), environ={ENV: KEY}, opener=FakeOpener(b" " * (2 << 20)))
    with pytest.raises(SpeechUnavailable, match="larger than"):
        run(provider.transcribe(clip()))


def test_synthesize_posts_json_and_reads_the_wav_answer():
    pcm = tone(250, 24000)
    opener = FakeOpener(wav_bytes(pcm, 24000))
    provider = OpenAISpeaker(tts(), environ={ENV: KEY}, opener=opener)
    speech = run(provider.synthesize("Cửa đã mở."))
    assert (speech.pcm, speech.sample_rate_hz, speech.channels) == (pcm, 24000, 1)
    ((request, _),) = opener.requests
    assert request.full_url == "https://api.openai.com/v1/audio/speech"
    assert request.get_header("Content-type") == "application/json"
    assert json.loads(request.data) == {
        "model": "tts-1",
        "voice": "alloy",
        "input": "Cửa đã mở.",
        "response_format": "wav",
    }


def test_a_streamed_wav_header_of_unknown_length_is_read_to_the_end():
    pcm = tone(100, 24000)
    data = bytearray(wav_bytes(pcm, 24000))
    data[4:8] = b"\xff\xff\xff\xff"  # RIFF size, as a streaming server writes it
    data[40:44] = b"\xff\xff\xff\xff"  # data size
    provider = OpenAISpeaker(tts(), environ={ENV: KEY}, opener=FakeOpener(bytes(data)))
    assert run(provider.synthesize("x")).pcm == pcm


@pytest.mark.parametrize(
    "answer, fragment",
    [
        (b"ID3\x03mp3 bytes", "not a PCM WAV"),
        (http_error(400, SPEECH.encode()), "refused the request"),
    ],
)
def test_a_tts_failure_is_unavailable(answer, fragment):
    provider = OpenAISpeaker(tts(), environ={ENV: KEY}, opener=FakeOpener(answer))
    with pytest.raises(SpeechUnavailable) as caught:
        run(provider.synthesize(SPEECH))
    assert fragment in caught.value.why and caught.value.role == "tts"
    assert SPEECH not in caught.value.render() and KEY not in caught.value.render()


def test_8_bit_audio_is_refused():
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(1)
        w.setframerate(8000)
        w.writeframes(b"\x80" * 800)
    provider = OpenAISpeaker(tts(), environ={ENV: KEY}, opener=FakeOpener(buffer.getvalue()))
    with pytest.raises(SpeechUnavailable, match="8-bit"):
        run(provider.synthesize("x"))


# --- a real HTTP stack, on 127.0.0.1 --------------------------------------------------------------


class Server:
    """A local HTTP server; `handle(handler)` answers each request."""

    def __init__(self, handle) -> None:
        self.seen: list[tuple[str, str | None]] = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                self.body = self.rfile.read(length)
                outer.seen.append((self.path, self.headers.get("Authorization")))
                handle(self)

            def log_message(self, *args):
                pass

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.httpd.daemon_threads = True
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.httpd.server_address[1]}/v1"

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=5)


def _answer(handler, status, body=b"", content_type="application/json", headers=()):
    handler.send_response(status)
    handler.send_header("Content-Type", content_type)
    for name, value in headers:
        handler.send_header(name, value)
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def test_a_round_trip_over_http_with_the_key_in_the_header_only():
    def handle(handler):
        if handler.path.endswith("/audio/transcriptions"):
            assert handler.headers["Content-Type"].startswith("multipart/form-data; boundary=")
            assert b'name="model"' in handler.body and b'name="file"' in handler.body
            _answer(handler, 200, json.dumps({"text": "mở cửa"}).encode())
        else:
            assert json.loads(handler.body)["voice"] == "alloy"
            _answer(handler, 200, wav_bytes(tone(100, 24000), 24000), "audio/wav")

    with Server(handle) as server:
        environ = {ENV: KEY}
        heard = run(OpenAITranscriber(stt(base_url=server.url), environ=environ).transcribe(clip()))
        spoken = run(OpenAISpeaker(tts(base_url=server.url), environ=environ).synthesize("Chào"))
    assert heard.text == "mở cửa" and spoken.sample_rate_hz == 24000
    assert server.seen == [
        ("/v1/audio/transcriptions", f"Bearer {KEY}"),
        ("/v1/audio/speech", f"Bearer {KEY}"),
    ]


@pytest.mark.parametrize("status", [302, 307])
def test_the_key_never_follows_a_redirect(status):
    with Server(lambda h: _answer(h, 200, b'{"text": "leaked"}')) as elsewhere:

        def handle(handler):
            _answer(
                handler, status, headers=[("Location", f"{elsewhere.url}/audio/transcriptions")]
            )

        with Server(handle) as server:
            provider = OpenAITranscriber(stt(base_url=server.url), environ={ENV: KEY})
            with pytest.raises(SpeechUnavailable, match="never follows a redirect"):
                run(provider.transcribe(clip()))
    assert elsewhere.seen == []  # the other host never heard from us, key or not


def test_a_server_slower_than_timeout_s_is_unavailable():
    release = threading.Event()

    def handle(handler):
        release.wait(5)
        _answer(handler, 200, b'{"text": "late"}')

    try:
        with Server(handle) as server:
            provider = OpenAITranscriber(
                stt(base_url=server.url, timeout_s=0.2), environ={ENV: KEY}
            )
            with pytest.raises(SpeechUnavailable, match="did not answer within 0.2 s"):
                run(provider.transcribe(clip()))
            release.set()
    finally:
        release.set()


# --- fakes, and what `pip install neuroedge` pulls in ---------------------------------------------


def test_the_fakes_are_deterministic_and_simulate_their_latency():
    fake = FakeSpeechToText({2: "tắt đèn"}, latency_ms=250, fail={3})
    assert fake.transcribe(clip(turn=1)).text == ""
    assert fake.transcribe(clip(turn=2)) == type(fake.transcribe(clip(turn=2)))("tắt đèn", 250.0)
    with pytest.raises(SpeechUnavailable) as caught:
        fake.transcribe(clip(turn=3))
    assert caught.value.latency_ms == 250
    speech = FakeTextToSpeech(ms_per_char=10).synthesize("abcd")
    assert len(speech.pcm) == 40 * 16 * 2 and speech.pcm == tone(40, 16000)


def test_clean_transcript_keeps_words_and_refuses_what_is_not():
    assert clean_transcript("  mở\tcửa\n", "w") == "mở cửa"
    assert clean_transcript("", "w") == ""
    with pytest.raises(SpeechUnavailable):
        clean_transcript(None, "w")


def test_the_speech_layer_imports_no_sdk(tmp_path):
    # FR-DX-02: `pip install neuroedge` gains no dependency — urllib and wave only.
    code = (
        "import sys, neuroedge.perception.providers, neuroedge.cli.voice\n"
        "bad = sorted({m.split('.')[0] for m in sys.modules} & "
        "{'httpx', 'requests', 'openai', 'sounddevice', 'numpy', 'litellm', 'aiohttp', 'urllib3'})\n"
        "print(bad)\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True, cwd=tmp_path
    )
    assert result.stdout.strip() == "[]"
