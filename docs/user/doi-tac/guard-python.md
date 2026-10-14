# Guide 2 — `neuroedge.guard` in a Python agent

> **Goal:** your Python agent (an LLM loop, a ROS node, a smart home script) touches devices **only through a `Guard`**: every
> call passes through a gate first, and the device function executes **only after the gate allows it**. **Duration:** ≤ 15 minutes from wheel installation.
>
> This guide requires no physical devices, Home Assistant, or network access: the device is modeled as a Python function. All command blocks here are
> executed from the wheel by [`scripts/partner_guides_check.sh`](../../../scripts/partner_guides_check.sh). For full syntax of `guard.toml` and `Tool`:
> [`docs/spec/extension_sdk.md`](../../spec/extension_sdk.md) §1–§3; limitations: [`gioi-han.md`](gioi-han.md).

## 0. Prerequisites

Install the wheel according to the [README](README.md). Work inside an empty directory. No environment variables need to be set.

## 1. Three commands to initial value

**Command 1 — write the gate.** The gate defines the conditions for a call to pass: here, the host application must confirm `badge_ok`, and `seconds` must fall within 1–60.

<!-- guide: run -->
```bash
mkdir -p gates && cat > gates/plug_on@1.0.0.yaml <<'YAML'
schema:  neuroedge.gate/v1
name:    plug_on
version: 1.0.0

arguments:
  seconds: { type: integer, minimum: 1, maximum: 60 }

evaluate:
  badge_ok:
    type: bool
    instructions: "Chương trình chủ đã xác thực người ra lệnh"

allow_when:
  badge_ok: true

on_block:
  action: deny

budget:
  p95_latency_ms: 150
  fail:           closed
YAML
```

**Command 2 — write the agent.** `run` is the only function touching the device; `Guard` invokes it only after ALLOW. `dispatcher("agent")` provides the caller with a port sourced as `bridge:agent`:
the caller **cannot** self-declare its source, and `ToolRequest` has no `source` field.

<!-- guide: run -->
```bash
cat > agent.py <<'PY'
import asyncio
import json

from neuroedge.guard import Guard, Tool
from neuroedge.sdk import ToolRequest

ran = []  # what the real device was actually asked


def plug_on(seconds):
    ran.append(seconds)  # <- here you call the real device (HTTP, serial, …); runs only after ALLOW


tool = Tool(
    "plug_on",
    "gates/plug_on@1.0.0.yaml",
    parameters={"seconds": {"type": "integer", "default": 5}},
    run=plug_on,
)


async def main():
    async with Guard([tool], name="my-agent") as guard:
        bridge = guard.dispatcher("agent")
        first = await bridge.dispatch(ToolRequest("plug_on", {"seconds": 5}))
        guard.set_fact("badge_ok", True)  # host program confirms: this is YOUR decision
        second = await bridge.dispatch(ToolRequest("plug_on", {"seconds": 5}))
        third = await bridge.dispatch(ToolRequest("plug_on", {"seconds": 600}))
        for outcome in (first, second, third):
            print(outcome.status, outcome.content.get("reason", ""))
        print("device was asked:", ran)
        with open("trace.json", "w") as out:
            json.dump(guard.trace(), out, indent=2)


asyncio.run(main())
PY
```

**Command 3 — run.**

<!-- guide: run expect="BLOCK criterion_unavailable" expect="ALLOW " expect="BLOCK argument_out_of_range" expect="device was asked: [5]" -->
```bash
python agent.py
```

Read the three output lines:

1. `BLOCK criterion_unavailable` — no component provided `badge_ok`, so the gate blocks: **the device was never asked**.
2. `ALLOW` — after `guard.set_fact("badge_ok", True)` the gate permits the call and `plug_on` runs.
3. `BLOCK argument_out_of_range` — `seconds = 600` exceeds the gate limit of 60: blocked even though `badge_ok` was true.

And `device was asked: [5]`: the device function executed **exactly once**, for the permitted call.

## 2. BLOCK then ALLOW — intentionally opening a gate

In this guide, "opening a gate" means your program sets a fact (`set_fact`) — the decision resides entirely in your code, not in the LLM: an LLM only sends `ToolRequest` and cannot invoke `set_fact`
unless you provide it. Two principles to remember:

