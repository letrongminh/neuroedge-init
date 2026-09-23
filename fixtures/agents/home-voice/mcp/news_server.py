"""
A sample **external** MCP server for home-voice: news headlines (Q-27).

System 2 reaches it as the tool ``news__headlines`` (``[mcp.servers.news]`` in
agent.toml). It is information only — it reads headlines and moves nothing —
and what it returns is untrusted data to the agent: text for the model to
phrase, never a command.

Here the headlines come from ``news.json`` next to this file, so the sample runs
offline and its tests are deterministic. A real deployment swaps the body of
`headlines` for an internet news API; nothing else changes. ``NEWS_FILE``
points it at another file.

Run by the agent over stdio; needs ``pip install 'neuroedge[mcp]'``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from mcp.server import MCPServer

server = MCPServer("news", instructions="Latest news headlines. Read-only.")


@server.tool()
def headlines(topic: str = "") -> str:
    """The latest headlines, optionally only those mentioning `topic`."""
    path = Path(os.environ.get("NEWS_FILE") or Path(__file__).with_name("news.json"))
    items = json.loads(path.read_text(encoding="utf-8"))
    if topic:
        items = [item for item in items if topic.casefold() in item["title"].casefold()]
    return (
        "\n".join(f"- {item['title']} ({item['source']})" for item in items)
        or "Không có tin."
    )


if __name__ == "__main__":
    server.run("stdio")
