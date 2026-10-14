# RFC-0015: Freezing Contracts for Integrators — Gated Tool Profile, `board.v1` Version Identifier, `NE*` Error Code Catalog

| | |
|:---|:---|
| **RFC Code** | 0015 |
| **Title** | Four new schemas in `schemas/` (`tool-call.v1`, `tool-result.v1`, `error.v1`, `error-codes.v1`) and the `schema` version identifier key for `board.v1` — TSK-I6-05 |
| **Affected contracts** | `schemas/` *(add four files; `board.v1.json` adds exactly one optional `schema` key)* · board loading rules (`python/neuroedge/hal/board.py`) · single source of truth for error code catalog (PRD Appendix B ↔ `python/neuroedge/errors.py`; update `CONTRIBUTING.md` §8.1) · **does not** touch `gate.v1`, `trace.v1`, evaluation semantics, `NETR`, `digests.lock`, three canonical traces |
| **Related PRD requirements** | FR-MDL-10, FR-GOV-01, FR-GOV-02, FR-HAL-02, FR-DX-04 |
| **Proposer** | — |
| **Date opened** | 2026-10-03 |
| **Status** | ✅ Approved (2026-10-04) — lead engineer signed off on PR #93; decisions in §10 (Q-66); implemented in two PRs (§8) |
| **Approvers** | **Lead Engineer — mandatory** (adding schemas to `schemas/`, touching `board.v1`, changing the single source of truth for the error code catalog). **Product Owner** for open questions in §10 of a product or licensing nature (Q10.4, Q10.5) |

> **When an RFC is required:** `CONTRIBUTING.md` §3 — editing `schemas/*.json` (adding schemas and modifying `board.v1.json`).
> Task: TSK-I6-05. Foundational decisions: `neuroedge-prd.md` §15 **Q-58** (freezing the Gated Tool Profile before public release,
> replacing the "when an external client exists" milestone of `TODOS.md` #23), **Q-63** (expanding scope: adding the `board.v1` version identifier key
> and the machine-readable error code catalog; `agent.toml` remains outside `schemas/`), Q-45 (schemas under Apache-2.0), Q-64
> (`docs/spec/python_api.md`: file-based contracts have their own versions, outside the Python API).
> Target: I6 exit criterion 8 — *"Gated Tool Profile, `board.v1` version identifier, and error code catalog live in `schemas/`
> via an approved RFC; all cases in `fixtures/tool_calls/` validate against that schema."*
> Publishing schemas to `https://schema.neuroedge.dev` is TSK-I6-02, **outside** this RFC (§3f only notes `$id` for consistency).
> All assertions about code below were reconciled against the repository at `87db7c7`; discrepancies between spec, corpus, and code are in §9.

## 1. Problem

Q-58 aims to allow another OSS project (Home Assistant MCP client, voice server, agent framework on another machine) to call the HAL and gate
via NeuroEdge **without reading Python code**. Today, three things they need are located where they cannot use them:

1. **Tool calls and their results are only specified in prose.** `docs/spec/tool_calling.md` §1 (envelope), §4 (result), §9 (corpus) describe
   the shape; the *executable* shape lives in code: `ToolCall` (`python/neuroedge/actions/tools.py`, dataclass `name`, `arguments`,
   `source`, `id`) and `result_schema()` (same file), a function constructing a JSON Schema dict from `Reason` and `ACTIONS` at runtime. A Rust
   or Go SDK cannot generate types from prose, nor run `result_schema()`. The corpus `fixtures/tool_calls/` (28 cases: 16 `valid/`, 12
   `invalid/`) can only be validated using the Python runtime (`neuroedge.testing.tool_corpus`), not using a schema.
2. **Board files carry no version.** A gate carries `schema: neuroedge.gate/v1` (`schemas/gate.v1.json`, `const`); a trace carries `$schema`
   (`schemas/trace.v1.json`, mandatory, `format: uri`); `boards/*.toml` carries nothing. Specific consequence, verified by trial run: `board.v1.json` is not
   closed (`additionalProperties` is not declared), so `validate_board_document` accepts even
   `{"schema": "garbage", "nonsense": 1, "board": …, "capabilities": …}`, and `BoardProfile.to_document()` drops those two keys when serializing back. An
   older runtime reading a board profile from a different major version will **silently ignore all keys it does not recognize** — for a board, that means ignoring hardware limits
   (RFC-0007 places `envelope` there) rather than merely losing a feature.
3. **The error code catalog lives in two handwritten places.** PRD Appendix B (markdown table, Vietnamese) and `python/neuroedge/errors.py` (classes). Neither
   is machine-readable; no test forces them to match; `CONTRIBUTING.md` §8.1 designates PRD Appendix B as the "single source of truth" but the promise
   at the start of Appendix B ("Class names and `NE…` codes match `errors.py`") is broken in three places (§9, F4). Devices also emit codes: `targets/esp32s3/components/ne_gate/src/ne_token.c`
   returns strings `"NE1001"` / `"NE1002"`, and `actuator_command_rejected.code` in traces carries them.

## 2. Why the Current Schema Does Not Solve This

- `schemas/` holds only three files, and `python/tests/test_schemas.py::test_schemas_directory_holds_exactly_the_three_frozen_schemas` locks down exactly three names —
  "a fourth schema appearing without an RFC is also a violation". There is no schema yet for tool calls, results, or errors.
- `board.v1.json`: `required: ["board", "capabilities"]`, no `schema`, no `additionalProperties`. There is no place for a board to declare "I am
  v1" or "I am v2", and no rule for a reader to reject unfamiliar versions. Gate has this (`const`), trace has `$schema` but **it is not pinned**
  (`format: uri` accepts any URI; only `neuroedge.trace.TRACE_SCHEMA_ID` writes correctly) — so "gates and traces already have version identifiers" (roadmap
  TSK-I6-05) is true for gates, but only half true for traces (§9, F6).
