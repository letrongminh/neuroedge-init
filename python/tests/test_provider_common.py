"""
What every provider table and adapter shares (`models/providers/common.py`,
`neuroedge/net.py`) — tested once, against each of `[system_two]`, `[system_one]`,
`[stt]` and `[tts]`, so they cannot drift apart again (wave-2 review, 2026-09-26):

* one endpoint check — the same URL is accepted or refused by every table, with the
  one deliberate difference that `[system_one]` never talks clear text to another
  machine, key or not (a man in the middle would decide gate facts);
* a key is never repeated — whatever scalar field it is pasted into;
* one HTTP layer — no proxy, no redirect, a deadline the worker thread keeps.
"""

from __future__ import annotations

import asyncio
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from neuroedge import net
from neuroedge.engine.compiler import build
from neuroedge.errors import AgentManifestError, BuildFailed
from neuroedge.models.providers import (
    SystemOneApi,
    parse_system_one,
    parse_system_two,
)
from neuroedge.models.providers.common import KEY_LIKE, is_loopback
from neuroedge.perception.providers import AudioClip, OpenAITranscriber, parse_speech
from neuroedge.perception.providers.fake import tone

KEY = "sk-test-DO-NOT-LEAK-0123456789abcdef"
ENV = "NEUROEDGE_TEST_COMMON_KEY"

# Each table, its URL field, and a minimal good table that has a key.
TABLES = {
    "system_two": (
        parse_system_two,
        "api_base",
        {"model": "openai/gpt-4o-mini", "api_key_env": ENV},
    ),
    "system_one": (
        parse_system_one,
        "api_base",
        {"model": "typesafe/jev-1.13", "api_key_env": ENV, "criteria": ["wants_light"]},
    ),
    "stt": (
        lambda table: parse_speech("stt", table),
        "base_url",
        {"model": "whisper-1", "api_key_env": ENV},
    ),
    "tts": (
        lambda table: parse_speech("tts", table),
        "base_url",
        {"model": "tts-1", "voice": "alloy", "api_key_env": ENV},
    ),
}


def _refused(name: str, table: dict) -> AgentManifestError:
    parse = TABLES[name][0]
    with pytest.raises(AgentManifestError) as caught:
        parse(table)
    error = caught.value
    assert error.where and error.why and error.how  # FR-DX-04
    assert KEY not in error.render()
    return error


def _with_url(name: str, url, *, keyed: bool = True) -> dict:
    _, field, good = TABLES[name]
    table = {**good, field: url}
    if not keyed:
        table.pop("api_key_env")
    return table


# --- one endpoint check -----------------------------------------------------------------------

REFUSED_URLS = {
    "credentials": f"https://user:{KEY}@api.example.com/v1",
    "a-query": f"https://api.example.com/v1?key={KEY}",
    "a-fragment": "https://api.example.com/v1#x",
    "a-key-shaped-path": f"https://proxy.example/{KEY}/v1",
    "a-key-glued-in-a-path": f"https://proxy.example/v1/{KEY}x",
    "not-http": "ftp://x/v1",
    "an-unclosed-ipv6-bracket": "http://[::1",
    "a-port-that-is-not-one": "http://h:port/v1",
    "no-host": "https://",
    "no-host-but-a-path": "https:///v1",
    "a-space": "https://exa mple.com/v1",
    "a-line-break": "https://example.com/v1\r\nX-Evil: 1",
    "not-a-string": 8000,
}


@pytest.mark.parametrize("name", TABLES)
@pytest.mark.parametrize("url", list(REFUSED_URLS.values()), ids=list(REFUSED_URLS))
def test_every_table_refuses_the_same_bad_urls_without_repeating_them(name, url):
    error = _refused(name, _with_url(name, url))
    assert error.where.endswith(TABLES[name][1])
    # (`_refused` checks that the key in the URL is never repeated.)


CLEAR_TEXT_TO_ANOTHER_MACHINE = [
    "http://10.0.0.5/v1",
    "http://192.168.1.10:8000/v1",
    "http://127.0.0.1.evil.example/v1",  # a DNS name that starts with "127." is someone else
    "http://localhost.evil.example/v1",
]


