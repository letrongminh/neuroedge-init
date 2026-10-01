# 07 · Data contracts

> **Scope:** every file format and wire format that components exchange, how they are versioned, and
> which ones are frozen. **Sources:** `schemas/`, `python/neuroedge/engine/`,
> `models/providers/config.py`, `perception/providers/config.py`, `sim/session.py`, `actions/tools.py`,
> `testing/uart.py`, `docs/spec/tool_calling.md`, `docs/spec/simulation_coverage.md` §4, PRD Appendices B–C.

## 1. Contract map

| Contract | Form | Who writes | Who reads | Checked by | Frozen | Status |
|:---|:---|:---|:---|:---|:---|:---:|
| **Gate** `gate.v1` | YAML | gate author | resolver | `schemas/gate.v1.json` + **resolution** (`gate lint`) | yes — RFC (`CONTRIBUTING.md` §3) | `done` |
| **Trace** `trace.v1` | JSON | `EventLog`, `TraceRecorder`, UART | player, golden, `trace view` | `schemas/trace.v1.json` | envelope: yes; event catalog: no | `done` |
| **Board** `board.v1` | TOML | OEM, core team | build, HAL | `schemas/board.v1.json` | yes | `done` |
| **Agent** `agent.toml` | TOML | agent author | build, session | each table has its own parser | no (normative in code) | `done` |
| **Grammar** `commands.toml` | TOML | agent author | `CommandGrammar` | parser | no | `done` |
| **Knowledge** `knowledge.toml` | TOML | agent author | `KnowledgeBase` | parser | no | `done` |
| **Tool call** | object / JSON | orchestrator, LLM, MCP client | `dispatch()` | `input_schema` generated from the signature | no — Gated Tool Profile v0 (`TODOS.md` #23) | `done` |
| **Device tree** `NETR` v1 | binary | `binary_tree.encode` | C walker | `ne_tree_load` (magic, version, CRC, limits) | yes — RFC-0003 | `done` |
| **UART stream** | text | firmware | `testing/uart.py`, CI scripts | parser, `^`-anchored regex | normative in `simulation_coverage.md` §4 | `done` |
| **Manifest** `manifest.v1` (`schemas/manifest.v1.json`, TSK-K3-03) | JSON | agent / gate packager | Gate Registry | JSON Schema | planned yes — → [`15`](15-target-architecture.md) §3.2 | `planned` |
| **Opus/JSON WebSocket frame** (and SLIP on UART if needed — PRD Appendix D.2) | binary / JSON | firmware (`provider_client.c`, TSK-S5-06) | provider layer / cloud provider | not specified yet | normative in PRD Appendix D.2 — → [`15`](15-target-architecture.md) §2.3 | `planned` |
| **Black-channel wire and multi-node trace** (`metadata.nodes[]`, `data.node_id`, Q-32) | Zenoh-pico (intent encoding unselected) / JSON | coordinating Pi, MCU node | MCU node, TracePlayer | RFC-node; optional field, no changes to `schemas/` (TSK-W3-04) | via RFC — → [`15`](15-target-architecture.md) §4.3 | `planned` |
| **`agent.toml` extension tables (`[lab]`, `[nodes]`)** | TOML | agent author | `agent.toml` parser | config parser (TSK-N1-02, RFC-node draft) | no — → [`15`](15-target-architecture.md) §4.2, §4.3 | `planned` |

## 2. Gate — `gate.v1`

A real gate in the repository, level 2 of the three-level chain:

```yaml
schema:  neuroedge.gate/v1
name:    unlock_door
version: 1.2.0
extends: neuroedge://gates/hospitality/base-access@1.0.0

evaluate:
  room_matches:
    type: bool
    instructions: "Số phòng yêu cầu trùng khớp hoàn toàn với hồ sơ đặt phòng của khách"

allow_when:
  room_matches: true
  risk_level:   { lte: low }    # siết chặt: medium → low

on_block:
  action:  escalate
  to:      human_receptionist
  message: "Yêu cầu cần được nhân viên lễ tân xác nhận trực tiếp trước khi mở khóa."

budget:
  p95_latency_ms: 120
  fail:           closed
```

| Field | Constraint |
|:---|:---|
| `schema`, `name`, `version` | Always required. `name` matches `^[a-z0-9_-]+$`; `version` is SemVer 2.0 |
| `extends` | `neuroedge://gates/<path>@MAJOR.MINOR.PATCH`. A root gate (no `extends`) must declare all of `evaluate`, `allow_when`, `on_block`, `budget` (RFC-0001) |
| `evaluate.<criterion>` | `type` ∈ `bool`, `level` (needs `levels`, ordered low to high), `choice` (needs `options`); `instructions` non-empty |
| `arguments.<parameter>` (RFC-0005) | `type` ∈ `string`, `integer`, `number`, `boolean`; optional `minimum`, `maximum`, `enum`, `max_length` |
| `allow_when` | Each clause is one operator on a declared criterion; operators by type in [`05`](05-code-gate-hal-c4l4.md) §2. The CEL string form is rejected today |
| `on_block.action` | `deny` · `escalate` (needs `to`) · `ask` (needs `message`, optional `confirms`) · `degrade` (needs `fallback_action`) |
| `budget` | `p95_latency_ms` ≥ 1; `fail` ∈ `closed` (default) · `open` |

The schema alone is not enough to conclude a gate is safe — principle 2 is a statement about **two**
documents, while JSON Schema sees only one. The checking gate is `neuroedge gate lint` (invariant 1).
Every `allow_when` change is a breaking change and needs a MAJOR bump.

## 3. Agent — `agent.toml`

Each table has its own parser; the code does not reject unknown top-level tables, but provider tables
reject unknown keys. Command syntax uses these tables: `CHANGELOG.md` §2.3.

| Table | Parser | Main keys and rules |
|:---|:---|:---|
| `[agent]` | `compiler.load_agent_manifest` | `name`, `version` (required; on `esp32s3` must be `MAJOR.MINOR.PATCH`), `language` (exactly 2 lowercase letters) |
| `[requires]` | `compiler.check_capabilities` | Keys are dotted primitives (`"digital.out"`…); `pins`, `sensors`, `sample_rate_hz`, `aec`, `min_width`… must exist on the board |
| `[gates]` | `compiler.resolve_gates` | `key = "neuroedge://…"` or a relative path; each `@action(gate=…)` must point to a key. On `esp32s3` keys must be C identifiers |
| `[targets]` | `compiler` | `supported = [...]` |
| `[sim.facts]`, `[sim.slot_facts]` | `sim/session.py` | Fixed facts of the session; facts taken from the command slot |
| `[sim.sensors]`, `[sim.sensor_facts]` | `sim/session.py` | Simulated readings; turning readings into facts: `equals`, `gte`/`lte`, or `bands` (increasing bands, the last band is the highest level of the gate); numeric rules need a unit |
| `[system_two]` | `models/providers/config.py` | `provider` (`litellm` or `python:…`), `model`, `api_key_env`, `api_base`, `timeout_s` (≤ 120), `max_tokens`, `temperature`, `options` |
| `[system_one]` | as above | `provider` (`systemone` or `python:…`), `model`, `criteria` (non-empty, no `call_source`), `threshold` [0.5; 1], `timeout_ms` (≤ 10 000, and plus 50 ms of headroom must be ≤ the gate's `p95`) |
| `[stt]`, `[stt.fallback]`, `[tts]` | `perception/providers/config.py` | `provider` (`openai` or `python:…`), `base_url`, `model`, `voice` (TTS), `language` (STT), `timeout_s`, `api_key_env`; `[stt]` needs `audio.in`, `[tts]` needs `audio.out` |
| `[wake_word]` | as above | `provider` (`openwakeword` or `python:…`), three model files `model`, `melspectrogram`, `embedding` (the user's), `word`, `threshold`; rejected on `esp32s3` |
| `[mcp]`, `[mcp.servers.<name>]` | `mcp_host.load_mcp_config` | `max_rounds` (1–16); each server: `command`, `tools` (allowlist, required), `args`, `env`, `timeout_s` |
| `[lab]` | `brain/` (TSK-N1-02, planned) | `enabled` flag, default false; when false, lab tools are not registered; `build --release` rejects when enabled (TSK-N1-03) — → [`15`](15-target-architecture.md) §4.2 |
| `[nodes]` | RFC-node (proposed) | MCU node configuration for layered robots; shape not finalized (open question 3 of draft RFC-node) — → [`15`](15-target-architecture.md) §4.3 |

**Common rule for all provider tables** (`models/providers/common.py`): fields named like keys
(`api_key`, `token`, `secret`…) are rejected; values that look like keys are rejected and never printed
back; endpoints must not carry credentials, query or fragment; `http://` to another machine with a key
is rejected, and for `[system_one]` `http://` to another machine is rejected in all cases.

## 4. Board — `board.v1`

| Part | Content |
|:---|:---|
| `[board]` | `id`, `target` (`sim` · `linux` · `esp32s3`), `mcu`, `name` |
| `[capabilities.audio_in]` | `channels`, `sample_rate_hz`, `aec`, `vad` |
| `[capabilities.audio_out]` | `channels`, `sample_rate_hz` |
| `[capabilities.digital_out]` | `pins` (logical names), `backend` |
| `[capabilities.sensor_read]` | `sensors` |
| `[capabilities.display]` | `width`, `height`, `color` |

The five core primitives are a closed set for v1.x (FR-HAL-01); new primitives only via RFC, and the four board-optional extension packs (FR-HAL-08, Q-53) enter v1.0 at I2a and I3a: RFC-0007 (`digital.in`, read-only I2C, `analog.in`), RFC-0009 (`numeric` criterion), RFC-0010 (PWM), RFC-0011 (`motion.*`), RFC-0012 (`vision.in`), RFC-0013 (board-optional). Today there are exactly three tier-1 profiles (Q-53 adds `sim-rpi5` and an ESP32-S3 camera board): `sim-default` (copies Box-3 exactly, never richer — invariant 7), `linux-rpi5` (`aec = false` until measured), `esp32s3-box-3`. Application code uses only pin **names**; GPIO numbers belong to the HAL.

## 5. Grammar and knowledge

```toml
# commands.toml
[grammar]
version   = 1
threshold = 0.80

[[command]]
intent    = "unlock"
patterns  = ["mở cửa phòng {room}", "mở cửa"]
tool      = "unlock_door"
arguments = { guest_id = "room" }
```

Each command does exactly one thing: call one `tool`, say a fixed sentence (`say`), or hand off to
System 2 (`ask`, with `offline_say`). Matching: normalization (NFC, lowercase, punctuation stripped,
Vietnamese diacritics kept), an exact pattern match scores 1.0, otherwise a `difflib` ratio against
`threshold` is used. `knowledge.toml` is a set of `questions` → `answer` entries, which become
`ask = "knowledge"` commands; the trace stores only the `id` and score of the retrieved entry.

## 6. Tool call and result

```text
ToolCall   { id, name, arguments, source }        source ∈ local_grammar · system_one · system_two · mcp · test
ToolResult { tool, status, … }                    status ∈ ALLOW · BLOCK · REJECTED
```

| `status` | Meaning | Pin | MCP `isError` |
|:---|:---|:---|:---|
| `ALLOW` | Gate allows, the function body ran | may change | false |
| `BLOCK` | Gate blocks (every `on_block`) | unchanged, except the pins of a `degrade` fallback if its own gate allows | false |
| `REJECTED` | Unknown tool or bad argument; no verdict | unchanged | true |

Empty `id`s are assigned `call_1`, `call_2`… per session. `source` is assigned by the runtime from the
connection, not declared by the caller. On `BLOCK`, the result carries `gate`, `reason`,
`failed_criterion`, `on_block`, `message`, `escalated_to`, and possibly `fallback` or
`confirmation {id, message, expires_in_ms, who}`. Full normative spec:
[`docs/spec/tool_calling.md`](../../spec/tool_calling.md).

## 7. Trace — `trace.v1`

```json
{ "$schema": "https://schema.neuroedge.dev/trace/v1.json",
  "metadata": { "session_id": "sess_…", "timestamp_utc": "…", "target": "sim",
                "board_id": "sim-default", "agent_version": "home-voice@0.1.0" },
  "events": [ { "offset_ms": 0, "type": "text_input", "data": { "text": "bật đèn" } } ] }
```

Frozen envelope: `metadata` requires five fields (and accepts other fields), each event has exactly
`offset_ms`, `type`, `data`. `type` is a **free string**, so adding an event kind needs no RFC. NaN and
infinity are rejected on read and written as strings.

Events by role in replay:

| Role | Events | During replay |
|:---|:---|:---|
| **Input** | `text_input`, `audio_in_*`, `wake_word_detected`, `stt_result`, `stt_unavailable`, `sensor_read`, `sensor_set`, `sensor_unavailable`, `intent_extracted` | fed in again |
| **Decision** | `gate_evaluation_begin`, `gate_facts`, `gate_evaluation_result`, `argument_out_of_range`, `actuator_command`, `actuator_aborted`, `actuator_command_rejected` | recomputed and compared against golden |
| **Orchestration** | `tool_call`, `tool_call_rejected`, `tool_confirm_*`, `action_requested`, `fallback_skipped`, `voice_state_changed`, `voice_reprompt`, `voice_late_result_dropped`, `stt_fallback` | recorded, not compared |
| **Output** | `tts_stream_start`, `tts_stream_end`, `tts_unavailable`, `display_frame` (digest only), `knowledge_retrieved` | not compared |
| **Measurement** | `system_one_call`, `system_one_fallback`, `system_two_call`, `system_two_unavailable`, `circuit_breaker`, `mcp_tool_result`, `turn_latency`, `session_summary` | skipped |
| **Device-only** | `device_info`, `trace_end` | UART session frame |

`session_summary` is never recorded during a session: `EventLog.to_trace()` computes and appends it on
export. By default, a trace hashes `text`, `utterance`, `transcript` at the source and carries
`metadata.anonymized = true`; `--raw` keeps it verbatim, and that trace carries `metadata.anonymized = false`
(NFR-PRIV-03). The three normative traces
(`fixtures/traces/happy-path.json`, `unverified_attempt.json`, `network_offline.json`) are frozen by RFC;
RFC-0008 adds `gate_digest` — the digest of the gate that decided each verdict — to every
`gate_evaluation_begin` they carry.

## 8. UART format

```text
NE1 {"offset_ms":0,"type":"device_info","data":{"board_id":"esp32s3-box-3","agent_version":"home-voice@0.1.0","device_id":"qemu","boot_id":"9f2c01aa"}}
NE1 {"offset_ms":3,"type":"gate_evaluation_begin","data":{"gate":"light_on@1.0.0","gate_digest":"sha256:4cc8…"}}
NE1 {"offset_ms":9,"type":"gate_evaluation_result","data":{"verdict":"ALLOW","evaluations":{"call_source":"local_grammar"}}}
NE1 {"offset_ms":57,"type":"trace_end","data":{"events":4}}
NE_SELFTEST PASS walker=26 token=11
NE_TRACE DONE sessions=4
```

- The `NE1 ` line starts at column 0, followed by a JSON object with **exactly** three keys; ≤ 512 bytes
  including the prefix. A line that does not fit is dropped whole but still counted.
- Each session opens with `device_info` at offset 0 and closes with `trace_end {events: N}`; N counts
  every line of the session. The host rejects (`NE4001`, pointing out `source:line`) a line that is not
  JSON, extra keys, an event before `device_info`, a restart mid-session, a count mismatch, an unclosed
  session.
- Other lines: `NE_SELFTEST PASS|FAIL`, `NE_TRACE DONE`, `NEUROEDGE_HEAP_JSON {…}`,
  `NEUROEDGE_MEMORY_JSON {…}`, and `NE_OTA <event> …` — the list and meanings are in
  [`docs/user/nap-firmware.md`](../../user/nap-firmware.md) §6.4; each line's format is defined by
  `components/ne_ota/src/ne_ota_policy.c`.

## 9. Two-way closed corpus

Each file has exactly one expected entry and each entry exactly one file; the test enforces both
directions.

| Corpus | Files | Expected |
|:---|:---|:---|
| Gate counterexamples | `fixtures/gates/invalid/*.yaml` (and `valid/`, `registry/` must resolve) | `fixtures/gates/expected_errors.yaml`: error class, code, principle, substring of location and reason |
| Trace counterexamples | `fixtures/traces/invalid/*.json` | `fixtures/traces/expected_errors.yaml` |
| Tool call | `fixtures/tool_calls/{valid,invalid}/*.yaml` | `fixtures/tool_calls/expected_results.yaml`: status, pin commands, reason… |
| Voice state machine | `fixtures/compliance/voice/*.json` | `fixtures/compliance/voice/expected_results.yaml`: full event list, exact offsets |
| Tree truth tables | `fixtures/decision_trees/*.truth.json` | the file itself; the C walker must match every line |

## 10. Versions, identifiers, digests

| Object | Convention |
|:---|:---|
| Agent | `<name>@<semver>` |
| Gate file | `<name>@<semver>.yaml` |
| Gate in registry | `neuroedge://gates/<group>/<name>@<semver>` → `<gates>/<group>/<name>@<semver>.yaml` |
| Session | `sess_<hex>` |
| Public schema | `https://schema.neuroedge.dev/<kind>/v<n>.json` (served from I6) |
| Digest | `"sha256:" + SHA-256(JCS RFC 8785)` |

**Frozen means** a change needs an RFC and CI enforcement: three schemas (file set, `$id`, valid
metaschema); gates in `digests.lock`; three normative traces; the `NETR` v1 layout. Not frozen: the
internal JSON tree, the Gated Tool Profile (v0), the trace event catalog.

## 11. Error codes

Every error has three parts: **where · why · what to do** (FR-DX-04). Code families (PRD Appendix B is
the source):

| Family | Meaning | Examples |
|:---|:---|:---|
| `NE1xxx` | Runtime action contract | `NE1001` call outside `c.do()`, wrong token · `NE1002` token reused, expired |
| `NE2xxx` | Gate at build time, lint, resolution | `NE2001` not found · `NE2002` bad schema or limit · `NE2003` inheritance violation |
| `NE3xxx` | Build | `NE3001` board missing capability · `NE3002` bad `agent.toml` · `NE3003` collects all issues, writes nothing |
| `NE4xxx` | Traces, replay, verify | `NE4001` bad trace or UART frame · `NE4002` safety regression · `NE4003` cannot replay or old firmware · `NE4004` scanned 0 artifacts |
| `NE5xxx` | Perception | `NE5001` grammar, knowledge or fallback missing or wrong |

A block caused by a deadline overrun or an unavailable fact source is **not an error**: it is a `BLOCK`
verdict with `budget_exceeded` or `gate_unreachable`.
