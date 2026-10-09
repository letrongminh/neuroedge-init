"""
TSK-I2c-19 (Q-70) — the partner pilot pack: the guides in `docs/user/doi-tac/` are executable.

`scripts/partner_guides_check.sh <wheel>` runs every command block of the three guides from an
installed wheel, against local doubles. These tests hold the guides to the same rules *without* a
wheel, so CI catches drift on every push: every shell/python block is marked (run, or skip with a
reason), every `neuroedge` command a guide runs names a command and options the CLI really has, every
relative link lands on a file, and the checklists agree with the stopwatch script.
"""

from __future__ import annotations

import asyncio
import importlib.util
import re
import shlex
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest
import typer.main

from neuroedge.cli.main import app
from neuroedge.errors import NeuroEdgeError
from neuroedge.proxy_mcp import init as init_mcp

ROOT = Path(__file__).resolve().parents[2]
USER = ROOT / "docs" / "user" / "doi-tac"
BUSINESS = ROOT / "docs" / "business" / "doi-tac"
GUIDES = [USER / "home-assistant-mcp.md", USER / "guard-python.md", USER / "proxy-http.md"]
PAGES = [*GUIDES, USER / "README.md", USER / "gioi-han.md", USER / "phan-hoi.md"]
BUSINESS_PAGES = [
    BUSINESS / "thoa-thuan.md",
    BUSINESS / "kenh-phan-hoi.md",
    BUSINESS / "buoi-do.md",
]

_spec = importlib.util.spec_from_file_location("guide_runner", ROOT / "scripts" / "guide_runner.py")
runner = importlib.util.module_from_spec(_spec)
sys.modules["guide_runner"] = runner
_spec.loader.exec_module(runner)  # type: ignore[union-attr]


# --- the rules --------------------------------------------------------------------------------------


@pytest.mark.parametrize("path", [*GUIDES, USER / "README.md"], ids=lambda p: p.name)
def test_every_block_of_a_guide_is_marked_and_runnable(path):
    blocks, problems = runner.extract(path)
    assert problems == [], problems
    commands = [b for b in blocks if b.runnable_language]
    assert commands, f"{path.name} has no command block"
    assert all(b.kind in ("run", "skip") for b in commands), "no unmarked shell or python block"
    assert all(b.reason for b in commands if b.kind == "skip"), "every skip says why"


@pytest.mark.parametrize("path", GUIDES, ids=lambda p: p.name)
def test_a_guide_runs_enough_and_skips_little(path):
    blocks, _ = runner.extract(path)
    run = [b for b in blocks if b.kind == "run"]
    skip = [b for b in blocks if b.kind == "skip"]
    assert len(run) >= 8, "a guide is mostly commands that are really run"
    assert len(skip) <= 4 and len(skip) < len(run)
    assert any(b.exit == 1 and b.expect for b in run), (
        "troubleshooting shows real messages (exit=1, expect=)"
    )
    # the promised outputs are checked: most run blocks name what they expect
    assert sum(1 for b in run if b.expect or b.log_has or b.log_lacks) >= len(run) // 2


def test_the_runner_refuses_an_unmarked_or_malformed_block(tmp_path):
    bad = tmp_path / "bad.md"
    bad.write_text(
        "# x\n\n```bash\necho unmarked\n```\n\n"
        "<!-- guide: skip -->\n```bash\necho no reason\n```\n\n"
        "<!-- guide: run bg=server -->\n```bash\nsleep 1\n```\n\n"
        "<!-- guide: run surprise -->\n```bash\necho x\n```\n\n"
        "<!-- guide: run -->\n\ntext between\n```bash\necho gap\n```\n\n"
        "<!-- guide: run -->\n```toml\nk = 1\n```\n",
        encoding="utf-8",
    )
    _, problems = runner.extract(bad)
    text = "\n".join(problems)
    for needle in (
        "an unmarked bash block",
        "skip needs reason=",
        "bg= needs wait=",
        "unknown marker word 'surprise'",
        "the marker is not right before a block",
        "`run` on a toml block",
    ):
        assert needle in text, needle


