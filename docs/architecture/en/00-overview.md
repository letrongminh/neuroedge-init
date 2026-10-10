# 00 · Architecture Overview

> **Scope:** the whole system, at the highest level. **Source of truth:** the code in `main`; requirements in
> [`neuroedge-prd.md`](../../../roadmap/neuroedge-prd.md); progress in
> [`neuroedge-roadmap.md`](../../../roadmap/neuroedge-roadmap.md) §0. Label conventions `done` / `partial` /
> `planned`: [`README.md`](../README.md).

**What this chapter is for:** This chapter is for every engineer, architect, and partner who needs an overall view of the entire NeuroEdge architecture. The document answers foundational questions: *What problem does NeuroEdge solve in Physical AI? What mechanism ensures physical actions never bypass the safety gate? How does the system tier and maintain target equivalence between the development machine (host) and the edge chip ($5)?* Before reading, readers only need a basic understanding of AI agents and embedded control. After this chapter, application developers should read [`01`](01-context-c4l1.md) and [`12`](12-dev-quickstart.md); systems engineers should read [`02`](02-container-c4l2.md) and [`03`](03-component-host-c4l3.md); architects should read [`15`](15-target-architecture.md).

## 1. What problem NeuroEdge solves

When a chatbot answers incorrectly, the user clicks "Regenerate". When an agent controlling a physical device is wrong, the door lock is already open, the fan is already off, the relay is already closed — there is no "Regenerate" button. An AI model produces proposals; it cannot be the place that decides whether a physical action is allowed to happen.

NeuroEdge separates those two concerns. Every action proposal — from the local command grammar, from an LLM, from another agent via MCP — is normalized into a **typed tool call**, then must pass a **gate**: a safety policy written in YAML, versioned, inheritable, compiled into a deterministic decision tree. When the gate returns `ALLOW`, a **single-use verdict token** ([one-time token](../../user/thuat-ngu.md)) is issued, and only that token can open the exact hardware pins of that action. Every fact, verdict and pin command is written to a replayable **trace** ([trace](../../user/thuat-ngu.md)). The same gate runs on the simulator (`sim`), on Linux (`linux`) and on the ESP32-S3 chip (`esp32s3`).

### 1.1 Product spirit — six promises

**No contract, no action.** Each promise below is something the user perceives, and each
promise has an architectural mechanism that holds it. When a design decision weakens a promise, that decision is wrong
— even when it makes the product faster or easier to demo.

| # | Promise to the user | Architecture holds the promise by | Where the user sees it |
|:---:|:---|:---|:---|
| 1 | **Errors in the real world cannot be undone, so every command must be approved in advance.** Models only propose, never decide | One single path `dispatch()` → gate → single-use token → HAL; no shortcuts ([`05`](05-code-gate-hal-c4l4.md)) | Every action has an `ALLOW`/`BLOCK` verdict with a reason |
| 2 | **When unsure, do not act.** Offline, stale sensors, frozen camera, model not answering ⇒ block | Fail-closed in every direction (invariant 2); only commands that bring actuators to a safe state are always allowed (Q-62) | The device stops or asks again, never guesses |
| 3 | **One contract everywhere.** Trying on a laptop is identical to running on a $5 chip | Same gate file, pure resolution, two implementations in Python and C of the same specification ([`10`](10-target-equivalence.md)) | `neuroedge verify` produces the same verdict on `sim`, `linux`, `esp32s3` |
| 4 | **Evidence over promises.** Every incident can be reproduced on the developer's machine | Every fact, verdict, pin command into the trace; replay recomputes without calling the model ([`06`](06-runtime-flows.md) §7) | `neuroedge replay`, `gate explain`, Action CI in PRs |
| 5 | **Humans hold the final authority.** Models and other agents cannot confirm on behalf of humans; but no one can confirm on behalf of a physical reading either | `ask` can only be answered by a human on the device (Q-26); drafts an MCP client writes through NeuroEdge Lab must be approved by a human, and no tool can lock them (Q-71); numeric criteria are forbidden in `confirms` (Q-62) | Confirmation prompt on the `--ui` page, via voice, or via button |
| 6 | **Plug into other stacks, do not swallow the whole stack.** NeuroEdge is a contract layer, not a closed platform | MCP is the entry door; model and speech are replaceable providers (P-4); schemas, specifications, compliance test suite under Apache-2.0 (Q-45); network MCP with authentication at launch (Q-58) | Claude, Home Assistant, or an agent framework calls the device through the gate |

