# Draft RFC — Design Notes (Unnumbered): Node Coordination Protocol for Tiered Robots

> **Design Notes — Draft RFC.** This file sits alongside numbered RFCs but has **not yet been assigned an RFC number**. When opening an RFC
> PR per `CONTRIBUTING.md` §3 (PR containing only the RFC file — TSK-W3-02), this draft will be renamed to
> `docs/rfc/NNNN-<slug>.md` following `docs/rfc/0000-template.md` with the next unused number
> ([`README.md`](README.md)). This file contains **no** schedule, task status, or exit criteria: those reside
> solely in [`neuroedge-roadmap.md`](../../roadmap/neuroedge-roadmap.md) increment **I14** (§7.4); a minimal single
> host ↔ single MCU version (serial, heartbeat, link loss) is split out earlier in **I3a**, TSK-I3a-06 (**Q-75**). Decisions reside only in
> `neuroedge-prd.md` §15: **Q-32** (trace `v1`), **Q-33** (RP2350), **Q-34** (ROS 2/Nav2), **Q-35**
> (link loss), **Q-36** (wire), **Q-37** (`motion.*` token), **Q-38** (safety certification), **Q-40**
> (post-Beta ordering). Reconciliation with settled specifications following TSK-S4-09 and TSK-S2-07 is located in §3.1, §3.3, §3.4,
> §5, and Appendix; open questions remain in Appendix.

| | |
|:---|:---|
| **RFC Code** | *(unassigned — assigned upon opening RFC PR)* |
| **Title** | Node coordination protocol for tiered robots (black channel) |
| **Affected contracts** | `trace.v1` *(no edits to `schemas/` — Q-32 selects Option A, §3.4)* · `NE1` stream specification (`simulation_coverage.md` §4) · command revocation contract (`voice_fsm.md` §5) · gate resolution semantics *(possible — see §3.6)* · `NETR` *(no, unless new nodes arise)* |
| **Related PRD requirements** | FR-TGT-08, FR-HAL-01, FR-CI-07, FR-MDL-10, NFR-SEC-04/05/09 |
| **Proposer** | *(fill upon opening)* |
| **Date opened** | *(not opened)* |
| **Status** | Draft — undiscussed |
| **Approvers** | Lead Engineer **if** touching gate resolution semantics; if only touching traces, follows regular RFC process |

**Related:** `docs/architecture/vi/15-target-architecture.md` §4.3 (parent design note, Stage 3);
`docs/spec/threat_model.md`; `docs/spec/tool_calling.md`; `docs/spec/voice_fsm.md` (command revocation);
`docs/spec/simulation_coverage.md` §4 (traces from devices); `docs/rfc/0002-mo-rong-target-va-nguyen-thuy-thi-giac.md`
(target tiers); IEC 61784-3 (black channel).

---

## 1. Problem

A FOFOCA-style robot comprises **one brain (Pi 5) and multiple controllers (MCUs)** coordinating together:
motor, display, manipulator. NeuroEdge today treats each execution environment as **independent**:

- Each target is a separate runtime (`sim`, `linux`, `esp32s3`); there is no concept of a single
  agent coordinating multiple nodes.
- `docs/spec/tool_calling.md` §8 (`esp32s3` stream) outlined "MCP for devices routed through gateway or `linux`
  machine", but that is **a single device behind a gateway**, not multiple MCUs coordinating.
- `trace.v1` hardcodes **one** `target`/`board_id` for an entire session
  (`schemas/trace.v1.json`, `metadata.required`) — leaving no place for node identities.
- MCP network transport is disabled by default (NFR-SEC-09); `mcp serve --http` (TSK-P2-04, Q-58) is the sole authenticated port, and not yet a channel to nodes.

Consequence: it is impossible to express "a single intent executed collaboratively across multiple nodes", nor is there
replay verification for a session spanning multiple chips.

## 2. Why the Current Schema Does Not Solve This