def test_the_markers_are_documented_in_the_runner():
    doc = runner.__doc__ or ""
    for word in (
        "run",
        "skip reason=",
        "exit=N",
        "expect=",
        "bg=NAME",
        "wait=",
        "stop=NAME",
        "log_has=",
        "log_lacks=",
    ):
        assert word in doc, word


# A value is a quoted string or a run without quotes or spaces — never both, so the match cannot
# backtrack exponentially (CodeQL py/redos).
COMMAND = re.compile(r"(?:^|&& )(?:env -u \w+ |[A-Z_]+=(?:\"[^\"]*\"|[^\s\"]+) )*neuroedge (.+)$")


def _commands(path: Path):
    """Every `neuroedge …` command line of the guide's run blocks: (block, words after `neuroedge`)."""
    blocks, _ = runner.extract(path)
    for block in blocks:
        if block.kind != "run" or block.lang not in runner.SHELL:
            continue
        for line in block.code.splitlines():
            found = COMMAND.search(line.strip())
            if found:
                yield block, shlex.split(found.group(1), comments=True)


@pytest.mark.parametrize("path", GUIDES, ids=lambda p: p.name)
def test_every_neuroedge_command_of_a_guide_exists_with_its_options(path):
    """The CLI contract, read from the Typer tree: a renamed command or flag turns a guide red."""
    root = typer.main.get_command(app)
    seen = 0
    for block, words in _commands(path):
        command = root
        index = 0
        while (
            hasattr(command, "commands") and index < len(words) and not words[index].startswith("-")
        ):
            assert words[index] in command.commands, (
                f"{block.label()}: no command {' '.join(words[: index + 1])!r}"
            )
            command = command.commands[words[index]]
            index += 1
        known = {
            opt
            for param in command.params
            if hasattr(param, "opts")
            for opt in [*param.opts, *param.secondary_opts]
        }
        for word in words[index:]:
            if word.startswith("--"):
                assert word.partition("=")[0] in known, (
                    f"{block.label()}: {word} is not an option of `{' '.join(words[:index])}`"
                )
        seen += 1
    assert seen >= 2, "the guide runs real neuroedge commands"


@pytest.mark.parametrize("path", [*PAGES, *BUSINESS_PAGES], ids=lambda p: p.name)
def test_every_relative_link_lands_on_a_file(path):
    text = path.read_text(encoding="utf-8")
    for target in re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", text):
        if re.match(r"[a-z]+:", target):
            continue
        assert (path.parent / target).resolve().exists(), (
            f"{path.name} links to {target}, which does not exist"
        )


def test_the_pages_say_what_the_pilot_promises_and_what_it_lacks():
    limits = (USER / "gioi-han.md").read_text(encoding="utf-8")
    for needle in (
        "esp32s3", "NeuroBrain", "thoại trên chip", "Raspberry Pi thật", "TSK-I2c-16", "chưa kiểm trên Home Assistant thật",
        "không chặn được lời gọi thẳng", "allow_lan_http", "PolyForm Noncommercial", "tham số của lời gọi", "không có xác thực ở phía trước",
    ):  # fmt: skip
        assert needle.casefold() in limits.casefold(), needle
    readme = (USER / "README.md").read_text(encoding="utf-8")
    assert "đặt một gate trước mọi lệnh AI chạm vào thiết bị bạn đang có" in readme
    assert "pip install './neuroedge-0.1.0-py3-none-any.whl[mcp]'" in readme
    feedback = (USER / "phan-hoi.md").read_text(encoding="utf-8")
    for needle in (
        "BLOCK đầu tiên",
        "ALLOW đầu tiên CÓ CHỦ Ý",
        "NGUYÊN VĂN",
        "TODOS.md",
        "phong-van.md",
    ):
        assert needle in feedback, needle
    for guide in GUIDES:
        text = guide.read_text(encoding="utf-8")
        assert "plugin doctor" in text and "trace validate" in text and "Lỗi thường gặp" in text, (
            guide.name
        )
    assert "chưa kiểm trên Home Assistant thật" in GUIDES[0].read_text(encoding="utf-8")


