"""
TSK-S2-11 — real System 2 providers: LiteLLM (extra `neuroedge[cloud]`) and
custom adapters, configured by `[system_two]` in agent.toml (Q-10, Q-12).

LiteLLM is ~120 MB and not in `dev`, so these tests never import it: a fake
`litellm` module is put in `sys.modules`, returning OpenAI-shaped objects the
way LiteLLM's `ModelResponse` does. The real library is exercised by
`scripts/cloud_smoke.py` in the CI job `cloud-extra`.
"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import subprocess
import sys
import types
from types import SimpleNamespace as NS

import pytest
from typer.testing import CliRunner

from neuroedge.cli.main import app
from neuroedge.engine.compiler import build
from neuroedge.errors import AgentManifestError, BuildFailed, PerceptionUnavailableError
from neuroedge.models import SystemTwo
from neuroedge.models.providers import (
    LiteLLMProvider,
    SystemTwoConfig,
    from_response,
    parse_system_two,
    to_messages,
)
from neuroedge.sim import SimSession
from neuroedge.trace import validate_trace

KEY = "sk-test-DO-NOT-LEAK-0123456789abcdef"
ENV = "NEUROEDGE_TEST_LLM_KEY"
SYSTEM_TWO = f"""
[system_two]
provider    = "litellm"
model       = "anthropic/claude-sonnet-5"
api_key_env = "{ENV}"
"""


# --- a fake litellm ---------------------------------------------------------------------------


def completion(text=None, tool_calls=(), prompt_tokens=42, completion_tokens=7):
    """What LiteLLM's `ModelResponse` looks like to the adapter (attribute access)."""
    calls = [
        NS(id=f"toolu_{i}", type="function", function=NS(name=name, arguments=arguments))
        for i, (name, arguments) in enumerate(tool_calls, 1)
    ]
    message = NS(role="assistant", content=text, tool_calls=calls or None)
    return NS(
        choices=[NS(index=0, message=message, finish_reason="stop")],
        usage=NS(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens),
    )


class FakeLiteLLM(types.ModuleType):
    def __init__(self, *replies):
        super().__init__("litellm")
        self.replies = list(replies)
        self.calls: list[dict] = []
        self.suppress_debug_info = False

    async def acompletion(self, **request):
        self.calls.append(request)
        reply = self.replies.pop(0) if self.replies else completion("…")
        if callable(reply):
            reply = reply(request)
        if hasattr(reply, "__await__"):
            reply = await reply
        if isinstance(reply, BaseException):
            raise reply
        return reply

    def completion_cost(self, completion_response):
        return 0.000123


class AuthenticationError(Exception):
    """Named like LiteLLM's; its message echoes the key, as some provider errors do."""


class Timeout(Exception):
    """Named like `litellm.Timeout`."""


@pytest.fixture
def fake(monkeypatch):
    """Install a fake `litellm`; `fake(*replies)` sets what it answers."""
    module = FakeLiteLLM()
    monkeypatch.setitem(sys.modules, "litellm", module)
    monkeypatch.setenv(ENV, KEY)

    def configure(*replies):
        module.replies[:] = list(replies)
        return module

    return configure


@pytest.fixture
def fresh_actions():
    """A copied agent defines the same @action names at another path: isolate the registry."""
    from neuroedge.actions import spec

    saved = dict(spec.REGISTRY)
    spec.REGISTRY.clear()
    yield
    spec.REGISTRY.clear()
    spec.REGISTRY.update(saved)


@pytest.fixture
def online(tmp_path, root, fresh_actions):
    """A copy of home-voice with `[system_two]` appended; `online(extra)` appends more."""

    def make(system_two: str = SYSTEM_TWO, *, gates: dict[str, str] | None = None):
        target = tmp_path / "home-voice"
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(root / "fixtures" / "agents" / "home-voice", target)
        manifest = target / "agent.toml"
        manifest.write_text(manifest.read_text("utf-8") + system_two, encoding="utf-8")
        for name, text in (gates or {}).items():
            (target / "gates" / name).write_text(text, encoding="utf-8")
        return manifest

    return make


def trace_text(session) -> str:
    trace = session.trace()  # validated against trace.v1
    return json.dumps(trace, ensure_ascii=False)


# --- state → OpenAI chat messages -------------------------------------------------------------


