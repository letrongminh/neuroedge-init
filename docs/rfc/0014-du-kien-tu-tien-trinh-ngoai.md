# RFC-0014: Facts from External Processes

| | |
|:---|:---|
| **RFC ID** | 0014 |
| **Title** | Numeric facts from external processes (Frigate, OpenCV, sensor boxes, Home Assistant integrations): sources declared in gates, source identity recorded in traces, `age_ms` per shared definition, lost source ⇒ missing fact ⇒ BLOCK |
| **Affected Contract** | `gate.v1` *(a new optional key `evaluate.<name>.external_source`, §3c)* · resolution semantics *(rules for that key in `engine/gate_resolver.py`, §3c)* · engine evaluation *(`_gather` in `engine/gate.py`, §3g)* · `agent.toml` `[external]` block *(no schema in `schemas/`; checked in `neuroedge build` and agent loading, like `[vision]` in RFC-0012)* · wire protocol between source and receiver *(new specification `docs/spec/external_facts.md`; whether to promote to `schemas/`: §9 question 5)* · trace event conventions *(does not alter `trace.v1`: `type` is open string, `events[].data` is free `object` — §4)* · does **not** touch `board.v1`, does **not** touch `NETR` layout, **no** new error codes (§4) |
| **Related PRD Requirements** | FR-MDL-04, FR-MDL-10, FR-GATE-03, FR-GATE-06, FR-CI-02, NFR-SEC-04, NFR-SEC-09 |
| **Author** | — |
| **Date Opened** | 2026-10-03 |
| **Status** | ✅ Approved (2026-10-04) — lead architect signed on PR #92; decisions in §9 (Q-65). Code implemented after v1.0 (`TODOS.md` #56) |
| **Approver** | **Lead Architect — mandatory** (touches `gate.v1`, resolution semantics, opens a fact path into safety gates from outside the process) |

> **When an RFC is required:** `CONTRIBUTING.md` §3 — modifying `schemas/gate.v1.json` and gate resolution semantics
> (`engine/gate_resolver.py`, `engine/constraints.py`). Task: **TSK-I6-07** (this RFC; exit criterion 10 of I6 is approved RFC).
> Implementation code is **not** part of I6: `TODOS.md` #56, scheduled post-v1.0 alongside Beta feedback. Foundation decisions:
> `neuroedge-prd.md` §15 **Q-63** (gap #3), **Q-54** (perception results enter gates as facts, thresholds locked by
> `numeric` criteria, no dedicated gate semantics), **Q-58** (network MCP requires authentication — TSK-P2-04), **Q-62** (single fact age definition;
> `age_ms < 0` ⇒ BLOCK). Aligns with [RFC-0012](0012-nguyen-thuy-vision-in.md) §9.2 (model labels → typed facts),
> [RFC-0009](0009-tieu-chi-so-numeric.md) (numeric criteria, `max_age_ms`), [RFC-0007](0007-digital-in-i2c-analog-in-phong-bi.md)
> (failed read ⇒ undecided ⇒ BLOCK).

## 1. Problem

Another project — Frigate recognizing people at the gate, an OpenCV process counting vehicles, a sensor box running custom firmware, a Home Assistant integration reading door sensors — possesses **observations** that gates require, but NeuroEdge does not want to (and, per Q-52/Q-54, must not) embed models or vision libraries into core. Today there is no formal mechanism to feed those observations into a verdict:

1. **`c.facts`** (`python/neuroedge/actions/conversation.py`, `Conversation.facts`): gate context set by **agent code**. `ActionContractEngine._gather` (`engine/gate.py`) accepts values in it for any criterion, unaware of where they came from, recording no source other than the default string `source="context"` (`Fact` in `engine/verdict.py`). Gates cannot demand "this criterion must come from Frigate".
2. **`[sim.sensor_facts]`** (`sim/session.py`, `SensorFact`): `sim`-only, read from simulated sensors, placing thresholds (`bands`, `gte`, `lte`) in the agent — exactly what Q-54 and RFC-0009 §1 rejected.
3. **HAL** (`sensor.read`, `digital.in`, `analog.in`): reads board hardware; not another process. `sensor.read` cannot even connect to `numeric` criteria (RFC-0009 §3f).
4. **`vision.in`** (RFC-0012): models run **in-core**, cameras are board capabilities, traces carry frame `vision_ref`. That is precisely what Q-63 states should not be required when observations originate in another process.
5. **`SystemOne`** (`models/system.py`): answers only `bool`, `level`, `choice` (constant `TYPES`) for an utterance, not measurements, and is an outbound call to a model initiated by NeuroEdge.
6. **Tool calls** (`ToolCall`, `docs/spec/tool_calling.md`): models and MCP clients are **untrusted** callers (`threat_model.md` §2b); unknown arguments are `REJECTED`. A fact cannot travel this road, and should not.

