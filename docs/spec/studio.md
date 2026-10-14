# `neuroedge studio` — local web application for all capabilities on a laptop

**Trạng thái:** spec for TSK-I1-04 (Q-51). Approved layout: [`wireframe/studio-v1.html`](../../wireframe/studio-v1.html).
This is the **contract** between the server (`python/neuroedge/studio/`) and the page (`python/neuroedge/studio/assets/`): routes,
JSON shapes, safety rules. Code that changes the contract must update this file in the same PR.

## 1. Command

```bash
neuroedge studio [--agent agent.toml] [--port 8765] [--no-browser] [--mic [--half-duplex]]
```

- Target `sim` only (the page displays the simulated device). Default agent is as in `run`.
- `--mic`: laptop microphone listening session right from the start (TSK-I4-04, Q-50); the microphone button on the page only **mutes/unmutes** the microphone
  (replaces frames with silence), without opening/closing the device. Without `--mic`, the voice screen explains how to enable it.
- Ctrl-C ⇒ exit code 0, closes microphone/speaker.

## 2. Non-negotiable rules

1. **127.0.0.1 only.** Never bind to any other address. **All** requests (GET included) must have a `Host` header of `127.0.0.1:<port>` or `localhost:<port>`, otherwise 403 — blocks DNS rebinding from reading `/state`, `/events`, traces.
2. **All POSTs come from this page** (`_Handler._post_refusal`): an `Origin` strictly matching `http://127.0.0.1:<port>` / `http://localhost:<port>` (a missing `Origin` is refused) **and** the header `X-NeuroEdge-UI-Key` equal to this run's key, which the terminal prints only after `#` in the URL (DP-A-02, `deployment_profiles.md`); refusals ⇒ 403 and `ui_auth_refused`; body ≤ 4096 bytes, `Content-Length` that is not a non-negative integer ⇒ 400. `lint`/`test`/`verify`/`build` run **one run at a time**; subprocess output masks environment variable values whose names look like keys.
3. **No external assets:** CSS/JS embedded in the page; no CDN, no web fonts, no `url(`, no `@import`.
   Images only from same-origin paths (`/api/device/golden/…`).
4. **Text from agent, trace, model is always set via `textContent`**, never `innerHTML`.
5. **Never return key values.** Provider only has `key_env` (variable name) and `key_present` (bool).
6. **Read filesystem only within the agent's directory** (traces, build) and, when running in a repository checkout,
   existing outputs of `demo/i3-firmware-qemu/run.sh`. Filenames from URLs must pass a whitelist, no `..`.
7. **Dual-language:** all page labels in `I18N.vi` and `I18N.en`; product terms kept as-is (gate, ALLOW, BLOCK,
   MCP, System 1/2, OTA, trace). Server returns data, not labels.
8. An API error is JSON `{"ok": false, "error": {"code"?, "where"?, "why", "how"?}}` (`NeuroEdgeError.as_dict()` format),
   HTTP 200 for business domain errors, 400 for malformed requests, 404 for unknown routes, 501 for unimplemented APIs.

## 3. Routes preserved from sim page

`GET /events` (SSE), `GET /state`, `POST /command`, `POST /confirm` — exactly as in `python/neuroedge/sim/ui.py`.
`GET /` returns the studio page (not the sim page).

## 4. New APIs

All successful responses have `"ok": true`.

`<name>` of a trace is a relative path to `traces/`, omitting `.json`, replacing `/` with `@` (`incidents/door.json` ⇒ `incidents@door`) to match route pattern. Names are matched only against the directory-derived whitelist, never concatenated directly into paths; files whose names do not match the pattern or duplicate existing names are not listed.

