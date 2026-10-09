"""
A DOUBLE of Home Assistant's MCP Server integration — **not Home Assistant**.

Built from what Home Assistant's public documentation says about that integration (the "Model Context
Protocol Server" integration): an MCP server over Streamable HTTP at `/mcp`, authenticated with a
long-lived access token sent as `Authorization: Bearer <token>`, exposing the Assist API's intents as
tools (`HassTurnOn`, `HassTurnOff`, `HassLightSet`, `GetLiveContext`, `GetDateTime`…). The tool names and
parameter shapes below follow that documentation as the authors read it; they have NOT been compared with a
running Home Assistant. Treat every guide step that uses this double as "chưa kiểm trên Home Assistant thật".

    HA_DOUBLE_TOKEN=<secret> python server.py PORT

Every call is appended to the file named by `UPSTREAM_LOG` (one JSON line: tool, arguments), so a test can
say what the "Home Assistant" was — and was not — asked. A request without the right bearer token gets 401
and is not logged as a call. Needs the `mcp` extra (and uvicorn, which it brings).
"""

from __future__ import annotations

import hmac
import json
import os
import sys
from typing import Any

from mcp.server import MCPServer

server = MCPServer(
    "home-assistant-double",
    instructions="A double of Home Assistant's MCP Server. Not Home Assistant.",
)


def _record(tool: str, **arguments: Any) -> None:
    path = os.environ.get("UPSTREAM_LOG")
    if path:
        with open(path, "a", encoding="utf-8") as log:
            log.write(json.dumps({"tool": tool, "arguments": arguments}) + "\n")


@server.tool(name="HassTurnOn")
def hass_turn_on(
    name: str | None = None,
    area: str | None = None,
    floor: str | None = None,
    domain: list[str] | None = None,
    device_class: list[str] | None = None,
) -> str:
    """Turns on/opens/presses a device or entity."""
    _record(
        "HassTurnOn",
        name=name,
        area=area,
        floor=floor,
        domain=domain,
        device_class=device_class,
    )
    return f"Turned on {name or area or 'everything'}"


@server.tool(name="HassTurnOff")
def hass_turn_off(
    name: str | None = None,
    area: str | None = None,
    floor: str | None = None,
    domain: list[str] | None = None,
    device_class: list[str] | None = None,
) -> str:
    """Turns off/closes a device or entity."""
    _record(
        "HassTurnOff",
        name=name,
        area=area,
        floor=floor,
        domain=domain,
        device_class=device_class,
    )
    return f"Turned off {name or area or 'everything'}"


@server.tool(name="HassLightSet")
def hass_light_set(
    name: str,
    brightness: int | None = None,
    color: str | None = None,
    temperature: int | None = None,
) -> str:
    """Sets the brightness percentage or color of a light."""
    _record(
        "HassLightSet",
        name=name,
        brightness=brightness,
        color=color,
        temperature=temperature,
    )
    return f"Set {name}"


@server.tool(name="GetLiveContext")
def get_live_context() -> str:
    """Provides real-time information about the CURRENT state of devices, sensors and areas."""
    _record("GetLiveContext")
    return "- names: Living room lamp\n  domain: light\n  state: 'on'\n"


@server.tool(name="GetDateTime")
def get_date_time() -> str:
    """Provides the current date and time."""
    _record("GetDateTime")
    return "2026-10-12 09:00:00"


class BearerOnly:
    """ASGI middleware: no `Authorization: Bearer <HA_DOUBLE_TOKEN>`, no MCP — a 401, like Home Assistant's."""

    def __init__(self, app: Any, token: str) -> None:
        self.app, self.token = app, token.encode()

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] == "http":
            given = dict(scope["headers"]).get(b"authorization", b"")
            if not hmac.compare_digest(given, b"Bearer " + self.token):
                body = json.dumps({"message": "401: Unauthorized"}).encode()
                await send({"type": "http.response.start", "status": 401, "headers": [
                    (b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]})  # fmt: skip
                await send({"type": "http.response.body", "body": body})
                return
        await self.app(scope, receive, send)


if __name__ == "__main__":
    import uvicorn

    token = os.environ.get("HA_DOUBLE_TOKEN")
    if not token:
        sys.exit(
            "set HA_DOUBLE_TOKEN: the double refuses to run without a bearer token"
        )
    uvicorn.run(
        BearerOnly(server.streamable_http_app(), token),
        host="127.0.0.1", port=int(sys.argv[1]), log_level="warning",
    )  # fmt: skip
