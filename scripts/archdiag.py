"""
A small, deterministic diagram model for the architecture posters.

One Python description per poster (``scripts/gen_architecture_diagrams.py``)
renders to both files the docs ship:

* ``docs/architecture/assets/excalidraw/<id>.excalidraw`` — editable in
  Excalidraw; every box, label and arrow is a real element, bound together;
* ``docs/architecture/assets/svg/<id>.svg`` — the poster the markdown embeds.

Both come from the same model, so the picture a reader sees and the file an
editor opens can never disagree. ``lint()`` refuses a diagram whose boxes
overlap, whose text overflows its box, or whose arrows name a missing box —
the checks a reviewer would otherwise do by eye.

Nothing here reads the clock or a random source: the same model gives the
same bytes, which is what lets ``--check`` run in CI.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from xml.sax.saxutils import escape

# --- styles -------------------------------------------------------------------------

# kind -> (fill, stroke, text colour). Colour carries meaning, and every meaning
# is also written in the box (status badge, legend), so the poster still reads
# in greyscale.
KINDS: dict[str, tuple[str, str, str]] = {
    "person": ("#1e293b", "#0f172a", "#ffffff"),
    "system": ("#1d4ed8", "#1e3a8a", "#ffffff"),
    "container": ("#dbeafe", "#1d4ed8", "#0f172a"),
    "component": ("#eff6ff", "#3b82f6", "#0f172a"),
    "device": ("#dcfce7", "#15803d", "#052e16"),
    "store": ("#f1f5f9", "#475569", "#0f172a"),
    "external": ("#ffedd5", "#c2410c", "#431407"),
    "gate": ("#fee2e2", "#b91c1c", "#450a0a"),
    "test": ("#fef9c3", "#a16207", "#422006"),
    "planned": ("#f8fafc", "#94a3b8", "#475569"),
    "note": ("#fffbeb", "#d97706", "#451a03"),
}
GROUP_KINDS: dict[str, tuple[str, str]] = {
    "boundary": ("#f8fafc", "#1e3a8a"),
    "host": ("#f8fbff", "#2563eb"),
    "device": ("#f7fdf9", "#15803d"),
    "cloud": ("#fffaf5", "#c2410c"),
    "planned": ("#fcfcfd", "#94a3b8"),
    "test": ("#fffef5", "#a16207"),
}
STATUS_BADGE = {"done": "", "partial": "◐ partial", "planned": "○ planned"}

TITLE_PX = 15
LINE_PX = 12.5
GROUP_PX = 13
EDGE_PX = 11.5
# Average glyph width as a share of the font size, for the overflow check. Bold
# text is wider; the estimate is deliberately pessimistic so a label that
# passes the lint fits in every common sans-serif.
AVG_GLYPH = 0.56
BOLD_GLYPH = 0.62
PAD_X = 12


def text_width(text: str, px: float, bold: bool = False) -> float:
    return len(text) * px * (BOLD_GLYPH if bold else AVG_GLYPH)


# --- model --------------------------------------------------------------------------


@dataclass
class Box:
    id: str
    x: float
    y: float
    w: float
    h: float
    title: str
    lines: tuple[str, ...] = ()
    kind: str = "component"
    status: str = "done"  # done | partial | planned

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2


@dataclass
class Group:
    id: str
    x: float
    y: float
    w: float
    h: float
    label: str
    kind: str = "boundary"
    status: str = "done"


@dataclass
class Edge:
    src: str
    dst: str
    label: str = ""
    dashed: bool = False
    via: tuple[tuple[float, float], ...] = ()  # waypoints between the two boxes
    label_at: tuple[float, float] | None = None  # override the label position
    both: bool = False  # arrowheads at both ends


@dataclass
class Diagram:
    id: str
    title: str
    subtitle: str
    width: int
    height: int
    boxes: list[Box] = field(default_factory=list)
    groups: list[Group] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    legend: tuple[str, ...] = ("done", "partial", "planned")

    def box(self, id: str) -> Box:
        for b in self.boxes:
            if b.id == id:
                return b
        raise KeyError(f"{self.id}: no box {id!r}")


# --- geometry -----------------------------------------------------------------------


def _border_point(b: Box, tx: float, ty: float) -> tuple[float, float]:
    """Where the segment from the centre of `b` towards (tx, ty) leaves the box."""
    dx, dy = tx - b.cx, ty - b.cy
    if dx == 0 and dy == 0:
        return b.cx, b.cy
    sx = (b.w / 2) / abs(dx) if dx else math.inf
    sy = (b.h / 2) / abs(dy) if dy else math.inf
    s = min(sx, sy)
    return b.cx + dx * s, b.cy + dy * s


def _snap(b: Box, wx: float, wy: float) -> tuple[float, float]:
    """
    Where a straight, axis-parallel segment from waypoint (wx, wy) meets box `b`:
    a waypoint level with the box enters from the side, one above or below enters
    from the top or bottom. Otherwise fall back to the line towards the centre.
    """
    if b.y <= wy <= b.y + b.h and not (b.x <= wx <= b.x + b.w):
        return (b.x if wx < b.x else b.x + b.w), wy
    if b.x <= wx <= b.x + b.w and not (b.y <= wy <= b.y + b.h):
        return wx, (b.y if wy < b.y else b.y + b.h)
    return _border_point(b, wx, wy)


def edge_points(d: Diagram, e: Edge) -> list[tuple[float, float]]:
    a, b = d.box(e.src), d.box(e.dst)
    if not e.via:
        # straight between the boxes: axis-parallel when they share a row or a column
        ox0, ox1 = max(a.x, b.x), min(a.x + a.w, b.x + b.w)
        oy0, oy1 = max(a.y, b.y), min(a.y + a.h, b.y + b.h)
        if ox1 - ox0 > 20:
            x = (ox0 + ox1) / 2
            return [_snap(a, x, b.cy), _snap(b, x, a.cy)]
        if oy1 - oy0 > 20:
            y = (oy0 + oy1) / 2
            return [_snap(a, b.cx, y), _snap(b, a.cx, y)]
        return [_border_point(a, b.cx, b.cy), _border_point(b, a.cx, a.cy)]
    return [_snap(a, *e.via[0]), *e.via, _snap(b, *e.via[-1])]


def _label_pos(pts: list[tuple[float, float]], e: Edge) -> tuple[float, float]:
    if e.label_at:
        return e.label_at
    # middle of the longest segment: labels sit on the straight part of an arrow
    best, pos = -1.0, pts[0]
    for (x1, y1), (x2, y2) in zip(pts, pts[1:], strict=False):
        length = math.hypot(x2 - x1, y2 - y1)
        if length > best:
            best, pos = length, ((x1 + x2) / 2, (y1 + y2) / 2)
    return pos


def label_rect(d: Diagram, e: Edge) -> tuple[float, float, float, float]:
    lx, ly = _label_pos(edge_points(d, e), e)
    lines = e.label.split("\n")
    w = max(text_width(s, EDGE_PX) for s in lines) + 10
    h = len(lines) * EDGE_PX * 1.3 + 6
    return lx - w / 2, ly - h / 2, w, h


class _R:
    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h


def _overlap(a, b) -> bool:
    return a.x < b.x + b.w and b.x < a.x + a.w and a.y < b.y + b.h and b.y < a.y + a.h


def _inside(inner, outer) -> bool:
    return (
        outer.x <= inner.x
        and outer.y <= inner.y
        and inner.x + inner.w <= outer.x + outer.w
        and inner.y + inner.h <= outer.y + outer.h
    )


def box_height_needed(b: Box) -> float:
    rows = 1 + len(b.lines) + (1 if STATUS_BADGE.get(b.status) else 0)
    return 14 + TITLE_PX * 1.35 + (rows - 1) * LINE_PX * 1.45 + 10


def lint(d: Diagram) -> list[str]:
    """Every problem a reviewer would otherwise have to spot on the picture."""
    problems: list[str] = []
    ids = [b.id for b in d.boxes]
    for dup in {i for i in ids if ids.count(i) > 1}:
        problems.append(f"{d.id}: box id {dup!r} is used twice")
    for b in d.boxes:
        if b.kind not in KINDS:
            problems.append(f"{d.id}/{b.id}: unknown kind {b.kind!r}")
        if b.status not in STATUS_BADGE:
            problems.append(f"{d.id}/{b.id}: unknown status {b.status!r}")
        if b.x < 0 or b.y < 0 or b.x + b.w > d.width or b.y + b.h > d.height:
            problems.append(f"{d.id}/{b.id}: outside the canvas")
        if text_width(b.title, TITLE_PX, bold=True) > b.w - 2 * PAD_X:
            problems.append(f"{d.id}/{b.id}: title {b.title!r} is wider than the box")
        for line in b.lines:
            if text_width(line, LINE_PX) > b.w - 2 * PAD_X:
                problems.append(f"{d.id}/{b.id}: line {line!r} is wider than the box")
        if box_height_needed(b) > b.h:
            problems.append(f"{d.id}/{b.id}: text needs {box_height_needed(b):.0f}px, box is {b.h}px")
    for i, a in enumerate(d.boxes):
        for b in d.boxes[i + 1 :]:
            if _overlap(a, b):
                problems.append(f"{d.id}: boxes {a.id!r} and {b.id!r} overlap")
    for g in d.groups:
        if g.kind not in GROUP_KINDS:
            problems.append(f"{d.id}/{g.id}: unknown group kind {g.kind!r}")
        if text_width(g.label, GROUP_PX, bold=True) > g.w - 2 * PAD_X:
            problems.append(f"{d.id}/{g.id}: group label is wider than the group")
        for b in d.boxes:
            if _overlap(b, g) and not _inside(b, g):
                problems.append(f"{d.id}: box {b.id!r} straddles the edge of group {g.id!r}")
            if _inside(b, g) and b.y < g.y + 30:
                problems.append(f"{d.id}: box {b.id!r} covers the label of group {g.id!r}")
    for e in d.edges:
        for end in (e.src, e.dst):
            if end not in ids:
                problems.append(f"{d.id}: edge {e.src}->{e.dst} names a missing box {end!r}")
    for e in d.edges:
        if e.src not in ids or e.dst not in ids:
            continue
        pts = edge_points(d, e)
        for (x1, y1), (x2, y2) in zip(pts, pts[1:], strict=False):
            seg = _R(min(x1, x2) - 0.5, min(y1, y2) - 0.5, abs(x2 - x1) + 1, abs(y2 - y1) + 1)
            for b in d.boxes:
                if b.id in (e.src, e.dst):
                    continue
                inner = _R(b.x + 2, b.y + 2, b.w - 4, b.h - 4)
                if _overlap(seg, inner):
                    problems.append(f"{d.id}: edge {e.src}->{e.dst} runs through box {b.id!r}")
            for g in d.groups:
                title = _R(g.x + 10, g.y + 6, 8 + text_width(g.label, GROUP_PX, bold=True), 20)
                if _overlap(seg, title):
                    problems.append(f"{d.id}: edge {e.src}->{e.dst} crosses the title of group {g.id!r}")
    rects = []
    for e in d.edges:
        if e.label and e.src in ids and e.dst in ids:
            r = _R(*label_rect(d, e))
            for b in d.boxes:
                if _overlap(r, b):
                    problems.append(f"{d.id}: label {e.label!r} of {e.src}->{e.dst} covers box {b.id!r}")
            for g in d.groups:
                title = _R(g.x, g.y, 14 + text_width(g.label, GROUP_PX, bold=True) + 10, 30)
                if _overlap(r, title):
                    problems.append(f"{d.id}: label {e.label!r} covers the title of group {g.id!r}")
            for other_label, o in rects:
                if _overlap(r, o):
                    problems.append(f"{d.id}: labels {e.label!r} and {other_label!r} overlap")
            rects.append((e.label, r))
    return problems


# --- SVG ----------------------------------------------------------------------------

FONT = "Inter, 'Segoe UI', system-ui, -apple-system, Roboto, Helvetica, Arial, sans-serif"
MONO_HINT = ("/", "_", "(", ".py", ".c", ".h", "--", "::")


def _t(x: float, y: float, s: str, px: float, fill: str, *, bold=False, anchor="middle", italic=False) -> str:
    weight = ' font-weight="700"' if bold else ""
    style = ' font-style="italic"' if italic else ""
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="{px}" fill="{fill}" text-anchor="{anchor}"'
        f"{weight}{style}>{escape(s)}</text>"
    )


def render_svg(d: Diagram) -> str:
    out: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {d.width} {d.height}" '
        f'width="{d.width}" height="{d.height}" font-family="{FONT}" role="img" '
        f'aria-labelledby="{d.id}-title {d.id}-desc">',
        f'<title id="{d.id}-title">{escape(d.title)}</title>',
        f'<desc id="{d.id}-desc">{escape(d.subtitle)}</desc>',
        "<defs>",
        '<marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
        'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#334155"/></marker>',
        "</defs>",
        f'<rect width="{d.width}" height="{d.height}" fill="#ffffff"/>',
        _t(32, 42, d.title, 22, "#0f172a", bold=True, anchor="start"),
        _t(32, 66, d.subtitle, 13, "#475569", anchor="start"),
    ]
    for g in d.groups:
        fill, stroke = GROUP_KINDS[g.kind]
        dash = ' stroke-dasharray="7 5"' if g.status == "planned" or g.kind == "planned" else ""
        out.append(
            f'<rect x="{g.x}" y="{g.y}" width="{g.w}" height="{g.h}" rx="14" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="1.6"{dash}/>'
        )
        out.append(_t(g.x + 14, g.y + 21, g.label, GROUP_PX, stroke, bold=True, anchor="start"))
    for e in d.edges:
        pts = edge_points(d, e)
        path = " ".join(f"{'M' if i == 0 else 'L'}{x:.1f},{y:.1f}" for i, (x, y) in enumerate(pts))
        dash = ' stroke-dasharray="6 5"' if e.dashed else ""
        start = ' marker-start="url(#arr)"' if e.both else ""
        out.append(
            f'<path d="{path}" fill="none" stroke="#334155" stroke-width="1.5"{dash}{start} '
            'marker-end="url(#arr)"/>'
        )
    for b in d.boxes:
        fill, stroke, ink = KINDS["planned"] if b.status == "planned" else KINDS[b.kind]
        if b.status == "planned":
            stroke = KINDS[b.kind][1]
        dash = ' stroke-dasharray="7 5"' if b.status == "planned" else ""
        width = "2.2" if b.kind in ("system", "gate") else "1.6"
        rx = 26 if b.kind == "person" else 10
        out.append(
            f'<rect x="{b.x}" y="{b.y}" width="{b.w}" height="{b.h}" rx="{rx}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{width}"{dash}/>'
        )
        if b.kind == "store":
            out.append(
                f'<path d="M{b.x + 1},{b.y + 12} Q{b.cx},{b.y + 24} {b.x + b.w - 1},{b.y + 12}" '
                f'fill="none" stroke="{stroke}" stroke-width="1.2"/>'
            )
        rows = [(b.title, TITLE_PX, True)] + [(s, LINE_PX, False) for s in b.lines]
        badge = STATUS_BADGE.get(b.status)
        if badge:
            rows.append((badge, LINE_PX, False))
        total = TITLE_PX * 1.35 + (len(rows) - 1) * LINE_PX * 1.45
        y = b.cy - total / 2 + TITLE_PX
        for i, (s, px, bold) in enumerate(rows):
            italic = badge is not None and i == len(rows) - 1 and bool(badge)
            out.append(_t(b.cx, y, s, px, ink, bold=bold, italic=italic))
            y += (TITLE_PX * 1.35) if i == 0 else LINE_PX * 1.45
    for e in d.edges:
        if not e.label:
            continue
        x, y, w, h = label_rect(d, e)
        out.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="4" fill="#ffffff" '
            'fill-opacity="0.96" stroke="#e2e8f0" stroke-width="0.8"/>'
        )
        for i, s in enumerate(e.label.split("\n")):
            out.append(_t(x + w / 2, y + 3 + EDGE_PX + i * EDGE_PX * 1.3 - 2, s, EDGE_PX, "#1e293b", italic=True))
    # legend
    lx, ly = d.width - 32, 56
    items = []
    if "done" in d.legend:
        items.append(("solid", "done — in code on main"))
    if "partial" in d.legend:
        items.append(("partial", "◐ partial — part in code"))
    if "planned" in d.legend:
        items.append(("dashed", "○ planned — not in code yet"))
    for i, (style, label) in enumerate(reversed(items)):
        wlabel = text_width(label, 12)
        x2 = lx - wlabel
        x1 = x2 - 40
        yy = ly - i * 20 + (len(items) - 1) * 20 - 26
        dash = ' stroke-dasharray="7 5"' if style == "dashed" else ""
        out.append(
            f'<rect x="{x1}" y="{yy - 10}" width="32" height="14" rx="3" fill="#ffffff" '
            f'stroke="#475569" stroke-width="1.4"{dash}/>'
        )
        out.append(_t(x2 + 4, yy + 1, label, 12, "#334155", anchor="start"))
    out.append("</svg>")
    return "\n".join(out) + "\n"


# --- Excalidraw ---------------------------------------------------------------------


def _seed(*parts: str) -> int:
    return int(hashlib.sha1("/".join(parts).encode()).hexdigest()[:8], 16)


def _base(eid: str, kind: str, x: float, y: float, w: float, h: float, d: Diagram) -> dict:
    return {
        "id": eid,
        "type": kind,
        "x": round(x, 2),
        "y": round(y, 2),
        "width": round(w, 2),
        "height": round(h, 2),
        "angle": 0,
        "strokeColor": "#1e293b",
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 1,
        "strokeStyle": "solid",
        "roughness": 0,
        "opacity": 100,
        "groupIds": [],
        "frameId": None,
        "roundness": None,
        "seed": _seed(d.id, eid),
        "version": 1,
        "versionNonce": _seed(d.id, eid, "nonce"),
        "isDeleted": False,
        "boundElements": [],
        "updated": 1,
        "link": None,
        "locked": False,
    }


def _text_el(eid: str, text: str, x, y, w, h, px, color, d: Diagram, container=None, align="center") -> dict:
    el = _base(eid, "text", x, y, w, h, d)
    el.update(
        {
            "strokeColor": color,
            "text": text,
            "originalText": text,
            "fontSize": px,
            "fontFamily": 2,
            "textAlign": align,
            "verticalAlign": "middle" if container else "top",
            "containerId": container,
            "lineHeight": 1.3,
            "autoResize": True,
        }
    )
    return el


def render_excalidraw(d: Diagram) -> str:
    els: list[dict] = []
    title = _text_el("title", d.title, 32, 20, text_width(d.title, 22, True), 28, 22, "#0f172a", d, align="left")
    sub = _text_el("subtitle", d.subtitle, 32, 52, text_width(d.subtitle, 13), 18, 13, "#475569", d, align="left")
    els += [title, sub]
    for g in d.groups:
        fill, stroke = GROUP_KINDS[g.kind]
        r = _base(f"group-{g.id}", "rectangle", g.x, g.y, g.w, g.h, d)
        r.update({"strokeColor": stroke, "backgroundColor": fill, "roundness": {"type": 3}})
        if g.status == "planned" or g.kind == "planned":
            r["strokeStyle"] = "dashed"
        els.append(r)
        els.append(
            _text_el(f"group-{g.id}-label", g.label, g.x + 14, g.y + 8, text_width(g.label, GROUP_PX, True),
                     18, GROUP_PX, stroke, d, align="left")
        )
    box_el: dict[str, dict] = {}
    for b in d.boxes:
        fill, stroke, ink = KINDS["planned"] if b.status == "planned" else KINDS[b.kind]
        if b.status == "planned":
            stroke = KINDS[b.kind][1]
        r = _base(f"box-{b.id}", "rectangle", b.x, b.y, b.w, b.h, d)
        r.update({"strokeColor": stroke, "backgroundColor": fill, "roundness": {"type": 3},
                  "strokeWidth": 2 if b.kind in ("system", "gate") else 1})
        if b.status == "planned":
            r["strokeStyle"] = "dashed"
        lines = [b.title, *b.lines]
        if STATUS_BADGE.get(b.status):
            lines.append(STATUS_BADGE[b.status])
        text = "\n".join(lines)
        t = _text_el(f"box-{b.id}-text", text, b.x + PAD_X, b.y + 8, b.w - 2 * PAD_X, b.h - 16, LINE_PX,
                     ink, d, container=r["id"])
        r["boundElements"].append({"type": "text", "id": t["id"]})
        box_el[b.id] = r
        els += [r, t]
    for i, e in enumerate(d.edges):
        pts = edge_points(d, e)
        x0, y0 = pts[0]
        a = _base(f"edge-{i}-{e.src}-{e.dst}", "arrow", x0, y0,
                  max(abs(p[0] - x0) for p in pts), max(abs(p[1] - y0) for p in pts), d)
        a.update(
            {
                "strokeColor": "#334155",
                "strokeStyle": "dashed" if e.dashed else "solid",
                "points": [[round(px - x0, 2), round(py - y0, 2)] for px, py in pts],
                "startBinding": {"elementId": box_el[e.src]["id"], "focus": 0, "gap": 1},
                "endBinding": {"elementId": box_el[e.dst]["id"], "focus": 0, "gap": 1},
                "startArrowhead": "arrow" if e.both else None,
                "endArrowhead": "arrow",
                "roundness": None,
                "elbowed": False,
            }
        )
        box_el[e.src]["boundElements"].append({"type": "arrow", "id": a["id"]})
        box_el[e.dst]["boundElements"].append({"type": "arrow", "id": a["id"]})
        els.append(a)
        if e.label:
            lx, ly = _label_pos(pts, e)
            lines = e.label.split("\n")
            w = max(text_width(s, EDGE_PX) for s in lines)
            h = len(lines) * EDGE_PX * 1.3
            t = _text_el(f"edge-{i}-label", e.label, lx - w / 2, ly - h / 2, w, h, EDGE_PX, "#1e293b", d,
                         container=a["id"])
            a["boundElements"].append({"type": "text", "id": t["id"]})
            els.append(t)
    doc = {
        "type": "excalidraw",
        "version": 2,
        "source": "neuroedge scripts/gen_architecture_diagrams.py",
        "elements": els,
        "appState": {"viewBackgroundColor": "#ffffff", "gridSize": None},
        "files": {},
    }
    return json.dumps(doc, ensure_ascii=False, indent=1) + "\n"