| Current proposition | Why it blocks multi-node |
|:--|:--|
| `metadata.target` 3-value enum (`trace.v1.json`) | Nowhere to declare multiple nodes; RP2350 node has no target yet (pending RFC-0002) |
| `events[].additionalProperties: false` (`trace.v1.json`) | Cannot add event-level `node_id` without changing schema — and the `NE1` stream specification, which has exactly three keys (`simulation_coverage.md` §4) |
| `board.py` `SUPPORTED_TARGETS = ("sim","linux","esp32s3")` (`python/neuroedge/hal/board.py`) | New nodes must go through RFC-0002 (tier 3 `rp2350`) |
| On-device fail-closed invariant (`docs/spec/voice_fsm.md`) | **Forbids** a "centralized gate on Pi" solution — if Pi is lost, actuators must return to safety autonomously |
| MCP defaults to stdio; `--http` is for clients, not nodes (TSK-P2-04) | No network channel exists yet to communicate with remote nodes |

## 3. Proposed Changes

### 3.1 Node Model

- **Node** = an execution environment having `node_id`, role, HAL, **its own gate**, cryptographic identity,
  and local safe state.
- Agent (System 1/2) running on **Pi** emits **intent** (intent/ToolCall). Each node **evaluates its own gate
  locally** with local facts before touching actuators. **No centralized gate**
  (rule BT2 of parent design note).
- **Identity** built atop existing `device_info` from TSK-S4-09 (`device_id`, `boot_id`): each device session
  self-declares, and host constructs `metadata` from it (`simulation_coverage.md` §4).
- **Intent on the wire**, not ALLOW or tokens: nodes evaluate locally, issuing and consuming their own tokens;
  nonces never leave the token ledger (`docs/spec/threat_model.md` §2). MCUs lack JSON parsers (KL-5,
  `hal_mcu_review.md`), so intent encoding must not be JSON, or KL-5 must be revised.
- Distinguish clearly: **Fleet OS** (multiple independent devices — Block 2) versus **multi-node** (a single
  robot with multiple MCUs — this RFC).

### 3.2 Wire Protocol

- Proposed: **Zenoh-pico** on MCU + `zenohd` on Pi (**Apache-2.0** license branch of
  Zenoh; `NOTICE` per `CONTRIBUTING.md` §4).
- Transport is **untrusted**: treated as a "black channel" per IEC 61784-3. All safety guarantees
  reside in §3.3 and individual node gates.
- Option B: **micro-ROS / Micro XRCE-DDS** (Apache-2.0). **Settled in Q-36:** Zenoh-pico; spike TSK-W3-01
  serves as elimination test (three thresholds in PRD §15); switch to micro-ROS only if Zenoh fails and micro-ROS passes (§7).

### 3.3 Black Channel Safety Layer

Each coordination message carries extra protection fields:

| Field | Role |
|:--|:--|
| `node_id` / `conn_id` | Identifies node and connection; protects against cross-node spoofing |
| `seq` | Protects against replay and out-of-order delivery; bounded acceptance window |
| `crc` | Detects bit corruption over untrusted channels |
| `epoch` / `boot_id` / `ttl` | Protects against stale intents. Device `offset_ms` clocks count from their respective `device_info` and reset per `boot_id`, making inter-device timestamps incomparable; token TTL (p95 × 3) runs on node's local clock and does not protect the wire |
| `heartbeat` | Pi↔node watchdog; loss → node rejects new intents and returns to safe state |

**Communication loss is a power-off-style stop.** `voice_fsm.md` §5.3 today permits only shutdown (SIGTERM) to abort
an assigned command. This RFC must amend §5: new `actuator_aborted.reason`, an input event
"communication loss" allowing replay to recalculate cancellations, and safe state declared per actuator (**Q-35**: stop if undeclared) —
cutting an active latch pulse re-locks the door (`voice_fsm.md` §5.3). For `motion.*`, leased tokens with deadlines
(**Q-37**) expire automatically when commands cease, making communication loss yield a stop without separate detection.

**Cross-chip barge-in / cancellation.** Dialogue state machine runs on Pi, while pending commands may reside on nodes.
§5.2 of `voice_fsm.md` requires cancellation within ≤ 20 ms and closing tokens (`ne_token_close`); this RFC must define
the Pi → node cancel message and its timing budget (RB-3, `hal_mcu_review.md`).

Local safe state (Tier T0 of parent design note): hardware pull-downs / watchdogs / current limits — software
**cannot** rescue during crash/SIGKILL (`docs/spec/lab_mcp.md` §2.3, §15 risk 3).