- Do not expose `guard` to the LLM or to bridges. Expose only one thing: `dispatcher(...)`.
- `Outcome` contains only `status` and `content` (reasons, failing criteria, fallback actions). It **does not** return values produced by `run` — by design, preventing callers from extracting
  data through this channel. If your application needs device results, store them where your code reads them (like `ran` above).

To configure via file instead of code: `Guard.load("guard.toml")` — runnable examples in [`examples/guard/`](../../../examples/guard/).

## 3. Inspecting traces

<!-- guide: run expect="VALID" -->
```bash
neuroedge trace validate trace.json
```

<!-- guide: run expect="gate_evaluation_result" expect="guard:my-agent@" expect="bridge:agent" -->
```bash
neuroedge trace show trace.json
```

The trace contains three calls, the `bridge:agent` source, each verdict, and its rationale. It includes the call **parameters** (unhashed). Replay a `Guard` trace using
`TracePlayer(trace, guard="guard.toml")` (requires `guard.toml`; see `extension_sdk.md` §1).

## 4. Making `Guard` the sole path

`plugin doctor` does **not** apply here (it parses `[proxy.*]` in `guard.toml`). With an in-process `Guard`, "sole path" relies on your code discipline:

- Devices must only be touched inside the `run` callback of a `Tool`. A `requests.post(...)` placed elsewhere in the agent is a bypass undetected by any tool of ours.
- `Guard` does not intercept OS-level networking and does not isolate against same-process code (threat model: [`threat_model.md`](../../spec/threat_model.md) §3). If a device accepts commands from another host, that command bypasses the gate.
- If the device exposes a network API, isolate it behind a firewall so only the agent host can reach it; we cannot do this for you.

## 5. Lỗi thường gặp (real messages)

**Invalid bridge ID** — only `[a-z][a-z0-9_]{0,31}`:

<!-- guide: run exit=1 expect="'Bad-Id' is not a bridge id" expect="use [a-z][a-z0-9_]{0,31}" -->
```bash
python - <<'PY'
from neuroedge.guard import Guard, Tool

Guard([Tool("plug_on", "gates/plug_on@1.0.0.yaml")]).dispatcher("Bad-Id")
PY
```

**Two bridges with identical IDs** — ID represents identity in traces and cannot be shared:

<!-- guide: run exit=1 expect="'bridge:agent' is already registered" -->
```bash
python - <<'PY'
from neuroedge.guard import Guard, Tool

guard = Guard([Tool("plug_on", "gates/plug_on@1.0.0.yaml")])
guard.dispatcher("agent")
guard.dispatcher("agent")
PY
```

**Gate file not found** — paths are evaluated relative to your current working directory (or relative to `base=` / directory containing `guard.toml`):

<!-- guide: run exit=1 expect="GateNotFoundError" expect="file does not exist" -->
```bash
python - <<'PY'
from neuroedge.guard import Guard, Tool

Guard([Tool("plug_on", "gates/khong-co.yaml")])
PY
```

**Tool requires pins but `Guard` has no board** — `requires` is only permitted when declaring `board=`; for simplicity, your device is a `run` function:

<!-- guide: run exit=1 expect="BoardCapabilityError" expect="this Guard has no board" -->
```bash
python - <<'PY'
from neuroedge.guard import Guard, Tool

Guard([Tool("plug_on", "gates/plug_on@1.0.0.yaml", requires=("digital.out:porch_light",))])
PY
```

**Unknown tool name or parameters** — does not raise an exception; returns `REJECTED` (and nothing executes):

<!-- guide: run expect="REJECTED" expect="no tool named 'khong_co'" expect="unknown argument 'la'" -->
```bash
python - <<'PY'
import asyncio

from neuroedge.guard import Guard, Tool
from neuroedge.sdk import ToolRequest


async def main():
    guard = Guard([Tool("plug_on", "gates/plug_on@1.0.0.yaml")])
    bridge = guard.dispatcher("agent")
    print((await bridge.dispatch(ToolRequest("khong_co", {}))).content)
    print((await bridge.dispatch(ToolRequest("plug_on", {"la": 1}))).content)


asyncio.run(main())
PY
```

**`run` accepts parameters differing from declared manifest** — `Tool` checks during initialization (`AgentManifestError`, "does not accept"): accurately declare the function's `parameters`.

## 6. Next steps

Submit feedback via [`phan-hoi.md`](phan-hoi.md). The other two guides: [`home-assistant-mcp.md`](home-assistant-mcp.md), [`proxy-http.md`](proxy-http.md).
