# Gated Tool Profile v0 — The Path from Language to Physical Action

**Status:** normative for `sim` and `linux` since v0; `esp32s3` per §8. Shapes of envelope and result
frozen in `schemas/tool-call.v1.json` and `schemas/tool-result.v1.json` (RFC-0015, §1, §4, §9). Decisions:
Q-24, Q-25, Q-26, Q-27, Q-58, Q-66 (`neuroedge-prd.md` §15).
**Source code:** `python/neuroedge/actions/tools.py` (dispatch), `python/neuroedge/mcp_server.py`
(MCP server), `python/neuroedge/mcp_http.py` (MCP server network port, §8.1), `python/neuroedge/mcp_host.py` (System 2 as MCP client; legacy, behind `NEUROEDGE_LEGACY_SYSTEM_TWO`, Q-83, DP-A-08),
`python/neuroedge/sim/session.py` (grammar, System 2 loop).

This document is the **sole** definition of tool calling in NeuroEdge. Other documents link
here without repeating content (CONTRIBUTING §8.1). The keywords **MUST**, **MUST NOT**, **SHOULD**
carry the meanings defined in RFC 2119.

## 0. Why a *Profile*, Not a Protocol

The AI agent ecosystem has converged on a common transport: MCP (`tools/list`, `tools/call`),
OpenAI-style function calling, and JSON Schema for parameters. NeuroEdge **does not** invent
a new transport — an agent from Claude Desktop, Cursor, or LangChain can call a NeuroEdge device
without proprietary adapters.

What the ecosystem leaves unspecified is **what happens between the tool call and the physical effect**.
In MCP and function calling, calling a tool means *execution*; errors are arbitrary strings; no one
knows where a call originated; network loss means no tool calls. This profile governs that gap:

| | Regular Tool Calls | Gated Tool Profile |
|:---|:---|:---|
| Semantics | Execution | **Request** — gate decides (§2) |
| Denied results | Error string | Three structured states (§4) |
| Call provenance | Unrecorded | `call_source` — trusted fact readable by gates (§5) |
| Human confirmation | Client asks optionally, bypassable | Enforced by device; model cannot confirm itself (§6) |
| Network loss | Unavailable | Local grammar synthesises tool calls on same pipeline (§1) |
| Evidence | Text logs | Trace: tool call → verdict → pin commands, replayable (§7) |

MCP has **two directions**, and the profile covers both:

| Direction | Who is Client | Who is Server | Section |
|:---|:---|:---|:---|
| **B — calling into device** | External agent (Claude Desktop, IDE, peer agent) | `neuroedge mcp serve` | §1–§9 |
| **A — device calling out** | Agent's System 2 (MCP host) | Agent's own MCP server **and** external MCP servers | §10 |

The profile is the third standard asset of NeuroEdge, alongside gate schemas and trace schemas
(`docs/architecture/16-ecosystem-landscape.md` §6).

## 1. `ToolCall` Envelope

Shape lives in [`schemas/tool-call.v1.json`](../../schemas/tool-call.v1.json), not duplicated here:
`#/$defs/request` is what the caller sends (`id`, `name`, `arguments`; **no** `source`, and any self-declared
`source` is rejected by the envelope), `#/$defs/call` is the envelope held by the dispatcher — adding the assigned `source` — and
also serves as `data` for the `tool_call` event (§7). The envelope is **closed** (unexpected keys rejected). Below is the
**semantics** that schemas cannot express:

| Field | Specification |
|:---|:---|
| `name` | Name of an agent `@action`. Each `@action` corresponds to exactly one tool |
| `arguments` | JSON object; keys are parameter names of `@action` |
| `source` | A built-in source or `bridge:<id>` / `mcp:<client>` (table below). **Assigned by runtime**, never declared by caller |
| `id` | `call_1`, `call_2`… sequential within session, assigned by dispatcher when empty. **MUST NOT** be random: traces must be deterministic for stable goldens and `--anonymize`. Model provider IDs are preserved |

| `source` | Origin |
|:---|:---|
| `local_grammar` | Sentence matching `commands.toml` → **synthetic** tool call (Q-14). Runs offline |
| `system_one` | Structured model (PRD §4.3, FR-MDL) |
| `system_two` | LLM with free-form utterance; calls device tools via in-process MCP connection to the agent itself (§10) |
| `mcp` | MCP client via `neuroedge mcp serve`, over stdio or network (§8.1) |
| `test` | Action CI |
| `bridge:<id>` | A loaded bridge (Muse, Home Assistant…): core assigns from registered bridge id inside `Dispatcher`; bridge has no mechanism to declare source (RFC-0017 §3b) |
| `mcp:<client>` | Network MCP client labeled by operator, from authenticated token `sub` (RFC-0017 §3c) — grammar accepted; client labeling **not yet** implemented (TSK-I2c-10 half (b)), so all network clients today remain `mcp` |
| `chat:<id>` | *planned · Q-72 (I2d), awaiting RFC for source `chat:<id>`.* A locally paired chat account. **Only** carries this source when runtime has verified a valid approval record (§6); **never** assigned merely because a connection exists from a chat platform — chat messages are normally worker LLM data, not human calls |
| *(worker LLM source)* | *planned · Q-72 (I2d), name finalized in RFC.* Local MCP connection of worker LLM — untrusted process holding operator agent's BYOK key. Assigned by runtime per connection, like `mcp`; not in `HUMAN_SOURCES` |

**Grammar of `source`** (RFC-0017 §3a): one of the five built-in names above, or `bridge:<id>` / `mcp:<client>` with
`<id>` matching `[a-z][a-z0-9_]{0,31}` (`SOURCE_ID` pattern in `actions/tools.py`; `source` maximum length 39 characters). Other families ⇒
`ToolCallError` NE1004 during instantiation; **built-in set remains closed**, adding a family or built-in name requires an RFC. Code validates with
`re.fullmatch` (`valid_source`), not `$`: Python's `$` matches before a trailing `\n`, whereas ECMA 262 does not
(`test_a_source_with_a_trailing_newline_is_refused`). Schema shape lives in
[`schemas/tool-call.v1.json`](../../schemas/tool-call.v1.json) `$defs/source`.