- `tool_calling.md` §4 explicitly states the result schema is generated from code and MCP clients validate `structuredContent` against it, but it is **closed**: `additionalProperties:
  false`, `reason` is an `enum` of `Reason` (10 values, expanded twice in ten days: RFC-0005 added `argument_out_of_range`, RFC-0009 added `value_out_of_range` — `git log -S` on `engine/verdict.py`). Freezing as-is means every new `Reason` is a `v2` for every client validating
  `outputSchema`. A deliberate decision is required (§3b); it cannot simply be "copied from code".
- The corpus is insufficient to validate a schema: 28 cases touch only 3 of 10 `reason` values (`condition_not_met` ×8, `argument_out_of_range` ×5, `criterion_unavailable` ×1),
  4 of 5 `source` values (no case for `system_one`), all 4 `on_block` values, all 3 `status` values (§9, F2). A schema passing the corpus without ever seeing
  `budget_exceeded` has not been tested.

## 3. Proposed Changes

Four new files and one new key. `$id` follows PRD Appendix C (`https://schema.neuroedge.dev/<type>/v<n>.json`); draft 2020-12 like the three existing files; English
descriptions like `gate.v1.json`.

### 3a. `schemas/tool-call.v1.json` — `ToolCall` Envelope

Extracted from `tool_calling.md` §1, `ToolCall` (`tools.py`), and `CASE_KEYS`/`CALL_KEYS` (`testing/tool_corpus.py`). Two shapes, because spec §1 states **the caller does not declare `source`**:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://schema.neuroedge.dev/tool-call/v1.json",
  "title": "NeuroEdge Gated Tool Profile — ToolCall envelope v1",
  "$ref": "#/$defs/call",
  "$defs": {
    "id":        { "type": "string", "description": "Provider-assigned; empty or absent: the dispatcher numbers it call_1, call_2…" },
    "name":      { "type": "string", "minLength": 1 },
    "arguments": { "type": "object", "default": {} },
    "source":    { "enum": ["local_grammar", "system_one", "system_two", "mcp", "test"],
                   "description": "Assigned by the runtime from the connection (tool_calling.md §5); never the caller's to state." },
    "request": {
      "description": "What a caller sends. No `source`: a request that states one is refused at the envelope.",
      "type": "object", "required": ["name"],
      "properties": { "id": { "$ref": "#/$defs/id" }, "name": { "$ref": "#/$defs/name" }, "arguments": { "$ref": "#/$defs/arguments" } },
      "additionalProperties": false
    },
    "call": {
      "description": "The envelope the dispatcher holds, and the data of the `tool_call` trace event: a request plus the assigned source.",
      "type": "object", "required": ["name"],
      "properties": { "id": { "$ref": "#/$defs/id" }, "name": { "$ref": "#/$defs/name" },
                      "arguments": { "$ref": "#/$defs/arguments" }, "source": { "$ref": "#/$defs/source" } },
      "additionalProperties": false
    },
    "input_schema": { "…": "§3a.2" },
    "tool": { "…": "§3a.2" }
  }
}
```

Verified by trial run: the document above is valid draft 2020-12, and **all 28 `call`s in `fixtures/tool_calls/` validate against `#/$defs/call`**; `{"name": "a", "source": "mcp"}` is rejected by `#/$defs/request`, while `{"name": "a"}` is not.

- **`name`** has `minLength: 1` and no `pattern`: an unknown tool is `REJECTED` in step 2 of `dispatch()` (§2), not an envelope error (`unknown_tool.yaml`). An empty `name`
  (`parse_tool_calls` produces `""` when payload has no name) still proceeds to `REJECTED` in runtime; the schema rejects earlier — invalid envelope ≠ rejected call.
- **`arguments`** is an open `object`: types of individual parameters are the responsibility of the `inputSchema` **of each individual tool** (§3a.2), not the envelope. The reserved key `__unparseable__` (inserted by
  `parse_tool_calls` when provider JSON is malformed; `dispatch` ⇒ `REJECTED` "unknown argument") is currently **not in the spec** (§9, F8); this RFC adds it to
  `tool_calling.md` §2, not into the schema.
- **`source`**: exactly five values of `SOURCES`; tests enforce both sides (§7). Closed set. Adding a value is relaxing an `enum` (does not break any valid file) but changes the contract
  of `call_source` in gates (§5 of spec; `choice` index in `NETR`), so it still requires an RFC — already a rule (`tool_calling.md` §5).
- **Network (§8.1 of spec) adds nothing to the envelope.** A call over `mcp serve --http` has `source = "mcp"`, just like stdio; gates do not distinguish the two ingress points. Authentication refusal happens
  **before** the envelope: HTTP 401/403, no `ToolResult`, no new `status` value; the trace event is `mcp_auth_refused` (§7 of spec), outside the result schema. Device identity
  (token `sub`) is not an envelope field. If a gate wants to specifically restrict network ingress or a specific device, it requires adding values to `source` — a change that
  this RFC does not make and deliberately leaves unblocked (§10, Q10.11). *(At the time of writing, §8.1 and `mcp_http.py` are on branch `feat/mcp-network`, commit `baff0ae`; the RFC references rather than copies.)*

**3a.2. Tool description (`tools/list`).** `mcp_tool()` (`tools.py`) returns `{name, description, inputSchema, outputSchema}`; `input_schema()` generates a JSON Schema **subset** — `type` ∈ {`string`, `integer`, `number`, `boolean`},
`default`, `required`, `additionalProperties: false`, plus `minimum`/`maximum`/`enum`/`maxLength` from the gate (RFC-0005, `engine/arguments.py::schema_hint`). `$defs.input_schema` describes precisely that subset and `$defs.tool` describes
the 4-tuple of fields, with `outputSchema` being `tool-result.v1` pinned to `tool` (§3b). This is the part that Profile implementers need to know what "call conforms to `inputSchema`" means — the boundary between `valid/` and `invalid/` in the corpus (§9 of spec) is placed right there
(`testing/tool_corpus.py::_conforms`). Whether to include this part or leave it outside is Q10.3.

