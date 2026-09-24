"""
What the device does when System 2 or an external source is not there.

* A model's text reaches speech trimmed (some models open with blank lines).
* A disabled external MCP server is said — to the model (so it tells the person
  the news is unavailable instead of claiming it has no tool), in the REPL, and
  in the banner.
* Local fallback for actions (Q-14): when the model cannot be reached, the
  device says which local commands still work — it never guesses an action
  from a near miss. Those commands meet their gate as always.
"""

from __future__ import annotations

import asyncio
import importlib.util
import shutil

import pytest
from rich.console import Console

from neuroedge.cli.run import _turn, mcp_lines
from neuroedge.models import SystemTwo
from neuroedge.models.providers.openai_chat import from_response
from neuroedge.sim import SimSession


@pytest.fixture(scope="module")
def home(root):
    return root / "fixtures" / "agents" / "home-voice" / "agent.toml"


def offline_model():
    def provider(task, name, state):
        raise ConnectionError("network down")

    return SystemTwo("offline", provider=provider)


def say(session, *lines):
    return [asyncio.run(session.handle(line)) for line in lines]


# --- 1. trimmed text -----------------------------------------------------------------------------


def response(content):
    return {"choices": [{"message": {"content": content, "tool_calls": None}}]}


def test_the_models_text_is_trimmed():
    assert from_response(response("\n\n  Tin mới nhất:\n1. A  \n"))["text"] == "Tin mới nhất:\n1. A"


def test_whitespace_only_text_is_no_text():
    assert from_response(response(" \n\t "))["text"] is None


# --- 2. a disabled external source is said -------------------------------------------------------


@pytest.fixture
def broken_news(tmp_path, root):
    from neuroedge.actions import spec

    saved = dict(spec.REGISTRY)
    spec.REGISTRY.clear()
    target = tmp_path / "home-voice"
    shutil.copytree(root / "fixtures" / "agents" / "home-voice", target)
    manifest = target / "agent.toml"
    text = manifest.read_text(encoding="utf-8")
    manifest.write_text(
        text[: text.index("[mcp]")]
        + '[mcp.servers.news]\ncommand = "/nonexistent/news"\ntools = ["headlines"]\n',
        encoding="utf-8",
    )
    yield manifest
    spec.REGISTRY.clear()
    spec.REGISTRY.update(saved)


def test_the_model_is_told_which_source_is_down_and_not_to_invent(broken_news):
    seen = {}

    def provider(task, name, state):
        seen.update(state)
        return "Hiện chưa lấy được tin tức."

    session = SimSession.load(broken_news, slow=SystemTwo("x", provider=provider))
    (turn,) = say(session, "đọc tin tức")
    assert "Không dùng được lúc này: news" in seen["instructions"]
    assert "đừng bịa" in seen["instructions"]
    assert [t["function"]["name"] for t in seen["tools"]] == ["light_on", "light_off"]
    assert turn.reply == "Hiện chưa lấy được tin tức."


def test_the_repl_shows_a_source_that_is_down(broken_news):
    session = SimSession.load(broken_news, slow=SystemTwo("x", provider=lambda *a: "ok"))
    console = Console(record=True, width=200)
    assert _turn("đọc tin tức", session, console, console)
    assert "! news không dùng được" in console.export_text()


def test_the_banner_says_the_mcp_sdk_is_missing(home, monkeypatch):
    session = SimSession.load(home, slow=SystemTwo("x", provider=lambda *a: "ok"))
    real = importlib.util.find_spec
    monkeypatch.setattr(
        importlib.util, "find_spec", lambda name, *a: None if name == "mcp" else real(name, *a)
    )
    (line,) = mcp_lines(session)
    assert "chưa cài SDK" in line and "neuroedge[mcp]" in line and "news (headlines)" in line


def test_the_banner_lists_the_sources_when_they_can_be_used(home):
    (online,) = mcp_lines(SimSession.load(home, slow=SystemTwo("x", provider=lambda *a: "ok")))
    assert "thông tin, không phải lệnh" in online
    (offline,) = mcp_lines(SimSession.load(home))
    assert "chỉ dùng khi có System 2" in offline


# --- 3. local fallback for actions ------------------------------------------------------------------


def test_with_the_model_unreachable_the_device_says_what_still_works(home):
    session = SimSession.load(home, slow=offline_model())
    (turn,) = say(session, "trời tối quá, mình không thấy gì")
    assert turn.reply_source == "offline_help"
    assert "“bật đèn”" in turn.reply and "“tắt đèn”" in turn.reply
    assert session.hal.spoken[-1] == turn.reply
    assert session.hal.pin("porch_light").commands == []  # nothing was guessed


def test_the_listed_command_then_works_offline_through_its_gate(home):
    session = SimSession.load(home, slow=offline_model())
    session.set_sensor("motion", True)
    _, on, off = say(session, "trời tối quá", "bật đèn", "tắt đèn")
    assert on.tool_results[0].call.source == "local_grammar" and on.allowed
    assert off.result.blocked and off.result.gate.failed_criterion == "room_empty"
    assert session.hal.pin("porch_light").commands == [("on", 0)]


def test_a_near_miss_is_never_turned_into_an_action(home):
    """'tắt đen' is close to 'tắt đèn' — but below the grammar threshold nothing runs."""
    session = SimSession.load(home, slow=offline_model())
    session.set_sensor("motion", False)
    (turn,) = say(session, "tắt hết đèn đóm trong nhà đi")
    assert turn.reply_source == "offline_help"
    assert session.events.of_type("tool_call") == []


def test_without_system_two_nothing_changes(home):
    session = SimSession.load(home)  # no provider configured: a grammar-only device
    (turn,) = say(session, "trời tối quá")
    assert (turn.reply, turn.reply_source) == (None, None)


def test_a_model_that_answers_with_nothing_is_not_an_outage(home):
    session = SimSession.load(home, slow=SystemTwo("x", provider=lambda *a: ""))
    (turn,) = say(session, "ờ thì")
    assert turn.reply_source is None


def test_the_repl_prints_the_fallback(home):
    session = SimSession.load(home, slow=offline_model())
    console = Console(record=True, width=200)
    assert _turn("trời tối quá", session, console, console)
    out = console.export_text()
    assert "System 2 unreachable" in out and "says (offline_help)" in out