def test_the_checklists_and_the_stopwatch_agree_on_the_steps():
    script = (ROOT / "scripts" / "partner_session_timer.sh").read_text(encoding="utf-8")
    ids = re.findall(r'^\s+"(S\d)\|', script, flags=re.M)
    table = (BUSINESS / "buoi-do.md").read_text(encoding="utf-8")
    scripted = re.findall(r"^\| [\d:–]+ \| \*\*(S\d)\*\* \|", table, flags=re.M)
    assert ids == scripted == [f"S{n}" for n in range(9)]
    assert "bash" in script.splitlines()[0] and "set -euo pipefail" in script


def test_the_stopwatch_writes_a_csv(tmp_path):
    out = tmp_path / "session.csv"
    answers = "\n\n\ns\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n"
    done = subprocess.run(
        ["bash", str(ROOT / "scripts" / "partner_session_timer.sh"), str(out)],
        input=answers, capture_output=True, text=True, timeout=60, check=False,
    )  # fmt: skip
    assert done.returncode == 0, done.stderr
    rows = out.read_text(encoding="utf-8").splitlines()
    assert rows[0] == "step,label,clock_utc,elapsed_s,hints,note"
    assert [r.split(",")[0] for r in rows[1:]][0] == "S0" and len(rows) >= 3
    skipped = [r for r in rows if r.startswith("S1,")]
    assert skipped and skipped[0].endswith(",,,,"), "an `s` writes a row with no time"


# --- the Home Assistant double ------------------------------------------------------------------------


def _free_port() -> int:
    with socket.socket() as spare:
        spare.bind(("127.0.0.1", 0))
        return spare.getsockname()[1]


def test_the_home_assistant_double_wants_a_bearer_token_and_exposes_assist_style_tools(
    tmp_path, monkeypatch
):
    port, token, log = _free_port(), "double-token-not-a-secret", tmp_path / "ha.log"
    env = {**__import__("os").environ, "HA_DOUBLE_TOKEN": token, "UPSTREAM_LOG": str(log)}
    server = subprocess.Popen(
        [sys.executable, str(ROOT / "fixtures" / "ha_mcp_double" / "server.py"), str(port)],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )  # fmt: skip
    try:
        for _ in range(100):
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
                break
            except OSError:
                time.sleep(0.1)
        url = f"http://127.0.0.1:{port}/mcp"
        with pytest.raises(urllib.error.HTTPError) as unauthorised:
            urllib.request.urlopen(
                urllib.request.Request(url, data=b"{}", method="POST"), timeout=10
            )
        assert unauthorised.value.code == 401
        monkeypatch.setenv("HA_AUTH", f"Bearer {token}")
        plan = asyncio.run(
            init_mcp(
                url,
                tmp_path / "ha",
                "homeassistant",
                header_env=["Authorization=HA_AUTH"],
                allow_lan_http=True,
            )
        )
        assert {
            "hassturnon",
            "hassturnoff",
            "hasslightset",
            "getlivecontext",
            "getdatetime",
        } <= set(plan.exposed)
        assert not log.exists() or log.read_text() == "", "listing tools is not a call"
        monkeypatch.setenv("HA_AUTH", "Bearer wrong")
        with pytest.raises(NeuroEdgeError, match="cannot connect to the real MCP server"):
            asyncio.run(
                init_mcp(
                    url,
                    tmp_path / "ha2",
                    "x",
                    header_env=["Authorization=HA_AUTH"],
                    allow_lan_http=True,
                )
            )
    finally:
        server.terminate()
        server.wait(timeout=10)