The product grows through ten user-facing release milestones (roadmap §0.5); the architecture of each milestone and how
each milestone proves the six promises again are in [`13`](13-evolution-i0-i18.md).

## 2. The system in one picture

![E-01 · System context](../assets/svg/E-01-system-context.svg)
*Figure E-01 — Users, external systems, and the boundary of NeuroEdge. Details: [`01`](01-context-c4l1.md).*

*How to read Figure E-01:* The figure shows the entire system context at the highest level: user actors and external systems lie outside the boundary; inside the boundary are NeuroEdge (Python SDK + CLI, C99 firmware), devices (`sim` · `linux` · `esp32s3`), and project files. Solid-bordered blocks are components that already have code; dashed-bordered blocks are components planned for the future (`planned`). Key takeaway: whether originating from typed commands, voice, or network connections, every physical action must pass through the same NeuroEdge safety control boundary.

The only path from intent to a hardware pin — the **execution spine** — is the same for every caller source and every environment:

```mermaid
flowchart LR
    subgraph Sources["Callers (untrusted)"]
        G["Local command grammar<br/>commands.toml"]
        S2["System 2 LLM<br/>via LiteLLM"]
        MCP["MCP client<br/>Claude Desktop"]
    end
    TC["ToolCall<br/>name · arguments · source"]
    D["dispatch()<br/>schema check · call_source"]
    DO["c.do()"]
    GATE{"Gate engine<br/>evaluate()"}
    TOK["TokenLedger<br/>one-time token"]
    HAL["HAL<br/>authorize(token, pin)"]
    PIN(["Pin / actuator"])
    OB["on_block<br/>deny · ask · escalate · degrade"]
    TR[("Trace<br/>trace.v1.json")]

    G --> TC
    S2 --> TC
    MCP --> TC
    TC --> D --> DO --> GATE
    GATE -- ALLOW --> TOK --> HAL --> PIN
    GATE -- BLOCK --> OB
    GATE -.-> TR
    HAL -.-> TR
```

*How to read the diagram:* Rectangular blocks are software components; diamonds are safety gate evaluation points; ellipses are physical actuator pins. Solid arrows represent the mandatory execution spine (untrusted caller source → `dispatch()` → `c.do()` → gate → token → HAL); dashed arrows represent logging data to the trace file (`trace.v1.json`). Key takeaway: there is no shortcut to hardware pins without possessing a single-use verdict token issued by the gate.

- **No shortcuts.** Calling an `@action` function directly, calling `digital.out()` outside `c.do()`, handing HAL a made-up string or token, reusing a token, using an expired token — all are refused and traced (`docs/spec/threat_model.md` §2).
- **When unsure, block.** Cannot adjudicate in time, offline with no fallback, missing or wrongly typed facts ⇒ `BLOCK`, never `ALLOW` (invariant 2, `CHANGELOG.md` §3.3).
- **Evidence by construction.** The trace holds enough facts to recompute every verdict without calling a model and without touching the machine (details: [`06`](06-runtime-flows.md) §7).

## 3. The five principles and where the architecture enforces them

The principles themselves are in PRD §1.5; this table points out the **architectural mechanism** that holds each principle.

