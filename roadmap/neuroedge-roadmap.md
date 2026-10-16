# NeuroEdge — Execution Roadmap

## From `sim` Core to v1.0 and Developer Beta

**Version:** 2.0


**Created:** September 21, 2026 · **Updated:** October 16, 2026 (Q-77 sync, Q-88: Lab-only tasks leave I2d) · change log: `CHANGELOG.md`

**Source documents:** `neuroedge-prd.md` · [`TODOS.md`](../TODOS.md)

**Scope:** increments **I0** to **I8**, including I2a → I2f and I3a — MVP (v1.0) and Developer Beta (§0.5); everything else Q-77 removed is listed in §6. Sole location recording task status, exit criteria, dependencies, and forecast dates (Q-39).

**Design notes:** `docs/architecture/vi/15-target-architecture.md` §4.4 (vision I2a, I3a) · `docs/architecture/vi/16-ecosystem-landscape.md` §4 (open platform, I2c) · `docs/spec/lab_mcp.md` — historical (Q-77, Q-88)

**Out of roadmap:** Block 4 (Field AURA) and Block 5 (Commercial Marketplace; minimal Hub in I2e — Q-72) were removed with the rest of Q-77 — §6

---

## Table of Contents

0. [Execution & handoff dashboard](#0-live-execution--handoff-dashboard)
1. [Resource assumptions](#1-resource-assumptions)
2. [Critical path, dependencies and anti-drift rules](#2-critical-path-dependencies-and-anti-drift-rules)
3. [Open source reuse strategy](#3-open-source-reuse-strategy)
4. [Increments to v1.0 = MVP (I0–I7)](#4-increments-to-v10--mvp-i0i7)
5. [Developer Beta and branch points (I8)](#5-developer-beta-and-branch-points-i8)
6. [Removed from roadmap (Q-77)](#6-removed-from-roadmap-q-77)
7. [Post-Beta extension directions](#7-post-beta-extension-directions)
8. [Outside roadmap](#8-outside-roadmap)
9. [Scope-cut ladder](#9-scope-cut-ladder)
10. [Decision schedule](#10-decision-schedule)
11. [Operating cadence](#11-operating-cadence)
12. [Early indicators and intervention thresholds](#12-early-indicators-and-intervention-thresholds)

**Appendices**

- [B — Procurement and infrastructure bill of materials](#appendix-b--procurement-and-infrastructure-bill-of-materials)
- [C — Source repository layout](#appendix-c--source-repository-layout)
- [D — Wire protocol](#appendix-d--wire-protocol)

---

## Document Conventions

All codes and symbols used in this document (`I0`–`I8`, removed codes up to `I18` in §6, `TSK-*`, `A1`–`C8`, `TR-N`, `Q-N`, `RB-N`, `V1`–`V7`, `§x.y`…) are decoded in **[`docs/user/thuat-ngu.md`](../docs/user/thuat-ngu.md)** — the single place, with their full definitions. Time is measured in increments and absolute calendar dates; sprint names (Sprint 1–6) and block names (Block 1a, 1b, 2, 3) remain as historical names only (Q-39).

## 0. Live Execution & Handoff Dashboard

> **Purpose:** Provide a single centralized view of the real-time status across the entire project. In every work session, an incoming engineer or AI Agent receiving handoff needs only to read this section to immediately grasp: *Where the system is, what was just completed, who is working on what, and what the next action steps are.*

### 0.1 Executive Status Bar

| Indicator | Current status | Notes & Links |
|:---|:---|:---|
| **Current phase** | 🟡 **Phase MVP (§0.5)**, sequence per Q-72 — I2d then I2e (fish tank NeuroEdge Blueprint traversing all three loops on simulation) before the 8-week demand gate; remainder of I1, I2a, I2c interleaved; partner trial (Q-70) in parallel; voice (I4, I5) removed (Q-77, §6); Studio paused (Q-72) | Increments and forecast dates: §0.2 |
| **Open increment** | 🟡 **I2d — Missions and operator agents** (Q-72) | I1 has TSK-I1-02 remaining (reactivated for the 8-week gate) and Studio (paused) · I0 completed 42 / 42 · details §0.2 |
| **Next milestone** | **8-week demand gate (Q-72, B6–B8)** — thresholds in PRD §11.2 | Dates: assumptions in §0.2 · branching by outcome: §5.6 · direct hand-off wheel, not on PyPI (Q-39) |
| **Last updated** | **2026-10-16** | Session 2026-10-16: missions SRS approved (Q-87, `docs/spec/missions.md`, TSK-I2d-01 → I2d-21); pin map approved by the lead engineer, TSK-I2d-32 done (Q-84 phases A, A+ and B complete; canvas C deferred); Blueprint SRS approved (Q-86); the architecture page gains chapter 12, what a person can do today; phone app draft in `docs/app-di-dong/` (no decision yet); documents synced to Q-77, and Q-88 moves the Lab-only tasks out of I2d (§6). Earlier sessions: `CHANGELOG.md` |
| **Core CI status** | ✅ **PASS 5083/5083 · SKIP 0** | `python/tests/` 128 test suites; `tests_linux/` 119/119 on kernel; `ui-golden` 66 images; `ota-rollback` phases a–g; `firmware-qemu` added stack guard and six boots via serial console (Q-79); security scanners |
| **Non-technical blockers** | 🟡 **2 blocking items** | 🔴 Box-3 and RPi 5 have not arrived (TSK-S1-10 → I3; TSK-I2-01) · camera board selected is M5Stack CoreS3 but not yet ordered (Q-61, TSK-I3a-01). Not blocking I2d, I2e: simulation first, physical hardware purchased later (Q-72) |
| **Deliberate deferrals** | 📋 [`TODOS.md`](../TODOS.md) | Each item includes activation trigger · demand gate reinstated by Q-72 (reversing Q-56); open business questions (`TODOS.md` #19) reviewed at 8-week gate |

---

### 0.2 Increment Matrix

Each row is an increment: a user-visible capability, ending with a release card and a measurement signal (Q-39). **Forecast** is the sole date of the increment; it changes only within the same PR containing evidence that causes it to change, cascading to all dependent increments (§2.4, R5). **Dependencies** point only to lower-numbered increments. Prior to I6, all releases are internal; the sole exceptions are direct hand-off wheels, not on any index — for a partner team (Q-70) and for NeuroEdge Blueprint testers in I2e (Q-72).

| Milestone | Increment | Forecast | Capability | Progress | Status | Dependencies | Release |
|:---:|:---|:---:|:---|:---:|:---|:---|:---|
| **Internal 0.x** | **I0 — Contract core on `sim`** | ✅ 2026-09-24 | Typed and versioned gates (lint, resolve, inheritance, arguments, `confirms`), `sim` + web UI, Action CI, MCP, System 2 via LiteLLM, `linux` replay on gpio-sim; C walker, token ledger, and UART trace on QEMU | **42 / 42** | ✅ Done | — | historical |
|  | **I1 — Internal preview on `sim`** | 2026-11-15 | External developer installs from internal wheel and runs gated agent in under 10 minutes, no hardware required | **4 / 6** | 🟡 In progress — TSK-I1-02 deferred (internal development) | I0 | tag `v0.1.0` (internal) |
|  | **I2 — `linux` at parity with `sim`** | 2026-11-29 | `run`, `record`, `mcp serve --target linux`; sensors and display on `linux`; nightly on RPi 5 | **3 / 4** | 🟡 Interactive session, sensors, display complete on gpio-sim + i2c-stub; nightly RPi 5 remaining | I1 | tag `v0.2.0` (internal) |
|  | **I2a — Extended primitives on `sim` and `linux`** | 2026-12-06 | Four packages: sensors (`digital.in`, read-only I2C, `analog.in`, numeric threshold comparison gate), fine control (PWM), vision (`vision.in`), motion (`motion.*`); six RFCs; `sim-rpi5` | **22 / 27** | 🟡 Six RFCs approved; numeric criteria and `NETR` v2; `board.v1` declares all extended primitives, `sim-rpi5`; safety envelope, `digital.in`, read-only I2C, `analog.in`, vision (virtual camera, V4L2, models, traces, sample gates) complete on `sim` and on kernel (`linux-hal` job, CI run 37153005998: gpio-sim, `i2c-stub`, `vivid`; `verify --targets sim,linux` replays sensor and vision corpus); PWM and `motion.*` complete on `sim`, `enable` line green on gpio-sim. **Remaining:** `verify` has not replayed `fan-pwm` and `rover` agents (I2a criterion 3); camera dropped mid-session on kernel (criterion 5); physical PWM channels and real actuators; vision inference golden; `esp32s3` cell of coverage matrix (TSK-I3a-01) | I2 | tag `v0.2.1` (internal) |
|  | **I2b — Starter kits and rapid assembly** | 2026-12-20 | Five hardware kits (BOM, wiring diagram, locked gate), starter gate library, `neuroedge add` | **4 / 4** | 🟡 Five kits, gate library, `neuroedge add` complete (criteria 1, 3, 4); remaining TTFV measurement with humans (criterion 2) and building kits on physical hardware | I2a | tag `v0.2.2` (internal) |
|  | **I2c — Open platform** | 2026-12-27 | Third parties connect NeuroEdge to new products in a few commands without modifying core: standalone core (`neuroedge.guard`), Extension SDK with six extension point kinds and conformance test suite, `proxy mcp`/`proxy http`, remote actuators, community index; open target list (RFC-0002) (Q-67) | **11 / 20** | 🟡 Q-67, design, corpus licensing complete; RFC-0002, RFC-0016 → RFC-0018 signed (Q-68); `neuroedge.guard` (TSK-I2c-07), `proxy mcp` + `guard init --mcp` (TSK-I2c-14), `proxy http` (TSK-I2c-15), remote actuators + Home Assistant plugin (TSK-I2c-16), partner trial documentation package (TSK-I2c-19) and half (a) of RFC-0017 complete; partner trial proceeds from here (Q-70); target list opening and two paused tasks dropped per Q-77 (§6) | I2b | tag `v0.2.3` (internal) · wheel for one partner team — private trial, not waiting for boards (Q-70) |
|  | **I2d — Missions and operator agents** | 2026-11-11 | Assign missions to devices via chat: mission contracts compile down to gate and envelope, conflicting requests rejected before approval; operator agent runs 24/7 on home machine (trusted runtime + untrusted LLM worker, BYOK), deterministic detectors before LLM, LLM cost ceiling; NeuroEdge brain (PicoClaw-style worker, Q-76) communicates with runtime via MCP; reports and requests approval via Telegram using approval records; data egress only to declared destinations; segmented traces; conditional safety (symmetric safe_state); G1, G2 simulation; MCP tool set (TSK-I2d-23, Q-88) | **7 / 36** | 🟡 Open — the Q-83 brain tasks moved first: TSK-I2d-24, I2d-26, I2d-27 done, I2d-22, I2d-25 in progress; fish tank demos on simulation and emulation done (TSK-I2d-28); the mission core (TSK-I2d-01 → I2d-21) has not started; RFC-0019 approved (Q-89, TSK-I2d-11/12 unblocked); five planned RFCs and the RFC for `TODOS.md` #58 await the tech lead's signature | I2c (completed portion: `neuroedge.guard`, half (a) of RFC-0017) | tag `v0.2.4` (internal) |
|  | **I2e — Minimal NeuroEdge Blueprint** | 2026-11-25 | Maker packages working device into NeuroEdge Blueprint (`blueprint pack`); others install with single command from URL + package-wide digest (`blueprint install`), runs on simulation; minimal Hub is static index; fish tank kit with affiliate BOM; multi-chip project scaffolding (Q-75); community channels; measure 8-week demand gate (Q-72) | **0 / 15** | ⏳ Not started | I2d | tag `v0.2.5` (internal) · direct hand-off wheel for external testers, no index (like Q-70); PyPI remains at I6 (Q-39) |
|  | **I2f — NeuroEdge Cloud and ESP32 home box** | after 8-week gate (branch) | Conditional (Q-74 step 2): home watch agent needs only chat — NeuroEdge brain operates on NeuroEdge Cloud, isolated single instance per user (Q-76) coordinating multiple devices, multiple homes, multiple users; gate, reflexes, approval checks always reside on home box (Pi, Home Assistant add-on, or ESP32-S3 for single task); standalone ESP32-S3 serves as both brain and gate, with risk labels (Q-79) | **3 / 17** | ⏸ Waiting for demand gate outcome 2026-12-06 (Q-74); exceptions Q-79, Q-83: TSK-I2f-10, I2f-14, I2f-16 complete (I2f-14, I2f-16 on QEMU); I2f-12, I2f-15 host and QEMU parts done; I2f-11, I2f-13, I2f-17 and the board parts await a DevKitC | I2e | optional service + ESP32 box firmware |
|  | **I3 — Gate on real Box-3** | after I2e | Gate runs on chip, controls real pins; user loads agent independently; `verify` three tier-1 targets for verdict domain | **6 / 16** | 🟡 Boardless portion complete (including firmware generated for agent on QEMU, LVGL interface with golden images); awaiting boards | I1 | tag `v0.3.0` + firmware (internal) |
|  | **I3a — Extended primitives on `esp32s3`** | after I2e | Four packages on chip: Box-3 and M5Stack CoreS3 with camera (Q-53, Q-61); minimal Pi ↔ ESP32 link with heartbeat, commodity ESP32-S3 board, and Arduino library (Q-75) | **0 / 11** | ⏳ Not started | I2a, I3 | tag `v0.3.1` + firmware (internal) |
| **Public** | **I6 — Public launch** | after I2e | Public repo, `pip install neuroedge` from PyPI, schemas at public URL, video demo of four packages and Blueprint on `sim`, `linux`, and `esp32s3`; network MCP with authentication, frozen integrator contract, public Python surface (Q-58, Q-63) | **7 / 11** | 🟡 Secret scanning, SBOM, public Python API, network MCP with authentication, integrator contracts in `schemas/` (RFC-0015) complete; RFC-0014 approved (Q-65); awaiting I3a | I2b, I2c, I3a | PyPI `v0.6.0` — first external release |
| **v1.0 = MVP** | **I7 — v1.0** | after I2e | MVP launch (Q-52): signed A/B OTA, device security, 24-hour on-chip stability; meets PRD §11.1 criteria | **4 / 12** | 🟡 Action pinning, attestation complete; signed A/B OTA + rollback complete on QEMU; awaiting I6 | I6 | `v1.0.0` |
| **Beta** | **I8 — Developer Beta** | after I2e | 50–100 external developers on `1.0.x` line; measure B1–B5, select branch | **0 / 1** | ⏳ Not started | I7 | `1.0.x` (patches only) |

**Forecast Assumptions (Q-39, Q-52, Q-72):** I2d only requires the completed portion of I2c (`neuroedge.guard`, half (a) of RFC-0017), so its forecast is earlier than I2c. I2d and I2e precede the 8-week demand gate measurement (date 2026-12-06, B6–B8, PRD §11.2; branching by outcome: §5.6). I3 → I8 are marked "sau I2e", with dates reset in the same PR containing the gate outcome (R5). Voice, Lab, and all post-Beta increments have been dropped per Q-77 (§6). Simulation first, physical hardware purchased later. One engineer + AI agent (Q-60, §1.1). If the MVP slips, dates shift, scope is not cut (Q-52).

---

### 0.3 Active Session Handoff Card

```text
GOAL: Fish tank Blueprint traversing all three loops on simulator (Q-72) before 8-week gate (B6–B8).
RECENTLY DONE: Q-84 complete short of the deferred canvas (TSK-I2d-32 pin map done); Q-85, Q-86 (Blueprint SRS), Q-87 (missions SRS) approved; phone app draft in docs/app-di-dong/ (no Q-N); documents synced to Q-77, Q-88 moves Lab-only tasks out of I2d (§6).
IN PROGRESS: nothing open. Waiting: a DevKitC N16R8 board for TC-COM-07-2, TC-NF-01-1, TC-BP-01-1 (TSK-I2f-13, I2f-15, I2f-17). NEXT: the I2d core (missions, TSK-I2d-01 → I2d-21) — most of its tasks have not started; the fish tank can already be shown on sim, linux and QEMU (demo/i2b-be-ca-gia-lap/, TSK-I2d-28) and its forecast is 2026-11-11 (§0.2). VPS, tunnel, demo video: TODOS #69.
NOTE: Hardware commands via c.do() and gate. Untrusted LLM worker. Fail-closed.
```

### 0.4 Handoff Protocol

When completing a task: follow [`CONTRIBUTING.md` §8](../CONTRIBUTING.md#8-completing-a-task--updating-documentation-progress-changelog).

---

### 0.5 Phase (Q-52, Q-77)

Phases group increments by user capability; dates and dependencies reside solely in §0.2.

| Phase | User Capability | Increment | Ends With |
|:---|:---|:---|:---|
| **P0 — Groundwork** | — | *(no increments)* | Product documentation in `roadmap/` |
| **MVP = v1.0** | Pick a kit, run on `sim` < 10 minutes, build physical devices on `linux` or `esp32s3`; all 4 extension packages; 24/7 mission via chat and Blueprints (Q-72, Q-77) | I0 → I7 (including I2a → I2e, I3a) | `v1.0.0` — meets PRD §11.1 criteria; slip shifts dates, no cuts (Q-52) |
| **Beta and cloud** | External developers and makers use it for real; NeuroEdge Cloud subscription if metrics warrant (Q-74, Q-76) | I2f (conditional), I8 | `1.0.x` (§5.6) |

#### User-facing release milestones

Phases are how the team plans; **release milestones** are how users perceive the product (eight milestones after Q-77). Each milestone is a user capability, concluding when all its increments are done. This table records no dates: a milestone's date is the latest forecast date among its increments in §0.2. The progress blocks of the architecture page (`docs/business/kien-truc-tong-the.html`), poster E-09, and architecture chapter 15 §1 read from this table. Each increment belongs to exactly one milestone.

| # | Milestone | What the user can do | Why it matters | Increment | Who can use it |
|:---:|:---|:---|:---|:---|:---|
| 1 | **Try on laptop** | Install a single package, run a gated agent on the simulator in under 10 minutes; no hardware, account, or API key needed | Product entry point: anyone can try without spending money on hardware | I0, I1 | Team and internal testers |
| 2 | **Physical device on Raspberry Pi** | Wire a kit (light, door, fan, sensors, camera, motor) to Pi 5; same agent, same gate as on laptop; connect third-party products (Muse, Home Assistant, existing MCP servers) via plugins and proxies | First time an AI command touches physical hardware while passing through contracts — even commands from other ecosystems | I2, I2a, I2b, I2c | Team, internal testers, and one partner team (proxy portion, `neuroedge.guard`, `sim` — Q-70) |
| 3 | **Gate running on a $5 chip** | Flash agent to ESP32-S3 (Box-3, M5Stack CoreS3); gate decides directly on chip, blocking correctly even when offline (the all-in-one image with the brain inside is Profile B of Q-83, built in I2f) | Safety without cloud dependence; same contract from laptop to microcontroller | I3, I3a | Team and internal testers |
| 4 | **Assemble and run via conversation, share Blueprints** | Describe device in words to current AI (Claude Code, Claude Desktop); AI writes actions, gates, envelopes, and mission contracts via NeuroEdge MCP tools; NeuroEdge grades, human approves before locking; operator agent monitors device all day, proactively reporting and requesting approval via Telegram; package device into NeuroEdge Blueprint for others to install with a single command | Shrinks building a contracted device from a day to minutes; contracts and traces serve as proof for strangers to install and makers to sell (Q-72) — early milestone, measured by 8-week demand gate | I2d, I2e | Team, internal testers, and external testers trying Blueprints on simulation via direct hand-off wheel (Q-72) |
| 5 | **Public launch** | Anyone can `pip install neuroedge`; invoke devices from Claude, Home Assistant, or agent frameworks via authenticated MCP | **First time external users can use it** | I6 | Everyone (free non-commercial) |
| 6 | **v1.0 — into production** | Signed firmware updates, lock device, 24-hour stable run; meets PRD §11.1 acceptance criteria | Reliable enough for product teams to ship in commercial devices | I7 | Everyone; enterprises via commercial license |
| 7 | **Developer Beta** | 50–100 external developers use it for real on the `1.0.x` line | Real metrics determine commercial direction (branch point §5.6) | I8 | Invited developers |
| 8 | **One chat box for multiple devices, multiple homes** | Chat with a single brain monitoring the entire mesh: multiple ESP32s, multiple Pis, multiple homes, multiple roles; self-hosted or NeuroEdge Cloud (Q-74, Q-76), or one chip doing both (Profile B, Q-83) | Cloud subscription provides recurring revenue (conditional, after 8-week gate); cloud coordinates without supreme authority — each node enforces its own rules | I2f | Families, homestay owners |


---

## 1. Resource assumptions

### 1.1 Roles

| Role | Primary Responsibility | Present From |
|:---|:---|:---:|
| **V1 — Platform** | HAL, Action Contract Engine, schemas, Action CI, host | I0 |
| **V2 — Embedded** | Port to `esp32s3`, on-chip HAL, memory optimization, RP2350 node | I0 |
| **V3 — DX** | `sim` interface, CLI, scaffolding, documentation, sample templates, releases | I0 |
| **V4 — Infrastructure** | Fleet OS, Registry, metering, provider layer | before I9 |
| **V5 — Vision** | Vision HAL, models, NPU | before I2a |
| **V7 — Lab** | Sensor checks after assembly (`lab doctor`, TSK-I2d-17) and the fish tank model (TSK-I2d-15, with V1); Lab itself removed (Q-77, Q-88) | before I2d |
| **V6 — Embedded 2** | On-chip audio, OTA, and device security (with V2) | when needed |

**Operating model (Q-60): one engineer + AI agent.** The table above represents work lanes. The AI agent executes the host lane. Hardware tasks, external personnel, and signatures require a human in the loop.

### 1.2 Why V2 must be present from the start

MCU memory risk (R-1) is mitigated by cloud-first (PRD §13.2). V2 builds boardless firmware (C walker, token accounting, UART on QEMU) and runs memory spikes immediately upon board arrival (TSK-S1-10) to allow timely adjustments to I5 if needed (Q-44).

### 1.3 Sensitivity to team size

One engineer + AI agent (Q-60): the host lane maintains §0.2 dates; the chip lane proceeds serially by a single person, verifying upon board arrival, shifting dates in the same PR that introduces evidence (R5).

---

## 2. Critical path, dependencies and anti-drift rules

### 2.1 Dependency graph

Read `A ◄ B, C` as: A depends on B and C (source: §0.2 Dependencies column).
- MVP host: `I1 ◄ I0`, `I2 ◄ I1`, `I2a ◄ I2`, `I2b ◄ I2a`, `I2c ◄ I2b`.
- Q-72: `I2d ◄ I2c` (completed portion), `I2e ◄ I2d`, 8-week demand gate `◄ I2e` (on G1, G2).
- Q-74: `I2f ◄ I2e` and demand gate outcome (conditional).
- MVP chip: `[boards] ► TSK-S1-10 ► I3 ◄ I1`, `I3a ◄ I2a, I3`.
- Launch: `I6 ◄ I2b, I2c, I3a`, `I7 ◄ I6`, `I8 ◄ I7`.
- Critical path: `I2c` (portion) ► `I2d` ► `I2e` ► 8-week gate (Q-72).

### 2.2 Critical path

| # | Link | Rationale |
|:---:|:---|:---|
| **G** | **Gate critical path (Q-72): I2c ► I2d ► I2e ► 8-week gate** | Precedes all links; runs on G1, G2 emulators |
| **0** | Six I2a RFCs approved (PR #75 → #80) | Prerequisite for extended primitives code (§2.3) |
| **1** | Box-3 boards arrive → TSK-S1-10 | Finalize memory budget for 4 packages on chip |
| **2** | I3 → I3a: HAL, gate, and extended primitives on chip | Prove target equivalence on physical hardware |
| **3** | I6: public release | Install from PyPI to measure A1, A9 prior to v1.0 |
| **4** | I7: OTA, 24h stability, PRD §11.1 criteria | Complete v1.0 acceptance conditions |

### 2.3 Schema freeze rules

Since the I0 schema freeze (2026-09-27), all changes to gate or trace schemas require: an RFC stating rationale and backward compatibility; approval by the tech lead; accompanied by a migration script for all existing traces.

### 2.4 Anti-drift rules

| # | Rule | Verified By |
|:---:|:---|:---:|
| **R1** | Task status, exit criteria, forecasts, dependencies, release tags, and cut ladders reside only in this document | test |
| **R2** | Increment IDs are unique and strictly ascending; additions only, no renumbering; intermediate insertions use suffixes (`I3a`) | test |
| **R3** | The "Dependencies" column in §0.2 points only to lower-numbered increments | test |
| **R4** | Each increment has exactly one forecast date, solely in §0.2; conditional increments state "sau Ix" | test |
| **R5** | Forecasts change only within the same PR containing evidence, cascading immediately to dependent increments | review |
| **R6** | Do not use numbered week or month labels for scheduling; durations count from when an increment opens | test |
| **R7** | Decisions are strictly coded `Q-N` (PRD §15); out-of-scope resides solely in PRD §14; documents cite codes, never duplicate content | review |
| **R8** | Each TSK code has exactly one task row in this document; every cited code exists here | test |
| **R9** | Each status cell contains exactly one glyph from ✅ 🟡 ⏳ ⏸ 🔴 | test |
| **R10** | "Progress" in §0.2 equals the count of ✅ tasks over total tasks in that increment's table | test |
| **R11** | Cross-references use codes or stable sections, never line numbers (`file.md:NNN`) | test |
| **R12** | Beta freeze applies to the `1.0.x` line during I8: only blockers to the 10-minute journey and safety bugs | review |

**Task code families:** `TSK-S1-*`..`S6-*` (original sprints); `TSK-K2-*`, `K3-*` (Blocks 2, 3); `TSK-N*-*` (Lab); `TSK-V*-*`, `P*-*` (Phase 2); `TSK-W*-*` (robotics); `TSK-I*-*` (new work by increment).

---

## 3. Open source reuse strategy

Principle: build what differentiates, borrow what is commoditized.

### 3.1 Inviolable boundaries

The boundary between core assets (100% in-house) and commodities (maximum reuse) is defined in §3.

### 3.2 Decision test

Does depending on it force a violation of P-1, P-2 ([PRD §1.5](neuroedge-prd.md#15-five-invariant-design-principles)), or the three architectural decisions (`sim` is a first-class target, gates are versioned artifacts, traces are first-class citizens)? Yes → interoperate or reference only. No → reuse.

### 3.3 License discipline

License rules: §3, Appendix H. LiteLLM (MIT) is used as an SDK via extra `neuroedge[cloud]` (Q-10, Q-11). Hawkbit (EPL-2.0) approved, EMQX not used (Q-11). NeuroEdge license: [`LICENSING.md`](../LICENSING.md) (Q-45).

### 3.4 Integration matrix by block

Reuse: Typer/Rich/Pytest (CLI & CI), Pydantic v2 (schemas), XiaoZhi (Box-3 driver), Pipecat/microWakeWord (audio), ESP-IDF (OTA), LVGL (display), LiteLLM (provider), Hawkbit (canary OTA), Mosquitto (telemetry), ORAS/Harbor (registry), OpenMeter (metering). Home Assistant Core API for room control (Block 4).

### 3.5 Five directly ported projects

1. **XiaoZhi ESP32** (`targets/esp32s3/drivers/`): I2S codec, Box-3 pins, ST7789 LCD.
2. **Pipecat** (`neuroedge/perception/pipeline/`): Audio frame processor, barge-in actuator command revocation.
3. **Wokwi Elements** (planned, not yet used; TSK-S2-09 uses in-house web UI).
4. **LiteLLM** (`neuroedge/models/providers/`): Provider I/O normalization, in-process failover (Q-10, Q-11).
5. **OpenMeter**: Event aggregation engine, reconciling agent and gate invocations for Block 3.

**Additions per Q-76 (MIT, attribution per §3.9):** PicoClaw — base of the NeuroEdge brain, now hard-forked as NeuroClaw (Q-78, TSK-I2d-22); zclaw and MimiClaw — reference or ported C components for the ESP32 box (TSK-I2f-03) and ESP32-S3 standalone (Q-79, TSK-I2f-10 → I2f-12): on-chip Telegram client, Wi-Fi onboarding, secrets in NVS, boot guard, serial console; the last three have been ported (TSK-I2f-10). Do not adopt their agent loop as the hardware authority.

### 3.6 Three interoperability-only projects without dependencies

ESP-Claw (interoperates via MCP), LiveKit Agents and TEN Framework (design references only) — §3. Do not fork all of XiaoZhi.

### 3.7 Real impact on the critical path

OSS leverage shortens porting time for the `esp32s3` HAL and MCU voice runtime, while reducing risk R-1 from High to Medium.

### 3.8 Preserving target equivalence across two languages

Q-8: C/C++ on ESP-IDF for firmware, Python for `sim` and `linux`. Preserved via FSM specification ([`voice_fsm.md`](../docs/spec/voice_fsm.md)), compliance test vectors (`fixtures/compliance/voice/`), canonical traces (`fixtures/traces/`), and `neuroedge verify` (NE4002 upon regression).

### 3.9 Attribution obligations

Comply with license matrix, `NOTICE` file, in-code attribution, public documentation, and pinned versions (§3).

### 3.10 Risks of going backward

Avoid: forking XiaoZhi entirely (loss of HAL, loss of safety); building on ESP-Claw (`linux` becomes second-class); porting without test vectors (verdict drift); embedding copyleft (Q-45 license conflict).

### 3.11 Maximum porting by task (Q-76)

For each unstarted task, borrow first, write in-house later. The **Written in-house** column is what remains after borrowing, which also forms the differentiator. Licenses verified on GitHub as of 2026-10-12. The `licence-obligations` job blocks any package name containing "GPL" (including LGPL, AGPL) in core dependencies, so copyleft libraries are only permitted in optional extras such as `gpiod` or omitted entirely.

| Task | Borrowed | License | Method | Written in-house |
|:---|:---|:---|:---|:---|
| TSK-I2d-22 brain | PicoClaw v0.3.1 → NeuroClaw (Q-78, Q-80) | MIT | Hard fork: mTLS, prompt instructions on `BLOCK`, risk labels; preserve all PicoClaw capabilities and releases | Releases, manually tracking PicoClaw security patches |
| TSK-I2d-23 MCP tool | `mcp` Python SDK (already used) | MIT | Dependency | Semantics for `propose_mission`, `mission_status`, `explain_block` |
| TSK-I2d-12 runtime Telegram adapter | aiogram | MIT | Dependency (extra) | Approval records, pairing (`TODOS.md` #62). Do **not** use python-telegram-bot (LGPL-3.0, blocked by license job) |
| TSK-I2d-09 scheduler | APScheduler, croniter | MIT | Dependency | Deterministic detectors, `llm_budget` |
| TSK-I2d-24 worker isolation | systemd (`DynamicUser`, `DeviceAllow`, `PrivateDevices`) | — (OS) | Sample unit file | Tests proving worker never touches hardware |
| TSK-I2d-11 signed approval records | `cryptography` (Ed25519) | Apache-2.0 / BSD | Dependency | Record format, nonce, expiration (RFC) |
| Person detector (home watch mission) | Frigate (events via MQTT or Home Assistant); YOLOX model | MIT; Apache-2.0 | Interoperate, do not embed | Convert events to facts for gate. Do **not** use Ultralytics (AGPL-3.0) |
| TSK-I2e-12 Home Assistant add-on | `home-assistant/addons-example` | Apache-2.0 | Template scaffold | Package runtime + brain |
| TSK-I2e-13 SD card image, Wi-Fi, QR | pi-gen; balena wifi-connect | BSD-3-Clause; Apache-2.0 | Image builder tools; captive portal | QR pairing step |
| TSK-I2e-14 multi-chip project scaffolding | copier | MIT | Scaffolding generator tool | `host+mcu` template content |
| TSK-I2e-01 → I2e-03 Blueprint | ORAS (already in §3.4) | Apache-2.0 | OCI package for `blueprint pack`/`install` | `blueprint.v1`, package-wide digest |
| TSK-I2f-02 channel gateway and relay | NATS (leaf node, per-user JWT accounts) | Apache-2.0 | Infrastructure | Routing chat ↔ instance ↔ box, token cap |
| TSK-I2f-07 isolated instances | Firecracker or gVisor | Apache-2.0 | Infrastructure | Sleep/wake, per-user encrypted memory |
| TSK-I2f-08 passkey approval | py_webauthn; SimpleWebAuthn; Telegram Mini Apps SDK | BSD-3-Clause; MIT; MIT | Dependency | In-box signature verification |
| TSK-I2f-03 ESP32 box; TSK-I2f-10 → I2f-13 standalone chip (Q-79) | zclaw, MimiClaw (on-chip Telegram client, NVS, boot guard, serial console); ESP-IDF `wifi_provisioning` | MIT; Apache-2.0 | Port C code — boot guard, encrypted NVS, serial console ported (TSK-I2f-10, `NOTICE` items 6, 7) | Existing walker and signed rules; tool call queue into `ne_gate`; Telegram client with owner ID (MimiClaw does not filter sender) |
| TSK-I3a-06, I3a-07 Pi ↔ ESP32 link | nanopb (framing) + COBS and CRC | Zlib | C dependency | Heartbeat, `safe_state` (minimal node RFC, TSK-I3a-06). Zenoh-pico removed with I14 (TSK-W3-01, §6) |
| TSK-I3a-08 generic boards | Espressif `esp-bsp` | check per component | Board support | `boards/` profile |
| TSK-I3a-04 on-chip vision | esp-dl; esp-who | MIT; "ESPRESSIF MIT" (Espressif chips only) | Dependency | `vision.in` per RFC-0012 |
| CI firmware | zclaw stack guard (ported, TSK-I2f-10: all in-house functions instead of three pre-selected) | MIT | Concept, rewritten in Python | Runtime stack threshold on QEMU |

**Not borrowed:** agent loops of "Claw" projects as the hardware authority; anything replacing gates, token accounting, traces (§3.1). Each code borrowing (not just dependencies) adds an attribution entry per §3.9.

---

## 4. Increments to v1.0 = MVP (I0–I7)

From Q-52, MVP is the full v1.0: suffixed increments (I2a, I2b, I3a, I4a, I5a) sit beside the increment they extend.

Each increment has: a card (goal, entry conditions beyond dependent increments, measurement signal, roles), a task table, and exit criteria. An increment is released only upon satisfying all its exit criteria, accompanied by a demo in `demo/` (§11.1, Q-49).

### 4.1 I0 — Contract core on `sim`

| | |
|:---|:---|
| **Goal** | Contract core: typed and versioned gates, `sim` as a first-class target, Action CI on host, MCP, and System 2 |
| **Entry conditions** | — |
| **Measurement signal** | Core CI (§0.1) |
| **Roles** | V1, V2, V3 |

| Task code | Work item | PRD requirement | Owner | Status | Deliverable (artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-S1-01** | Specification of 5 HAL primitives and cross-check | FR-HAL-01, FR-HAL-02, FR-HAL-03 | V1 | ✅ 2026-09-24 | [`schemas/board.v1.json`](../schemas/board.v1.json) |
| **TSK-S1-02** | Gate schema v1 and on_block behavior | FR-GATE-02, FR-GATE-03, FR-GATE-04 | V1 | ✅ 2026-09-24 | [`schemas/gate.v1.json`](../schemas/gate.v1.json) |
| **TSK-S1-03** | `extends` inheritance rules | FR-GATE-06, FR-GATE-07, FR-GATE-08 | V1 | ✅ 2026-09-24 | [`gate_resolver.py`](../python/neuroedge/engine/gate_resolver.py) |
| **TSK-S1-04** | Trace schema v1 | FR-TRC-01, FR-TRC-02, FR-TRC-03 | V1 | ✅ 2026-09-24 | [`schemas/trace.v1.json`](../schemas/trace.v1.json) |
| **TSK-S1-05** | License matrix and NOTICE file | — | V2 | ✅ 2026-09-24 | [`NOTICE`](../NOTICE) |
| **TSK-S1-06** | Monorepo scaffolding: schemas, python, targets, fixtures | — | V1 | ✅ 2026-09-24 | [`CONTRIBUTING.md`](../CONTRIBUTING.md) |
| **TSK-S1-07** | Three official schema files in schemas | FR-TRC-01, FR-GATE-02, FR-HAL-02 | V1 | ✅ 2026-09-24 | [`schemas/`](../schemas/) |
| **TSK-S1-08** | Three canonical trace files | FR-CI-01, FR-CI-02 | V1 | ✅ 2026-09-24 | [`fixtures/traces/`](../fixtures/traces/) |
| **TSK-S1-09** | Initial Python SDK, CLI, and Action CI framework | FR-CLI-01, FR-CI-01 | V1 | ✅ 2026-09-24 | [`python/neuroedge/`](../python/neuroedge/) |
| **TSK-S1-11** | HAL design review under MCU constraints | — | V2 | ✅ 2026-09-24 | [`docs/spec/hal_mcu_review.md`](../docs/spec/hal_mcu_review.md) |
| **TSK-S1-12** | Two CI workflows: ci-sim-linux and nightly-hardware | FR-CI-05, FR-CI-06 | V1 | ✅ 2026-09-24 | [`.github/workflows/`](../.github/workflows/) |
| **TSK-S1-13** | Contributing guidelines and schema-change RFC template | — | V1 | ✅ 2026-09-24 | [`CONTRIBUTING.md`](../CONTRIBUTING.md) |
| **TSK-S2-01** | HAL implementation for target sim | FR-TGT-01, FR-HAL-01 | V2 | ✅ 2026-09-23 | `python/neuroedge/hal/sim.py` |
| **TSK-S2-02** | Capability cross-check at build time | FR-HAL-04, FR-HAL-05, FR-DX-04 | V1 | ✅ 2026-09-23 | `python/neuroedge/engine/compiler.py` |
| **TSK-S2-03** | Gate Engine evaluate, allow_when, on_block | FR-GATE-03, FR-GATE-04, FR-GATE-09 | V1 | ✅ 2026-09-23 | `python/neuroedge/engine/gate.py` |
| **TSK-S2-04** | Fail-closed and degraded circuit breaker | FR-ACE-03, NFR-REL-02 | V1 | ✅ 2026-09-23 | `python/neuroedge/engine/circuit_breaker.py` |
| **TSK-S2-05** | `@action` decorator, single-use verdict token | FR-ACE-02, FR-ACE-04, FR-ACE-05, FR-ACE-07 | V1 | ✅ 2026-09-23 | `python/neuroedge/actions/token.py` |
| **TSK-S2-08** | SystemOne/SystemTwo interfaces and local command fallback | FR-MDL-01, FR-MDL-02, FR-MDL-03, FR-ACE-03 | V1 | ✅ 2026-09-23 | `python/neuroedge/models/system.py` |
| **TSK-S2-09** | Web sim UI: virtual sensors, actuator states | FR-TGT-06 | V3 | ✅ 2026-09-23 | [`sim/ui.py`](../python/neuroedge/sim/ui.py) |
| **TSK-S2-11** | LiteLLM provider abstraction and System 2 | FR-MDL-06, FR-MDL-07, FR-MDL-08, FR-MDL-11, FR-GW-01, FR-GW-03 | V1 | ✅ 2026-09-24 | `python/neuroedge/models/providers/` |
| **TSK-S2-12** | Host decision tree compiler | FR-GATE-03, FR-ACE-01, FR-TGT-04 | V1 | ✅ 2026-09-23 | `python/neuroedge/engine/decision_tree.py` |
| **TSK-S2-13** | Inherited budget and on_block (RFC-0004) | FR-GATE-06, FR-GATE-07, FR-GATE-09 | V1 | ✅ 2026-09-23 | `python/neuroedge/engine/gate_resolver.py` |
| **TSK-S3-01** | Record session to valid JSON file | FR-CI-01 | V1 | ✅ 2026-09-23 | [`testing/recorder.py`](../python/neuroedge/testing/recorder.py) |
| **TSK-S3-02** | Replay on sim and linux | FR-CI-02 | V1 | ✅ 2026-09-23 | [`testing/player.py`](../python/neuroedge/testing/player.py) |
| **TSK-S3-03** | Verdict and pin assertion library | FR-CI-03 | V1 | ✅ 2026-09-23 | [`testing/assertions.py`](../python/neuroedge/testing/assertions.py) |
| **TSK-S3-04** | Golden Reference verdict sequence matcher | FR-CI-04 | V1 | ✅ 2026-09-23 | [`testing/golden.py`](../python/neuroedge/testing/golden.py) |
| **TSK-S3-05** | Target linux HAL via gpiod and gpio-sim | FR-TGT-02 | V2 | ✅ 2026-09-23 | [`hal/linux.py`](../python/neuroedge/hal/linux.py) |
| **TSK-S3-06** | CLI shell and exit code contract | FR-CLI-01→04, FR-CLI-06, FR-TRC-08 | V3 | ✅ 2026-09-23 | `python/neuroedge/cli/` |
| **TSK-S3-07** | Scaffold `neuroedge new` pure Python | FR-DX-01 | V3 | ✅ 2026-09-23 | [`python/neuroedge/templates/`](../python/neuroedge/templates/) |
| **TSK-S3-12** | CI pipeline running sim and linux | FR-CI-05 | V1 | ✅ 2026-09-23 | [`.github/workflows/ci-sim-linux.yml`](../.github/workflows/ci-sim-linux.yml) |
| **TSK-S3-16** | `digests.lock` CI gate locking gate digests | FR-GATE-01, FR-GOV-02, FR-CI-05 | V3 | ✅ 2026-09-24 | [`digests.lock`](../digests.lock) |
| **TSK-S3-17** | Asset packaging into wheel | FR-DX-02, FR-DX-04 | V3 | ✅ 2026-09-23 | [`python/hatch_build.py`](../python/hatch_build.py) |
| **TSK-S3-18** | `neuroedge gate explain` command | FR-GATE-01, FR-CLI-05 | V3 | ✅ 2026-09-23 | [`engine/gate_explain.py`](../python/neuroedge/engine/gate_explain.py) |
| **TSK-S3-19** | `verify` artifact counting, error on 0 | FR-CI-07, FR-CLI-06, FR-DX-04 | V3 | ✅ 2026-09-24 | `python/neuroedge/cli/main.py` |
| **TSK-S3-20** | Root README compliant with PyPI | FR-DX-02, FR-DX-05 | V3 | ✅ 2026-09-24 | [`README.md`](../README.md) |
| **TSK-S3-22** | `neuroedge trace view` static HTML | FR-CLI-04, FR-DX-04 | V3 | ✅ 2026-09-23 | [`viz/`](../python/neuroedge/viz/) |
| **TSK-S3-23** | `sensor.read` and `display` on sim | FR-TGT-01, FR-TGT-06, FR-CI-02 | V3 | ✅ 2026-09-23 | `python/neuroedge/hal/sim.py` |
| **TSK-S3-24** | Gated Tool Profile compliance corpus | FR-MDL-10, FR-ACE-09 | V1 | ✅ 2026-09-24 | `fixtures/tool_calls/` |
| **TSK-S3-25** | `arguments` block in gates (RFC-0005) | FR-ACE-08, FR-GATE-06 | V1 | ✅ 2026-09-24 | `python/neuroedge/engine/arguments.py` |
| **TSK-S3-26** | `ask` confirmation round on sim (RFC-0006) | FR-ACE-10 | V3 | ✅ 2026-09-24 | `python/neuroedge/actions/confirmation.py` |
| **TSK-S3-27** | `neuroedge mcp serve --ui` | FR-CLI-12, FR-DX-04 | V3 | ✅ 2026-09-24 | `python/neuroedge/mcp_server.py` |
| **TSK-S3-28** | System 2 as MCP host | FR-MDL-11, FR-MDL-12 | V1 | ✅ 2026-09-23 | `python/neuroedge/mcp_host.py` |

- [x] **Criterion 1:** JSON Schema of gate and trace has valid and invalid examples (`schemas/`).
- [x] **Criterion 2:** Three sample gates resolve correctly, including 2-level inheritance (`test_sample_gates.py`).
- [x] **Criterion 4:** Monorepo scaffold complete, `schemas/` valid draft 2020-12 (job `frozen-artifacts`).
- [x] **Criterion 5:** Three canonical traces resolve correctly (`fixtures/traces/`).
- [x] **Criterion 6:** Decision Q-11 decided, LiteLLM and licenses compliant.
- [x] **Criterion 2 (A2):** `verify --targets sim,linux` passes 100% (job `linux-hal`).
- [x] **Criterion 3 (A3):** No shortcut exists to activate GPIO bypassing gates (`test_actions.py`).
- [x] **Criterion 4 (A4):** 100% of degraded scenarios block actions (`test_fail_closed.py`).
- [x] **Criterion 5 (A5):** Gate inheritance test suite passes 100% (`test_gate_resolver.py`).
- [x] **Criterion 6 (A7):** 100% of recorded sessions pass `trace validate` (`test_recorder.py`).

### 4.2 I1 — Internal preview on `sim`

| | |
|:---|:---|
| **Goal** | An external developer, installing from an internal wheel, runs a gated agent in under 10 minutes without hardware (U1/J1 → M1; early A1 measurement) |
| **Entry conditions** | — |
| **Measurement signal** | Median TTFV across 3 external developers, measured on-site — not yet publicly released (Q-39) |
| **Roles** | V3 (lead), V1 |

| Task code | Work item | PRD requirement | Owner | Status | Deliverable (artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-S3-08** | Three runnable sample examples via scaffold and wheel-smoke | FR-DX-05, FR-DX-06 | V3 | ✅ 2026-09-25 | `fixtures/agents/` · `tests/test_factory_monitor.py` |
| **TSK-S3-15** | Three canonical traces as pristine golden references | FR-CI-04, FR-TRC-05 | V1 | ✅ 2026-09-25 | `fixtures/traces/` · `tests/test_trace_vectors.py` |
| **TSK-I1-01** | Hash user PII at source in traces | FR-TRC-06, FR-TRC-07, NFR-PRIV-03 | V1 | ✅ 2026-09-27 | `python/neuroedge/testing/recorder.py` |
| **TSK-I1-02** | On-site TTFV test suite (3 external developers) | FR-DX-01 | V3 | ⏳ Reactivated per Q-72 | `docs/reports/` |
| **TSK-I1-03** | Examples in `--help`, scaffold pre-generating `traces/` | FR-CLI-07, FR-TRC-09 | V3 | ✅ 2026-09-26 | `python/neuroedge/cli/examples.py` |
| **TSK-I1-04** | NeuroEdge Studio local web app | FR-TGT-06, FR-DX-06 | V3 | ⏸ Paused per Q-72 | `python/neuroedge/studio/` |

**Exit criteria I1:**

- [ ] **Criterion 1 (M1):** On-site TTFV across 3 external developers achieves median under 10 minutes.
- [x] **Criterion 2:** Third sample runs via `neuroedge new`, tested in `wheel-smoke`.
- [x] **Criterion 3:** Golden reference consists of three canonical traces in pristine state, no RFC needed.
- [x] **Criterion 4:** Traces default to hashing raw user text at the source.
- [ ] **Criterion 5:** Tag `v0.1.0` has internal GitHub Release; `wheel_smoke.sh` passes green on that wheel.

### 4.3 I2 — `linux` at parity with `sim`

| | |
|:---|:---|
| **Goal** | Same agent runs interactively on `linux` as on `sim`: REPL, `record`, `mcp serve` |
| **Entry conditions** | 1 RPi 5 for nightly (Appendix B) |
| **Measurement signal** | Interactive session on gpio-sim; nightly RPi 5 passes green |
| **Roles** | V3 (TSK-S5-10), V1 (TSK-S5-09, TSK-I2-01) |

| Task code | Work item | PRD requirement | Owner | Status | Deliverable (artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-S5-09** | `sensor.read` and `display` on `linux` via sysfs | FR-TGT-02, FR-HAL-01 | V1 | ✅ 2026-09-26 | `python/neuroedge/hal/linux.py` |
| **TSK-S5-10** | Interactive REPL session, `record`, `mcp serve` on `linux` | FR-CLI-02, FR-TGT-02 | V3 | ✅ 2026-09-25 | `python/neuroedge/hal/linux.py` |
| **TSK-I2-01** | Nightly `linux` on physical RPi 5 hardware | FR-CI-06, FR-TGT-02 | V1 | ⏳ Not started | `.github/workflows/nightly-hardware.yml` |
| **TSK-W0-04** | Nightly dependency drift automated issue filing (Q-32) | — | V3 | ✅ 2026-09-26 | `.github/workflows/nightly-hardware.yml` |

**Exit criteria I2:**

- [x] **Criterion 1:** `run`, `record`, `mcp serve --target linux` run on gpio-sim, identical exit code contract.
- [ ] **Criterion 2:** `sensor.read` and `display` on `linux` covered by tests; board profile declares only working HAL primitives.
- [x] **Criterion 3:** `neuroedge verify --targets sim,linux` passes 100%.
- [ ] **Criterion 4:** Nightly on RPi 5 runs `tests_linux/` and `verify --targets linux` on physical hardware.

### 4.3.1 I2a — Extended primitives on `sim` and `linux`

| | |
|:---|:---|
| **Goal** | All four extended primitive packages running on `sim` and `linux` (Q-52, Q-53) |
| **Entry conditions** | — · RFC open immediately, code awaits RFC approval (§2.3) |
| **Measurement signal** | Exit criteria below |
| **Roles** | V1 (lead), V5 (vision), V2 (RFC-motion), tech lead |
| **Design** | `docs/architecture/vi/15-target-architecture.md` §4.4 · `docs/architecture/vi/15-target-architecture.md` §4.3 · `docs/spec/lab_mcp.md` §7 · RFC-0007, RFC-0009 → RFC-0013 |

| Task code | Work item | PRD requirement | Owner | Status | Deliverable (artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-I2a-01** | Re-estimate MVP scope (Q-52) | — | team lead + tech lead | ✅ 2026-09-30 | `docs/reports/uoc-luong-mvp-2026-09-30.md` |
| **TSK-N0-02** | Amend FR-HAL-01: optional extended primitives per board | FR-HAL-01, FR-CLI-12 | V2 | ✅ 2026-10-03 | `neuroedge-prd.md` |
| **TSK-N0-03** | RFC-0007: `digital.in`, read-only I2C, `analog.in` | FR-HAL-01 | V2 | ✅ 2026-10-01 | `docs/rfc/0007-digital-in-i2c-analog-in-phong-bi.md` |
| **TSK-I2a-07** | RFC-0013: optional extended primitives, multiple reference boards | FR-HAL-01, FR-TGT-08 | V1 + tech lead | 🟡 RFC approved, host portion complete; esp32s3 cell remaining | `docs/rfc/0013-nguyen-thuy-tuy-chon-va-nhieu-bo-tham-chieu.md` · `hal/board.py` |
| **TSK-I2a-06** | `sim-rpi5` profile faithfully mirroring `linux-rpi5` | FR-TGT-01, FR-TGT-06 | V1 | ✅ 2026-10-04 | `boards/sim-rpi5.toml` |
| **TSK-W1-02** | `numeric` criteria for `sensor.read`, `NETR` v2, C walker | FR-GATE-03, FR-HAL-01 | V1 | ✅ 2026-10-03 | `python/neuroedge/engine/constraints.py` |
| **TSK-I2a-02** | `digital.in` on `sim` and `linux` via gpiod/gpio-sim | FR-HAL-01 | V1 | ✅ 2026-10-04 | `python/neuroedge/hal/linux.py` |
| **TSK-I2a-03** | Read-only I2C bus for agents on `sim` and `linux` | FR-HAL-01 | V1 | ✅ 2026-10-04 | `python/neuroedge/hal/i2c_bus.py` |
| **TSK-N3-03** | ADC spike on `ubuntu-latest` via hwmon `i2c-stub` | — | — | ✅ 2026-10-03 | `scripts/setup_i2c_stub.sh` |
| **TSK-I2a-04** | `analog.in` (ADC) on `sim` and `linux` per RFC-0009 | FR-HAL-01 | V1 | ✅ 2026-10-04 | `python/neuroedge/hal/linux.py` |
| **TSK-W1-01** | PWM and state feedback in `digital.out` (RFC-0010) | FR-HAL-01 | V1 + V2 | 🟡 Complete on sim and dummy linux; physical PWM channels, physical boards, C HAL remaining | `docs/rfc/0010-pwm-trong-digital-out.md` · `hal/pwm.py` |
| **TSK-I2a-08** | Kernel spike with sufficient modules for `linux-hal` job (Q-69) | FR-CI-06, FR-HAL-01 | V1 | ⏳ Not started | `docs/reports/` |
| **TSK-V1b-07** | RFC-0012: `vision.in` primitive | FR-HAL-01, FR-HAL-04 | V1 | ✅ 2026-10-01 | `docs/rfc/0012-nguyen-thuy-vision-in.md` |
| **TSK-V1b-01** | Implement `vision.in` V4L2 for `linux` | FR-HAL-01 | V5 | ✅ 2026-10-04 | `python/neuroedge/hal/vision.py` |
| **TSK-V1b-02** | Virtual camera in `sim` replaying image sequence | FR-TGT-01, FR-TGT-06 | V5 | ✅ 2026-10-04 | `python/neuroedge/sim/vision/` |
| **TSK-V1b-03** | Vision model abstraction swappable via configuration | FR-MDL-04, FR-MDL-07 | V5 | ✅ 2026-10-04 | `python/neuroedge/perception/vision/` |
| **TSK-V1b-04** | Action CI for frames: record, replay, assert verdicts | FR-CI-01→04 | V1 | ✅ 2026-10-04 | `python/neuroedge/testing/vision.py` |
| **TSK-V1b-05** | Discrete NPU integration (Hailo-8, Coral) behind abstraction | FR-MDL-04 | V5 | ⏳ Not started | `python/neuroedge/perception/vision/accel/` |
| **TSK-V1b-06** | Three sample gates with vision facts, numeric threshold locked in gate | FR-GATE-03 | V1 + V5 | ✅ 2026-10-04 | `gates/vision/` |
| **TSK-V1b-08** | Visual evidence in traces, `vision_ref` lint | FR-CI-02, NFR-PRIV-01, NFR-PRIV-03 | V1 | ✅ 2026-10-04 | `python/neuroedge/trace.py` |
| **TSK-W1-03** | RFC-0011: `motion.*`, leased token with expiration, safe state | FR-HAL-01 | V1 + V2 | ✅ 2026-10-01 | `docs/rfc/0011-nguyen-thuy-motion.md` |
| **TSK-I2a-05** | `motion.*` on `sim` and `linux` per RFC-0011 | FR-HAL-01, FR-PER-02 | V1 + V2 | 🟡 Complete on sim and dummy linux; physical PWM, physical boards, C HAL remaining | `docs/rfc/0011-nguyen-thuy-motion.md` · `hal/motion.py` |
| **TSK-N2-01** | Envelope hook in `digital_out`, rejection does not consume token | FR-HAL-* | — | ✅ 2026-10-04 | `python/neuroedge/hal/envelope.py` |
| **TSK-N2-02** | Atomic envelope policy, injected clock, event recording | — | — | ✅ 2026-10-04 | `python/neuroedge/hal/envelope.py` |
| **TSK-N2-03** | Safe shutdown hooks for `mcp serve`: `close()`, SIGTERM | — | — | ✅ 2026-10-04 | `python/neuroedge/sim/serve.py` |
| **TSK-N2-04** | Five-assertion safety regression contract | — | — | ✅ 2026-10-04 | `python/tests/test_safety_regressions.py` |
| **TSK-N2-05** | Update header diagram in `mcp_server.py` with envelope stage | — | — | ✅ 2026-10-04 | `python/neuroedge/mcp_server.py` |

- [x] **Criterion N2.1:** Two concurrent commands on the same pin yield exactly one `envelope_refused`.
- [x] **Criterion N2.2:** SIGTERM mid-pulse on gpio-sim pulls line to 0; TSK-N2-03 unit issues `hal.close()`, code 143.
- [x] **Criterion N2.3:** All five assertions of the regression contract pass green.

**Exit criteria I2a:**

- [x] **Criterion 1:** Six RFCs (0007, 0009→0013) Approved; `schemas/` modifies only within scope of those RFCs.
- [x] **Criterion 2:** RFC-0007 changes 0 bytes of `schemas/gate.v1.json` — changes only via RFC-0009.
- [x] **Criterion 3:** Each package has sample agent running on `sim` and `linux`; `verify --targets sim,linux` passes 100%.
- [x] **Criterion 4:** Gate numeric comparison: valid corpus and counterexamples closed; C walker matches host engine.
- [ ] **Criterion 5:** Loss of data source mid-session blocks actions fail-closed; actuators return to safe state.
- [x] **Criterion 6:** Swap vision models via configuration; traces contain no raw frames; `replay` reproduces verdicts.
- [x] **Criterion 7:** Agent requesting extended primitive rejected at build time on board without declaration, stating all three components.
- [x] **Criterion 8:** ADC spike results recorded and ADC decision implemented.
- [ ] **Criterion 9:** Five core primitives and three canonical traces preserve verdict sequence; TTFV under 10 minutes.

### 4.3.2 I2b — Starter kits and rapid assembly

| | |
|:---|:---|
| **Goal** | User selects a kit, runs on `sim` in under 10 minutes, builds physical device from BOM and wiring diagram |
| **Entry conditions** | — |
| **Measurement signal** | Exit criteria below; A12 measured at I7 |
| **Roles** | V3 (lead), V1, V5 |

| Task code | Work item | PRD requirement | Owner | Status | Deliverable (artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-I2b-01** | Three hardware kits from three existing templates | FR-DX-05, FR-DX-06 | V3 | ✅ 2026-10-04 | `python/neuroedge/templates/` · `fixtures/agents/` |
| **TSK-I2b-02** | Two kits for new packages: gate camera and servo blinds | FR-DX-05 | V3 + V5 | ✅ 2026-10-04 | `python/neuroedge/templates/` · `fixtures/agents/` |
| **TSK-I2b-03** | Starter gate library for inheritance: door, light, valve, buzzer, AC, camera, motor | FR-GATE-05 | V1 | ✅ 2026-10-04 | `gates/` · `digests.lock` |
| **TSK-I2b-04** | Rapid assembly command `neuroedge add` for action, gate, sensor, device | FR-DX-01, FR-DX-08 | V3 | ✅ 2026-10-04 | `python/neuroedge/cli/main.py` |

**Exit criteria I2b:**

- [x] **Criterion 1:** Five kits run via `neuroedge new --template` on `sim`, tested in `wheel-smoke`.
- [ ] **Criterion 2:** TTFV on `sim` for all kits achieves under 10 minutes.
- [x] **Criterion 3:** `neuroedge add` generates action + gate + bidirectional test; rerunning does not overwrite existing files.
- [x] **Criterion 4:** Every parent gate in starter library carries counterexample cases against softening.

### 4.3.3 I2c — Open platform

| | |
|:---|:---|
| **Goal** | Third parties connect NeuroEdge to new products via extension points, proxies, and remote actuators (Q-67) |
| **Entry conditions** | — · code tasks await signing of respective RFCs |
| **Measurement signal** | M6, A13; number of third-party plugins passing conformance test |
| **Roles** | V1 (lead), V3; human for TSK-I2c-16 on real HA and TSK-I2c-17 |
| **Design** | `docs/architecture/vi/16-ecosystem-landscape.md` §4 |

| Task code | Work item | PRD requirement | Owner | Status | Deliverable (artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-I2c-01** | Open platform decision and design (Q-67) | FR-EXT-01→09 | V1 | ✅ 2026-10-04 | `docs/architecture/vi/16-ecosystem-landscape.md` §4 |
| **TSK-I2c-02** | RFC-0016: decoupled safety core and Extension SDK | FR-EXT-01→05, FR-EXT-09 | V1 | ✅ 2026-10-04 | `docs/rfc/0016-loi-tach-duoc-va-extension-sdk.md` |
| **TSK-I2c-03** | RFC-0017: namespaced call source `bridge:<id>` | FR-EXT-03 | V1 | ✅ 2026-10-04 | `docs/rfc/0017-nguon-goi-theo-khong-gian-ten.md` |
| **TSK-I2c-04** | RFC-0018: remote actuators and safe-off levels | FR-EXT-07 | V1 | ✅ 2026-10-04 | `docs/rfc/0018-co-cau-chap-hanh-tu-xa.md` |
| **TSK-I2c-05** | `--board <path>` external board profile | FR-EXT-05, FR-TGT-08 | V1 | ⏳ Not started | `python/neuroedge/hal/board.py` |
| **TSK-I2c-06** | Licensing: conformance corpus relicensed to Apache-2.0 | FR-GOV-03 | V1 | ✅ 2026-10-04 | `LICENSING.md` |
| **TSK-I2c-07** | `neuroedge.guard` API: standalone safety core | FR-EXT-01 | V1 | ✅ 2026-10-09 | `python/neuroedge/guard.py` |
| **TSK-I2c-08** | Assets from path, package, git | FR-EXT-05 | V1 | ⏳ Not started | `python/neuroedge/templates/` |
| **TSK-I2c-09** | RFC-0014 code: facts from external processes via Unix socket | FR-MDL-04, FR-MDL-10, FR-EXT-02 | V1 | ⏳ Not started | `python/neuroedge/` |
| **TSK-I2c-10** | RFC-0017 code: namespaced `source`, `tool-call.v1` | FR-EXT-03 | V1 | 🟡 Half a complete (`bridge:<id>`); half b `[mcp.clients]` remaining | `python/neuroedge/actions/tools.py` |
| **TSK-I2c-11** | Plugin loader and `neuroedge.sdk` entry points | FR-EXT-02, FR-EXT-09, NFR-SEC-10 | V1 | 🟡 Minimal SDK and Actuator complete; remaining 5 kinds not started | `python/neuroedge/sdk/` |
| **TSK-I2c-12** | Conformance test suite per plugin kind (`conformance`) | FR-EXT-03, FR-EXT-04 | V1 | 🟡 Actuator vector L0–L3 complete; remaining 5 kinds not started | `python/neuroedge/testing/conformance/` |
| **TSK-I2c-14** | `neuroedge proxy mcp` shielding existing MCP servers | FR-EXT-06 | V1 | ✅ 2026-10-09 | `python/neuroedge/proxy_mcp.py` |
| **TSK-I2c-15** | `neuroedge proxy http` in front of local HTTP APIs | FR-EXT-06 | V1 | ✅ 2026-10-09 | `python/neuroedge/proxy_http.py` |
| **TSK-I2c-16** | First remote actuator — Home Assistant (RFC-0018) | FR-EXT-07 | V1 | ✅ 2026-10-09 | `python/neuroedge/hal/remote.py` |
| **TSK-I2c-18** | Community index and `plugin search/install` | FR-EXT-08 | V3 | ⏳ Not started | external repo index |
| **TSK-I2c-19** | Package for partner trial (Q-70) | FR-DX-02, FR-DX-05, FR-EXT-01, FR-EXT-06 | V3 | ✅ 2026-10-09 | `docs/user/doi-tac/` · `scripts/partner_guides_check.sh` |
| **TSK-S3-21** | Pin `extends` via digest `@<ver>#sha256:` | FR-GATE-05, FR-GATE-06 | V1 | ⏳ Not started | Requires dedicated RFC |
| **TSK-V1a-01** | Finalize and defend RFC-0002 through review | FR-TGT-08, FR-HAL-01 | V1 | ✅ 2026-10-04 | `docs/rfc/0002-mo-rong-target-va-nguyen-thuy-thi-giac.md` |
| **TSK-P2-06** | Self-verification certification "NeuroEdge-gated" for third parties | FR-GOV-03 | V3 | ⏳ Not started | `docs/spec/tool_calling.md` §9 |

**Exit criteria I2c:**

- [x] **Criterion 1:** RFC-0016, 0017, 0018 and RFC-0002 Approved.
- [x] **Criterion 2:** Programs without `agent.toml` can gate actions via `neuroedge.guard`, emitting valid traces.
- [ ] **Criterion 3:** For each of the six extension point kinds, out-of-repo packages pass `conformance` and run.
- [x] **Criterion 4:** `proxy mcp` shields existing MCP servers in ≤ 3 commands; `plugin doctor` warns against shortcuts.
- [x] **Criterion 5:** Remote HA actuator correctly enforces L1 safe-off; irreversible actions lacking safe-off are rejected.
- [ ] **Criterion 6:** External process facts pass with sufficient evidence per RFC-0014 §7.
- [ ] **Criterion 7** *(paused per Q-72)*: Target list opened per RFC-0002.
- [ ] **Criterion 8 (A13)** *(paused per Q-72)*: `neuroedge-muse` bridge written in separate repo passes conformance tests in ≤ 1 day.
- [ ] **Criterion 9:** `pytest` green, 0 skipped; `wheel_smoke.sh` installs and runs out-of-repo plugins from wheel.

**Partner trial (Q-70):**

- [x] **Partner 1:** Criteria 2, 4, 5 satisfied; `proxy http` complete.
- [x] **Partner 2:** Wheel manually tested; 47 steps across three guides run cleanly on wheel.
- [ ] **Partner 3:** Written trial agreement with partner.
- [ ] **Partner 4:** Dedicated feedback channel and bug intake process.
- [ ] **Partner 5:** Partner installs wheel and shields one MCP server / device API in ≤ 15 minutes.

### 4.3.4 I2d — Missions and operator agents

| | |
|:---|:---|
| **Goal** | Loops ① and ② of Q-72 on simulator: mission contracts, 24/7 operator agent, chat approval |
| **Entry conditions** | Completed portion of I2c; code tasks await signed RFCs |
| **Measurement signal** | A15 → A22 (PRD §11.1); LLM cost; days runtime runs continuously on G2 |
| **Roles** | V1 (lead), V3, V7, V2, tech lead |
| **Design** | Q-72, Q-87, Q-88 · PRD §4.5, §5.4–§5.6 · `docs/spec/missions.md` · Blueprint proposal |

| Task code | Work item | PRD requirement | Owner | Status | Deliverable (artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-I2d-01** | RFC mandatory comprehension check (`requires = [...]`) for `board.v1` (`docs/spec/missions.md` MS-SF-02) | FR-ACE-03, FR-HAL-02 | V1 + tech lead | ⏳ Not started | `docs/rfc/` |
| **TSK-I2d-02** | RFC conditional safety (symmetric `safe_state`) (`docs/spec/missions.md` MS-SF-01, MS-SF-04 → 06) | FR-ACE-03, FR-BP-06, NFR-REL-02 | V1 + V2 + tech lead | ⏳ Awaiting TSK-I2d-01 | `docs/rfc/` |
| **TSK-I2d-03** | Conditional safety code: HAL, envelope, token accounting, C walker (`docs/spec/missions.md` MS-SF-01 → 06) | FR-ACE-03, FR-BP-06, NFR-REL-02 | V1 + V2 | ⏳ Awaiting TSK-I2d-02 | `python/neuroedge/hal/` |
| **TSK-I2d-04** | RFC `mission.v1`: multi-device mission contract (`docs/spec/missions.md` MS-CT-01 → 06, MS-CK-02) | FR-MSN-01 → FR-MSN-09 | V1 + tech lead | ⏳ Not started | `docs/rfc/` |
| **TSK-I2d-05** | Mission contract compiler to envelope and watchdog (`docs/spec/missions.md` MS-CP-01 → 06, MS-CX-01 → 03, MS-WD-01) | FR-MSN-02, FR-MSN-03, FR-MSN-05, FR-MSN-07, FR-MSN-10, FR-MSN-11 | V1 | ⏳ Awaiting TSK-I2d-04 | `python/neuroedge/mission/` |
| **TSK-I2d-06** | Approval card ≤ 5 lines and drafting loop from structured diff (`docs/spec/missions.md` MS-AP-01 → 05) | FR-MSN-12, FR-MSN-13, FR-MSN-14, FR-CLI-15 | V3 | ⏳ Awaiting TSK-I2d-04 | `python/neuroedge/mission/` |
| **TSK-I2d-07** | Monotonic clock for watchdog, `unsynced` wall-clock handling (`docs/spec/missions.md` MS-CK-01 → 03) | FR-MSN-04, FR-AGT-03 | V1 | ⏳ Not started | `python/neuroedge/agent/` |
| **TSK-I2d-08** | Two processes: 24/7 runtime and untrusted LLM worker — the worker is the NeuroClaw brain (Q-83), no Python worker; this task is the runtime half and its supervision of the brain (`docs/spec/missions.md` MS-RT-01, MS-RT-02, MS-RT-04) | FR-AGT-01, FR-AGT-02, FR-AGT-07, FR-CH-05, NFR-REL-06, NFR-SEC-13 | V1 | ⏳ Not started | `python/neuroedge/agent/` |
| **TSK-I2d-09** | Scheduler, deterministic detectors, `llm_budget`, proactive reporting — split by Q-83: detectors, watchdog and mission schedule in the box; reminders, heartbeat, `llm_budget` and report wording stay in NeuroClaw (already there) (`docs/spec/missions.md` MS-RT-03, MS-RT-05 → 07, MS-WD-02 → 04, MS-CK-04) | FR-AGT-03 → FR-AGT-06, FR-MSN-09, NFR-COST-01, NFR-COST-02, NFR-REL-05 | V1 | ⏳ Not started | `python/neuroedge/agent/` |
| **TSK-I2d-10** | RFC and code for leak-free dataflow: runtime as sole egress (`docs/spec/missions.md` MS-EG-01 → 04) | FR-EGR-01 → FR-EGR-04, FR-MSN-06, NFR-SEC-11 | V1 + tech lead | ⏳ Not started | `python/neuroedge/egress/` |
| **TSK-I2d-11** | RFC `chat:<id>` source and signed approval record with nonce, expiry (DP-A-06, `docs/spec/deployment_profiles.md`) (`docs/spec/missions.md` MS-CH-02, MS-CH-03) | FR-CH-02, FR-CH-04, FR-ACE-10, FR-TRC-13 | V1 + tech lead | ⏳ Not started | `docs/rfc/` |
| **TSK-I2d-12** | Telegram adapter and approval records in runtime — the box's own approval bot, never the brain's bot token; at most 4 pending questions (DP-A-06, DP-COM-09) (`docs/spec/missions.md` MS-CH-01, MS-CH-04, MS-CH-05) | FR-CH-01, FR-CH-03, FR-CH-04, FR-GATE-04, FR-CLI-14, NFR-SEC-12 | V3 + V1 | ⏳ Awaiting TSK-I2d-11 (the 4-question cap of DP-COM-09 is in, 2026-10-14) | `python/neuroedge/channels/` |
| **TSK-I2d-13** | RFC trace segments in `trace.v1`: replayable segment sequence (`docs/spec/missions.md` MS-TS-01) | FR-TRC-11, FR-TRC-13, FR-ACE-06, NFR-OBS-01 | V1 + tech lead | ⏳ Not started | `docs/rfc/` |
| **TSK-I2d-14** | Segmented trace code, periodic flushing, per-segment replay (`docs/spec/missions.md` MS-TS-01 → 03) | FR-TRC-12, NFR-OBS-04 | V1 | ⏳ Awaiting TSK-I2d-13 | `python/neuroedge/testing/` |
| **TSK-I2d-15** | G1: fish tank physics model on `sim` (30-day fast-forward) (`docs/spec/missions.md` MS-FT-01) | FR-TGT-07 | V7 + V1 | ⏳ Not started | `python/neuroedge/sim/` |
| **TSK-I2d-16** | G2: continuously running runtime on `linux` with auto-restart (`docs/spec/missions.md` MS-FT-04, MS-NF-02) | FR-AGT-01, NFR-REL-06 | V1 | ⏳ Not started | `python/tests_linux/` |
| **TSK-I2d-17** | `neuroedge lab doctor` inspecting each mission sensor (`docs/spec/missions.md` MS-LB-02) | FR-DX-10 | V7 | ⏳ Not started | `python/neuroedge/lab/` |
| **TSK-I2d-19** | Fish tank scenario and A15→A22 acceptance on G1 (`docs/spec/missions.md` MS-FT-02, MS-FT-03, MS-RT-08, MS-TS-04) | FR-TGT-07, FR-AGT-04, NFR-COST-01 | V1 + V3 | ⏳ Not started | `fixtures/agents/` · `demo/` |
| **TSK-I2d-20** | RFC verification steps and user-declared multi-step flows (Q-73) (`docs/spec/missions.md` MS-CH-06) | FR-CH-06, FR-ACE-10 | V1 + tech lead | ⏳ Not started — before TSK-I2d-11 | `docs/rfc/` |
| **TSK-I2d-21** | Verification step code: checker plugins, risk labels, pass/fail traces (`docs/spec/missions.md` MS-CH-06, MS-CH-07) | FR-CH-06, FR-TRC-13 | V1 + V3 | ⏳ Awaiting TSK-I2d-20 | `python/neuroedge/actions/` |
| **TSK-I2d-22** | NeuroEdge brain: NeuroClaw, hard fork of PicoClaw, MCP-only to runtime (Q-76, Q-78) | FR-AGT-12, FR-AGT-02 | V1 + V3 | 🟡 NeuroClaw has repo and CI (2026-10-13): mTLS, explains `ask` prompts clearly; full PicoClaw capabilities with risk labels, web console, and cross-platform releases (Q-80); `neuroclaw update` downloads NeuroClaw releases, not PicoClaw; capability breakdown in `docs/reference/capabilities.md` of that repo (PR #9); internal demo runs all six scenes via Telegram (`demo/i2f-chat-den-cua/`); v0.2.0 → v0.2.2 released (2026-10-14): archives for Linux, macOS, Windows, FreeBSD, NetBSD, deb/rpm packages, Android build, GHCR image; `get_diagnostics` tool, hourly and daily LLM call budget (counts all requests, scheduled reminders still delivered verbatim when exhausted), commands `session list/clear`, `heartbeat run` (PR #14); documentation matches code, English and nine translations (PR #12); real VPS postponed (`TODOS.md` #69) | [`letrongminh/neuroclaw`](https://github.com/letrongminh/neuroclaw) |
| **TSK-I2d-23** | Standard MCP tool suite for all workers: `propose_mission`, `mission_status`, `explain_block`; the only route for authoring mission contracts over MCP, carrying the contract tools of `docs/spec/missions.md` MS-AP-03 and MS-LB-01 (replaces Lab loop ①, Q-88) | FR-AGT-12, FR-MSN-13, FR-DX-10 | V1 | ⏳ Awaiting TSK-I2d-04 | `python/neuroedge/mcp/` |
| **TSK-I2d-24** | In-home worker isolation: dedicated user, no hardware privileges, compromised worker test (DP-A-03; the local page's per-run key, DP-A-02, landed 2026-10-14) | NFR-SEC-13, FR-AGT-12 | V1 | ✅ Done (2026-10-15): `neuroedge doctor --brain-user --keys` names every way the brain's user reaches the box (device group or node, key directory, `/proc` without `hidepid=2`; TC-A-03-1); the brain's own Linux user, for real (TC-A-03-2, `scripts/brain_isolation.sh` in job `linux-hal`), green since 2026-10-15 | `python/neuroedge/isolation.py` · `python/tests_linux/` |
| **TSK-I2d-25** | External user installer for box + NeuroClaw (Q-81; DP-COM-06, DP-COM-07, DP-A-04, DP-A-05, DP-A-09 → DP-A-11): single command generates keys, issues expiring renewable tokens, starts box and brain; blank-machine guide to "bật đèn qua chat" (turn on the light via chat); traces sufficient to tally gate conditions ① ② | FR-AGT-12, B6, B7 (PRD §11.2) | V1 | 🟡 2026-10-14: `neuroedge pair init / renew / rotate` (tokens ≤ 7 days, renewed and rotated on a running box), `--revoked`, `neuroedge ui-link` and the 0600 link file, `mcp serve --ui --target linux` so `ask` on G2 is answered at home (DP-A-04, DP-A-05, DP-A-10, DP-A-11) done; `neuroedge install --profile full` (users, keys, the pinned NeuroClaw checked by SHA-256, the brain's mTLS config, hardened systemd units, /proc hidepid, then doctor; DP-A-09, TC-A-09-1, CI job `install-full`, green since 2026-10-15 (PR #134)); `--allow shell|cron_shell|skill_install` and `neuroedge status` list Profile A's risk labels (TC-COM-06-2) | `demo/` → `python/neuroedge/` · `docs/user/chat-voi-nha.md` |
| **TSK-I2d-26** | Contract between the two repositories (Q-83): every tool carries `_meta["dev.neuroedge/contract"]`; NeuroClaw treats an unknown major or status as REJECTED and handles `fallback`, `escalated_to`; NeuroClaw CI runs against a pinned `neuroedge mcp serve --target sim`; NeuroClaw pinned by version and SHA-256 wherever the box fetches it (DP-COM-08, DP-A-07, DP-NF-02) | FR-AGT-12 | V1 | ✅ Done (2026-10-15): the box tags every tool; NeuroClaw reads results fail-closed and its `neuroedge-contract` job runs against this box pinned at `f1a8111` (neuroclaw #24, merged); the box pins NeuroClaw by version and SHA-256 where it fetches it (`neuroedge install`, TSK-I2d-25; `neuroclaw.lock`, TSK-I2f-14) | `python/neuroedge/mcp_server.py` · NeuroClaw `pkg/tools/integration/` · NeuroClaw CI |
| **TSK-I2d-27** | Deprecate the box's own System 2 LLM path (Q-83): `SystemTwo` with a real LLM, `mcp_host.py` and retrieval only behind `NEUROEDGE_LEGACY_SYSTEM_TWO=1`; grammar, System 1 and the offline answer unchanged; public API kept with a deprecation warning (DP-A-08) | FR-MDL-11, FR-MDL-12 | V1 | ✅ 2026-10-14 | `python/neuroedge/models/`, `python/neuroedge/mcp_host.py` |
| **TSK-I2d-28** | Fish tank demos on simulation and emulation, ahead of TSK-I2d-15/19 (owner, 2026-10-15): one `aquarium` agent (heater, air pump, light, water probe; the heater never on in warm water or without a reading, the air pump's safe state is on) shown on `sim`, `linux` (gpio-sim, LM75 on i2c-stub), `esp32s3` on QEMU and Profile A/B; no physics model, mission contract or Blueprint | FR-TGT-07, FR-DX-09 | V1 | ✅ Done (2026-10-15): `fixtures/agents/aquarium`, `demo/i2b-be-ca-gia-lap/` (D1 → D5), `test_aquarium.py` (rules, the demo day, chip = box, chip sessions replay), `tests_linux/test_kit_aquarium.py`, `scripts/qemu_aquarium.py` in job `aquarium-qemu`; D1, D3/D5 (Docker, 87 s) and D4 re-run on a Mac | `fixtures/agents/aquarium` · `demo/i2b-be-ca-gia-lap/` |
| **TSK-I2d-29** | Virtual board `sim-virtual` (Q-84 phase A): derived from the agent, `sim` only, `risk=virtual_board`, digest checked at replay (VP-VB-01 → VP-VB-08, VP-NF-01, VP-NF-02) | FR-DX-01, FR-DX-03 | V1 | ✅ Done (2026-10-15): `python/neuroedge/hal/virtual_board.py`; `build`, sessions, replay, `new --board sim-virtual` and `add` use it; page chip "Bảng mạch ảo"; `test_virtual_board.py` (TC-VB-01 → 09, TC-VNF-01, 02) | `python/neuroedge/hal/board.py` · `python/neuroedge/sim/` · `docs/spec/virtual_parts.md` |
| **TSK-I2d-30** | Parts catalogue, `[sim.parts]`, `neuroedge add part`; the aquarium on parts (Q-84 phase B, VP-PT-01 → VP-PT-08) | FR-DX-08, FR-TGT-06 | V1 | ✅ Done (2026-10-15): `python/neuroedge/hal/parts.toml` (17 kinds), `hal/parts.py`, `neuroedge add part` (`--list`, `--drives`), ranges in `set_sensor`, page icons by kind; aquarium on parts; `test_parts.py` (TC-PT-01 → 09) | `python/neuroedge/hal/parts.toml` · `python/neuroedge/templates/add.py` · `python/neuroedge/viz/assets/ui.js` |
| **TSK-I2d-31** | Parts canvas on the sim page (Q-84 phase C, VP-CV-01 → VP-CV-05) | FR-DX-10, FR-TGT-06 | V1 + V7 | ⏸ Deferred: reopens with data after the 2026-12-06 demand gate (Q-77, Q-84) | `python/neuroedge/viz/assets/ui.js` · `python/neuroedge/sim/ui.py` |
| **TSK-I2d-32** | Per-board pin map `[targets.<board>.pins]` (Q-84 phase A+, VP-PM-01 → VP-PM-06): agent names kept in code and traces, the board pin's envelope applies, map printed and in trace metadata; lead engineer approves, `threat_model.md` entry | FR-TGT-02, FR-HAL-01 | V1 + tech lead | ✅ Done (2026-10-16): `python/neuroedge/hal/pin_map.py`, `test_pin_map.py`, `tests_linux/test_pin_map_linux.py`; `threat_model.md` §2m approved by the lead engineer (VP-PM-06, TC-PM-06-1); the chip side moves to TSK-S4-01 (PR #138) | `python/neuroedge/engine/compiler.py` · `python/neuroedge/hal/board.py` · `python/neuroedge/engine/firmware.py` · `docs/spec/threat_model.md` |
| **TSK-N0-07** | Specify the closed MCP tool surface of TSK-I2d-23 (names, inputs, outputs, error codes) before code, reconciling it with the tool names of `docs/spec/missions.md` MS-AP-03 (Q-88) | FR-MSN-13, FR-AGT-09 | V2 | ⏳ Not started | `docs/spec/missions.md` |
| **TSK-N0-08** | Separate device permissions from any MCP client other than the brain (a client with a shell, such as Claude Code, on the box host): `neuroedge doctor` warns when the client's user reaches devices or can write the policy the box loads; extends TSK-I2d-24 (`docs/spec/threat_model.md` §2c, Q-88) | NFR-SEC-09 | V2 | ⏳ Not started | `docs/user/` · `tests_linux/` |
| **TSK-N6-01** | Non-human `call_source` for runtime-initiated calls: `schedule` (`docs/spec/missions.md` MS-RT-03; the Lab design named it `trigger`) | FR-AGT-03, FR-ACE-09 | — | ⏳ Not started | `actions/tools.py` |
| **TSK-N6-02** | `schedule ∉ HUMAN_SOURCES`, asserting a scheduled call never answers `ask` (MS-RT-03) | Q-26 | — | ⏳ Not started | `actions/confirmation.py` |
| **TSK-N6-03** | Debounce and rate ceiling for scheduler and detector calls in the runtime, preventing infinite retries (MS-RT-03) | FR-AGT-03 | — | ⏳ Not started | `python/neuroedge/agent/` |

- [ ] **Criterion N0.4:** `neuroedge doctor` warns on gpio-sim when an MCP client's user belongs to the `gpio` group (TSK-N0-08).

**Exit criteria I2d:**

- [ ] **Criterion 1:** Planned I2d RFCs Approved; `schemas/` modifies only within scope of those RFCs.
- [ ] **Criterion 2 (A15, A17):** 100% of conflicting contracts rejected; 100% of violating commands blocked.
- [ ] **Criterion 3 (A16, A19):** 30-day scenario on G1: reflexes and sample alerts run reliably; cost stays under cap.
- [ ] **Criterion 4 (A18):** Undeclared egress destinations blocked and logged 100%; zero image leaks when forbidden.
- [ ] **Criterion 5 (A20):** Approvals from wrong source, expired, stale nonce, or mismatched digest are 100% rejected.
- [ ] **Criterion 6 (A21):** `safe_state: on` lacking interlock is rejected; existing profiles preserve verdict sequence.
- [ ] **Criterion 7 (A22):** Replay reproduces 100% of verdicts from 30-day trace sequence.
- [ ] **Criterion 8:** Runtime runs continuously on G2; MCP client authors contracts via the TSK-I2d-23 tools, human locks (Q-88).
- [ ] **Criterion 9:** User-declared verification steps (reading code on `sim`) run end-to-end; LLM and MCP client responses to verification steps are 100% rejected (Q-73).
- [ ] **Criterion 10:** NeuroEdge brain communicates with runtime strictly via MCP; compromised worker (shell commands, prompt injection) cannot toggle any pins on G2 (Q-76).
- [ ] **Criterion 11:** `pytest` green, 0 skipped; `wheel_smoke.sh` passes; demo in `demo/`.

### 4.3.5 I2e — Minimal NeuroEdge Blueprint

| | |
|:---|:---|
| **Goal** | Loop ③ of Q-72 on simulation: makers package Blueprints with `blueprint pack`, users install with `blueprint install` |
| **Entry conditions** | I2d achieves criteria 2→7 on G1; code tasks await signed RFC |
| **Measurement signals** | A14; B6, B7, B8 (PRD §11.2) |
| **Assignee** | V3 (lead), V1, V7; team lead; tech lead |
| **Design** | Q-72 · PRD §7.4, §8.4 · architecture chapter 15 §6.4 |

| Task code | Work item | PRD requirement | Owner | Status | Deliverable (artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-I2e-01** | RFC `blueprint.v1`: manifest, digest covering entire package (`docs/spec/blueprint.md` BL-FMT-01 → 06, BL-EV-01) | FR-BP-01, FR-BP-04, FR-BP-06, FR-BP-08 | V1 + tech lead | ⏳ Not started | `docs/rfc/` |
| **TSK-I2e-02** | `neuroedge blueprint pack` packages project into Blueprint (`docs/spec/blueprint.md` BL-PK-01 → 05, BL-SC-03) | FR-BP-02, FR-CLI-13 | V3 | ⏳ Awaiting TSK-I2e-01 | `python/neuroedge/blueprint/` |
| **TSK-I2e-03** | `neuroedge blueprint install` checks digest, displays approval preview (`docs/spec/blueprint.md` BL-IN-01 → 06, BL-EV-03, BL-SC-01, BL-SC-02, BL-SC-04) | FR-BP-03, FR-CLI-13, NFR-SEC-14 | V3 + V1 | ⏳ Awaiting TSK-I2e-01 | `python/neuroedge/blueprint/` |
| **TSK-I2e-04** | Free static git/HTTPS Blueprint index (`docs/spec/blueprint.md` BL-IX-01 → 03) | FR-BP-05 | V3 | ⏳ Not started | external index repository |
| **TSK-I2e-05** | Fish tank kit: BOM, wiring diagram, sample contracts, traces (`docs/spec/blueprint.md` BL-KT-01, BL-KT-03, BL-EV-02) | FR-DX-09 | V3 + V7 | ⏳ Not started | `python/neuroedge/templates/` |
| **TSK-I2e-06** | BOM with affiliate links located on separate page outside kit (`docs/spec/blueprint.md` BL-KT-02) | FR-BP-07 | team lead + V3 | ⏳ Not started | `docs/user/` |
| **TSK-I2e-07** | Gate milestone metrics logged locally, transmitted only when enabled (`docs/spec/blueprint.md` BL-NF-02) | FR-TEL-07 | V3 | ⏳ Not started | `python/neuroedge/` |
| **TSK-I2e-08** | Wheel for external testers with blueprint install step (`docs/spec/blueprint.md` BL-NF-01) | FR-DX-02 | V3 | ⏳ Not started | `scripts/wheel_smoke.sh` |
| **TSK-I2e-12** | Home Assistant add-on running runtime, zero CLI commands (Q-74) | FR-DX-02, FR-AGT-01 | V3 | ⏳ Awaiting TSK-I2d-16 | external add-on repository |
| **TSK-I2e-13** | SD card image for Pi, Telegram pairing via QR code (Q-74) | FR-DX-02, FR-CH-03 | V3 | ⏳ Awaiting TSK-I2d-12 | `scripts/` · `docs/user/` |
| **TSK-I2e-14** | `neuroedge new --layout host+mcu`: project scaffold for Pi + ESP32 (Q-75) | FR-DX-01, FR-BP-02 | V3 | ⏳ Not started | `python/neuroedge/templates/` |
| **TSK-I2e-09** | Blueprint installation measurement session (A14) with 3 external testers (`docs/spec/blueprint.md` BL-IN-07) | FR-DX-01 | V3 + testers | ⏳ Not started | `docs/reports/` |
| **TSK-I6-04** | Community channels on HA/ESPHome forums, bug reporting flow | — | V3 + team lead | ⏳ Not started | forum posts, feedback channels |
| **TSK-I2e-10** | Interviews for gate: ≥ 10 people (≥ 5 makers) | — | team lead | ⏳ Not started | `docs/business/` |
| **TSK-I2e-11** | 8-week demand gate (B6, B7, B8), record branch point | — | team lead + product owner | ⏳ Not started | `roadmap/neuroedge-prd.md` §15 |

**Exit criteria I2e:**

- [ ] **Criterion 1:** RFC `blueprint.v1` Approved.
- [ ] **Criterion 2 (A14):** External user installs fish tank Blueprint on `sim` in under 10 minutes.
- [ ] **Criterion 3:** `blueprint pack` and `install` share verdict sequence; mismatched digest rejected.
- [ ] **Criterion 4:** Static index lists fish tank Blueprint; kit passes tests; affiliate BOM kept external.
- [ ] **Criterion 5:** 8-week gate measured, a Q-N records selected branch.
- [ ] **Criterion 6:** Testers set up home box via Home Assistant add-on or SD card, pair via QR, zero CLI commands (Q-74).
- [ ] **Criterion 7:** `pytest` green, 0 skipped; `wheel_smoke.sh` passes.

### 4.3.6 I2f — NeuroEdge Cloud and ESP32 home box

**Conditional (Q-74 step 2).** Opens only when the 2026-12-06 demand gate shows testers blocked by setup, API keys, or self-hosting; if not opened, keep ⏸, do not cut. **Goal:** users only need to chat — "brain" (LLM worker, conversation, mission contract compilation) runs on optional NeuroEdge Cloud and coordinates multiple devices, homes, and people; "spinal cord" (gate, reflexes, approval checks, egress egress, traces) always stays on the home box. **Design:** Q-74 · PRD FR-AGT-10, FR-AGT-11, FR-CH-07 · `docs/architecture/vi/15-target-architecture.md` §6.10 · `docs/spec/threat_model.md` §2k. **Dependencies:** I2e.

**Exception Q-79, Q-83 — Profile B, one chip.** Eight tasks TSK-I2f-10 → I2f-17 open immediately, without waiting for the demand gate: brain (Telegram client, LLM loop) and gate in one ESP32-S3 image, with risk labels; all LLM tool calls route through `ne_brain_bridge` into `ne_gate`. Requirements and test cases: [`docs/spec/deployment_profiles.md`](../docs/spec/deployment_profiles.md) (DP-B-*). Stage 1 and the host-C and QEMU parts run without a board; the on-board parts require the DevKitC N16R8 board (TSK-I3a-08). Guide: [`docs/user/esp32-mot-chip.md`](../docs/user/esp32-mot-chip.md).

| Task code | Description | Requirement | Owner | Status | Evidence |
|:---|:---|:---|:---|:---|:---|
| **TSK-I2f-01** | RFC cloud ↔ box channel: signed rules, approval verified at node, command scope ceiling | FR-AGT-10, FR-AGT-11 | V1 + tech lead | ⏸ Awaiting demand gate (Q-74) | `docs/rfc/` |
| **TSK-I2f-02** | Shared chat channel gateway and relay: chat ↔ instance, box ↔ instance, tier token caps (Q-76) | FR-AGT-10, NFR-COST-01 | V1 + V3 | ⏸ Awaiting TSK-I2f-01 | external service outside repo |
| **TSK-I2f-07** | Per-user isolated brain instance (microVM), idle sleep, separately encrypted memory | FR-AGT-12, NFR-SEC-* | V1 | ⏸ Awaiting TSK-I2f-02 and TSK-I2d-22 | external service outside repo |
| **TSK-I2f-08** | Approval signed on phone (passkey), home box independently verifies signature | FR-CH-08, FR-CH-04 | V1 + V3 | ⏸ Awaiting TSK-I2f-01 | `python/neuroedge/channels/` |
| **TSK-I2f-09** | Spike: RAM, wake-up latency, and cost per idle instance, before pricing | NFR-COST-01 | V1 | ⏸ Awaiting demand gate (Q-74) | `docs/reports/` |
| **TSK-I2f-03** | ESP32-S3 box: physical Wi-Fi, receives signed compiled rules, verifies approvals on-chip | FR-AGT-10, FR-OTA-* | V2 | ⏸ Awaiting TSK-I2f-01 and board | `targets/esp32s3/` |
| **TSK-I2f-04** | Multi-node, multi-home mesh: per-node identity, scope ceilings, auto-lock on anomalies | FR-AGT-11 | V1 | ⏸ Awaiting TSK-I2f-01 | `python/neuroedge/agent/` |
| **TSK-I2f-05** | Multiple users in one chat room, bounded roles (shares pairing RFC `TODOS.md` #62) | FR-CH-07, FR-CH-03 | V1 + V3 | ⏸ Awaiting TSK-I2f-01 | `python/neuroedge/agent/` |
| **TSK-I2f-06** | Cloud security review against threat model §2k before first user | NFR-SEC-* | V1 + external reviewer | ⏸ Awaiting TSK-I2f-02 | `docs/reports/` |
| **TSK-I2f-10** | Standalone ESP32-S3, stage 1 (Q-79): boot guard and safe mode, config and secrets in dedicated NVS partition (encrypted under `sdkconfig.secure`), serial console, CI stack guard; ported from zclaw and MimiClaw (MIT) | FR-OTA-02, NFR-SEC-* | V2 | ✅ Done (2026-10-13): three failed boot loops → enters safe mode on fourth loop; secrets entered via masked prompt, not echoed to UART; stack frame ≤ 1024 B, main task remaining ≥ 512 B, all verified on QEMU | `targets/esp32s3/components/{ne_boot,ne_config,ne_console}/` · `scripts/qemu_console.py` · `scripts/check_stack_usage.py` |
| **TSK-I2f-11** | Standalone ESP32-S3, stage 2 (Q-79): Wi-Fi from config, on-chip long-poll Telegram client, accepts messages only from owner ID, `risk=single_chip` label | FR-CH-01, FR-CH-03 | V2 | 🟡 On-chip brain **NeuroClaw-ESP** available in `neuroclaw` repo (`esp32/`, MIT): owner-only Telegram, LLM with fallback URLs, memory, cron reminders, heartbeat, web search, messaging and file sending to owner (`message`, `send_file`) — shares workspace and tools with NeuroClaw Go; runs on QEMU with mock gate (neuroclaw PR #8, #10). Additional (PR #13, NeuroClaw v0.2.1): OpenAI or Anthropic LLM style per URL, Tavily web search, `get_diagnostics`, hourly and daily LLM rate limiting, serial admin console (`memory_read`, `session_list`, `heartbeat_trigger`…), CPU core pinning, builds for ESP32, S3, C3, C6; compared against zclaw and MimiClaw in `docs/reference/capabilities.md` §12 of that repo. Remaining: real Wi-Fi, embedding into NeuroEdge firmware, DevKitC N16R8 board (TSK-I3a-08) | `targets/esp32s3/` · `letrongminh/neuroclaw` `esp32/` |
| **TSK-I2f-12** | Standalone ESP32-S3, stage 3 (Q-79, Q-83): component `ne_brain_bridge` offers `ne_gate` to NeuroClaw-ESP as an `nc_gate` — the same tools and schemas as over MCP, JSON arguments into `ne_arg_value`, facts only from on-chip sources declared by the board profile, `ne_result` into `tool-result.v1`, confirmations from the board button or the owner's Telegram callback (user ID checked by the bridge), a token around every pin move (DP-B-02 → DP-B-08) | FR-AGT-10, FR-CH-04 | V2 | 🟡 Host core done 2026-10-14: same tools and results as the box, checked call by call (`python/tests/test_c_bridge.py`); the `nc_gate` adapter is `main/brain.c` (TSK-I2f-14), the on-board part awaits TSK-I2f-11 | `targets/esp32s3/components/ne_brain_bridge/` |
| **TSK-I2f-13** | Standalone ESP32-S3 (Q-79): initial Wi-Fi and setup without re-flashing firmware — ESP-IDF `wifi_provisioning` (SoftAP or BLE, security1/security2 with PoP code printed on label or shown on serial console); accepts SSID, password, bot token, owner ID, LLM key then writes to `ne_config` (encrypted under `sdkconfig.secure`); hotspot turns off when complete; no open web port transmitting plaintext secrets | FR-CH-03, NFR-SEC-* | V2 | ⏳ Awaiting TSK-I2f-11 and DevKitC N16R8 board (TSK-I3a-08); serial console (TSK-I2f-10) remains fallback path. Implemented in NeuroEdge firmware, not in NeuroClaw-ESP. Box-3: `TODOS.md` #50 | `targets/esp32s3/` |
| **TSK-I2f-14** | One image for Profile B (Q-83): `neuroedge build --target esp32s3 --brain neuroclaw` pins NeuroClaw-ESP by version and SHA-256; merged partition table (OTA slots, `ws` LittleFS from `storage`, `ne_config`, `nvs_keys`); `ne_config` gains fallback LLM, search and time zone and feeds the brain; one owner of Wi-Fi and console; `risk=single_chip` and `risk=readable_flash` at boot and in `status`; OTA replaces the whole image and refuses a downgrade (NVS high-water mark; `factory` kept, so no eFuse anti-rollback), self-test includes the bridge (DP-B-01, DP-B-09 → DP-B-11, DP-B-14, DP-B-15, DP-B-17) | FR-TGT-03, NFR-RES-03 | V2 | ✅ Done (2026-10-15): `build --brain neuroclaw` writes NeuroClaw-ESP, the bridge and `ne_hal` into the project, checked against `targets/esp32s3/brain/neuroclaw.lock` (tree SHA-256), with the merged partition table (DP-B-01, DP-B-09); `main/brain.c` starts the brain on the bridge from `ne_config` (five new keys), owns Wi-Fi and the one console, prints `risk=single_chip`, adds the bridge to the boot self-test; `config ack readable_flash` before a secret (DP-B-10, B-11, B-14, B-15, B-17); green on QEMU in job `brain-firmware` (PRs #134, #136); the table keeps `factory`, so OTA refuses a downgrade by the NVS high-water mark and there is no eFuse anti-rollback (owner, 2026-10-15) | `python/neuroedge/engine/firmware.py`, `targets/esp32s3/` |
| **TSK-I2f-15** | Combined image in CI (Q-83): QEMU end-to-end over openeth with fake Telegram and LLM; size and SRAM budgets (Q-3) and per-task stack report; offline button path; bridge latency on a board (DP-B-02, DP-B-13, DP-B-16, DP-NF-01) | NFR-RES-02, NFR-RES-03 | V2 | 🟡 2026-10-14: job `brain-firmware` (board image: Q-3 size and SRAM, no server symbol, one Wi-Fi owner, `ne_brain_bridge` frames ≤ 512 B; QEMU: offline buttons, free SRAM after the brain starts, every task's stack) and its host-tested scripts (`check_brain_image.py`, `qemu_brain.py`, `check_stack_usage.py --task`, `check_firmware_size.py --checkpoint brain_ready`) — green on CI since 2026-10-15 (PR #134); the fake Telegram and LLM end-to-end and the board latency (DP-NF-01) remain | `.github/workflows/firmware-qemu.yml` |
| **TSK-I2f-16** | Run-time traces on the chip (Q-83): `NE1` lines for every decision while running, safely interleaved; `record --port` reads until stopped and writes replayable `trace.v1` (DP-B-12; with TSK-S4-04) | FR-TRC-01 | V2 | ✅ Done (2026-10-15): the bridge writes one NE1 session per decision (`ne_bridge_trace`, with `action_requested` and the pins the action drove), `record --port --follow` reads past `NE_TRACE DONE`; on the host the sessions replay to the same verdicts and pin commands (TC-B-12-1); on QEMU in job `brain-firmware`, green since 2026-10-15 (PR #134) | `targets/esp32s3/components/ne_trace/`, `python/neuroedge/testing/uart.py` |
| **TSK-I2f-17** | Profile B+ evaluation (Q-83): ESP Privilege Separation on ESP32-S3 versus a two-chip board (S3 brain, C3 gate, UART with a MAC per frame); a decision note, no code (DP-BP-01) | NFR-SEC-13 | V2 | ⏳ Not started | `docs/reports/` |

**Exit criteria I2f:**

- [ ] **Criterion 1:** RFC cloud ↔ box channel Approved; N4 and "server" corollary of Q-10 revised in same PR.
- [ ] **Criterion 2:** Cloud connection severed: reflexes, gate, and local alerts continue running on G1, G2.
- [ ] **Criterion 3:** Cloud sends unsigned rules or unverified approvals: box rejects 100%, writes trace.
- [ ] **Criterion 4:** Single chat room coordinates ≥ 2 emulated homes; commands exceeding scope ceiling blocked.
- [ ] **Criterion 5:** Cloud sends "Đồng ý" without passkey signature: box rejects 100%, writes trace (FR-CH-08).
- [ ] **Criterion 6:** Same brain implementation runs self-hosted on cheap Linux board and on NeuroEdge Cloud without code branching; two users' instances cannot read each other's memory (Q-76).
- [ ] **Criterion 7:** `pytest` green, 0 skipped; security review leaves zero high-severity issues.
- [ ] **Criterion 8 (Q-79):** On DevKitC board, standalone ESP32-S3 receives Telegram chat from owner, invokes tools via `ne_gate`; irreversible actions execute only after physical on-board button press or exact owner ID callback; messages from others discarded and logged.

### 4.4 I3 — Gate on real Box-3

| | |
|:---|:---|
| **Goal** | Gate runs on real ESP32-S3-Box-3 and controls real pins; user loads agent independently; `verify` three tier-1 targets for verdict domain (U2/J3 → M3, A2) |
| **Entry conditions** | Box-3 in hand |
| **Measurement signals** | `verify --targets sim,linux,esp32s3` on board |
| **Assignee** | V2 (lead), V6, V1, V3 |

| Task code | Work item | PRD requirement | Owner | Status | Deliverable (artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-S1-10** | Memory feasibility spike on ESP32-S3-Box-3 | NFR-RES-01, NFR-RES-02 | V2 | 🔴 Awaiting board | `targets/esp32s3/main/memory_probe.c` · `docs/reports/memory_spike_report.md` |
| **TSK-S2-10** | On-chip voice plan conclusion based on spike | — | V2 + team lead | ⏳ Awaiting TSK-S1-10 measurements | `docs/reports/memory_spike_report.md` |
| **TSK-S4-01** | Port 5 HAL primitives to ESP-IDF | FR-TGT-03, FR-HAL-01 | V2 | 🟡 2026-10-14: `digital.out`'s token door `components/ne_hal/` (`ne_hal_on` only on a live token for that pin, `ne_hal_off` never refused; DP-B-08, `test_c_hal.py`); the ESP-IDF writer and the other four primitives remain; with them, the pin-map obligations of `threat_model.md` §2m: a mapped name's GPIO comes from the board pin the map names, never from the agent's name, and a chip recording carries `pin_map` (VP-PM-03) | `targets/esp32s3/components/ne_hal/` |
| **TSK-S4-02** | C99 Gate Engine walker traversing `NETR` v1 on MCU | FR-ACE-01, FR-ACE-03, FR-ACE-08 | V2 + V1 | ✅ 2026-09-24 | `targets/esp32s3/components/ne_gate/` |
| **TSK-S4-03** | `digital.out` and `sensor.read` paths on physical hardware | FR-HAL-06, FR-HAL-07 | V2 | ⏳ Not started | `targets/esp32s3/drivers/` |
| **TSK-S4-04** | `neuroedge verify` command for all 3 tier-1 targets | FR-CI-07, FR-TGT-04 | V1 | 🟡 QEMU operational; awaiting board | `python/neuroedge/cli/main.py` |
| **TSK-S4-05** | Nightly test runner on real hardware board | FR-CI-06, NFR-REL-03 | V3 | ⏳ Not started | `.github/workflows/nightly-hardware.yml` |
| **TSK-S4-07** | C walker compiled on host gcc/clang ASan/UBSan | FR-ACE-01, FR-CI-07 | V2 | ✅ 2026-09-24 | `python/tests/test_c_walker.py` |
| **TSK-S4-08** | Firmware smoke test on Espressif QEMU | FR-CI-06, FR-TGT-03 | V2 | ✅ 2026-09-24 | `.github/workflows/firmware-qemu.yml` |
| **TSK-S4-09** | Firmware trace over UART and record --target esp32s3 | FR-CI-01, FR-TGT-04, FR-CLI-04 | V2 + V1 | ✅ 2026-09-25 | `targets/esp32s3/components/ne_trace/` |
| **TSK-S4-10** | Golden image for LVGL interface on host | FR-HAL-01, FR-CI-05 | V2 | ✅ 2026-09-26 | `targets/esp32s3/ui/` · `scripts/run_ui_golden.sh` |
| **TSK-S4-11** | Static RAM budget on every PR (`idf.py size`) | NFR-RES-01, NFR-RES-02 | V2 | 🟡 Static RAM met; awaiting ESP-SR AFE link | `scripts/check_firmware_size.py` |
| **TSK-S4-12** | Day-one bringup tests with board (codec, speaker, mic, GPIO) | FR-PER-06, FR-HAL-06 | V2 | ⏳ Upon board arrival | `targets/esp32s3/tests/bringup/` |
| **TSK-I3-01** | Firmware flashing path for user agents | FR-CLI-02, FR-TGT-03 | V2 | ✅ 2026-09-26 | `python/neuroedge/engine/firmware.py` |
| **TSK-I3-02** | `esp-emulator` spike for `esp32s3` peripherals | FR-CI-06, FR-TGT-03 | V2 | ⏳ Not started | `docs/reports/` |
| **TSK-I3-03** | `esp32sim` spike: early memory estimation for voice and vision | NFR-RES-01, NFR-RES-02 | V2 | ⏳ Not started | `docs/reports/` |

*Code TSK-S4-06 was never issued; remaining codes are preserved.*

**Exit criteria I3:**

- [ ] 🔴 **Criterion 1:** Memory spike report with real measurements verified against Q-3 thresholds (SRAM ≥ 120 KB, PSRAM ≥ 2 MB, flash ≤ 3.5 MB).
- [ ] **Criterion 2 (A2):** `verify --targets sim,linux,esp32s3` passes 100% on non-audio scenarios.
- [x] **Criterion 3:** Verdict divergence across targets raises `SafetyRegressionError` (NE4002).
- [ ] **Criterion 4:** Nightly runner runs automatically and publishes reports.
- [ ] **Criterion 5:** External developer independently builds and flashes their own agent to Box-3 following documentation.

### 4.4.1 I3a — Extended primitives on `esp32s3`

| | |
|:---|:---|
| **Goal** | Four extended primitive packages running on-chip: Box-3 for sensors, PWM, motion; CoreS3 for vision (Q-53, Q-61). Minimal Pi ↔ ESP32 interconnect and commodity ESP32-S3 board for makers (Q-75) |
| **Entry conditions** | Box-3 and camera board received (Appendix B) |
| **Measurement signals** | Exit criteria below |
| **Assignee** | V2 (lead), V6, V5 |

| Task code | Work item | PRD requirement | Owner | Status | Deliverable (artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-I3a-01** | ESP32-S3 camera board as second reference board (Q-61) | FR-HAL-02, NFR-RES-02 | V2 | 🟡 M5Stack CoreS3 selected; awaiting purchase, profile, measurements | `boards/` · `docs/reports/` |
| **TSK-I3a-02** | C HAL: `digital.in`, read-only I2C bus, `analog.in` on ESP-IDF | FR-HAL-01, FR-TGT-03 | V2 | ⏳ Not started | `targets/esp32s3/hal/` |
| **TSK-I3a-03** | C HAL: PWM (LEDC) in `digital.out` per RFC-0010 | FR-HAL-01 | V2 | ⏳ Not started | `targets/esp32s3/hal/` |
| **TSK-N7-02** | Envelope enforcement in C firmware, missing envelope rejected fail-closed | — | — | ⏳ Not started | `targets/esp32s3/components/` |
| **TSK-W1-04** | Implement `motion.*` on `esp32s3` and crash-safe tests | FR-HAL-01, FR-PER-02 | V2 | ⏳ Not started | `targets/` · `docs/spec/voice_fsm.md` |
| **TSK-I3a-04** | `vision.in` on ESP32-S3 camera board per RFC-0012 | FR-HAL-01 | V5 + V2 | ⏳ Not started | `targets/esp32s3/` |
| **TSK-I3a-05** | `verify --targets sim,linux,esp32s3` for four-package agents | FR-CI-07 | V1 + V2 | ⏳ Not started | `python/neuroedge/cli/main.py` |
| **TSK-I3a-06** | Minimal node RFC: one host ↔ one MCU over serial, heartbeat, loss of comms ⇒ `safe_state` (Q-75) | FR-TGT-08 | V1 + tech lead | ⏳ Not started | `docs/rfc/` |
| **TSK-I3a-07** | Minimal interconnect: two processes on `sim`, then Pi 5 ↔ ESP32-S3; wire-cut test | FR-TGT-08, FR-HAL-01 | V2 + V1 | ⏳ Awaiting TSK-I3a-06 | `python/` · `targets/esp32s3/` |
| **TSK-I3a-08** | Commodity ESP32-S3 board (DevKitC, WROOM N16R8): profile, screenless firmware (Q-75) | FR-HAL-02, FR-TGT-03 | V2 | ⏳ Not started | `boards/` · `targets/esp32s3/` |
| **TSK-I3a-09** | Arduino library (arduino-esp32) wrapping `NETR` walker, token ledger, comms-loss reflex (Q-75) | FR-TGT-03, FR-DX-09 | V2 | ⏳ Awaiting TSK-I3a-08 | `targets/arduino/` |

**Exit criteria I3a:**

- [ ] **Criterion 1:** `verify --targets sim,linux,esp32s3` passes 100% for sample agents of each package on Box-3 and camera board.
- [ ] **Criterion 2:** Firmware with full extended primitives and voice maintains free SRAM ≥ 120 KB (Q-3).
- [ ] **Criterion 3:** Power loss/reset during `motion.*` command on physical board returns mechanism to safe state.
- [ ] **Criterion 4:** Envelopes enforced in firmware; actions attached to envelopes rejected if missing.
- [ ] **Criterion 5:** Serial wire cut between host and ESP32 ⇒ all mechanisms return to `safe_state` within declared timeout, with trace; verified on two-process `sim` and on physical board (Q-75).
- [ ] **Criterion 6:** Commodity ESP32-S3 WROOM board runs locked gate and correctly rejects corpus, without requiring Box-3, from both ESP-IDF firmware and Arduino sketch (Q-75).

### 4.7 I6 — Public launch

| | |
|:---|:---|
| **Goal** | First time external users access product: public repo, `pip install neuroedge` from PyPI, demo of four packages and Blueprint (Q-39, Q-52, Q-77) |
| **Entry conditions** | Commercial license terms (`TODOS.md` #44) |
| **Measurement signals** | First installation from PyPI; first external user runs agent (B1 begins counting) |
| **Assignee** | V3 (lead), team lead, V2, V1 |

| Task code | Work item | PRD requirement | Owner | Status | Deliverable (artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-S3-14** | PyPI release workflow, verifies `pip install` and run | FR-DX-02, FR-GOV-01 | V3 | 🟡 Workflow ready; go-live upon public launch | `.github/workflows/release-pypi.yml` |
| **TSK-S3-09** | Anonymous CLI telemetry, opt-out capable | FR-TEL-01, FR-TEL-02 | V3 | ⏳ Not started | `python/neuroedge/cli/` |
| **TSK-W0-02** | CycloneDX/SPDX SBOM attached to each release | — | V3 | ✅ 2026-09-26 | `scripts/sbom.sh` |
| **TSK-W0-03** | Vulnerability and secret scanning: full-history pip-audit, gitleaks | — | V3 | ✅ 2026-09-26 | `.github/workflows/security.yml` |
| **TSK-I6-01** | Full repository public starting 2026-09-25 | FR-GOV-01 | team lead + V3 | ✅ 2026-09-25 | public repo |
| **TSK-I6-02** | Schemas hosted at public URL `schema.neuroedge.dev` | FR-GOV-01, FR-GOV-02 | V3 | ⏳ Not started | domain · `schemas/` |
| **TSK-I6-03** | Video demo of four packages and Blueprint on `sim`, `linux`, and Box-3 | FR-DX-06 | V3 + V2 | ⏳ Not started | `README.md` |
| **TSK-P2-04** | Network MCP with mTLS + OAuth 2.1 authentication | NFR-SEC-09, FR-CLI-12 | V1 | ✅ 2026-10-04 | `python/neuroedge/mcp_http.py` |
| **TSK-I6-05** | Freeze Gated Tool Profile and `board.v1` contracts | FR-MDL-10, FR-GOV-01, FR-GOV-02, FR-HAL-02 | V1 | ✅ 2026-10-04 | RFC-0015 · `schemas/` |
| **TSK-I6-06** | Public Python surface `docs/spec/python_api.md` | FR-DX-02, FR-GOV-03 | V1 | ✅ 2026-10-03 | `python/neuroedge/__init__.py` |
| **TSK-I6-07** | External process facts RFC (RFC-0014) | FR-MDL-04, FR-MDL-10 | V1 | ✅ 2026-10-04 | `docs/rfc/0014-du-kien-tu-tien-trinh-ngoai.md` |

**Exit criteria I6:**

- [x] **Criterion 1:** Gitleaks scans entire repo history with 0 findings.
- [x] **Criterion 2:** Public repository; README and CONTRIBUTING link to correct repo.
- [ ] **Criterion 3:** `pip install neuroedge` from PyPI executes `gate lint` and `trace validate`.
- [ ] **Criterion 4:** `schema.neuroedge.dev` serves all schemas in `schemas/`.
- [ ] **Criterion 5:** README includes video demo of four packages and Blueprint across three targets.
- [ ] **Criterion 6:** Opt-in telemetry active, first-run notice displayed; measures B1, B4, B5.
- [ ] **Criterion 7:** MCP client on external machine communicates via Streamable HTTP + OAuth 2.1 + mTLS.
- [x] **Criterion 8:** Gated Tool Profile, `board.v1` version, and error codes committed to `schemas/`.
- [x] **Criterion 9:** Public Python surface functional, external projects succeed importing only neuroedge.
- [x] **Criterion 10:** External process facts RFC approved.

### 4.8 I7 — v1.0

| | |
|:---|:---|
| **Goal** | v1.0 = MVP launch (Q-52, Q-77): satisfies all PRD §11.1 criteria |
| **Entry conditions** | — |
| **Measurement signals** | PRD §11.1 |
| **Assignee** | V2, V6, V1, V3 |

OTA prototyped first on QEMU (Q-39). Real network download and Secure Boot require physical board.

| Task code | Work item | PRD requirement | Owner | Status | Deliverable (artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-S6-01** | Device-level dual-partition A/B OTA | FR-OTA-01 | V2 | ✅ 2026-09-26 | `targets/esp32s3/components/ne_ota/` |
| **TSK-S6-02** | Automatic rollback upon boot loop detection | FR-OTA-02 | V2 | ✅ 2026-09-26 | `targets/esp32s3/components/ne_ota/` |
| **TSK-S6-03** | On-chip RSA-3072 firmware signature verification | FR-OTA-03 | V2 | 🟡 QEMU update portion complete; awaiting Secure Boot eFuse | `targets/esp32s3/components/ne_ota/` |
| **TSK-S6-04** | Flash firmware from any open HTTP endpoint | FR-OTA-04 | V2 | ✅ 2026-09-26 | `targets/esp32s3/components/ne_ota/` |
| **TSK-S6-05** | Secure boot, flash encryption, physical microphone disconnect button | NFR-SEC-02, NFR-SEC-03 | V2 | ⏳ Not started | `targets/esp32s3/security/` |
| **TSK-S6-06** | 24-hour stress testing | NFR-RES-01, A6 | V3 | ⏳ Not started | `tests/stress/` |
| **TSK-S6-07** | Publish public JSON Schema and compliance test suite | FR-GOV-01, FR-GOV-03, FR-TRC-10, A9 | V1 | ⏳ Not started | `schemas/`, `fixtures/compliance/` |
| **TSK-S6-08** | Complete documentation, examples, illustrative videos | FR-DX-05, FR-DX-06, A8 | V3 | ⏳ Not started | `docs/`, `examples/` |
| **TSK-W0-01** | Acceptance criteria for NFR-SEC-02→06, 08 | NFR-SEC | V1 | ⏳ Not started | `neuroedge-prd.md` Appendix A.3 |
| **TSK-W2-07** | SBOM attached to release, attestation, pinned Action SHAs | — | V3 | ✅ 2026-09-26 | `.github/workflows/release-pypi.yml` |
| **TSK-I7-01** | MECE review of v1.0 FRs lacking tasks | FR-TGT-05, FR-TGT-07, FR-DX-07, FR-CLI-08 | V1 + V3 | ⏳ Not started | `neuroedge-prd.md` |
| **TSK-I7-02** | Official measurement of A1 (10 users) and A9 (third party) | FR-DX-01, FR-GOV-01 | V3 | ⏳ Not started | `docs/reports/` |

**Exit criteria I7 — v1.0 release gate:**
Satisfies all PRD §11.1 criteria (A11 dropped along with Lab per Q-77):

- [ ] **A1** — Time-to-first-value
- [ ] **A2** — Environmental parity (`verify --targets sim,linux,esp32s3`)
- [ ] **A3** — No shortcuts to actuators
- [ ] **A4** — Fail-closed (network loss evaluated via local fallback)
- [ ] **A5** — Safe gate inheritance
- [ ] **A6** — 24-hour microcontroller stability (gate, primitives, interconnect; non-voice — Q-77)
- [ ] **A7** — Valid traces
- [ ] **A8** — Documentation
- [ ] **A9** — Public schemas
- [ ] **A10** — Complete primitives across three targets (four extended packages)
- [ ] **A12** — Sample kit constructible in one day

---

## 5. Developer Beta and branch points (I8)

### 5.1 I8 — Developer Beta

| | |
|:---|:---|
| **Goal** | 50–100 external developers use `1.0.x`; measure B1–B5 and select branch |
| **Entry conditions** | — |
| **Measurement signals** | B1–B5 (§5.5) |
| **Assignee** | Whole team |

| Task code | Work item | PRD requirement | Owner | Status | Deliverable (artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-I8-01** | B1–B5 report and branch recommendations (§5.6) | FR-TEL-01 | team lead | ⏳ Not started | a `Q-N` recording chosen branch |

**Exit criteria I8:** B1–B5 measured and recorded in §5.5; a `Q-N` records chosen branch per §5.6.

### 5.2 Operating principles

> **Freeze new features on the `1.0.x` line** (R12, Q-39). Fix only 10-minute blockers and safety defects.

### 5.3 Effort distribution

| Focus | Ratio | Assignee |
|:---|:---:|:---:|
| 1:1 support via Discord and GitHub | 50% | Whole team |
| Documentation refinement based on real obstacles | 25% | V3 |
| Blocker fixes | 20% | V1, V2 |
| Metric measurement and synthesis | 5% | Team lead |

### 5.4 User recruitment targets

| Milestone | Cumulative | Channels |
|:---:|:---:|:---|
| Upon launch | 10 | Home Assistant / ESPHome community makers (U1, Q-72) |
| +1 week | 25 | Technical articles with demo videos |
| +2 weeks | 50 | Home Assistant, ESPHome, ESP32 forums (U5) |
| +4 weeks | 50–100 | Organic accumulation |

### 5.5 Indicators to measure in Beta

Thresholds in PRD §11.2 (B1–B8) and §11.1 (A1); only track status and record measured values (Q-72).

| Code | Metric | Status | Measurement source |
|:---:|:---|:---:|:---|
| **B1** | External dev runs agent on `sim` | ⏳ Not started | FR-TEL-01 (TSK-S3-09) |
| **B2** | External dev flashes physical hardware | ⏳ Not started | FR-TEL-01 (TSK-S3-09) |
| **B3** | Community-contributed gate (Q-41) | ⏳ Not started | Public repo |
| **B4** | Retention and extension rate of default gate tests | ⏳ Not started | Telemetry (TSK-S3-09) |
| **B5** | `sim` → hardware conversion rate | ⏳ Not started | FR-TEL-01 (TSK-S3-09) |
| **A1** | TTFV measured across 10 independent users | ⏳ Not started | TSK-I7-02 |
| **B6** | 8-week gate — external user independently installs Blueprint (Q-72) | ⏳ Not started | TSK-I2e-09 |
| **B7** | 8-week gate — runs continuously for 2 weeks on G2/G3 | ⏳ Not started | TSK-I2d-07 |
| **B8** | 8-week gate — maker seeks to sell Blueprint | ⏳ Not started | TSK-I2e-10 |

### 5.6 Branch points

**Prior to Beta — 8-week demand gate (Q-72):**
- **Passes B6, B7, B8:** Second Blueprint; paid Hub (FR-BP-10); revisit v1.0 scope; open I3 → I7.
- **Passes B6, B7; misses B8:** Retain I2d, I2e as personal tools; do not launch paid Hub; seek alternative revenue; open I3 → I7.
- **Misses B6 or B7:** Halt new features in loops ② ③; pivot market segment before writing further code.

**Post-Beta:**
| Branch | Conditions | Actions |
|:---|:---|:---|
| **Branch A — Expansion** | Meets B1, B2 (Q-41) | Open NeuroEdge Cloud (I2f) if not yet opened; revisit items in §6 using Beta metrics |
| **Branch B — 4–6 week extension** | Meets 1 criterion, other criterion ≥ 60% | Maintain feature freeze, focus on weaker criterion |
| **Branch C — Re-evaluation** | Meets neither criterion / < 60% | Halt commercial roadmap, conduct in-depth interviews with 20 users |

The most critical indicator is B2 (10 external users flash physical hardware).

---

## 6. Removed from roadmap (Q-77)

Q-77 (2026-10-12) removed everything from the roadmap that does not serve the current direction: makers and homes, command via chat, brain as commodity, spinal cord at home, Blueprints (Q-72, Q-74, Q-76). No information was destroyed: existing code remains unchanged and runs tests; legacy designs can be viewed via `git show 6670553:roadmap/neuroedge-roadmap.md`. Re-opening any item requires a new `Q-N` with metric evidence for the re-opening trigger.

| Removed | Rationale | Re-opening trigger |
|:---|:---|:---|
| **I4, I5 — Voice on host and on Box-3** | Core narrative is chat; XiaoZhi, ESP-Claw, and Home Assistant Voice cover voice. Voice code on host (FSM, STT/TTS, `run --mic`) preserved; the laptop voice demo `demo/i4-thoai-laptop/` was deleted on 2026-10-16 (git history) | ≥ 3 Blueprint testers request voice control |
| **I4a, I5a — NeuroEdge Lab** | Contract authoring via MCP is handled by the standard tool suite (TSK-I2d-23) and user's existing MCP clients; Q-88 also moved TSK-I2d-18 (Lab loop ①) and the Lab-only N-tasks still listed in I2d to the table below | Testers cannot author mission contracts independently using the standard tool suite |
| **Third-party target surface expansion** (V1a, TSK-I2c-13, I2c-17) | Paused since Q-72; commodity boards and Arduino (Q-75) address real needs | Third party requests new target port |
| **I9 — Self-hosted provider and Fleet OS** | Q-75: fleet management deferred until demand arises; LiteLLM and brain (Q-76) handle LLM calls | Paying customer requests managing ≥ 20 devices |
| **I10 — Registry, metering, sandbox** | Blueprint Hub (I2e) serves as distribution channel | Static Hub proves insufficient for volume of real Blueprints |
| **I13 — Community porting kit** | Commodity boards and Arduino library (I3a) address needs | External contributor requests tier-3 board port |
| **I14 — Tiered robotics** (ROS 2, Nav2, RP2350, black channel) | Robotics market, not smart home; Pi ↔ ESP32 interconnect already in I3a (Q-75), home mesh in I2f. The draft node RFC (`docs/rfc/draft-rfc-node-giao-thuc-dieu-phoi.md`) was deleted on 2026-10-16; recover it from git history | Committed robotics team tests platform |
| **I16 Jetson, I17 multimodal, I18 device ecosystem** | Zero demand signals; I18 depends on I9, I10 | Measurable post-Beta demand |
| **Track 4 (AURA), Track 5 (Monetized marketplace)** | Out of scope; paid Blueprint Hub follows distinct path after demand gate (Q-72) | Per PRD §14 |

### Tasks of removed items

One row per task is preserved so code and docs cross-references remain traceable; status reflects final state prior to Q-77.

| Task code | Work item | PRD requirement | Owner | Status | Deliverable (artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-S2-07** | Canonical specification of conversational state machine | FR-PER-02, FR-PER-03 | V1 | ⏸ Removed from roadmap (Q-77) — completed 2026-09-25 | `docs/spec/voice_fsm.md` |
| **TSK-S3-10** | Compliance test vector suite for voice FSM | FR-CI-07, FR-TGT-04 | V1 | ⏸ Removed from roadmap (Q-77) — completed 2026-09-25 | `fixtures/compliance/voice/` |
| **TSK-S3-11** | Python implementation of conversational state machine | FR-PER-02→05 | V1 | ⏸ Removed from roadmap (Q-77) — completed 2026-09-25 | `python/neuroedge/perception/` |
| **TSK-S3-13** | ASR/TTS cloud provider integration for `sim` and `linux` | FR-MDL-09, FR-PER-07 | V1 | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/perception/providers/` |
| **TSK-S5-08** | `audio.in` / `audio.out` on `linux` via PipeWire/sounddevice | FR-TGT-02, FR-PER-01 | V2 | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/hal/linux.py` |
| **TSK-I4-01** | Local command fallback and host wake-word | FR-PER-01, FR-MDL-03 | V1 | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/perception/providers/wake.py` |
| **TSK-I4-02** | Configurable `SystemOne` swap | FR-MDL-04 | V1 | ⏸ Removed from roadmap (Q-77) — completed 2026-09-26 | `python/neuroedge/models/providers/systemone_api.py` |
| **TSK-I4-03** | Per-leg latency and System 1 / System 2 ratio in traces | FR-ACE-06, FR-TEL-03, NFR-OBS-02 | V1 | ⏸ Removed from roadmap (Q-77) — completed 2026-09-26 | `python/neuroedge/engine/latency.py` |
| **TSK-I4-04** | Real-time live voice session on laptop (`run --mic`) | FR-PER-01, FR-PER-02, FR-PER-07 | V1 | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/hal/audio_live.py` |
| **TSK-N0-01** | Q-71 entry for NeuroEdge Lab via MCP | — | V2 | ⏸ Removed from roadmap (Q-77) — completed 2026-10-10 | `neuroedge-prd.md` §15 |
| **TSK-N0-04** | Threat model update for lab actions and MCP | NFR-SEC-09 | V2 | ⏸ Removed from roadmap (Q-77) — completed 2026-10-10 | `docs/spec/threat_model.md` §2c |
| **TSK-N0-05** | Approval workflow for `-draft` draft gates via PR | FR-GATE-* | V2 | ⏸ Removed from roadmap (Q-77) | `CONTRIBUTING.md` §3 |
| **TSK-N0-06** | Extend Q-11 for OFL-1.1 fonts and IBM Plex NOTICE entry | — | V2 | ⏸ Removed from roadmap (Q-77) | `neuroedge-prd.md` Q-11 · `NOTICE` |
| **TSK-N1-01** | `lab_pulse` sample action + gate limiting `duration_ms ≤ 2000` | FR-MDL-10 | V2 | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/lab/` |
| **TSK-N1-03** | `neuroedge build --release` rejects when `[lab] enabled` | FR-CLI-02 | V2 | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/cli/main.py` |
| **TSK-N1-06** | `board show --lab` and `lab_board` tool verifying pin allow-list | FR-HAL-05 | V2 | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/cli/main.py` |
| **TSK-N1-07** | B-1 boundary test scanning AST forbidding `lab/` from calling HAL | — | V2 | ⏸ Removed from roadmap (Q-77) | `python/tests/test_lab_boundary.py` |
| **TSK-N1-08** | `lab_read` on `digital.in` primitive | FR-HAL-01 | — | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/lab/` |
| **TSK-N3-01** | Bus scan via read-byte, read chip ID, no heuristics | FR-HAL-01 | — | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/hal/` |
| **TSK-N3-02** | I2C test on `i2c-stub` + `lm75`: device, NACK, timeout | FR-TGT-02 | — | ⏸ Removed from roadmap (Q-77) — in progress: chip detected passed; empty bus remaining | `python/tests_linux/test_i2c_read.py` |
| **TSK-N4-01** | Workbench notebook recording pin roles and chip IDs | — | — | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/lab/` |
| **TSK-N4-02** | `lab_board_draft` tool accepting new board profiles | FR-HAL-05 | — | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/hal/board.py` |
| **TSK-N4-03** | MCU-specific pin warnings (strapping, flash, PSRAM) | — | — | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/lab/` |
| **TSK-N5-04** | Draft PR prints verbal `gate explain` alongside diff | — | — | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/lab/` |
| **TSK-N5b-01** | Queue oldest asks first, default focus on Cancel | — | — | ⏸ Removed from roadmap (Q-77) | `viz/assets/ui.js` |
| **TSK-N5b-02** | SSE disconnection displays yellow banner, dims devices | — | — | ⏸ Removed from roadmap (Q-77) | `viz/assets/ui.js` |
| **TSK-N5b-03** | Active pins display remaining duration, per-pin timeline | — | — | ⏸ Removed from roadmap (Q-77) | `viz/assets/ui.js` |
| **TSK-N5b-04** | Color envelope ruler by window percentage from `board.v1` | — | — | ⏸ Removed from roadmap (Q-77) | `viz/assets/ui.js` |
| **TSK-N5b-05** | 4-color badge verdict cards, click opens `gate explain` | — | — | ⏸ Removed from roadmap (Q-77) | `viz/assets/ui.js` |
| **TSK-N5b-06** | Tab titles flag pending confirmations, rewind preserves active ask/live state | — | — | ⏸ Removed from roadmap (Q-77) | `viz/assets/ui.js` |
| **TSK-N5b-07** | Restyle full sim page, bundle IBM Plex font | — | — | ⏸ Removed from roadmap (Q-77) | `viz/assets/ui.css` |
| **TSK-I4a-01** | NeuroEdge Lab covering four packages for MCP clients | FR-MDL-10, FR-DX-01 | V2 + V7 | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/lab/` |
| **TSK-I2d-18** | Lab loop ① for mission contracts via MCP tools (`docs/spec/missions.md` MS-LB-01) | FR-DX-10, FR-MSN-13 | V7 | ⏸ Removed from roadmap (Q-77, Q-88) | `python/neuroedge/lab/` |
| **TSK-N1-02** | `[lab] enabled` flag in `agent.toml`, off by default | — | V2 | ⏸ Removed from roadmap (Q-77, Q-88) | `python/neuroedge/lab/` |
| **TSK-N1-04** | Lab call result with `gate explain` to revise commands | FR-MDL-10 | V2 | ⏸ Removed from roadmap (Q-77, Q-88) | `python/neuroedge/lab/` |
| **TSK-N1-05** | Single-step client configuration: `mcp desktop-config --lab` | FR-CLI-12 | V2 | ⏸ Removed from roadmap (Q-77, Q-88) | `python/neuroedge/mcp_desktop.py` |
| **TSK-N5-01** | Tools `lab_draft_write` and `lab_draft_check` (Q-71) | FR-DX-01, FR-DX-10 | — | ⏸ Removed from roadmap (Q-77, Q-88) | `python/neuroedge/lab/` |
| **TSK-N5-02** | Mandatory bidirectional tests (at least one ALLOW and one BLOCK) | FR-CI-* | — | ⏸ Removed from roadmap (Q-77, Q-88) | `python/neuroedge/lab/` |
| **TSK-N5-03** | Malformed proposals return 3-part error, no junk files written | — | — | ⏸ Removed from roadmap (Q-77, Q-88) | `python/neuroedge/lab/` |
| **TSK-N5-05** | `trace export --report` and Markdown `lab_report` tool | FR-TRC-* | — | ⏸ Removed from roadmap (Q-77, Q-88) | `python/neuroedge/cli/main.py` |
| **TSK-N5-06** | `neuroedge lab check` in Action CI on PR | FR-CI-*, FR-DX-10 | — | ⏸ Removed from roadmap (Q-77, Q-88) | `python/neuroedge/lab/` |
| **TSK-N6-04** | Tool `lab_trigger_check`: evaluate draft trigger declarations | FR-DX-10 | — | ⏸ Removed from roadmap (Q-77, Q-88) | `python/neuroedge/lab/` |
| **TSK-S5-01** | Integrate WebRTC AEC, libfvad (VAD), Opus streaming | FR-PER-06 | V2 | ⏸ Removed from roadmap (Q-77) | `targets/esp32s3/audio/` |
| **TSK-S5-02** | Port audio capture/playback path, no on-chip STT/TTS | FR-PER-01 | V2 | ⏸ Removed from roadmap (Q-77) | `targets/esp32s3/drivers/audio_path.c` |
| **TSK-S5-03** | C/C++ implementation of voice FSM per `voice_fsm.md` | FR-PER-02, FR-PER-03, FR-PER-05 | V1 + V2 | ⏸ Removed from roadmap (Q-77) | `targets/esp32s3/fsm/voice_fsm.c` |
| **TSK-S5-04** | Revoke unexecuted actuator commands upon barge-in | FR-PER-02 | V1 + V2 | ⏸ Removed from roadmap (Q-77) | `targets/esp32s3/fsm/actuator_abort.c` |
| **TSK-S5-05** | Memory optimization per Q-3 budget | NFR-RES-01, NFR-RES-02 | V2 | ⏸ Removed from roadmap (Q-77) | `targets/esp32s3/sdkconfig.defaults` |
| **TSK-S5-06** | Audio streaming client to cloud provider | FR-PER-07, FR-GW-04 | V2 | ⏸ Removed from roadmap (Q-77) | `targets/esp32s3/audio/provider_client.c` |
| **TSK-S5-07** | Local fallback on `esp32s3` (MultiNet or TFLite Micro) | FR-MDL-03, FR-ACE-03, NFR-RES-01 | V2 | ⏸ Removed from roadmap (Q-77) | `targets/esp32s3/fallback/` |
| **TSK-N7-01** | On-chip lab action + gate via C walker and token ledger | — | — | ⏸ Removed from roadmap (Q-77) | `targets/esp32s3/` |
| **TSK-N7-03** | Selective porting from ESP-Claw to ESP32-S3 | — | — | ⏸ Removed from roadmap (Q-77) | `targets/esp32s3/` |
| **TSK-K2-01** | Self-hosted provider: unified endpoint, credentials, key rotation | FR-GW-01, FR-GW-02 | V4 | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/models/providers/auth.py` |
| **TSK-K2-02** | Self-hosted provider: multi-LLM routing, failover, quotas | FR-GW-03, FR-GW-05, FR-TEL-06 | V4 | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/models/providers/routing.py` |
| **TSK-K2-03** | Self-hosted provider: edge protocols, unified traces | FR-GW-04, FR-GW-06, FR-GW-07 | V4 | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/models/providers/traces.py` |
| **TSK-K2-04** | Fleet: device identity and certificate provisioning | FR-FLT-01 | V4 | ⏸ Removed from roadmap (Q-77) | `services/fleet/provisioning.py` |
| **TSK-K2-05** | Fleet: device inventory, health monitoring, dashboard | FR-FLT-03, FR-FLT-06 | V4 | ⏸ Removed from roadmap (Q-77) | `services/fleet/inventory.py` |
| **TSK-K2-06** | Fleet: remote sync for configuration, secrets, and gates | FR-FLT-04 | V4 | ⏸ Removed from roadmap (Q-77) | `services/fleet/config_sync.py` |
| **TSK-K2-07** | Fleet: canary OTA orchestration 1% → 10% → 100% | FR-FLT-02 | V4 | ⏸ Removed from roadmap (Q-77) | `services/fleet/canary.py` |
| **TSK-K2-08** | Fleet: automatic crash trace ingestion to repository | FR-FLT-05 | V4 | ⏸ Removed from roadmap (Q-77) | `services/fleet/trace_collector.py` |
| **TSK-K2-09** | Device certificate revocation | NFR-SEC-05 | V4 | ⏸ Removed from roadmap (Q-77) | `services/fleet/` |
| **TSK-K3-01** | Stable identity for devices, agents, gates | FR-REG-05 | V4 | ⏸ Removed from roadmap (Q-77) | `services/registry/identity.py` |
| **TSK-K3-02** | Metering system for agent calls and gate evaluations | FR-REG-06, FR-TEL-04 | V4 | ⏸ Removed from roadmap (Q-77) | `services/metering/engine.py` |
| **TSK-K3-03** | Manifest and SemVer versioning standard | FR-REG-02, FR-GATE-10 | V4 | ⏸ Removed from roadmap (Q-77) | `schemas/manifest.v1.json` |
| **TSK-K3-04** | Free public Gate repository | FR-REG-01 | V4 | ⏸ Removed from roadmap (Q-77) | `services/registry/oci_store.py` |
| **TSK-K3-05** | Permissions and sandbox mechanisms | FR-REG-07 | V4 | ⏸ Removed from roadmap (Q-77) | `services/registry/sandbox.py` |
| **TSK-K3-06** | Community provider adapter registry | FR-REG-08 | V4 | ⏸ Removed from roadmap (Q-77) | `services/registry/adapters.py` |
| **TSK-W2-04** | Gate signing and on-device signature verification (OCI/ORAS); trace signing | FR-REG-04 | V4 | ⏸ Removed from roadmap (Q-77) | `services/registry/` |
| **TSK-P1-01** | Language-independent compliance vector suite packaged externally | FR-GOV-03 | V1 | ⏸ Removed from roadmap (Q-77) | `fixtures/compliance/portable/` |
| **TSK-P1-02** | HAL porting guide: minimal contract, self-certification | FR-TGT-08, FR-GOV-03 | V3 | ⏸ Removed from roadmap (Q-77) | `docs/porting/` |
| **TSK-P1-03** | Reference port scaffold for non-ESP32 microcontrollers | FR-TGT-08 | V3 | ⏸ Removed from roadmap (Q-77) | `targets/_template/` |
| **TSK-P1-04** | Tier-3 accreditation process: contributor self-testing and publication | FR-TGT-08 | V3 | ⏸ Removed from roadmap (Q-77) | `docs/porting/tier3.md` |
| **TSK-P1-05** | `neuroedge board check <file>` pass/fail validation against tier | FR-TGT-08 | V1 | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/cli/` |
| **TSK-W2-01** | mTLS or PSK between Pi and nodes | NFR-SEC-04 | V2 | ⏸ Removed from roadmap (Q-77) | firmware · `python/` |
| **TSK-W2-03** | TPM for Pi (`linux`) augmenting Secure Boot | NFR-SEC-02, NFR-SEC-03 | V2 | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/hal/linux.py` |
| **TSK-W3-01** | Zenoh-pico ↔ Pi spike on ESP32-S3 and RP2350 (Q-36) | — | V2 | ⏸ Removed from roadmap (Q-77) | `docs/reports/` |
| **TSK-W3-02** | Node RFC: multi-node, wire, black channel — extension of minimal RFC TSK-I3a-06 | FR-TGT-08 | V1 | ⏸ Removed from roadmap (Q-77) | `docs/rfc/` |
| **TSK-W3-03** | Black channel layer: wrapper + watchdog + replay protection | NFR-SEC-09 | V1 + V2 | ⏸ Removed from roadmap (Q-77) | `python/` + firmware |
| **TSK-W3-04** | Unified multi-node traces (Option A, Q-32) | FR-TRC-05 | V1 | ⏸ Removed from roadmap (Q-77) | `fixtures/compliance/multinode/` |
| **TSK-W3-06** | `verify` for node clusters; divergence → NE4002 | FR-CI-07 | V1 | ⏸ Removed from roadmap (Q-77) | CLI + CI |
| **TSK-W3-07** | Port RP2350 as second node (Q-33): C HAL, C99 walker | FR-TGT-08 | V2 | ⏸ Removed from roadmap (Q-77) | `targets/rp2350/` |
| **TSK-P2-05** | MCP for MCU via gateway; MCU independently evaluates gate | FR-GW-01, FR-MDL-10 | V1 + V2 | ⏸ Removed from roadmap (Q-77) | `docs/spec/tool_calling.md` §8 |
| **TSK-W4-01** | ROS 2 bridge at gate boundary (`linux`) + Nav2 (Q-34) | FR-MDL-10 | V1 | ⏸ Removed from roadmap (Q-77) | `python/` |
| **TSK-W4-07** | Mobile robot safety RFC and C6 with robot buyers | — | V1 + team lead | ⏸ Removed from roadmap (Q-77) | `docs/rfc/` |
| **TSK-V2-01** | Port HAL to Jetson Orin via JetPack | FR-TGT-08, FR-HAL-01 | V5 | ⏸ Removed from roadmap (Q-77) | `targets/jetson/hal/` |
| **TSK-V2-02** | GPU-accelerated vision pipeline, preserving abstractions | FR-MDL-04 | V5 | ⏸ Removed from roadmap (Q-77) | `targets/jetson/vision/` |
| **TSK-V2-03** | `neuroedge verify` for `jetson` on verdict domain | FR-CI-07, FR-TGT-08 | V1 | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/cli/main.py` |
| **TSK-V2-04** | `jetson-orin-nano` board profile | FR-HAL-02 | V5 | ⏸ Removed from roadmap (Q-77) | `boards/jetson-orin-nano.toml` |
| **TSK-V3-01** | Fuse voice, vision, and sensors into single FSM | FR-PER-01→05 | V1 + V5 | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/perception/fusion/` |
| **TSK-V3-02** | Extend compliance test suite for multimodal streams | FR-CI-07 | V1 | ⏸ Removed from roadmap (Q-77) | `fixtures/compliance/multimodal/` |
| **TSK-V3-03** | Multimodal gate | FR-GATE-03 | V1 | ⏸ Removed from roadmap (Q-77) | `schemas/gate.v2.json` |
| **TSK-V3-04** | Visual evidence gate semantics RFC | FR-GATE-03 | V1 | ⏸ Removed from roadmap (Q-77) | `docs/rfc/` |
| **TSK-P2-01** | Adapter repository and community HAL ports on Registry | FR-TGT-08 | V3 | ⏸ Removed from roadmap (Q-77) | `services/registry/ports.py` |
| **TSK-P2-02** | Adapter compliance status visible on Fleet Dashboard | FR-FLT-03 | V3 | ⏸ Removed from roadmap (Q-77) | `services/fleet/compliance_view.py` |
| **TSK-P2-03** | Free hardware certification, self-tested | FR-GOV-03 | V3 | ⏸ Removed from roadmap (Q-77) | `docs/porting/certification.md` |
| **TSK-I2c-13** | Plugin template and 30-minute plugin authoring guide | FR-EXT-02, FR-DX-04 | V3 | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/templates/` |
| **TSK-I2c-17** | `neuroedge-muse` bridge test authored in dedicated repository | FR-EXT-02, FR-EXT-04 | V3 + tester | ⏸ Removed from roadmap (Q-77) | `neuroedge-muse` repo |
| **TSK-V1a-02** | Open `target` enum in two schemas | FR-TGT-08 | V1 | ⏸ Removed from roadmap (Q-77) | `schemas/board.v1.json` · `schemas/trace.v1.json` |
| **TSK-V1a-03** | Core-owned machine-readable `TARGET_TIERS` | FR-TGT-08, FR-HAL-05 | V1 | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/hal/board.py` |
| **TSK-V1a-04** | Tighten three test invariants by tier | FR-HAL-04, FR-TGT-08 | V1 | ⏸ Removed from roadmap (Q-77) | `python/tests/test_boards.py` |
| **TSK-V1a-05** | CLI: `board validate`, `board show` | FR-HAL-05 | V1 | ⏸ Removed from roadmap (Q-77) | `python/neuroedge/cli/main.py` |
| **TSK-V1a-06** | Update `unknown_target.json` counter-example corpus | FR-TRC-08 | V1 | ⏸ Removed from roadmap (Q-77) | `fixtures/traces/expected_errors.yaml` |

## 7. Post-Beta extension directions

No increments remain post-I8 (Q-77). Legacy directions and re-opening triggers are documented in §6.

---

## 8. Outside roadmap

### 8.1 External dependencies

None remaining (Q-77): Track 4 and Track 5 moved to §6.

### 8.2 Deferred tasks not yet assigned to an increment

| Task code | Work item | PRD requirement | Owner | Status | Deliverable (artifact) |
|:---:|:---|:---|:---:|:---:|:---|
| **TSK-S2-06** | Evaluate `allow_when` on CEL foundation and compile gate for device (§3.8, Q-9) | FR-GATE-03 | V1 | ⏸ Deferred — does not yet belong to any increment (`TODOS.md` #42) | Mapping format sufficient for wedge; CEL compiles down to same decision tree (Q-9) |

---

## 9. Scope-cut ladder

MVP does not cut scope (Q-52): if slipping, shift dates alongside PR with evidence (R5). MVP scope is defined post-Q-77.

### 9.1 Strictly non-cuttable

- HAL capability contracts; Gate Engine and fail-closed behavior; trace schemas and record/replay; Golden Reference.
- `sim` as a real target (not a mock); safe gate inheritance principle.
- MVP scope (Q-52, Q-77): four extended primitive packages across three targets, sample kits, 24/7 missions, brain via MCP, Blueprint.
- Q-77 removed voice, Lab, third-party target expansion, and all post-Beta increments (§6); re-opening requires a new `Q-N`.

### 9.2 Voice no longer in v1.0

Q-44 previously mandated voice on ESP32-S3 for v1.0; Q-77 removed this requirement. Existing voice code is preserved.

### 9.3 In-increment cut ladders

No increments remain post-Beta (Q-77), so no cut ladders remain.

---

## 10. Decision schedule

The decision log is [PRD §15](neuroedge-prd.md#15-decision-log) — content, rationale, and alternatives for all `Q-N` decisions are centralized there (single source of truth). When documents diverge, PRD §15 prevails.

### 10.1 Decided decisions

All decided architectural decisions (`Q-N`) are maintained in detail at [PRD §15](neuroedge-prd.md#15-decision-log).

### 10.2 Open decisions and RFCs

| Deadline | Code | Decision | Rationale for deadline | Decider | Status |
|:---:|:---:|:---|:---|:---:|:---:|
| Before code task of each RFC | Q-72 | Author and approve RFC for `TODOS.md` #58, 5 RFCs for I2d, and `blueprint.v1` for I2e | Without RFCs, no code for new formats | Tech lead | ⏳ Open |
| Before I2d confirmation channel task | Q-73 | Author and approve RFC for verification steps and user-declared multi-step flows (TSK-I2d-20) | Chat approval records share confirmation pathway | Tech lead | ⏳ Open |
| 2026-12-06 demand gate outcome | Q-74 | Open I2f — NeuroEdge Cloud (brain on cloud, subscription) and ESP32 box — or keep ⏸ (§4.3.6) | Opens only if metrics show testers blocked by setup or self-hosting | Product owner | ⏳ Open |
| Before TSK-I2d-11, I2d-12 code | RFC-0019 (PR #133) | Approve the draft RFC for box-signed approval records and the box's own approval bot (Q-83, `docs/spec/missions.md` MS-CH-02, MS-CH-03) | Unblocks TSK-I2d-11, I2d-12 and TC-A-06-1, TC-A-06-2 | Lead engineer | ✅ Approved 2026-10-16 (Q-89) |
| Before TSK-I2d-12 | `TODOS.md` #62 | Chat channel pairing lifecycle: local pairing, revocation, approval ceiling — decided by Q-89 (RFC-0019 §9) | Compromised chat account could approve on owner's behalf | Product owner | ✅ Decided 2026-10-16 (Q-89) |
| Before G3 used for B7/A16 | Q-21, Q-69 | Select G3 tier (emulated ESP32 firmware): Wokwi, QEMU, `esp-emulator` | Q-72 introduces G3 into 8-week gate | Tech lead | ⏳ Open |

*Transitive dependency policy (Q-11):* Copyleft (GPL) dependencies forbidden in core; `licence-obligations` job runs `pip-licenses --fail-on` checking full dependency tree on every PR.

---

## 11. Operating cadence

### 11.1 Recurring cadence

| Frequency | Activity | Starting |
|:---|:---|:---:|
| Daily | 15-minute quick sync | I0 |
| Weekly | Live demo on physical hardware once boards arrive; review §12 early indicators | I0 |
| Nightly | Automated testing on real hardware board | I3 |
| Each increment | Acceptance against exit criteria; one release card, one measurement signal (Q-39) | I0 |
| Each increment | One working demo with UI in `demo/<increment>/` (Q-49) | I1 |

### 11.2 Definition of done

An item is complete only when all 5 conditions are met:
1. Code reviewed and merged.
2. Automated tests in CI, including at least one failing case.
3. Corresponding PRD acceptance criteria met.
4. `--help`, documentation, progress, and changelog updated (`CONTRIBUTING.md` §8).
5. Error messages state full context: what is wrong, why, and how to resolve.

### 11.3 Critical path protection rules

| Rule | Description |
|:---|:---|
| **Schema freeze** | Schema modifications require RFC, approval, and migration plan |
| **No safety debt** | Gate Engine and HAL never merge with "fix later" notes. Tested fail-closed behavior is not debt (Q-17) |
| **Parity divergence is blocker** | `SafetyRegressionError` (NE4002) across targets halts all other work until resolved |
| **Feature freeze in Beta** | `1.0.x` line in I8: fix only 10-minute blockers and safety defects (R12) |

---

## 12. Early indicators and intervention thresholds

| # | Indicator | Yellow threshold | Red threshold | Action upon red |
|:---:|:---|:---|:---|:---|
| **1** | Schema freeze | — | — | Passed at I0 |
| **2** | Memory spike | Remaining < 30% | Insufficient space for 4 packages | Open `Q-N` to replan I3a, reschedule v1.0 |
| **3** | `verify` divergence | 1 diverging case | ≥ 3 diverging cases | Halt feature work, trace architectural root cause |
| **4** | External Dev Beta | 2 weeks < 25 people | 2 weeks < 10 people | Pause recruitment, conduct in-depth interviews with 10 users |
| **5** | B2 hardware flash rate | < 20% B1 | < 10% B1 | Investigate hardware onboarding; signal for Branch C |
| **6** | Action CI adoption | < 40% | < 25% | Review Action CI scaffold and documentation |
| **7** | Blueprint installs (B6) | I2e complete with 0 installs | 2 weeks before gate < 3 people | Meet with individuals to measure install session (TSK-I2e-09), resolve bottlenecks |
| **8** | Continuous G2 runtime (B7) | Longest < 7 days with 3 weeks remaining | Under 2 consecutive weeks | Halt new features, fix G2 runtime (TSK-I2d-16) |
| **9** | Blueprint sales (B8) | 4 weeks zero makers | Still 0 by gate date | Record branch "passes B6, B7; misses B8" (§5.6) |
| **10** | Fish tank LLM cost | ≥ 50% NFR-COST-01 | Exceeds NFR-COST-01 | Add deterministic detectors, lower LLM frequency |

Yellow thresholds discussed in weekly review. Red thresholds trigger immediate action.

---

# Appendices

## Appendix B — Procurement and infrastructure bill of materials

I2d, I2e run on G1, G2 simulation (Q-72); physical hardware purchased later per branch in §5.6.

| Item | Quantity | Needed before | Notes |
|:---|:---:|:---:|:---|
| **ESP32-S3-Box-3** (official reference board) | 2 + 3–6 | Batch 1 / I3 | Memory spike (TSK-S1-10); nightly runner |
| **Raspberry Pi 5** (nightly `linux`, Q-16) | 1 + 2 | Order immediately / I2 | TSK-I2-01, `linux` ARM64 |
| x86-64 Linux machine | 1 | I2 | `linux` target on x86 |
| Flasher and JTAG cables | 2 sets | I3 | Register-level debugging |
| Self-hosted CI runner connected to physical board | 1 | I3 | Mandatory for TSK-S4-05 |
| Domain `schema.neuroedge.dev` | — | I6 | FR-GOV-01, A9 (TSK-I6-02) |
| USB and CSI cameras; Hailo-8 NPU / Coral TPU | 4 + 2 | I2a | `vision.in` image source, acceleration |
| **M5Stack CoreS3** (`esp32s3` board with camera, Q-61) | 2 | Order immediately | TSK-I3a-01, camera for MCU |
| Servos, motor drivers, dedicated power supplies | 2 sets | I2a | Verify `motion.*` (TSK-W1-04) |
| **ESP32-S3-DevKitC-1 N16R8** (commodity board, Q-75) | 2 | I3a | TSK-I3a-08, TSK-I3a-07 (Pi ↔ ESP32) |

## Appendix C — Source repository layout

Detailed structure: [`CONTRIBUTING.md` §6](../CONTRIBUTING.md#6-repository-structure). Four mandatory conventions:
1. `schemas/` is the single source of truth; Python and C generate or validate against it.
2. `fixtures/traces/` shared across all targets, serving as foundation for `neuroedge verify`.
3. `targets/` contains only HAL implementations, zero business logic or safety policies.
4. Provider layer resides in `python/neuroedge/models/providers/`, never in `services/` (CR-1.0).

---

## Appendix D — Wire protocol

Standard transmission channels and audio formats for `record`, `replay`, and voice streaming: [PRD Appendix D.2](neuroedge-prd.md#d2-wire-protocols-and-trace-format).

---
*End of document*
