"""
TSK-S3-22 — `neuroedge trace view` (offline HTML) and `trace export --format chrome`.

The page must open with no network (FR-DX-02), embed the trace so nothing is
fetched, and never let trace text break out of its <script> element.
"""

from __future__ import annotations

import json
import re

from typer.testing import CliRunner

from neuroedge.cli.main import app
from neuroedge.viz import board_info, render_trace_html, to_chrome_trace

runner = CliRunner()


def canonical(traces_dir, name):
    return json.loads((traces_dir / f"{name}.json").read_text(encoding="utf-8"))


def embedded(page: str) -> dict:
    (payload,) = re.findall(
        r'<script type="application/json" id="ne-data">(.*?)</script>', page, re.S
    )
    return json.loads(payload)


def test_trace_view_writes_a_page_next_to_the_trace(traces_dir, tmp_path):
    source = tmp_path / "happy.json"
    source.write_text((traces_dir / "happy-path.json").read_text("utf-8"), encoding="utf-8")
    result = runner.invoke(app, ["trace", "view", str(source)])
    assert result.exit_code == 0, result.output
    page = (tmp_path / "happy.html").read_text("utf-8")
    assert page.startswith("<!doctype html>")
    data = embedded(page)
    assert data["meta"]["session_id"] == "sess_a1b2c3d4"
    assert [e["type"] for e in data["events"]][-2] == "actuator_command"


def test_the_page_needs_no_network(traces_dir):
    page = render_trace_html(canonical(traces_dir, "happy-path"))
    assert not re.search(r"<(script|link|img)[^>]+(src|href)=", page)
    assert "@import" not in page and "url(" not in page
    assert "fetch(" not in page  # only the live page talks to its own server


def test_the_board_is_embedded_so_untouched_pins_show(traces_dir):
    data = embedded(render_trace_html(canonical(traces_dir, "unverified_attempt")))
    assert data["board"]["pins"] == ["door_lock", "porch_light", "gate_relay"]
    assert "temperature" in data["board"]["sensors"]
    assert board_info("no-such-board") == {}


def test_trace_text_cannot_close_the_script_element(traces_dir):
    trace = canonical(traces_dir, "happy-path")
    trace["events"][-1]["data"]["text"] = "</script><script>alert(1)</script>"
    page = render_trace_html(trace)
    assert "</script><script>alert(1)" not in page
    assert embedded(page)["events"][-1]["data"]["text"] == "</script><script>alert(1)</script>"


def test_an_invalid_trace_is_refused(traces_dir, tmp_path):
    result = runner.invoke(
        app, ["trace", "view", str(traces_dir / "invalid" / "missing_board_id.json")]
    )
    assert result.exit_code == 1
    assert "NE4001" in result.output


# --- Perfetto export ------------------------------------------------------------------


def test_gate_evaluations_and_pulses_become_slices(traces_dir):
    chrome = to_chrome_trace(canonical(traces_dir, "happy-path"))
    slices = {e["name"]: e for e in chrome["traceEvents"] if e.get("ph") == "X"}
    gate = slices["unlock_door@1.2.0 ALLOW"]
    assert (gate["ts"], gate["dur"]) == (550_000, 40_000)  # µs: begin 550 ms → result 590 ms
    pulse = slices["door_lock pulse"]
    assert (pulse["ts"], pulse["dur"]) == (595_000, 30_000_000)
    threads = {e["args"]["name"] for e in chrome["traceEvents"] if e["name"] == "thread_name"}
    assert {"gates", "pin door_lock", "events"} <= threads


def test_trace_export_cli(traces_dir, tmp_path):
    out = tmp_path / "t.chrome.json"
    result = runner.invoke(
        app, ["trace", "export", str(traces_dir / "network_offline.json"), "--out", str(out)]
    )
    assert result.exit_code == 0, result.output
    names = [e["name"] for e in json.loads(out.read_text("utf-8"))["traceEvents"]]
    assert "unlock_door@1.2.0 BLOCK" in names
    bad = runner.invoke(
        app, ["trace", "export", str(traces_dir / "happy-path.json"), "--format", "svg"]
    )
    assert bad.exit_code == 1