**Schema boundaries — stated clearly to avoid misinterpretation.** The schema **cannot** express: string → number/bool type coercion (§2 step 3 of spec: grammar slot is string), gate parameter constraints (checked **after** schema, `BLOCK argument_out_of_range` rather than `REJECTED`, §3 of spec),
`call_source` facts, or whether a tool exists. A successful schema validation **does not** prove a runtime complies with the Profile; the compliance test suite is the corpus `fixtures/tool_calls/` executed via `dispatch()` — identical reasoning to invariant `CHANGELOG.md` §3.3 #1 for gates.

### 3b. `schemas/tool-result.v1.json` — Results

Fixed into a static file matching the exact shape `result_schema()` generates today (printed and verified), with **two deliberate relaxations** so that the contract survives future RFCs without requiring a `v2` bump:

| | `result_schema()` today | Proposed `tool-result.v1.json` | Rationale |
|:---|:---|:---|:---|
| `tool`, `status`, `gate`, `failed_criterion`, `message`, `escalated_to`, `problems`, `fallback`, `confirmation` | as in `tools.py` | **retain unchanged** types, conditional requirements (`BLOCK` ⇒ `gate`, `on_block`; `REJECTED` ⇒ `problems`) | already verified by corpus and `test_an_mcp_client_gets_the_same_result_and_its_sdk_accepts_it` |
| `status` | `enum` ALLOW · BLOCK · REJECTED (in `fallback`: ALLOW · BLOCK) | **closed**, as today | adding a status changes the meaning of the result for all clients ⇒ `v2` |
| `on_block` | `enum` `ACTIONS` (`deny`, `escalate`, `ask`, `degrade`) | **closed**, as today; test enforces match with `gate.v1.json` | adding a blocking action is already an RFC on `gate.v1` (RFC-0004, RFC-0006) |
| `reason` | `enum` of `Reason` (10 values) | `type: string`, `pattern: ^[a-z][a-z0-9_]*$`, with list of known values in annotation `x-neuroedge-known`; test enforces list = `Reason` bidirectional | `Reason` has expanded twice in ten days; a client encountering an unknown `reason` under `status: BLOCK` **must** treat it as blocked (fail-closed, already the meaning of `BLOCK`), not a malformed result. **Proposed, pending decision: Q10.1** |
| Objects (`additionalProperties`) | `false` at root, `fallback`, `confirmation` | `true` | matches PRD §10.3 versioning policy for traces — "adding optional fields does not bump version". Tests (§7) enforce that **code** only emits declared keys, so relaxing in schema does not allow code to silently add keys. **Q10.2** |

Direction of correctness: "strict in what we accept, tolerant in what clients must accept". Envelope in §3a is closed (`additionalProperties: false` — we reject unknown keys);
result is open (client must not break because we added a field).

**Single source of truth.** `result_schema(tool)` stops building dicts manually: it **reads `schemas/tool-result.v1.json`** (via `neuroedge.paths.schema_path`), then pins `tool` (and strips `$id`/`$schema` when embedding into MCP `outputSchema`). `Reason` and `ACTIONS` remain the
source for code; tests (§7) lock bidirectional agreement between them and the file. Result payload content is still generated by `ToolResult.content()` — this RFC does not change a single byte of it.

### 3c. `board.v1` Version Identifier Key

All existing `boards/*.toml` files must remain valid verbatim, and the mechanism must be independent of keys RFC-0007 and RFC-0010→0013 are adding to `board.v1.json` (touching only one new key, `schema`, at the root level).

```toml
# Root level of boards/*.toml — first line of file
schema = "neuroedge.board/v1"

[board]
id = "esp32s3-box-3"
…
```

```jsonc
// board.v1.json — add to "properties" (do not add to "required")
"schema": {
  "description": "Schema version identifier. Absent means neuroedge.board/v1. Frozen at neuroedge.board/v1.",
  "type": "string",
  "const": "neuroedge.board/v1"
}
```

Rules (proposed; the baseline reality supporting them — open schema, `to_document()` drops unknown keys — verified by trial run, §9 F7):

1. **Name and value format follow gate:** key `schema`, value `neuroedge.<type>/v<major>` (`neuroedge.gate/v1`). Trace-style `$schema` cannot be used in TOML (bare TOML keys cannot begin with `$`).
2. **Optional in `v1`:** absent ⇒ interpreted as `neuroedge.board/v1`. Three existing profiles remain valid without change; the implementation PR **adds** this line to the three files so examples teach correctly, and `BoardProfile.to_document()` emits it.
   From `v2`, the `v2` schema **requires** this key (with `const: neuroedge.board/v2`).
3. **Reader rejects unfamiliar versions before schema validation.** `load_board_document` checks: if `schema` is present and not in supported set (`SUPPORTED_BOARD_SCHEMAS = {"neuroedge.board/v1"}`) ⇒ `BoardCapabilityError` (NE3001), 3-part message stating
   parsed value, supported set, and "upgrade neuroedge". Checked **before** validation because `board.v1.json` is open: validating against v1 schema will never catch a v2 file — it would accept the file and ignore unrecognized keys. This is what the `schema` key achieves; it does not replace
   closing the schema (Q10.6 addresses the rest).
4. **Not the revision/model number of a board.** `board.id` already carries board suffixes (`villa-panel-v2`, PRD Appendix C); `schema` is the version of the *declaration format*, not of hardware.
5. **`board.v1.json` adds only this key.** Another worker is adding RFC-0007/0010→0013 keys to the same file; the two changes touch disjoint keys and merge cleanly. Implementation order is in §8.

### 3d. Machine-Readable `NE*` Error Code Catalog

Two files, one source of truth.

