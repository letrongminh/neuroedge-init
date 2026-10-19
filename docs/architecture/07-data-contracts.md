# 07 · Data Contracts

> **Scope:** all file and wire formats exchanged between components, how they
> are versioned, and which are frozen. **Sources:** `schemas/`, `python/neuroedge/engine/`,
> `models/providers/config.py`, `perception/providers/config.py`, `sim/session.py`, `actions/tools.py`,
> `testing/uart.py`, `docs/spec/tool_calling.md`, `docs/spec/simulation_coverage.md` §4, PRD Appendices B–C.

## 1. Contract Map

| Contract | Format | Writer | Reader | Verified By | Frozen | Status |
|:---|:---|:---|:---|:---|:---|:---:|
| **Gate** `gate.v1` | YAML | gate author | resolver | `schemas/gate.v1.json` + **resolution** (`gate lint`) | yes — RFC (`CONTRIBUTING.md` §3) | `done` |
| **Trace** `trace.v1` | JSON | `EventLog`, `TraceRecorder`, UART | player, golden, `trace view` | `schemas/trace.v1.json` | envelope: yes; event catalog: no | `done` |
| **Board** `board.v1` | TOML | OEM, core team | build, HAL | `schemas/board.v1.json` | yes | `done` |
| **Agent** `agent.toml` | TOML | agent author | build, session | each table has its own parser | no (normative in code) | `done` |
| **Grammar** `commands.toml` | TOML | agent author | `CommandGrammar` | parser | no | `done` |
| **Knowledge** `knowledge.toml` | TOML | agent author | `KnowledgeBase` | parser | no | `done` |
| **Tool call** `tool-call.v1` | object / JSON | dispatcher, LLM, MCP client | `dispatch()` | `schemas/tool-call.v1.json` (envelope, tool description); `input_schema` generated from signature | yes — RFC-0015 | `done` |
| **Tool result** `tool-result.v1` | JSON | `dispatch()` | LLM, MCP client (`outputSchema`) | `schemas/tool-result.v1.json` | yes — RFC-0015 | `done` |
| **Error** `error.v1` · **code catalog** `error-codes.v1` | JSON | `NeuroEdgeError.as_dict()` · catalog file | Studio, `sim` page, integrator SDK | `schemas/error.v1.json`, `schemas/error-codes.v1.json` | yes — RFC-0015 | `done` |
| **Device tree** `NETR` v1 | binary | `binary_tree.encode` | C walker | `ne_tree_load` (magic, version, CRC, limits) | yes — RFC-0003 | `done` |
| **UART lines** | text | firmware | `testing/uart.py`, CI scripts | parser, anchored regex `^` | normative in `simulation_coverage.md` §4 | `done` |
| **Mission contract** `mission.v1` (`planned · Q-72`, I2d) | YAML (Q-87(3)) | LLM worker (draft), mission compiler | runtime | schema + compiler (contradiction check) | planned RFC — §12.1; `docs/spec/missions.md` MS-CT-01 | `planned` |
| **`missions.lock`** (`planned · Q-87(3)`, I2d) | file written by the box | runtime, only after a person approves the exact digest | runtime, `agent run` | digest check | no — MS-AP-05 | `planned` |
| **NeuroEdge Blueprint** `blueprint.v1` (`planned · Q-72`, I2e); manifest `blueprint.toml` | package + manifest (digest over canonical manifest + per-file SHA-256, Q-86(4), BL-PK-02) | seller, maker | `blueprint install`, Hub index | schema + full-package digest | planned RFC — §12.2 | `planned` |
| **Data destination declarations** (`planned · Q-72`, I2d) | in `mission.v1` and runtime config | user | runtime egress port | runtime | planned RFC — §12.3 | `planned` |
| **Chat events** and **approval records** (`planned · Q-72`, I2d) | in-runtime JSON, `trace.v1` events | chat adapter, runtime | runtime, `replay` | runtime | planned RFC (source `chat:<id>`) — §12.4 | `planned` |
| **`safe_state` in `board.v1`** (`planned · Q-72`, I2d) | TOML | OEM, maker | build, HAL | `schemas/board.v1.json` | planned RFC (conditional safety) — §4 | `planned` |
| **Trace segment** `trace.v1` (`planned · Q-72`, I2d) | JSON | 24/7 runtime | player, `replay` | `schemas/trace.v1.json` | planned RFC — §7 | `planned` |