### 3.4 Unified Trace

**Q-32 (2026-09-25) selected Option A.** Table retained for rationale:

| | Option A (recommended for v1.x) | Option B |
|:--|:--|:--|
| Approach | Optional `metadata.nodes[]` + `data.node_id` convention in events | `trace.v2` with `nodes[]` and event-level `node_id` |
| Compatibility | Non-breaking: `metadata.additionalProperties: true` (`trace.v1.json`) | Breaking: requires schema version bump |
| Cost | Low; **no edits to `schemas/`** (`metadata` open, `data` free-form — precedent RFC-0002, `TODOS.md` #1); document conventions in `simulation_coverage.md` §3–§4 | High: migrate corpus; change `NE1` stream specification |
| Risk | "Soft" conventions inside `data` | Clean, formal |

Regardless of option selected: each device maintains its own `offset_ms` clock, so unified traces must align clocks.
Multi-node traces live in `fixtures/compliance/multinode/` (closed corpus), **not** in
`fixtures/traces/`: that directory holds exactly three canonical traces (`voice_fsm.md` §9), and a fourth file breaks
tests and alters firmware vectors.

### 3.5 Gateway and MCP

- Reuse TSK-P2-05 direction (MCP gateway) as ingress for nodes; **do not** use MCP as
  MCU wire protocol (JSON-RPC is too heavy).
- Network MCP remains at agent boundary: **Streamable HTTP + OAuth 2.1** per MCP spec 2026-07-28,
  following mTLS (NFR-SEC-04) and blocked call repeat testing (`test_repeating_a_blocked_call_over_the_network_never_slips_through`, TSK-P2-04).

### 3.6 CLI and `verify`

- `verify` expands for node clusters: compares verdicts and actuator states across nodes;
  divergence → `SafetyRegressionError` (NE4002, FR-CI-07 — tier 1 targets only). Built on
  existing `verify --targets esp32s3 --port` (TSK-S4-09); unimplemented features exit with code 2 (invariant 10).
- No new CLI flags added in v1; node configuration design lives in `agent.toml` (`[nodes]` section,
  proposed — finalized in full RFC).

## 4. Compatibility Impact

| Item | Impact |
|:---|:---|
| Do currently valid files remain valid? | Yes — Option A (Q-32) adds only optional fields in `metadata` |
| Do currently invalid files become valid? | No |
| Does it require bumping schema version (`v1` → `v2`)? | No (Q-32) |
| Impact on issued gate hashes / signatures? | None (gates unchanged) |
| Impact on three canonical trace files? | None — multi-node traces reside in `fixtures/compliance/multinode/` |
| Does any gate in `digests.lock` change digest? | None |
| Must `NETR` layout or C walker change? | No, unless new node types arise |
| Does any expected answer in tool call corpus change? | Yes — adds multi-node cases (closed corpus) |

## 5. Safety Impact

**Gates must never become looser.** This RFC only introduces new communication paths, all of which must
traverse individual node gates. New threats requiring rows in `docs/spec/threat_model.md` §2c:

| Shortcut | Blocked by |
|:--|:--|
| Node spoofing (sending intent posing as another node) | Identity + binding key (PSK/mTLS); `node_id` in wrapper |
| Replaying stale intents | `seq` + epoch/`boot_id` + window; ALLOW and tokens never traverse wire (nodes evaluate locally) |
| Channel message tampering | CRC + (optional) MAC; transport untrusted |
| Heartbeat starvation/manipulation | Watchdog → local safe state |
| Compromised Pi sending malicious commands | Individual node gates remain final check; envelope N2 constrains duty/rate. **Insufficient:** `call_source` binds per connection (`tool_calling.md` §5), yet all connections to nodes originate from Pi — either nodes cannot distinguish sources, or Pi forwards sources and a compromised Pi can spoof `local_grammar`. `ask` confirmation (Q-26) also traverses Pi. Requires dedicated row in `threat_model.md` §2c |
| Interruption on Pi with command pending at node | Cancel message Pi → node within budget of `voice_fsm.md` §5.2 — not yet designed (§3.3) |
| Compromised node minting own tokens | Out of scope for v1 (as in threat model §3); milestone in `TODOS.md` #2 |

If RFC touches gate resolution semantics: requires Lead Engineer approval.

## 6. Alternatives Considered and Rejected

| Alternative | Rejection rationale |
|:---|:---|
| Centralized gate on Pi | Breaks on-device fail-closed upon network loss (rule BT2 of parent design note; Appendix H.3) |
| MQTT as wire | "Broker paradox" — introduces a broker between brain and nodes in the same robot. (Q-11: EMQX rejected; permissive brokers reserved for Fleet OS, Block 2) |
| DDS/ROS 2 as wire | Infeasible on MCUs; heavy multicast; pulls state machine off device |
| Custom proprietary binary protocol | High build + maintenance cost, no ecosystem; "black channel" portion still requires custom implementation |
| MCP as MCU wire | Heavy JSON-RPC; ill-suited for microcontroller resource constraints |
| Pure HTTP/REST | Lacks pub/sub, heartbeats, discovery; requires more custom plumbing than Zenoh |

## 7. Verification Evidence

- [ ] **Spike TSK-W3-01 (elimination test, Q-36):** Zenoh-pico on ESP32-S3 and RP2350 (Q-33) ↔ `zenohd` on Pi:
      p99 Pi → node ≤ 20 ms, internal SRAM ≤ 40 KB, reconnect ≤ 2 s, with flash; failure ⇒ evaluate micro-ROS under identical conditions;
      document report in `docs/reports/`.
- [ ] Fault injection: drop / delay / replay / tamper → **zero ALLOW leaks**; link loss
      → node transitions to safe state — verified on physical hardware (QEMU does not emulate GPIO, `TODOS.md` #21).
- [ ] Replay of unified multi-node traces passing in CI.
- [ ] Fuzz black channel wrapper (reusing pattern from `NETR`).
- [ ] Tool call corpus extended with multi-node cases per bidirectional closure rule.
- [ ] `neuroedge gate lint` and `neuroedge verify` remain green; 0 skipped tests.
- [ ] `NOTICE` updated if adopting Zenoh/micro-ROS code (5 obligations under `CONTRIBUTING.md` §4).

## 8. Implementation Steps Upon Approval

- [ ] Option A (Q-32): do not edit `schemas/` — document conventions in `simulation_coverage.md` §3–§4
- [ ] Update `docs/spec/voice_fsm.md` §5 (communication loss stop, cross-chip cancellation) and §8 (new events)
- [ ] Update `docs/spec/threat_model.md` §2c and `docs/spec/tool_calling.md`
- [ ] Update `neuroedge-prd.md` if any FRs are affected; new decisions → `Q-N` in §15
- [ ] Update status of TSK-W3-01, W3-02, W3-03, W3-04, W3-06, W3-07 in `neuroedge-roadmap.md` I14 (§7.4)
- [ ] Add fixtures + tests: corpus `fixtures/compliance/multinode/` + `expected_results.yaml`, bidirectionally closed (`digests.lock` locks gates only, unrelated)
- [ ] Update RFC row in `docs/rfc/README.md` and one `CHANGELOG.md` entry under `[Unreleased]`
- [ ] `NOTICE`: Zenoh (Apache-2.0 branch) or micro-ROS

## Appendix — Open Questions of Draft

1. ~~Wire protocol: Zenoh or micro-ROS?~~ — Q-36: Zenoh-pico, spike serves as elimination test
2. ~~Trace: A or B?~~ — Q-32: A
3. Node configuration model in `agent.toml` (`[nodes]`) — concrete shape?
4. ~~Reference node: ESP32-S3 + RP2350 or ESP32-S3 only first?~~ — Q-33: ESP32-S3 + RP2350
5. Node pairing keys: symmetric PSK first or immediate mTLS?
6. Communication loss: policy Q-35 (per-actuator, stop by default); open: how to amend `voice_fsm.md` §5?
7. Cross-chip cancellation: Pi → node cancel message, timing budget?
8. `call_source` and `ask` confirmation via Pi: which source does the node trust?
9. Intent encoding on MCU (KL-5: no JSON parser)?
10. Inter-device clock synchronization for unified traces?