| Principle (PRD §1.5) | Enforcing architectural mechanism | Where |
|:---|:---|:---|
| **P-1** Physical actions are typed contracts | One single path `dispatch()` → `c.do()` → gate → token → HAL; without a token ledger, HAL refuses every command | [`05`](05-code-gate-hal-c4l4.md) · `actions/`, `hal/` |
| **P-2** Execution environments are peers | The same gate file, the same evaluation semantics on host (Python) and chip (C); `verify` compares decisions across targets; verification commitments are tiered by target tier (FR-TGT-08, Q-13) | [`10`](10-target-equivalence.md) |
| **P-3** Value in fleet management and commercial licensing | The safety core lives entirely in the `neuroedge` package; services (Fleet OS) are separate containers, with no code yet | [`02`](02-container-c4l2.md) §5 |
| **P-4** AI models are replaceable | Every model sits behind the `FactSource` protocol / provider; STT/TTS are also providers replaceable via configuration; the chip only captures/plays audio and evaluates gates (PRD §1.5 P-4); no SDK is imported in the core | [`03`](03-component-host-c4l3.md) §3.4 |
| **P-5** Network effects from sharing policies | Gates are versioned data, identified by `neuroedge://`, hashed with JCS SHA-256, inheritance only tightens | [`07`](07-data-contracts.md) §2 |

## 4. Architectural characteristics, in priority order

When two characteristics conflict, the one higher up wins. Each row is a design decision already backed by code.

| # | Characteristic | Means | Main tactic | Chapter |
|:---:|:---|:---|:---|:---|
| 1 | **Safe by default** | Every failure leads to a block | `budget.fail` defaults to `closed`; `fail: open` cannot be inherited; a full token ledger refuses instead of evicting old tokens | [`05`](05-code-gate-hal-c4l4.md), [`08`](08-nfr.md) |
| 2 | **Deterministic and replayable** | Same facts ⇒ same verdict, everywhere | Gate resolution is a pure function; the decision tree never reads the clock; replay recomputes from recorded facts | [`05`](05-code-gate-hal-c4l4.md), [`06`](06-runtime-flows.md) |
| 3 | **Equivalence across environments** | The agent never branches on target | Two implementations (Python, C) of the same specification, proven by truth tables and shared vectors | [`10`](10-target-equivalence.md) |
| 4 | **Auditable** | A reviewer can understand it without reading code | Gates are readable YAML; `gate explain`; traces follow a frozen schema; errors always have three parts | [`07`](07-data-contracts.md) |
| 5 | **Replaceable model** | Change provider by configuration | OpenAI-compatible standard, `python:` adapter; a model returns facts only, never `ALLOW` | [`03`](03-component-host-c4l3.md) |
| 6 | **Runs offline** | Safety functions need no Internet | The local command grammar is the fallback for every model; the core uses only the standard library for HTTP | [`06`](06-runtime-flows.md) §5 |
| 7 | **Fits a small chip** | The gate runs on ESP32-S3 | No JSON, no CEL on the chip; the `NETR` binary tree is read in place in flash; the walker allocates nothing, stack ≤ 512 B | [`04`](04-component-device-c4l3.md) |

## 5. System shape

NeuroEdge has three parts, plus the CI chain that keeps them in sync:

| Part | What it is | Language | Status |
|:---|:---|:---|:---|
| **`neuroedge` package** (host) | SDK, CLI, gate engine, `sim`/`linux` HAL, models, voice (from WAV files `done`, real-time voice sessions `partial` — [`neuroedge-roadmap.md`](../../../roadmap/neuroedge-roadmap.md) I4), MCP, Action CI | Python 3.11+ | `done` (real-time voice `partial` — roadmap I4) |
| **`esp32s3` firmware** | `NETR` walker, token ledger, UART trace, generated component for the agent, signed OTA | C99 on ESP-IDF v5.4 | `partial` — runs on QEMU; does not drive pins yet |
| **Data contracts** | `gate.v1`, `trace.v1`, `board.v1`, `agent.toml`, `NETR` v1, UART lines | JSON Schema, TOML, binary | `done`, frozen via RFC |
| **CI** | Python tests, gpio-sim, QEMU, golden images, OTA, security | GitHub Actions | `done` |