**`schemas/error.v1.json`** — shape of serialised error (`NeuroEdgeError.as_dict()`, `errors.py`; Studio and `sim` page return it under `"error"`, `studio/server.py`, `sim/ui.py`). This is the **complete** shape; the looser shape in `docs/spec/studio.md` (item 8: `{"code"?, "where"?, "why", "how"?}`, and 501 stub containing only `why`) is a separate Studio API contract, outside this schema (F12):

```json
{
  "$id": "https://schema.neuroedge.dev/error/v1.json",
  "type": "object",
  "required": ["code", "where", "why", "how"],
  "properties": {
    "code":  { "type": "string", "pattern": "^NE[0-9]{4}$" },
    "where": { "type": "string", "minLength": 1 },
    "why":   { "type": "string", "minLength": 1 },
    "how":   { "type": "string", "minLength": 1 },
    "principle": { "type": "string", "pattern": "^[1-5]$" },
    "reason":    { "type": "string" }
  },
  "allOf": [
    { "if": { "properties": { "code": { "const": "NE2003" } }, "required": ["code"] }, "then": { "required": ["principle"] } },
    { "if": { "properties": { "code": { "const": "NE1002" } }, "required": ["code"] }, "then": { "required": ["reason"] } }
  ],
  "$defs": { "catalog": { "…": "shape of error-codes.v1.json, §below" } }
}
```

`code` uses `pattern`, **not** `enum`: adding an error code does not change this schema. Non-empty `where`/`why`/`how` is FR-DX-04; currently `NeuroEdgeError.__init__` does not enforce this — the implementation PR scans and fixes any place emitting empty strings (if any) before
freezing. `principle` is a **string** because `GateInheritanceError.as_dict()` returns `str(self.principle)` even though the attribute is `int` (§9, F5): freeze what is currently running, do not alter.

**`schemas/error-codes.v1.json`** — catalog, a data document self-declaring `"schema": "neuroedge.error-codes/v1"` and validating against `error.v1.json#/$defs/catalog`. Each entry:

```json
{ "code": "NE1002", "name": "TokenReplayError", "parent": "ActionContractViolation", "status": "stable",
  "fields": ["reason"], "also_a": [], "aliases": [], "rfc": null, "since": "0.1" }
{ "code": "NE1003", "name": "EnvelopeRefusedError", "parent": "ActionContractViolation", "status": "stable", "rfc": "RFC-0007" }
{ "code": "NE5001", "name": "PerceptionUnavailableError", "parent": "NeuroEdgeError", "status": "stable",
  "aliases": ["ProviderUnavailable", "MalformedResponse", "SpeechUnavailable", "CameraUnavailable", "VisionUnavailable"] }
{ "code": "NE0000", "name": "NeuroEdgeError", "parent": null, "status": "stable", "general": true }
```

