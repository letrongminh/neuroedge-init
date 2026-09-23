"""
The home-voice sample: one voice assistant, three kinds of behaviour.

* knowledge base — RAG through System 2; offline, the local answer (speech, L3);
* news — System 2 only; offline, it says so and invents nothing;
* lights — physical, gated: never off while the motion sensor sees someone.
"""

from __future__ import annotations

import asyncio

import pytest
from typer.testing import CliRunner

from neuroedge.cli.main import app
from neuroedge.errors import BuildFailed, PerceptionUnavailableError
from neuroedge.models import CommandGrammar, SystemTwo
from neuroedge.models.knowledge import KnowledgeBase
from neuroedge.sim import SimSession
from neuroedge.testing import TracePlayer, assert_matches_golden
from neuroedge.testing.recorder import TraceRecorder

runner = CliRunner()


@pytest.fixture(scope="module")
def agent(root):
    return root / "fixtures" / "agents" / "home-voice" / "agent.toml"


def session_for(agent, *, provider=None, motion=False, events=None):
    slow = SystemTwo("test-llm", provider=provider) if provider else None
    session = SimSession.load(agent, slow=slow, events=events)
    session.set_sensor("motion", motion)
    return session


def say(session, *lines):
    return [asyncio.run(session.handle(line)) for line in lines]


# --- lights: physical, gated -----------------------------------------------------------


def test_light_on_is_allowed_and_drives_the_pin(agent):
    session = session_for(agent)
    (turn,) = say(session, "bật đèn")
    assert turn.allowed
    assert session.hal.pin("porch_light").commands == [("on", 0)]


def test_light_off_is_refused_while_someone_is_in_the_room(agent):
    session = session_for(agent, motion=True)
    _, off = say(session, "bật đèn", "tắt đèn")
    assert off.result.blocked
    assert off.result.gate.failed_criterion == "room_empty"
    assert off.result.gate.on_block_action == "ask"
    # The assistant asks the question aloud; the light stays on.
    assert off.reply_source == "gate_ask"
    # …then says how a person answers (RFC-0006: the gate lets them confirm room_empty).
    assert session.hal.spoken[-2:] == [
        off.result.gate.message,
        "Nói “có” để xác nhận, “không” để huỷ.",
    ]
    assert off.confirmation is not None
    assert session.hal.pin("porch_light").commands == [("on", 0)]


def test_light_off_is_allowed_once_the_room_is_empty(agent):
    session = session_for(agent)
    say(session, "bật đèn", "tắt đèn")
    assert session.hal.pin("porch_light").commands == [("on", 0), ("off", 0)]


# --- knowledge base: RAG, local offline ---------------------------------------------------


def test_offline_the_local_answer_is_said(agent):
    session = session_for(agent)
    (turn,) = say(session, "wifi nhà mình là gì")
    assert turn.reply_source == "knowledge_local"
    assert turn.reply == "Mạng wifi là NhaMinh, mật khẩu dán ở mặt dưới router."
    assert session.events.of_type("knowledge_retrieved") == [
        {"entries": [{"id": "wifi", "score": 1.0}]}
    ]
    assert session.events.of_type("system_two_unavailable")[0]["task"] == "knowledge"
    assert session.hal.pin("porch_light").never_pulsed()


def test_online_system_two_answers_from_the_retrieved_context(agent):
    seen = {}

    def provider(task, name, state):
        seen.update(state)
        return "Dạ, wifi nhà mình là NhaMinh, mật khẩu ở dưới router ạ."

    session = session_for(agent, provider=provider)
    (turn,) = say(session, "mật khẩu wifi")
    assert turn.reply_source == "knowledge_rag"
    assert turn.reply == "Dạ, wifi nhà mình là NhaMinh, mật khẩu ở dưới router ạ."
    assert seen["task"] == "knowledge"
    assert [c["id"] for c in seen["context"]] == ["wifi"]
    assert "chỉ dựa trên context" in seen["instructions"]


