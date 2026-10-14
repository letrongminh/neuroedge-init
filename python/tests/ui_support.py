"""
What the page itself sends with every POST (DP-A-02, `docs/spec/deployment_profiles.md`):
its own `Origin` and the key made for this run. Tests that act as the page use these; tests
that act as another process on the machine leave them out.
"""

from __future__ import annotations

from typing import Any


def page_headers(server: Any) -> dict[str, str]:
    port = server.httpd.server_address[1]
    return {"Origin": f"http://127.0.0.1:{port}", "X-NeuroEdge-UI-Key": server.key}