| Method, route | Returns | Module |
|:---|:---|:---|
| `GET /api/agent` | `{label, root, requires: {primitive: {...}}, targets: [..], board: {id, capabilities}, providers: [{role, label, key_env, key_present}], templates: [..]}` — `role` ∈ `stt`, `stt.fallback`, `tts`, `system_one`, `system_two`, `wake_word` | `api_agent` |
| `GET /api/gates` | `{gates: [{name, version, ref, digest, levels, fail, status: "OK"\|"FAIL", error?}], lint: {resolved, total}}` — gates in `[gates]` of the agent | `api_agent` |
| `GET /api/gates/<name>` | `{name, version, chain: ["base@1.0.0", …], evaluate: {criterion: {type, levels?, options?, instructions?}}, allow_when: {...}, on_block: {...}, budget: {...}, explanation: {...}}` — `explanation` from `engine/gate_explain.py` | `api_agent` |
| `POST /api/gates/<name>/whatif` body `{"facts": {criterion: value}}` | `{verdict: "ALLOW"\|"BLOCK", reason?, failed_criterion?, evaluations, action?}` — pure evaluation, **no** session, HAL, or ledger side-effects | `api_agent` |
| `GET /api/mcp` | `{tools: [{name, description, input_schema}], desktop_config: "<command + JSON>" \| null, desktop_config_error?, servers: [{name, tools}]}` — missing MCP SDK (`neuroedge[mcp]`) still includes `tools`, with `desktop_config` as null along with error | `api_agent` |
| `GET /api/traces` | `{traces: [{name, valid, session_id, events, target, board, anonymized, recorded_at, error?}]}` — `*.json` under `<agent>/traces/` including subdirectories (excluding `golden/`); files failing validation are still listed with `valid: false`, `error`, and remaining fields `null` | `api_checks` |
| `GET /api/traces/<name>` | `{ok: true, $schema, metadata, events}` — full `trace.v1` trace, flattened alongside `ok` | `api_checks` |
| `POST /api/traces/<name>/replay` | `{match: bool, verdicts: [...], pins: [...], detail?}` — same as `neuroedge replay` on `sim` | `api_checks` |
| `POST /api/record` | `{name, events}` — records the current session into `<agent>/traces/` (hashed text, like `record`) | `api_checks` |
| `POST /api/lint` | `{resolved, total, gates: [...]}` — same as `gate lint gates` in the agent directory; if agent lacks its own `gates/`, uses the repository's `gates/` (where `neuroedge://` references resolve) | `api_checks` |
| `POST /api/verify` | `{passed: bool, summary: "<Passed:/Failed: line>", compared: "decisions only — not timing", matrix: [{item, sim, linux, esp32s3}]}` — `sim` runs live locally; `linux`/`esp32s3` is `{"source": "ci", "job": "linux-hal"\|"uart-trace"}` | `api_checks` |
| `POST /api/test` | `{passed, failed, output_tail}` — `neuroedge test` in the agent directory, subprocess, 120 s timeout; `output_tail` is the last 20 lines | `api_checks` |
| `GET /api/device` | `{firmware: {built: bool, dir?, files?}, screens: [{name, langs: ["vi","en"]}], golden: {checked?: "66/66"}, qemu: {selftest?, trace_done?, log?} \| null, ota: {phases: [{phase, markers: [..], ok}]} \| null, hint}` | `api_device` |
| `POST /api/device/build` | `{built, dir, files, checked}` — same as `build --target esp32s3 --board esp32s3-box-3` (generates ESP-IDF project, does not compile) | `api_device` |
| `GET /api/device/golden/<lang>/<name>.png` | PNG image (`image/png`); `lang` ∈ `vi`,`en`; `name` must exist in `screens` | `api_device` |
| `GET /api/voice` | `{enabled, running, muted, half_duplex, state, counters: {turns, barge_in, stt_unavailable, cancelled}, devices: {input, output}, error?}` (`error`: only present when voice session stopped due to device error, 3-part shape) | `voice` |
| `POST /api/voice/mute` body `{"muted": bool}` | same as `GET /api/voice` | `voice` |

## 5. Screens and data sources

| Screen (wireframe) | Data |
|:---|:---|
| Live session | `/events` (SSE) + `/command`, `/confirm`; `/api/voice`; verdict explanation built from `gate_evaluation_result`, `gate_facts`, and `/api/gates/<name>` |
| Gate | `/api/gates`, `/api/gates/<name>`, `/api/gates/<name>/whatif`, `/api/lint` |
| Trace | `/api/traces`, `/api/traces/<name>`, `…/replay`, `/api/record` |
| Verification | `/api/verify`, `/api/lint`, `/api/test` |
| ESP32-S3 device | `/api/device`, `/api/device/build`, `/api/device/golden/…` |
| MCP & integrations | `/api/mcp` + `tool_call` events with `source: mcp` |
| Agent & configuration | `/api/agent` |