def test_a_failing_provider_falls_back_to_the_local_answer(agent):
    def provider(task, name, state):
        raise ConnectionError("network unreachable")

    (turn,) = say(session_for(agent, provider=provider), "mấy giờ đổ rác")
    assert turn.reply_source == "knowledge_local"
    assert "19 giờ" in turn.reply


def test_retrieval_is_local_ranked_and_thresholded(root):
    kb = KnowledgeBase.load(root / "fixtures" / "agents" / "home-voice" / "knowledge.toml")
    (best, score), *_ = kb.retrieve("reset máy lọc nước")
    assert (best.id, score) == ("loc-nuoc", 1.0)
    assert kb.retrieve("thời tiết sao hỏa thế nào") == []
    assert len(kb.retrieve("wifi", k=1)) <= 1


def test_a_malformed_knowledge_base_fails_the_build(tmp_path, root):
    source = root / "fixtures" / "agents" / "home-voice"
    for name in ("agent.toml", "commands.toml"):
        (tmp_path / name).write_text((source / name).read_text("utf-8"), encoding="utf-8")
    (tmp_path / "gates").mkdir()
    for gate in (source / "gates").iterdir():
        (tmp_path / "gates" / gate.name).write_text(gate.read_text("utf-8"), encoding="utf-8")
    (tmp_path / "knowledge.toml").write_text(
        '[knowledge]\nversion = 1\n\n[[entry]]\nquestions = []\nanswer = "x"\n', encoding="utf-8"
    )
    with pytest.raises(BuildFailed) as failed:
        SimSession.load(tmp_path / "agent.toml")
    assert any("questions" in p.why for p in failed.value.problems)


# --- news: System 2 only -----------------------------------------------------------------


def test_news_offline_says_so_and_invents_nothing(agent):
    session = session_for(agent)
    (turn,) = say(session, "đọc tin tức")
    assert turn.reply_source == "offline"
    assert turn.reply == "Hiện không có mạng, mình chưa lấy được tin tức."
    assert session.events.of_type("system_two_unavailable") == [
        {"task": "news", "reason": "no provider or fallback produced an answer"}
    ]


def test_news_online_comes_from_system_two(agent):
    (turn,) = say(
        session_for(agent, provider=lambda task, name, state: "Tin sáng nay: ..."), "đọc tin tức"
    )
    assert (turn.reply_source, turn.reply) == ("system_two", "Tin sáng nay: ...")


# --- grammar fields ------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("command", "complaint"),
    [
        ('action = "a"\nsay = "x"', "does one thing"),
        ('offline_say = "x"', "there is no `ask`"),
        ('say = ""', "non-empty text"),
    ],
)
def test_grammar_rejects_ambiguous_speech_fields(command, complaint):
    document = f'[grammar]\nversion = 1\n\n[[command]]\nintent = "i"\npatterns = ["p"]\n{command}\n'
    import tomllib

    with pytest.raises(PerceptionUnavailableError, match=complaint):
        CommandGrammar.from_document(tomllib.loads(document))


# --- trace, replay, CLI --------------------------------------------------------------------


async def test_a_recorded_session_replays_to_the_same_decisions(agent):
    recorder = TraceRecorder()
    session = session_for(agent, events=recorder)
    for line in ("bật đèn", "wifi nhà mình là gì", "đọc tin tức"):
        await session.handle(line)
    session.set_sensor("motion", True)
    await session.handle("tắt đèn")
    trace = recorder.to_trace()
    result = await TracePlayer(trace, agent=agent).replay()
    assert result.verdicts == ["ALLOW", "BLOCK"]
    assert_matches_golden(result, trace)


def test_the_repl_says_where_an_answer_came_from(agent):
    result = runner.invoke(app, ["run", "--agent", str(agent), "-c", "wifi nhà mình là gì"])
    assert result.exit_code == 0, result.output
    assert "says (knowledge_local): Mạng wifi là NhaMinh" in result.output


def test_the_page_has_a_panel_for_what_the_assistant_said():
    from neuroedge.viz import render_trace_html

    page = render_trace_html({"metadata": {}, "events": []})
    assert "Trợ lý nói" in page
