"""
`neuroedge studio` — the local web app that shows every capability on a laptop
(TSK-I1-04, Q-51). The contract between this server and its page — paths, JSON
shapes, safety rules — is docs/spec/studio.md.

    server.py      the HTTP server: the sim page's session routes, plus /api/*
    page.py        the page: studio.css, i18n.js and studio.js inlined, no external asset
    api_agent.py   /api/agent, /api/gates…, /api/mcp
    api_checks.py  /api/traces…, /api/record, /api/lint, /api/verify, /api/test
    api_device.py  /api/device…
    voice.py       /api/voice… — the microphone session behind the page (Q-50)
"""

from .server import StudioServer, serve

__all__ = ["StudioServer", "serve"]