Two parts have no code today and appear only in the `planned` state: **Fleet OS** (I9) and the **Gate Registry** (I10). Everything else that is planned (the four extension primitive packs, NeuroEdge Lab over MCP, multi-node robots, vision on Jetson) is in [`13`](13-evolution-i0-i18.md).

### 5.1 Five-layer logical model

The 5-layer logical model of NeuroEdge ([`neuroedge-proposal.md`](../../../roadmap/neuroedge-proposal.md) §3.1) is spanned horizontally by the Action CI testing axis:

| Layer / Axis | Nature of layer (proposal §3.1) | Host package (`03` §2) and firmware component (`04`) implementing | Status |
|:---|:---|:---|:---|
| **L4: Agent Application Layer** | Agent logic, context memory, gated tool calls (MCP), System 2 | `mcp_host`, `mcp_server`, System 2 in `models/` | `done` |
| **L3: Action Contract Engine** (core IP) | Typed gate evaluation, policy inheritance, fail-closed circuit breaker | `engine/`, `actions/` (single-use token ledger), `ne_gate` (`ne_walker.c`, `ne_token.c`), `ne_agent` | `done` (host and QEMU) |
| **L2: Perception & conversation runtime** | Wake-word recognition, neural VAD, AEC acoustic echo cancellation, low-latency STT/TTS, the real-time conversation state machine (Q-48) | `perception/` (state machine, wake, STT/TTS), `hal/audio.py` (`EnergyVAD`), `models/` (System 1/2, grammar, knowledge) | `partial` — voice from WAV files and cloud STT/TTS `done`; real-time sessions, AEC (Q-22), remaining real wake-word models (roadmap I4) |
| **L1: Hardware Abstraction Layer (HAL)** | 5 basic primitives v1.x (`audio.in`, `audio.out`, `digital.out`, `sensor.read`, `display`), capability contract verification at compile time | `hal/` (board verification, API); firmware HAL on chip | `done` (`hal/` on host); `planned` on chip (TSK-S4-01) |
| **L0: Peer execution environments** | Specific implementations for each target (`sim`, `linux`, `esp32s3`) | `hal/sim.py` (`SimHAL`), `hal/linux.py` (`LinuxHAL`), firmware for `esp32s3` in `targets/esp32s3/` (the `sim/` package is both target `sim` (L0) and the host-side assembly point — `03` §2 rank 7) | `done` (`sim`, virtual `linux`); `partial` (`esp32s3` on QEMU) |
| **Horizontal axis: Action CI** | Event recording (JSON) → Exact replay → Action comparison | `testing/` (`TraceRecorder`, `TracePlayer`, `GoldenComparator`), `trace.py` (`trace.v1`) and `engine/trace_sink.py` (`EventLog`), `cli` (`record`, `replay`, `verify`) | `done` |

System 1 adapters in L2 (`models/`) implement the `FactSource` protocol specified by L3 (`engine/gate.py`) instead of L3 depending on L2 — that is dependency inversion; meanwhile `perception/` depends on `sim` ([`03`](03-component-host-c4l3.md) §2, rank 8). Therefore, the import graph between packages is not a naive top-down stack.

### 5.2 Layering and tiering terminology

To prevent readers from confusing the different layer/tier divisions across the documentation:

| Concept | Scale | Meaning | Defining document |
|:---|:---|:---|:---|
| **C4 architecture levels** | L1…L4 | Four architecture visualization levels: L1 Context · L2 Container · L3 Component · L4 Code | C4 model (Simon Brown) · [`01`](01-context-c4l1.md)…[`05`](05-code-gate-hal-c4l4.md) |
| **System logical layers** | L0…L4 | Five logical functional layers of the platform: L0 Target · L1 HAL · L2 Perception/Runtime · L3 Action Contract Engine · L4 Agent Application, plus the Action CI axis | [`neuroedge-proposal.md`](../../../roadmap/neuroedge-proposal.md) §3.1 |
| **Package dependency ranks** | Rank 0…10 | Import order of host-side Python modules, preventing cyclic dependencies (Tier 0: `errors`, `paths`… Tier 10: `cli`) | [`03`](03-component-host-c4l3.md) §2 · `python/tests/test_architecture_layers.py` |
| **Target commitment tiers** | Tier 1…3 | Hardware verification commitment levels of the core team: Tier 1 (official: `sim`, `linux`, `esp32s3`), Tier 2 (extended: `jetson`), Tier 3 (community: `stm32`, `rp2350`) | PRD FR-TGT-08, Q-13 · proposal §3.2 · [`15`](15-target-architecture.md) §4.1 |
| **Robot layering tiers** | T0…T6 | Seven distributed robot architecture layers: T0 Hardware actuators/local safety · T1 Wire Zenoh-pico · T2 Black channel safety layer · T3 Per-node gates · T4 Unified trace · T5 MCP · T6 ROS 2 bridge | `draft-ke-hoach-mo-rong-robot-fofoca.md` §4 · [`15`](15-target-architecture.md) §4.3 |

## 6. Current state by capability

The table below is a snapshot of the shape, not a progress table; per-task progress is in roadmap §4–§8.

| Capability | `sim` | `linux` | `esp32s3` |
|:---|:---|:---|:---|
| Gate: resolution, evaluation, tokens | `done` | `done` | `done` on host and QEMU |
| Pin control | `done` (virtual) | `done` on gpio-sim | `planned` (TSK-S4-01) |
| Sensors, display | `done` (virtual) | `done` on `i2c-stub`, `vkms` | `planned`; the LVGL interface builds on host only |
| Voice (from WAV files) | `done` | `done` | `planned` (I5) |
| Real-time voice (microphone) | `done` on a laptop (`run --mic`, TSK-I4-04) | `partial` — only opens the device | `planned` |
| Cloud models (System 1, System 2) | `done` | `done` | not applicable: the chip only evaluates gates |
| MCP | `done` | `done` | not applicable |
| Trace, replay, verify | `done` | `done` | `done` (UART, QEMU) |
| Signed OTA update | not applicable | not applicable | `partial` — on QEMU |

## 7. Boundaries — what NeuroEdge is not

- **Not certified functional safety** (no SIL per IEC 61508, no PL per ISO 13849 — Q-38). The gate does not replace an emergency stop or a hardware interlock.
- **Does not defend against an attacker inside the same process.** A token is `(nonce, digest)` in memory; the in-scope threat is **accidentally bypassing the gate**, and that is proven by tests (`docs/spec/threat_model.md` §3, `TODOS.md` #2).
- **Not a cloud service.** Today NeuroEdge is a library, a CLI and a firmware; there is no server operated by NeuroEdge.
- **Not an inference token reseller** ([`neuroedge-proposal.md`](../../../roadmap/neuroedge-proposal.md) §6.4; PRD §1.4 N4). The provider abstraction is self-hosted within the core; users operate it themselves and pay model providers directly.
- **Does not do SLAM or navigation itself** — only gates velocity commands via ROS 2 / Nav2 ([`neuroedge-prd.md`](../../../roadmap/neuroedge-prd.md) §14, Q-34).
- **No paid marketplace** ([`neuroedge-prd.md`](../../../roadmap/neuroedge-prd.md) §14, PF-3).
- **No agent-to-agent payment** ([`neuroedge-prd.md`](../../../roadmap/neuroedge-prd.md) §14, PF-4).
- **No custom wake-word training in v1.0** ([`neuroedge-prd.md`](../../../roadmap/neuroedge-prd.md) §3).

The overall target architecture (to-be architecture) for subsequent phases is in [`15-target-architecture.md`](15-target-architecture.md).

## 8. Further reading

Reading paths by role are in [`README.md`](../README.md). Beginners start at [`12-dev-quickstart.md`](12-dev-quickstart.md).
