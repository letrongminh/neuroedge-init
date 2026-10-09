"""
A stand-in **upstream** MCP server for the tests of `neuroedge proxy mcp` (TSK-I2c-14).

It plays what Home Assistant's MCP server plays: tools the proxy must put a gate in front of.
Every call is appended to the file named by ``UPSTREAM_LOG`` (one JSON line each), so a test can
say what the upstream was — and was not — asked. Over stdio by default; ``--http PORT`` serves
Streamable HTTP on 127.0.0.1 instead.

Tools:

* ``get-state``      a hyphenated name (guard tool names cannot have a hyphen), one string argument;
* ``turn_on``        a required string, an optional integer with a default, an optional string
                     without one, an optional object (the proxy drops it);
* ``call_service``   a REQUIRED object argument — the proxy cannot expose it;
* ``crash``          ends the process mid-call: the upstream fails after the gate said ALLOW.

Needs the `mcp` extra.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from mcp.server import MCPServer

server = MCPServer("upstream", instructions="A stand-in smart-home server for tests.")


def _record(tool: str, **arguments: Any) -> None:
    path = os.environ.get("UPSTREAM_LOG")
    if path:
        with open(path, "a", encoding="utf-8") as log:
            log.write(json.dumps({"tool": tool, "arguments": arguments}) + "\n")


@server.tool(name="get-state")
def get_state(entity_id: str) -> str:
    """The state of one entity."""
    _record("get-state", entity_id=entity_id)
    return f"{entity_id}: on"


@server.tool()
def turn_on(
    entity_id: str,
    brightness: int = 100,
    note: str | None = None,
    attributes: dict[str, Any] | None = None,
) -> str:
    """Turn an entity on."""
    _record("turn_on", entity_id=entity_id, brightness=brightness, note=note, attributes=attributes)
    return f"{entity_id} on at {brightness}"


@server.tool()
def call_service(domain: str, data: dict[str, Any]) -> str:
    """Call any service with free-form data."""
    _record("call_service", domain=domain, data=data)
    return "called"


@server.tool()
def crash() -> str:
    """Never answers: the process ends."""
    _record("crash")
    os._exit(3)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--http":
        server.run("streamable-http", host="127.0.0.1", port=int(sys.argv[2]))
    else:
        server.run("stdio")
