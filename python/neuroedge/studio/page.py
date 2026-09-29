"""
The studio page: one HTML document with studio.css, i18n.js and studio.js inlined
(docs/spec/studio.md §2.3 — no external asset). Boot data goes in a JSON script
element, `</` escaped, like `viz.page`.
"""

from __future__ import annotations

import html
from importlib import resources
from typing import Any

from ..viz import _embed


def _asset(name: str) -> str:
    return resources.files(__package__).joinpath("assets", name).read_text(encoding="utf-8")


def studio_page(server: Any) -> str:
    session = server.session
    boot = {
        "agent": session.manifest.label,
        "target": session.target,
        "board": session.hal.board.id,
        "voice": server.voice is not None,
    }
    title = html.escape(f"NeuroEdge Studio · {session.manifest.label}")
    return (
        '<!doctype html><html lang="vi"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{title}</title><style>{_asset('studio.css')}</style></head>"
        '<body><div id="studio"></div>'
        f'<script type="application/json" id="ne-boot">{_embed(boot)}</script>'
        f"<script>{_asset('i18n.js')}</script><script>{_asset('studio.js')}</script>"
        "</body></html>"
    )
