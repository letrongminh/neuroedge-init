"""
DP-A-08 (Q-83, TSK-I2d-27) — the box's own System 2 LLM path is legacy.

The brain is NeuroClaw, over MCP. An agent that still declares `[system_two]` keeps its grammar,
System 1 and offline answer; the LLM, the MCP host it drives and retrieval answers run only with
`NEUROEDGE_LEGACY_SYSTEM_TWO=1`, and then with a deprecation warning.
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
import textwrap

import pytest

from neuroedge.models.providers import LEGACY_FLAG
from neuroedge.sim import SimSession

SYSTEM_TWO = """
[system_two]
provider    = "litellm"
model       = "anthropic/claude-sonnet-5"
api_key_env = "NEUROEDGE_TEST_LEGACY_KEY"
"""


def test_without_the_flag_the_box_answers_with_grammar_and_the_offline_line(
    copy_agent, monkeypatch
):
    """TC-A-08-1: no LLM in the box, the same local answers, and the trace says why."""
    monkeypatch.delenv(LEGACY_FLAG, raising=False)
    plain = SimSession.load(copy_agent("home-voice", "", {}))
    session = SimSession.load(copy_agent("home-voice", SYSTEM_TWO, {}))
    assert not session.slow.available
    assert session.events.of_type("system_two_off") == [
        {"provider": "litellm", "model": "anthropic/claude-sonnet-5", "flag": LEGACY_FLAG}
    ]
    for line in ("bật đèn", "trời tối quá"):
        mine, theirs = asyncio.run(session.handle(line)), asyncio.run(plain.handle(line))
        assert (mine.reply_source, mine.reply, mine.action) == (
            theirs.reply_source,
            theirs.reply,
            theirs.action,
        )
    assert not session.events.of_type("system_two_call")
    assert session.hal.pin("porch_light").commands == [("on", 0)]
    session.trace()  # validated against trace.v1


def test_without_the_flag_loading_the_agent_never_imports_litellm(copy_agent):
    """The legacy path is not merely unused: its SDK is never loaded."""
    agent = copy_agent("home-voice", SYSTEM_TWO, {})
    code = textwrap.dedent(
        f"""
        import asyncio, os, sys
        os.environ.pop({LEGACY_FLAG!r}, None)
        from neuroedge.sim import SimSession
        session = SimSession.load({str(agent)!r})
        asyncio.run(session.handle("trời tối quá"))
        assert "litellm" not in sys.modules, "litellm was imported"
        """
    )
    subprocess.run([sys.executable, "-c", code], check=True, timeout=120)


def test_with_the_flag_the_old_path_works_and_warns(copy_agent, monkeypatch):
    monkeypatch.setenv(LEGACY_FLAG, "1")
    with pytest.warns(DeprecationWarning, match="DP-A-08"):
        session = SimSession.load(copy_agent("home-voice", SYSTEM_TWO, {}))
    assert session.slow.available
    assert not session.events.of_type("system_two_off")