## 2. Gate — `gate.v1`

A real gate in the repository, tier 2 of a three-tier chain:

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
  risk_level:   { lte: low }    # tightened: medium → low

on_block:
  action:  escalate
  to:      human_receptionist
  message: "Yêu cầu cần được nhân viên lễ tân xác nhận trực tiếp trước khi mở khóa."

budget:
  p95_latency_ms: 120
  fail:           closed
```

| Field | Constraints |
|:---|:---|
| `schema`, `name`, `version` | Always required. `name` matches `^[a-z0-9_-]+$`; `version` is SemVer 2.0 |
| `extends` | `neuroedge://gates/<path>@MAJOR.MINOR.PATCH`. Root gate (no `extends`) must declare all of `evaluate`, `allow_when`, `on_block`, `budget` (RFC-0001) |
| `evaluate.<criterion>` | `type` ∈ `bool`, `level` (requires `levels`, ordered from low to high), `choice` (requires `options`); `instructions` non-empty |
| `arguments.<parameter>` (RFC-0005) | `type` ∈ `string`, `integer`, `number`, `boolean`; optional `minimum`, `maximum`, `enum`, `max_length` |
| `allow_when` | One operator per clause on a declared criterion; operators by type in [`05`](05-code-gate-hal-c4l4.md) §2. CEL string format is currently rejected |
| `on_block.action` | `deny` · `escalate` (requires `to`) · `ask` (requires `message`, optional `confirms`) · `degrade` (requires `fallback_action`) |
| `budget` | `p95_latency_ms` ≥ 1; `fail` ∈ `closed` (default) · `open` |

The schema alone is insufficient to conclude that a gate is safe — Principle 2 is a statement about **two**
documents, whereas JSON Schema only sees one. The check gate is `neuroedge gate lint` (Invariant 1). Any
change to `allow_when` is a breaking change, requiring a MAJOR version bump.

## 3. Agent — `agent.toml`

Each table has its own parser; code does not reject unknown top-level tables, but provider tables reject
unknown keys. CLI syntax uses these tables: `docs/reference/cli.md` §3.