@pytest.mark.parametrize("name", TABLES)
@pytest.mark.parametrize("url", CLEAR_TEXT_TO_ANOTHER_MACHINE)
def test_a_key_never_crosses_the_network_in_clear_text(name, url):
    assert "clear text" in _refused(name, _with_url(name, url)).why


@pytest.mark.parametrize("name", TABLES)
@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8000/v1",
        "http://127.0.0.2:8000/v1",
        "http://127.8.0.1:8000/v1",
        "http://[::1]:8000/v1",
        "http://LOCALHOST/v1",
        "http://localhost.:8000/v1",
        "https://api.example.com/v1",
    ],
)
def test_this_machine_and_tls_are_accepted_by_every_table(name, url):
    TABLES[name][0](_with_url(name, url))


def test_a_keyless_server_on_the_lan_is_fine_except_for_system_one():
    url = "http://192.168.1.10:8000/v1"
    for name in ("system_two", "stt", "tts"):
        TABLES[name][0](_with_url(name, url, keyed=False))
    assert "forge" in _refused("system_one", _with_url("system_one", url, keyed=False)).why


@pytest.mark.parametrize(
    ("host", "loopback"),
    [
        ("127.0.0.1", True),
        ("127.0.0.2", True),
        ("[::1]", True),
        ("[::ffff:127.0.0.1]", True),
        ("localhost", True),
        ("127.0.0.1.nip.io", False),
        ("10.0.0.1", False),
        ("[::2]", False),
    ],
)
def test_loopback_is_decided_by_the_ip_address_not_by_the_spelling(host, loopback):
    assert is_loopback(f"http://{host}:8000/v1") is loopback


@pytest.mark.parametrize(
    ("name", "extra", "where"),
    [
        (
            "system_one",
            '[system_one]\nmodel = "typesafe/jev-1.13"\napi_key_env = "E"\n'
            'criteria = ["wants_light"]\napi_base = "http://[::1"\n',
            "[system_one] api_base",
        ),
        (
            "system_two",
            '[system_two]\nmodel = "openai/gpt-4o-mini"\napi_key_env = "E"\n'
            'api_base = "http://[::1"\n',
            "[system_two] api_base",
        ),
        (
            "tts",
            '[tts]\nmodel = "tts-1"\nvoice = "alloy"\nbase_url = "http://[::1"\n',
            "[tts] base_url",
        ),
    ],
    ids=["system_one", "system_two", "tts"],
)
def test_a_malformed_url_is_a_three_part_build_problem_not_a_crash(copy_agent, name, extra, where):
    """`http://[::1` used to reach urlsplit unguarded: `neuroedge build` died with a ValueError."""
    manifest = copy_agent("home-voice", "\n" + extra)
    with pytest.raises(BuildFailed) as failed:
        build(manifest, target="sim", board_id="sim-default")
    problems = [p for p in failed.value.problems if p.where.endswith(where)]
    assert len(problems) == 1, [p.where for p in failed.value.problems]
    assert problems[0].why and problems[0].how


# --- a key is never repeated, whatever field it lands in ---------------------------------------

SCALAR_FIELDS = {
    "system_two": [
        "provider",
        "model",
        "api_key_env",
        "api_base",
        "timeout_s",
        "max_tokens",
        "temperature",
        "options",
    ],
    "system_one": [
        "provider",
        "model",
        "api_key_env",
        "api_base",
        "criteria",
        "threshold",
        "timeout_ms",
        "options",
    ],
    "stt": ["provider", "base_url", "model", "language", "timeout_s", "api_key_env", "options"],
    "tts": ["provider", "base_url", "model", "voice", "timeout_s", "api_key_env", "options"],
}
CASES = [(name, field) for name, fields in SCALAR_FIELDS.items() for field in fields]


@pytest.mark.parametrize(("name", "field"), CASES, ids=[f"{n}.{f}" for n, f in CASES])
def test_a_key_pasted_into_any_field_is_refused_and_never_repeated(name, field):
    error = _refused(name, {**TABLES[name][2], field: KEY})
    assert error.where.endswith(field), error.where


@pytest.mark.parametrize("name", TABLES)
def test_a_key_pasted_as_a_field_name_or_a_criterion_is_never_repeated(name):
    _refused(name, {**TABLES[name][2], KEY: 1})
    if name == "system_one":
        _refused(name, {**TABLES[name][2], "criteria": [KEY]})