Sentences matching grammar **MUST** become tool calls and flow through the exact same path as all other sources —
there is no separate "offline" path to pins.

Successful schema validation **does not** prove runtime compliance: schemas cannot represent tool existence, string
coercion (§2), gate parameter constraints (§3, checked **after** schema), or `call_source`. The compliance test suite
is the corpus in §9 executed through `dispatch()` — same rationale as gates: the gatekeeper is `neuroedge gate lint`,
not schema validation (`CHANGELOG.md` §3.3 #1).

## 2. Dispatch Order

Every tool call, from any source, traverses `dispatch()` in strict order:

1. Log `tool_call` event.
2. Tool exists — if no ⇒ `REJECTED`.
3. Arguments match schema (§3): no unexpected arguments, all required arguments present, correct types. Strings
   coerced to numbers or bools when schema requires it (grammar slots are text); no other guessing.
   Invalid ⇒ `REJECTED`, log `tool_call_rejected`.
4. Insert facts `call_source` and `call_channel` (§5). A source `bridge:<id>` / `mcp:<client>` whose id is unregistered
   in the session ⇒ programming error NE1004, raised **before** step 1: no call, no event.
5. `c.do(action, **arguments)` → gate → single-use token → `@action` body → HAL.

**Reserved** `arguments` key `__unparseable__`: `parse_tool_calls` inserts it when model provider
`arguments` is not valid JSON (or not an object), with value set to raw corrupted fragment. No `@action`
has a parameter by that name, so step 3 rejects it ("unknown argument") and the call is `REJECTED`;
no gate sees it. Callers **SHOULD NOT** send this key directly.

Steps 2–3 occur **before** the gate: a malformed call is not a safety question, so it incurs no
gate budget and produces no verdict.

Contract violations (`ActionContractViolation` NE1001, `TokenReplayError` NE1002) **MUST** be
raised. The dispatcher **MUST NOT** catch them and return `BLOCK`: that is a programming bug, not
a verdict, and suppressing it masks a bypass around gates.

## 3. Tool Schema

Schemas are generated from `@action` signatures (`input_schema()`): `str` → `string`, `int` → `integer`,
`float` → `number`, `bool` → `boolean`; parameters without defaults are `required`;
`additionalProperties: false`. Description is the opening docstring paragraph appended with *"Guarded by gate
`X`: the call may be blocked."*

The JSON Schema subset used by `inputSchema`, and the four fields of a tool (`name`, `description`,
`inputSchema`, `outputSchema`), are described in `schemas/tool-call.v1.json` (`#/$defs/input_schema`, `#/$defs/tool`).

The identical schema is emitted in two forms: MCP `inputSchema` (`neuroedge mcp tools --json`) and
OpenAI function calling `parameters` (`--openai`, Q-12).

Starting with RFC-0005 (Q-25, TSK-S3-25), schema represents the **intersection** of signature and gate parameter
constraints: `minimum`, `maximum`, `enum`, `maxLength` from gates enter `inputSchema` so models see boundaries
before calling. Gates re-validate — schemas guide models, gates enforce.

## 4. Results

| `status` | Meaning | Pins | MCP `isError` |
|:---|:---|:---|:---:|
| `ALLOW` | Gate permitted, `@action` body executed | May change | `false` |
| `BLOCK` | Gate blocked (all `on_block`, Q-17) | Unchanged — except pins of `fallback_action` when `degrade` and fallback permitted by its gate | `false` |
| `REJECTED` | Unknown tool or malformed arguments; no verdict | Unchanged | `true` |

`BLOCK` is **not** a protocol error: the gate performed its duty, and the caller needs to read the reason
to respond to the user. Only `REJECTED` is an error — the caller submitted an invalid request.

The shape of return content (`ToolResult.content()`; MCP sends both in `structuredContent` and a `text` block
containing identical JSON) is [`schemas/tool-result.v1.json`](../../schemas/tool-result.v1.json), not duplicated
here. The schema dictates field conditions: `tool` and `status` are always present; `BLOCK` carries `gate` and
`on_block`; `REJECTED` carries `problems` (non-empty); `fallback` (recursive, result of `fallback_action` evaluated through
its own gate) and `confirmation` (§6) belong to `on_block: degrade` and `ask`.

The MCP server declares this exact schema under `outputSchema` of each tool, pinning `tool` to tool name and removing
`$id`/`$schema` (`result_schema()` in `actions/tools.py` **reads** the file; it does not build the schema). MCP clients validate
`structuredContent` of every non-error result against that schema; `REJECTED` results
(`isError: true`) are unvalidated by the SDK, yet still match schema (unknown tools match schema without
pinned `tool` name).

**Rules for result consumers (RFC-0015 §3b, Q-66):**

- **`status` decides. `reason` is an explanation only — MUST NOT branch on it, and absolutely never branch
  to ALLOW.** `reason` is an open string: known values listed in `x-neuroedge-known` in schema (tests enforce exact match
  with `Reason`), expanding across RFCs. An unknown `reason` under `status: BLOCK` remains blocked (fail-closed), not a corrupted result.
- **Open result object:** consumers **MUST** ignore unknown keys. Runtime emits only declared schema keys
  (test `test_the_mcp_server_emits_only_documented_result_keys`); adding an optional key does not bump `v1`.
- **`status` and `on_block` are closed sets:** adding values requires `v2`.

## 5. `call_source`

The dispatcher injects fact `call_source = <source>` into the gate context of **that specific call**
(`Conversation.do_with`): a snapshot of `c.facts` taken at call inception, overridden by `call_source`. `c.facts`
is neither mutated nor restored. Concurrent calls on a single `Conversation` (one `mcp`, one `system_two`)
cannot observe each other's sources; `degrade` fallback and `ask` prompts inherit the source of their parent call,
even during interleaved executions (`tests/test_call_source_isolation.py`). Gates evaluate it like any `choice` criterion:

```yaml
evaluate:
  call_source:
    type: choice
    options: [local_grammar, system_one, system_two, mcp, test]
    instructions: Where call originated — inserted by runtime, not inferred from speech
allow_when: call_source in ["local_grammar", "system_one"]   # MCP cannot open door
```

Sources are **connection-bound**, assigned when runtime establishes the connection: `neuroedge mcp serve` is `mcp`, including over network (`--http`, §8.1); System 2 in-process connection is `system_two` (`build_server(session, source=...)`). A bridge receives source `bridge:<id>` from its registered id at load time.

*Planned · Q-72 (I2d), awaiting RFC.* Operator agents introduce two additional connections under the same "connection-bound" rule: worker LLMs call runtime over local MCP and receive the runtime-assigned worker source; chat channel adapters reside in runtime, with source `chat:<id>` appearing solely on approval record paths (§6), never assigned across the entire chat platform connection. New built-in names or families require an RFC like any other source.

Network calls today are `mcp`: stdio and network share one server and one gate pipeline, so gates do not yet distinguish ports. Per-device differentiation uses operator-assigned `mcp:<client>` labels (RFC-0017 §3c, half (b), unbuilt); unlabelled devices remain `mcp`. Adding families or built-in names for `call_source` requires an RFC (`CONTRIBUTING.md` §3).

**ID registration.** `dispatch()` accepts only `bridge:<id>` / `mcp:<client>` registered on session `Conversation`
(`register_source`; internal, outside `neuroedge.__all__`): bridge loader and `[mcp.clients]` table register, corpus runner
(§9) acts as loader. IDs outside grammar, built-in collisions, or duplicate IDs ⇒ NE1004; unregistered IDs ⇒ NE1004 in `dispatch()`. This is a guard against
typos and external code outside `Dispatcher`, not a sandbox against in-process adversarial code (`threat_model.md` §2b, §3).

**`call_channel` — source family.** The dispatcher also injects derived fact `call_channel`: prefix before first `:` of
`call_source` (or full name for five built-ins) — `bridge` for `bridge:muse`, `mcp` for `mcp:hub`. Injected at the **exact call site** where
`call_source` enters gate context (`Conversation._context`), *after* merging fact sources, so `c.facts`,
`[sim.facts]`, fact sources, and models cannot override it; it persists across `ask` prompts (§6), nested `c.do()`,
and `degrade` fallbacks. Missing valid `call_source` ⇒ missing `call_channel` ⇒ `criterion_unavailable`. Lives in `RUNTIME_CRITERIA`: `[system_one]` cannot
delegate it to models. Gates specify "exactly Muse bridge" via `call_source`, or "all active bridges" via `call_channel`:

```yaml
evaluate:
  call_source:  { type: choice, options: [local_grammar, mcp, bridge:muse, test], instructions: "…" }
  call_channel: { type: choice, options: [local_grammar, system_one, system_two, mcp, bridge, test], instructions: "…" }
allow_when:
  call_source:  { in: [local_grammar, bridge:muse] }   # exactly Muse; other bridges ⇒ BLOCK
# or "all bridges":  call_channel: { in: [local_grammar, bridge] }
```

**Fail-closed.** Values outside gate `options` ⇒ `BLOCK`, `criterion_unavailable`, even under `fail: open`; all current gates
enumerate five sources, so all bridges `BLOCK` by default until a gate explicitly names the bridge or family. `gate.v1` and `NETR` layout unchanged
(`bridge:muse` is a string in that gate's domain; domains support up to 32 values, so "all bridges" uses `call_channel`).
`bridge:*` and `mcp:*` are not in `HUMAN_SOURCES` (§6). Replay uses recorded `gate_facts` only, requiring no bridge present (§7).

Callers **MUST NOT** declare their own source: `call_source` is not a tool parameter, so
models passing `{"call_source": "local_grammar"}` are `REJECTED` in step 3
(`test_a_model_cannot_claim_its_own_call_source`). Complete examples:
`fixtures/agents/home-voice/gates/`, and `fixtures/agents/driveway/gates/open_gate@1.0.0.yaml`
(MCP client cannot open gate).

## 6. Confirmation `on_block: ask` (Q-26)

`ask` means *ask the human*. Therefore:

- Only **humans, through device channels**, may confirm: voice or typing matching grammar
  (`local_grammar`), or buttons on device page (`ui`). This is the set of **confirmation
  sources** (`HUMAN_SOURCES`, `actions/confirmation.py`), distinct from the five `source` values of §1: `ui`
  does not emit tool calls, and `call_source` never equals `ui`.
- Sources `system_two`, `mcp`, `bridge:<id>`, and `mcp:<client>` **MUST NOT** issue confirmations. Otherwise, prompt-injected models
  or client-side autonomous agents could answer safety questions intended for humans.
- Gates declare upfront **what** humans may confirm: `on_block.confirms` (RFC-0006).
  Lacking `confirms` ⇒ `ask` notifies only, with no pending question.
- Questions open (`tool_confirm_requested`) only when a "có" ("yes") response is **enough** to allow — given identical
  facts, treating criteria in `confirms` as met must result in ALLOW. If gate blocks due to other
  criteria or argument bounds, no question is asked.
- Confirmations bind to question (`confirm_N`) and `gate_digest` of the blocked instance; **single-use**
  (even if re-evaluation still blocks); expires after `max(p95 × 3, 10 s)`; gate changes mid-flight
  ⇒ invalidated. Sources other than `local_grammar` / `ui` ⇒ `tool_confirm_rejected`, question
  remains pending human answer.
- Text input and UI buttons answer latest pending question. Spoken **voice** answers questions only within
  its own turn — rules in `docs/spec/voice_fsm.md` §5.4 (Q-46 (D3)).
- Confirmation does not bypass gates: gate is **re-evaluated** with **current** facts and
  `call_source` of the **original request** (and `call_channel` derived from it); only criteria in `confirms` are treated as met. All other criteria,
  argument bounds, and fail-closed handling during adjudicator degradation remain active. Results log
  `confirmed: [...]`.
- Caller (System 2, MCP client) is notified in `BLOCK` result: `confirmation: {id, message,
  expires_in_ms, who}` — for reporting to users, not for autonomous answering. No confirmation tool exists.

**User-declared verification steps — planned · Q-73 (FR-CH-06), awaiting RFC TSK-I2d-20.** Beyond yes/no, `on_block` will support declaring a verification step (passcode, voiceprint, facial recognition, phone fingerprint…) via validator plugins, accompanied by risk labels; source rules above remain unchanged: only humans through device channels may answer.

On `sim`: REPL — type `có` ("yes") / `không` ("no") (or `:confirm` / `:decline`); UI — banner *Thiết bị
hỏi xác nhận* (Device requests confirmation) with buttons Đồng ý (Approve) / Huỷ (Cancel) and remaining time (`POST /confirm`, same origin).

**Approval record path via chat channels — planned · Q-72 (I2d), awaiting RFC for source `chat:<id>`.** Q-72 extends Q-26: humans
may approve via paired chat channels, covering both `ask` prompts and mission contract amendments, excluding data authority expansions (local approval only,
FR-MSN-14); LLMs never approve.
Design decided in Q-72 architectural review (2026-10-11), unbuilt — `HUMAN_SOURCES` today remains `local_grammar` and
`ui` only:

- Runtime transmits an **approval record** `{id, nonce, deadline, change digest, approval text ≤ 5 lines}` to paired chat.
  Approval text is deterministically generated by runtime and compiler from structured diffs, not from LLM prose.
- Responses must target matching `id` (button or code). Runtime verifies: sender is paired, not a group chat, unused nonce,
  unexpired on monotonic clock, digest matches proposed change.
- Meeting all five conditions routes approval into the **identical confirmation pipeline above** with source `chat:<id>`: gate re-evaluates, treating only criteria
  in `confirms` as met. Missing any condition ⇒ reject and trace, never consulting LLM.
- Pairing performed locally; revocation, pairing expiry, and approval rate ceilings deferred in `TODOS.md` #62. Threat
  model: `threat_model.md` §2e.

## 7. Traces

This is the **sole** catalog of events for tool calling, confirmations, MCP host, System 2, System 1 cloud
models, and turn measurements (§7.1). HAL primitive events (`actuator_command`, `sensor_read`, `display_frame`…) live in
`docs/spec/simulation_coverage.md` §3.

| Event | Data | Available Since |
|:---|:---|:---|
| `tool_call` | `id`, `name`, `arguments`, `source` | v0 |
| `plugin_loaded` | `kind`, `name`, `distribution`, `version`, `files_sha256` (or `editable: true`, unhashed) — one event per enabled entry point at boot, matching `metadata.plugins` ([`extension_sdk.md`](extension_sdk.md) §7); replay skips | RFC-0016 §3d (TSK-I2c-16) |
| `tool_call_rejected` | `id`, `name`, `problems` | v0 |
| `tool_confirm_requested` | `id`, `action`, `gate`, `message`, `confirms`, `expires_ms` (trace timeline, like `offset_ms`), `ttl_ms` | RFC-0006 |
| `tool_confirmed` · `tool_confirm_declined` | `id`, `source` | RFC-0006 |
| `tool_confirm_rejected` | `id`, `source`, `reason` | RFC-0006 |
| `tool_confirm_expired` | `id` | RFC-0006 |
| `tool_confirm_withheld` | `action`, `gate`, `pending` — a call that would ask while `pending` (4) questions wait; no question sent, the call is BLOCK `budget_exceeded` | DP-COM-09 (`deployment_profiles.md`) |
| `mcp_auth_refused` | `reason`, `status?`, `subject?` — request to network port (§8.1) met 401 or 403, forwarding nothing. `reason`: `no_token` · `malformed_authorization` · `invalid_token` (signature, formatting, missing `exp` `iat` `iss` `sub`) · `expired` · `wrong_audience` · `wrong_issuer` · `not_cert_bound` · `cert_mismatch` · `lifetime_too_long` (`exp` − `iat` over 7 days, DP-A-04) · `insufficient_scope` (`status` 403) · `revoked_certificate` (the client certificate is in `--revoked`: the connection is closed after the handshake, before any HTTP, so no `status`; DP-A-11). `subject` present only after signature validated (`cert_mismatch`, `not_cert_bound`, `insufficient_scope`). **Never** contains token, client address, or certificate. Max 10,000 events per session; final event marked `last_recorded: true`. Not a turn (no `turn_latency`); replay skips | TSK-P2-04 |
| `ui_auth_refused` | `reason`, `path`, `last_recorded?` — POST to the local page (`run --ui`, `mcp serve --ui`, Studio) refused with 403, nothing run. `reason`: `foreign_host` · `no_origin` · `foreign_origin` · `no_key` · `wrong_key` · `bad_code` (`POST /pair`) · `bad_control` (`POST /pair/new` without the control secret of `ui.json`, DP-A-10). `path` cut to 64 characters. **Never** contains the key or the pairing code. Max 10,000 events per session; final event marked `last_recorded: true`. Not a turn; replay skips | DP-A-02 (`deployment_profiles.md`) |
| `mcp_tool_result` | `id`, `server`, `tool`, `status`, `sha256`, `bytes` — payload unrecorded (§10 rule 3) | Q-27 |
| `mcp_server_unavailable` | `server`, `reason` (§10 rule 4) | Q-27 |
| `system_two_call` | `provider`, `model`, `task`, `latency_ms`, `status`, `prompt_tokens?`, `completion_tokens?`, `cost_usd?`, `error?` — no prompts, no keys; replay skips | FR-MDL-06 |
| `system_two_off` | `provider`, `model`, `flag` — the agent declares `[system_two]` but the box's own LLM path is legacy and off without `NEUROEDGE_LEGACY_SYSTEM_TWO=1`; the grammar, System 1 and the offline answer run as before. Once per session; replay skips | DP-A-08 (`deployment_profiles.md`) |
| `system_two_unavailable` | `task`, `reason` — model failed to answer | FR-MDL-06 |
| `system_two_rounds_exceeded` | `task`, `rounds` — exceeded `max_rounds` (§10 rule 6) | FR-MDL-11 |
| `system_one_call` | `provider`, `model`, `criterion`, `latency_ms`, `status` (`ok` · `unavailable`), `reason?` (`Unavailable` reason: `offline`, `timeout`, `rate_limited`, `refused`, `malformed`, `empty`), `http_status?`, `confidence?`, `served_by?` (responding model version), `prompt_tokens?`, `completion_tokens?`, `cost_usd?` — per-turn SystemOne evaluation of cloud model for a criterion (`[system_one]`). Model receives speaker utterance only (`state = {utterance}`), never caller action or parameters; absent speaker utterance (e.g. MCP client call) or missing key skips call and logging. Events omit state, text, or keys; replay skips | TSK-I4-02 |

Utterances spoken by device are logged in `tts_stream_start` (simulation_coverage §3); utterance origin tracked in turn
`reply_source` (e.g. `gate_ask`, `confirmed`, `offline_help` — §10 rule 5; complete list in
`Turn.reply_source`, `python/neuroedge/sim/session.py`).

**Planned events — planned · Q-72 (I2d, I2e).** Code emitting following events unbuilt; event family
names represent directions decided in 2026-10-11 architecture review, with full names and data finalized in respective RFCs. Upon implementation, each
row replaces with real name and data, recording task in "Available Since" column.

| Event | Meaning | Available Since |
|:---|:---|:---|
| `mission_*` | Mission contract lifecycle: draft, question, compile and conflict check, lock, expiry | planned · Q-72, RFC `mission.v1` |
| `detector_fired` | Deterministic detector fires event (threshold, trend, stuck sensor) — calls LLM only thereafter | planned · Q-72 |
| `llm_budget_*` | Contract LLM cost ceiling: usage, near limit, exhausted — upon exhaustion reflexes and hardcoded alerts continue running | planned · Q-72 |
| `chat_in` · `chat_out` | Inbound and outbound messages with paired chat channels | planned · Q-72 |
| `approval_*` | Approval record (§6): requested, approved, rejected (unknown sender, group, reused nonce, expired, digest mismatch), expired | planned · Q-72, RFC source `chat:<id>` |
| `egress_blocked` | Runtime or worker LLM network blocks transmission to undeclared destination | planned · Q-72, RFC data flow |
| `segment_*` | Trace segment boundary for 24/7 runtime: each segment carries initial state and digest of prior segment | planned · Q-72, RFC trace segmentation `trace.v1` |

Field `type` in `trace.v1` is open, so adding events **requires no RFC**; except `segment_*` which alters canonical trace chunking and requires an RFC. Replay (`testing/player.py`) recomputes each gate evaluation from recorded `gate_facts` —
including `call_source` — ensuring LLM calls replay deterministically without re-querying models.
`REJECTED` calls do not reach gates and are absent from replay verdicts.

### 7.1 Stage Latencies and System 1 / System 2 Ratios (TSK-I4-03)

FR-ACE-06, FR-TEL-03, NFR-OBS-02. Each turn in `sim` / `linux` sessions — typed line or
transcript (`SimSession.handle`), System 2 reply routed by voice controller
(`run_tool_calls`), `offline_help` prompt when System 2 is unavailable (`say_offline`), confirmation button
(`confirm` / `decline`) — concludes with **one** `turn_latency`. Traces exported from logs with
`turn_latency` conclude with **one** `session_summary`, recomputed from `turn_latency` entries at export,
not stored in logs. Tool calls from external MCP clients are not turns: no
`turn_latency`. Implementation: `python/neuroedge/engine/latency.py`.

| Event | Data |
|:---|:---|
| `turn_latency` | `turn` (1, 2, …), `path`, `stages_ms` `{perception, system_two, gate, action, other}`, `total_ms`, `reply_source?`, `usage?` `{prompt_tokens?, completion_tokens?, cost_usd?}` — aggregated from turn's `system_two_call` entries, only when reported by provider (FR-TEL-03) |
| `session_summary` | `turns`, `paths` `{system_1, system_2, fallback, none}` (turn counts), `shares` (ratio of total turns, 4 decimal places), `stages_ms` `{perception, system_two, gate, action, other, total}` — each stage `{sum, max}`, `usage?` (aggregate across turns) |

**Stages** — non-overlapping, summing exactly to `total_ms` (ms, 3-decimal float, non-negative):

| Stage | What is Measured |
|:---|:---|
| `perception` | Input reading and command grammar parsing (typed text / transcript → command); for voice via STT provider (TSK-S3-13), includes STT latency — from dispatching turn audio (T04) until transcript received or STT failure (`stt_unavailable`) |
| `system_two` | Waiting on System 2: all `respond` / `reply` of turn; for voice, from transcript receipt until response (or timeout) arrives |
| `gate` | `ActionContractEngine.evaluate()` — all gates of turn, aggregated |
| `action` | Bodies of `@action` executed after ALLOW, aggregated |
| `other` | Remainder: speech synthesis, coordination, tool pipeline |

Stages opened inside other stages (an `@action` re-invoking `c.do()`) attribute to outer stage.
Clocks use `offset_ms` clock (injectable, virtual in tests), ensuring deterministic test metrics.

**`path`** — who served the turn:

| `path` | When |
|:---|:---|
| `system_1` | Device command grammar / System 1 served turn, System 2 unconsulted — including "có" / "không" ("yes" / "no") spoken to device `ask` prompts |
| `system_2` | System 2 answered (at least one response in turn) |
| `fallback` | System 2 consulted but failed to respond, device answered autonomously (Q-14): `reply_source` is `offline`, `offline_help`, or `knowledge_local` — even if an earlier System 2 round answered. In agents lacking System 2, such answers classify as `system_1` or `none`, depending on command recognition |
| `none` | No model served: command unrecognized without System 2, user clicked confirmation button, or STT failed and device spoke offline fallback (`offline_help`, System 2 unconsulted — `docs/spec/voice_fsm.md` §7) |

`system_one_fallback` (primary System 1 → local grammar, FR-MDL-03) remains a distinct event without
altering `path`. These two events **carry no text** — redaction requires no extra hashing — and **do not
enter decision matching**: replay and goldens ignore them, allowing legacy traces to replay without them and new
traces to replay against older engines. `neuroedge trace show` prints ratios and stages, recomputed from
`turn_latency`.

## 8. By Target

| Target | Tool Calls | MCP Server |
|:---|:---|:---|
| `sim` | Full (§1–§7) | `neuroedge mcp serve` via stdio; `--ui` additionally serves web page for **same session** on 127.0.0.1: MCP calls, typed commands on page (including `:sensor`), and confirmation buttons (§6) execute sequentially under single lock, allowing users on page to adjust sensors and answer `ask` questions opened by MCP calls |
| `linux` | Full | Same as `sim`, on device host |
| `esp32s3` | Gate: C99 walker traversing `NETR` v1 tree generated by `neuroedge build` (Q-23, RFC-0003). Parameter constraints (RFC-0005) and `confirms` (RFC-0006) reside **within** that layout; `call_source` is a `choice` fact like any criterion, indexed by `neuroedge build` (`<gate>.netree.h`). Grammar → synthetic tool call in C: unbuilt (TSK-S5-07) | **Does not** run on MCU. MCP for device routes via gateway or a `linux` host (FR-GW), with device retaining autonomous gate evaluation. MCU **does not act as MCP host**: host (§10) resides where System 2 executes |

Default MCP transport is **stdio**: caller with execution privileges is the operator.
Network transport (Streamable HTTP) introduced in TSK-P2-04 (Q-58, NFR-SEC-09), **disabled by default**, activated
only via `neuroedge mcp serve --http` with full authentication configuration (§8.1). Configuration block for
Claude Desktop generated via `neuroedge mcp desktop-config` — uses absolute paths, as Desktop launches servers
from `/` with minimal `PATH`; emits stdio blocks only.

Two rules keep stdio `mcp serve` alive when abandoned by clients (`--http` lacks these: listens on port, does not hold stdin). Claude Desktop may terminate client before `initialize` while holding stdin open, preventing EOF.

- No `initialize` after `--init-timeout` seconds (default 30) causes process to exit 0 and release
  port. Initialized sessions have no timeout.
- The `--ui` page never crashes MCP. If port is busy, even when explicitly specified via `--port`, the page binds
  to a free port and prints actual URL to stderr.

### 8.1 MCP over Network: `mcp serve --http` (TSK-P2-04, Q-58, Q-32)

Same server, same hardware pipeline as stdio: `SimSession.load`, `build_server`, gates,
single-use verdict tokens, HAL, traces (redacted by default). Only the **gateway port** differs (`mcp_http.py`);
no flags bypass gates, and `call_source` remains `mcp` (§5). MCP SDK provides Streamable HTTP application,
bearer validation middleware, and protected resource metadata (RFC 9728, `/.well-known/oauth-protected-resource`);
`mcp_http.py` supplies TLS context, token validator, and perimeter guards.

**Closed startup.** `--http` requires **all six**: `--tls-cert` and `--tls-key` (server certificate), `--client-ca`
(device certificate issuing CA — mTLS), `--issuer` (authorization server https URL), `--audience` (MCP server https URL,
matching token `aud`; its path is endpoint path, default `/mcp`), `--jwks` (issuer token signing public keys). If any is
missing, or unreadable (certificate key mismatch, empty CA, JWKS lacking signing keys), **exits code 1 with tripartite error, before building session and before
opening any socket**. Binding non-loopback addresses (`--host`) requires no extra flags — full configuration is
mandatory for all addresses. Defaults to `127.0.0.1`, port 8443 (`--port 0` selects random free port).
`--http --ui` runs both on **same session**: remote clients (brain on NeuroEdge Cloud, Q-76) call tools via
network port, while 127.0.0.1 page (port 8765, `--port` then applies to `--http`) represents the **home owner**. Only
the page can answer `ask` questions (`ui` source, §6); MCP lacks confirmation tools and cannot forge `call_source`,
so remote commands can only open questions, never answer them (test
`test_the_door_never_opens_from_the_cloud_without_the_owner_at_home`). Network flags without `--http` rejected
(code 1), not ignored. `--required-scope` (default `neuroedge:call`)
is the sole flag with a default.

**Layer 1 — mTLS, TLS 1.3 or higher (NFR-SEC-04).** Client certificates **mandatory** and must be signed by `--client-ca`;
clients without certificates (or signed by unknown CA, or offering TLS 1.2 only) fail handshake, admitting zero HTTP bytes to
application. Occurs at TLS layer before application code, producing **no trace events**; uvicorn
stderr log is sole footprint.

**Layer 2 — per-device bearer token.** Server acts as OAuth 2.1 *resource server*; token issuance belongs to
`--issuer` (out of scope), and server validates without outbound network verification calls. Tokens are JWTs (RFC 9068); all
conditions below must hold, otherwise **401** (with `WWW-Authenticate: Bearer` pointing to resource metadata) and
nothing forwards to MCP:

| Check | Details |
|:---|:---|
| Signature | Asymmetric algorithms only (`RS*`, `PS*`, `ES*`, `EdDSA`) against `--jwks` keys, matched by `kid` (omitted `kid` allowed only with single key). `none` and `HS*` rejected unconditionally. JWKS containing private keys (`d`), symmetric keys (`oct`), or lacking signing keys **aborts startup**: a resource server holding signing keys can forge its own tokens |
| `iss`, `aud`, `exp`, `iat`, `sub` | All mandatory. `iss` equals `--issuer`; `aud` contains `--audience` (RFC 8707); `exp` unexpired, no clock skew tolerance; `exp` − `iat` at most 7 days (`lifetime_too_long`, DP-A-04: `neuroedge pair renew` issues the next one while the box runs); `sub` is device ID |
| Revocation (`--revoked`, optional) | One certificate thumbprint per line, read again whenever the file changes. A client certificate on the list is cut off right after the TLS handshake, before any HTTP (`revoked_certificate`, DP-A-11); `neuroedge pair rotate` issues the brain a new certificate and lists the old one |
| Certificate binding (RFC 8705) | `cnf.x5t#S256` mandatory and must match SHA-256 of connecting client certificate. Token issued to device A presented with certificate B returns 401; unbound tokens return 401. Both must be compromised together to exploit |
| Scope | Token contains `--required-scope` in `scope` (space-delimited string) or `scp`; missing returns **403** (`insufficient_scope`) |

MCP sessions bind to creator's identity (issuer, `client_id`, `sub`): differing devices, even if authenticated,
cannot hijack sessions (404; `test_a_session_belongs_to_the_device_that_opened_it`). All 401/403 log `mcp_auth_refused` (§7) — fixed `reason` text only, never logging
tokens.

**Single path to gates.** Calls passing both layers become standard `tools/call` like stdio: `ToolCall` with
`source = "mcp"`, schema, `c.do()`, gate, token, HAL; `BLOCK` results remain valid responses, not protocol errors (§4).
Repeating blocked calls does not alter verdicts: gates are deterministic, each attempt generating a `BLOCK` and a trace sequence
(`tests/test_mcp_http.py`, `TODOS.md` #29; `docs/spec/threat_model.md` §2b). Calls execute sequentially (`build_server`), matching stdio.

**Explicitly unbuilt.** No revocation lists: tokens die on expiry (use short lifespans) or when issuer
rotates keys — `--jwks` read **once at startup**, key rotations require restart; client certificate revocations take effect only
by replacing `--client-ca` (no CRL/OCSP checks). Tokens verified upon **request receipt**, so active SSE streams
survive past token expiry until closed. No application-layer rate limiting.
Protected resource metadata served without token (RFC 9728 requirement) — but gated behind mTLS.
No public Python API for network port (`serve_mcp` remains stdio-only); no MCU MCP bridge (TSK-P2-05, I14).
Untested across two physical machines: tests execute in-process on 127.0.0.1 with temporary CAs.

## 9. Compliance

A runtime is certified **NeuroEdge-gated** when it passes the corpus
`fixtures/tool_calls/{valid,invalid}/` with `expected_results.yaml` — bidirectional closure
like gate corpora: every file has an entry, every entry has a file (TSK-S3-24).

- **Case files** specify inputs: `agent` (directory in `fixtures/agents/`), `call`
  (`name`, `arguments`, `source` — runtime-assigned connection source), `facts` (overriding
  `[sim.facts]`), `sensors` (simulated readings prior to call), and `board` (board ID from `boards/`, defaulting
  to target reference board — e.g. `sim-rpi5` for agents requiring PWM or `motion.*`, RFC-0010, RFC-0011).
- **`expected_results.yaml`** declares expected outputs per file: `status`, §4 fields (`reason`,
  `failed_criterion`, `on_block`, `escalated_to` must match exactly; `problems` substring comparison;
  `confirmation`, `fallback` presence must match), `pins` — all pin commands in exact sequence (`pwm`
  commands append `frequency_hz` and `duty` — `duty` is HAL-quantised value, RFC-0010 §9.15) —
  and `motion` — all motion commands and safe-state commands per channel in exact sequence (`command:
  {channel, kind, speed|target, run}`, `safe: {channel, state, cause}`).
- **`valid/`** contains calls matching declared tool `inputSchema` (after string coercion in §2): gate decides,
  `ALLOW` or `BLOCK`. **`invalid/`** contains malformed calls: unknown tool, unknown argument, type mismatch,
  missing required argument, self-declared `call_source` ⇒ `REJECTED`; values exceeding parameter limits
  (`minimum`, `maximum`, `enum`, `maxLength` — RFC-0005) ⇒ blocked by gate, `BLOCK`
  `argument_out_of_range` (§3). No `invalid/` call may result in `ALLOW`. The test runner validates this
  partition, preventing test cases from misplaced directories.

The corpus spans both namespaces: agent `bridge-lamp` (gate explicitly targeting `bridge:muse`, or entire family `bridge` via `call_channel`) and
`open_gate_from_a_bridge_degrades.yaml` in `driveway` (`test_the_corpus_of_tool_calls_covers_every_family`). The runner acts as loader: registering
IDs read from test case `call.source` (§5).

Runner `neuroedge.testing.tool_corpus` executes each case through genuine `dispatch()` of a fresh `SimSession`
— identical to MCP client and System 2 pipelines — then asserts against expected outputs. `neuroedge verify` executes the entire
corpus; `pytest tests/test_tool_corpus.py` additionally routes each case through a live MCP client, verifying result conformity
with `outputSchema` (§4). The distributed wheel bundles the corpus (`neuroedge/_data/fixtures/tool_calls/`), enabling
installed packages to self-verify.

Envelope schemas (`tool-call.v1.json`, including tool descriptions) and results (`tool-result.v1.json`) are frozen
in `schemas/` via [RFC-0015](../rfc/0015-hop-dong-cho-nguoi-tich-hop.md) (TSK-I6-05, Q-58, Q-66), alongside error shapes
(`error.v1.json`) and machine-readable `NE*` error code catalog (`error-codes.v1.json`, Q-63), allowing external OSS implementations
without Python codebase dependencies. Every corpus case validates against them (`python/tests/test_contracts.py`:
`test_every_tool_call_corpus_case_validates_against_the_tool_call_schema`,
`test_every_tool_call_corpus_result_validates_against_the_tool_result_schema`); `fixtures/contracts/` serves as counter-example corpus for
these schemas, with bidirectional closure. Hence the profile shape is **v1**; modifying shapes requires an RFC (`CONTRIBUTING.md` §3).
Compliance corpus licensing not yet under Apache-2.0: `TODOS.md` #57.

## 10. NeuroEdge as MCP Client (Q-27)

System 2 acts as an **MCP host** (legacy: only with `NEUROEDGE_LEGACY_SYSTEM_TWO=1`, Q-83, DP-A-08): every tool it invokes routes through an MCP client
(`ToolHost`, `python/neuroedge/mcp_host.py`), connecting to two server categories:

```text
                  ┌─────────────────────── ToolHost ───────────────────────┐
System 2 ─tool──► │ agent: in-process → build_server(source="system_two")   │─► dispatch() → gate → HAL
 ▲ (≤ max_rounds) │ news:  stdio → [mcp.servers.news], allowlisted tools only │─► untrusted data
 └── result ◄──── └────────────────────────────────────────────────────────┘
```

Six rules:

1. **Device tools accessible exclusively through agent's own MCP server.** All calls route through
   §2. `call_source = system_two` connection-bound (§5). Contract violations raised unmodified
   across in-process connection, not converted to MCP results. Core installs lacking `mcp` extra:
   connection resolves to direct calls — same source, same `dispatch()`; external servers
   skipped with logged reasons.
2. **External MCP servers provide information only.** `agent.toml` explicitly enumerates permitted tools
   (`tools = [...]`) — agent authors attest these lack physical side-effects. Tools outside allowlist
   hidden from models; invocations return `REJECTED`. Server-declared `readOnlyHint` annotations are
   **not** trusted. Third-party tools with physical effects (e.g. Home Assistant) **MUST** be wrapped in
   gated `@action` functions, **or** devices declared as **remote actuators** (`[actuators.<name>]`, RFC-0018,
   [`extension_sdk.md`](extension_sdk.md) §6) — the recommended pattern: commands route via tokens, envelopes,
   and auto-off like pins, whereas `@action` bodies calling MCP or HTTP directly only enforce gates at
   ingress (`neuroedge build` warns when `@action` modules import common network clients). Functions
   executable only within `c.do()`. Name collisions between `server__tool` and `@action` ⇒
   `neuroedge build` raises error.
3. **External tool outputs treated as untrusted data.** Returned to model marked
   `"trust": "untrusted data …"`, never parsed as commands. Traces record `mcp_tool_result`
   (§7 fields) — payload unrecorded. Models acting on instruction-injected outputs still encounter gates
   (`test_prompt_injection_in_the_news_still_meets_the_gate`).
4. **Unreachable servers skipped and reported**: log `mcp_server_unavailable` (§7); device tools continue operating. Models informed in `instructions` which sources
   are disabled and why (including missing `mcp` SDK), enabling user notifications of *temporary unavailability*
   — never claiming tools do not exist, never hallucinating. REPL prints warnings; `run` banner lists
   servers and statuses. Complete network loss ⇒ no System 2 ⇒ host unopened; local grammar
   dispatches directly (§1, Q-14).
5. **Local fallback for actions**: System 2 failing to answer free-form utterances ⇒ device
   **announces available local commands** (one sample sentence per tool in `commands.toml`,
   `reply_source = offline_help`). Never guess actions from approximate phrasing — incorrect
   guesses cause unintended physical actions; users restate commands, which traverse gates as normal.
6. **Bounded loops** (FR-MDL-11): tool results return to model in `state["messages"]`,
   up to `max_rounds` (default 4, range 1..16); exceeding ⇒ `system_two_rounds_exceeded`. Gate returning
   `ask` ⇒ loop halts, device speaks gate `message`; questions open only when permitted by §6
   (`confirms` present and single "có" ("yes") suffices). Models cannot answer on human's behalf (§6).

Configuration (`agent.toml`, outside `schemas/`):

```toml
[mcp]
max_rounds = 4

[mcp.servers.news]                # tools presented to model as news__<tool>
command = "python"                # "python" / "python3" = running interpreter
args    = ["mcp/news_server.py"]  # relative to agent directory
tools   = ["headlines"]           # allowlist — informational tools only
# env = { NEWS_FILE = "..." } · timeout_s = 10
```

Models driving System 2 declared in `[system_two]` of `agent.toml` (LiteLLM or custom adapter,
TSK-S2-11, `python/neuroedge/models/providers/`): `tools` and `state["messages"]` rounds formatted
per OpenAI function calling; non-JSON tool arguments forwarded raw to dispatch, resulting in `REJECTED`
calls (§2) — no guessing. Model failures ⇒ `system_two_unavailable`.

Working example: `fixtures/agents/home-voice/mcp/news_server.py`. Connections open per
turn; persistent inter-turn connections and outbound HTTP transports deferred
(`TODOS.md` #25).
