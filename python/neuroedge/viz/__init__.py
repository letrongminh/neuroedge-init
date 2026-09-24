"""
Session visualisation (TSK-S3-22, TSK-S2-09; docs/spec/simulation_coverage.md §5).

* `render_trace_html(trace)` — one self-contained HTML file: devices (door lock,
  lights, relays), sensors, screen, gate verdicts and the event timeline, with a
  slider to scrub through the session. No network, no external asset: the CSS
  and JS are inlined and the trace is embedded as JSON (FR-DX-02).
* `page(...)` — the same page, used live by `neuroedge run --ui`.
* `to_chrome_trace(trace)` — Chrome Trace Event JSON for Perfetto: gate
  evaluations and pulses as slices on their own tracks, everything else instant.
"""

from __future__ import annotations

import html
import json
from importlib import resources
from typing import Any

from ..errors import BoardCapabilityError
from ..hal.board import load_board_by_id


def _asset(name: str) -> str:
    return resources.files(__package__).joinpath("assets", name).read_text(encoding="utf-8")


def _embed(value: Any) -> str:
    """JSON safe inside <script>: no `</` can close the element early."""
    return json.dumps(value, ensure_ascii=False).replace("</", "<\\/")


def board_info(board_id: str | None) -> dict[str, Any]:
    """Pins, sensors and display the board declares — so the page shows untouched pins too."""
    if not board_id:
        return {}
    try:
        board = load_board_by_id(board_id)
    except BoardCapabilityError:
        return {}
    info: dict[str, Any] = {
        "id": board.id,
        "pins": list(board.pins),
        "sensors": list(board.sensors),
    }
    if board.supports("display"):
        info["display"] = board.capability("display")
    return info


def page(
    *,
    title: str,
    meta: dict[str, Any],
    events: list[dict[str, Any]],
    board: dict[str, Any],
    live: bool = False,
) -> str:
    boot = "const data = JSON.parse(document.getElementById('ne-data').textContent);\n" + (
        "const view = NE.mount(document.getElementById('ne'), {meta: data.meta, board: data.board,"
        " events: data.events, live: true, onCommand: function (text) {"
        " fetch('/command', {method: 'POST', headers: {'Content-Type': 'text/plain; charset=utf-8'},"
        " body: text}); }, onConfirm: function (id, yes) {"
        " fetch('/confirm', {method: 'POST', headers: {'Content-Type': 'application/json'},"
        " body: JSON.stringify({id: id, answer: yes ? 'yes' : 'no'})}); }});\n"
        "const stream = new EventSource('/events');\n"
        "stream.onmessage = function (m) { const s = JSON.parse(m.data);"
        " view.update(s.events, s.now_ms); };\n"
        if live
        else "NE.mount(document.getElementById('ne'), {meta: data.meta, board: data.board,"
        " events: data.events, live: false});\n"
    )
    return (
        '<!doctype html>\n<html lang="vi">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{html.escape(title)}</title>\n<style>\n{_asset('ui.css')}</style>\n</head>\n"
        '<body>\n<div id="ne"></div>\n'
        f'<script type="application/json" id="ne-data">{_embed({"meta": meta, "board": board, "events": events})}</script>\n'
        f"<script>\n{_asset('ui.js')}</script>\n<script>\n{boot}</script>\n</body>\n</html>\n"
    )


def render_trace_html(trace: dict[str, Any]) -> str:
    meta = trace.get("metadata", {})
    title = f"{meta.get('agent_version', 'NeuroEdge')} · {meta.get('session_id', '')}"
    return page(
        title=title,
        meta=meta,
        events=trace.get("events", []),
        board=board_info(meta.get("board_id")),
    )


def to_chrome_trace(trace: dict[str, Any]) -> dict[str, Any]:
    """Chrome Trace Event format (microseconds) for ui.perfetto.dev or chrome://tracing."""
    tracks: dict[str, int] = {}

    def tid(name: str) -> int:
        return tracks.setdefault(name, len(tracks) + 1)

    out: list[dict[str, Any]] = []
    begin: tuple[str, int] | None = None
    for event in trace.get("events", []):
        kind, data, at = event["type"], event.get("data", {}), event["offset_ms"] * 1000
        if kind == "gate_evaluation_begin":
            begin = (data.get("gate", "gate"), at)
        elif kind == "gate_evaluation_result" and begin is not None:
            gate, start = begin
            out.append(
                {
                    "name": f"{gate} {data.get('verdict')}",
                    "cat": "gate",
                    "ph": "X",
                    "ts": start,
                    "dur": max(at - start, 1),
                    "pid": 1,
                    "tid": tid("gates"),
                    "args": data,
                }
            )
            begin = None
        elif kind == "actuator_command":
            out.append(
                {
                    "name": f"{data.get('pin')} {data.get('operation')}",
                    "cat": "actuator",
                    "ph": "X",
                    "ts": at,
                    "dur": max(int(data.get("duration_ms", 0)) * 1000, 1),
                    "pid": 1,
                    "tid": tid(f"pin {data.get('pin')}"),
                    "args": data,
                }
            )
        else:
            out.append(
                {
                    "name": kind,
                    "cat": kind.split("_")[0],
                    "ph": "i",
                    "s": "t",
                    "ts": at,
                    "pid": 1,
                    "tid": tid("events"),
                    "args": data,
                }
            )
    meta = trace.get("metadata", {})
    names = [
        {
            "name": "process_name",
            "ph": "M",
            "pid": 1,
            "args": {"name": meta.get("agent_version", "neuroedge")},
        }
    ] + [
        {"name": "thread_name", "ph": "M", "pid": 1, "tid": number, "args": {"name": name}}
        for name, number in tracks.items()
    ]
    return {"traceEvents": names + out, "displayTimeUnit": "ms", "metadata": meta}