@pytest.mark.parametrize("name", TABLES)
def test_a_model_with_a_line_break_is_refused(name):
    error = _refused(name, {**TABLES[name][2], "model": "whisper-1\r\nX-Evil: 1"})
    assert error.where.endswith("model")


@pytest.mark.parametrize(
    "value",
    ["sk-or-v1-0123456789abcdef", "gsk_0123456789abcdef", "x" * 40, "model/sk-ant-0123456789ab"],
)
def test_what_looks_like_a_key_is_found_anywhere_in_a_value(value):
    assert KEY_LIKE.search(value)


@pytest.mark.parametrize(
    "value",
    ["typesafe/jev-1.13", "anthropic/claude-sonnet-5", "whisper-large-v3", "mask-rcnn-resnet50"],
)
def test_model_ids_do_not_look_like_keys(value):
    assert not KEY_LIKE.search(value)


def test_the_speech_tables_say_their_endpoint_is_base_url():
    error = _refused("stt", {**TABLES["stt"][2], "api_base": "https://api.example.com/v1"})
    assert "`base_url`" in error.how


# --- one HTTP layer -------------------------------------------------------------------------------


class Recorder:
    """A local HTTP server that answers every POST with `answer(handler)` and records it."""

    def __init__(self, answer) -> None:
        self.seen: list[tuple[str, str | None]] = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                self.rfile.read(length)
                outer.seen.append((self.path, self.headers.get("Authorization")))
                answer(self)

            def log_message(self, *args):
                pass

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.httpd.daemon_threads = True
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.httpd.server_address[1]}"

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.httpd.shutdown()
        self.httpd.server_close()


def _json(handler, status: int, body: bytes) -> None:
    try:
        handler.send_response(status)
        handler.send_header("Content-Type", "application/json")
        handler.send_header("Content-Length", str(len(body)))
        handler.end_headers()
        handler.wfile.write(body)
    except (BrokenPipeError, ConnectionResetError):
        pass


NOUL = b'{"model": "typesafe/jev-1.13", "answers": {"wants_light": {"type": "noul", "noul": 0.97}}}'
HEARD = '{"text": "mở"}'.encode()


def test_no_request_ever_goes_through_a_proxy(proxies):
    """F3: with http_proxy set, a call to http://localhost went to the proxy, key and all."""
    with (
        Recorder(lambda h: _json(h, 502, b"{}")) as proxy,
        Recorder(lambda h: _json(h, 200, NOUL if "systemone" in h.path else HEARD)) as target,
    ):
        proxies(proxy.url)
        status, _ = net.post(
            f"{target.url}/v1/x",
            {"Authorization": f"Bearer {KEY}"},
            b"{}",
            timeout_s=2,
            deadline=time.monotonic() + 2,
            max_bytes=1024,
        )
        jev = SystemOneApi(
            parse_system_one({**TABLES["system_one"][2], "api_base": f"{target.url}/v1"}),
            environ={ENV: KEY},
        )
        fact = asyncio.run(
            jev.adjudicate(
                "wants_light", {"type": "bool", "instructions": "x"}, {"utterance": "bật đèn"}
            )
        )
        stt = OpenAITranscriber(
            parse_speech("stt", {**TABLES["stt"][2], "base_url": f"{target.url}/v1"}),
            environ={ENV: KEY},
        )
        heard = asyncio.run(stt.transcribe(AudioClip(tone(1000, 16000), 16000, 1)))
    assert status == 200 and fact.value is True and heard.text == "mở"
    assert proxy.seen == [], "the proxy never saw a request, nor the key"
    assert [path for path, _ in target.seen] == [
        "/v1/x",
        "/v1/systemone",
        "/v1/audio/transcriptions",
    ]
    assert {auth for _, auth in target.seen} == {f"Bearer {KEY}"}


def _trickle(stop: threading.Event):
    """Headers at once, then one byte every 50 ms for up to 5 s: each read is in time."""

    def answer(handler):
        try:
            handler.send_response(200)
            handler.send_header("Content-Type", "application/json")
            handler.send_header("Content-Length", "100")
            handler.end_headers()
            for _ in range(100):
                if stop.wait(0.05):
                    return
                handler.wfile.write(b" ")
                handler.wfile.flush()
        except OSError:
            return

    return answer