| Table | Parser | Primary Keys and Rules |
|:---|:---|:---|
| `[agent]` | `compiler.load_agent_manifest` | `name`, `version` (required; on `esp32s3` must be `MAJOR.MINOR.PATCH`), `language` (exactly 2 lowercase letters) |
| `[requires]` | `compiler.check_capabilities` | Keys are dotted primitives (`"digital.out"`…); `pins`, `sensors`, `channels` (`analog.in`, each channel must be declared by the board), `sample_rate_hz`, `aec`, `min_width`… must exist on the board |
| `[gates]` | `compiler.resolve_gates` | `key = "neuroedge://…"` or relative path; each `@action(gate=…)` must point to a key. On `esp32s3` keys must be C identifiers |
| `[targets]` | `compiler` | `supported = [...]` |
| `[sim.facts]`, `[sim.slot_facts]` | `sim/session.py` | Fixed session facts; facts extracted from command slots |
| `[sim.sensors]`, `[sim.sensor_facts]` | `sim/session.py` | Simulated readings; converts readings to facts: `equals`, `gte`/`lte`, or `bands` (ascending ranges, last band is the gate's highest level); numeric rules require units |
| `[system_two]` | `models/providers/config.py` | `provider` (`litellm` or `python:…`), `model`, `api_key_env`, `api_base`, `timeout_s` (≤ 120), `max_tokens`, `temperature`, `options` |
| `[system_one]` | as above | `provider` (`systemone` or `python:…`), `model`, `criteria` (non-empty, no `call_source`), `threshold` [0.5, 1], `timeout_ms` (≤ 10,000, and plus 50 ms margin must be ≤ gate's `p95`) |
| `[stt]`, `[stt.fallback]`, `[tts]` | `perception/providers/config.py` | `provider` (`openai` or `python:…`), `base_url`, `model`, `voice` (TTS), `language` (STT), `timeout_s`, `api_key_env`; `[stt]` requires `audio.in`, `[tts]` requires `audio.out` |
| `[wake_word]` | as above | `provider` (`openwakeword` or `python:…`), three model files `model`, `melspectrogram`, `embedding` (user-provided), `word`, `threshold`; rejected on `esp32s3` |
| `[mcp]`, `[mcp.servers.<name>]` | `mcp_host.load_mcp_config` | `max_rounds` (1–16); each server: `command`, `tools` (allowlist, required), `args`, `env`, `timeout_s` |

**Common rules for all provider tables** (`models/providers/common.py`): fields named like keys
(`api_key`, `token`, `secret`…) are rejected; values that look like keys are rejected and never reprinted;
endpoints must not carry credentials, query, or fragment; `http://` to other machines carrying keys
is rejected, and for `[system_one]`, `http://` to other machines is rejected in all cases.

## 4. Board — `board.v1`

| Section | Content |
|:---|:---|
| `[board]` | `id`, `target` (`sim` · `linux` · `esp32s3`), `mcu`, `name` |
| `[capabilities.audio_in]` | `channels`, `sample_rate_hz`, `aec`, `vad` |
| `[capabilities.audio_out]` | `channels`, `sample_rate_hz` |
| `[capabilities.digital_out]` | `pins` (logical names), `backend` |
| `[capabilities.sensor_read]` | `sensors` |
| `[capabilities.display]` | `width`, `height`, `color` |

The five core primitives form a closed set for v1.x (FR-HAL-01); new primitives enter only via RFC, and four board-optional extension packs (FR-HAL-08, Q-53) enter v1.0 in I2a and I3a: RFC-0007 (`digital.in`, read-only I2C, `analog.in`), RFC-0009 (`numeric` criteria), RFC-0010 (PWM), RFC-0011 (`motion.*`), RFC-0012 (`vision.in`), RFC-0013 (board options). Today there are exactly three tier-1 profiles (Q-53 adds `sim-rpi5` and an ESP32-S3 board with camera): `sim-default` (exact replica of Box-3, never richer — Invariant 7), `linux-rpi5` (`aec = false` until benchmark passes), `esp32s3-box-3`. Application code only uses pin **names**; GPIO numbers belong to HAL.

**Symmetric `safe_state` (`planned · Q-72`, I2d, pending RFC for conditional safety).** Today `safe_state`
only exists on `motion.*` channels (`stop` or `hold`, RFC-0011, `hal/board.py`). Under [Q-72](../../roadmap/neuroedge-prd.md#15-decision-log),
all actuators will have a `safe_state` declared in `board.v1`, default `off`; duration, `max_continuous_ms`, lease,
levels L0–L3 (RFC-0018), and Q-62 gate exemptions all refer to "returning to `safe_state`", while the direction of *leaving*
`safe_state` is subject to gates and limits. A `safe_state` other than `off` may only be declared here — not in mission
contracts, gates, or NeuroEdge Blueprints — and `safe_state: on` realized through default-on wiring
(normally-closed relays) is declared as a hardware interlock. Existing profiles (`off`; `motion.*` `stop`/`hold`)
preserve their behavior. Precondition: `TODOS.md` #58 (old parsers ignoring unknown keys in `board.v1`) must
be fixed first, so that a new safety key is not silently ignored. On a `sim` board, `safe_state = on` with an interlock entry is allowed under the label `risk=simulated_interlock`, never on `sim-virtual` (Q-87(4), MS-SF-05); shipped boards inside a Blueprint wait for the conditional-safety RFC (Q-86(2), BL-FMT-04).

## 5. Grammar and Knowledge

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

Each command does exactly one thing: calls a `tool`, speaks a fixed phrase (`say`), or delegates to
System 2 (`ask`, with `offline_say`). Matching: normalization (NFC, lowercase, strip punctuation,
keep Vietnamese diacritics), exact pattern match scores 1.0, otherwise uses `difflib` ratio against
`threshold`. `knowledge.toml` consists of `questions` → `answer` entries, which become an
`ask = "knowledge"` command; the trace stores only the `id` and score of the retrieved entry.

## 6. Tool Calls and Results

The shapes are defined in `schemas/tool-call.v1.json` (envelope `ToolCall { id, name, arguments, source }`,
`source` ∈ five sources; tool description) and `schemas/tool-result.v1.json` (`ToolResult`,
`status` ∈ ALLOW · BLOCK · REJECTED); not duplicated here.

| `status` | Meaning | Pins | MCP `isError` |
|:---|:---|:---|:---|
| `ALLOW` | Gate allows, function body executed | may change | false |
| `BLOCK` | Gate blocks (all `on_block`) | unchanged, except pins of a `degrade` fallback if its own gate allows | false |
| `REJECTED` | Unknown tool or invalid parameters; no verdict | unchanged | true |

An empty `id` is assigned `call_1`, `call_2`… per session. `source` is assigned by the runtime based
on the connection, not declared by the caller. Result consumers do not branch on `reason` (an open
string): `status` decides. Full normative spec: [`docs/spec/tool_calling.md`](../spec/tool_calling.md).

## 7. Trace — `trace.v1`

```json
{ "$schema": "https://schema.neuroedge.dev/trace/v1.json",
  "metadata": { "session_id": "sess_…", "timestamp_utc": "…", "target": "sim",
                "board_id": "sim-default", "agent_version": "home-voice@0.1.0" },
  "events": [ { "offset_ms": 0, "type": "text_input", "data": { "text": "bật đèn" } } ] }
```

Frozen envelope: `metadata` requires five fields (and accepts additional fields), each event has exactly
`offset_ms`, `type`, `data`. `type` is a **freeform string**, so adding an event type does not require
an RFC. NaN and infinity are rejected on read and written as strings.

Events by role during replay:

| Role | Events | During Replay |
|:---|:---|:---|
| **Input** | `text_input`, `audio_in_*`, `wake_word_detected`, `stt_result`, `stt_unavailable`, `sensor_read`, `sensor_set`, `sensor_unavailable`, `intent_extracted` | re-injected |
| **Decision** | `gate_evaluation_begin`, `gate_facts`, `gate_evaluation_result`, `argument_out_of_range`, `actuator_command`, `actuator_aborted`, `actuator_command_rejected` | recomputed and compared against golden |
| **Coordination** | `tool_call`, `tool_call_rejected`, `mcp_auth_refused`, `tool_confirm_*`, `action_requested`, `fallback_skipped`, `voice_state_changed`, `voice_reprompt`, `voice_late_result_dropped`, `stt_fallback` | recorded, not compared |
| **Output** | `tts_stream_start`, `tts_stream_end`, `tts_unavailable`, `display_frame` (digest only), `knowledge_retrieved` | not compared |
| **Telemetry** | `system_one_call`, `system_one_fallback`, `system_two_call`, `system_two_unavailable`, `circuit_breaker`, `mcp_tool_result`, `turn_latency`, `session_summary` | ignored |
| **Device-only** | `device_info`, `trace_end` | UART session frame |

`session_summary` is never recorded during the session: `EventLog.to_trace()` calculates and appends it
on export. By default, traces hash `text`, `utterance`, `transcript` at source and carry
`metadata.anonymized = true`; `--raw` preserves verbatim text, and that trace carries
`metadata.anonymized = false` (NFR-PRIV-03). The three canonical traces
(`fixtures/traces/happy-path.json`, `unverified_attempt.json`, `network_offline.json`) are frozen by
RFC; RFC-0008 adds `gate_digest` — the digest of the gate that decided each verdict — to each of their
`gate_evaluation_begin` events.

**24/7 runtime trace segments (`planned · Q-72`, I2d, pending RFC `trace.v1`).** A session today is
a single command process and writes one file upon closing. A runtime operating for months will write a
**sequence of segments** over time (daily or upon exceeding size): each segment carries initial state
(gate digest, token ledger, envelope counters, running leases) and the digest of the previous segment.
The invariant "one session, one trace" is reinterpreted as "one session, one trace sequence, each segment
replayable"; missing segments are detected because the digest chain breaks. Appended sequentially, flushed on
a timer (around 10 seconds, configurable) and immediately upon a block verdict or approval; a power outage loses
at most the trailing normal events, and `replay` reports a truncated segment. Retention and size limits:
[PRD §9](../../roadmap/neuroedge-prd.md#9-non-functional-requirements) Modifying the canonical trace envelope
is an RFC-level change (`CONTRIBUTING.md` §3).

## 8. UART Format

```text
NE1 {"offset_ms":0,"type":"device_info","data":{"board_id":"esp32s3-box-3","agent_version":"home-voice@0.1.0","device_id":"qemu","boot_id":"9f2c01aa"}}
NE1 {"offset_ms":3,"type":"gate_evaluation_begin","data":{"gate":"light_on@1.0.0","gate_digest":"sha256:4cc8…"}}
NE1 {"offset_ms":9,"type":"gate_evaluation_result","data":{"verdict":"ALLOW","evaluations":{"call_source":"local_grammar"}}}
NE1 {"offset_ms":57,"type":"trace_end","data":{"events":4}}
NE_SELFTEST PASS walker=26 token=11
NE_TRACE DONE sessions=4
```

- `NE1 ` line at column 0, followed by a JSON object with **exactly** three keys; ≤ 512 bytes including
  the prefix. Oversized lines are dropped entirely but still counted.
- Each session opens with `device_info` at offset 0 and closes with `trace_end {events: N}`; N counts all
  lines of the session. The host rejects (`NE4001`, pointing out `source:line`) non-JSON lines, extra keys,
  events before `device_info`, reboots mid-session, miscounts, and unclosed sessions.
- Other lines: `NE_SELFTEST PASS|FAIL`, `NE_TRACE DONE`, `NEUROEDGE_HEAP_JSON {…}`,
  `NEUROEDGE_MEMORY_JSON {…}`, and `NE_OTA <event> …` — list and meanings in
  [`docs/user/nap-firmware.md`](../user/nap-firmware.md) §6.4; individual line formats are defined by
  `components/ne_ota/src/ne_ota_policy.c`.

## 9. Bidirectional Closed-World Corpus

Each file has exactly one expected entry and each entry has exactly one file; tests enforce this bidirectionally.

| Corpus | File | Expected |
|:---|:---|:---|
| Counterexample gates | `fixtures/gates/invalid/*.yaml` (and `valid/`, `registry/` must resolve) | `fixtures/gates/expected_errors.yaml`: error class, code, principle, substring of location and reason |
| Counterexample traces | `fixtures/traces/invalid/*.json` | `fixtures/traces/expected_errors.yaml` |
| Tool calls | `fixtures/tool_calls/{valid,invalid}/*.yaml` | `fixtures/tool_calls/expected_results.yaml`: status, pin commands, reason… |
| Integrator contracts | `fixtures/contracts/{tool-call,tool-result,error}/{valid,invalid}/*.json` | `fixtures/contracts/expected_errors.yaml`: schema (`against`) for each file; `invalid/` files with error (`keyword`, `path`, message substring) |
| Voice state machine | `fixtures/compliance/voice/*.json` | `fixtures/compliance/voice/expected_results.yaml`: full event list, correct offsets |
| Tree truth table | `fixtures/decision_trees/*.truth.json` | the file itself; C walker must match every line |

## 10. Versions, Identifiers, Digests

| Object | Convention |
|:---|:---|
| Agent | `<name>@<semver>` |
| Gate file | `<name>@<semver>.yaml` |
| Gate in registry | `neuroedge://gates/<group>/<name>@<semver>` → `<gates>/<group>/<name>@<semver>.yaml` |
| Session | `sess_<hex>` |
| Public schema | `https://schema.neuroedge.dev/<type>/v<n>.json` (served from I6) |
| Digest | `"sha256:" + SHA-256(JCS RFC 8785)` |

**Frozen means** changes require an RFC and are enforced by CI: seven schemas (file set, `$id`,
valid superschema); gates in `digests.lock`; three canonical traces; `NETR` v1 layout. Not frozen:
internal JSON trees, trace event catalog.

## 11. Error Codes

All errors have three parts: **where · why · how to fix** (FR-DX-04). Code families
(`schemas/error-codes.v1.json` is the source of structure: code, class, parent, status; PRD Appendix B
holds the text):

| Family | Meaning | Examples |
|:---|:---|:---|
| `NE1xxx` | Runtime action contracts | `NE1001` called outside `c.do()`, wrong token · `NE1002` token reused, expired |
| `NE2xxx` | Gate at build, lint, resolution | `NE2001` not found · `NE2002` invalid schema or limits · `NE2003` inheritance violation |
| `NE3xxx` | Build | `NE3001` board lacks capability · `NE3002` invalid `agent.toml` · `NE3003` aggregates all problems, writes nothing |
| `NE4xxx` | Traces, replay, verify | `NE4001` invalid trace or UART frame · `NE4002` safety regression · `NE4003` replay failure or stale firmware · `NE4004` scanned 0 artifacts |
| `NE5xxx` | Perception | `NE5001` grammar, knowledge, or fallback missing or invalid |

Blocking due to timeout or lost fact source is **not an error**: it is a `BLOCK` verdict with
`budget_exceeded` or `gate_unreachable`.

## 12. Planned Contracts Under Q-72 (`planned · Q-72`)

There are no schemas or code yet in this section. Target designs follow [Q-72](../../roadmap/neuroedge-prd.md#15-decision-log);
each contract is a **planned RFC** (unnumbered, listed in [PRD §15](../../roadmap/neuroedge-prd.md#15-decision-log)),
because introducing a new schema to `schemas/` or modifying `trace.v1`, `board.v1` requires an RFC (`CONTRIBUTING.md` §3).

### 12.1 Mission Contract — `mission.v1` (I2d)

The unit of policy for a chain of actions across multiple devices: allowed and forbidden, frequency, time
windows, obligations (only bounded watchdog style), data flow (§12.3), on failure, expiration, and
`llm_budget` (LLM cost ceiling). The mission compiler lowers each clause to the lowest tier capable of
enforcing it — reflex (MCU with `ne_gate`), skill (host), thinking (LLM) — rejects conflicting contracts
with specific conflict locations, then deterministically generates an **approval sheet of ≤ 5 lines** from
the structured diff. Gates remain pure functions; mission contracts do not carry a `safe_state` (§4; Q-87(4), MS-SF-05). Contract format, locking and `missions.lock`: Q-87(3), `docs/spec/missions.md` MS-CT-01, MS-AP-05. Time-window clauses read wall-clock facts; such facts carry `unsynced` when the machine has not
synced time and are then treated as missing facts. Flow: [`06`](06-runtime-flows.md) §11.1.

### 12.2 NeuroEdge Blueprint — `blueprint.v1` (I2e)

Requirements: `docs/spec/blueprint.md`; packing and install choices: Q-86 (manifest `blueprint.toml`, package digest taken over the canonical manifest and each file's SHA-256 so a directory, a git checkout and a `.tar.gz` give one digest, BL-PK-02; `contract` and `detectors` sections reserved and refused in v1, BL-FMT-05). Distribution is by URL (git or HTTPS) plus digest; the Hub is a static index repository listing URLs, digests and evidence, with no NeuroEdge-operated server. Evidence traces are marked "unsigned" (signing deferred, `TODOS.md` #1). The OCI Registry (Gate Registry, `manifest.v1`) was removed from the roadmap (Q-77). A NeuroEdge Blueprint is declarative only, carrying no executable code in the runtime. It differs from a Home Assistant Blueprint (an automation template) and may bundle an HA blueprint.

### 12.3 Data Destination Declarations (I2d)

Data flow rules aim to **prevent data leakage** (hacks, prompt injection, exfiltration), without
restricting user-built flows. Each destination declared by the user — LLM provider, chat channel, relay,
webhook — includes fields allowed to be sent to it, including images to the LLM if permitted by the user.
The runtime decides what the LLM worker *sees* and only transmits to declared destinations; sending to
undeclared destinations is blocked and traced. Content rules (e.g. "images do not leave the home") are
optional user flags in the contract, not defaults. Network-level enforcement:
[PRD §9](../../roadmap/neuroedge-prd.md#9-non-functional-requirements)

### 12.4 Chat Events and Approval Records (I2d)

- **Chat events:** inbound and outbound messages of the chat adapter, logged to the trace with the chat
  id (paired or not, whether a group), never containing bot keys or tokens. Inbound message content is
  untrusted data.
- **Approval records:** `{id, nonce, expiry, change digest, approval sheet ≤ 5 lines}`. Expiry is
  computed using the monotonic clock. Responses must target the specific `id`; runtime verifies that
  the sender is paired, not a group, nonce is unused, unexpired, digest still matches, then routes it
  into the confirmation path with source `chat:<id>` (following the source grammar with namespaces from
  RFC-0017). Every request, approval, and rejection is logged to `trace.v1` and flushed immediately.
  Flow: [`06`](06-runtime-flows.md) §11.4.
