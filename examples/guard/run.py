"""Gates one action with `neuroedge.guard` — no agent.toml, no @action, no SimSession."""

import asyncio
import json
import sys
from pathlib import Path

from neuroedge.guard import Guard
from neuroedge.sdk import ToolRequest


async def main(out: str | None = None) -> None:
    async with Guard.load(Path(__file__).with_name("guard.toml")) as guard:
        bridge = guard.dispatcher("ros_node")  # every call below is "bridge:ros_node"
        refused = await bridge.dispatch(ToolRequest("lamp_on", {"seconds": 3}))
        guard.set_fact("badge_ok", True)
        allowed = await bridge.dispatch(ToolRequest("lamp_on", {"seconds": 3}))
        print(refused.status, allowed.status)  # BLOCK ALLOW
        if out:
            Path(out).write_text(json.dumps(guard.trace(), indent=2), encoding="utf-8")


asyncio.run(main(*sys.argv[1:2]))