@pytest.fixture
def started_threads(monkeypatch):
    """Every thread started while the test runs, recorded as it starts."""
    started: list[threading.Thread] = []
    original = threading.Thread.start

    def start(self):
        started.append(self)
        return original(self)

    monkeypatch.setattr(threading.Thread, "start", start)
    return started


@pytest.mark.parametrize("who", ["systemone", "stt"])
def test_a_trickling_server_does_not_keep_the_worker_thread_past_the_deadline(who, started_threads):
    """
    The call returns at its deadline — and so must the thread doing the HTTP: a server
    that sends a byte every 50 ms passes every socket timeout, and only the per-chunk
    deadline in `net.post` stops the read (wave-2 review: the thread and socket leaked).
    """
    stop = threading.Event()
    try:
        with Recorder(_trickle(stop)) as server:
            started = time.monotonic()
            if who == "systemone":
                table = {**TABLES["system_one"][2], "api_base": f"{server.url}/v1"}
                jev = SystemOneApi(
                    parse_system_one({**table, "timeout_ms": 300}), environ={ENV: KEY}
                )
                answer = asyncio.run(
                    jev.adjudicate(
                        "wants_light",
                        {"type": "bool", "instructions": "x"},
                        {"utterance": "bật đèn"},
                    )
                )
                assert answer.reason == "timeout"
                name = "neuroedge-systemone"
            else:
                table = {**TABLES["stt"][2], "base_url": f"{server.url}/v1", "timeout_s": 0.3}
                stt = OpenAITranscriber(parse_speech("stt", table), environ={ENV: KEY})
                with pytest.raises(Exception, match="did not answer within 0.3 s"):
                    asyncio.run(stt.transcribe(AudioClip(tone(1000, 16000), 16000, 1)))
                name = "neuroedge-stt"
            assert time.monotonic() - started < 1.5
            workers = [thread for thread in started_threads if thread.name == name]
            assert workers, "the call ran in a named worker thread"
            for worker in workers:
                worker.join(timeout=1.5)
                assert not worker.is_alive(), "the worker outlived its deadline"
            assert time.monotonic() - started < 3, "the server was still trickling"
    finally:
        stop.set()


def test_post_caps_the_answer_and_starts_nothing_past_its_deadline():
    with Recorder(lambda h: _json(h, 200, b"x" * 5000)) as big, pytest.raises(net.TooLarge):
        net.post(
            f"{big.url}/v1", {}, b"", timeout_s=2, deadline=time.monotonic() + 2, max_bytes=1000
        )
    with pytest.raises(net.DeadlineExceeded):
        net.post(
            "http://127.0.0.1:9/v1",
            {},
            b"",
            timeout_s=1,
            deadline=time.monotonic() - 1,
            max_bytes=10,
        )


@pytest.mark.parametrize(
    ("value", "expected"),
    [(None, None), ("", None), ("   \n", None), (f"{KEY}\n", KEY), (f"  {KEY}  ", KEY)],
)
def test_a_key_is_read_stripped(value, expected):
    environ = {} if value is None else {ENV: value}
    assert net.env_key(environ, ENV) == expected


@pytest.mark.parametrize("value", [f"{KEY}\r\nX-Evil: 1", f"{KEY[:8]} {KEY[8:]}", f"{KEY}\x7f"])
def test_a_key_with_control_characters_or_spaces_inside_is_unusable_and_never_repeated(value):
    with pytest.raises(net.KeyUnusable) as caught:
        net.env_key({ENV: value}, ENV)
    assert KEY[:8] not in str(caught.value)


def test_a_speech_key_with_control_characters_is_not_sent():
    from neuroedge.perception.providers import SpeechUnavailable

    stt = OpenAITranscriber(parse_speech("stt", TABLES["stt"][2]), environ={ENV: f"{KEY}\r\nX: 1"})
    with pytest.raises(SpeechUnavailable) as caught:
        asyncio.run(stt.transcribe(AudioClip(tone(1000, 16000), 16000, 1)))
    assert caught.value.called is False and KEY not in caught.value.render()