Fields: `code` (unique, **never reused**), `name` (public class in `errors.py`), `parent`, `status` (`stable` · `reserved` — placeholder code for not-yet-implemented class; NE1003 of RFC-0007 is `reserved` until PR #91 adds the class), `fields` (extra keys beyond the four standard keys in `as_dict()`),
`also_a` (other Python class it inherits from — `ToolCallError` is also a `ValueError`; needed only by Python SDK), `aliases` (subclasses sharing the code, `NE5001`), `general` ("unclassified" code — NE0000, NE2000: recipient **must not** branch on it), `rfc`, `since`.
Today: 17 `stable` entries (NE0000, NE1001→NE1004, NE2000→NE2003, NE3001→NE3003, NE4001→NE4004, NE5001), 0 `reserved` entries (§10 question 13). NE5001 has five subclasses sharing the code (`aliases`): three provider and voice classes, plus `CameraUnavailable`, `VisionUnavailable` from RFC-0012.

**Source of truth — proposed decision.** `schemas/error-codes.v1.json` is the **single** source declaring *which codes exist, class names, parent-child relationships, status*. The other two locations are **validated** against it, without re-declaring independently:

| Location | What it holds | Validated by |
|:---|:---|:---|
| `schemas/error-codes.v1.json` | identity and structure: code, class, parent, status, extra keys | *(is source)* + self-validates against `error.v1.json#/$defs/catalog` |
| `python/neuroedge/errors.py` (and subclasses sharing codes) | Python implementation | bidirectional closed test: every `NeuroEdgeError` class in package ↔ one entry (or `aliases`); `code`, `parent`, `fields` match; `reserved` entries have no class; every `name` is in `neuroedge.__all__` (already covered by `test_every_error_class_of_the_package_is_public`) |
| PRD Appendix B | **prose** (timing, cause, system behavior — Vietnamese, FR-DX-04) | bidirectional closed test on (class, code) pairs between table ↔ catalog; prose remains in PRD, not copied to JSON |
| `targets/esp32s3/components/ne_gate/` | two strings `NE1001`, `NE1002` | test: every `NE\d{4}` in `targets/` ⊂ catalog |

Why PRD or `errors.py` is not the source: PRD is human-readable markdown prose in Vietnamese — parsing that table to generate public Apache-2.0 data is fragile, and it lacks parent/status columns; `errors.py` is PolyForm NC licensed (`LICENSING.md`), so a Rust SDK cannot/should not
generate code from it. Cost: `CONTRIBUTING.md` §8.1 row "Error code `NE…`" changes single source of truth from PRD Appendix B to this catalog (PRD remains the single source of truth for *prose*), and rule 4 of each slice ("new error class has code in PRD Appendix B and `errors.py`") adds "and in catalog".

**Versioning rules for catalog.** Adding a code, or adding `fields`/`aliases` keys ⇒ relaxation, same `v1`. Changing meaning, renaming class, removing or reusing a code ⇒ breaking, `v2`. A `reserved` code transitioning to `stable` when the class is introduced — not a breaking change.

### 3e. Corpus Validation Against New Schemas (Exit Criterion 8)

- Each `call` across 28 cases in `fixtures/tool_calls/{valid,invalid}/` (plus empty `id`) validates against `tool-call.v1.json#/$defs/call`. Including `invalid/` cases: *"invalid"* in the corpus means not conforming to the **tool's** `inputSchema`, not a broken envelope (§3a) — a broken envelope case belongs in `fixtures/contracts/`, not this corpus.
- `ToolResult.content()` of each case (real result, executed via `dispatch()` on a fresh `SimSession`, including nested `fallback`) validates against `tool-result.v1.json`.
- `outputSchema` published by `neuroedge mcp serve` for all tools **equals** `tool-result.v1.json` pinned to `tool` (verified for every tool of every agent in `fixtures/agents/`).
- The `tool_call` trace record (`dispatch`) validates against `#/$defs/call` — **without** modifying `trace.v1.json`.
- Because the corpus covers only 3/10 `reason` values and 4/5 `source` values (§2), enum coverage comes from a new corpus, **`fixtures/contracts/`** (§7): valid and invalid minimal documents for each schema (`tool-call`, `tool-result`, `error`, `board`), each file matching one entry in `expected_errors.yaml`, bidirectionally closed like all other corpora
  (`CONTRIBUTING.md` §3). Tests enforce that `valid/` files collectively cover **all** known `status`, `on_block`, `source`, `reason` values and all codes in the catalog.
- The implementation PR adds a `source: system_one` case to `fixtures/tool_calls/` (regular PR, per closure rule) so the corpus covers all five sources.

### 3f. Versions, Paths, Publishing

| File | `$id` | Rules |
|:---|:---|:---|
| `tool-call.v1.json` | `https://schema.neuroedge.dev/tool-call/v1.json` | PRD §10.3 / FR-GOV-02: path `/v1`; adding optional fields or relaxing `enum` does not bump; renaming, removing, or tightening requires `v2` with transition period (`docs/architecture/vi/16-ecosystem-landscape.md` §6 pillar 3) |
| `tool-result.v1.json` | `…/tool-result/v1.json` | as above |
| `error.v1.json`, `error-codes.v1.json` | `…/error/v1.json`, `…/error-codes/v1.json` | as above; catalog-specific rules in §3d |
| `board.v1.json` | unchanged | `schema` key in §3c |

The implementation PR adds four rows to PRD §10.3 matrix. `$id` matches so that TSK-I6-02 only serves files; this RFC does not handle hosting. Licensing: `schemas/` is Apache-2.0 (`LICENSING.md`); the four new files belong there. **Corpus** is not yet Apache-2.0 (§9, F3, Q10.4).

## 4. Compatibility Impact

| Item | Impact |
|:---|:---|
| Do currently valid files remain valid? | **Yes**, including three `boards/*.toml` (optional `schema` key) and all gates and traces. A board file carrying a `schema` key with a value other than `neuroedge.board/v1` — valid today because the schema is open — **will become invalid**: this is formally tightening loose validation. None exists in the repo (`grep '^schema' boards/` is empty) and the key is not documented anywhere, so this is deemed acceptable; **lead engineer explicitly signs off on this** (Q10.5) |
| Do currently invalid files become valid? | Tool results: `reason` outside current `Reason` enum and extra keys previously violating closed `outputSchema` now become valid (§3b) — intentional relaxation. None otherwise |
| Does it require bumping schema version (`v1` → `v2`)? | **No.** Four new schemas originate at `v1`; `board.v1` only adds one optional key |
| Impact on issued gate hashes / signatures? | None |
| Impact on three canonical trace files? | None: `trace.v1.json` and `fixtures/traces/` unchanged |
| Does any gate in `digests.lock` change digest? | None |
| Must `NETR` layout or C walker change? | None |
| Does any expected answer in tool call corpus (`expected_results.yaml`) change? | No expected answers change; **adds** one `system_one` case and entry (§3e) |
| `python/tests/test_schemas.py` | Changes: exact 3-file set ⇒ exact 7-file set (`SCHEMA_IDS` adds four); stronger, not weaker — still locks name set, still checks `$id` and `$schema` |
| Public Python API (`python_api.md`) | `result_schema` is not a public name; `ToolCall`, `ToolResult` do not change shape. `BoardProfile.to_document()` adds one key; `load_board*` raises `NE3001` additionally for unfamiliar versions (additive, MINOR per `python_api.md` §3) |
| CLI | Unchanged |

## 5. Safety Impact

This RFC does not touch `gate.v1`, evaluation semantics, or the path to HAL; no gate becomes looser, no B.5 principle or fail-closed default changes. Four scrutiny points:

1. **Closed envelope, runtime-assigned source.** `$defs/request` lacks `source` and has `additionalProperties: false`, so a validator at ingress (`#/$defs/request`) **rejects** calls self-declaring `source` at envelope level, aligned with today's `REJECTED`
   (`caller_declares_call_source.yaml` is a parameter case, not an envelope case — two layers of defense). `source` exists only in `#/$defs/call`, assigned envelope.
2. **Relaxing results does not relax permissions.** `tool-result` describes output; a client treating an unknown `reason` under `BLOCK` as blocked cannot turn `BLOCK` into `ALLOW`. Client rule documented in `tool_calling.md` §4 upon implementation: *"`status` governs; `reason` is explanation only — never branch ALLOW based on `reason`"*.
3. **Board reader rejects unfamiliar versions (fail-closed).** Today an older runtime reading a newer board drops keys it does not recognize. The `schema` key only protects across **major version** boundaries; extra keys added *within* `v1` (such as `envelope` in RFC-0007) that an older reader does not understand are still ignored. That is a real vulnerability outside this RFC — Q10.6.
4. **Error code catalog.** `reserved` codes prevent an SDK from reusing a reserved code (NE1003 prior to PR #91). No error behavior changes. Devices emit only `NE1001`/`NE1002`; test `targets/` ⊂ catalog preserves that.

Answer to "is there any avenue making gates looser?": **No**. Lead engineer approval is required due to `schemas/` and `board.v1` scope, not gate safety.

## 6. Alternatives Considered and Rejected

| Alternative | Rejection rationale |
|:---|:---|
| A single `tool-profile.v1.json` file containing both envelope and results | Read by two different parties (runtime receives envelope, client checks result — and MCP SDK already validates `outputSchema` per tool); two `$id`s allow independent `$ref` and independent version bumps. Not a strong opinion: Q10.7 |
| Copying `result_schema()` verbatim (closed result, `reason` as `enum`) | Every new `Reason` or field becomes `v2` for all clients; `Reason` has expanded twice in ten days. Rejected in §3b, but is a product decision — Q10.1, Q10.2 |
| Mandatory board version identifier right in `v1` | Breaks three existing files and all user-authored board profiles (count unknown): violates RFC template rule "currently valid files must remain valid" |
| `$schema` key (URL) like traces, or `[board] schema`/`version` | `$schema` is not a bare TOML key; nesting under `[board]` requires readers to parse a table before knowing version. Root + `neuroedge.<type>/v<n>` matching gate is most consistent |
| Closing `board.v1.json` (`additionalProperties: false`) to catch unknown keys | Tightening: files with unknown keys valid today would break ⇒ `v2`. Outside "version identifier" scope; Q10.6 |
| Generating error catalog **from `errors.py`** (code as source) | `errors.py` is licensed under PolyForm NC and lacks status column (`reserved`), shared-code subclass relationships, `general`. Loses "single source of truth" when a Rust SDK wants to contribute codes |
| Extracting catalog **from PRD Appendix B table** (PRD as source) | PRD is a prose contract, unstructured; parsing markdown to generate public data is fragile and forces every table formatting change to become a contract change. PRD holds **prose**, catalog holds **structure** |
| Embedding catalog into `error.v1.json` (single file, `oneOf` per code) | SDKs need an array to iterate; 20-branch `oneOf` is hard for code generation and conflates two purposes (validating an error ↔ enumerating codes). Two files, single source |
| `code` in `error.v1.json` as `enum` of codes | Every new code requires editing schema. `pattern` + catalog cleanly decouples the two concerns |
| Placing `agent.toml` and `fixtures/tool_calls/expected_results.yaml` into `schemas/` | `agent.toml` remaining outside `schemas/` is decided (`tool_calling.md` §9, Q-63). Corpus case and expectation format: deferred alongside TSK-I6-02 — Q10.4 |
| Freezing JSON schema of decision tree as well | Already rejected in Q-63: the real contract is `NETR` byte layout (RFC-0003, RFC-0009) |

## 7. Verification Evidence

Tests below are **proposed names** — they do not exist until the RFC is approved. The "existing" column indicates current tests that remain passing.

- [x] *(PR A completes `tool-call`, `tool-result`, `error` parts: `test_every_error_code_of_the_catalog_has_a_valid_error_example`, `test_every_known_reason_and_every_source_appears_in_a_valid_contract_example`, `test_the_corpus_of_tool_calls_covers_every_source`; PR B adds `board/valid/sim-default.json`, `board/valid/without_schema_key.json`)* Valid examples added to `fixtures/`: `fixtures/contracts/<tool-call|tool-result|error|board>/valid/` — covers all `status`, `on_block`, `source`, known `reason` values, two-level nested `fallback`, all catalog codes; one `source: system_one` case in `fixtures/tool_calls/valid/`
- [x] *(PR A completes all cases except board cases; PR B adds `board/invalid/schema_v2.json`; `test_every_contract_example_has_an_expectation_and_every_expectation_an_example`, `test_an_invalid_contract_example_fails_the_way_its_expectation_says`)* Invalid examples with expectations (`fixtures/contracts/expected_errors.yaml`, bidirectionally closed): envelope with `source` in `request`; empty `name`; `arguments` as array; `source` outside five values; `BLOCK` result missing `gate`; `REJECTED` missing `problems`; `status` outside three values; `NE2003` error missing `principle`; malformed `code`; board with `schema: neuroedge.board/v2`
- [x] Automated tests *(PR A and PR B)*:
  - [x] `test_every_tool_call_corpus_case_validates_against_the_tool_call_schema` *(exit criterion 8)*
  - [x] `test_every_tool_call_corpus_result_validates_against_the_tool_result_schema`
  - [x] `test_the_published_output_schema_of_every_tool_is_the_frozen_result_schema_pinned_to_its_name`
  - [x] `test_a_recorded_tool_call_event_validates_against_the_envelope_schema`
  - [x] `test_the_tool_call_schema_and_the_dataclass_agree` (`ToolCall` fields, `SOURCES`, `CASE_KEYS`/`CALL_KEYS` from `tool_corpus.py`)
  - [x] `test_the_known_reasons_of_the_schema_are_exactly_the_Reason_enum` · `test_the_on_block_enum_is_the_gate_schemas` *(action: `[x]`)*
  - [x] `test_the_mcp_server_emits_only_documented_result_keys` (locks against "schema relaxation allowing code to add keys silently")
  - [x] `test_the_error_catalog_and_errors_py_agree_both_ways` · `test_every_error_class_of_the_package_has_a_catalog_entry` *(action: `[x]`)* · `test_the_prd_error_table_and_the_catalog_agree_on_class_and_code` · `test_every_error_code_in_targets_is_in_the_catalog` *(action: `[x]`)* · `test_a_reserved_code_has_no_class` *(action: `[x]`; `test_the_prd_error_table_and_the_catalog_agree_on_class_and_code` also `[x]`)*
  - [x] `test_every_serialised_error_validates_against_the_error_schema` (runs all error classes with sample data; catches empty strings)
  - [x] `test_a_board_with_a_schema_key_of_another_version_is_refused_before_validation` · `test_a_board_without_a_schema_key_is_read_as_v1` · `test_every_shipped_board_declares_its_schema` · `test_board_to_document_round_trips_the_schema_key` *(PR B, `tests/test_boards.py`; added `test_a_board_document_in_memory_is_refused_for_another_version_too`)*
  - [x] `test_schemas_directory_holds_exactly_the_seven_frozen_schemas` (changed from "three")
- [x] *(PR A, PR B: `scripts/wheel_smoke.sh` green on installation, added four files to checklist and a check for `result_schema()` from wheel; ruff, pytest green; `gate lint` / `verify` unchanged — still in CI)* `neuroedge gate lint` and `neuroedge verify` remain green; `scripts/wheel_smoke.sh` passes on installed wheel (`schemas/` packages entire directory into wheel via `hatch_build.py`, added `schemas/tool-result.v1.json` to its checked list)
- Existing, still passing: `test_tool_corpus.py::test_an_mcp_client_gets_the_same_result_and_its_sdk_accepts_it`, `test_every_case_has_an_expectation_and_every_expectation_a_case`, `test_public_api.py::test_every_error_class_of_the_package_is_public`

## 8. Implementation Steps Upon Approval

Proposed order — two implementation PRs because `board.v1.json` is actively being modified by another worker and roadmap schedules TSK-I6-05 after I2a (§0.3 item 5: "`board.v1` freezes when sufficient keys are present"):

**PR A — non-`board.v1.json` scope (actionable immediately upon approval):**

- [x] Add `schemas/tool-call.v1.json`, `tool-result.v1.json`, `error.v1.json`, `error-codes.v1.json`; update `test_schemas.py` (`test_schemas_directory_holds_exactly_the_seven_frozen_schemas`; `ci-sim-linux.yml` also updated from three to seven files)
- [x] `actions/tools.py::result_schema` reads static file (`test_result_schema_is_the_static_file_pinned_and_without_its_identity`); add `system_one` case; `fixtures/contracts/` and `expected_errors.yaml`; tests in §7
- [x] Update `docs/spec/tool_calling.md`: §1 and §4 link to schemas (without duplicating); §2 adds `__unparseable__` key; §4 adds rule "do not branch on `reason`"; §9 final paragraph ("freeze into `schemas/` via an RFC…") marked implemented. *Closing `TODOS.md` #23 is the integrator's responsibility (do not modify `TODOS.md` in this PR).*
- [x] Update `neuroedge-prd.md` *(§10.3 matrix adds four schemas; PR B adds board `schema` key row)*: §10.3 matrix (add four schemas and board `schema` key); Appendix B preamble (declare catalog as source of structure; PRD retains prose; add NE0000, NE2000 rows and notes on NE5001 subclasses); assign `Q-N` to any new decisions
- [x] Update `CONTRIBUTING.md` §8.1 row "Error code `NE…`" and §3 (add four schemas to "Modifying `schemas/*.json`" if needed); `docs/spec/python_api.md` §1 (file-based contracts: add four schemas)
- [x] `docs/architecture/{vi,en}/07-data-contracts.md` *(and `02-container-c4l2.md`: "seven schemas"; new edge `actions` → `paths` already in `test_architecture_layers.py` and `03-component-host-c4l3.md` for same reason)*: schema catalog; if `error-codes` is read from Python code, check dependency edge in `tests/test_architecture_layers.py` and `03-component-host-c4l3.md` (no new edge if only tests read file)

**PR B — `board.v1.json` (after RFC-0007, 0010→0013 finish implementing their keys — achieved via PR #91, §10 item 13):**

- [x] Add `schema` key to `schemas/board.v1.json`; `SUPPORTED_BOARD_SCHEMAS` and pre-validation check in `hal/board.py`; line `schema = "neuroedge.board/v1"` in four `boards/*.toml` (adds `sim-rpi5` from RFC-0013); `to_document()`; board tests in §7

**General:**

- [x] *(both PRs squashed into PR #94, preserving separate commits; single CHANGELOG entry)* One `CHANGELOG.md` entry under `[Unreleased]` for each PR; progress in roadmap TSK-I6-05 (PR A alone does not close task); exit criterion 8 ticked only when both PRs are complete
- [x] Update RFC-0015 row in `docs/rfc/README.md`
- [x] Do not touch `digests.lock` (no gates change) *(RFC-0015 portion changes no entries; PR #94 adds entries only for I2b gates)*

## 9. Findings from Spec, Corpus, and Code Audit

Verified by running code or reading exact lines; not speculative.

| # | Finding | Location |
|:---:|:---|:---|
| F1 | Today's result schema is **closed** (`additionalProperties: false`, `reason` is an `enum`) and client-side MCP SDK validates against it; freezing as-is makes every new `Reason` a `v2`. `Reason` expanded via RFC-0005 (`argument_out_of_range`, 2026-09-24) and RFC-0009 (`value_out_of_range`, 2026-10-02) | `actions/tools.py::result_schema`, `engine/verdict.py::Reason`; §3b |
| F2 | The 28-case corpus covers only 3/10 `reason` values and 4/5 `source` values (no `system_one`) — "corpus validates against schema" does not yet prove enum coverage | `fixtures/tool_calls/`; §3e |
| F3 | **Licensing:** `fixtures/tool_calls/` (and `fixtures/traces/`) do not sit under Apache-2.0 row in `LICENSING.md` (only `schemas/`, `docs/spec/`, `fixtures/compliance/` — which only contains `voice/`), whereas `tool_calling.md` §9 calls this corpus the compliance standard and Q-58 demands the integration surface "sits under Apache-2.0 (schemas, specifications, compliance suites)". Today an external OSS project running the corpus uses PolyForm NC code/files | `LICENSING.md`; Q10.4 |
| F4 | PRD Appendix B states class names and codes "match `errors.py`; all classes inherit from `NeuroEdgeError`", but `errors.py` has `NE0000` (root class) and `NE2000` (`GateError`) without rows in PRD; three subclasses sharing `NE5001` (`ProviderUnavailable`, `MalformedResponse`, `SpeechUnavailable`) have no rows; NE1003 is referenced but has no class (RFC-0007 approved, not yet implemented). **36 places** instantiate `NeuroEdgeError(...)` directly and emit `NE0000` (`grep` outside `errors.py`, excluding comment lines: `cli/` 17, `studio/` 9, root 4, `engine/` 2, `sim/` 2, `testing/` 2), plus internal class `engine/firmware.py::_Refused` also carries `NE0000` — "generic" code, not branchable | `errors.py`, PRD Appendix B; §3d |
| F5 | `GateInheritanceError.as_dict()["principle"]` is a **string** (`str(self.principle)`) even though the attribute is `int` and gate corpus records `principle: 2` (integer) | `errors.py`; §3d |
| F6 | `trace.v1.json` has mandatory `$schema` but only `format: uri`, **not pinned** — trace version identification is written by code, not enforced by schema (whereas gate has `const`) | `schemas/trace.v1.json`; Q10.10 |
| F7 | `board.v1.json` is open at root and inside `board`/`capabilities`; verified by trial run: a document with `schema: "garbage"` and `nonsense: 1` validates, and `to_document()` drops both keys | `hal/board.py`; §1, §3c |
| F8 | `parse_tool_calls` inserts key `__unparseable__` into `arguments` when provider JSON is malformed; behavior is tested (`test_tools.py`, `test_providers.py`) but **absent from `tool_calling.md`** | `actions/tools.py`; §3a |
| F9 | `ToolCall.source` has default `"test"` in dataclass, whereas §1 of spec states `source` is "assigned by runtime": a Python caller omitting `source` gets `"test"` instead of an error. (Any gate not listing `test` blocks — safe, but spec does not mention this default) | `actions/tools.py`; §3a |
| F10 | `tool_calling.md` §8/§8.1 (network) exists only on branch `feat/mcp-network`; RFC baseline (`87db7c7`) does not yet have it | §3a |
| F11 | `test_schemas_directory_holds_exactly_the_three_frozen_schemas` must change; cannot be overlooked because it will turn red | `tests/test_schemas.py`; §4 |
| F12 | `docs/spec/studio.md` (item 8) permits Studio API errors to contain only `why` (`code`, `where`, `how` optional) and `studio/server.py` returns `{"why": "not implemented yet"}` for 501 stubs — two "error" shapes both referred to as `as_dict()`-shaped; `error.v1` accepts only the complete shape | `docs/spec/studio.md`, `studio/server.py`; §3d |

## 10. Decisions for Open Questions (Q-66, 2026-10-04)

Product Owner and Lead Engineer accept the **recommendations** for each question, under the highest-safety principle of Q-57. Because the recommendations are already reflected in §3–§8, this section does not change the design. It merely records two things that changed since writing (question 13) and logs two deferred items into `TODOS.md` (questions 4 and 6). This section is the decision record: if §3–§8 conflict with this section, fix §3–§8. Lead engineer signed off on PR #93.

1. **`reason` is an open string** (§3b), with list of known values and rule "`status` governs; never branch ALLOW on `reason`". Lack of typo checking in validator is compensated by bidirectional tests with `Reason`.
2. **Result object is open** (`additionalProperties: true` at root, in `fallback`, and in `confirmation`), with tests ensuring code emits only declared keys.
3. **`tool-call.v1.json` includes `inputSchema` and tool description.** Profile implementers need them to determine the boundary between `valid/` and `invalid/`.
4. **This RFC does not change licensing.** Moving the compliance corpus (`fixtures/tool_calls/`, `fixtures/agents/`, and `fixtures/traces/` used by the corpus) into Apache-2.0 is the responsibility of the license holder (Q-45, Q-59), not a technical task. This task is `TODOS.md` #57, must be completed before schema publishing (TSK-I6-02). Until done, another OSS project running the corpus uses PolyForm NC files.
5. **Board `schema` key is optional in `v1`.** Lead engineer accepts the tightening point in §4: a board carrying a `schema` other than `neuroedge.board/v1` is now rejected.
6. **"Must-understand keys" and closing `board.v1.json` require a separate RFC, and do not block this RFC.** Rationale: touches hardware safety and schema tightening. The loophole is real: an older reader silently ignores `envelope`. Today it causes no harm, because only one reader exists (Python runtime of the same version as the board). That separate RFC is `TODOS.md` #58. Trigger milestone: before a second `board.v1` reader appears (`esp32s3` firmware reading profiles, external SDK, or older runtime reading newer board), and at the latest before Milestone B.
7. **Two files:** `tool-call.v1.json` and `tool-result.v1.json` (§6). No third `tool` file; tool descriptions live inside `tool-call.v1.json` (question 3).
8. **Agreed on source separation:** catalog `schemas/error-codes.v1.json` is the source of *structure*, PRD Appendix B retains *prose*. PR A updates `CONTRIBUTING.md` §8.1 accordingly.
9. **`NE0000` and `NE2000` freeze with `general: true`.** Recipients promise not to branch on these two codes. Assigning distinct codes to the 36 places currently emitting `NE0000` (F4) is deferred; that is a relaxing change, within `v1`.
10. **Do not pin `$schema` of `trace.v1.json` at this time.** Pinning is tightening, requiring a dedicated RFC on `trace.v1` when needed.
11. **Do not reserve new `source` values** (such as `mcp_network`). Each value enters `NETR` as a `choice` index, so add only when needed.
12. **Placing `error.v1` into JSON-RPC `error.data`: out of scope.** That requires an RFC on MCP behavior.
13. **Approve immediately and split into two implementation PRs (§8).** Two things changed since writing the RFC (baseline `87db7c7`), both thanks to PR #91 (Milestone A):
    - **PR B prerequisites met.** RFC-0007 and RFC-0010 → RFC-0013 implemented their keys on `sim` and `linux`, so PR B can proceed immediately after PR A.
    - **NE1003 has a class:** `EnvelopeRefusedError` (RFC-0007). The catalog today therefore has 17 `stable` entries and 0 `reserved` entries (§3d updated; initial signed draft mistakenly listed 20, corrected during implementation). Field `status: reserved` is retained in the schema for future placeholders.