Consequence: integrators must write agent code stuffing values into `c.facts` — losing source identity, age tracking, and trust boundaries — or keep thresholds in the agent. Both are loopholes invisible to pure gates (invariant #4).

## 2. Why the Current Schema Does Not Solve It

- `schemas/gate.v1.json`: `evaluate.<name>` has `additionalProperties: false` and only knows `type`, `instructions`, `levels`, `options`, `unit`, `range`, `max_age_ms`. Nowhere can a gate state "this fact must come from external source named X". Because gates are cryptographically signed files (`gate_digest` = hash of `ResolvedGate.to_artifact()`, including `evaluate`), declaring sources only in the agent leaves source authority outside the signature — the same flaw identified in RFC-0012 §3c regarding `confidence_gte` ("gates do not know which criteria come from vision; `gate lint` cannot block it").
- `agent.toml` provides no place to declare external sources. `[vision]` (RFC-0012) declares model labels → facts but relies on `vision.in` and in-core models.
- `board.v1` declares **hardware**. External sources are software peers, not pins or buses (§6: why this is not a primitive).
- No wire protocol specification exists for external processes communicating with runtime: transport, authentication, clocks, message formats, disconnect behavior.
- The Q-62 age definition (RFC-0009 §3c: `age_ms` = evaluation timestamp − HAL read timestamp, on the same monotonic session timeline) was designed for readings stamped by **in-process HAL** (`Fact.read_ms`, `engine/gate.py::_numeric_marks`: "a source cannot state its own age"). An external process runs an independent clock; no rule currently establishes its timestamp on the session timeline.

## 3. Proposed Change

### 3a. Scope and Boundaries

An **external source** is a process external to NeuroEdge, co-located on the same machine as runtime, actively **pushing** current observed state (numbers) to a local socket listened to by runtime. The core:

- accepts only **typed numeric facts** (`numeric`): no frames, no labels, no free strings, no models, no vision libraries;
- never **initiates outbound calls** back to sources during gate evaluation or replay (§3g, §3h);
- treats all messages as **untrusted until** passing authentication (§3d) and schema validation (§3e); any suspicion ⇒ **missing fact** ⇒ `criterion_unavailable` ⇒ BLOCK (§3i);
- alters zero words of gate rules: thresholds, scales, maximum age remain gate `numeric` criteria (RFC-0009), adding only **source constraints** (§3c).

Scope in this version (limits are intentional, each with rationale and open question in §9 if product owner decision is required):

| Limit | Rationale |
|:---|:---|
| `numeric` only (counts, confidence scores, measurements; two-state flags sent as 0/1 with `range: { min: 0, max: 1 }`) | All required guarantees already exist for `numeric` (RFC-0009): mandatory `max_age_ms` locked by gate, mandatory `range`, no `confidence_gte`, no `on_block.confirms`, and **`fail: open` does not forgive** missing numeric facts (`known_failure` in `engine/decision_tree.py`). `bool` has no age, and `known_failure` ignores missing `bool` facts — the exact three loopholes RFC-0012 §3c had to patch with companion criteria. Adding `bool` is a future RFC if product owner decides (§9 question 4) |
| Same machine as runtime only (Unix domain sockets) | Network authentication is the responsibility of TSK-P2-04 (§3d); avoid building a second authentication mechanism |
| Targets `sim` and `linux` only | `esp32s3` lacks local sockets; gates declaring `external_source` building for `esp32s3` are rejected (§3i). MCU gateways belong to TSK-P2-05 (I14) |
| No `level`/`choice`/string facts | Same rationale as RFC-0012 §3c (no `level`/`choice`); strings from external processes present command injection surface without benefit |

### 3b. Transport — Alternatives Evaluated and Selected Option

| Alternative | Conclusion |
|:---|:---|
| **Push, Unix socket (`AF_UNIX`, stream), runtime listens** | **Selected.** Kernel provides peer uid (`SO_PEERCRED` on Linux, `LOCAL_PEERCRED` on macOS), grounding authentication without bespoke mechanisms; exposes no network ports, needs no TLS, adds no new dependencies (Q-11); latency tens of microseconds; source death immediately closes socket endpoint, alerting runtime instantly (§3i) |
| Push, HTTP/WebSocket over `127.0.0.1` | Rejected: pulls in entire web stack and HTTP auth; `mcp serve --ui` precedent had to block DNS rebinding and `Origin` (`threat_model.md` §2b) for this exact surface; lacks peer uid |
| MQTT (runtime subscribes to topics) | Rejected for this version: requires broker, which belongs to Fleet (Q-11, I9; `TODOS.md` #52); ACL managed by broker, not verified by us; EMQX is BSL license (Q-11). An MQTT → Unix socket adapter belongs **outside core** (§3j) |
| Pull (runtime polls Frigate/HA via HTTP on demand) | Rejected: either requires network calls **in the evaluation path** (latency consumes gate `p95_latency_ms` budget; replay has nothing to poll), or core must know vendor-specific APIs — violates FR-MDL-04 (vendor changes without modifying gates) and Q-63 ("no vision libraries in core") |
| Child processes via stdio (runtime spawns adapter, like MCP stdio) | Not rejected: structural trust (operator runs it), but adapter lifecycle becomes runtime's responsibility and ill-fits Frigate as a standalone service. Message framing in §3e can be reused verbatim over pipes; adding later requires no new RFC if §3e remains unchanged |
| Network sockets with mTLS | Deferred: requires device identity from TSK-P2-04. Question §9 question 1 |

**Push current state, not events.** Sources resend the *entire current value* of facts they manage at regular intervals (recommended ≤ `max_age_ms` / 2 of the tightest criterion using it). A source sending "person appeared" and falling silent will be treated as stale — by design: silence is not "nothing changed" (aligning with RFC-0009 §5). Aggregating events into state is the adapter's responsibility.

### 3c. Declaring Sources: Gates Hold Authority, `agent.toml` Holds Deployment Bindings

**Gate** (`gate.v1`) declares *that* a numeric criterion must come from an external source, and the *logical name* of that source — declaring no addresses, sockets, or tokens:

```yaml
# gates/close_gate — authority (example connecting RFC-0012 §3c via external source instead of in-core model)
evaluate:
  people_at_gate:
    type: numeric
    unit: count
    range: { min: 0, max: 50 }
    max_age_ms: 500
    external_source: frigate_front        # new
    instructions: "Number of people in gate area, reported by frigate_front"
allow_when:
  people_at_gate: { lte: 0 }
```

```json
"external_source": {
  "description": "Logical name of the external process that must supply this criterion (RFC-0014). Only with type numeric.",
  "type": "string",
  "pattern": "^[a-z][a-z0-9_]{0,31}$"
}
// inside allOf: if type is not "numeric", external_source must not be present (same pattern as unit / range / max_age_ms for bool, level, choice)
```

Rules (resolver and engine; violations ⇒ `GateSchemaError`, `NE2002`, three-part error):

| Rule | Rationale |
|:---|:---|
| `external_source` only on `type: numeric` | §3a |
| Inheritance: criterion declaring `external_source` in parent gate cannot be altered or dropped in child gate ⇒ `GateInheritanceError` (`NE2003`, principle 1) — **no new code needed**: `_merge_evaluate` (`engine/gate_resolver.py`) already rejects redefining inherited criteria | Child gates cannot strip parent source constraints or switch to more permissive sources |
| Criteria with `external_source` forbidden in `on_block.confirms` | Already true for all `numeric` criteria (RFC-0009 §3a); humans on device cannot confirm in place of observations, especially from dead sources |
| `confidence_gte` on this criterion rejected | Already true for all `numeric` criteria (RFC-0009 §3a). Unlike RFC-0012 §3c: **gate lint can check this**, because gates declare the source explicitly |

**`agent.toml`** (maker/deployment; unversioned in `schemas/`, checked in `neuroedge build` and agent loading) declares *how* logical sources bind to runtime:

```toml
[external]
socket = "run/neuroedge-external.sock"      # relative to agent working directory; max 100 bytes after expansion

[external.sources.frigate_front]
token_env = "NE_EXT_FRIGATE_FRONT_TOKEN"    # environment variable name, like api_key_env in [system_one]; never raw value
[external.sources.frigate_front.facts.people_at_gate]
unit = "count"
```

| Rule (`AgentManifestError`, `NE3002`, wrapped in `BuildFailed`, `NE3003`) | Rationale |
|:---|:---|
| Fact name matches gate criterion name, and `unit` matches criterion `unit` (same channel-binding rule as RFC-0009 §3f) | Unit mismatch distorts threshold semantics |
| **Bidirectional:** all criteria with `external_source: X` must have `[external.sources.X.facts.<criterion>]`, and all facts in `[external.sources.X.facts.*]` must correspond to a criterion with `external_source: X` | No gate criterion left unmapped; makers cannot wire a criterion locked by gates to another source, or push facts into criteria not requesting external sources |
| Unknown keys in `[external.*]` (including `range`, `bands`, `threshold`, `min`, `max`) | No thresholds exist in agents (Q-54, RFC-0012 §3c "no thresholds in `agent.toml`") |
| Secret field names (`token`, `key`, `secret`, `password`) or invalid env variable name in `token_env` | Reuses `secret_fields`, `refuse_unknown`, and env name checks (`ENV_NAME`) from `models/providers/common.py`, like `api_key_env`; `agent.toml` is committed |
| `source_id` outside `^[a-z][a-z0-9_]{0,31}$`; `socket` too long for `sun_path`; two sources sharing `token_env` | Clarity; two sources sharing a token cannot be distinguished |
| Gate has `external_source` but agent lacks `[external]` block | Build rejects, preventing dangling criteria |

Criteria with `external_source` never accept values from elsewhere. `ActionContractEngine._gather` treats the §3g receiver as the **sole** source: values in `c.facts` for that criterion are ignored (ignored rather than overwritten, preventing accidental overrides from changing verdicts), and `facts_source` is not consulted. Missing ⇒ `criterion_unavailable`.

### 3d. Source Authentication

In-scope threats (`threat_model.md` §2 "gate bypass through error" extended to a new fact path; §3 excludes co-equal uid attackers): **a local process masquerading as a legitimate source** feeding numbers into gates, or **a legitimate source spoofing another source**.
Four defense layers, all must pass:

1. **Socket owned by operator.** Runtime creates parent directory (if missing) with `0700` permissions and socket with `0600`, owned by runtime uid; if socket already exists, it is unlinked only if it **belongs to this exact uid**, otherwise ⇒ reject loading (`PerceptionUnavailableError`, `NE5001` — "perception component failed to initialize", matching Appendix B). Sockets cannot run without proper permissions.
2. **Peer uid** read from kernel; must equal runtime uid (or an explicit `peer_uid = <int>` declared per source). Operating systems unable to read peer uid ⇒ receiver refuses to initialize (no "skip check" fallback on that platform).
3. **Dedicated token per source.** `hello` carries `source_id` and `token`; compared using constant-time comparison (`hmac.compare_digest`) against value in environment variable `token_env` for that source. Tokens must be at least 32 characters; shorter ⇒ reject loading. Dedicated tokens prevent source A's compromised token from injecting source B's facts.
4. **Connection bound to single `source_id` after handshake.** All facts over that connection accepted only for names declared under `[external.sources.<source_id>.facts.*]`; any other name (including names belonging to other sources) ⇒ protocol violation, close connection, discard all facts for that source (§3i).

Brute-force and socket exhaustion defense: max 8 unauthenticated connections, 2 s handshake timeout; 5 consecutive authentication failures for a `source_id` ⇒ lock out source for 60 s; min 1 s between handshakes for a single source. Two authenticated connections for the same `source_id`: **new connection replaces old** (old closed, its facts discarded, `external_source_lost` event with reason `replaced`) — better to drop a fact for one tick than retain a half-dead connection. These constants are proposed; lead architect approves (§9 question 10). Runtime never writes tokens anywhere, including traces and error messages.

**Network sources (outside this RFC).** Connecting sources on other machines (Frigate on NAS) requires **device identity from TSK-P2-04** — per-device mTLS (NFR-SEC-04) and per-device authorization (Q-58, Q-32) — using unified provisioning and revocation, not a second "shared network secret" mechanism. Message layer §3e remains identical; only handshake §3d changes. See §9 question 1.

**New section for `docs/spec/threat_model.md`** (written on implementation, §8) — "§2c. In-scope: External fact sources":

| Attack Vector | Mitigated By | Result |
|:---|:---|:---|
| Different user process connects to socket | `0700`/`0600` permissions + peer uid check | Rejected, `external_source_refused` |
| Co-equal uid process lacking token | `hello` missing/invalid `token` | Rejected; source locked out after 5 failures |
| Source A declares facts of source B | Connection bound to `source_id` (layer 4) | Closes connection, discards facts of A |
| LLM or MCP client "injects facts" via tools | Facts are not arguments to any tool; socket is not an MCP path | `REJECTED` as unexpected parameter (`tool_calling.md` §5) |
| Agent code sets `c.facts["people_at_gate"] = 0` to bypass | `_gather` ignores `c.facts` for criteria with `external_source` (§3c) | `criterion_unavailable`. *Prevents accidental errors; in-process code remains outside scope (§3 of threat model)* |
| Replaying old messages on same connection | `seq` must strictly increase (§3e) | Closes connection, discards facts |
| Message flooding to consume CPU or bloat traces | Line size limits, rate limiting, aggregated per-second rejections (§3e, §3h) | Closes connection |
| Legitimate but hung source repeatedly sending old values with small `observed_age_ms` | **Cannot be stopped in core** — source misrepresents freshness | Residual risk, §5 |

### 3e. Wire Protocol

One line = one UTF-8 JSON object terminated by `\n`, max 4096 bytes; duplicate keys rejected. All messages contain `"v": 1`.

```json
{ "v": 1, "type": "hello",   "source_id": "frigate_front", "token": "…", "adapter": { "name": "ne-frigate-adapter", "version": "0.3.1" } }
{ "v": 1, "type": "welcome" }
{ "v": 1, "type": "facts",   "seq": 812, "observed_age_ms": 40, "facts": { "people_at_gate": 0 } }
```

- `hello` is first and only message on connection; `adapter` is informative for trace readers (untrusted, unused in verdicts). `welcome` is the sole response; authentication failure ⇒ silently closes connection (emits no failure reasons over wire).
- `facts.<name>` is a **JSON number** (not `true`/`false`, no strings). Finite numbers outside criterion `range`, or overflowing to infinity (`1e999`), are **not** protocol violations: they reach the engine as-is, and the engine evaluates `value_out_of_range` (RFC-0009 §3c) — post-hoc audit distinguishes "sensor returned garbage" from "source lost".
- `seq`: integer, strictly increasing per connection. `observed_age_ms`: integer `0 … 4294967295` — age of observation **at moment source transmitted**, a **duration** measured by source clock (not an epoch timestamp), applied to all facts in message. Each message applies **atomically** or not at all.
- **Protocol violations** — corrupted JSON, line too long, unknown `type`, `v` ≠ 1, missing/mistyped fields, fact name undeclared for source, non-increasing `seq`, invalid `observed_age_ms` (negative/non-integer/exceeding ceiling), message before `hello`, exceeding 100 msgs/s — ⇒ **closes connection and discards all facts for that source** (§3i). No "skip malformed line and proceed" mode: a source sending garbage cannot be trusted for subsequent lines.
- One message for multiple facts is the sole mechanism ensuring atomic observations (e.g. `people_at_gate` and `person_confidence` from same frame). Core does not force gates to demand matching `seq`; traces record per-fact `seq` allowing audits to detect skew (§3h).

Complete specification and compliance vectors (§7) in `docs/spec/external_facts.md` — licensed under Apache-2.0 like other specs, enabling third-party OSS adapters (Q-58, Q-59).

### 3f. Fact Age and Clock Domains (Q-62)

Only **one** timeline exists: monotonic session timeline used by `EventLog` (`monotonic_ms` in `engine/trace_sink.py`, or simulated mock clocks in tests). Source clocks **never** enter calculations.
Rationale: monotonic clock origins across Go, Node, or JVM processes are independent; matching OS `CLOCK_MONOTONIC` is platform coincidence; wall clocks can jump due to NTP step adjustments.

```
read_ms   = recv_ms − observed_age_ms        # on session timeline; recv_ms measured by RECEIVER
age_ms    = eval_offset_ms − offset_of(read_ms)      # matches RFC-0009 §3c formula exactly
```

- `recv_ms` is `clock()` (`EventLog` clock) **immediately after line read completes**, in a dedicated reader task doing no heavy compute between reading and timestamping. Kernel socket buffer transit latency is unmeasured: represents negative error (actual age ≥ calculated age), bounded by event loop latency, documented in §5.
- `observed_age_ms` declared by source is **strictly additive**. Because calculated age = (age since receipt, measured by us) + (source-declared duration ≥ 0), a lying source can only make age **equal** to age-since-receipt, never younger. The principle "a source cannot state its own age" (`_numeric_marks` in `engine/gate.py`) holds: sources cannot appear fresher than their arrival time.
- `offset_of` correctly handles timestamps prior to log start (negative offset, increasing age — never "fresh as start").
- Engine calculates `age_ms`, comparing against criterion `max_age_ms`; `age_ms < 0` or `> max_age_ms` ⇒ `criterion_unavailable` (RFC-0009 §3c, `engine/decision_tree.py::_classify`). No special-case bypass for external sources.
- Newly arrived facts replace older facts of the **same name** in receiver (`seq` strictly increases); older facts never overwrite newer ones.
- Source wall clocks (e.g. Frigate `start_time`) are the adapter's responsibility: convert to `observed_age_ms` using source's own clock. Core rejects absolute timestamps.

### 3g. Receiver → Engine: No Outbound Calls

Receiver (new runtime class, public name determined by task implementation and pinned in `docs/spec/python_api.md` §2 alongside `tests/test_public_api.py`) maintains **latest value per (source, fact)**: `(value, read_ms, seq, connection, observed_age_ms)`. When gates evaluate, `_gather` calls a **synchronous, zero-I/O** function returning `Fact(value, source="external:<id>", read_ms=…)` or `None`.
Engine calculates timestamps like any numeric reading (`gate.py`, `_numeric_marks`). Source disconnect, connection drop, or protocol violation ⇒ receiver **immediately clears** facts for that source (does not allow natural expiration): returning nothing ⇒ `None` ⇒ `walk()` evaluates `criterion_unavailable`.

Two guarantees: receiver **never** returns `Unavailable("offline")` (which becomes `gate_unreachable`, a *degraded* reason that `budget.fail: open` can convert to ALLOW — `DEGRADED_REASONS` in `engine/verdict.py`); and it **never** reuses previous connection values after source reconnects. Missing numeric facts are blocked by `known_failure` even under `fail: open` (§3a), ensuring safety remains intact even if another source (e.g. SystemOne) simultaneously degrades.

### 3h. Traces and Replay

`trace.v1` is **unchanged**. Facts enter existing `gate_facts` (`engine/gate.py`), adding keys for external sources; replayers ignore unknown keys (`recorded_steps` in `testing/player.py` reads only `value`, `confidence`, `source`, and three timestamps):

```json
{ "offset_ms": 5210, "type": "gate_facts", "data": {
    "people_at_gate": { "value": 0, "confidence": null, "source": "external:frigate_front",
                        "read_offset_ms": 5130, "eval_offset_ms": 5210, "age_ms": 80,
                        "connection": 3, "seq": 812, "observed_age_ms": 40 } } }
```

- **Source identity** on every fact: `source = "external:<source_id>"` (matching `"<name>:<model>"` pattern in `SystemOneApi.source` in `models/providers/systemone_api.py`), including `connection` (connection sequence number in session) and `seq` to verify whether two facts share an observation. Tokens and `adapter` omitted from traces; `adapter` recorded only in `external_source_connected`.
- Lifecycle events (names and fields added to unified catalog `docs/spec/tool_calling.md` §7 upon implementation; adding events needs no RFC):
  `external_source_connected` `{source_id, connection, adapter?, peer_uid}` · `external_source_lost` `{source_id, connection, reason}` where `reason` ∈ `closed` · `protocol_violation` · `replaced` · `shutdown` ·
  `external_source_refused` `{claimed_id, reason, count}` where `reason` ∈ `unknown_source` · `bad_token` · `bad_peer` · `locked_out` — **aggregated per second** (preventing flood-induced trace bloat); `claimed_id` normalized to `"?"` if not matching `source_id` regex (avoids copying arbitrary strings into traces) ·
  `external_fact_unavailable` `{criterion, source_id, why}` where `why` ∈ `not_connected` · `no_reading_yet` — emitted when criteria with `external_source` lack facts at evaluation time, allowing audits to distinguish "source down" from "stale fact" (the latter indicated by `age_ms` in `gate_facts` and `evaluations`).
- Semantic trace linting in `python/neuroedge/trace.py` (violations ⇒ `TraceValidationError`, `NE4001`): `gate_facts` entry with `source` starting with `external:` missing `connection`/`seq`/`observed_age_ms` or three timestamps; `age_ms` inconsistent with `eval_offset_ms − read_offset_ms` (verified by replayer — `_numeric_entry`); invalid `source_id` pattern.
- **Replay uses recorded facts only.** `ReplaySession` feeds exact recorded `gate_facts` (values and three timestamps); it **never** opens sockets, creates receivers, or reads token environment variables (guaranteed by tests: §7). Lifecycle events are informational, unverified in verdict comparison. A source dropping mid-session replays identically to runtime: missing fact in `gate_facts` ⇒ `criterion_unavailable`.
- **`sim`**: virtual sources in `neuroedge.testing` use **identical receiver logic** (identical schema validation, `seq` tracking, `read_ms` calculations) via in-process queues without sockets; real sockets tested separately on host. Both paths share validation functions, covered by §7 compliance vectors.
- Privacy: traces record **numbers** (person counts, confidence scores), no frames, no labels. Preventing image leakage is the adapter's responsibility; core accepts only numbers. Anonymization rules (FR-TRC-07) unchanged as no `text` is stored.
- Three canonical traces `fixtures/traces/*.json` carry no external facts, remaining unchanged (RFC-0008).

### 3i. Fail-Closed

Checked in order; all branches BLOCK, **no interpolation, no defaults, no reuse of prior connection values**:

| Scenario | Result |
|:---|:---|
| Criterion declares `external_source` but authenticated connection absent; or connection active but fact not yet received (`not_connected` / `no_reading_yet`) | Missing fact ⇒ `criterion_unavailable` |
| Connection closes, read error, handshake timeout, connection replaced | Immediately drops **all** facts for source ⇒ `criterion_unavailable` until reconnected and fresh facts arrive |
| Authentication failure (wrong token, wrong uid, undeclared source) | Silent disconnect; no facts accepted |
| Protocol violation §3e (including facts belonging to another source, decreasing `seq`, malformed `observed_age_ms`) | Closes connection, drops all facts for source ⇒ `criterion_unavailable` |
| `age_ms < 0`, or `age_ms > max_age_ms` of criterion | `criterion_unavailable` (engine, RFC-0009 §3c) |
| Non-finite number, or outside `range` | `value_out_of_range` (RFC-0009 §9.1) |
| Finite, in range, fails `allow_when` interval | `condition_not_met` |
| `c.facts` or `SystemOne` also supplies value for criterion | Ignored; receiver only (§3c) |
| Agent loading: `[external]` declared but socket cannot be created (permissions, uid, path too long, foreign-owned socket), or token missing/short | Rejects loading, `PerceptionUnavailableError` (`NE5001`); **never** continues in "temporarily without external sources" mode |
| `neuroedge build --target esp32s3` for gate with `external_source` | Rejects, `BoardCapabilityError` (`NE3001`): target does not provide capability. Decision tree not sent to device expecting external facts |
| Gate awaiting source while caller requests returning actuator **to safe state** (`off`, `duty = 0`, `safe_state`) | Bypasses gate (RFC-0007 §9.7, Q-62): dead source never blocks safe-direction commands |

### 3j. Outside Core (Intentional)

Excluded from `neuroedge` core and outside core Apache-2.0/PolyForm licenses (Q-45, Q-59): adapters for Frigate, OpenCV, Home Assistant, MQTT, Zigbee; all vision libraries; models; any label → number transforms (`person` in `gate_area` → count); converting wall clocks to `observed_age_ms`; event-to-state aggregation; MQTT bridges (`TODOS.md` #52). Core contains only the receiver, protocol, gate constraints, and compliance vectors. Location of sample adapters: §9 question 7.

**Relation to RFC-0012.** RFC-0012 §9.2 states "maker declares model labels to facts; gate locks thresholds". With external sources, **label → fact transforms occur inside the adapter**, not in `agent.toml`: core sees no labels and no frames, so concepts like `zone`, `min_frames`, `vision_ref`, and model identity **do not exist** here.
Shared aspects: typed facts (`numeric` only here), fact names matching gate criteria names, thresholds and `max_age_ms` in gates, no thresholds in agents, `confidence_gte` rejected. An agent may use both (RFC-0012 for on-board camera; RFC-0014 for Frigate) for **different criteria**; a single criterion has exactly one source.

### 3k. Error Codes

No new codes added. Classes used already exist in `python/neuroedge/errors.py`: `GateSchemaError` (`NE2002`), `GateInheritanceError` (`NE2003`), `BoardCapabilityError` (`NE3001`), `AgentManifestError` (`NE3002`), `BuildFailed` (`NE3003`), `TraceValidationError` (`NE4001`), `PerceptionUnavailableError` (`NE5001`). The *Cause* column in Appendix B of `neuroedge-prd.md` is widened per §4. At runtime, the receiver **never throws** exceptions to gates: all failures represent *missing facts* ⇒ verdict `criterion_unavailable` (independent of RFC-0007 §3e runtime NE5001 scope changes).

## 4. Compatibility Impact

| Item | Impact |
|:---|:---|
| Do currently valid files remain valid? | Yes — `external_source` is optional key; no gate in `gates/`, `fixtures/gates/`, `fixtures/agents/` has it; no agent has `[external]` |
| Do currently invalid files become valid? | Yes, exactly one category: `numeric` criteria with valid `external_source`. Schema relaxation, feasible in `v1`. *Older `neuroedge` versions will reject gates using this key (`additionalProperties: false`)* — fail-closed, not a breaking change |
| Does schema version need bumping (`v1` → `v2`)? | No. `trace.v1` unchanged (open `type`, `data` is `object`); `board.v1` unchanged |
| Impact on published gate hashes / signatures? | None — gates without new key hash identically. Gates **using** new key produce different digest than identical gates without it (`evaluate` included in `to_artifact()`): intentional, sources covered by signature |
| Impact on three canonical trace files? | None |
| Which gates in `digests.lock` change digest? | None; sample gates using external sources enter `digests.lock` via normal PR (`scripts/check_digests.py --update`) |
| Must `NETR` layout or C walker change? | No. `compile_tree` (`engine/decision_tree.py`) builds numeric nodes from existing fields, `external_source` does not enter device tree; devices do not accept external facts (§3a, §3i) |
| Do any answers in tool call corpus (`expected_results.yaml`) change? | No |
| Resolution semantics? | Yes, narrowly: resolver recognizes, checks, and retains `external_source` across inheritance; engine `_gather` ignores `c.facts` for criteria declaring key |

**Touched Contracts Explicitly Stated:** `gate.v1` **modified** (one optional key). `trace.v1` **unmodified**. `board.v1` **unmodified**. `agent.toml` **modified** (new `[external]` block; outside `schemas/`). New wire protocol spec outside `schemas/` (§9 question 5).

**Error Codes** (`neuroedge-prd.md` Appendix B): no new codes; widen *Cause* for five rows:

| Class | Added Cause |
|:---|:---|
| `GateSchemaError` (`NE2002`) | Malformed `external_source`, or present on non-`numeric` criteria |
| `AgentManifestError` (`NE3002`) | Invalid `[external]` block (§3c): missing bidirectional mapping gate ↔ agent, mismatched `unit`, unknown keys, raw secrets, invalid `source_id` regex |
| `BoardCapabilityError` (`NE3001`) | Gate with `external_source` built for target that rejects external sources (`esp32s3`) |
| `TraceValidationError` (`NE4001`) | Semantic lint on facts originating from external sources (§3h) |
| `PerceptionUnavailableError` (`NE5001`) | Receiver fails to initialize at load time (§3i) |

## 5. Safety Impact

- **Gate no looser and no new verdict semantics** (Q-54): thresholds, `range`, `max_age_ms`, narrowing-only inheritance, confirmation forbidden, `confidence_gte` forbidden, `fail: open` does not forgive missing numeric facts — all RFC-0009 rules preserved intact. `external_source` only **adds** a constraint (source binding), and inheritance cannot remove it (§3c).
- **Authority in gates, deployment in agents:** makers cannot alter *who* supplies facts for a criterion, cannot inject thresholds; only wire logical sources to local sockets, where missing or excess mappings are blocked at build time (§3c, bidirectional).
- **Untrusted callers remain untrusted:** models and MCP clients cannot inject facts (no tool parameters, no socket access), and `call_source` remains unchanged (`tool_calling.md` §5).
- **Single age definition (Q-62):** read timestamp is measured by *receiver* on session timeline; source-declared duration is additive only, preventing facts from appearing younger than arrival time (§3f). `age_ms < 0` ⇒ BLOCK. Traces record all three timestamps, recomputed by `replay`.
- **Source failure ⇒ BLOCK, never ALLOW** (§3i): missing facts evaluate to standard `criterion_unavailable` (not degraded reasons), preventing `budget.fail: open` from granting ALLOW. Safe-direction commands bypass gates (§3i), ensuring dead sources never trap actuators in hazardous states.
- **No thresholds in agents, no labels or frames in core:** injection surfaces via content (unexpected labels, arbitrary strings) do not exist; only numbers pass through.
- **Residual Risks — Stated Directly, Unmitigated in Core:**
  1. **Sources lying about freshness.** A hung adapter repeatedly sending old values with small `observed_age_ms` appears fresh. RFC-0012 caught camera freezes in core via frame hashes; here core lacks frames. Mitigations: (a) adapters must compute `observed_age_ms` from **capture time of observation itself**, not poll time (mandatory in `docs/spec/external_facts.md`, with compliance vectors for sample adapters if present); (b) short gate `max_age_ms` forces regular updates; (c) gates for hazardous actions **pair** trusted core criteria (`analog.in`, `digital.in`) with external criteria — gate's choice; `neuroedge build` warns when an actuator-controlling action relies solely on external sources, and sample gates always pair (§9 question 8).
  2. **High-confidence source errors** (Frigate reporting "nobody there" when someone is present). Similar to RFC-0012 §5: mitigated by gate thresholds and pairing criteria; cannot be confirmed away (confirms forbidden), requiring physical core criteria alongside irreversible actions.
  3. **Attacker with identical runtime uid possessing token** lies outside threat model (`threat_model.md` §3: equal privileges with runtime). Dedicated per-source tokens limit blast radius of a compromised source to its own criteria.
  4. **Negative error in `recv_ms`:** delay between kernel socket receipt and reader task timestamping is unmeasured. Bounded by event loop latency (milliseconds); gate `max_age_ms` should comfortably exceed this margin (recommended in spec).
  5. **Observations split across `seq` boundaries:** two consecutive messages could contain halves of one observation. Mitigated by one-observation-per-message convention (§3e); traces record `seq` for auditability.
- Requires lead architect approval because it touches `gate.v1`, resolution semantics, and opens an out-of-process fact path into safety gates.

## 6. Alternatives Considered and Rejected

| Alternative | Reason for Rejection |
|:---|:---|
| Declaring sources only in `agent.toml`, leaving `gate.v1` unchanged | Gates cannot lock sources, leaving `gate lint` blind (same flaw as RFC-0012 §3c with `confidence_gte`); makers could remap sensitive criteria to easier sources unnoticed. TSK-I6-07 roadmap row specifies "sources declared in gates" |
| Declaring socket addresses or tokens in gates | Gates are signed files distributed via registry across deployments; addresses and secrets belong to deployment. Gates carry logical names only, like FR-HAL-06 for pin names |
| External sources as `external.in` **primitive** in `board.v1` | RFC-0013 §2 and Q-53 demand all extension primitives across **all three** targets; `esp32s3` lacks local sockets. FR-HAL-01 closes primitive set as static firmware arrays; `board.v1` declares hardware, not software peers |
| Sources sending pre-evaluated **decisions** (`person_detected: true`, Frigate threshold) | Thresholds reside outside gates (Q-54, RFC-0009 §1); `bool` lacks age tracking and `known_failure` ignores missing `bool` (§3a) |
| Permitting `bool`, `level`, `choice` in initial version | Three loopholes in §3a; add later via dedicated RFC if product owner requires (§9 question 4) |
| Trusting source absolute timestamps (epochs, Frigate `start_time`) | Wall clocks jump during NTP steps; monotonic origins vary across runtimes; violates Q-62 (single age definition on session timeline) |
| Calculating age strictly from receipt, ignoring `observed_age_ms` | Observations captured 3 s earlier sitting in source pipelines appear fresh on arrival. Adding `observed_age_ms` makes age equal or older, never younger — no safety justification to omit |
| Sources declaring complete age (`age_ms` instead of `observed_age_ms`) | Sources could claim to be younger than arrival; violates engine principle "a source cannot state its own age" |
| Pulling (HTTP to source) in evaluation path | §3b: latency inside `p95_latency_ms`, replay lacks endpoints, core requires vendor API knowledge |
| Local HTTP/WebSocket instead of Unix sockets | §3b: introduces web stack, DNS rebinding, `Origin`, lacks peer uid |
| Native MQTT inside core | §3b: broker belongs to Fleet, ACL unverified, EMQX BSL license (Q-11); `TODOS.md` #52 |
| "Skip malformed lines and proceed" | Sources sending garbage cannot be trusted for subsequent lines; closes connection and drops facts (§3e) |
| Retaining stale facts on source disconnect until `max_age_ms` expires | Window of hundreds of milliseconds where dead source appears "fresh"; drop immediately (§3g) |
| Receiver returning `Unavailable("offline")` on disconnect | Becomes `gate_unreachable`, a degraded reason that `fail: open` can convert to ALLOW (`engine/verdict.py`, `engine/gate.py::_degraded`) |
| Allowing `c.facts` to overwrite criteria with `external_source` | Agent code could bypass source constraints by error; ignored (§3c) |
| Single shared token across all sources | Compromised source can inject facts for other sources (§3d layers 3–4) |
| Bespoke network authentication for remote sources | Two identity provisioning/revocation mechanisms; use TSK-P2-04 (§3d) |
| `gate.v2` | No currently valid files break; `v2` bump is unnecessary (same rationale as RFC-0002 §4, RFC-0009 §6) |

## 7. Verification Evidence

All items below are **mandatory implementation requirements** (`TODOS.md` #56); unchecked as this RFC contains no code yet. Corpus follows bidirectional closure rules (`CONTRIBUTING.md` §3): add row for new corpus to table there (§8).

- [ ] **Valid gates and negative tests** (`fixtures/gates/valid/`, `fixtures/gates/invalid/` + `expected_errors.yaml`): valid `external_source` usage ⇒ lint passes; `external_source` on `bool`/`level`/`choice`, malformed names, criteria present in `on_block.confirms`, paired with `confidence_gte` ⇒ `GateSchemaError` (`NE2002`); child gates dropping or altering parent `external_source` ⇒ `GateInheritanceError` (`NE2003`, principle 1)
- [ ] **Bidirectional gate ↔ agent verification** (`python/tests/test_compiler.py`): agent missing `[external.sources.X.facts.<criterion>]`; fact declared without gate requirement; mismatched `unit`; unknown keys (`range`, `bands`, `threshold`); raw secrets; malformed `source_id`; two sources sharing `token_env`; gate declaring source but agent lacking `[external]` ⇒ `AgentManifestError` (`NE3002`); building `--target esp32s3` ⇒ `BoardCapabilityError` (`NE3001`)
- [ ] **Protocol compliance vectors** (`fixtures/external_facts/{valid,invalid}/` + `expected_results.yaml`, bidirectional closure; spec in `docs/spec/external_facts.md`): message streams → retained receiver facts or connection close + drop. Negative tests: malformed JSON, line > 4096 bytes, duplicate keys, unexpected `v`, unexpected `type`, missing fields, `true` for numbers, strings for numbers, fact names of another source, equal/decreasing `seq`, negative/non-integer/> 4294967295 `observed_age_ms`, message before `hello`, exceeding 100 msgs/s
- [ ] **Authentication on live sockets** (host): foreign uid ⇒ reject; missing/wrong token ⇒ silent rejection; 5 failures ⇒ lock out for 60 s; source A declaring B's facts ⇒ close + drop; second connection replaces first; foreign pre-existing socket ⇒ `NE5001`; `sun_path` too long ⇒ reject loading; token shorter than 32 chars ⇒ reject loading. Tokens never appear in traces or error logs
- [ ] **Age and clock calculations** (mock clocks, like `tests/test_numeric_tree.py`): `observed_age_ms` added to age; sources cannot make age younger than age-since-receipt; `age_ms > max_age_ms` ⇒ `criterion_unavailable`; exact `max_age_ms` match ⇒ pass; `read_ms` before log start ⇒ negative offset, not "fresh"; newer facts overwrite older ones; wall clock step adjustments **never** alter verdicts (no path consumes them)
- [ ] **Fail-closed per table §3i**, one test per row: disconnected; disconnect mid-session ⇒ facts dropped immediately and **do not** resurrect on reconnect without new facts; protocol violations; out-of-range numbers ⇒ `value_out_of_range`; `±inf` from `1e999` ⇒ `value_out_of_range`; `c.facts` providing value for sourced criterion ⇒ ignored, `criterion_unavailable`; **gate `fail: open`, degraded SystemOne, disconnected external source ⇒ still BLOCK** (pins `known_failure`/`DEGRADED_REASONS` boundary)
- [ ] **Traces** (`fixtures/traces/invalid/` + `expected_errors.yaml`): `gate_facts` with `source: external:…` missing `connection`/`seq`/`observed_age_ms` or timestamps; mismatched `age_ms`; malformed `source_id` ⇒ `TraceValidationError` (`NE4001`). `external_source_refused` aggregated per second (floods do not bloat traces); malformed `claimed_id` ⇒ `"?"`
- [ ] **Standalone external source warning** (`python/tests/test_compiler.py`, §9 question 8): actuator-controlling action where all `allow_when` criteria declare `external_source` ⇒ `build` warns, build succeeds; paired with non-external criterion ⇒ no warning; non-actuator action (`signal_pins`, read-only) ⇒ no warning
- [ ] **Replay never touches sources:** `ReplaySession` on traces containing external facts produces identical verdicts without sockets, without token environment variables, and with all `socket`/`bind`/`connect` calls blocked (tested using mock interceptor)
- [ ] **Target equivalence:** `verify` produces identical verdicts on `sim` and `linux` from identical `gate_facts`; virtual `sim` sources use identical receiver and message validation functions as physical sockets
- [ ] **Public contract:** `tests/test_public_api.py` and `docs/spec/python_api.md` §2 pin public receiver name; no new CLI commands beyond declarations (if added, `tests/test_cli_contract.py` and spec §6 update together)
- [ ] `neuroedge gate lint` and `neuroedge verify` green; `pytest -q` 0 failed, 0 skipped

## 8. Post-Approval Tasks

- [ ] Update `schemas/gate.v1.json` (`external_source`, `allOf` for `type: numeric` only) and `docs/user/thuat-ngu.md` (external sources, `external_source`)
- [ ] `engine/gate_resolver.py` (pattern check, preserve across inheritance), `engine/constraints.py` if needed, `engine/gate.py::_gather` (receiver is sole provider for sourced criteria), `engine/compiler.py` and agent loader (`[external]` block, bidirectional §3c, reject `esp32s3`)
- [ ] Unix socket receiver, message layer §3e, virtual sources in `neuroedge.testing`; `python/neuroedge/trace.py` (lint §3h); `testing/player.py` (ensure replay does not touch sources)
- [ ] `docs/spec/external_facts.md` (protocol specification, adapter conventions: capture-time `observed_age_ms`, transmission rates, atomic messages) and compliance vectors §7; no `schemas/external_fact.v1.json` yet (§9 question 5)
- [ ] `docs/spec/threat_model.md`: section "§2c. In-scope: External fact sources" (table §3d); state that external facts never enter through `ToolCall`
- [ ] `docs/spec/tool_calling.md` §7: four lifecycle events §3h; `docs/spec/simulation_coverage.md`: note external sources are **not HAL primitives** so do not enter matrix §2
- [ ] `docs/spec/python_api.md` §2 and `tests/test_public_api.py`: public receiver name; `CONTRIBUTING.md` §3: add `fixtures/external_facts/` corpus to "Adding a negative fixture" table
- [ ] `neuroedge-prd.md`: Appendix B (widen causes for five rows in §4); FR-MDL-04/FR-MDL-10 if wording changes; product owner decisions in §9 assigned `Q-N` in §15
- [ ] `neuroedge-roadmap.md`: TSK-I6-07 complete, exit criterion 10 of I6; `TODOS.md` #56 unblocked ("RFC approved" trigger achieved)
- [ ] Sample gates in `fixtures/gates/valid/` using external sources: standard PR, `scripts/check_digests.py --update`; sample gates for actuator actions always pair with in-core trusted criteria (§9 question 8)
- [ ] `neuroedge build` warning (`engine/compiler.py`) for actuator actions relying solely on external sources (§9 question 8)
- [ ] `docs/rfc/README.md` (RFC-0014 row) and `CHANGELOG.md` `[Unreleased]`

## 9. Decisions on Open Questions (Q-65, 2026-10-04)

Product owner decided under the **maximum safety** principle of Q-57: between two alternatives, choose the fail-closed option that is harder to misuse. Questions 1–7 and 9–10 retain draft defaults, written in §3. Question 8 adds a build warning and has been incorporated into §5, §7, and §8. This section is the decision record: if §3–§8 conflict with this section, fix §3–§8. Signed by lead architect on PR #92.

1. **Remote sources: omitted in initial version.** Local co-located sources only, over Unix sockets (§3a, §3d). Remote sources (Frigate on NAS) require a supplemental RFC using TSK-P2-04 device identities (mTLS) for handshakes, avoiding a second authentication mechanism. *Why:* multiple identity provisioning/revocation mechanisms multiply points of failure.
2. **`esp32s3` does not accept external facts.** `neuroedge build --target esp32s3` rejects agents declaring `[external]` (`NE3001`, §3i). Gateway routing (TSK-P2-05) requires a separate RFC.
3. **Humans cannot confirm in place of dead sources.** `on_block.confirms` forbidden on sourced criteria, as with all `numeric` criteria (RFC-0009 §3a). Modifying this requires an RFC amending RFC-0009.
4. **`numeric` only.** Two-state flags transmitted as numbers 0/1 with `range: { min: 0, max: 1 }`. Guarantees facts carry age tracking and do not slip through the `known_failure` loophole of missing `bool` criteria (§3a).
5. **Wire protocol in `docs/spec/external_facts.md`, not yet in `schemas/`.** This specification serves as a Beta trial. Freezing as `schemas/external_fact.v1.json` requires an RFC following Beta feedback. *Why:* freezing before user validation forces all future revisions into `v2` (consequence of Q-58).
6. **No fact types beyond `numeric`.** New types (`level`, `choice`, string) require dedicated RFCs; strings introduce command injection surfaces.
7. **Core contains only receiver, protocol, and compliance vectors** (§3j). The repository contains no sample adapters (Frigate, Home Assistant, MQTT). Adapter hosting, licensing, and maintenance will be decided upon implementing `TODOS.md` #56.
8. **External sources permitted as sole basis for ALLOW, but not silently.**
   - Gates retain full authority; this RFC does not alter resolution semantics.
   - `neuroedge build` **warns** (does not block) when an actuator-controlling action has a gate where all `allow_when` criteria declare `external_source`. Actuator-controlling actions drive non-`signal_pins` `digital_out` pins, PWM channels, or `motion.*`. The warning highlights residual risks 1–2 in §5 and the recommended fix: pairing with an in-core trusted criterion (`analog.in`, `digital.in`).
   - Repository sample gates for actuator actions always pair criteria accordingly.
   - *Why warn rather than block:* gates do not know which action they attach to (binding lives in the agent), so `gate lint` cannot enforce this. Blocking at `build` eliminates legitimate camera-only integrations. Warning surfaces the risk without altering verdicts.
9. **Default closed: confirmed.** Receiver runs only when `agent.toml` declares `[external]`. No CLI flag can force-enable it (similar to network MCP in Q-58).
10. **(Lead Architect) Approved constants in §3d–§3e as proposed:**

    | Constant | Value |
    |:---|:---|
    | Minimum token length | 32 characters |
    | Maximum unauthenticated connections | 8 |
    | Handshake timeout | 2 s |
    | Lock out source after 5 consecutive failures | 60 s |
    | Minimum interval between handshakes per source | 1 s |
    | Maximum messages per second | 100 |
    | Maximum line length | 4096 bytes |
    | Maximum `observed_age_ms` | 4294967295 (matches `NETR` `max_age_ms` field width) |

    Future modifications to constants are changes to `docs/spec/external_facts.md`; relaxing safety limits requires an RFC.

**Minor amendment (2026-10-04, Q-68):** [RFC-0016](0016-loi-tach-duoc-va-extension-sdk.md) §9 question 6 adds `plugin` key under `[external.sources.<id>]` for in-process fact sources (plugin group `neuroedge.fact_sources`), and makes `socket` optional when no source uses sockets. Bidirectional gate ↔ agent rules, fact age tracking, and fail-closed semantics of this RFC remain unchanged.