def test_a_multi_round_react_state_becomes_exact_openai_messages():
    state = {
        "task": "converse",
        "utterance": "trời tối quá",
        "instructions": "Gọi tool khi cần.",
        "tools": [{"type": "function", "function": {"name": "light_on"}}],
        "messages": [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [{"id": "toolu_1", "name": "light_on", "arguments": {}}],
            },
            {
                "role": "tool",
                "tool_call_id": "toolu_1",
                "name": "light_on",
                "content": {"tool": "light_on", "status": "BLOCK", "reason": "không được"},
            },
            {
                "role": "assistant",
                "content": "Thử lại",
                "tool_calls": [{"id": "ref_2", "name": "news__headlines", "arguments": {"n": 3}}],
            },
            {
                "role": "tool",
                "tool_call_id": "ref_2",
                "name": "news__headlines",
                "content": {"status": "OK", "content": "Hà Nội se lạnh"},
            },
        ],
    }
    assert to_messages("respond", None, state) == [
        {"role": "system", "content": "Gọi tool khi cần."},
        {"role": "user", "content": "trời tối quá"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "toolu_1",
                    "type": "function",
                    "function": {"name": "light_on", "arguments": "{}"},
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "toolu_1",
            "content": '{"tool": "light_on", "status": "BLOCK", "reason": "không được"}',
        },
        {
            "role": "assistant",
            "content": "Thử lại",
            "tool_calls": [
                {
                    "id": "ref_2",
                    "type": "function",
                    "function": {"name": "news__headlines", "arguments": '{"n": 3}'},
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "ref_2",
            "content": '{"status": "OK", "content": "Hà Nội se lạnh"}',
        },
    ]


def test_the_knowledge_task_puts_the_retrieved_context_in_the_system_message():
    state = {
        "task": "knowledge",
        "utterance": "mật khẩu wifi",
        "instructions": "Chỉ dựa trên context.",
        "context": [{"id": "wifi", "question": "mật khẩu wifi", "answer": "NhaMinh"}],
    }
    system, user = to_messages("reply", None, state)
    assert system["role"] == "system"
    assert system["content"].startswith("Chỉ dựa trên context.")
    assert '"answer": "NhaMinh"' in system["content"]
    assert user == {"role": "user", "content": "mật khẩu wifi"}


def test_a_response_is_normalised_and_bad_arguments_are_passed_on_unguessed():
    response = completion(
        "ok",
        tool_calls=[("light_on", '{"level": 2}'), ("light_off", '{"oops'), ("x", "[1, 2]")],
    )
    assert from_response(response) == {
        "text": "ok",
        "tool_calls": [
            {"id": "toolu_1", "name": "light_on", "arguments": {"level": 2}},
            {"id": "toolu_2", "name": "light_off", "arguments": '{"oops'},
            {"id": "toolu_3", "name": "x", "arguments": "[1, 2]"},
        ],
    }
    # Plain JSON (an OpenAI-compatible server through a custom adapter) reads the same.
    raw = {"choices": [{"message": {"content": "hi", "tool_calls": None}}]}
    assert from_response(raw) == {"text": "hi", "tool_calls": []}
    for broken in ({}, {"choices": []}, {"choices": [{}]}, NS(choices=None)):
        with pytest.raises(PerceptionUnavailableError):
            from_response(broken)


# --- a tool-call round trip on home-voice -----------------------------------------------------


async def test_the_model_turns_the_light_on_through_the_gate_and_its_answer_is_spoken(fake, online):
    litellm = fake(completion(None, [("light_on", "{}")]), completion("Đã bật đèn hiên."))
    session = SimSession.load(online())
    turn = await session.handle("trời tối quá")

    (result,) = turn.tool_results
    assert (result.call.source, result.status) == ("system_two", "ALLOW")
    assert session.hal.pin("porch_light").commands == [("on", 0)]
    assert (turn.reply, turn.reply_source) == ("Đã bật đèn hiên.", "system_two")

    first, second = litellm.calls
    assert first["model"] == "anthropic/claude-sonnet-5"
    assert first["api_key"] == KEY
    assert first["timeout"] == 20.0
    assert {t["function"]["name"] for t in first["tools"]} >= {"light_on", "light_off"}
    assert [m["role"] for m in first["messages"]] == ["system", "user"]
    assistant, tool = second["messages"][2:]
    assert assistant["tool_calls"] == [
        {"id": "toolu_1", "type": "function", "function": {"name": "light_on", "arguments": "{}"}}
    ]
    assert tool["tool_call_id"] == "toolu_1"
    assert json.loads(tool["content"])["status"] == "ALLOW"


async def test_a_blocked_call_is_fed_back_and_the_models_explanation_is_spoken(fake, online, root):
    # light_on refuses System 2 here, with `deny`: the model is told why and answers.
    gate = (root / "fixtures/agents/home-voice/gates/light_on@1.0.0.yaml").read_text("utf-8")
    gate = gate.replace(
        "call_source: { in: [local_grammar, system_one, system_two, mcp] }",
        "call_source: { in: [local_grammar] }",
    )

    def explain(request):
        told = json.loads(request["messages"][-1]["content"])
        assert (told["status"], told["failed_criterion"]) == ("BLOCK", "call_source")
        return completion("Mình không được phép bật đèn — bạn nói 'bật đèn' nhé.")

    litellm = fake(completion(None, [("light_on", "{}")]), explain)
    session = SimSession.load(online(gates={"light_on@1.0.0.yaml": gate}))
    turn = await session.handle("trời tối quá")

    assert [r.status for r in turn.tool_results] == ["BLOCK"]
    assert session.hal.pin("porch_light").commands == []
    assert turn.reply_source == "system_two"
    assert turn.reply.startswith("Mình không được phép")
    assert len(litellm.calls) == 2


async def test_an_ask_block_stops_the_loop_and_the_device_asks(fake, online):
    litellm = fake(completion(None, [("light_off", "{}")]), completion("never said"))
    session = SimSession.load(online())
    session.set_sensor("motion", True)
    turn = await session.handle("phòng chói quá, cho tối lại giùm")
    assert turn.reply_source == "gate_ask"
    assert session.hal.pin("porch_light").commands == []
    assert len(litellm.calls) == 1  # the model may not answer for the person (Q-26)


async def test_malformed_json_arguments_are_rejected_and_no_pin_moves(fake, online):
    def react(request):
        told = json.loads(request["messages"][-1]["content"])
        assert told["status"] == "REJECTED"
        return completion("Xin lỗi, mình gọi sai.")

    fake(completion(None, [("light_on", '{"oops')]), react)
    session = SimSession.load(online())
    turn = await session.handle("trời tối quá")

    (result,) = turn.tool_results
    assert result.status == "REJECTED"
    assert "__unparseable__" in result.problems[0]
    assert session.hal.pin("porch_light").commands == []
    assert turn.reply == "Xin lỗi, mình gọi sai."


async def test_the_knowledge_task_sends_the_retrieved_context(fake, online):
    litellm = fake(completion("Wifi là NhaMinh nhé."))
    session = SimSession.load(online())
    turn = await session.handle("mật khẩu wifi")
    assert (turn.reply, turn.reply_source) == ("Wifi là NhaMinh nhé.", "knowledge_rag")
    (request,) = litellm.calls
    assert "tools" not in request  # a reply task offers no tools
    assert "NhaMinh" in request["messages"][0]["content"]


# --- FR-MDL-06: one event per model call, no prompt, no key -----------------------------------


async def test_each_model_call_is_traced_without_prompt_or_key(fake, online):
    fake(completion(None, [("light_on", "{}")]), completion("Đã bật đèn."))
    session = SimSession.load(online())
    await session.handle("trời tối quá")

    events = session.events.of_type("system_two_call")
    assert len(events) == 2
    for event in events:
        assert set(event) == {
            "provider",
            "model",
            "task",
            "latency_ms",
            "status",
            "prompt_tokens",
            "completion_tokens",
            "cost_usd",
        }
        assert (event["provider"], event["model"], event["task"]) == (
            "litellm",
            "anthropic/claude-sonnet-5",
            "converse",
        )
        assert (event["prompt_tokens"], event["completion_tokens"]) == (42, 7)
        assert event["status"] == "ok"
    text = trace_text(session)
    assert KEY not in text
    assert "Gọi tool khi" not in text  # the instructions (prompt) are not traced


def test_an_online_session_replays_to_the_same_decisions_without_model_or_key(
    fake, online, monkeypatch
):
    from neuroedge.testing.player import replay_sync

    litellm = fake(completion(None, [("light_on", "{}")]), completion("Đã bật đèn."))
    manifest = online()
    session = SimSession.load(manifest)
    asyncio.run(session.handle("trời tối quá"))
    trace = session.trace()
    calls = len(litellm.calls)

    monkeypatch.delenv(ENV)  # replay needs neither the model nor its key
    result = replay_sync(trace, agent=manifest)
    assert result.divergences == []
    assert [a.blocked for a in result.actions] == [False]
    assert len(litellm.calls) == calls


# --- failures: fail-safe, explicit, and the key never leaks -----------------------------------


async def test_without_the_cloud_extra_the_agent_says_its_offline_line(monkeypatch, online):
    monkeypatch.setitem(sys.modules, "litellm", None)  # `import litellm` raises ImportError
    monkeypatch.setenv(ENV, KEY)
    session = SimSession.load(online())
    turn = await session.handle("đọc tin tức")
    assert turn.reply_source == "offline"
    (event,) = session.events.of_type("system_two_unavailable")
    assert "pip install 'neuroedge[cloud]'" in event["reason"]
    assert session.events.of_type("system_two_call") == []  # nothing was called


async def test_without_the_key_nothing_is_sent(fake, online, monkeypatch):
    litellm = fake(completion("never"))
    monkeypatch.setenv(ENV, "  ")
    session = SimSession.load(online())
    turn = await session.handle("đọc tin tức")
    assert turn.reply == "Hiện không có mạng, mình chưa lấy được tin tức."
    assert litellm.calls == []
    (event,) = session.events.of_type("system_two_unavailable")
    assert f"set {ENV}" in event["reason"]
    assert session.events.of_type("system_two_call") == []


async def test_a_provider_error_never_carries_the_key(fake, online, caplog, capsys):
    caplog.set_level(logging.DEBUG)
    fake(AuthenticationError(f"invalid x-api-key: {KEY}"))
    session = SimSession.load(online())
    turn = await session.handle("đọc tin tức")
    assert turn.reply_source == "offline"
    (event,) = session.events.of_type("system_two_unavailable")
    assert "rejected the API key" in event["reason"]
    assert "***" in event["reason"]
    (call,) = session.events.of_type("system_two_call")
    assert (call["status"], call["error"]) == ("error", "ProviderUnavailable")
    out = capsys.readouterr()
    for text in (trace_text(session), caplog.text, out.out, out.err):
        assert KEY not in text

    fake(AuthenticationError(f"invalid x-api-key: {KEY}"))
    with pytest.raises(PerceptionUnavailableError) as raised:
        await session.slow.provider("respond", None, {"task": "converse", "utterance": "x"})
    assert KEY not in str(raised.value)
    # The original exception (it may hold the request) is not chained to the error.
    assert raised.value.__cause__ is None and raised.value.__suppress_context__


@pytest.mark.parametrize("hang", [False, True], ids=["provider-timeout", "no-answer"])
async def test_a_timeout_is_unavailable_with_what_to_do(fake, online, hang):
    async def never(request):
        await asyncio.sleep(5)

    fake(never if hang else Timeout("Request timed out"))
    session = SimSession.load(online(SYSTEM_TWO + "timeout_s = 0.05\n"))
    turn = await session.handle("đọc tin tức")
    assert turn.reply_source == "offline"
    (event,) = session.events.of_type("system_two_unavailable")
    assert "in time" in event["reason"] or "within 0.05 s" in event["reason"]
    (call,) = session.events.of_type("system_two_call")
    assert call["status"] == "error"


async def test_a_reply_task_with_no_text_is_unavailable(fake):
    fake(completion(None))
    config = SystemTwoConfig(model="openai/gpt-4o-mini", api_key_env=ENV)
    slow = SystemTwo("openai/gpt-4o-mini", provider=LiteLLMProvider(config))
    with pytest.raises(PerceptionUnavailableError) as raised:
        await slow.reply({"task": "knowledge", "utterance": "?"})
    assert "no text" in raised.value.why


def test_no_system_two_table_leaves_the_agent_offline(root):
    session = SimSession.load(root / "fixtures" / "agents" / "home-voice" / "agent.toml")
    assert not session.slow.available


def test_importing_the_providers_does_not_import_litellm():
    code = "import sys, neuroedge.models.providers, neuroedge.sim; print('litellm' in sys.modules)"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "False"


# --- [system_two] is checked by the build -----------------------------------------------------


def test_an_api_key_in_agent_toml_fails_the_build_without_repeating_it(online):
    manifest = online(SYSTEM_TWO + f'api_key = "{KEY}"\n')
    with pytest.raises(BuildFailed) as failed:
        build(manifest, target="sim", board_id="sim-default")
    (problem,) = failed.value.problems
    assert isinstance(problem, AgentManifestError)
    assert problem.where.endswith("[system_two] api_key")
    assert "never" in problem.why
    assert "api_key_env" in problem.how
    assert KEY not in failed.value.render() + "".join(p.render() for p in failed.value.problems)

    result = CliRunner().invoke(app, ["build", "--agent", str(manifest), "--target", "sim"])
    assert result.exit_code != 0
    assert "api_key" in result.output
    assert KEY not in result.output


@pytest.mark.parametrize(
    ("table", "where", "complaint"),
    [
        ({"model": "x", "api_key_env": ENV, "temp": 1}, "temp", "not fields"),
        ({"provider": "openai", "model": "x", "api_key_env": ENV}, "provider", "provider must"),
        ({"api_key_env": ENV}, "model", "needs a string `model`"),
        ({"model": "x"}, "api_key_env", "does not say where"),
        ({"model": "x", "api_key_env": ENV, "timeout_s": 0}, "timeout_s", "timeout_s must"),
        ({"model": "x", "api_key_env": ENV, "max_tokens": -1}, "max_tokens", "positive"),
        ({"model": "x", "api_key_env": ENV, "temperature": 3}, "temperature", "0 to 2"),
        ({"model": "x", "api_key_env": ENV, "api_base": "ftp://h"}, "api_base", "http"),
        ({"model": "x", "api_key_env": ENV, "options": {"a": 1}}, "options", "custom adapter"),
        ({"provider": "python:m:f", "options": {"token": "t"}}, "options.token", "never"),
    ],
)
def test_a_bad_system_two_table_is_a_three_part_error(table, where, complaint):
    with pytest.raises(AgentManifestError) as raised:
        parse_system_two(table)
    assert raised.value.where.endswith(where)
    assert complaint in raised.value.why
    assert raised.value.how


def test_a_key_pasted_as_the_variable_name_is_refused_and_not_repeated():
    with pytest.raises(AgentManifestError) as raised:
        parse_system_two({"model": "anthropic/claude-sonnet-5", "api_key_env": KEY})
    assert KEY not in raised.value.render()
    assert "ANTHROPIC_API_KEY" in raised.value.how


def test_a_keyless_local_server_needs_only_api_base():
    config = parse_system_two({"model": "ollama/llama3", "api_base": "http://localhost:11434"})
    assert (config.api_key_env, config.timeout_s) == (None, 20.0)


# --- a custom adapter (FR-MDL-08) -------------------------------------------------------------

ADAPTER = '''
"""An adapter written outside NeuroEdge: it imports nothing from it."""


def make_provider(config):
    def provider(task, name, state):
        return f"{config.options['greeting']} ({state['task']}, {config.model})"

    provider.name = "echo"
    return provider
'''


async def test_a_custom_adapter_named_by_dotted_path_runs_without_touching_the_core(online):
    manifest = online(
        '\n[system_two]\nprovider = "python:my_llm.echo:make_provider"\nmodel = "local-echo"\n'
        '[system_two.options]\ngreeting = "Xin chào"\n'
    )
    package = manifest.parent / "my_llm"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "echo.py").write_text(ADAPTER, encoding="utf-8")
    try:
        session = SimSession.load(manifest)
        turn = await session.handle("mật khẩu wifi")
    finally:
        for name in ("my_llm", "my_llm.echo"):
            sys.modules.pop(name, None)
    assert (turn.reply, turn.reply_source) == ("Xin chào (knowledge, local-echo)", "knowledge_rag")
    (call,) = session.events.of_type("system_two_call")
    assert (call["provider"], call["model"], call["status"]) == ("echo", "local-echo", "ok")
    validate_trace(session.trace())


def test_an_adapter_whose_factory_fails_is_a_three_part_error_at_load(online):
    manifest = online('\n[system_two]\nprovider = "python:bad_llm:make"\n')
    (manifest.parent / "bad_llm.py").write_text(
        "def make(config):\n    raise RuntimeError('no endpoint')\n", encoding="utf-8"
    )
    try:
        with pytest.raises(AgentManifestError) as raised:
            SimSession.load(manifest)
    finally:
        sys.modules.pop("bad_llm", None)
    assert "raised RuntimeError: no endpoint" in raised.value.why


def test_an_adapter_that_cannot_be_imported_fails_the_build(online):
    manifest = online('\n[system_two]\nprovider = "python:no_such_adapter:make"\n')
    with pytest.raises(BuildFailed) as failed:
        build(manifest, target="sim", board_id="sim-default")
    (problem,) = failed.value.problems
    assert "cannot import" in problem.why
    assert problem.where.endswith("[system_two] provider")


# --- the Q-11 licence policy check used by CI (`scripts/check_licences.py`) --------------------


@pytest.fixture(scope="module")
def licences(root):
    import importlib.util

    path = root / "scripts" / "check_licences.py"
    spec = importlib.util.spec_from_file_location("check_licences", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "licence",
    [
        "MIT",
        "MIT License\n\nCopyright (c) 2022 OpenAI\n\nPermission is hereby granted",
        "Apache-2.0 AND CNRI-Python",
        "Apache-2.0 OR BSD-2-Clause",
        "Apache Software License; BSD License",
        "ISC License (ISCL)",
        "Mozilla Public License 2.0 (MPL 2.0)",
        "MPL-2.0 AND MIT",
        "(MIT OR Apache-2.0) AND BSD-3-Clause",
        "Python Software Foundation License",
    ],
)
def test_the_licence_policy_allows_the_permissive_families(licences, licence):
    assert licences.offenders([{"Name": "p", "Version": "1", "License": licence}]) == []


@pytest.mark.parametrize(
    "licence",
    [
        "GNU General Public License v3 (GPLv3)",
        "LGPL-2.1-or-later",
        "AGPL-3.0",
        "SSPL-1.0",
        "BUSL-1.1",
        "UNKNOWN",
        "",
        "Proprietary Limited License",  # "Limited" contains "mit": a substring test passes it
        "MIT AND GPL-3.0-only",
        "Commercial",
    ],
)
def test_the_licence_policy_refuses_everything_else(licences, licence):
    assert licences.offenders([{"Name": "p", "Version": "1", "License": licence}])


def test_the_product_itself_is_not_held_to_the_dependency_policy(licences):
    """Q-45: neuroedge carries its own licence; Q-11 governs what it depends on."""
    own = {
        "Name": "neuroedge",
        "Version": "0.1.0",
        "License": "PolyForm-Noncommercial-1.0.0 AND Apache-2.0",
    }
    assert licences.offenders([own]) == []
    dependency = {**own, "Name": "some-dependency"}
    assert licences.offenders([dependency]), "a noncommercial dependency must still fail"


def test_the_script_allows_exactly_what_q11_names(licences, root):
    """One fact, one place: every family the script lets through is named in PRD Q-11."""
    q11 = next(
        line
        for line in (root / "neuroedge-prd.md").read_text(encoding="utf-8").splitlines()
        if line.startswith("| **Q-11** |")
    )
    policy = q11[q11.index("Chính sách phụ thuộc bắc cầu") :]
    for family in ("MIT", "BSD", "Apache-2.0", "ISC", "PSF", "CNRI-Python", "MPL-2.0"):
        assert family in policy, family
    for family in ("MIT", "BSD-3-Clause", "Apache-2.0", "ISC", "PSF-2.0", "CNRI-Python", "MPL-2.0"):
        assert licences.ALLOWED_RE.match(family), family


# --- the CLI says which model answers, never the key -------------------------------------------


def test_the_repl_banner_names_the_model_and_the_key_variable_not_the_key(fake, online):
    from rich.console import Console

    from neuroedge.cli.run import banner

    console = Console(record=True, width=200)
    banner(SimSession.load(online()), console)
    text = console.export_text()
    assert f"system 2: litellm anthropic/claude-sonnet-5 (key from ${ENV}" in text
    assert "offline, typed text" not in text
    assert KEY not in text


def test_run_without_the_key_says_the_offline_line(online, monkeypatch):
    monkeypatch.delenv(ENV, raising=False)
    result = CliRunner().invoke(app, ["run", "--agent", str(online()), "-c", "đọc tin tức"])
    assert result.exit_code == 0, result.output
    assert "Hiện không có mạng" in result.output
