# NeuroEdge — Product Requirements Document

## NeuroEdge — Where Intent Becomes Physical AI Products: Build, Run Safely, Share, and Sell

*The trust layer: no contract, no action — LLMs think, hard rules hold (Q-30, Q-72).*

**PRD Version:** 1.6
**Release Date:** October 11, 2026 (Q-72)
**Source Documents:** `docs/business/proposal-blueprint-2026-10-11.md` · format specification `docs/spec/core_contracts.md`
**Status:** Draft pending technical approval
**Change History:** `CHANGELOG.md` — this document describes the current state only.
**Target Audience:** Development Engineers · Engineering Managers · QA · Technical Writers · Makers and micro-OEMs selling NeuroEdge Blueprints · OEM Partners

**Document Scope:** Functional and non-functional requirements · Acceptance criteria · Data interface specifications · Milestone release plan · Metrics and measurement requirements
**Out of Scope:** Strategic rationale · Competitive analysis · Financial models (see source documents)

---

## Table of Contents

1. [Product Goals](#1-mục-tiêu-sản-phẩm)
2. [Users and Context of Use](#2-người-dùng-và-bối-cảnh-sử-dụng)
3. [Release Scope](#3-phạm-vi-phát-hành)
4. [Functional Requirements — Execution Core](#4-yêu-cầu-chức-năng--lõi-thực-thi)
5. [Functional Requirements — Action Safety](#5-yêu-cầu-chức-năng--an-toàn-hành-động)
6. [Functional Requirements — Action CI Testing](#6-yêu-cầu-chức-năng--kiểm-thử-action-ci)
7. [Functional Requirements — Developer Experience](#7-yêu-cầu-chức-năng--trải-nghiệm-lập-trình-viên)
8. [Functional Requirements — Commercial Service Layer](#8-yêu-cầu-chức-năng--tầng-dịch-vụ-thương-mại)
9. [Non-Functional Requirements](#9-yêu-cầu-phi-chức-năng)
10. [Data Interface Specifications](#10-đặc-tả-giao-diện-dữ-liệu)
11. [Release Acceptance Criteria](#11-tiêu-chí-nghiệm-thu-phát-hành)
12. [Metrics and Measurement Requirements](#12-hệ-chỉ-số-và-yêu-cầu-đo-đạc)
13. [Dependencies, Risks, and Assumptions](#13-phụ-thuộc-rủi-ro-và-giả-định)
14. [Out of Scope](#14-ngoài-phạm-vi)
15. [Decision Log](#15-sổ-quyết-định)

**Appendices**

- [A — Requirements Traceability Matrix](#phụ-lục-a--ma-trận-truy-vết-yêu-cầu)
- [B — Standard Error Code Catalog](#phụ-lục-b--danh-mục-mã-lỗi-chuẩn)
- [C — Identification and Versioning Conventions](#phụ-lục-c--quy-ước-định-danh-và-phiên-bản)
- [D — Monorepo Structure and Transport Protocols](#phụ-lục-d--cấu-trúc-monorepo-và-giao-thức-truyền-dẫn)

---

## Document Conventions

All codes and symbols used in this document (`FR-*`, `NFR-*`, `P0`–`P2`, `A1`–`A22`, `B1`–`B8`, `C1`–`C8`, `Q-N`, `PF-N`, `R-N`, `U`/`J`, `§x.y`…) are decoded in **[`docs/user/thuat-ngu.md`](../docs/user/thuat-ngu.md)** — the single source of truth, with full definitions.

The keywords **MUST**, **SHOULD**, **MAY** are to be interpreted as described in RFC 2119.

---

## 1. Product Goals

### 1.1 The Problem

No existing tool tests the physical behavior of an AI agent **before** the device operates in the field. When a physical agent makes a wrong decision, the motor has already spun, the relay has closed, the door latch has unlocked — these actions are irreversible. An in-home voice assistant mixes both kinds of behavior in a single conversation: an incorrect knowledge-base answer or news update can be corrected; turning off the light while someone is still on the stairs cannot — the product must separate those two paths (`docs/architecture/vi/00-overview.md` §1).

Q-72 expands the problem from a single command to the entire lifecycle of an AI-enabled device. Anyone who wants such a device faces three barriers: **build** (from intent to kit, wiring, firmware, and gates is embedded specialist work), **run** (delegating tasks by voice, having something watch the device all day, proactively alerting when issues arise, with predictable LLM bills), and **sell** (a maker builds a working device but has no way to package it as a product for others). The biggest barrier to selling is the **trust gap**: buyers are strangers who do not read code and need proof that the device remains safe when the AI fails — MCU-level gates, human-locked contracts, replayable traces. The existing contract layer answers that exact question; Q-72 turns it into a passport for sharing and selling, rather than a standalone product.

Six questions current tools cannot answer:

| # | Câu hỏi | Yêu cầu đáp ứng |
|:---:|:---|:---|
| 1 | After changing a prompt, does the agent still refuse to unlock for unauthenticated persons? | §6 — Action CI with Golden Reference baselines |
| 2 | When switching AI models, do gate verdicts and GPIO signals regress? | §6 — Assert on gate verdicts, do not assert on LLM text |
| 3 | Given identical inputs, do all targets yield identical verdicts? | §4 — Target equivalence principle |
| 4 | If I say "trông bể cá giúp tôi" (watch over my fish tank) — how do I get a working device without knowing firmware? | §5.4 — Mission contracts (FR-MSN); §7.1 — Kits and NeuroEdge Lab (FR-DX-09, FR-DX-10) |
| 5 | Who watches the device all day and alerts me to strange trends without exceeding my set LLM bill? | §4.5 — Operator agent (FR-AGT); §5.5 — Chat channels (FR-CH) |
| 6 | How can I sell an AI device to strangers while proving it is safe when the AI fails? | §7.4 — NeuroEdge Blueprint (FR-BP); §8.4 — Revenue streams |

### 1.2 Product Manifesto

> **NeuroEdge — where intent becomes physical AI products: build, run safely, share, and sell** *(Q-72)*. Three loops: ① **build** — from a single sentence to kit, firmware, gates, and test runs on `sim`; ② **run** — operator agents execute mission contracts all day, instant reflex on-device, proactive alerts and proposals via chat channels; ③ **share and sell** — packaged into evidence-backed NeuroEdge Blueprints that others install with a single command. **LLMs think, hard rules hold.**
>
> **The trust layer — "Contracts into Physical AI" (Q-30).** No contract, no action: every physical action by an AI agent (door latches, relays, valves, lights) heading to the physical world must pass through a **typed, versioned safety contract** — the innermost guard layer sitting directly atop the 5 HAL primitives. Contracts are tested automatically in CI via replay + assertions on gate verdicts and pin states, executing consistently across all targets — from developer laptops to $5 edge microcontrollers. This layer is what allows strangers to trust an AI device built by another maker.

> **Open, with transparency (Q-73).** NeuroEdge does not decide for users how to verify or design interaction flows; any method can be implemented, each carrying a risk label. **One chat window for the entire mesh (Q-74).** Users only need to chat: the "brain" (conversation, LLM, planning) may run on optional NeuroEdge Cloud and orchestrate multiple devices, multiple homes, multiple people; the "spinal cord" (rules, reflexes, approval checks) remains strictly on the home box and on each chip — cloud orchestrates but holds no supreme authority.

### 1.3 Product Goals

Order per Q-72: **M7 → M8 → M9** (the first Blueprint completing all three loops in simulation) comes first; M1 → M4 and M6 remain; **M5** (large fleet) comes after the 8-week demand gate.

| # | Mục tiêu | Chỉ số nghiệm thu |
|:---:|:---|:---|
| **M7** | A single sentence into a working, contracted device *(Q-72)* | From the phrase "tôi muốn trông bể cá" to an approved mission contract running on `sim`: contradictory contracts rejected before approval, 100% of violating commands blocked (A15, A17) |
| **M8** | Operator agent runs all day, alerts proactively, capped LLM costs *(Q-72)* | Fast-forwarded 30-day scenario: at least one correct trend detection, LLM cost < $2 USD; on network loss or LLM loss, reflexes still hold (A16, A19) |
| **M9** | NeuroEdge Blueprint installs in a single command, and someone wants to sell it *(Q-72)* | External user installs Blueprint on a clean machine and runs on `sim` in < 10 minutes (A14); ≥ 1 maker wants to package and sell their Blueprint (B8) |
| **M1** | External developer runs a gated agent without buying hardware | Median TTFV < 10 minutes across 10 independent users |
| **M2** | All physical actions pass through a testable contract | 100% of actuator commands blocked without a valid gate |
| **M3** | Identical agent source code runs consistently across all targets | `neuroedge verify` achieves 100% across Tier 1 targets: `sim`, `linux`, `esp32s3` |
| **M4** | Field incidents reproducible on developer machines | Download trace and replay successfully in a single command |
| **M6** | Third parties integrate NeuroEdge with a new product or ecosystem without modifying core or waiting for core team *(Q-67)* | A bridge for a previously unsupported ecosystem, written in a separate repository solely from public documentation, passes compliance test suite in **≤ 1 day**; wraps an existing MCP server in **≤ 3 commands** (A13) |
| **M5** | Fleet ops updates large-scale firmware with zero bricked devices *(after 8-week gate — Q-72)* | 1,000 devices / 0 brick incidents |

### 1.4 Non-Goals

| # | Phi mục tiêu | Lý do |
|:---:|:---|:---|
| **N1** | Not becoming an AI model provider | Models are replaceable components (§0.4 principle 4) |
| **N2** | Not competing on driver depth for any single chip family | Left to first-party SDKs (§10.3) |
| **N3** | Not pursuing broad hardware coverage in early stages | Three Tier 1 targets are sufficient to prove equivalence. From Phase 2, coverage expands via target tiers (FR-TGT-08) rather than the core team taking on more boards (§9) |
| **N4** | Not reselling inference tokens as the primary profit margin source | Thin margins, directly competing with model vendors (§0.4 principle 3). Q-72 maintains: users pay for LLMs directly with their own keys (BYOK). Q-74 Step 2 (conditional): NeuroEdge Cloud subscription may bundle tokens, BYOK still retained — amend N4 when unlocking that step |
| **N5** | Not serving as the sole safety guard layer, not a certified safety function | Protection against hazards (fire, overcurrent, dry-run) always belongs to hardware — thermal fuses, overcurrent relays, float switches; NeuroEdge keeps devices operating when the brain is lost and summons humans when choosing between two bad outcomes (Q-38, Q-72) |

### 1.5 Five Invariant Design Principles

All requirements in this document must adhere to the following five principles. Conflict with any principle is grounds for rejecting the requirement.

| # | Nguyên tắc | Hệ quả kỹ thuật ràng buộc |
|:---:|:---|:---|
| **P-1** | Physical actions are typed standard contracts, not arbitrary function calls | HAL rejects any actuator command lacking a passed gate signature. Every path from language to action — offline voice, LLM, MCP client, chat channel, operator agent LLM worker — is a **typed tool call** passing through the same gate (Q-24, `docs/spec/tool_calling.md`). The sole exception is a command **moving toward the safe state** (Q-62). *Pending conditional safety RFC (Q-72):* "safe state" is the actuator's `safe_state` declared in `board.v1` (default `off`), not always off; moving *away from* `safe_state` is the direction gated and limited, so the exception remains symmetric without opening new shortcuts |
| **P-2** | Execution targets are peers | Branching logic by target in agent source code is prohibited. Verification commitment levels are categorized into three target tiers (FR-TGT-08); this technical implication applies equally across all tiers |
| **P-3** | Value centers on product creators: build, sell, and operate devices *(amended by Q-72)* | Non-commercial users get the entire core for free; selling NeuroEdge Blueprints or devices is commercial use (Q-45). Near-term revenue: kit commissions (affiliate, no inventory), Blueprint revenue share, per-device commercial licenses, optional cloud relay; Fleet OS comes later (§8). For enterprise, core safety features are always included in the commercial license, never split into paid add-ons; no revenue stream sits on the safety path |
| **P-4** | AI models are replaceable components — cloud-first, provider-pluggable | All model access passes through the `SystemOne` / `SystemTwo` interface; the default connection standard is the OpenAI API, incompatible providers connect via custom adapters; ASR and TTS are also replaceable providers. Heavy language processing runs on cloud/host, `esp32s3` only captures/plays audio and evaluates gates |
| **P-5** | Network effects from sharing safety policies and extension components | Gates are versioned data files, shareable and inheritable. Provider connection adapters and HAL ports are the second class of shared assets; because they are executable code, they come with dedicated control gates — Conformance Test Suite, permission sandboxing, and build-time capability reconciliation. From Q-67, all external connections are Extension SDK plug points (FR-EXT): third parties connect without modifying core, while safety invariants remain unchanged. From Q-72, the primary shared asset is the **NeuroEdge Blueprint** (FR-BP): builder creates Blueprint → user installs → **consented** operational data sharing improves detectors → better Blueprint → more users, more builders |

---

## 2. Users and Context of Use

### 2.1 Target User Groups

Per Q-72, the initial market is the **global maker community around Home Assistant and ESPHome** (U1), followed by makers turning into micro-manufacturers (U5); U2 and U3 become secondary.

| Mã | Nhóm | Bối cảnh | Nhu cầu cốt lõi | Ưu tiên |
|:---:|:---|:---|:---|:---:|
| **U1** | **Makers in the global Home Assistant / ESPHome community** | Has an intent ("trông bể cá" [watch over fish tank], "tưới theo nhu cầu cây" [water plants on demand]), usually without hardware in hand yet; familiar with Home Assistant, ESPHome, asks Claude how to build | From a single sentence to a working device; test run on simulation before buying; delegate tasks by voice, get alerts via chat channels; no friction, no account in the first ten minutes | **Primary — initial market (Q-72)** |
| **U2** | **Embedded Engineering Lead** | Team of 3–10 people, preparing to move product into production | Automated safety testing, switch boards without rewriting code | Secondary *(from Q-72; previously Primary)* |
| **U3** | **Fleet Operations Engineer (Fleet Ops)** | Managing 100–10,000 deployed devices | Safe updates, remote diagnostics, zero bricked devices | Secondary — from v1.1, after 8-week gate (Q-72) |
| **U4** | **Safety & QA Specialist** | Responsible for approving device behavior | Human-readable safety conditions, auditable logs | Secondary |
| **U5** | **Micro-OEM: makers selling NeuroEdge Blueprints or devices** *(Q-72; includes OEM/ODM board partners)* | Built a well-running device, wants to sell to hundreds; small hardware startup | Package kit, firmware, template contracts, detectors, and evidence into a single-command installable package; clear commercial license; no vendor lock-in to one chip family | **Primary — trial test of the 8-week gate (B8)** |
| **U6** | **Tiered Robot Integration Team** | Robots with one brain (Pi 5) and multiple MCU controllers: motors, robotic arms, navigation via ROS 2/Nav2 (Q-32, Q-34) | All motion commands pass through gates on each node; on loss of communication, each actuator reverts to safe state (Q-35) | Secondary — from I14; hypothesis, verified via interviews in `TODOS.md` #40 |
| **U7** | **Integration Author (third party)** | Emerging AI hardware vendor, community of an ecosystem (Muse Gadgets, Home Assistant, xiaozhi…), maker writing bridges for products they use | Connect own product to the safety layer solely via public documentation without modifying core; self-prove compliance via conformance test suite (Q-67) | Primary — from I2c |
| **U8** | **End User Installing NeuroEdge Blueprints** *(Q-72)* | Non-programmer; buys kit according to BOM or buys device from U5 | Install a Blueprint, read a ≤ 5-line approval summary, approve via chat channel, get a smart device running immediately; no need to read code or gates | Primary — from I2e |
| **U9** | **Component and Kit Supplier** *(Q-72)* | Sells sensors, boards, relays according to Blueprint BOM | Pre-defined orders per BOM; affiliate purchase links for exact part numbers | Secondary — initial revenue exploration (kit commission) |

### 2.2 Jobs To Be Done

| Mã | Nhóm | Nhiệm vụ | Đáp ứng bởi |
|:---:|:---:|:---|:---|
| **J1** | U1 | "I want to try a voice agent tonight without having a board yet" *(voice temporarily paused — Q-72; text input on `sim` remains Journey 1)* | FR-TGT-01, FR-DX-01 |
| **J2** | U2 | "I need to ensure a prompt update does not cause the door latch to unlock incorrectly" | FR-CI-03, FR-CI-04 |
| **J3** | U2 | "I need to migrate from RPi to ESP32-S3 without rewriting logic" | FR-TGT-02, FR-HAL-01 |
| **J4** | U3 | "A device at a villa failed; I need to know what happened without going on-site" | FR-CI-01, FR-FLT-05 |
| **J5** | U3 | "I need to update 1,000 devices without the risk of mass bricking" | FR-OTA-01, FR-FLT-02 |
| **J6** | U4 | "I need to approve unlock conditions without reading Python source code" | FR-GATE-01, FR-GATE-02 |
| **J7** | U2 | "I want to reuse safety policies that others have refined" | FR-GATE-05, FR-REG-01 |
| **J8** | U1 | "Trông bể cá 120 lít giúp tôi: oxy thấp thì bật sục khí, có gì lạ chụp ảnh gửi tôi" (Watch over my 120-liter fish tank: if oxygen is low turn on aeration, if anything is unusual take a photo and send it to me) *(Q-72)* | FR-DX-09, FR-DX-10, FR-MSN-01 → 14, FR-AGT-01 |
| **J9** | U1, U8 | "Alert me to strange trends, but don't message all day and don't let the LLM bill exceed $2 USD a month" *(Q-72)* | FR-AGT-04 → 07, FR-MSN-09, FR-CH-01 |
| **J10** | U5 | "I want to sell devices I built to others, with proof that it is safe" *(Q-72)* | FR-BP-01 → 10, §8.4 |
| **J11** | U8 | "I want to install devices others built without programming, and understand what I am allowing it to do" *(Q-72)* | FR-BP-03, FR-MSN-12, FR-CH-04 |

### 2.3 Four Primary User Journeys

Journey 0 is the **primary journey** from Q-72; Journey 1 remains; Journeys 2 and 3 (device fleet, Fleet OS) come after the 8-week demand gate.

#### Journey 0 — Fish tank goes through three loops (U1 builds → U8 installs → U5 sells) *(Q-72, running on simulation first)*

| Vòng | Bước | Phản hồi hệ thống kỳ vọng | Yêu cầu |
|:---:|:---|:---|:---|
| ① | User says to Claude (MCP client connected to NeuroEdge Lab): *"Tôi muốn trông bể cá 120 lít."* ("I want to watch over a 120-liter fish tank.") | Proposes a verified kit from catalog (temperature sensor, dissolved oxygen, camera, aeration and heater relays), wiring diagram, parts list with purchase links; test runs on `sim` with fish tank model (simulation tier G1) before buying | FR-DX-09, FR-DX-10, FR-TGT-07 |
| ① | Build, flash, check assembly; connect Telegram | Board config, firmware, gate generated from a single source; `neuroedge lab doctor` checks each sensor (*"cảm biến oxy đọc 0 — kiểm lại dây"* ["oxygen sensor reads 0 — check wiring"]); `neuroedge chat connect telegram`, pair account using code displayed locally | FR-DX-10, FR-CH-01, FR-CH-03, FR-CLI-14 |
| ② | Assign mission: *"Trông bể, oxy thấp thì bật sục khí, có gì lạ chụp ảnh gửi tôi."* ("Watch over the tank, if oxygen is low turn on aeration, if anything is unusual take a photo and send it to me.") | Draft mission contract; ask when ambiguous (*"Ngưỡng oxy thấp là bao nhiêu? Gợi ý 5 mg/L cho cá nhiệt đới"* ["What is the low oxygen threshold? Suggested 5 mg/L for tropical fish"]); conflict check; ≤ 5-line approval summary; human approves in chat or local UI — LLM cannot lock | FR-MSN-01 → 14, FR-CH-04 |
| ② | Run | Local reflex (oxygen below threshold → aeration); LLM proposes *"tắt sục khí cho yên tĩnh"* ("turn off aeration for quietness") → blocked, with reason; network disconnects → aeration still runs (declared `safe_state`); heater overheats for 10 minutes → reflex shuts off heater, sounds alarm | FR-MSN-05, FR-MSN-10, FR-ACE-03, FR-AGT-01 |
| ② | Proactive | Deterministic detector spots morning oxygen declining 3 days in a row → LLM writes proposal → proposal compiles into draft contract amendment → Telegram message with approval request and compiler-generated approval summary, not written by LLM (*"…Đề xuất vệ sinh lọc và thêm sục khí 2h–5h. Thêm vào hợp đồng?"* ["…Proposed cleaning filter and adding aeration 2h–5h. Add to contract?"]); replying "Có" ("Yes") matching approval request → amendment approved with approval record | FR-AGT-04 → 06, FR-MSN-14, FR-CH-04 |
| ③ | Share | `neuroedge blueprint pack` packages kit, firmware, template contract, detectors, and evidence trace; second user runs `neuroedge blueprint install <url>` on a clean machine, runs on `sim` in < 10 minutes | FR-BP-01 → 06, FR-CLI-13 |
| ③ | Sell *(after 8-week gate)* | Commercial license and revenue share go through NeuroEdge; evidence must be signed before Hub collects payments for seller | FR-BP-08, FR-BP-10, §8.4 |

#### Journey 1 — The First Ten Minutes (U1)

| Phút | Hành động | Phản hồi hệ thống kỳ vọng | Yêu cầu |
|:---:|:---|:---|:---|
| 0–1 | `pip install neuroedge` | Installation completes, asks for no account, asks for no API key | FR-DX-02 |
| 1–2 | `neuroedge new my-agent` | Generates scaffold project with 1 action, 1 gate, 1 test | FR-DX-01 |
| 2–4 | `neuroedge run --target sim`, type a command (e.g. *"mở cửa phòng 101"*) | Offline, keyless, deterministic: local command grammar matcher receives command; virtual actuator moves and gate verdict is shown. Voice is optional — requires cloud STT key *(Q-15)* | FR-TGT-01, FR-DX-02 |
| 4–6 | Edit `allow_when` in gate | Agent denies action, displays cause in trace | FR-ACE-02 |
| 6–8 | `neuroedge test` | Green CI; break condition → red CI, identifies violating gate by name | FR-CI-03 |
| 8–10 | `neuroedge run --target linux` | Same source code, running on real hardware | FR-TGT-02, FR-CLI-02 |

**Mandatory constraint:** throughout this entire journey, the system **MUST NOT** require purchasing hardware, creating an account, or entering payment information. The constraint applies to the **first ten minutes** (and to installing a NeuroEdge Blueprint and running it on `sim`, A14). Subsequent steps of Journey 0 may require user-chosen third-party accounts — chat platforms, their own LLM keys (BYOK), optional relay — but none sit on the safety path, and core never demands a NeuroEdge account.

#### Journey 2 — From field incident to developer machine (U3 → U2) *(Fleet OS — after the 8-week gate, Q-72)*

```text
Field device generates alert
        │
        ▼
Fleet OS automatically downloads JSON trace to central store      ← FR-FLT-05
        │
        ▼
Engineer downloads file to local machine
        │
        ▼
neuroedge trace validate traces/incidents/<session>.json     ← FR-CLI-04
        │
        ▼
neuroedge replay traces/incidents/<session>.json --target sim ← FR-CI-02
        │
        ▼
Accurately reproduces gate verdict sequence and GPIO signals
        │
        ▼
Adds trace file as permanent regression test case         ← FR-CI-03
```

#### Journey 3 — Scaling from 1 to 1,000 devices (U2 → U3) *(after the 8-week gate, Q-72)*

| Giai đoạn | Hành động | Yêu cầu chi phối |
|:---|:---|:---|
| 1 device | Flash firmware manually, virtual `sim` device appears on Fleet Dashboard | FR-FLT-03 |
| 10 devices | Automated certificate provisioning on first boot | FR-FLT-01 |
| 100 devices | Update gates and configs remotely without reflashing firmware | FR-FLT-04 |
| 1,000 devices | Canary OTA updates 1% → 10% → 100%, automatic halt if error threshold exceeded | FR-FLT-02 |

---

## 3. Release Scope

### 3.1 Three Release Milestones

The order and forecast dates for each milestone reside in **one place**: the roadmap increment table (§0.2), per Q-39. The table below only states which milestone includes which increments.

| Mốc | Tên | Increment (roadmap §0.2) | Nội dung | Điều kiện khởi động |
|:---|:---|:---:|:---|:---|
| **0.x** | Internal increments | I1–I3a | Each increment has an internal tag and a measurement signal; **not released externally** (Q-39) | — |
| **Partner trial** | Wheel delivered directly to one partner team — gates for devices they already own (Q-70) | I2c (TSK-I2c-19) | `proxy mcp`, `proxy http`, `neuroedge.guard`, `sim`, Action CI; no `esp32s3`, no on-chip voice, no NeuroEdge Lab; not published to any index | Conditions in roadmap §4.3.3 — not waiting for boards |
| **Blueprint on simulation** | First NeuroEdge Blueprint (fish tank) completing all three loops in simulation (Q-72) | I2d, I2e | Mission contracts, conditional safety (pending RFC), operator agent, Telegram + approval records, `blueprint pack`/`install`, static index, fish tank kit with affiliate BOM; no physical hardware, no payment collection; PyPI remains at I6 (Q-39) — delivery method for testers in roadmap | 8-week demand gate **after deciding** Q-72 measures results (B6–B8, §11.2) |
| **Public** | Public repo + PyPI | I6 | Release candidate for MVP: demo of four expanded primitive packages and Blueprint on `sim`, `linux`, and `esp32s3` (Q-77) | I3a, I2b, and I2e released |
| **v1.0 = MVP** | Core (source-available, Q-45) — MVP launch (Q-52, Q-77) | I7 | Block 1a + Block 1b + four expanded primitive packages (Q-53) + sample kits + open platform (Q-67) + mission contracts, operator agent, chat channels, NeuroEdge Blueprint (Q-72). Voice, Studio, `jetson` **temporarily paused, not cut**; v1.0 scope **re-evaluated at the 8-week gate** using data (Q-72) | Achieves all criteria in §11.1 (A1–A13) |
| **Developer Beta** | Beta on `1.0.x` line | I8 | Feature freeze on `1.0.x` line, supporting 50–100 developers | v1.0 released |

Block 4 (Field AURA, post-Beta — conditions in §14) and Block 5 (Monetized Marketplace) are out of scope for this PRD. Specifically for NeuroEdge Blueprint, the **minimal Hub** — static index, serverless, free — belongs to scope I2e (FR-BP-05); monetized Hub only opens after the 8-week gate (§14, Q-72), replacing the G1–G4 milestone conditions of §11.2 specifically for Blueprint. Block 4 and Block 5 are specified in dedicated product documents when their milestones arrive. Per Q-39, execution plans for Phase 2, NeuroEdge Lab (I4a, I5a — Q-55, Q-71), and tiered robots (I14) reside in the master roadmap; this PRD specifies only the contracts Phase 2 must adhere to (FR-TGT-08, FR-HAL-01), not its detailed requirements.

### 3.2 Scope of Each Milestone

| Nhóm yêu cầu | v1.0 Khối 1a<br>(I0–I2) | v1.0 Khối 1b<br>(I3–I7) | Đã bỏ khỏi roadmap<br>(Q-77) |
|:---|:---:|:---:|:---:|
| HAL capability contracts (FR-HAL) | ● | ● | — |
| `sim` + `linux` targets (FR-TGT) | ● | — | — |
| `esp32s3` target (FR-TGT) | — | ● | — |
| Action Contract Engine (FR-ACE) | ● | — | — |
| Gate format (FR-GATE) | ● | — | ◐ registry |
| Model abstraction (FR-MDL) | ◐ except FR-MDL-09 | ● FR-MDL-09 ASR/TTS | — |
| Perception & conversational runtime (FR-PER) | ◐ FSM spec (TSK-S2-07) | — (voice dropped from v1.0, Q-77) | ● on-chip voice |
| Action CI (FR-CI) | ● | ◐ `verify` Tier 1 targets | — |
| Trace schema (FR-TRC) | ● | — | — |
| CLI (FR-CLI) | ● | ◐ additions | — |
| Developer experience (FR-DX) | ● | ● FR-DX-08 → FR-DX-10 (kits, `neuroedge add`, NeuroEdge Lab) | — |
| Expanded primitives (FR-HAL-08) | ◐ `sim` + `linux` (I2a) | ● `esp32s3` (I3a) | — |
| Device-level OTA (FR-OTA) | — | ● | — |
| Provider abstraction layer (FR-GW) | ◐ FR-GW-01, 03 minimal (Q-28) | ◐ MCU streaming client of FR-GW-04 (TSK-S5-06) | ● remainder (Q-28) |
| Fleet Management OS (FR-FLT) | — | — | ● |
| Infrastructure rails (FR-REG) | — | — | ● |

**Legend:** ● complete in milestone · ◐ partially complete · — not in milestone

**Requirements group for Q-72** precedes Block 1b in sequence; increments and tasks in roadmap §0.2:

| Nhóm yêu cầu | I2d — Nhiệm vụ và agent vận hành | I2e — NeuroEdge Blueprint tối thiểu | Sau cổng 8 tuần |
|:---|:---:|:---:|:---:|
| Mission contracts (FR-MSN) | ● | — | — |
| Conditional safety (FR-ACE-03, pending RFC) | ● | — | — |
| Operator agent (FR-AGT) | ● | — | ◐ model routing (FR-AGT-08) |
| Chat channels and approval records (FR-CH) | ● Telegram | — | ◐ Slack, Zalo |
| Leak-proof data flow (FR-EGR) | ● | — | ◐ relay (FR-EGR-05) |
| Chunked traces (FR-TRC-11 → 13) | ● | — | — |
| Simulation G1 (physical model), G2 (FR-TGT-07) | ● | — | — |
| Standard MCP tool set for the brain (FR-AGT-12; replacing Lab loop ①, Q-77) | ● | — | — |
| NeuroEdge Blueprint, static index (FR-BP-01 → 07) | — | ● | ◐ licenses, monetized Hub (FR-BP-08, 10) |
| Fish tank kit with affiliate BOM (FR-DX-09) | — | ● | — |

### 3.3 Activation Conditions for v1.1

v1.1 **MUST NOT** launch on a fixed schedule. It only launches when Developer Beta satisfies **simultaneously** B1 and B2 — thresholds in §11.2. B3 is still measured but is not a gating condition (Q-41). Per Q-72, Fleet OS (U3) also comes after the 8-week demand gate (B6–B8); gate outcomes may change the ordering of v1.1, but will not change B1, B2.

### 3.4 Scope Freeze for Block 1b

The following items **MUST** be excluded from Block 1b to ensure memory stability on microcontrollers. This is a constraint of the **v1.0 milestone**, not a permanent constraint — see §14 of this document for the long-term status of each item.

| Hạng mục | Trạng thái trong v1.0 |
|:---|:---|
| Custom wake-word training | Not supported — only use pre-trained wake-word *"Hey Neuro"* |
| Board coverage | **Official reference board ESP32-S3-Box-3** (integrated ST7789 LCD, dual-mic ES7210, speaker ES8311, I/O dock; DevKitC relegated to secondary board maintained by community), plus **one ESP32-S3 board with camera** for `vision.in` (Q-53): **M5Stack CoreS3** (Q-61, TSK-I3a-01) |
| Computer vision | **In scope for v1.0** (Q-53): `vision.in` across three targets; results enter gate as maker-declared facts, confidence thresholds locked by numeric criteria (Q-54) |
| Connection to cloud AI providers (LLM · ASR · TTS) | **In scope for v1.0** — default architecture per P-4 |
| NeuroEdge-operated cloud services, NeuroEdge account system | Out of scope for core — users run provider layer themselves and hold their own keys (BYOK). **Limited exception (Q-72):** optional relay (pass-through TLS tunnel, non-decrypting relay, FR-EGR-05) and static Blueprint index (FR-BP-05) are permitted; both **never sit on the safety path** — if disabled or broken, reflexes, gates, contracts, and approvals still run |
| Messaging channels (Telegram first, then Slack, Zalo) | **In scope** (Q-72): adapter runs in runtime on host machine, not on MCU (FR-CH) |
| Jetson, Matter, HomeKit | Out of scope (`jetson` temporarily paused per Q-72) |
| AI model fine-tuning | Out of scope |

---

## 4. Functional Requirements — Execution Core

### 4.1 Hardware Abstraction Layer (FR-HAL)

HAL is a bidirectional check contract: the board declares provided capabilities, the agent declares required resources, and all incompatibilities are detected **at compile time**.

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-HAL-01** | The system provides 5 **core** primitives: `audio.in`, `audio.out`, `digital.out`, `sensor.read`, `display`. Core primitives are mandatory for each target's default board and for all Tier 1 reference boards outside `EXTENSION_REFERENCE_BOARDS`. Outside core are the **expanded** primitives of FR-HAL-08 (`digital.in`, read-only I2C bus, `analog.in`, PWM in `digital.out`, `motion.*`, `vision.in`): **optional per board**, boards declare only primitives physically present on hardware, and agents requesting primitives not declared by the board are rejected at build time (FR-HAL-04, FR-HAL-05). The primitive set, both core and expanded, is **frozen for v1.x**; adding primitives requires an RFC *(RFC-0013, Q-53)* | P0 | All 5 core primitives have complete implementations on Tier 1 targets; each expanded primitive is present on at least one reference board of each Tier 1 target (FR-HAL-08) | §3.3, RFC-0013 |
| **FR-HAL-02** | Boards declare capabilities via a `board.toml` file following a standard schema | P0 | Files violating schema rejected with message identifying error field | §4.2 |
| **FR-HAL-03** | Agents declare capability requirements via `[requires]` block in `agent.toml` | P0 | Missing `[requires]` block when agent has physical actions → build halts | §4.3 |
| **FR-HAL-04** | Capability reconciliation tool runs **at build time**, not runtime | P0 | Incompatibility causes `neuroedge build` to exit with non-zero code, generating no firmware | §4.9 |
| **FR-HAL-05** | Capability error messages clearly state: missing capability, what board provides, source code call location | P0 | Message contains all 3 components and suggests remediation steps | §4.9 |
| **FR-HAL-06** | GPIO pins and sensors are identified by **logical names**, not physical pin numbers | P0 | Switching boards only requires modifying `board.toml`, no agent code changes | Appendix A.2 |
| **FR-HAL-07** | HAL rejects any `digital.out` command lacking a passed gate signature | P0 | Direct call raises `ActionContractViolation` | Appendix A.2 |
| **FR-HAL-08** | Four expanded primitive packages, **optional per board**: sensors (`digital.in`, read-only I2C bus, `analog.in`, `numeric` gate criteria), fine control (PWM in `digital.out`), vision (`vision.in`), motion (`motion.*`). Each expanded primitive has at least one Tier 1 reference board on **each** Tier 1 target *(Q-53; RFC-0007, RFC-0009 → RFC-0013)* | P0 | `verify --targets sim,linux,esp32s3` reaches 100% for each package's sample agent; agents requesting primitives not declared by the board are rejected at build time (FR-HAL-05) | Q-53 |

### 4.2 Execution Targets (FR-TGT)

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-TGT-01** | The `sim` environment is an official execution target, faithfully implementing HAL contracts — not a mock | P0 | `sim` runs identical agent code as real hardware, with no separate code branches | §3.7 |
| **FR-TGT-02** | The `linux` environment is an official peer target, supporting RPi and x86 via `gpiod` | P0 | Sample agent runs live on RPi 5 and x86 Linux — sample agent requires `aec`, thus depending on Q-22 | §3.2 |
| **FR-TGT-03** | The `esp32s3` environment is an official peer target, built with ESP-IDF | P0 | Sample agent runs live on reference board | §8.2 |
| **FR-TGT-04** | **Equivalence principle:** the same agent code yields identical gate verdict sequences across all targets, without modifying a single line | P0 | `neuroedge verify --targets sim,linux,esp32s3` achieves 100% | §3.2 |
| **FR-TGT-05** | Switch targets via the `--target` parameter; branching logic by target in agent code is **forbidden** | P0 | Code audit: no conditional expressions based on target name in the application layer | §4.1 |
| **FR-TGT-06** | `sim` provides a web UI displaying virtual sensors and actuator states | P0 | Openable in browser, reflecting virtual GPIO pin states in real time; operates offline (no CDN downloads). Command: `neuroedge run --ui` (TSK-S2-09) | §4.10 |
| **FR-TGT-07** | `sim` can simulate sensor scenarios and degraded network conditions. *Extended by Q-72:* **mission** scenarios — multi-day sensor time series generated from a **physical model** (fish tank: temp, oxygen over time, effects of heater and aerator), fast-forwarded 30 days, including network outage, LLM outage, chat channel crash, power outage events (simulation tier G1) | **P0** *(promoted from P1 by Q-72; I2d)* | Declares network loss scenarios to test fail-closed behavior. The 30-day fish tank scenario runs deterministically (same seed gives identical sensor sequences and verdicts), sufficient to measure A16, A19, NFR-COST-01, and 30-day trace size (NFR-OBS-04) | §4.7, Q-72 |
| **FR-TGT-08** | **Target tiering:** each execution target belongs to exactly one commitment tier — Tier 1 official (`sim`, `linux`, `esp32s3`), Tier 2 extended maintained by core team, Tier 3 community ports and self-verified. Tiers are explicitly declared, not inferred | P0 | **Accepted in Phase 2** — requires `TARGET_TIERS` (RFC-0002 PR2): each target has its tier recorded in documentation and in the core code tier table (RFC-0002 §3b); `board.toml` does not self-declare tier; 100% `verify` threshold only binds Tier 1; Tier 3 does not block releases. **Currently only Tier 1 exists** (`sim`, `linux`, `esp32s3`), verified via A2. **Reference boards (RFC-0013):** each Tier 1 target has at least one reference board (`REFERENCE_BOARDS`, first element is default); each `sim-*` profile mirrors exactly one reference board (`SIM_MIRRORS`) and has no greater capabilities than it; each expanded primitive is present on at least one reference board of each Tier 1 target; `verify` replays all reference boards, and `build` without `--board` never auto-selects a different board | §3.2 |

**Known limitations, must be explicitly stated in technical documentation:** `sim` does not simulate room acoustic reflections, microphone noise, mic-array beamforming, or microcontroller memory fragmentation. These error classes are controlled via nightly testing on real hardware (NFR-REL-03).

**Simulation first, physical hardware later (Q-72).** The three loops of Journey 0 run on four **simulation tiers** before purchasing hardware — tier codes `G1`–`G4` here differ from milestones G1–G4 in §11.2 and assumptions `G-a`… in §13.3:

| Tầng | Công cụ | Chạy được gì | Dùng cho |
|:---|:---|:---|:---|
| **G1** Physical model | NeuroEdge `sim` adding physical model (FR-TGT-07) | Contracts, gates, operator agent, detectors, LLM costs | Loops ② and ③; CI |
| **G2** `linux` runtime with simulated peripherals | Kernel `gpio-sim` (already used in `linux-hal` job), plus simulated sensors | The exact runtime that will run on Pi, lacking only electricity | Run continuously for 2 weeks before acquiring Pi (B7) |
| **G3** ESP32 firmware on host | Espressif QEMU (Q-21), simulation spikes from Q-69; Wokwi and Velxio are options cited by Q-72, must reconcile against "not used" portions of Q-21 and Q-69 before entering CI | Firmware with `ne_gate`, reflexes during network loss | Test reflex tier |
| **G4** Home Assistant maker route | ESPHome host platform (sensors replaced by template sensors) | HA users test Blueprint without needing a board | Test with HA, ESPHome community |

Simulation does not catch wiring errors, electrical noise, sensor drift, or intermittent Wi-Fi (R-16); physical hardware must be purchased before selling the first Blueprint.

### 4.3 AI Model Abstraction (FR-MDL)

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-MDL-01** | All model access passes through the `SystemOne` or `SystemTwo` interface; default connection interface complies with OpenAI API standard | P0 | No direct vendor SDK calls exist in core | §3.6 |
| **FR-MDL-02** | `SystemOne` supports exactly 3 primitive types: `bool`, `level`, `choice` | P0 | All three types execute and map directly into the gate `evaluate` block | §3.6, Appendix B.2 |
| **FR-MDL-03** | Both interfaces must support declaring a `fallback` path. For `SystemOne`, the local fallback is a **fixed command recognizer** (command grammar → intent with confidence) and is P0 *(Q-14)* | P0 | Disconnecting primary provider → system auto-switches to fallback, logs event in trace; network loss → `SystemOne` evaluates via local command grammar *(Q-14)* | §3.6 |
| **FR-MDL-04** | Replacing model providers requires no modifications to agent code or gates | P0 | Switching `SystemOne` to local model via configuration change only | §3.6 |
| **FR-MDL-05** | Routing policy for System 1 / System 2 is declarative configuration, not hard-coded | P1 | Changing escalation confidence threshold via configuration, no recompilation | §3.5 |
| **FR-MDL-06** | System logs System 1 / System 2 usage ratio and per-turn cost | P0 | Metrics appear in trace file of each session: each System 2 invocation is a `system_two_call` event (provider, model, latency, tokens, `cost_usd`; no prompt, no key); S1/S2 ratio in `session_summary`, serving path and per-hop latency of each turn in `turn_latency` (`docs/spec/tool_calling.md` §7.1). *Q-72:* per-turn `cost_usd` is the basis for operator agent LLM cost cap (FR-AGT-05) | §12.1, Q-72 |
| **FR-MDL-07** | **Provider pluggable:** LLM, ASR, and TTS connect via OpenAI API standard or user-written adapters | P0 | Adding an OpenAI-compatible provider via endpoint and key configuration only (`[system_two]` table: `model`, `api_base`, `api_key_env`), no code edits | §3.6, §6.1 |
| **FR-MDL-08** | **Custom adapters:** users can write custom connection logic for providers not yet supporting OpenAI standard | P0 | An external sample adapter (`provider = "python:pkg.mod:factory"`, contract `neuroedge/models/providers/base.py`) runs without modifying NeuroEdge core | §3.6 |
| **FR-MDL-09** | **ASR/TTS as providers:** STT and TTS are not hard-coded to a library, replaceable via configuration | P0 | Switching STT and TTS providers via configuration only; agent and gates remain unchanged | §3.4, §3.6 |
| **FR-MDL-10** | **Actions as tool calls (Q-24):** every `@action` is a tool with schema generated from signature; `SystemOne`, `SystemTwo`, local command grammar, and MCP clients invoke actions via identical `ToolCall`, through the same gate — per `docs/spec/tool_calling.md` | P0 | Unknown tool or invalid/wrong-typed argument ⇒ `REJECTED`, no pin changes; identical call from different sources receives same verdict unless gate reads `call_source`; on network loss, grammar-matched sentence still becomes tool call; runtime passes corpus `fixtures/tool_calls/` (`docs/spec/tool_calling.md` §9) | §3.6, Q-24 |
| **FR-MDL-11** | **System 2 tool loop:** result of each tool call (including BLOCK and reason) returns to System 2 to reply to user; loop count has declared limit | P0 | Gate blocks ⇒ System 2 states reason instead of repeating call; exceeding loop limit ⇒ halts, logs event | `docs/spec/tool_calling.md` §4 |
| **FR-MDL-12** | **System 2 as MCP host (Q-27):** calls device tools via agent's own MCP server (still through gate) and **informational** tools of external MCP servers declared in `[mcp.servers]` (allowlist); external results are untrusted data | P0 | Tool outside allowlist ⇒ `REJECTED`; server not running ⇒ `mcp_server_unavailable`, device tools still run; injected external content cannot bypass gate; trace contains digest only | `docs/spec/tool_calling.md` §10 |

### 4.4 Perception Layer and Conversational Runtime (FR-PER)

Principle: **integrate the best open-source libraries, do not rewrite basic signal processing algorithms.**

*Temporarily paused per Q-72:* the FR-PER group follows mission contracts, operator agents, chat channels, and Blueprints; v1.0 scope re-evaluated at the 8-week gate (applies to NFR-PERF-01, NFR-PERF-07, A6).

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-PER-01** | Built-in two-tier voice processing pipeline: **(a) on-device** — wake-word, VAD, AEC, audio capture/playback, conversational state machine; **(b) cloud** — STT, TTS, and language inference via providers | P0 | Sample agent works end-to-end with provider configuration only, requiring no additional library configuration | §3.4 |
| **FR-PER-02** | **Barge-in:** interrupts TTS immediately when user begins speaking, while revoking unexecuted actuator commands | P0 | Test scenario: barge-in mid-sentence → TTS stops < 300 ms, zero leaking actuator commands | §3.4 |
| **FR-PER-03** | **Dynamic silence:** distinguishes pausing to think from turn completion | P0 | Slow speakers not cut off across standard test scenarios | §3.4 |
| **FR-PER-04** | **Partial stream responses:** plays audio from the first token, retracts safely when model changes conclusion | P1 | Retraction causes no duplicate playback or dropped segments | §3.4 |
| **FR-PER-05** | **Self-recovery on STT errors:** empty strings or noise do not hang state machine, no infinite question loops | P0 | Injecting 20 consecutive noise frames → state machine still responds correctly | §3.4 |
| **FR-PER-06** | Memory-optimized voice runtime on `esp32s3`, including audio capture/playback, WebRTC AEC, libfvad VAD *(matching `docs/spec/voice_fsm.md`)*, Opus streaming, conversational state machine, gate evaluation, and local fixed command recognizer *(ESP-SR MultiNet or TFLite Micro / ESP-NN, selected in Block 1b — Q-14)*. **On-device STT/TTS not required** | P0 | Runs stably for 24 hours continuously on reference board with capture/playback pipeline + state machine + gates, zero out-of-memory errors | §8.2 |
| **FR-PER-07** | **Cloud-first voice:** STT and TTS run by default on cloud via providers; microcontroller only streams audio up and receives audio stream back | P0 | Voice loop runs end-to-end on reference board with STT/TTS placed on cloud providers | §3.4, §6.1 |

### 4.5 Operator Agent (FR-AGT)

*Planned — Q-72, increment I2d; no code yet.* The operator agent runs continuously on home hardware (Pi, mini PC, NAS) after the MCP client session closes. Today, all NeuroEdge processes live within the currently executing command (`run`, `mcp serve`); I2d adds the first long-lived process. It splits into **two processes**, reusing boundaries from Q-71 (only one process holds device privileges; MCP client is an untrusted caller):

- **Trusted runtime** — HAL and device permissions, gates, mission contract execution, scheduler, deterministic detectors, chat channel adapters and approval verification, data egress (FR-EGR), traces. Does not call LLMs, holds no LLM keys.
- **Untrusted LLM worker** — holds user LLM keys (BYOK), calls runtime as a local MCP client; source attributed by runtime; never approves.

The operator agent **does not build or lock** contracts (role of NeuroEdge Lab, Q-71): runtime LLM only explains and *proposes* amendments. Package and process decomposition: `docs/architecture/`.

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-AGT-01** | **Continuous trusted runtime:** a long-lived process (systemd service or equivalent) holding all trusted components listed above; restarts automatically after errors or power failure; each restart is an event in trace | P0 | Kill runtime process ⇒ restarts automatically, all actuators reverted to `safe_state` in the interim via on-device duration/lease (FR-ACE-03), trace contains restart event; runs continuously for 2 weeks on G2 or G3 without intervention (B7, NFR-REL-06) | Q-72 |
| **FR-AGT-02** | **Untrusted LLM worker:** isolated process holding BYOK keys, invoking models via LiteLLM (FR-MDL-07; includes local models like Ollama); invokes runtime via local MCP; source attributed by runtime per connection, not self-declared (FR-ACE-09); all action calls pass through gates; holds no device permissions; never serves as human source | P0 | Penetration test suite: worker self-declares `call_source` ⇒ `REJECTED`; worker sends `ask` confirmation or approval ⇒ rejected (FR-CH-05); worker user cannot open `/dev/gpiochip*`, `/dev/i2c-*`; key never appears in traces, contracts, Blueprints, or chat messages (NFR-SEC-13) | Q-71, Q-72 |
| **FR-AGT-03** | **Scheduling:** runs time-of-day and periodic terms (sensor polling, summaries, permission expiration); durations, deadlines, periods measured via **monotonic clock**; wall clock used only for time-window terms, via facts marked with `unsynced` status (FR-MSN-04). A stuck sensor read must not block runtime loop — `TODOS.md` #48 becomes real risk. Existing foundation: NeuroEdge Lab event-driven triggers (block N6: runs without client session, debounce, rate ceiling, non-`HUMAN_SOURCES` origin) | P0 | G1 scenario: changing wall clock (NTP jump) does not lengthen or shorten durations or approval deadlines; bus-stuck sensor does not delay other sensors' reflexes beyond gate budget | Q-72 |
| **FR-AGT-04** | **Deterministic detectors first, LLM second:** thresholds, trend slopes (e.g., oxygen declining 3 consecutive days), flatline sensors, oscillations — computed via conventional code, declared in mission contracts or Blueprints; LLM invoked only when a detector fires an event, or for scheduled summaries; detector events recorded in trace and replayable | P0 | 30-day scenario on G1: oxygen trend detector fires on exact day, does not fire on control series; LLM call count equals fired events plus summary count; trace replay reproduces identical detector event sequence | Q-72 |
| **FR-AGT-05** | **LLM cost ceiling (`llm_budget`):** runtime enforces ceiling declared in contract (FR-MSN-09) **prior to** dispatching tasks to worker, accumulated from per-turn `cost_usd` (FR-MDL-06); unmetered turn costs calculated via unit rate in configuration, or blocked if rate absent. Reaching ceiling ⇒ stops calling LLM until period resets; reflexes, detectors, and hard-templated alerts continue running; user receives exactly one message: "đã hết ngân sách phân tích kỳ này" ("analysis budget exhausted for this period") | P0 | G1 low-budget scenario: after hitting ceiling, zero `system_two_call` events occur; total period cost does not exceed ceiling by more than the running turn at time of limit; urgent alerts still delivered (NFR-COST-01) | Q-72 |
| **FR-AGT-06** | **Proactive alerts, batching, message budgets:** trend explanations and proposals written by LLM, sent via paired chat channel (FR-CH-01); routine messages batched into summaries (e.g., one daily digest per LLM call); **urgent alerts use hard templates**, without LLMs, never batched or delayed; exceeding message budget ⇒ routine messages rolled into next summary. Contract change proposals follow standard amendment pipeline (FR-MSN-14) | P0 | 30-day scenario: non-urgent message count does not exceed declared budget (NFR-COST-02); all urgent alerts delivered within their latency budget; one trend proposal reaches chat accompanied by approval request | Q-72 |
| **FR-AGT-07** | **Failure branches:** worker dies or hangs ⇒ runtime still executes reflexes, runs detectors, sends hard-templated alerts, restarts worker, reports "phân tích tạm ngưng" ("analysis temporarily paused"); chat channel drops ⇒ bounded queue + local alerts on local UI, delayed messages carry original timestamps; LLM budget exhausted ⇒ FR-AGT-05; approval request expires ⇒ not approved (FR-CH-04); relay lost ⇒ safety unaffected (FR-EGR-05); power loss ⇒ traces handled per FR-TRC-12 | P0 | Each branch has a G1 (or G2) scenario with pre-recorded expected outcomes; no branch causes an actuator to leave `safe_state` or drops a recorded block verdict | Q-72 |
| **FR-AGT-08** | **Model routing for agents:** local models for routine summaries, powerful models for proposals — both via LiteLLM, declared by configuration (FR-MDL-05, FR-GW-03) | P1 | Switching models per task category via configuration only; costs for each category appear separately in trace | Q-72 |
| **FR-AGT-09** | **Agent does not build, does not lock:** runtime and worker have no pathway to lock drafts, modify locked gates, edit `digests.lock`, update `board.v1` profiles, or lock mission contracts; all such changes pass through humans (FR-MSN-14, Q-71) | P0 | Test suite: no MCP tool exposed by runtime to worker can write to above files; tool list pinned by tests | Q-71, Q-72 |
| **FR-AGT-10** | **Optional cloud brain** *(planned · Q-74 Step 2, conditional)*: LLM worker, conversation, and mission contract compilation run on NeuroEdge Cloud; trusted runtime (gates, reflexes, approval verification, data egress, traces) strictly resides on home box, initiating outbound connections, with no inbound ports open | P2 | Severing cloud connection ⇒ reflexes and gates continue operating; cloud sends rules lacking valid signature or approvals unverified locally ⇒ box rejects, records trace | Q-74 |
| **FR-AGT-11** | **Multi-node, multi-home mesh** *(planned · Q-74)*: one agent orchestrates multiple ESP32s, multiple Pis, multiple homes; each node only executes signed rules and autonomously reverts to safe state on disconnect; a command cannot affect more than declared device or home limits without dedicated approval; irreversible actions in any home always require human confirmation | P2 | Spoofed command from cloud to unlock ⇒ blocked at node; command exceeding scope limit ⇒ blocked and alerted; each node maintains distinct identity and trace | Q-74 |
| **FR-AGT-12** | **Self-hosted or cloud NeuroEdge Brain** *(planned · Q-76; internal demo 2026-10-13: `demo/i2f-chat-den-cua/`)*: identical worker (conversation, LLM, memory, schedule) runs on user's inexpensive Linux board or on NeuroEdge Cloud, with isolated instances per user; worker interacts with home devices strictly via runtime MCP tools; shell, hardware bus, and skill installation toggled by user, each active capability carrying a risk label (Q-80) | P2 | Compromised worker (prompt injection, `exec`) running under dedicated user of TSK-I2d-24 cannot toggle any pin; identical worker code runs self-hosted and cloud without code branching; one user's instance cannot read another user's memory | Q-76 |

---

## 5. Functional Requirements — Action Safety

### 5.1 Action Contract Engine (FR-ACE)

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-ACE-01** | All actuator commands **must** pass through their corresponding gate; no shortcuts exist | P0 | Penetration test: no public API activates GPIO while bypassing gate | §3.5 |
| **FR-ACE-02** | Physical actions callable only via `c.do()`; direct call raises `ActionContractViolation` | P0 | Test asserts exception raised and GPIO pin not energized | §4.4 |
| **FR-ACE-03** | **Fail-closed default for commands:** timeout or model returns invalid data → block action. **Network loss** → gate still evaluates via local fixed command recognizer; only blocks with `gate_unreachable` when fallback unavailable or non-functional *(Q-14)*. **Actuators revert to declared `safe_state`** *(pending conditional safety RFC — Q-72)*: each actuator has a `safe_state` declared in `board.v1`, default `off` (today only `motion.*` has `safe_state`: `stop`/`hold`); duration, `max_continuous_ms`, lease, remote actuator auto-off levels L0–L3 (RFC-0018), and Q-62 gate exemption all refer to "reverting to `safe_state`", while moving *away from* `safe_state` is the direction gated and limited. `safe_state` other than `off` can **only** be declared in `board.v1` — never in mission contracts, gates, or Blueprints — and `safe_state: on` actuators must declare a **hardware interlock** (default-on wiring like normally closed relay, thermal fuse, float switch); software only commands leaving that state, bounded by timeout. Resolve `TODOS.md` #58 first so legacy parsers do not silently ignore new keys. Existing profiles retain behavior | P0 | Scenario `network=offline` → gate evaluates via local command grammar: sentence matching with sufficient confidence receives verdict per `allow_when`, unmatched or below-threshold sentence blocked per normal criteria. Scenario `network=offline` + fallback absent/fails → action blocked with reason `gate_unreachable`. *When RFC lands:* `board.v1` declaring `safe_state: on` without interlock ⇒ flashing rejected (A21); `safe_state` declared in contract, gate, or Blueprint ⇒ rejected; fish tank aeration with `safe_state: on` still runs during network loss, LLM loss, or expired lease (A16); command "tắt sục khí 10 phút" ("turn off aeration for 10 minutes") is gated and automatically reverts to on upon expiry; three golden traces and all corpora replay identically on existing profiles | §3.5, Q-62, Q-72 |
| **FR-ACE-04** | Decorator `@action` binds `requires` to participate in build-time capability reconciliation | P0 | Missing capability → build halts, pinpointing calling code line | §4.4 |
| **FR-ACE-05** | Decorator `@action` must point to a gate declared in `agent.toml` | P0 | Missing gate declaration → build halts | §4.4 |
| **FR-ACE-06** | Each interaction session generates a complete JSON trace file. *Operator agent 24/7 runtime (Q-72, pending RFC):* a session is a **series of trace chunks**, each replayable (FR-TRC-11) | P0 | File contains per-hop latency, gate evaluation outcomes, actuator commands | §3.5 |
| **FR-ACE-07** | Type separation between utterance behavior (`c.say()`) and physical action (`c.do()`) | P0 | `c.say()` does not pass through gate; `c.do()` always passes through gate | §4.6 |
| **FR-ACE-08** | **Parameter constraints in gates (Q-25):** gate declares range/value set for action arguments; inheritance only narrows | P0 | Tool call with out-of-range argument ⇒ BLOCK `argument_out_of_range`, pin unchanged; child gate widening range ⇒ `GateInheritanceError` | RFC-0005 |
| **FR-ACE-09** | **Call origin is trusted fact:** dispatcher injects `call_source`; caller cannot self-declare | P0 | Tool call carrying `call_source` argument ⇒ `REJECTED`; gate can restrict call origin | `docs/spec/tool_calling.md` §5 |
| **FR-ACE-10** | **Human confirmation for `ask` only (Q-26):** confirmation originates from device channel, bound to specific block event, single-use, bounded expiry. *Extended by Q-72 (pending RFC for `chat:<id>` source):* humans can also confirm via **paired chat channel**, strictly via verified **approval record** (FR-CH-04) — for both runtime `ask` and mission contract amendments; LLM, group chats, and unpaired accounts can never confirm | P0 | Confirmation from `system_two` or `mcp` rejected; expired or replayed confirmation ⇒ no effect; valid confirmation ⇒ gate re-evaluates, only replacing criteria in `confirms` (RFC-0006). *Q-72:* chat approval enters confirmation path only when approval record passes all checks of FR-CH-04; LLM worker sending confirmation ⇒ rejected (A20) | `docs/spec/tool_calling.md` §6, Q-72 |

### 5.2 Safety Gate Format (FR-GATE)

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-GATE-01** | Gates are YAML files conforming to schema `neuroedge.gate/v1`, **not executable source code** | P0 | Gates can be read, diffed, and reviewed in pull requests | §3.5 |
| **FR-GATE-02** | Gates have 8 top-level fields: `schema`, `name`, `version`, `extends`, `evaluate`, `allow_when`, `on_block`, `budget`. Only `schema`, `name`, `version` are **always mandatory**; `evaluate`, `allow_when`, `on_block`, `budget` are mandatory when the gate **lacks** `extends` *(RFC-0001)*. `budget.fail` is optional — omission defaults to `closed` | P0 | Missing mandatory field under above conditions → `GateSchemaError`; gate with `extends` omitting four inherited fields remains valid | Appendix B.1, RFC-0001 |
| **FR-GATE-03** | `evaluate` block supports 4 types: `bool`, `level`, `choice`, and `numeric` (RFC-0009: `unit`, `range`, `max_age_ms` mandatory), with corresponding condition operators. `allow_when` **operator-mapping form is the v1 form**; CEL string form is permitted only on gates without `extends` — in inheritance chains it is rejected, fail-closed, because child cannot be proven stricter than parent. *Until CEL compiler completes (TSK-S2-06, currently postponed), `gate lint` rejects CEL even on standalone gates (`GateSchemaError`) — fail-closed, not under-evaluated* | P0 | Four types execute correctly with operators `eq`, `lte`, `gte`, `in`, `not_in`, `confidence_gte` and, for `numeric`, `gt`, `gte`, `lt`, `lte`; `allow_when` string form in `extends` chain → `GateInheritanceError` | Appendix B.2, Q-9 |
| **FR-GATE-04** | `on_block` block supports 4 behaviors: `escalate`, `deny`, `ask`, `degrade`. In v1.0, **all** `on_block` behaviors block physical actions; `escalate`/`ask` log event + invoke hook (default no-op); `degrade` executes `fallback_action` through its own gate *(Q-17)*. `ask` includes `confirms`: human confirmation on device channel causes gate re-evaluation *(Q-26, RFC-0006)*. *Q-72 (planned, I2d):* when operator agent runs, `ask` and `escalate` forward to paired chat channel (human receives real `escalate` — part of `TODOS.md` #20); responses to `ask` only take effect via approval records (FR-CH-04). Adds **"alarm, summon human"** state for actuators where both directions are dangerous (e.g., aeration overheating): actuator retains declared `safe_state`, runtime sends hard-templated urgent alert and waits for human — never letting LLM decide | P0 | Four behaviors execute correctly and are recorded in trace. *Q-72:* `ask`/`escalate` during runtime execution creates an approval request in chat; "alarm, summon human" state has dedicated G1 scenario | Appendix B.3, Q-72 |
| **FR-GATE-05** | Gates support inheritance via `extends` from base gate URI | P0 | Pulling community gates, overriding specific parts, executes correctly | Appendix B.5 |
| **FR-GATE-06** | **Child gates may only tighten, never loosen** (B.5 Principle 2) — applies to `allow_when`, and from RFC-0004 to `budget`/`on_block` *(Q-18)*: child `p95_latency_ms` ≤ parent; child cannot introduce new `degrade`/`fallback_action` (can only retain parent's), can change to `deny`/`escalate`/`ask` and update `to`/`message` | P0 | Child gate loosening parent's `allow_when`, `budget`, or `on_block` → `GateInheritanceError` (NE2003, Principle 2), resolution rejected *(budget/on_block part: TSK-S2-13)* | Appendix B.5, RFC-0004 |
| **FR-GATE-07** | `fail: open` **is not inherited**; must be explicitly declared at each level (B.5 Principle 4). From RFC-0004: if chain resolved to `closed` (declared or default), child gate **cannot** reopen with `fail: open` *(Q-18)* | P0 | Parent gate `fail: open`, child undeclared → child is `closed`; chain already `closed`, child declares `fail: open` → `GateInheritanceError` (NE2003, Principle 4) | Appendix B.5, RFC-0004 |
| **FR-GATE-08** | Inheritance depth maximum 3 levels; dependency cycles blocked during resolution | P0 | 4-level chain or circular dependency → clear resolution error | Appendix B.5 |
| **FR-GATE-09** | Exceeding `budget.p95_latency_ms` handled as an error condition | P0 | Budget exceeded → applies declared `fail` policy | Appendix B.4 |
| **FR-GATE-10** | Changes to `allow_when` considered breaking changes, requiring major version bump | P1 | Tooling warns when modifying `allow_when` without bumping major version | Appendix B.1 |

**Business rationale for FR-GATE-06 and FR-GATE-07:** these two principles are prerequisites for safely reusing community gates. Without them, `extends` becomes a risk rather than a feature.

### 5.3 Device-Level Firmware Updates (FR-OTA)

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-OTA-01** | Devices support dual-partition A/B firmware flashing | P0 | Failed update does not compromise running partition | §6.4 |
| **FR-OTA-02** | Devices automatically rollback locally upon detecting boot loops | P0 | Flashing intentionally faulty firmware → device automatically reverts to previous version without intervention | §6.4 |
| **FR-OTA-03** | Devices verify cryptographic signatures (RSA or ECDSA) of firmware before applying | P0 | Unsigned or invalidly signed firmware rejected | §6.4 |
| **FR-OTA-04** | Devices can fetch firmware from any open HTTP endpoint, **not required to use NeuroEdge services** | P0 | Self-hosting firmware server and successfully updating without an account | §6.4 |

**Principle P-3 constraint:** FR-OTA-01 through FR-OTA-04 belong to core, never split into paid add-ons (Q-45). Commercialization only covers large-scale campaign orchestration (FR-FLT-02).

### 5.4 Mission Contracts (FR-MSN)

*Planned — Q-72, increment I2d; no code yet.* Mission contracts are the rule unit for entire sequences of actions across multiple devices. They **do not replace gates**: each action still points to a locked gate, and the gate remains a pure function; contracts group, **tighten only**, and schedule them. The compiler lowers each term to the lowest enforceable tier: **reflex** (device with `ne_gate`, milliseconds, runs during network outage), **skill** (host runtime, seconds), **deliberation** (LLM worker, seconds to minutes). The `mission.v1` schema touches `schemas/`, so it **requires an RFC** (planned RFC, `CONTRIBUTING.md` §3); the table below defines requirements that RFC must satisfy.

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-MSN-01** | **Contracts are versioned data:** files conforming to schema `mission.v1` (requires RFC), not code; specifies devices, associated actions and gates, terms, parameters, human locker; lockable only by humans, never by LLMs or agents | P0 | Schema-violating contracts ⇒ rejected with three-part error (FR-DX-04); contract pointing to unlocked gate (`-draft`) ⇒ rejected; compiling same contract twice yields identical digest | Q-72 |
| **FR-MSN-02** | **Permitted / prohibited:** terms permitting and prohibiting actions, with parameter bounds; terms may only **tighten** relative to action gates, following gate inheritance (Appendix B.5 Principle 2, RFC-0005) | P0 | "Permitted" term broader than gate ⇒ compilation rejected, stating term and gate; "prohibited" command ⇒ BLOCK, reason referencing exact term (e.g. "tắt sục khí cho yên tĩnh") | Q-72 |
| **FR-MSN-03** | **Frequency, duration:** "at most N times per hour", "run for no longer than T" lowered to existing envelopes (`window_s`, `max_on_ms_per_window`, `min_interval_ms`, `max_continuous_ms` — RFC-0007, RFC-0010) and only tighten board envelopes | P0 | Term loosening board envelope ⇒ rejected; command exceeding rate ⇒ `EnvelopeRefusedError` or BLOCK as today | Q-72 |
| **FR-MSN-04** | **Time windows:** terms like "only 23:00–05:00" read a **runtime-injected wall-clock fact** (new — today `RUNTIME_CRITERIA` only has `call_source`, `call_channel`); fact marked with `unsynced` status when host has no NTP or RTC; time-window terms treat `unsynced` as **missing fact** (fail-closed for commands leaving `safe_state`). Durations, approval deadlines, watchdogs, and reflexes use monotonic clock | P0 | Power loss scenario, no NTP/RTC: command allowed only within time window blocked as missing fact; approval summary and UI display "đồng hồ chưa đồng bộ" ("clock not synchronized"); actuator does not leave `safe_state` | Q-72 |
| **FR-MSN-05** | **Obligations ("must") are bounded watchdogs:** sole pattern "X exceeds threshold for longer than T ⇒ Y reverts to `safe_state` (or 'alarm, summon human' state) and alerts"; T, threshold, and action all have declared bounds; no unbounded obligations. Moving toward `safe_state` does not require gate (Q-62 per FR-ACE-03); other directions pass through gate | P0 | Fish tank scenario: heater above 30 °C for > 10 minutes ⇒ shuts off heater and alarms, even during network loss if device has reflex tier; unbounded obligation ⇒ compilation rejected | Q-72 |
| **FR-MSN-06** | **Data egress:** contract declares **destinations** (LLM providers, chat channels, relays, webhooks) and data types permitted per destination; by default user-declared destinations receive user-authorized data, including photos to LLMs; **content rules** ("photos do not leave local network", closed event vocabulary) are user-enabled options. Enforced in FR-EGR | P0 | Approval summary lists all destinations and data types; probabilistic terms (e.g. "do not send photos containing human faces") explicitly marked as probabilistic | Q-72 |
| **FR-MSN-07** | **Failure handling:** for each actuator, behavior on loss of brain, network, sensor, or LLM is **reverting to `safe_state` declared in `board.v1`**, or "alarm, summon human" state when both directions are dangerous (FR-GATE-04); contracts cannot declare `safe_state` other than `off` | P0 *(pending conditional safety RFC)* | Contract declaring `safe_state` ⇒ rejected; each actuator in approval summary has "on failure" line populated from `board.v1` | Q-72 |
| **FR-MSN-08** | **Expiration:** all permissions in contract have task-level validity periods; on expiration ⇒ permissions revoked, actuators revert to `safe_state`, user notified to renew; renewal is an amendment requiring approval (FR-MSN-14) | P0 | G1 scenario fast-forwarding past expiry: command leaving `safe_state` after expiry blocked, exactly one expiration notification sent | Q-72 |
| **FR-MSN-09** | **Budgets:** contract declares `llm_budget` (LLM cost ceiling per period, e.g. $2 USD/month) and **message budget** (non-urgent messages per day); behavior on hitting ceiling in FR-AGT-05, FR-AGT-06 | P0 | Contract missing `llm_budget` when deliberation-tier terms exist ⇒ compilation rejected | Q-72 |
| **FR-MSN-10** | **Tiered compilation:** each term assigned to exactly one tier — reflex, skill, deliberation — being the lowest tier capable of enforcement; only devices with `ne_gate` have reflex tier; devices integrated via Home Assistant or remote actuators stop at skill tier, which approval summary explicitly notes; **safety terms are never placed at deliberation tier**. Modifying `NETR` layout to carry reflex terms requires RFC | P0 | Each term in compiled output has exactly one tier; safety terms lowerable only to deliberation tier ⇒ rejected | Q-72 |
| **FR-MSN-11** | **Conflict rejection before approval:** contradictory contracts (e.g. "prohibit turning off aeration" and "turn off aeration 2h–5h"), or conflicting with `safe_state` and board envelopes, are rejected **before** reaching human approvers, identifying the two conflicting terms | P0 | Closed bidirectional contradictory contract corpus — each file has single answer (`CONTRIBUTING.md` §3); 100% rejected with correct conflicting term pair (A15) | Q-72 |
| **FR-MSN-12** | **≤ 5-line approval summary:** generated **deterministically** by compiler from structured diff of contract, not from LLM-written prose; plain language; each line denotes enforcement tier; lists only non-default terms; always highlights actuators with `safe_state` other than `off`, new data destinations, and probabilistic terms. Reuses capabilities of `neuroedge gate explain`. Changes that cannot be summarized in 5 lines are not sent via chat and must be approved locally with full version *(proposed for RFC)* | P0 | Identical contract ⇒ identical byte-for-byte summary and identical digest; approval summary sent via chat never exceeds 5 lines; LLM rephrasing summary cannot alter transmitted content | Q-72 |
| **FR-MSN-13** | **Ask when ambiguous:** MCP client (Lab) or LLM worker translates user utterance into draft; missing parameters (oxygen threshold, quiet hours, alert channels) must be asked back to human, only pre-filling suggested defaults if Blueprint declares them, and human still sees that value in approval summary; draft has no effect until human locks | P0 | Draft missing required parameters ⇒ cannot compile, states parameters to prompt; no path enables unlocked draft | Q-71, Q-72 |
| **FR-MSN-14** | **Amendments follow single pipeline:** all amendments — including those proposed by operator agents — proceed draft → compile and conflict check → approval summary → human approves locally (local UI, CLI) or via approval record in chat (FR-CH-04). Amendments expanding data permissions (new destination, new data type) approved locally only | P0 | Proposal "thêm sục khí 2h–5h" ("add aeration 2h–5h") from agent ⇒ approval request in chat, inactive until approved; proposal adding data destination ⇒ cannot be approved via chat | Q-72 |

### 5.5 Chat channels and remote approvals (FR-CH)

*Planned — Q-72, increment I2d; no code yet.* The messaging channel is where users live with their devices every day: receiving reports, issuing commands, and **approving**. Because chat is a remote channel carrying text sent from outside, approval via chat is a **coded approval record**, not a freetext "Có" ("Yes"). Source `chat:<id>` follows the same runtime-assigned source grammar of RFC-0017 and **requires an RFC** (planned RFC: source `chat:<id>` + approval record). Today `HUMAN_SOURCES = ("local_grammar", "ui")` (`python/neuroedge/actions/confirmation.py`).

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-CH-01** | **Chat channel adapter in runtime:** Telegram first (I2d), Slack and Zalo later; adapter runs in trusted runtime, routes only through `dispatch()`, does not import `hal`; chat message content enters LLM worker as **untrusted data** | P0 · Slack, Zalo: P1 | Send and receive messages via Telegram in scenario G1; architectural test: chat channel package does not import `hal`; chat message containing prompt injection cannot bypass gate | Q-72 |
| **FR-CH-02** | **Commands from chat are sourced tool calls:** message from paired user becomes a tool call with runtime-assigned source `chat:<id>`, routed through `dispatch()` → gate like any source; source `chat:<id>` is **not** in `HUMAN_SOURCES` — a regular message never confirms `ask` | P0 *(requires RFC)* | Tool call from chat carrying self-declared `source` ⇒ `REJECTED`; message "Có" not targeting an approval request ⇒ confirms nothing | Q-72 |
| **FR-CH-03** | **On-site pairing:** only chat accounts paired with the home machine via a pairing code displayed **on-site** (local UI or CLI) can send commands and approvals; **chat groups never approve**. Revocation, pairing expiration, and hourly approval caps: deferred in `TODOS.md` #62, milestone before the I2d chat approval task | P0 | Message from unpaired account ⇒ dropped, traced; approval from group ⇒ rejected (A20); pairing code displayed only on local UI or CLI on the home machine | Q-72 |
| **FR-CH-04** | **Approval record:** runtime issues approval request `{id, nonce, deadline, change digest, approval summary ≤ 5 lines}` to paired chat; approval summary generated by compiler (FR-MSN-12); reply must **target exact `id`** (button or code); runtime verifies, in order: sender is paired, not a group, nonce unused, within deadline (monotonic clock), digest matches pending change — only when all pass is it admitted into confirmation path with source `chat:<id>`; each approval (passed or rejected) recorded in `trace.v1` with sender, `id`, digest, and approval summary. Applies to both runtime `ask` and contract amendments. Approvals do not pass through relay | P0 *(requires RFC)* | Scenario suite: approval from unpaired account, from group, used nonce, expired, digest mismatch (change modified after request sent), wrong `id` targeted ⇒ all rejected and traced; two concurrent pending requests are never mis-approved (A20) | Q-26, Q-72 |
| **FR-CH-05** | **LLM never approves:** LLM worker and agents have no route to submit approvals; responses drafted by LLM cannot enter chat as approvals; only approval records from paired humans enter confirmation path (FR-CH-04) | P0 | Worker sending fake approval record via MCP ⇒ rejected, traced; no tool exposed by runtime to worker can respond to approval request | Q-26, Q-72 |
| **FR-CH-06** | **User-declared verification step** *(planned · Q-73, pending RFC TSK-I2d-20)*: `on_block` can declare a verification step (reading code, voice, face, keypad, card, phone fingerprint…) via checker plugin; passing sets user-declared fact; retry limit and timeout; each method carries risk label displayed in approval summary, `gate explain`, and Blueprint | P1 | Verification step answered by LLM, MCP client, or automated source ⇒ rejected; trace records pass/fail only, no codes; risk label displayed in all three places | Q-73 |
| **FR-CH-07** | **Multi-user with roles** *(planned · Q-74, TSK-I2f-05)*: a chat space can have multiple paired users; roles determine who can command, who can approve, for which devices, in which home, during which time windows | P2 | User without approval role sends approval ⇒ rejected; role expired (tenant guest) ⇒ privileges revoked on time | Q-74 |
| **FR-CH-08** | **Phone-signed approvals** *(planned · Q-76, TSK-I2f-08)*: approval button in chat opens signing page using passkey created during pairing; home box retains public key and verifies locally; cloud shared channel gateway forwards messages but cannot forge approvals | P2 | Cloud sends "Đồng ý" ("Agree") without signature ⇒ box rejects, traces; revoked passkey ⇒ subsequent approvals rejected | Q-76 |

### 5.6 Leak-proof data flow (FR-EGR)

*Planned — Q-72, increment I2d; no code yet.* Data flow rules are designed to **prevent leaks** — hacking, prompt injection, data theft — rather than restrict user-configured flows: any user-declared destination (LLM provider, chat channel, relay, webhook) receives permitted user data, including images sent to LLM. **Residual risk, must be stated in documentation and threat model:** a compromised LLM worker can still send permitted data to permitted destinations. Destination declaration schema **requires an RFC** (planned RFC: data flow and destinations).

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-EGR-01** | **Runtime as egress gate; declared destinations only:** runtime only sends data to destinations declared in contract or configuration; sends to undeclared destinations are blocked and traced | P0 | Scenario: message or webhook to undeclared address ⇒ blocked, trace contains block event with destination (A18) | Q-72 |
| **FR-EGR-02** | **Runtime decides what worker sees:** LLM worker only receives fields permitted by data flow terms to reach LLM provider | P0 | Contract disallows images to LLM ⇒ no images in data provided by runtime to worker | Q-72 |
| **FR-EGR-03** | **Worker network sandboxed at OS level:** worker only has outbound network access to declared provider endpoints (dedicated user and firewall rules, or runtime proxy); diagnostics tool warns when network rules are absent | P0 | Worker opens connection to undeclared host ⇒ fails; missing network rules ⇒ diagnostics warning and clearly noted in approval summary | Q-72 |
| **FR-EGR-04** | **Optional content rules:** user can enable deterministic rules ("ảnh không rời mạng nội bộ" ["images never leave local network"], only emit events conforming to closed vocabulary `{zone, type, timestamp, confidence}`) — enforced at egress, absolute guarantee — and probabilistic rules ("do not send images containing human faces") — fail-closed only: do not send when uncertain. Freetext generated by LLM never leaves network when contract allows schema events only | P0 | Enabling "ảnh không rời mạng nội bộ" ("images never leave local network") ⇒ in 30-day scenario no images reach external destinations (A18); approval summary flags probabilistic rules | Q-72 |
| **FR-EGR-05** | **Optional relay is transparent TLS tunnel:** home machine initiates outbound connection to relay; relay routes destination via SNI and **does not decrypt** (Nabu Casa SniTun pattern); trace backups encrypted client-side on home machine before sending; approvals do not pass through relay; if relay is down or compromised, all safety components continue operating. This is a limited exception to "no NeuroEdge-operated servers" (Q-10) | P1 | Compromised relay sees only metadata (domain, timestamp), cannot read traces, cannot inject commands; shutting down relay mid-scenario ⇒ verdicts unchanged | Q-72 |

---

## 6. Functional Requirements — Action CI Testing

### 6.1 Four Action CI components (FR-CI)

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-CI-01** | **Record:** record complete event sequence of an actual execution run to a JSON file | P0 | `neuroedge record --target esp32s3` produces valid file conforming to schema | §3.7 |
| **FR-CI-02** | **Replay:** reproduce that event sequence across any environment | P0 | Same trace file yields identical verdict sequence across all environments | §3.7 |
| **FR-CI-03** | **Assert:** behavioral assertion library — actions blocked, which gate blocked, escalation destination, which pin remained unasserted | P0 | Four assertion groups executable in pytest | §4.7 |
| **FR-CI-04** | **Golden Reference:** anchor reference verdict sequence; deviation from golden reference turns CI red | P0 | Changing prompt causes verdict divergence → CI fails, pinpointing divergence point | §3.7 |
| **FR-CI-05** | Action CI runs automatically on `sim` and `linux` on every pull request | P0 | Sample CI pipeline available in scaffold project | §3.2 |
| **FR-CI-06** | Action CI runs automatically nightly on real `esp32s3` hardware | P0 | Nightly runner configuration and reporting available | §3.2 |
| **FR-CI-07** | `neuroedge verify` command checks consistency of gate verdicts and GPIO states across tier 1 environments | P0 | Discrepancy raises `SafetyRegressionError` (NE4002) pinpointing first diverging event | §8.2 |

### 6.2 Three levels of assurance (FR-CI-LVL)

This is the most critical technical boundary of the product: **Action CI does not assume language models are deterministic functions.**

| Mã | Cấp độ | Tính xác định | Action CI khẳng định điều gì | Ưu tiên |
|:---|:---|:---:|:---|:---:|
| **FR-CI-L1** | Gate verification (rule engine): `allow_when` expressions, value comparisons, latency budgets | 100% deterministic | Bit-exact replay; verdicts compared strictly against Golden Reference | P0 |
| **FR-CI-L2** | Structured System 1 decisions: intent classification, entity extraction, fixed schema | Near-deterministic | Verify JSON schema compliance and validate `confidence >= threshold` | P0 |
| **FR-CI-L3** | Open System 2 reasoning (LLM): free-form text generation | Non-deterministic | **Do NOT assert on generated text strings.** Assert only on **gate verdicts (ALLOW/BLOCK)** and **GPIO pin states** | P0 |

**Acceptance consequence:** a valid Action CI test **MUST NOT** contain assertions matching text strings generated by System 2. This rule must be automatically enforced by linting tools in scaffold projects.

### 6.3 Trace schema (FR-TRC)

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-TRC-01** | Traces are JSON conforming to JSON Schema draft 2020-12, published publicly at `https://schema.neuroedge.dev/trace/v1.json` | P0 | Accessible URL, valid schema | §3.7 |
| **FR-TRC-02** | Trace contains complete `metadata` block: `session_id`, `timestamp_utc`, `target`, `board_id`, `agent_version` | P0 | Missing any field → `neuroedge trace validate` reports error | §3.7 |
| **FR-TRC-03** | Trace covers 6 event categories: input, perception, model decision, gate evaluation, actuator command, output | P0 | Sample session produces all 6 categories | Appendix C.1 |
| **FR-TRC-04** | Traces are **replayable across all environments** | P0 | FR-CI-02 passes | Appendix C.2 |
| **FR-TRC-05** | Format is **stable across versions**: legacy traces replay successfully after minor upgrades | P0 | Regression trace suite from previous version continues to run | Appendix C.2 |
| **FR-TRC-06** | Traces are **human-readable**, requiring no specialized tools | P0 | Open in text editor and understand sequence | Appendix C.2 |
| **FR-TRC-07** | **Anonymization at source mode:** configuration flag replaces raw content with hash, preserving decision sequence | P0 | Enabling flag → no raw audio or text data remains, replay remains valid | Appendix C.2 |
| **FR-TRC-08** | Command `neuroedge trace validate <file>` validates file against JSON Schema | P0 | Malformed file caught before commit | §3.7 |
| **FR-TRC-09** | Adheres to path conventions: `traces/`, `traces/incidents/<session_id>.json`, `traces/golden/<scenario>.json` | P1 | Scaffold project generates three pre-configured directories | §3.7 |
| **FR-TRC-10** | Schema registered on public SchemaStore for automatic IDE recognition | P1 | VS Code auto-suggests when opening trace file without installing NeuroEdge tools | §3.7 |
| **FR-TRC-11** | **Segmented traces for 24/7 runtime** *(Q-72, requires RFC `trace.v1`)*: operator agent traces are a **sequence of segments** over time (daily, or sooner when exceeding size); each segment carries **segment-head state** (gate digest, token ledger, envelope counter, active lease) and digest of previous segment. Invariant "one trace per session" becomes "one session as a trace sequence, each segment replayable" | P0 | `replay` of an individual segment yields identical verdicts as runtime, including envelope counters and leases spanning segment boundaries; missing or modified segment ⇒ digest chain points to exact break; single-session trace retains format | Q-72 |
| **FR-TRC-12** | **Record and retain traces on home machine** *(Q-72)*: append logging, flushed periodically (default ~10 seconds, configurable) and **immediately** upon block verdict or approval; retain latest **30 days** on-site, older segments compressed then deleted or exported via encrypted relay (FR-EGR-05); power loss loses at most tail of regular events, and `replay` reports truncated segment | P0 | Power loss scenario mid-segment: all block verdicts and approvals prior to power loss remain in trace; `replay` reports truncated segment instead of reporting pass; 30-day size measured on G1 and recorded in NFR-OBS-04 | Q-72 |
| **FR-TRC-13** | **New events for Q-72** *(requires RFC `trace.v1`)*: approval requests and approvals (sender, `id`, digest, approval summary, check result), detector triggers, sends to destination (destination, data type, blocked or not), cumulative periodic LLM cost, reaching budget caps, runtime or worker restarts, `unsynced` clock | P0 | 30-day aquarium scenario produces all above event types and passes `neuroedge trace validate` | Q-72 |

### 6.4 Open schema governance (FR-GOV)

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-GOV-01** | Gate and trace schemas published publicly under Apache-2.0 license (Q-45) | P0 | Public schema repository with license file | §3.8 |
| **FR-GOV-02** | Schema versioning managed via URL paths (`/v1`, `/v2`); breaking changes strictly require major version bump | P0 | Version policy document in schema repository | §3.8 |
| **FR-GOV-03** | **Compliance test suite:** publish reference trace suite with expected replay outcomes for third-party independent verification | P0 | Third parties can run test suite without proprietary certification | §3.8 |
| **FR-GOV-04** | All schema changes go through public RFC process on GitHub | P1 | RFC template available and at least one RFC processed | §3.8 |

---

## 7. Functional Requirements — Developer Experience

### 7.1 Scaffolding and developer loop (FR-DX)

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-DX-01** | `neuroedge new <name>` generates scaffold project containing: `agent.toml`, 1 action, 1 gate, 1 CI test scenario | P0 | New project runs `neuroedge test` successfully out of the box without modifications | §4.8 |
| **FR-DX-02** | Installing and running `sim` **does not require** an account, API key, or credit card. Default input for `sim` is **typed text** → command grammar matcher; voice is optional *(Q-15)* | P0 | Clean machine, no specialized LAN, no keys: complete 10-minute journey via typed commands. `pip install neuroedge` does not pull LiteLLM — cloud dependencies reside in `neuroedge[cloud]` extra *(Q-10)* | §4.10 |
| **FR-DX-03** | Median time-to-first-value under 10 minutes, measured across 10 independent developers | P0 | Measurement protocol records timestamped steps for all 10 developers | §12.1 |
| **FR-DX-04** | All error messages clearly state: what went wrong, where, and how to fix it | P0 | Review of all error codes in Appendix B confirms all 3 components present | §4.9 |
| **FR-DX-05** | Documentation provides at least 3 complete runnable sample applications | P0 | Three samples run successfully on clean machine following instructions *(progress: TSK-S3-08)* | §12.1 |
| **FR-DX-06** | Documentation provides at least 1 video or animated visual demo in README | P0 | Visual asset under 30 seconds demonstrates value loop | §12.1 |
| **FR-DX-07** | Scaffold project lint tool blocks text matching assertions generated by System 2 | P1 | Test violating FR-CI-L3 flagged as lint error | §3.7 |
| **FR-DX-08** | `neuroedge add` generates `@action` + gate + bi-directional tests + `[requires]` declaration for all primitives, from bundled templates | P0 | On scaffold project: `gate lint` clean, ALLOW and BLOCK tests green; re-running does not overwrite existing files | Q-52 |
| **FR-DX-09** | Reference kit for each primitive package: BOM, wiring diagram, board profile, locked gate, golden trace, "from box to live execution" guide. *Extended by Q-72:* **kit catalog** with BOM including purchasing links (affiliate links, no inventory held), starting with **aquarium kit** (I2e); kit is the `kit` section of a NeuroEdge Blueprint (FR-BP-01) and testable on simulation before purchase | P0 | A12. *Q-72:* aquarium kit includes BOM with purchase links for each component, runnable on G1 before purchase | Q-52, Q-72 |
| **FR-DX-10** | NeuroEdge Lab: client-agnostic MCP tool suite enabling an MCP client (Claude Code, Claude Desktop…) to draft `@action` + gate `0.1.0-draft` + bi-directional tests for all primitives — NeuroEdge grades drafts (`neuroedge lab check`, shared code between tool and Action CI) without invoking LLMs internally; draft is locked only after `gate lint` and human review via PR — no tool can lock policies. *Extended by Q-72:* Lab represents **Loop ①** — from action up to **mission contract**: client drafts `mission.v1` (FR-MSN-13), NeuroEdge grades via identical compiler and conflict checks, human locks; and `neuroedge lab doctor` inspects **each sensor** during assembly (e.g., *"cảm biến oxy đọc 0 — kiểm lại dây"* ["oxygen sensor reads 0 — re-check wiring"]), in addition to existing privilege separation warnings. Loop ① scope for missions moved from I4a into I2d | P0 | A11. *Q-72:* an aquarium mission contract drafted by MCP client via Lab tools passes checks and is human-locked; `lab doctor` pinpoints incorrectly reading sensor in scenario G2 | Q-55, Q-71, Q-72 |

### 7.2 Command-line interface (FR-CLI)

**Exit code contract** *(`CHANGELOG.md` §2.3 — CI and Action CI anchor on it)*: `0` check executed and **passed** · `1` executed and **failed** · `2` command **not yet implemented** (or command syntax error). Unimplemented commands **MUST NOT** exit with code 0.

| Mã | Nhóm lệnh | Lệnh bắt buộc | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---|:---:|:---|:---:|
| **FR-CLI-01** | Scaffolding | `neuroedge new <name>` | P0 | Generated project runs `neuroedge test` exiting with code 0 immediately without modification (FR-DX-01) | §4.8 |
| **FR-CLI-02** | Development | `neuroedge run --target sim` · `neuroedge run --target linux` · `neuroedge build --target esp32s3 --board <id>` | P0 | `run --target sim` accepts typed commands without keys *(Q-15)*, verifies agent ↔ board capabilities before running (mismatch → code 1); `run -c "<cmd>"` executes one command and exits 0 even when gate blocks; `build` encountering capability mismatch → code 1, does not generate firmware (FR-HAL-04) | §4.8 |
| **FR-CLI-03** | Testing | `neuroedge test` · `neuroedge verify --targets sim,linux,esp32s3` | P0 | `test` exits 0 when all assertions pass, 1 when any assertion fails; `verify` mismatch across targets → code 1, pinpointing first diverging event (FR-CI-07); scanning 0 artifacts (gates, canonical traces, or replays) → `VerificationError` (NE4004), code 1, does not exit 0 (TSK-S3-19); `esp32s3` requires `--port`: firmware replays canonical traces, host compares to golden (TSK-S4-09, `docs/spec/simulation_coverage.md` §4); missing `--port` ⇒ code 1 | §4.8 |
| **FR-CLI-04** | Diagnostics | `neuroedge record --target <t> --out <dir>` · `neuroedge trace validate <file>` · `neuroedge replay <file> --target <t>` · `neuroedge trace view <file>` · `neuroedge trace export --format chrome <file>` | P0 · `view`/`export`: P1 | `record` generates file passing `trace validate`; `trace validate` on any invalid file → whole command exits 1 with `TraceValidationError`; `replay` yields identical verdict sequence (FR-CI-02); `record --target esp32s3 --port <port>` reads trace over UART (including on QEMU); `trace view` generates static HTML file viewable offline | §4.8 |
| **FR-CLI-05** | Gate ecosystem | `neuroedge gate publish <file>` · `neuroedge gate add <uri>` · `neuroedge gate explain <file\|uri>` | P1 | `publish` prints SHA-256 hash of canonical RFC 8785 JSON, two runs yield identical hash; `add` resolves gate from registry and states imposed inheritance constraints; `explain` states which level introduced each criterion, which clauses child tightened vs parent, budgets, and `on_block` — resolution error → code 1 with 3-part error | §4.8 |
| **FR-CLI-09** | Gate safety gate | `neuroedge gate lint [dir] [--registry <dir>]` | P0 | **This is a safety check gate**, not schema validation: resolves full `extends` chain of all gates and enforces Appendix B.5 principles (including Q-18 extensions). Violation → code 1 with `GateInheritanceError` or `GateSchemaError`; negative fixture corpus `fixtures/gates/invalid/` MUST exit **strictly** with code 1 in CI. Individual schema validation is insufficient to conclude a gate is safe | Appendix B.5 |
| **FR-CLI-10** | Gate resolution | `neuroedge gate resolve <file\|URI> [--json] [--registry <dir>]` | P0 | Prints effective policy and hash; invalid chain → code 1 with identical error as `gate lint`; same input yields identical hash | Appendix B.5 |
| **FR-CLI-11** | Boards | `neuroedge board list` · `neuroedge board show <id>` · `neuroedge board validate <path>` *(RFC-0002 PR2, Phase 2)* | P0 · `validate`: Phase 2 | `board show` prints capabilities across 5 primitives (FR-HAL-01); `board validate` with schema-violating file → code 1 with `BoardCapabilityError`; prior to RFC-0002 PR2, `board validate` exits code 2 | §4.2, RFC-0002 |
| **FR-CLI-12** | Tool integration | `neuroedge mcp tools [--json\|--openai] [--external]` · `neuroedge mcp serve [--agent a.toml] [--ui] [--http …]` · `neuroedge mcp desktop-config [--agent a.toml] [--ui] [--lab] [--write]` | P1 | `tools` prints schema of each `@action`; `serve` is stdio MCP server (`--ui`: same session as `sim` web UI; `--http`: over network via Streamable HTTP, mTLS and per-device OAuth 2.1 tokens, disabled by default, missing config piece ⇒ code 1 before binding port — NFR-SEC-09, TSK-P2-04; `--ui --http`: same-session home page is sole place to answer `ask`), each `tools/call` passes through `dispatch()` and gate (Q-24); `desktop-config` prints (or writes, with backup, exactly one `mcpServers` entry) Claude Desktop configuration using absolute paths; `--lab` *(I4a, TSK-N1-05)* configures lab agent in one step, still exactly one `mcpServers` entry and all lab tools still pass through gate; missing `mcp` extra ⇒ code 1 with installation instructions | §4.8 |
| **FR-CLI-13** | NeuroEdge Blueprint *(Q-72, I2e; planned)* | `neuroedge blueprint pack [dir]` · `neuroedge blueprint install <url\|file> [--digest <sha256>]` | P0 | `pack` prints whole-package digest, two runs yield identical digest, rejects package missing evidence or containing unlocked gates (code 1); `install` digest mismatch ⇒ code 1, writes no files; displays approval summary prior to activation (FR-BP-02, FR-BP-03) | Q-72 |
| **FR-CLI-14** | Chat channels *(Q-72, I2d; planned)* | `neuroedge chat connect <channel>` · `neuroedge chat pair` | P0 | `connect telegram` stores bot token in runtime configuration, does not print token; `pair` runs only on home machine and displays pairing code on-site (FR-CH-03); unsupported channel ⇒ code 2 | Q-72 |
| **FR-CLI-15** | Missions and operator agents *(Q-72, I2d; planned)* | `neuroedge mission check <file>` · `neuroedge mission explain <file>` · `neuroedge agent run` | P0 | `mission check` exits 0 when contract compiles, 1 with 3-part error on schema violation or conflict (FR-MSN-11); `mission explain` prints deterministic approval summary ≤ 5 lines (FR-MSN-12); `agent run` boots trusted runtime (FR-AGT-01), rejects execution when contract is unlocked. Command names finalized in `mission.v1` RFC | Q-72 |

**General requirements for all CLI commands:**

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu |
|:---|:---|:---:|:---|
| **FR-CLI-06** | All commands return exit codes conforming to the `0`/`1`/`2` contract above for CI integration | P0 | CLI tests strictly pin exit code of each command; CI step checking negative corpus strictly matches code 1 |
| **FR-CLI-07** | All commands provide `--help` thoroughly describing parameters and usage examples | P0 | `--help` for every command exits 0 and contains at least one example; automated tests traverse all commands |
| **FR-CLI-08** | Long-running commands display progress; destructive commands require confirmation | P1 | `build`, `verify`, `record` display progress; commands deleting or overwriting data do not run without confirmation and exit non-zero |

### 7.3 Third-party extensions (FR-EXT)

Design: `docs/architecture/vi/16-ecosystem-landscape.md` §4; contracts in RFC-0016, RFC-0017,
RFC-0018 (`docs/rfc/`). Decisions: Q-67.

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-EXT-01** | **Safety core standalone usage:** `neuroedge.guard` API for any arbitrary program (proxy, bridge, robot node) — gate → token → envelope → trace, does not require `agent.toml`, `@action`, or `SimSession` | P0 | Short program gates an action and records valid trace without `agent.toml` | Q-67 |
| **FR-EXT-02** | **Six extension point types via entry points:** bridge, fact source, actuator, board, template, exporter. Plugins load only when explicitly enabled; failed load or SDK version mismatch ⇒ does not start; origin printed and recorded in trace | P0 | For each type, an out-of-tree package installed via `pip` runs without modifying core code | Q-67 |
| **FR-EXT-03** | **Structural invariants of plugins:** bridge can only submit tool requests without `source` through dispatcher provided by core (core assigns `bridge:<id>`), no HAL handle; fact source cannot self-declare fact age; actuator driven by HAL only after token and envelope | P0 | Compliance test suite proves each invariant; A3 remains 0 shortcuts | Q-67 |
| **FR-EXT-04** | **Compliance test suite per plugin type:** `neuroedge conformance <package>`, machine-readable results | P0 | Sample plugin passes; each check has a negative test case caught | Q-67 |
| **FR-EXT-05** | **Out-of-package assets:** `--board <path>` for community boards (self-certified, never reference boards); templates from path, package, or commit-pinned git; multiple gate registry roots; `extends` can be digest-pinned | P0 | Each source covered by tests; `verify` never includes out-of-tree boards in tier 1 equivalence | Q-67, RFC-0002 |
| **FR-EXT-06** | **Two universal proxies:** `neuroedge proxy mcp` wrapping an existing MCP server (`guard init --mcp` generates default-block gate for each tool) and `neuroedge proxy http` | P0 | Wrap existing MCP server in ≤ 3 commands; diagnostics tool warns when destination is reachable bypassing proxy | Q-67 |
| **FR-EXT-07** | **Remote actuators** declare explicit auto-shutdown levels; non-undoable actions require level where device auto-shuts down even on loss of connectivity | P0 | Conforms to RFC-0018 §7; Home Assistant adapter matches its declared level | Q-67 |
| **FR-EXT-08** | **Discovery and distribution:** community index (dedicated repo, Apache-2.0), `neuroedge plugin search/install`, "NeuroEdge-gated" badge granted only upon passing FR-EXT-04. No fees, no paid placement. This index is **for plugins only** and permanently free; NeuroEdge Blueprints have a separate index using the same static repo pattern (FR-BP-05), which is the sole monetization venue, and only after the 8-week demand gate (§14, Q-72) | P1 | Third-party plugin installed from index displays compliance results | Q-67, Q-72 |
| **FR-EXT-09** | **`neuroedge.sdk` stability:** independent versioning; stricter commitment than package `0.x` level (`docs/spec/python_api.md`) | P0 | Tests pin SDK surface like `test_public_api.py` pins `__all__` | Q-67 |

### 7.4 NeuroEdge Blueprint (FR-BP)

*Planned — Q-72, increment I2e (after I2d); no code yet.* **NeuroEdge Blueprint** is the sharing and commercial distribution unit of Loop ③: a declarative bundle comprising **kit** (`board.v1` profile + BOM with purchasing links), **firmware** (firmware generation config with `ne_gate`), **sample mission contract** with prompt parameters, locked gate, **detectors**, and **evidence traces**. It differs from a **Home Assistant Blueprint** (automation template shared on Blueprint Exchange, imported via URL); a NeuroEdge Blueprint can bundle an HA blueprint allowing HA users to install both in a single step. The `blueprint.v1` schema touches `schemas/` and therefore **requires an RFC** (planned RFC); its relationship with `manifest.v1` of the Gate Registry (FR-REG-02) is decided in that RFC.

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-BP-01** | **Package format:** manifest `blueprint.v1` (requires RFC) enumerates above sections, author, SemVer version, license; package is **declarative only** — no arbitrary code executes on home machine during installation; firmware regenerated from board config, prebuilt binaries if provided carry dedicated digests; optionally bundles HA blueprint | P0 | Schema-violating package ⇒ rejected with 3-part error; package containing undeclared files ⇒ rejected | Q-72 |
| **FR-BP-02** | **`neuroedge blueprint pack`:** bundles components into package, computes **whole-package digest** (kit, firmware, sample contract, gates, detectors, evidence traces; SHA-256 over canonical format like `gate publish`); rejects packages with unlocked gates, missing evidence traces, or failing evidence `replay` | P0 | Two runs of `pack` on identical content yield identical digest; modifying one byte anywhere ⇒ digest changes; package with `-draft` gate ⇒ code 1 (FR-CLI-13) | Q-72 |
| **FR-BP-03** | **`neuroedge blueprint install`:** fetch via URL (git or HTTPS) or file, **verifies whole-package digest** prior to writing any files; executes evidence `replay` on installer's machine; prompts for parameters; displays approval summary (permissions, data destinations, actuators with `safe_state` other than `off`, "unsigned evidence" badge) before activation; does not self-lock contract — installing human approves | P0 | Digest mismatch ⇒ rejected, 3-part error, zero files written; third party outside team installs aquarium Blueprint on clean machine and runs on `sim` in < 10 minutes, no account (A14) | Q-72 |
| **FR-BP-04** | **Evidence:** `trace.v1` trace executed live or on simulation, clearly stating tier (G1–G4 or real hardware) and duration; **no Blueprint can be sold without evidence** passing `replay`. At MVP evidence is **unsigned** — seller can edit traces — thus all display surfaces explicitly state "unsigned"; signed traces revisit before Hub monetization for sellers (`TODOS.md` #1) | P0 | `install` and index display "unsigned" and evidence tier; evidence failing `replay` ⇒ `install` rejected | Q-72 |
| **FR-BP-05** | **Minimal Hub is static index:** a static index repository (same style as plugin index in FR-EXT-08, TSK-I2c-18) enumerating URL, digest, author, license, evidence tier, and "unsigned" badge; sellers self-host packages (e.g., on GitHub); no NeuroEdge servers, no accounts, no fees, no paid ranking until after 8-week gate; transitions to OCI Registry (H2, FR-REG) when Hub monetizes | P0 | `blueprint install` from index entry verifies exact digest specified in index; index contains zero server-side runtime components | Q-72 |
| **FR-BP-06** | **Package safety:** sample contracts and gates in package cannot declare `safe_state`; bundled `board.v1` profile with `safe_state` other than `off` must declare hardware interlocks (FR-ACE-03), and `blueprint install` highlights each such actuator **separately**, installer confirms on-site; all package permissions and data destinations displayed in approval summary | P0 *(pending conditional safety RFC)* | Package declaring `safe_state` in contract ⇒ rejected; profile with `safe_state: on` lacking interlock ⇒ loading rejected (A21); installation approval summary isolates `safe_state: on` actuators | Q-72 |
| **FR-BP-07** | **Kit with linked BOM:** Blueprint BOM lists part numbers and purchase links (affiliate links, NeuroEdge holds no inventory); aquarium kit is first kit (FR-DX-09) | P0 | Every component of aquarium kit has at least one purchase link; BOM matches declared capabilities in board profile | Q-72 |
| **FR-BP-08** | **License in manifest:** each Blueprint specifies its license; personal use is free; selling Blueprints or hardware built with NeuroEdge is commercial use (Q-45, PolyForm Noncommercial) governed by NeuroEdge commercial license (terms: `TODOS.md` #44) | P1 | `install` displays license; index displays license for each entry | Q-45, Q-72 |
| **FR-BP-09** | **Consented data sharing:** user can opt into sharing anonymized operational data to improve detectors of a Blueprint; **disabled by default**, routed through egress like any other destination (FR-EGR-01) | P2 | Unchecked ⇒ zero data leaves machine for this purpose; enabled ⇒ destination displayed in approval summary (NFR-PRIV-05) | Q-72 |
| **FR-BP-10** | **Monetized Hub** *(post 8-week gate)*: Blueprint revenue sharing, payments, seller dashboard; gating conditions: 8-week gate met (B6–B8), signed traces (`TODOS.md` #1), distribution migrated to OCI Registry using FR-REG rails (identity, metering, authorization) | P2 | Specified once gate is achieved, governed by new `Q-N` decision | Q-72 |


---

## 8. Functional Requirements — Commercial Service Layer

**§8.1 (FR-GW) belongs to the core**, delivered across two milestones (Q-28: FR-GW-01 and 03 minimal in v1.0, remainder in v1.1) — a user-operated provider abstraction layer with no service fees (commercial use requires core license — Q-45). **§8.2 (FR-FLT) and §8.3 (FR-REG) belong to milestone v1.1**, initiated only upon meeting conditions in §3.3. **Revenue streams under Q-72:** PolyForm Noncommercial is the monetization mechanism — free for personal use, selling Blueprints or hardware is commercial use (§8.4). NeuroEdge does not resell tokens (N4): users pay LLM providers directly with their own keys.

### 8.1 Model provider abstraction layer (FR-GW)

The FR-GW group belongs to **core**; delivery milestone of each requirement follows Q-28 and §3.2. Users operate this layer themselves, configure providers, and retain keys; NeuroEdge does not operate intermediary gateways and does not resell tokens.

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-GW-01** | Self-hosted abstraction layer provides single endpoint and single credential for all model providers | P0 | Single configuration serves multiple providers; devices do not hardcode keys for individual providers | §6.1 |
| **FR-GW-02** | Security keys managed by user within self-hosted layer, rotatable without reflashing firmware | P0 | Rotate keys across 10 active devices without service interruption | §6.1 |
| **FR-GW-03** | Multi-provider routing with automatic failover — core feature | P0 | Disconnecting primary provider → devices observe no interruption | §6.1 |
| **FR-GW-04** | Protocol optimized for edge devices: persistent WebSocket, binary audio frames, streaming responses — core feature, not a paid service | P0 | Microcontroller does not perform TLS handshake for each request | §6.1 |
| **FR-GW-05** | Per-device hard usage caps — optional within self-hosted layer | P1 | Buggy looping device blocked upon hitting cap, generates alert | §6.1 |
| **FR-GW-06** | Semantic cache and System 1 / System 2 ratio telemetry — core option | P1 | Reports ratio and cost savings broken down by task group | §6.1 |
| **FR-GW-07** | Abstraction layer exports JSON trace files in **identical format** with Action CI for each session | P0 | Traces from provider layer replayable locally without transformation | §6.1 |

### 8.2 Fleet management operating system (FR-FLT)

| Mã | Yêu cầu | Ưu tiên | Tiêu chí nghiệm thu | Nguồn |
|:---|:---|:---:|:---|:---:|
| **FR-FLT-01** | Provision unique cryptographic identity and certificate per device on first boot | P0 | Automated claiming workflow succeeds on batch of 100 devices | §6.2 |
| **FR-FLT-02** | Coordinate OTA updates via canary phases 1% → 10% → 100%, automatically pausing and rolling back when failure rate exceeds threshold | P0 | 1,000-device campaign, 0 bricked devices | §6.2, §12.2 |
| **FR-FLT-03** | Inventory ledger and health monitoring: online/offline, firmware version, RSSI, chip temperature, boot loop alerts | P0 | Dashboard reflects accurate status within 60 seconds | §6.2 |
| **FR-FLT-04** | Remote update of configuration, secrets, and **gates** without reflashing firmware | P0 | Modify gate thresholds fleet-wide, taking effect without restart | §6.2 |
| **FR-FLT-05** | Automatically upload JSON trace files to central repository when device triggers alert | P0 | Field incidents appear in repository within 5 minutes | §6.2 |
| **FR-FLT-06** | Virtual devices in `sim` appear immediately on Fleet Dashboard | P0 | Dashboard useful at scale n = 1, requires no physical hardware | §6.2 |

### 8.3 Platform infrastructure rails (FR-REG)

Seven rails (FR-REG-01→07, matching `docs/architecture/vi/15-target-architecture.md` §3.2) are cheap early on but **impossible to add later**. FR-REG-08 is an extension of Rail 1 (Registry repository), not an eighth rail. Under Q-72, these rails also serve as the **foundation for the monetized Hub** for NeuroEdge Blueprints post-8-week demand gate (FR-BP-10): manifests and identity for packages, metering for revenue share, access control for untrusted packages.

| Mã | Thành phần | Giá trị ngày đầu | Vai trò dài hạn | Ưu tiên |
|:---|:---|:---|:---|:---:|
| **FR-REG-01** | Free public Gate registry | `neuroedge gate add <uri>` | Most heavily reused policy data | P0 |
| **FR-REG-02** | Manifest and SemVer version standard | Transparent dependency management | Distribution unit of Marketplace | P0 |
| **FR-REG-03** | Hardware capability declaration | Block incompatibility errors at build time | Pre-installation compatibility checks | P0 |
| **FR-REG-04** | Versioned gates supporting `extends` | Safety policy reuse | Highest-value tradable asset | P0 |
| **FR-REG-05** | Stable identities for devices, agents, gates | Precise debugging and lookup | Revenue and responsibility attribution | P0 |
| **FR-REG-06** | Metering system per agent call and gate evaluation | Usage telemetry | Foundation for revenue distribution | P0 |
| **FR-REG-07** | Authorization mechanism and sandbox | Safety when testing untrusted agents | Prerequisite to execute third-party code on actuator-bearing devices | P0 |
| **FR-REG-08** | Shared provider adapter registry | Users download existing adapters instead of rewriting | Network effect wedge easier to form than gates since provider connectivity is an immediate need | P1 |

**Architectural warning:** FR-REG-05, FR-REG-06, and FR-REG-07 must be designed upfront in v1.1. Lacking them, the system cannot later reconcile revenue or permit third-party code execution on devices with physical actuators.

### 8.4 Revenue streams under Q-72: kits, Blueprint Hub, per-device licensing, relay

All revenue streams below are **optional** for users and **never sit on the safety path**: reflex, gate, contract, and approvals continue running if they fail or shut down. Tracking metric: C6 (§11.3). Order reflects timeline tiers in proposal Q-72; which stream enters first is decided by the 8-week demand gate.

| Dòng thu | Ai trả | Khi nào | Điều kiện, yêu cầu dẫn |
|:---|:---|:---|:---|
| **Kit commissions** (affiliate links, no inventory held) | Component suppliers (U9) | **Initial revenue exploration** — aquarium kit in I2e | FR-BP-07, FR-DX-09; measured via seller affiliate reports |
| **NeuroEdge Blueprint revenue share** | Makers selling Blueprints (U5) | Post-8-week gate | Monetized Hub FR-BP-10: gate met, signed traces (`TODOS.md` #1), OCI Registry and FR-REG rails |
| **Commercial license per device** | Micro-OEMs, hardware startups selling devices (U5); enterprises using core (U2) | Upon first commercial seller | Q-45 (PolyForm Noncommercial); terms, pricing, trials: `TODOS.md` #44. Core safety features always included in license, no premium unbundling (P-3) |
| **Optional cloud relay** — remote access, push notifications, encrypted trace backup | End users (U8), makers | Post-minimal Blueprint; sequencing decided by 8-week gate | FR-EGR-05, NFR-SEC-15; limited exception to Q-10 |
| **NeuroEdge Cloud subscription** — home watch agent requiring only chat, multi-device and multi-home orchestration *(Q-74 Step 2, conditional)* | End users (U8), homestay hosts, multi-property families | Only if 8-week gate metrics indicate testers struggle with setup, API keys, or self-hosting | FR-AGT-10, FR-AGT-11; amends N4 when activated |
| **Fleet OS** | Fleet operations teams (U3) | v1.1 — post-8-week gate and §3.3 conditions | §8.2 (FR-FLT) |
| **Physical capabilities for third-party AI agents called via MCP**; industry aggregate metrics from consented data | Third-party AI agents; aggregate data buyers | Distant — unspecified | No requirement yet; requires dedicated `Q-N` |

**Invariant until Q-74 Step 2 activation:** NeuroEdge does not resell tokens (N4) and does not store user LLM keys on its servers (NFR-SEC-13). Cloud subscription, if activated, uses NeuroEdge keys; user BYOK keys never leave the home box.

---

## 9. Non-Functional Requirements

### 9.1 Performance and Latency (NFR-PERF)

| Mã | Chỉ tiêu | Ngưỡng cam kết | Điều kiện đo | Ưu tiên |
|:---|:---|:---|:---|:---:|
| **NFR-PERF-01** | Full round-trip voice response latency — streaming-capable provider | **P95 < 850 ms** | Wi-Fi connection, streaming-capable STT/LLM/TTS provider, from speech end until speaker emits sound | P0 — *paused (Q-72)* |
| **NFR-PERF-02** | Gate evaluation latency — local processing | **P95 < 120 ms** | On Tier 1 environments | P0 |
| **NFR-PERF-03** | Gate evaluation latency — when cloud provider data is required | **P95 < 450 ms** | Stable network | P0 |
| **NFR-PERF-04** | Structured `SystemOne` decisions | **< 100 ms** | Local model or fast model via provider abstraction layer | P0 |
| **NFR-PERF-05** | Dual-model routing efficiency | Saves **≥ 60%** token cost compared to forwarding entirely to System 2 | Measured on real traffic, broken down by task category. *Q-72:* NeuroEdge does not resell tokens, so this metric measures benefit for users paying for their own LLM (BYOK); for operator agents, the cost constraint is an **absolute ceiling** NFR-COST-01, not a savings percentage | P0 |
| **NFR-PERF-06** | Action CI execution time for sample project | **< 30 seconds** on `sim` | Typical development machine | P1 |
| **NFR-PERF-07** | Full round-trip voice response latency — request-response provider | **P95 < 1,500 ms** | Wi-Fi connection, non-streaming provider, from speech end until speaker emits sound | P1 — *paused (Q-72)* |

### 9.2 Resources and Hardware Constraints (NFR-RES)

| Mã | Chỉ tiêu | Yêu cầu | Ưu tiên |
|:---|:---|:---|:---:|
| **NFR-RES-01** | `esp32s3` runtime runs stably on reference board with audio capture/playback pipeline, conversation state machine, and gate evaluation *(STT/TTS hosted at cloud provider)* | No memory leak / out-of-memory over 24 hours of continuous operation | P0 |
| **NFR-RES-02** | Minimum free SRAM/PSRAM budget remaining for runtime | Free SRAM ≥ 120 KB · PSRAM ≥ 2 MB *(decided in §15 of this document, Q-3; easier to achieve since v1.0 due to cloud-first under CR-1.0 — Change Request 1.0, 2026-09-21: shifted to cloud-first, provider-pluggable; full record in `CHANGELOG.md`)* | P0 |
| **NFR-RES-03** | Maximum firmware size for reference board | ≤ 3.5 MB *(decided in §15 of this document, Q-3 — fits dual A/B partitions on 16 MB Flash)* | P1 |
| **NFR-RES-04** | System fully operational on core when Internet connectivity is lost | 100% of safety features operate offline | P0 |

### 9.3 Reliability (NFR-REL)

| Mã | Chỉ tiêu | Ngưỡng cam kết | Ưu tiên |
|:---|:---|:---|:---:|
| **NFR-REL-01** | Large-scale OTA update reliability | **1,000 devices / 0 brick incidents** | P0 |
| **NFR-REL-02** | Default behavior under degraded component conditions | **Commands:** `fail: closed` — block physical action. **Actuators:** revert to `safe_state` declared in `board.v1` — default `off`, maintaining existing behavior unchanged *(pending conditional safety RFC — Q-72, FR-ACE-03)* | P0 |
| **NFR-REL-03** | Nightly testing on real hardware | Runs nightly, reports results and trends | P0 |
| **NFR-REL-04** | Old traces replayable across minor version upgrades | 100% of regression trace suites continue to run | P0 |
| **NFR-REL-05** | Reflex on loss of network or loss of LLM *(Q-72)* | **100%** of reflex tier and skill tier terms remain enforced when network is lost, LLM worker is lost, or LLM budget is exhausted; only analysis halts | P0 |
| **NFR-REL-06** | 24/7 runtime liveness *(Q-72)* | Runtime restarts automatically after failures or power loss; dead worker does not stop runtime; runs continuously for **2 weeks** on G2 or G3 without intervention (B7) | P0 |

### 9.4 Security (NFR-SEC)

Defense layers follow `docs/spec/threat_model.md` — physical action, untrusted caller (NFR-SEC-09), device, network, privacy *(specified separately in §9.5 of this document)*, update — operate by default. The table below adds two requirement groups beyond those layers: third-party code (track 7, `docs/architecture/vi/15-target-architecture.md` §3.2) and external providers (consequence of P-4).

| Mã | Lớp | Yêu cầu | Ưu tiên |
|:---|:---|:---|:---:|
| **NFR-SEC-01** | Physical action | No shortcuts to actuators outside gates; all gate evaluations are traced | P0 |
| **NFR-SEC-02** | Device | Enable Secure Boot and flash encryption on ESP32-S3; support TPM on Linux | P0 |
| **NFR-SEC-03** | Device | Reference board has a physical microphone kill switch | P0 |
| **NFR-SEC-04** | Network | TLS 1.3 end-to-end; mutual mTLS device ↔ cloud; certificate pinning | P0 |
| **NFR-SEC-05** | Network | Each device has its own revocable cryptographic certificate | P0 |
| **NFR-SEC-06** | Update | Digitally signed firmware; verify on-chip signature before applying | P0 |
| **NFR-SEC-07** | Third-party code | Sandbox limits access permissions to sensitive actuator pins | P0 (v1.1) |
| **NFR-SEC-08** | External provider | Audio and text data sent to cloud providers must traverse a TLS 1.3 encrypted channel; system records provider in use in the trace. Selecting a regulatory-compliant provider is user responsibility | P0 |
| **NFR-SEC-09** | Tool caller | MCP defaults to **stdio** (process runner is operator). Network transport in v1.0 (Q-58, TSK-P2-04): **disabled by default**, enabled only with OAuth 2.1 authentication and per-device mTLS (NFR-SEC-04); missing either refuses startup. LLM and MCP clients are **untrusted** callers — `docs/spec/threat_model.md` §2b | P0 |
| **NFR-SEC-10** | Third-party plugin | In-process plugins are operator-trusted code (`threat_model.md` §3): loaded only when explicitly enabled, provenance (package, version, file hash) printed and recorded in trace; no `neuroedge.sdk` API grants hardware handles to bridges or fact sources (FR-EXT-03, Q-67) | P0 |
| **NFR-SEC-11** | Data exfiltration prevention *(Q-72)* | **100%** of dispatches to undeclared destinations are blocked and traced; LLM worker cannot open connections outside declared provider endpoints (FR-EGR-01 → 03). Remaining risk recorded in threat model: compromised worker can still send permitted data to permitted destinations | P0 |
| **NFR-SEC-12** | Chat channels *(Q-72)* | Approvals valid only via fully verified approval records (FR-CH-04); bot token resides only in trusted runtime, never in worker, trace, or Blueprint; threat model has dedicated entry for chat channels, including risk of hijacked chat account (revocation, expiry, ceilings: `TODOS.md` #62) | P0 |
| **NFR-SEC-13** | User LLM keys (BYOK) *(Q-72)* | Keys reside only in LLM worker on home box; never in traces, contracts, Blueprints, chat messages, or NeuroEdge-operated servers; runtime does not retain keys | P0 |
| **NFR-SEC-14** | NeuroEdge Blueprint *(Q-72)* | `install` verifies full package digest before writing anything; package executes no arbitrary code on home box during installation; actuators with `safe_state` other than `off` displayed separately and require local confirmation; "unsigned" evidence prominently displayed everywhere (FR-BP-03 → 06) | P0 |
| **NFR-SEC-15** | Optional relay *(Q-72)* | Relay does not decrypt; compromised relay exposes only metadata, cannot read traces, cannot inject commands; home box-side encrypted backup (FR-EGR-05) | P1 |

### 9.5 Privacy (NFR-PRIV)

| Mã | Yêu cầu | Ưu tiên |
|:---|:---|:---:|
| **NFR-PRIV-01** | Audio stream processed live, **no storage by default** | P0 |
| **NFR-PRIV-02** | Language processing defaults to cloud-first architecture; priority on-device when hardware capability permits. Users select provider and configure corresponding privacy level | P0 |
| **NFR-PRIV-03** | Traces by default store decisions only, no raw data; raw storage must be explicitly enabled | P0 |
| **NFR-PRIV-04** | Anonymization mode at source replaces raw content with hash without breaking replay capability | P0 |
| **NFR-PRIV-05** | Operational data shared to improve detectors only when user **explicitly enables**; disabled by default; destination displayed in approval summary *(Q-72, FR-BP-09)* | P2 |

### 9.6 Observability (NFR-OBS)

| Mã | Yêu cầu | Ưu tiên |
|:---|:---|:---:|
| **NFR-OBS-01** | Each interaction session generates exactly one complete trace file. *24/7 runtime (Q-72, pending RFC):* one session produces a chain of trace segments, each segment replayable (FR-TRC-11) | P0 |
| **NFR-OBS-02** | Traces display System 1 / System 2 ratio, per-turn cost, and complete gate evaluation results | P0 |
| **NFR-OBS-03** | Traces record hop-by-hop latencies sufficient to compare against `budget.p95_latency_ms` budget | P0 |
| **NFR-OBS-04** | Traces on home box *(Q-72)*: retain most recent **30 days**; flush approximately every 10 seconds (configurable) and immediately upon a block verdict or approval; power loss drops at most the tail of normal events. 30-day trace size of the aquarium scenario measured on G1 then recorded on this line (FR-TRC-12) | P0 |

### 9.7 Compatibility and Open Standards (NFR-COMP)

| Mã | Yêu cầu | Ưu tiên |
|:---|:---|:---:|
| **NFR-COMP-01** | Core released under PolyForm Noncommercial 1.0.0; schemas, specifications, and compliance test suite under Apache-2.0 (Q-45, `LICENSING.md`) | P0 |
| **NFR-COMP-02** | No core safety feature locked behind paid accounts | P0 |
| **NFR-COMP-03** | All cloud services accessed via pluggable backend interfaces | P0 |
| **NFR-COMP-04** | Gate and trace schemas are open standards, governed under public RFC process | P0 |
| **NFR-COMP-05** | Minimum supported Python version: **Python 3.11+** (leverages built-in `tomllib`, `asyncio.TaskGroup`, and bytecode speed optimizations) | P0 |
| **NFR-COMP-06** | Supported operating systems for `linux` environment: Debian/Ubuntu on ARM64 and x86-64 | P0 |

### 9.8 Cost and Annoyance (NFR-COST) *(Q-72)*

| Mã | Chỉ tiêu | Ngưỡng cam kết | Điều kiện đo | Ưu tiên |
|:---|:---|:---|:---|:---:|
| **NFR-COST-01** | Operator agent LLM cost | Aquarium scenario **30 days simulated < $2 USD**; single-period cost never exceeds `llm_budget` by more than the running turn's cost upon reaching ceiling | Fast-forwarded G1, Blueprint default provider and model, unit price recorded alongside results | P0 |
| **NFR-COST-02** | Message budget | Non-urgent messages per day do not exceed budget declared in contract; urgent messages not batched or delayed due to budget | 30-day scenario on G1, count messages by category | P0 |

---

## 10. Data Interface Specifications

Four format files constitute the entire **existing** data surface of the product; Q-72 adds planned formats in §10.1a. Detailed field specifications are located in Appendices A, B, C of the source document; this section specifies **mandatory constraints** on implementation.

### 10.1 Four Format Files

| Tệp | Định dạng | Vai trò | Đặc tả chi tiết |
|:---|:---|:---|:---|
| `board.toml` | TOML | Board declaring provided capabilities | §4.2, Appendix A |
| `agent.toml` | TOML | Agent declaring required capabilities, gates, and supported environments | §4.3 |
| `<gate>@<version>.yaml` | YAML | Condition permitting a physical action | §4.5, Appendix B |
| `<session>.json` | JSON | Trace event sequence of an interaction session | §3.7, Appendix C |

### 10.1a Planned Formats of Q-72

No code yet, no schema yet. Every line touching `schemas/` or canonical traces **requires an RFC** (`CONTRIBUTING.md` §3); file names are planned, decided in RFCs.

| Định dạng | Vai trò | Yêu cầu | Trạng thái |
|:---|:---|:---|:---|
| Mission contract (`mission.v1`) | Allowed/prohibited terms, frequency, time windows, obligations, data egress, failure behavior, expiration, `llm_budget`, message budget, confirmation parameters | FR-MSN-01 → 14 | Planned, RFC required |
| NeuroEdge Blueprint manifest (`blueprint.v1`) | Kit, BOM, firmware, template contract, gates, detectors, evidence, license, full-package digest; relationship with `manifest.v1` (FR-REG-02) decided in RFC | FR-BP-01 → 08 | Planned, RFC required |
| Detector definitions | Thresholds, trend slopes, sensor stalls, oscillations — declared in mission contract or Blueprint | FR-AGT-04 | Planned, belongs to `mission.v1` RFC |
| Data egress declaration | Destinations (LLM, chat, relay, webhook) and data types permitted to be sent to each destination | FR-MSN-06, FR-EGR | Planned, RFC required |
| Approval records | Request `{id, nonce, expiry, change_digest, summary ≤ 5 lines}` and reply; event in `trace.v1` | FR-CH-04, FR-TRC-13 | Planned, RFC required (`chat:<id>` source) |
| Trace segment | Initial state of segment and previous segment digest, extending `trace.v1` | FR-TRC-11 | Planned, RFC required (`trace.v1`) |
| `safe_state` in `board.v1` | `safe_state` for all actuators, mandatory hardware interlock when other than `off` | FR-ACE-03 | Planned, conditional safety RFC required; address `TODOS.md` #58 first |

### 10.2 Mandatory Constraints on Implementation

| Mã | Ràng buộc | Lý do |
|:---|:---|:---|
| **DATA-01** | Pins and sensors identified by logical names in both `board.toml` and `agent.toml` | Preserves the environment equivalence principle |
| **DATA-02** | Capability reconciliation executed at build time; outcome is block or allow, no soft warning state | Configuration errors must not leak into the field |
| **DATA-03** | Gates are files independent of source code, with own SemVer versioning | Shareable, auditable, and commercializable |
| **DATA-04** | Gate `evaluate` block maps one-to-one to the three primitives of `SystemOne` | Switching model providers does not require rewriting gates |
| **DATA-05** | Traces are the single source of truth for both field diagnostics and CI testing | Field and CI share a common language |
| **DATA-06** | Golden References are a subset of traces, stripping timestamps and raw content | Resilient to model changes, prompt changes, and environment changes |

### 10.3 Version Compatibility Matrix

| Thành phần | Quy tắc phiên bản | Thay đổi phá vỡ tương thích |
|:---|:---|:---|
| Trace schema | URL `/v1`, `/v2` | Increment major version; adding optional fields does not increment |
| Gate schema | `neuroedge.gate/v1` | Increment major version |
| Specific gate file | SemVer | Any change in `allow_when` |
| Tool call schema (`schemas/tool-call.v1.json`: envelope, tool descriptor) | URL `/v1`, `/v2` | Renaming, removing, or tightening a field; adding optional fields or widening `enum` does not increment (RFC-0015) |
| Tool result schema (`schemas/tool-result.v1.json`) | URL `/v1`, `/v2` | Same as above; `reason` is an open string and result object is open, so adding `Reason` or optional fields does not increment; adding `status` or `on_block` increments (RFC-0015) |
| Error schema (`schemas/error.v1.json`) | URL `/v1`, `/v2` | Same as above (RFC-0015) |
| Error code catalog (`schemas/error-codes.v1.json`) | URL `/v1`, `/v2` | Changing meaning, class name, removing or reusing a code; adding codes, `fields`, or `aliases` does not increment (RFC-0015 §3d) |
| Board schema (`schemas/board.v1.json`, key `schema = "neuroedge.board/v1"` at root of `boards/*.toml`) | `neuroedge.board/v1` | Increment major version; missing key ⇒ `v1`; parser rejects versions it cannot read (NE3001) prior to validation (RFC-0015 §3c) |
| Planned schemas of Q-72 (`mission.v1`, `blueprint.v1`, egress declaration, approval records) | URL `/v1`, `/v2` like all schemas | Rules decided in RFC for each schema |
| `neuroedge` package | SemVer | Changes to public API surface ([`docs/spec/python_api.md`](../docs/spec/python_api.md)) or CLI |

---

## 11. Release Acceptance Criteria

Each milestone is published only upon meeting **all** corresponding criteria. Partial achievement or averaging is not accepted.
Internal increments prior to public release (I1–I5) may not be claimed as meeting any criteria in this section (Q-39).

### 11.1 Acceptance v1.0 — Core

| # | Tiêu chí | Ngưỡng | Phương pháp kiểm chứng |
|:---:|:---|:---|:---|
| **A1** | Time-to-first-value | Median **< 10 minutes** across 10 independent developers | Measurement log with per-step timestamps |
| **A2** | Environment equivalence | `neuroedge verify` achieves **100%** across Tier 1 targets: `sim`, `linux`, `esp32s3` | Run in CI, retain logs |
| **A3** | No shortcuts to actuators | **0** paths activating GPIO bypassing gates | Code audit and penetration testing |
| **A4** | Fail-closed | **100%** of degraded scenarios block action — loss of network specifically: evaluate via local command fallback, block when fallback fails to run *(Q-14)* | Scenario suite: loss of network (with and without fallback), timeout, invalid model data |
| **A5** | Safe gate inheritance | Child gate relaxing parent gate — `allow_when`, `budget`, `on_block` (Q-18) or `arguments` (Q-25) — rejected in **100%** of cases | Inheritance resolution test suite · `fixtures/gates/invalid/` corpus via `neuroedge gate lint` |
| **A6** | Stability on microcontroller *(no voice — Q-77)* | **24 hours** continuous operation without memory exhaustion, with gate evaluation, four extended primitive packages, and host link | Load testing on reference board |
| **A7** | Valid traces | **100%** of sessions generate files passing `neuroedge trace validate` | Automated execution in CI |
| **A8** | Documentation | 3 runnable sample applications + 1 visual asset in README | Verification on a clean machine |
| **A9** | Public schemas | JSON Schemas accessible at published URLs, accompanied by compliance test suite | Third party runs test suite successfully |
| **A10** | Full primitives on three targets | Each extended primitive of FR-HAL-08 has a sample agent achieving **100%** `verify` on `sim`, `linux`, `esp32s3` *(Q-53)* | Run in CI and nightly on real hardware, retain logs |
| **A11** | ~~Conversational contract authoring~~ | Dropped alongside NeuroEdge Lab (Q-77); authoring via standard MCP toolset measured in A15, A17 | — |
| **A12** | Buildable sample kit | Median **≤ 1 day** from unboxing to real device running gated agent, across 5 external testers, each with one kit *(Q-52)* | Measurement log with per-step timestamps |
| **A13** | Open platform | A third party connects NeuroEdge to a previously unsupported ecosystem, in an external repository, solely from public documentation, passing compliance test suite in **≤ 1 day**, with zero lines changed in core; wraps an existing MCP server in **≤ 3 commands** *(Q-67)* | Measurement log of `neuroedge-muse` test (roadmap TSK-I2c-17); CI test installing plugin from external repository |

**Acceptance for first NeuroEdge Blueprint — aquarium (Q-72).** A14 → A22 measurable as soon as I2d, I2e are complete, on simulation, prior to the 8-week gate; they remain v1.0 criteria. Conditional safety RFC written **from these exact cases**, not in advance.

| # | Tiêu chí | Ngưỡng | Phương pháp kiểm chứng |
|:---:|:---|:---|:---|
| **A14** | Blueprint installation | External user installs aquarium Blueprint and runs on `sim` from a clean machine in **< 10 minutes**, no account | Measurement log with per-step timestamps |
| **A15** | Contradictory contracts | **100%** of contradictory contracts in corpus rejected **prior to approval**, pinpointing conflicting clause pairs | Two-way closed corpus executed in CI |
| **A16** | Loss of network, loss of LLM | Network loss: aeration keeps running; heater follows local reflex rules; worker crash or budget exhausted: reflexes and hard-coded emergency alerts continue running | G1 scenario; firmware reflex tier on G3 |
| **A17** | Contract-violating commands | **100%** of contract-violating commands blocked across scenario suite, including commands proposed by LLM ("turn off aeration for quiet") | G1 scenario suite, assert on gate verdicts and pin states (FR-CI-L3) |
| **A18** | Data egress | No photos leave local network when contract prohibits; **100%** of dispatches to undeclared destinations blocked and traced | G1 scenario with mock destinations; count egress events in trace |
| **A19** | Capped proactive alerting | Agent sends **≥ 1** correct trend detection; LLM cost of 30-day simulated scenario **< $2 USD** | 30-day scenario on G1 (NFR-COST-01) |
| **A20** | Approval via chat | Approvals from unpaired accounts, from groups, stale approvals (reused nonce), expired, mismatched digest, or sent by LLM worker rejected in **100%** of cases | Scenario suite for FR-CH-04, FR-CH-05 |
| **A21** | `safe_state: on` does not become a shortcut | `board.v1` declaring `safe_state: on` without hardware interlocks rejected upon loading in **100%** of cases; `safe_state` declared outside `board.v1` rejected | `fixtures/boards/` corpus (when RFC lands) |
| **A22** | Replay | `replay` reproduces **100%** of verdicts from traces, including each segment of 30-day trace sequence | Executed in CI against Blueprint evidence traces |

### 11.2 Developer Beta Acceptance

| # | Tiêu chí | Ngưỡng |
|:---:|:---|:---|
| **B1** | External developers successfully running agent on `sim` | ≥ 50 developers |
| **B2** | External developers successfully flashing and controlling real hardware | ≥ 10 developers |
| **B3** | Safety gates authored and contributed by external community | ≥ 3 gates *(measured and reported, not an unlock condition for v1.1 — Q-41)* |
| **B4** | Action CI adoption rate | ≥ 50% of scaffolded projects retain and expand gate test suites |
| **B5** | Conversion rate to real hardware | ≥ 15% of `sim` runners flash to board within 30 days |
| **B6** | 8-week gate — external users installing on their own *(Q-72)* | ≥ 3 external users independently install and run a NeuroEdge Blueprint |
| **B7** | 8-week gate — continuous operation *(Q-72)* | ≥ 1 person running continuously for 2 weeks on simulation G2 or G3 |
| **B8** | 8-week gate — someone wanting to sell *(Q-72)* | ≥ 1 maker wanting to package and sell their Blueprint |

**(Home) box + NeuroClaw (Q-81).** B6 and B7 also count a NeuroEdge box connected to a NeuroClaw brain, controlling at least one device via chat, as an exemplar Blueprint *in-home chat assistant*; thresholds remain unchanged. Counting methodology: `docs/business/cong-nhu-cau-2026-10-25/cham-diem.md` §4.0.

**8-week demand gate (Q-72, reversing Q-56).** B6 → B8 measured **8 weeks after deciding Q-72**, prior to Developer Beta; they are **decision gates**, not Beta announcement prerequisites. Outcomes: achieving all three ⇒ invest in Hub, kit catalog, second Blueprint, and revisit v1.0 scope; achieving B6 and B7 but missing B8 ⇒ NeuroEdge serves as a personal tool, keep loops ① and ②, seek alternative revenue streams; missing B6 or B7 ⇒ pivot target segment or messaging before implementing further features. In parallel: score the three completed interviews and interview 10 additional people, including at least 5 makers, regarding selling hardware devices — responsibility of the team lead, not delegated to AI agents.

**Beta phase operating principles:** feature freeze on new capabilities across the `1.0.x` line (Q-39). All resources dedicated to direct technical support, documentation refinement, and polishing user experience.

### 11.3 Acceptance v1.1 — Commercial Service Layer

> **No increment currently uses the C set (Q-77):** I9 and I10 have been removed from the roadmap (§6 of roadmap). Table retained for reference when a new `Q-N` re-opens the service layer.

| # | Tiêu chí | Ngưỡng |
|:---:|:---|:---|
| **C1** | OTA reliability | Meets NFR-REL-01 |
| **C2** | Voice latency *(measured full round-trip via cloud provider)* | Meets NFR-PERF-01 and NFR-PERF-07 |
| **C3** | Gate evaluation latency | Meets NFR-PERF-02 and NFR-PERF-03 |
| **C4** | Routing efficiency | Meets NFR-PERF-05 |
| **C5** | Community gate sharing | ≥ 20 gates achieving ≥ 5 installations by independent users |
| **C6** | Revenue composition | **Tracking metric, not a release prerequisite (Q-42):** revenue across each stream in §8.4 — kit commissions, Blueprint revenue share, per-device commercial licenses and core license (Q-45), relay, Fleet OS — relative to break-even path, reported monthly *(NeuroEdge generates no inference revenue — N4; revenue streams per Q-72)* |
| **C7** | Trace format consistency | Traces from provider abstraction layer replayable on personal machines without conversion |
| **C8** | Structured `SystemOne` decision latency | Meets NFR-PERF-04, measured on real traffic via FR-TEL-06 |

---

## 12. Metrics and Measurement Requirements

Principle: **every metric in this section must have a corresponding measurement requirement.** A metric that cannot be measured is not a metric.

### 12.1 Mandatory Measurement Requirements (FR-TEL)

| Mã | Yêu cầu | Phục vụ chỉ số | Ưu tiên |
|:---|:---|:---|:---:|
| **FR-TEL-01** | CLI collects **anonymous, opt-out** telemetry regarding milestones: installation, project initialization, first `sim` run, first hardware build | TTFV, conversion rate sim → hardware | P0 |
| **FR-TEL-02** | Telemetry policy publicly stated; opt-out command displayed on first run | Community trust | P0 |
| **FR-TEL-03** | Traces record System 1 / System 2 ratio and per-turn cost | Routing efficiency | P0 |
| **FR-TEL-04** | Registry records downloads and inheritance counts per gate, distinguishing authors from other users | Community gate sharing, milestone G2/G3 (§11.2) | P0 (v1.1) |
| **FR-TEL-05** | Fleet OS records outcome of each OTA campaign: device count, failure rate, rollback count | OTA reliability | P0 (v1.1) |
| **FR-TEL-06** | Provider abstraction layer records hop-by-hop latency sufficient to compute P95 across task categories | Latency SLA | P0 |
| **FR-TEL-07** | *(Q-72)* CLI and runtime additionally collect, under same anonymous and opt-out policy as FR-TEL-01, milestones: installing a Blueprint, connecting a chat channel, first mission contract approved, runtime operating continuously every 7 days. Static index does not count installs, so B6 → B8 are also measured via direct contact with testers | 8-week demand gate (B6, B7), M9 | P0 |
| **FR-TEL-08** | *(Q-72)* Clicks and orders via kit affiliate links obtained from seller affiliate reports, not from user devices | Initial revenue exploration, C6 | P1 |

### 12.2 Metrics Table by Milestone

Thresholds are located in §11 and §9; this table links each metric to criteria and data sources.

| Chỉ số | Mốc | Tiêu chí | Nguồn dữ liệu |
|:---|:---:|:---|:---|
| Time-to-first-value | v1.0 | A1 | Direct measurement logs of 10 users |
| Environment equivalence | v1.0 | A2 | CI logs |
| Action CI adoption rate | Beta | B4 | FR-TEL-01 |
| Conversion rate to hardware | Beta | B5 | FR-TEL-01 |
| OTA reliability | v1.1 | C1 (NFR-REL-01) | FR-TEL-05 |
| Voice latency P95 | v1.1 | C2 (NFR-PERF-01, 07) | FR-TEL-06 |
| Gate latency P95 | v1.1 | C3 (NFR-PERF-02, 03) | FR-TEL-06 |
| `SystemOne` decision latency | v1.1 | C8 (NFR-PERF-04) | FR-TEL-06 |
| Token cost savings | v1.1 | C4 (NFR-PERF-05) | FR-TEL-03 |
| Community gate sharing | v1.1 | C5 | FR-TEL-04 |
| Revenue composition | v1.1 | C6 | Invoicing system; kit affiliate reports (FR-TEL-08) |
| Blueprint install on clean machine | I2e | A14 | Direct measurement logs |
| LLM cost for 30-day simulated scenario | I2d | A19 (NFR-COST-01) | G1 scenario traces |
| External users independently installing Blueprint | 8-week demand gate | B6 | FR-TEL-07, direct contact |
| Continuous operation for 2 weeks | 8-week demand gate | B7 | FR-TEL-07 |
| Maker wanting to sell Blueprint | 8-week demand gate | B8 | Team lead interviews |

**Metrics deliberately excluded:** GitHub stars, page views, documentation views. These metrics measure attention, not utility value.

---

## 13. Dependencies, Risks, and Assumptions

### 13.1 External Technical Dependencies

| Thành phần | Vai trò | Rủi ro phụ thuộc | Phương án giảm thiểu |
|:---|:---|:---|:---|
| ESP-IDF | Toolchain for `esp32s3` | API changes between major releases | Pin versions; nightly testing detects regressions early |
| libfvad, Silero VAD, WebRTC AEC, Opus | Signal processing pipeline | Upstream maintenance cessation | Wrap behind internal interfaces, each component replaceable |
| ESP-SR MultiNet or TFLite Micro / ESP-NN | Local fixed command recognizer on `esp32s3` *(Q-14, replacing Sherpa-ONNX)* | ESP-SR license (to current understanding: restricted to Espressif SoCs); memory consumption | Verify license prior to I5; spike TSK-S1-10 additionally benchmarks MultiNet; common command grammar for all backends |
| `gpiod` | Linux GPIO access | Divergence across distributions | Restrict support to Debian/Ubuntu (NFR-COMP-06) |
| `SystemOne` provider | Structured decisions | Price changes, tightened access, vendor shipping competing framework | Interface from day one (FR-MDL-01); local fixed command fallback is P0 *(Q-14)* |
| `SystemTwo` provider | Open-ended reasoning | Same as above | Multi-provider routing (FR-GW-03) |
| SchemaStore | Schema recognition in IDEs | Slow review process | Non-blocking for release; P1 requirement |
| Telegram Bot API *(Q-72)* | First chat channel: reporting, commands, approvals (FR-CH) | API changes, rate limiting, bot bans; compromised user account | Adapter behind runtime channel interface; bounded queue + on-device alerts when channel fails (FR-AGT-07); approvals only via approval records (FR-CH-04) |
| Slack, Zalo API *(Q-72)* | Chat channels following Telegram | Bot terms of service, enterprise verification (Zalo) | P1; shared channel interface, approval rules unchanged |
| ESPHome (host platform, external component) *(Q-72)* | Simulation tier G4 and plug point into Home Assistant community devices | Config or API changes between releases | Pin version in Blueprint; G4 is only one simulation tier, does not replace G1–G3 |
| Ollama and local models *(Q-72)* | User's LLM running on home box via LiteLLM | Quality and resource limits on Pi; API changes | Abstracted behind LiteLLM (Q-10); deterministic detectors independent of LLM (FR-AGT-04) |
| Wokwi, Velxio *(Q-72)* | Options for simulation tier G3 (on-host ESP32 firmware) | Wokwi closed source, requires token, lacks I2S — excluded from standard CI per Q-21 and Q-69; Velxio unverified | Espressif QEMU remains primary path for G3; Wokwi or Velxio used only after re-evaluation against Q-21, Q-69 |
| Component retailers (affiliate) *(Q-72)* | Kit BOM and purchase links (FR-BP-07) | Out-of-stock, changed part numbers, modified affiliate programs | Each component has alternative purchase sources; NeuroEdge holds no inventory |

### 13.2 Product Risks

This section records **product and execution** risks. **Strategic** risks (competition, business model, scope fragmentation) reside in §13 with numbering `#1–#6`. Three pairs cross between the two registers: **R-4 ↔ §11 #1** (model vendor dependence) · **R-6 ↔ §11 #5** (cloud outage) · **R-7 ↔ §11 #6** (hardware breadth). Remaining risks belong strictly to one register. R-8 → R-20 are drawn from the risk table of the Blueprint proposal (`docs/business/proposal-blueprint-2026-10-11.md`, Q-72); going forward, this table tracks them.

| # | Rủi ro | Mức độ | Dấu hiệu cảnh báo sớm | Phương án ứng phó |
|:---:|:---|:---:|:---|:---|
| **R-1** | Block 1b scope exceeds schedule due to microcontroller memory optimization | Medium *(downgraded from High per CR-1.0)* | Spike TSK-S1-10 misses a Q-3 threshold, or 3 weeks post-I3 audio capture/playback loop still missing on board | Cloud-first architecture moved STT/TTS off microcontroller, significantly easing memory pressure (P-4, FR-PER-07). If still missing: **do not cut voice** (Q-44) — immediately open a `Q-N` re-planning I5 (TSK-S5-05, TSK-S5-07) and adjust v1.0 forecast |
| **R-2** | `sim` environment drifts from real hardware over time | High | `neuroedge verify` begins showing isolated divergences | Nightly testing on real hardware (NFR-REL-03); treat any divergence as release-blocking defect |
| **R-3** | Developers bypass Action CI, using framework solely as a voice library | Medium | Action CI adoption rate below 50% in Beta | Embed gate tests into default scaffolds; center documentation on Action CI |
| **R-4** | Model vendors modify access terms | Medium | API terms changes, vendor announces device SDK | Expand local fallback beyond fixed command grammar of Q-14 |
| **R-5** | Sharing network effects — gates and NeuroEdge Blueprints — fail to form *(rewritten per Q-72)* | High | 8-week gate misses B6 or B8; fewer than 3 community gates at Beta close | Follow branches of 8-week demand gate (§11.2): missing B8 ⇒ retain loops ① ② as personal tools, forego monetized Hub, explore alternative revenue; missing B6 ⇒ pivot target segment or messaging before implementing new features. Monetized Hub opens only when gate is met (FR-BP-10) |
| **R-6** | Cloud provider dependence during connection loss | Medium | Abnormally high percentage of sessions terminating with `gate_unreachable` · Cumulative provider downtime exceeds commitments | Fail-closed blocks all physical action when gate cannot be evaluated (NFR-RES-04, A4); gates and state machine run entirely on-device. **Local fallback is P0** (Q-14, FR-ACE-03): gate remains evaluatable during network outages |
| **R-7** | Broad Phase 2 hardware coverage dilutes Tier 1 quality | Medium | Bug fix times on Tier 1 boards lengthen · Nightly test failures increase in frequency · Tier 3 support exceeds 10% of core team bandwidth | Tiered strategy FR-TGT-08: core team commits only to Tier 1 and Tier 2; Tier 3 community-ported and self-certified. All thresholds in §9 and §11 remain anchored to Tier 1. Each Phase 2 block adds at most one reference board |
| **R-8** | Spreading thin: three loops becoming three separate products *(Q-72)* | High | I2d or I2e extends beyond ~6 weeks; implementing features outside aquarium Blueprint | Single Blueprint traverses all three loops end-to-end; six verbs exist only within Blueprint format, not built simultaneously; voice, Studio, `jetson` paused |
| **R-9** | Two-sided marketplace cold-start *(Q-72)* | High | Index contains fewer than 3 Blueprints at 8-week gate | NeuroEdge team authors first 5–10 Blueprints in-house, analogous to Shopify building initial themes |
| **R-10** | No makers want to sell Blueprints *(Q-72)* | High | No maker in interviews has sold a device or wants to sell (B8) | Ask makers "have you built devices for others, did anyone pay?" **before** building monetized Hub; "misses ③" branch of 8-week gate |
| **R-11** | Proactive messages cause annoyance, users mute notifications *(Q-72)* | Medium | Testers mute notifications or leave chat channels within first two weeks | Message budgets, summary digests, hard-coded emergency alerts (FR-AGT-06, NFR-COST-02) |
| **R-12** | Unpredictable LLM invoices *(Q-72)* | Medium | 30-day scenario cost exceeds $2 USD; testers complain about bills | Deterministic detectors first, LLM second; cost ceilings in contract (FR-AGT-04, FR-AGT-05, NFR-COST-01) |
| **R-13** | Home box retains LLM keys and controls physical devices *(Q-72)* | Medium | Prompt injection via chat messages reaches HAL or keys | Two processes: untrusted worker holds keys, runtime holds HAL (FR-AGT-01, 02); worker network restricted to declared destinations (FR-EGR-03); contract locked only by humans (Q-71) |
| **R-14** | Malicious Blueprint on Hub *(Q-72)* | Medium | Package requests broad permissions, strange data destinations, or `safe_state` other than `off` | Blueprints purely declarative; full-package digest; `safe_state` other than `off` allowed only in `board.v1` with hardware interlock, displayed separately on install; installer runs `replay`; permissions shown in approval summary (FR-BP-01 → 06) |
| **R-15** | Users approve without reading *(Q-72)* | Medium | Approvals arrive within seconds of request, consistently | Approval summary ≤ 5 lines, highlights only clauses diverging from defaults; data permission expansion approved locally only (FR-MSN-12, FR-MSN-14) |
| **R-16** | Simulation diverges from real hardware *(Q-72)* | Medium | Real-board testers encounter bugs unreproducible on G1–G4 | Four simulation tiers; purchase hardware before selling first Blueprint; simulation limits explicitly documented (§4.2) |
| **R-17** | Unsigned evidence, sellers modifying traces *(Q-72)* | Medium | Blueprint evidence does not match behavior when installer runs `replay` | Accepted in MVP; marked "unsigned" everywhere; installer runs `replay` locally; sign traces before Hub collects money for sellers (`TODOS.md` #1, FR-BP-04) |
| **R-18** | Compromised chat account allows unauthorized approvals *(Q-72)* | Medium | Approvals originate from unfamiliar locations or devices; surge of approvals in short window | Local pairing, one-time bounded approval records with digest (FR-CH-03, 04); data permission expansion approved locally only; revocation, pairing expiry, approval ceilings: `TODOS.md` #62. Accepted consequence of deciding Q-72 |
| **R-19** | Misinterpreted as a certified safety function *(Q-72)* | High (legal) | Users or Blueprints advertise device as "safe" for medical or eldercare use cases | Q-38 in README, approval summary, and Blueprint; hazard protection always belongs to hardware (N5); medical and eldercare deferred (§14) |
| **R-20** | Hardware fulfillment friction: shipping, returns, quality *(Q-72)* | High | Component complaints directed to NeuroEdge | Affiliate links only, no inventory held (FR-BP-07) |

### 13.3 Hypotheses to Validate

**Single source of truth** for the assumptions catalog; §13 refers back here. Each hypothesis includes its rationale, measurement method, and evaluation milestone.

| # | Giả định | Vì sao quan trọng | Phương pháp kiểm chứng | Mốc |
|:---:|:---|:---|:---|:---:|
| **G-a** | Fleet management pricing of $1/device/month is market-acceptable | Determines fleet size required to reach break-even (`docs/architecture/vi/16-ecosystem-landscape.md` §7) | Trial enterprise tier (SLA commitment, trace audit) with first 5 enterprise customers; measure willingness to pay more | 90 days post-I9 release (Q-43) |
| **G-b** | Conversion rate `sim` → hardware ≥ 15% | Confirms `sim` serves as a true funnel leading to hardware (`docs/architecture/vi/16-ecosystem-landscape.md` §5) | Anonymous telemetry from CLI (FR-TEL-01); review at 100-developer milestone | When I8 (Beta) closes — same metric as B5 (Q-43) |
| **G-c** | Dual-model routing saves ≥ 60% token costs | Quantitative validation for System 1 / System 2 architecture | Measured on real traffic via provider abstraction layer, broken down by task category | 90 days post-I9 release (Q-43) |
| **G-d** | Community genuinely wants to share and reuse gates | Foundation of network effects prior to Marketplace launch | Download and inheritance frequency on free Registry over 12 months | 12 months post-I10 release; early signal: B3 (Q-43) |
| **G-e** | Trace reproduction eliminates 70% of field trips | Core underpinning of TCO model (Q-72) | Actual warranty data from first 3 AURA customers, categorizing incident root causes (software/configuration vs physical failure) | 6 months post-first three AURA sites (Q-43) |
| **G-f** | Makers want to sell devices they build, via NeuroEdge Blueprints *(Q-72)* | Acid test of entire Q-72 model; if invalidated, NeuroEdge is a personal tool | Interview at least 5 makers regarding selling; B8 | 8-week gate following Q-72 decision |
| **G-g** | Users accept paying for LLMs with their own keys (BYOK) *(Q-72)* | NeuroEdge generates no revenue from tokens and retains no keys; if invalidated, alternative LLM path needed | Percentage of testers entering keys or using local models when reaching proactive alert step (FR-TEL-07) | 8-week gate following Q-72 decision |
| **G-h** | Proactive alerts deliver value, users do not disable *(Q-72)* | Loop ② is the core reason for daily usage | Percentage of testers still receiving messages after 2 weeks; feedback on trend detections | When first tester achieves B7 |
| **G-i** | Kit affiliate links convert to orders *(Q-72)* | Initial revenue exploration source | Seller affiliate reports (FR-TEL-08) | 90 days post-I2e release |

---

## 14. Out of Scope

Explicit exclusion catalog — **single source of truth** for status and revisit conditions. All proposals falling into this catalog are rejected unless formal scope change decision is made.

**Priority filters PF-1 → PF-4** ("Criteria" column below):

| # | Bộ lọc | Câu hỏi |
|:---:|:---|:---|
| **PF-1** | Time to first value | Does it shorten the time from `pip install` to first successful run? |
| **PF-2** | Foundations that cannot be added late | If not done now, will it require an architectural rewrite later? |
| **PF-3** | Validated demand | Has an actual user requested this, or is it merely conjecture? |
| **PF-4** | Legal safety | Does it entail holding funds in escrow, KYC, financial licensing, or legal liabilities exceeding team capabilities? |

Violating PF-4 → **blocked**, revisited only with dedicated legal review. Satisfying PF-1 or PF-2 → prioritized. Unclear PF-3 → deferred for validation. Payouts to Blueprint sellers touch PF-4 (holding funds or serving as merchant of record): evaluated after 8-week gate, prior to Hub monetizing (Q-72).

| Hạng mục | Trạng thái | Tiêu chí | Điều kiện xem xét lại |
|:---|:---|:---:|:---|
| Commercial monetized marketplace | **Minimal Hub in scope** (Q-72): static index of NeuroEdge Blueprints, serverless, unmonetized (FR-BP-05, I2e). **Monetization: deferred until after 8-week gate** | PF-3 | 8-week gate met (B6–B8), signed traces (`TODOS.md` #1), OCI Registry and FR-REG rails (FR-BP-10) — replacing milestone G1–G4 conditions of §11.2 specifically for Blueprints. Community plugin index (FR-EXT-08) is never monetized, no paid ranking |
| Automated agent-to-agent payments | Blocked | PF-4 | Milestone reached and dedicated legal review completed |
| Paid hardware certification program | Blocked | PF-3 | Milestone reached and independent benchmarking process established |
| Computer vision (camera, NPU) | **Moved to Phase 2**, split into two steps | PF-1, PF-3 | **2a open target list:** RFC-0002 approved · **2b implementation** (including primitive RFC `vision.in`): measurable camera demand from real customers, voice TTFV remains < 10 minutes |
| Jetson | **Moved to Phase 2** at Tier 2 (FR-TGT-08) — **paused** (Q-72) | PF-3 | RFC-0002 approved and measurable demand from real customers; post-8-week gate |
| In-house SLAM, obstacle avoidance, autonomous navigation, drones | Blocked — **exception Q-34:** native ROS 2/Nav2 integration, gate evaluates all velocity commands (roadmap I14) | PF-1, PF-3 | None — navigation belongs to ROS 2/Nav2 |
| Matter, HomeKit | Deferred — until trigger condition met | PF-3 | Measurable demand from real customers. Community can implement as remote actuator plugins (FR-EXT-07, Q-67) without core team |
| SSO/SAML, SOC 2 certification | Deferred — until trigger condition met | PF-3 | Specific enterprise contract requirement |
| Functional safety certification (SIL under IEC 61508, PL under ISO 13849, ISO 13482) | Temporarily blocked (Q-38) | PF-3 | Question C6 of interview guide (`docs/business/cong-nhu-cau-2026-10-25/`, now informational input only — Q-56): a segment labeled **R** ≥ 3/5 (`CEO-T2`), or robot buyers responding affirmatively (`TODOS.md` #40) |
| Multi-region, on-premise | Deferred — until trigger condition met | PF-3 | Data sovereignty constraints from real customers |
| Fine-tuned local fallback model | Conditionally deferred | PF-3 | Early warning signals for R-4 or R-6 appear |
| Custom BI dashboards, complex alerting engines | Indefinitely deferred | PF-1, PF-3 | None. **Excludes** operator agent deterministic detectors (thresholds, trends, sensor stalls — FR-AGT-04): they **are in scope** (Q-72), declared in contracts or Blueprints, not a generalized alert engine |
| Voice (FR-PER, NFR-PERF-01, 07, A6), NeuroEdge Studio (Q-51) | **Paused** (Q-72) — remains within v1.0 scope (Q-52), not cut, requirements not deleted | PF-3 | Post-I2d, I2e; v1.0 scope reviewed at 8-week gate |
| Vertical markets: medical, eldercare, domestic help; shrimp ponds and aquaculture | Deferred (Q-72) | PF-3, PF-4 | Post-8-week gate. Medical and eldercare cases require separate legal evaluation due to R-19 (Q-38); shrimp ponds are an interface re-skin of aquarium Blueprint |
| Signing Blueprint evidence traces | Deferred (Q-72) | PF-3 | Prior to Hub collecting money for sellers (`TODOS.md` #1) |
| Kubernetes architecture | Indefinitely deferred | PF-1 | Exceeds 50,000 devices scale |
| In-house model fine-tuning and training | Indefinitely deferred | PF-3 | None |
| Custom wake-word training | Deferred post-v1.0 | PF-1 | After `esp32s3` runtime stabilizes |
| Core team in-house porting of additional board variants outside Tier 1 and Tier 2 | Indefinitely deferred — **except RP2350** as tiered robot node (Q-33) | PF-1 | None — hardware coverage expands via **Tier 3 community ports** (FR-TGT-08), not core team |
| **Free, self-certified** hardware certification program | **Moved to Phase 2** | PF-2, PF-3 | ≥ 3 Tier 3 ports pass Conformance Test Suite *(distinguished from **paid** certification row above, which remains Blocked)* |

---

## 15. Sổ quyết định

Mọi quyết định kỹ thuật, đã chốt hoặc còn mở — xem cột Trạng thái.

**Đây là sổ quyết định duy nhất của dự án.** Mọi quyết định kỹ thuật, kể cả quyết định phát sinh trong lúc thực thi, đều được cấp mã và ghi tại đây. `neuroedge-roadmap.md` §10 không định nghĩa quyết định mới — nó chỉ theo dõi **hạn chốt, người quyết và trạng thái** của cùng bộ mã này.

| # | Hạng mục | Trạng thái | Nội dung đã chốt chính thức |
|:---:|:---|:---:|:---|
| **Q-1** | Phiên bản Python tối thiểu | **ĐÃ CHỐT** | **Python 3.11+** (NFR-COMP-05: tích hợp sẵn `tomllib`, TaskGroup/ExceptionGroup, bytecode nhanh hơn 25%). |
| **Q-2** | Bo mạch tham chiếu chính thức | **ĐÃ CHỐT** | **ESP32-S3-Box-3** (§3.4: tích hợp sẵn LCD ST7789, dual-mic ES7210, loa ES8311, dock GPIO; tránh nhiễu clock I2S do câu dây). |
| **Q-3** | Ngân sách SRAM/PSRAM & firmware | **ĐÃ CHỐT** | **SRAM tự do ≥ 120 KB**, **PSRAM ≥ 2 MB** (ringbuffer + VAD/wake-word), **Firmware ≤ 3,5 MB** (vừa phân vùng kép A/B 16MB Flash). |
| **Q-4** | Nhà cung cấp System 1/2 ở v1.0 | **ĐÃ CHỐT** *(sửa 2026-09-23; 2026-09-26)* | **System 1:** Jev (cloud) + **fallback cục bộ = bộ nhận diện lệnh cố định** (Q-14); **System 2:** **`claude-sonnet-5`** & GPT-4o-mini **qua LiteLLM** (Q-10). Kết nối theo Q-12: System 2 qua chat completions; Jev qua endpoint quyết định System One của OpenRouter (`POST {api_base}/systemone`), bảng `[system_one]` (TSK-I4-02). |
| **Q-5** | Xác thực & chống lạm dụng Registry | Chờ v1.1 | Thiết kế trước khi I10 (Registry) mở, theo chuẩn CNCF ORAS và GitHub token. |
| **Q-6** | Chính sách lưu trữ vết ghi Fleet OS | **ĐÃ CHỐT** *(2026-09-25, CPO)* | **Fleet Standard giữ vết 90 ngày; Fleet Enterprise giữ 3 năm.** Vết lên kho theo FR-FLT-05 và chỉ chứa quyết định, không dữ liệu thô (NFR-PRIV-03). Ràng buộc là dữ liệu cá nhân nên thời hạn là mức trần, không phải mức sàn. Hạn mức theo thiết bị chỉ để chặn lặp vòng khi dựng Khối 2. |
| **Q-7** | Từ khóa kích hoạt mặc định v1.0 | **ĐÃ CHỐT** | *"Hey Neuro"* qua mô hình `microWakeWord` (tối ưu cho Box-3) và `openWakeWord` (Linux/Sim). |
| **Q-8** | Ngôn ngữ lõi firmware | **ĐÃ CHỐT** | **C/C++ trên ESP-IDF** cho `esp32s3`; Python cho `sim` và `linux`. Kéo theo nghĩa vụ đặc tả chuẩn tắc và bộ vector tuân thủ dùng chung cho hai hiện thực. |
| **Q-9** | Lượng giá CEL trên vi điều khiển | **ĐÃ CHỐT** | **`neuroedge build` biên dịch gate thành cây quyết định tất định**; firmware chỉ duyệt cây, không nhúng CEL VM trên thiết bị. Trình biên dịch và duyệt cây là mã NeuroEdge không nhận phụ thuộc. Dạng `allow_when` biên dịch là ánh xạ toán tử; chuỗi CEL hoãn (TSK-S2-06). Định dạng cây trên MCU dùng bố cục nhị phân `NETR` (Q-23). Lý do: bảo đảm tương đương môi trường và nhẹ bộ nhớ. |
| **Q-10** | Mức độ phụ thuộc vào LiteLLM | **ĐÃ CHỐT** *(2026-09-23)* | LiteLLM dùng như **thư viện định tuyến (SDK)** sau giao diện nội bộ `neuroedge.models.providers`, không chạy proxy server. Cài qua **extra `neuroedge[cloud]`** để giữ cài đặt mặc định nhẹ và keyless (FR-DX-02). |
| **Q-11** | Ngoại lệ giấy phép: Hawkbit EPL-2.0, EMQX BSL, LiteLLM | **ĐÃ CHỐT** *(LiteLLM 2026-09-23; Hawkbit/EMQX 2026-09-25)* | **LiteLLM: ĐÃ DUYỆT** (2026-09-23) — `litellm==1.102.0` giấy phép MIT, wheel không chứa thư mục `enterprise/`, 55 phụ thuộc bắc cầu đều MIT/BSD/Apache-2.0/PSF + MPL-2.0 (`certifi`, `tqdm`) + CNRI-Python (`regex`). **Chính sách phụ thuộc bắc cầu:** cho phép MIT, BSD-2/3-Clause, Apache-2.0, ISC, PSF, CNRI-Python, MPL-2.0 (chỉ dùng nguyên bản, không sửa); *CNRI-Python ghi thêm 2026-09-24:* giấy phép lịch sử của Python 1.6, OSI duyệt, không copyleft, chỉ buộc giữ thông báo bản quyền — đến qua `regex` (litellm → tiktoken → regex), pip tự cài, không đóng gói lại nên không phát sinh nghĩa vụ; cấm GPL/LGPL/AGPL, SSPL, BSL, giấy phép thương mại hoặc không xác định; cưỡng chế bằng `scripts/check_licences.py` trong job CI `cloud-extra`. *Zlib và CC0-1.0 ghi thêm 2026-09-26, duyệt 2026-09-27:* numpy 2.5 (dev set của `neuroedge`, và extra `wake`) khai `BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0` — Zlib giữ thông báo bản quyền, CC0-1.0 là hiến tặng phạm vi công cộng, cả hai không copyleft; đến qua pip, không đóng gói lại. **Hawkbit EPL-2.0: ĐÃ DUYỆT** (2026-09-25, CPO) — dùng nguyên bản làm dịch vụ Fleet OS; nếu sửa mã Hawkbit thì công bố phần sửa theo EPL-2.0; mã NeuroEdge chỉ nói chuyện qua API nên không bị ràng buộc. **EMQX BSL: KHÔNG DÙNG** — thay bằng broker MQTT giấy phép trong allowlist (Mosquitto theo EDL-1.0, NanoMQ MIT hoặc VerneMQ Apache-2.0), chọn bằng đo tải khi mở Khối 2. |
| **Q-12** | Chuẩn kết nối nhà cung cấp AI | **ĐÃ CHỐT** *(nới 2026-09-26)* | Chuẩn mặc định là **nền tảng tương thích OpenAI API** (chat completions cho LLM, `audio/transcriptions` và `audio/speech` cho ASR/TTS) và **endpoint quyết định có kiểu** cho System One (`POST /api/v1/systemone`, Q-4). Provider chưa tương thích kết nối qua adapter tự viết (FR-MDL-07→09). |
| **Q-13** | Phân tầng cam kết theo bậc target | **ĐÃ CHỐT** | Ba bậc: **bậc 1** (`sim`, `linux`, `esp32s3`) giữ toàn bộ cam kết; **bậc 2** do đội lõi bảo trì với cam kết hẹp hơn; **bậc 3** do cộng đồng port và tự kiểm chứng (FR-TGT-08). Nguyên tắc P-2 áp dụng ở mọi bậc. |
| **Q-14** | Hành vi khi mất mạng + fallback cục bộ | **ĐÃ CHỐT** *(2026-09-23)* | Mất mạng ⇒ gate **vẫn lượng giá** bằng bộ nhận diện **lệnh cố định** cục bộ (P0, FR-ACE-03, FR-MDL-03, R-6); chỉ BLOCK `gate_unreachable` khi fallback không chạy được. Backend cùng ngữ pháp: `sim` = khớp chữ gõ (A1, TSK-S2-08); `esp32s3` = ESP-SR MultiNet hoặc TFLite Micro / ESP-NN; `linux` = TFLite / KWS tương đương. |
| **Q-15** | Đầu vào mặc định của `sim` | **ĐÃ CHỐT** *(2026-09-23)* | Mặc định **gõ chữ** (CLI/UI) qua bộ khớp ngữ pháp lệnh (Q-14): không mạng, không key, tất định (FR-DX-02). Giọng nói là tuỳ chọn khi có key cloud. |
| **Q-16** | GPIO cho `linux` trong CI | **ĐÃ CHỐT** *(2026-09-23)* | CI dùng **`gpio-sim`** (kernel ≥ 5.19, configfs, job `linux-hal`, TSK-S3-05). HAL `linux` ném lỗi khi thiếu `/dev/gpiochip*`. RPi 5 dùng cho nightly phần cứng. |
| **Q-17** | Hành vi `on_block` ở v1.0 | **ĐÃ CHỐT** *(2026-09-23)* | Mọi `on_block` đều chặn hành động vật lý: `deny` chặn; `escalate`/`ask` chặn, ghi vết và gọi hook; `degrade` chặn hành động gốc và chạy `fallback_action` qua gate riêng. Xác nhận `ask` theo Q-26; người nhận `escalate` theo `TODOS.md` #20. Sửa bởi Q-72: chuyển cảnh báo tới kênh chat. |
| **Q-18** | Kế thừa `budget`/`on_block` | **ĐÃ CHỐT** *(2026-09-23, RFC-0004)* | Ngữ nghĩa kế thừa (RFC-0004, FR-GATE-06/07): (1) `p95_latency_ms` của con ≤ của cha; (2) chuỗi đã `closed` thì con cấm khai `fail: open`; (3) con không được thêm `fallback_action` mới, chỉ được đổi sang `deny`/`escalate`/`ask`. Vi phạm ném `GateInheritanceError` (TSK-S2-13). |
| **Q-19** | Lịch Sprint 2–3 | **ĐÃ CHỐT** *(2026-09-23)* | Đã bị thay bởi Q-39: roadmap chuyển sang đo bằng increment, mốc M1 neo theo ngày của I1. |
| **Q-20** | Cổng nhu cầu mềm | **ĐÃ CHỐT** *(2026-09-23)* | Đã bị thay bởi Q-56 và Q-72: cổng nhu cầu mềm 2026-10-25 được thay bằng cổng nhu cầu 8 tuần của Q-72. |
| **Q-21** | Mô phỏng theo tầng bằng OSS đã kiểm chứng | **ĐÃ CHỐT** *(2026-09-23, cùng kế hoạch lấp khoảng trống kỹ thuật)* | Không tự viết emulator, mỗi tầng dùng công cụ mở: `SimHAL` (logic), `gpio-sim` (GPIO `linux`), `sounddevice` (âm thanh CI), `i2c-stub` + `lm75`, LVGL host (`display`), mã C firmware biên dịch trên host (TSK-S4-07), Espressif QEMU cho boot `esp32s3` (TSK-S4-08); bo thật đo âm học và bộ nhớ. Không dùng Renode, Wokwi, `iio_simple_dummy`. Bổ sung bởi Q-69 và Q-72. |
| **Q-22** | AEC phần mềm trên `linux` | **ĐÃ CHỐT** *(2026-09-23, phương án A)* | `LinuxHAL` lấy `audio.in` đã khử vang qua PipeWire `libpipewire-module-echo-cancel` (`aec/libspa-aec-webrtc`). Module tạo 4 nút: `capture` → `source` (`audio.in`), `sink` (`audio.out`) → `playback`. `boards/linux-rpi5.toml` chỉ khai `aec = true` khi nightly trên Pi đạt tiêu chí (`docs/spec/simulation_coverage.md` §6). |
| **Q-23** | Định dạng cây quyết định trên MCU | **ĐÃ CHỐT** *(2026-09-23)* | **`neuroedge build` sinh cây thành bố cục nhị phân `NETR`** (RFC-0003); firmware duyệt trực tiếp, không nhúng parser JSON trên MCU. Bản v1.0 link dạng mảng `const` trong flash; cập nhật qua phân vùng flash riêng bằng `esp_partition_mmap`. Walker C99 tại `targets/esp32s3/components/ne_gate/`. |
| **Q-24** | Hành động là tool call · MCP | **ĐÃ CHỐT** *(2026-09-23)* | Mỗi `@action` là một **tool**; mọi nguồn (`local_grammar`, `system_one`, `system_two`, `mcp`) gửi cùng một `ToolCall` qua duy nhất `dispatch()` → `c.do()` → gate → token; dispatcher chèn `call_source`. SDK MCP qua extra `neuroedge[mcp]`. Đặc tả: Gated Tool Profile ([`docs/spec/tool_calling.md`](../docs/spec/tool_calling.md) §1–§5). |
| **Q-25** | Ràng buộc tham số của tool call | **ĐÃ CHỐT** *(2026-09-23; RFC-0005 chấp thuận 2026-09-24, không có `arguments_closed` ở v1)* | Ràng buộc tham số (khoảng, tập giá trị, độ dài) nằm **trong gate** (RFC-0005): kế thừa chỉ thu hẹp, `gate lint` chứng minh được và ánh xạ vào `inputSchema` cho mô hình. |
| **Q-26** | Ai xác nhận `on_block: ask` | **ĐÃ CHỐT** *(2026-09-23)* | Chỉ **người, qua kênh thiết bị** xác nhận được; `system_two` và `mcp` bị từ chối. Xác nhận làm gate lượng giá lại tiêu chí trong `on_block.confirms` (RFC-0006, [`docs/spec/tool_calling.md`](../docs/spec/tool_calling.md) §6). Sửa bởi Q-72: cho phép người duyệt qua kênh chat đã ghép đôi bằng bản ghi duyệt; LLM không bao giờ duyệt. |
| **Q-27** | NeuroEdge làm MCP client | **ĐÃ CHỐT** *(2026-09-23)* | System 2 là **MCP host**: tool thiết bị qua MCP server của agent (qua gate); MCP server bên ngoài chỉ lấy thông tin theo allowlist `[mcp.servers]`, kết quả là dữ liệu không tin cậy. MCU không làm host ([`docs/spec/tool_calling.md`](../docs/spec/tool_calling.md) §10). |
| **Q-28** | Mốc giao lớp trừu tượng provider (FR-GW) | **ĐÃ CHỐT** *(2026-09-24)* | FR-GW thuộc lõi: **v1.0 giao FR-GW-01 và FR-GW-03 tối thiểu** (bảng `[system_two]` trong `agent.toml`, key từ biến môi trường; failover trong mã). **v1.1 giao phần còn lại** (TSK-K2-01→03, FR-GW-02, 04 phía máy chủ, 05, 06, 07; client streaming MCU là TSK-S5-06). Lý do: v1.0 chạy cục bộ, phần cho đội thiết bị đi cùng Fleet OS. |
| **Q-29** | Định vị trước MHS (Anthropic) | **ĐÃ CHỐT** *(2026-09-24)* | **Theo dõi, không đầu tư ở v1.0** (trượt PF-3; [`TODOS.md`](../TODOS.md) #32–#33). Khi MHS mở mã nguồn và ổn định, hỗ trợ bằng adapter HAL host trên `linux` do cộng đồng/đối tác port; NeuroEdge định vị là tầng an toàn và kiểm thử trên thiết bị MHS. |
| **Q-30** | Định vị "Hợp đồng vào Physical AI" (engine-first) | **ĐÃ CHỐT** *(2026-09-24)* | Hợp đồng là lớp bảo vệ gần nhất trên 5 nguyên thủy HAL: không hợp đồng, không hành động; kiểm thử trong CI, chạy nhất quán mọi target. Sửa bởi Q-72: mở rộng thành nơi biến ý định thành sản phẩm vật lý có AI (dựng, chạy an toàn, chia sẻ và bán); hợp đồng thành lớp niềm tin. |
| **Q-31** | Tên và định vị NeuroBrain | **ĐÃ CHỐT** *(2026-09-25, CPO)* | Đã bị thay bởi Q-71: bỏ tên NeuroBrain, năng lực gọi là NeuroEdge Lab qua MCP và định vị gộp vào Q-30. |
| **Q-32** | Hướng mở rộng cho robot phân tầng (FOFOCA) | **ĐÃ CHỐT** *(2026-09-25, CPO)* | Mở rộng robot phân tầng sau Developer Beta, giữ nguyên đường găng v1.0: trace đa node mở rộng trường tuỳ chọn trong `trace.v1`, motor/servo là nguyên thủy `motion.*` riêng (Q-37), wire protocol theo Q-36, an toàn theo Q-38. |
| **Q-33** | Node RP2350 do đội lõi port | **ĐÃ CHỐT** *(2026-09-25, CPO)* | RP2350 là node tham chiếu thứ hai cho robot phân tầng sau Beta, do đội lõi port (HAL C trên Pico SDK, walker C99 ARM, test trên mạch thật). Bo tham chiếu v1.0 vẫn là ESP32-S3-Box-3 (Q-2). |
| **Q-34** | ROS 2 / Nav2 | **ĐÃ CHỐT** *(2026-09-25, CPO)* | Tích hợp nguyên bản ROS 2 và Nav2 qua adapter tại ranh giới gate; gate xét mọi lệnh tốc độ kể cả khi Nav2 đang dẫn đường. Cần RFC riêng và kiểm chứng nhu cầu theo Q-38 trước khi thiết kế (`TODOS.md` #40). |
| **Q-35** | Trạng thái an toàn khi node mất liên lạc | **ĐÃ CHỐT** *(2026-09-25, CPO)* | Mỗi cơ cấu tự khai trạng thái an toàn khi mất liên lạc với não (`safe_state`), không khai thì dừng (fail-closed); cần RFC khai báo (`board.v1`/`@action`). Sửa bởi Q-72: `safe_state` mở rộng cho mọi cơ cấu. |
| **Q-36** | Wire protocol giữa Pi và node MCU | **ĐÃ CHỐT** *(2026-09-25, CPO)* | Dùng **Zenoh-pico** trên MCU và `zenohd` trên Pi (Apache-2.0). Phép thử loại trên mạch thật đo ba ngưỡng: độ trễ p99 ≤ 20 ms, SRAM nội ≤ 40 KB, tự nối lại ≤ 2 s; trượt mới xét micro-ROS. |
| **Q-37** | Token cho lệnh `motion.*` | **ĐÃ CHỐT** *(2026-09-25, CPO)* | Lệnh `motion.*` dùng **token thuê có hạn (lease)**: kênh, biên độ tối đa và thời hạn ngắn (~200 ms). Hết hạn hoặc mất liên lạc thì cơ cấu tự về `safe_state` (Q-35); gate vẫn là hàm thuần, đếm hạn ở HAL/runtime. |
| **Q-38** | Chứng nhận an toàn chức năng (IEC 61508, ISO 13849, ISO 13482) | **ĐÃ CHỐT — tạm thời** *(2026-09-25, CPO)* | Tạm thời loại khỏi phạm vi: NeuroEdge **không** phải chức năng an toàn được chứng nhận (không SIL, không PL); bảo vệ nguy hiểm luôn do phần cứng (nút dừng khẩn, rơ-le, phao). Xem xét lại khi có dữ liệu phỏng vấn (`TODOS.md` #40). |
| **Q-39** | Roadmap theo increment và chính sách phát hành | **ĐÃ CHỐT** *(2026-09-25, CPO)* | Roadmap duy nhất đo bằng **increment `I0…`** kèm điều kiện vào, bằng chứng ra và một ngày dự báo (roadmap §0.2). Không phát hành ra ngoài cho tới I6 (công khai PyPI, A9); riêng một đội đối tác nhận wheel trực tiếp (Q-70). Đóng băng tính năng Beta áp dụng cho dòng `1.0.x`. Nhân sự cập nhật bởi Q-60; thứ tự cập nhật bởi Q-72. |
| **Q-40** | Thứ tự các hướng mở rộng sau Beta | **ĐÃ CHỐT** *(2026-09-25, CPO)* | Đã bị thay bởi Q-53, Q-55 và Q-71: thị giác vào v1.0 (Q-53), NeuroBrain thành NeuroEdge Lab (Q-55, Q-71); sau Beta còn mở rộng target (I11/I2c), port cộng đồng (I13) và robot (I14). |
| **Q-41** | Điều kiện mở v1.1 và B3 | **ĐÃ CHỐT** *(2026-09-25, CPO)* | v1.1 mở khi Beta đạt đồng thời **B1 và B2** (§3.3); B3 bỏ khỏi điều kiện mở (đo qua Registry ở v1.1 nên tránh phụ thuộc vòng), vẫn theo dõi để nối vào C5. |
| **Q-42** | C6 ở v1.1 | **ĐÃ CHỐT** *(2026-09-25, CPO)* | **C6 là chỉ số theo dõi**, không là điều kiện phát hành v1.1 (công bố khi đạt C1–C5, C7, C8). Lý do: hòa vốn cần hàng chục nghìn thiết bị nên không thể chặn phát hành kỹ thuật. Sửa bởi Q-72: theo dõi các dòng thu mới. |
| **Q-43** | Mốc kiểm chứng giả định G-a..G-e | **ĐÃ CHỐT** *(2026-09-25, CPO)* | Mốc kiểm chứng giả định neo theo increment (§13.3): G-b khi I8 đóng (cùng B5); G-a và G-c đo 90 ngày sau I9; G-d đo 1 năm sau I10 (tín hiệu sớm B3); G-e đo 180 ngày sau ba site AURA. |
| **Q-44** | Bậc cắt 5 — tách thoại khỏi MCU | **ĐÃ CHỐT** *(2026-09-25, CPO)* | Bỏ bậc cắt 5: thoại trên ESP32-S3 là bắt buộc cho v1.0, giữ A6. Nếu trượt ngưỡng Q-3 thì dời lịch I5 (TSK-S5-05, TSK-S5-07) chứ không cắt phạm vi. Sửa bởi Q-72: tạm dừng thoại để ưu tiên Blueprint bể cá, không cắt. |
| **Q-45** | Giấy phép của NeuroEdge và kho công khai | **ĐÃ CHỐT** *(2026-09-25, CPO)* | **Mã lõi theo PolyForm Noncommercial 1.0.0**, chuẩn giữ mở theo **Apache-2.0** (`schemas/`, `docs/spec/`, `fixtures/compliance/`, `LICENSING.md`). Cá nhân phi thương mại dùng miễn phí; thương mại cần license của NeuroEdge (`TODOS.md` #44). Đóng góp ngoài cần CLA (`TODOS.md` #43). Kho công khai toàn bộ từ 2026-09-25; PyPI mở ở I6. Sửa bởi Q-72: PolyForm NC là cơ chế thu tiền khi bán Blueprint hoặc thiết bị. |
| **Q-46** | Câu "có"/"không" nói ra trả lời câu hỏi nào | **ĐÃ CHỐT** *(2026-09-26)* | Câu trả lời thoại chỉ xác nhận câu hỏi `ask` của chính lượt đó (đang mở hoặc cắt lời khi đang đọc); không áp dụng cho lượt trước. TTS đọc lỗi thì về IDLE, không mở xác nhận (`docs/spec/voice_fsm.md`, RFC-0006). Lý do: tránh ảo giác STT hoặc trả lời nhầm câu hỏi. |
| **Q-47** | FastAPI WebSockets trong Fleet OS dùng cho gì | **ĐÃ CHỐT** *(2026-09-28)* | FastAPI WebSockets trong Fleet OS **chỉ dùng cho kết nối và viễn trắc**; âm thanh không qua Fleet OS mà đi thẳng tới lớp provider lõi (FR-GW-04). Lý do: bảo vệ quyền riêng tư (NFR-PRIV-03) và NeuroEdge không đứng giữa luồng token (N4). |
| **Q-48** | Máy trạng thái hội thoại thuộc tầng nào | **ĐÃ CHỐT** *(2026-09-28)* | Máy trạng thái hội thoại thuộc **L2 — Perception & runtime hội thoại** (`docs/spec/voice_fsm.md`), chạy thời gian thực trên cả chip lẫn host với cùng vector tuân thủ, không lượng giá gate và không lái chân trực tiếp. |
| **Q-49** | Mỗi increment ra kèm một demo | **ĐÃ CHỐT** *(2026-09-29)* | Mỗi increment bắt buộc kèm một demo chạy được trong `demo/<increment>/` (roadmap §11.1, `demo/README.md`), kiểm chứng bằng review trước khi đánh dấu hoàn thành. Lý do: bảo đảm tính kiểm chứng độc lập khi chưa có phần cứng. |
| **Q-50** | Phiên thoại thời gian thực trên máy tính, trước khi có Pi | **ĐÃ CHỐT** *(2026-09-29)* | Hỗ trợ thoại thời gian thực trên `sim` qua `neuroedge run --mic` (TSK-I4-04): tai nghe cho full-duplex (cắt lời được); loa ngoài dùng `--half-duplex` (không cắt lời). Pi giữ AEC PipeWire; wake-word demo chỉ thử nội bộ (`TODOS.md` #49). |
| **Q-51** | Giao diện của milestone: NeuroEdge Studio | **ĐÃ CHỐT** *(2026-09-29)* | Lệnh `neuroedge studio` mở web UI cục bộ đa màn hình trên 127.0.0.1 (TSK-I1-04, `docs/spec/studio.md`), bảo đảm an toàn: không tài nguyên ngoài, không lộ key. Sửa bởi Q-72: tạm dừng cùng thoại. |
| **Q-52** | MVP = v1.0 đầy đủ, bốn phase | **ĐÃ CHỐT** *(2026-09-30, chủ sản phẩm)* | MVP là v1.0 đầy đủ (năm nguyên thủy lõi + bốn gói mở rộng Q-53 trên ba target, nghiệm thu A1–A12), trượt thì dời ngày có bằng chứng chứ không cắt phạm vi. Nhân sự thay bởi Q-60. Sửa bởi Q-72: không cắt phạm vi nhưng đổi thứ tự, đưa Blueprint bể cá (I2d, I2e) lên trước, phạm vi v1.0 xét lại ở cổng 8 tuần. |
| **Q-53** | Bốn gói nguyên thủy mở rộng trên ba target | **ĐÃ CHỐT** *(2026-09-30, chủ sản phẩm)* | Bốn gói nguyên thủy mở rộng vào v1.0 trên cả ba target bậc 1 (RFC-0007, RFC-0009→0013): cảm biến, PWM, thị giác (`vision.in`), chuyển động (`motion.*`). Thêm bo ESP32-S3 có camera (Q-61) và profile `sim-rpi5`. Phong bì an toàn áp dụng chung cho mọi actuator. |
| **Q-54** | Thị giác trong gate | **ĐÃ CHỐT** *(2026-09-30, chủ sản phẩm)* | Dữ kiện thị giác do maker tự định nghĩa từ nhãn model; gate khoá ngưỡng tin cậy bằng tiêu chí `numeric` (RFC-0009), không có ngữ nghĩa gate riêng. Mất camera hoặc model thì dữ kiện chưa quyết và gate chặn; vết ghi chỉ lưu tham chiếu, không lưu ảnh thô (RFC-0012). |
| **Q-55** | NeuroBrain vào MVP | **ĐÃ CHỐT** *(2026-09-30, chủ sản phẩm)* | Đã bị thay bởi Q-71: chuyển thành NeuroEdge Lab qua MCP, giữ nguyên phạm vi bốn gói nguyên thủy nhưng không tự chạy LLM. |
| **Q-56** | Bỏ luật cổng nhu cầu | **ĐÃ CHỐT** *(2026-09-30, chủ sản phẩm)* | Đã bị thay bởi Q-72: khôi phục cổng nhu cầu có hiệu lực đo sau khi chốt Q-72 8 tuần với ba tiêu chí B6, B7, B8. |
| **Q-57** | Câu hỏi mở của sáu RFC nguyên thủy mở rộng | **ĐÃ CHỐT** *(2026-09-30, chủ sản phẩm uỷ quyền, nguyên tắc an toàn cao nhất)* | Chốt các câu hỏi mở của RFC-0007, RFC-0009→0013 (§9 của từng RFC): I2C chỉ ghi con trỏ thanh ghi đã khai; phong bì có `max_continuous_ms` và `min_interval_ms`; tiêu chí `numeric` cần `range` và `max_age_ms`; PWM bắt buộc `enable_pin`; `motion.*` dừng khi cắt lời/BLOCK/mất liên lạc, lease 200 ms; thị giác `present` cần ≥ 2 khung liên tiếp. Sửa bởi Q-72: mở rộng `safe_state` phủ mọi cơ cấu qua RFC an toàn có điều kiện. |
| **Q-58** | Bề mặt tích hợp vào MVP | **ĐÃ CHỐT** *(2026-10-01, chủ sản phẩm)* | Hai hạng mục vào I6: (1) MCP qua mạng có xác thực Streamable HTTP + OAuth 2.1 + mTLS (TSK-P2-04, mặc định tắt); (2) đóng băng Gated Tool Profile vào `schemas/` qua RFC (TSK-I6-05). Lý do: cho phép hệ sinh thái ngoài tích hợp qua chuẩn mở Apache-2.0 an toàn. |
| **Q-59** | Giấy phép qua v1.0, mở sau | **ĐÃ CHỐT** *(2026-10-01, chủ sản phẩm)* | Giữ PolyForm Noncommercial cho mã nguồn qua v1.0; xem xét mở sau khi có dữ liệu Beta (`TODOS.md` #51). CLA bắt buộc cấp quyền tái cấp phép để mở trong tương lai (`TODOS.md` #43). Hệ sinh thái ngoài tích hợp qua chuẩn Apache-2.0 (Q-58). |
| **Q-60** | Mô hình vận hành: một người + AI agent | **ĐÃ CHỐT** *(2026-10-01, chủ sản phẩm)* | Mô hình vận hành là chủ sản phẩm kết hợp AI agent (thay nhân sự Q-52; V1→V7 là làn việc, không phải người). AI agent làm việc trên host; việc cần phần cứng, người ngoài hoặc chữ ký do người thực hiện với kịch bản chuẩn bị sẵn. |
| **Q-61** | Bo ESP32-S3 có camera | **ĐÃ CHỐT** *(2026-10-01, chủ sản phẩm)* | Chọn **M5Stack CoreS3** làm bo tham chiếu thứ hai cho `esp32s3` (Box-3 vẫn là mặc định). Bo đạt chuẩn RFC-0013: Flash 16 MB, PSRAM 8 MB, camera GC0308 VGA, dual-mic ES7210, loa AW88298, màn cảm ứng, I/O Grove/M5-Bus. Bác bỏ ESP32-S3-EYE (thiếu loa, flash hẹp) và Korvo-2 (rời rạc). |
| **Q-62** | Sửa sáu RFC nguyên thủy mở rộng theo review độc lập | **ĐÃ CHỐT** *(2026-10-01, chủ sản phẩm duyệt hướng sửa, nguyên tắc an toàn cao nhất như Q-57)* | Sửa sáu RFC nguyên thủy mở rộng (RFC-0007, RFC-0009→0013): lệnh về phía an toàn không bị gate/phong bì chặn; tự tắt bắt buộc tại `min(hạn, max_continuous_ms)`; phong bì ghi bền write-ahead; mọi chân `digital_out` mặc định là cơ cấu chấp hành trừ khi khai `signal_pins`; watchdog cho hẹn giờ an toàn; thị giác lượng giá từng khung rồi AND; `NETR` v2 ghim byte ở RFC-0009. Sửa bởi Q-72: "phía an toàn" theo `safe_state` trong `board.v1` (bắt buộc khoá liên động phần cứng nếu khác `off`). |
| **Q-63** | Khoảng hở nền tảng cho người tích hợp | **ĐÃ CHỐT** *(2026-10-02, chủ sản phẩm)* | Bổ sung ba hạng mục nền tảng vào I6: (1) định nghĩa bề mặt Python công khai `__all__` có SemVer (TSK-I6-06); (2) mở rộng RFC TSK-I6-05 khoá schema `board.v1` và danh mục mã lỗi; (3) viết RFC dữ kiện từ tiến trình ngoài (TSK-I6-07). Không phơi tool MCP quản trị qua mạng để tránh tấn công lặp (`TODOS.md` #29). |
| **Q-64** | Quy tắc ngừng hỗ trợ của API Python công khai | **ĐÃ CHỐT** *(2026-10-03, chủ sản phẩm)* | Quy tắc ngừng hỗ trợ (`docs/spec/python_api.md` §3, §5): tên công khai đánh dấu ngừng hỗ trợ ở bản MINOR, giữ qua một bản MINOR kèm `DeprecationWarning` trước khi bỏ ở bản MAJOR (trong `0.x` bản MINOR đóng vai MAJOR). Chốt hợp đồng CLI và ghim cây lệnh bằng `test_cli_contract.py`. |
| **Q-65** | Câu hỏi mở của RFC-0014 (dữ kiện từ tiến trình ngoài) | **ĐÃ CHỐT** *(2026-10-04, chủ sản phẩm; nguyên tắc an toàn cao nhất như Q-57)* | Chốt RFC-0014 ([RFC-0014](../docs/rfc/0014-du-kien-tu-tien-trinh-ngoai.md) §9): chỉ nhận dữ kiện từ tiến trình cùng máy qua Unix socket; `esp32s3` không nhận nguồn ngoài; chỉ hỗ trợ `numeric` (nhị phân biểu diễn 0/1); chỉ bật khi `agent.toml` có `[external]`. Mã hiện thực kéo vào I2c theo Q-67. |
| **Q-66** | Câu hỏi mở của RFC-0015 (hợp đồng cho người tích hợp) | **ĐÃ CHỐT** *(2026-10-04, chủ sản phẩm và kỹ thuật trưởng; nguyên tắc an toàn cao nhất như Q-57)* | Chốt RFC-0015 ([RFC-0015](../docs/rfc/0015-hop-dong-cho-nguoi-tich-hop.md) §10): `reason` là chuỗi mở, `status` quyết định phán quyết; đóng băng `tool-call.v1.json`, `tool-result.v1.json` và danh mục `schemas/error-codes.v1.json`; khoá `schema` bo mạch mặc định `v1`, phiên bản lạ bị từ chối; hoãn khoá bắt buộc hiểu cho `board.v1` (`TODOS.md` #58). |
| **Q-67** | Nền tảng mở: bên thứ ba tự nối NeuroEdge với sản phẩm mới mà không chờ đội lõi | **ĐÃ CHỐT** *(2026-10-04, chủ sản phẩm; kỹ thuật trưởng ký RFC-0002)* | Bên thứ ba tự nối với NeuroEdge mà không sửa lõi qua **increment I2c — Nền tảng mở** (M6, U7, A13, FR-EXT). Tám điểm: không gian tên `source` (`bridge:<id>`, RFC-0017); hiện thực RFC-0014 trong I2c; RFC-0002 và `--board <đường dẫn>` (RFC-0016); cơ cấu từ xa có mức tự tắt (RFC-0018); corpus tuân thủ sang Apache-2.0; SDK `neuroedge.sdk` có phiên bản riêng; runtime giữ PolyForm NC; plugin theo giấy phép tác giả. |
| **Q-68** | Câu hỏi mở của RFC-0016, RFC-0017, RFC-0018 (nền tảng mở) | **ĐÃ CHỐT** *(2026-10-04, kỹ thuật trưởng ký trên PR #99; nguyên tắc an toàn cao nhất như Q-57)* | Chốt §9 của RFC-0016, RFC-0017, RFC-0018: `neuroedge.guard` ổn định ngang `__all__`; bridge cấm chuyển lời xác nhận `ask` (`bridge:*` ngoài `HUMAN_SOURCES`); cơ cấu từ xa khai ở `agent.toml` và bắt buộc đọc lại cho hành động không hoàn tác; adapter Home Assistant ở kho riêng; chốt các hằng số an toàn tắt (`OFF_SLACK_MS` 100 ms, `OFF_RETRY_MS` 500 ms). |
| **Q-69** | Giả lập ngoại vi `esp32s3` và kernel đủ module cho `linux` trước khi bo mạch về (bổ sung Q-21) | **ĐÃ CHỐT** *(2026-10-05, chủ sản phẩm)* | Ba spike giả lập bổ sung Q-21: (1) `esp-emulator` (Espressif) cho GPIO/I2C/Wi-Fi `esp32s3` (TSK-I3-02); (2) `esp32sim` để ước lượng sớm bộ nhớ ESP-SR và chạy suy luận (TSK-I3-03); (3) kernel trong VM (virtme-ng) cho `linux-hal` có `pwmchip` và âm thanh thật, cộng runner ARM64 (TSK-I2a-08). Vẫn loại Wokwi và Renode; không thay thế đo trên phần cứng thật. |
| **Q-70** | Thử riêng với một đội đối tác trên thiết bị họ đang có, không chờ bo mạch (bổ sung Q-39; giữ Q-52) | **ĐÃ CHỐT** *(2026-10-09, chủ sản phẩm)* | Thử nghiệm riêng trước I6 với một đội đối tác trên thiết bị sẵn có qua `proxy mcp`, `proxy http`, `neuroedge.guard`, `sim` và Action CI (TSK-I2c-19). Phân phối wheel trực tiếp, không lên index, không chờ bo mạch. Loại trừ: `esp32s3`, thoại trên chip. Lý do: lấy phản hồi người dùng thực tế trước khi công khai. |
| **Q-71** | NeuroEdge Lab: dựng hợp đồng bằng AI người dùng đang có, qua MCP — thay NeuroBrain (thay Q-31; đổi cách hiện thực của Q-55; giữ phạm vi Q-52) | **ĐÃ CHỐT** *(2026-10-10, chủ sản phẩm)* | **NeuroEdge không tự chạy LLM để dựng hợp đồng** mà phơi năng lực lab thành tool MCP trung lập: client viết, NeuroEdge chấm và cưỡng chế, chỉ người khoá qua PR (thay Q-31, đổi cách hiện thực Q-55). Hai nhóm tool: tool tác động (`lab_pulse`, `lab_read`) qua gate và tool dựng (xem bo, kiểm bản nháp, replay) chỉ ghi thư mục agent. Cấm mọi tool khoá bản nháp hay sửa `digests.lock`. Tool MCP và Action CI (`neuroedge lab check`) dùng chung mã kiểm. Client có shell là bên gọi không tin cậy: tách quyền thiết bị (chỉ `mcp serve` giữ quyền), nạp chính sách từ nhánh đã duyệt. Restyle IBM Plex chờ mở rộng Q-11 (TSK-N0-06). Sửa bởi Q-72: Lab là vòng ① dựng hợp đồng nhiệm vụ. |
| **Q-72** | Định vị Blueprint: từ một câu nói tới một sản phẩm vật lý có AI — dựng, chạy an toàn, chia sẻ và bán (sửa Q-26, Q-30, Q-45, Q-62; đảo Q-56; đổi thứ tự Q-52; bổ sung Q-57, Q-71) | **ĐÃ CHỐT HƯỚNG** *(2026-10-11, chủ sản phẩm; RFC từng phần cần chữ ký kỹ thuật trưởng)* | **Định vị ba vòng:** ① **Dựng** — client MCP gợi ý kit, sinh firmware, chạy thử trên `sim`, nạp, nối chat (Q-71); ② **Chạy** — agent vận hành 24/7 thực thi hợp đồng nhiệm vụ nhiều thiết bị (được/cấm, tần suất, khung giờ, watchdog có cận, luồng dữ liệu, khi hỏng về `safe_state`, hết hạn), phản xạ MCU, bộ phát hiện tất định trước rồi mới gọi LLM, báo chủ động qua chat; ③ **Chia sẻ, bán** — NeuroEdge Blueprint (kit + firmware + hợp đồng mẫu + bộ phát hiện + bằng chứng), `blueprint pack`/`install`, Hub. Hợp đồng là lớp niềm tin. Người dùng đầu: maker cộng đồng HA/ESPHome (U1), rồi micro-OEM (U5); U2, U3 lùi xuống phụ. Blueprint đầu tiên: bể cá. LLM: người dùng tự trả (BYOK qua LiteLLM, có mô hình tại chỗ), có trần chi phí trong hợp đồng; chạm trần thì phản xạ và cảnh báo mẫu cứng vẫn chạy. Dòng tiền: PolyForm NC (Q-45) là cơ chế thu khi bán Blueprint hoặc thiết bị; hoa hồng kit (liên kết bán kit bể cá ở I2e), relay tuỳ chọn, giấy phép theo thiết bị, chia doanh thu Blueprint; không dòng thu nào nằm trên đường an toàn. Bốn điểm chốt: (1) người duyệt qua kênh chat (Telegram trước) bằng bản ghi duyệt một lần có hạn và digest, bản duyệt ≤ 5 dòng; nhóm chat và LLM không bao giờ duyệt; (2) bằng chứng MVP chưa ký (người cài tự replay, ký trước khi Hub thu tiền ở `TODOS.md` #1); (3) `safe_state` khác `off` chỉ khai trong `board.v1` kèm khoá liên động phần cứng, sửa `TODOS.md` #58 trước; (4) giả lập trước phần cứng thật mua sau qua 4 tầng G1–G4 (firmware ESP32 trên QEMU, Wokwi và Velxio chờ đối chiếu Q-21, Q-69). Cổng nhu cầu 8 tuần đo B6, B7, B8; trượt B8 thì giữ vòng ①② làm công cụ cá nhân. Thứ tự: hợp đồng nhiệm vụ, agent vận hành, kênh chat, Blueprint tối thiểu đi trước; thoại, Studio, `jetson` tạm dừng. Cần RFC: an toàn có điều kiện, `mission.v1`, `blueprint.v1`, luồng dữ liệu, nguồn `chat:<id>`. Hệ quả đã chấp nhận: rủi ro tài khoản chat bị chiếm, bằng chứng chưa ký, giới hạn giả lập, thêm hai vai quản trị (agent vận hành, Hub). *Bổ sung bởi Q-81 (2026-10-14): điều kiện ① đếm cả hộp + NeuroClaw như một Blueprint mẫu, ngưỡng không đổi.* |
| **Q-73** | Mở, có minh bạch: người dùng tự chọn cách xác minh và luồng nhiều bước (sửa Q-26, Q-15) | **ĐÃ CHỐT HƯỚNG** *(2026-10-12, chủ sản phẩm; RFC cần chữ ký kỹ thuật trưởng)* | NeuroEdge giúp người dùng dựng IoT, AIoT, Physical AI nhanh và **không quyết hộ họ cách xác minh hay luồng tương tác**. **Mở:** (1) *bước xác minh do người dùng khai* — đọc mã, giọng nói, khuôn mặt, bàn phím, thẻ, điện thoại… qua plugin bộ kiểm (Extension SDK); một bước xác minh đạt thì đặt dữ kiện người dùng khai (ví dụ `user_verified`), kể cả khi bằng chứng đến từ lời nói; (2) *luồng nhiều bước do người dùng viết* (đánh thức → yêu cầu → hỏi lại → xác minh → hành động); (3) NeuroEdge không cấm cách nào; gate vẫn nới được như hôm nay (`fail: open`, bỏ tiêu chí). **Minh bạch thay cho cấm:** mỗi cách xác minh mang mức rủi ro khai sẵn (ví dụ mã đọc to: nghe lén, phát lại được), hiện trong bản duyệt, trong `gate explain` và trong NeuroEdge Blueprint để người cài thấy trước. **Ba bất biến giữ lại** — bảo vệ người dùng khỏi người khác, không giới hạn lựa chọn của họ: (a) LLM, client MCP và nguồn tự động không bao giờ trả lời bước xác minh hay câu hỏi lại dành cho người (chống prompt injection; Q-26, FR-CH-05); (b) luật đã khai chạy đúng như khai, không đường vòng ngầm; (c) mọi bước xác minh và phán quyết ghi vào vết ghi (không ghi mã bí mật — chỉ đạt/trượt). **Cần RFC** (CONTRIBUTING §3, ngữ nghĩa xác nhận): kiểu bước xác minh trong `on_block`, giao diện plugin bộ kiểm, số lần thử và hạn, sự kiện vết ghi; việc theo dõi: TSK-I2d-20. **Lý do:** người dùng muốn tự quyết cách dùng thiết bị của mình; cấm hộ làm NeuroEdge khó dùng mà không thêm an toàn cho chính chủ. **Hệ quả đã chấp nhận:** người dùng chọn cách yếu (mã đọc to) thì chịu rủi ro đã được hiện rõ; NeuroEdge không chặn. |
| **Q-74** | Não trên cloud tuỳ chọn, tuỷ sống tại nhà: "đấu vào chat là có agent" (sửa hệ quả "không máy chủ" của Q-10 và N4 ở bước 2; bổ sung Q-72) | **ĐÃ CHỐT HƯỚNG** *(2026-10-12, chủ sản phẩm; bước 2 chờ số đo cổng nhu cầu)* | Người dùng không phải tự host agent (OpenClaw hay máy chủ riêng) mà vẫn có agent trông nhà chỉ bằng chat. **Chia đôi theo ranh giới sẵn có của Q-72:** *não* (LLM worker, trò chuyện, lập kế hoạch, biên dịch hợp đồng nhiệm vụ) được phép chạy trên **NeuroEdge Cloud tuỳ chọn**; *tuỷ sống* (gate, phản xạ, kiểm bản ghi duyệt, cửa ra dữ liệu, vết ghi) **luôn ở nhà**. Hộp tại nhà mở kết nối ra, không mở cổng; mất mạng thì an toàn vẫn chạy; cloud bị chiếm thì hộp vẫn chỉ thi hành luật đã ký và lời duyệt đã kiểm tại chỗ. **Hai bậc hộp tại nhà:** *đầy đủ* — Pi hoặc add-on Home Assistant (camera, nhiều hãng, nhật ký 30 ngày, LLM tại chỗ tuỳ chọn); *nhỏ* — ESP32-S3 cho một việc cụ thể (walker `NETR`, sổ token, phản xạ, kiểm lời duyệt trên chip; luật biên dịch ở cloud, nhận có ký; nhật ký đẩy lên cloud mã hoá hoặc thẻ SD). **Hai bước:** (1) ngay — I2d như kế hoạch (runtime và Telegram tại máy nhà) cộng hộp tại nhà dễ cài (add-on Home Assistant, ảnh thẻ SD cho Pi, ghép đôi bằng QR), TSK-I2e-12, TSK-I2e-13; (2) sau cổng nhu cầu 2026-12-06 và chỉ khi số đo cho thấy người thử vướng ở cài đặt, khoá API hay tự host — mở NeuroEdge Cloud có thuê bao (lúc đó sửa N4: NeuroEdge trả token trong gói, BYOK vẫn giữ) và bậc ESP32 — increment I2f (roadmap §4.3.6). **Lý do:** người dùng muốn "đấu vào chat là có"; ranh giới runtime tin cậy / LLM worker không tin cậy của Q-72 cho phép dời worker lên cloud mà không dời quyền phần cứng; thuê bao là dòng tiền rõ nhất. **Mạng lưới đa nút, đa nhà, đa người:** một ô chat điều phối nhiều ESP32, nhiều Pi, nhiều nhà và nhiều người; bốn nguyên tắc: (a) mỗi nút chỉ thi hành luật có chữ ký, lời duyệt kiểm tại nút; (b) việc không hoàn tác ở bất kỳ nhà nào luôn cần người xác nhận; (c) trần phạm vi và tốc độ cho một lệnh, bất thường thì tự khoá; (d) mỗi nút một danh tính, một vết ghi. Vai trò theo người: TSK-I2f-05. **Hệ quả đã chấp nhận:** vận hành dịch vụ cloud 24/7 có đường gửi lệnh vào nhà người dùng (bảo mật, chi phí token, trực sự cố) với đội một người + AI; ảnh và dữ liệu lên cloud khi người dùng khai đích đó (FR-EGR). |
| **Q-75** | Bằng chứng thực địa: "host nghĩ, ESP32 làm" — liên kết Pi ↔ ESP32 sớm, bo phổ thông, khung dự án nhiều chip, chưa làm quản lý đội thiết bị (bổ sung Q-35, Q-40, Q-74) | **ĐÃ CHỐT** *(2026-10-12, chủ sản phẩm)* | **Bằng chứng:** hai bài Reddit đọc 2026-10-12. (1) r/robotics, robot phun thuốc diệt cỏ SprayShark: Pi 5 gửi lệnh chữ qua USB serial tới ESP32-S3; bơm bật bằng relay; mất kết nối thì xe dừng nhưng bơm không tắt; không có watchdog; repo lộn xộn sau ba lần làm lại phần cứng; bo Freenove WROOM với Arduino, không phải Box-3. (2) r/IOT, khoảng 20 Pi 5 + Hailo cho nuôi thủy sản: chỉ suy luận, không cơ cấu; nỗi đau là OTA, giám sát, nguồn chập chờn, thẻ SD; đã xem Balena, Mender và thấy quá nặng; mạng khách hàng chỉ cho kết nối ra qua HTTPS. **Bốn quyết định:** (a) **liên kết host ↔ MCU tối thiểu lên I3a** — RFC node một host, một MCU qua serial, nhịp tim, mất liên lạc ⇒ `safe_state` tại MCU (TSK-I3a-06, TSK-I3a-07); bản nhiều node, black channel vẫn ở I14 (TSK-W3-02); (b) **bo ESP32-S3 phổ thông và Arduino** — DevKitC/WROOM là bo maker dùng thật (TSK-I3a-08, TSK-I3a-09); (c) **khung dự án nhiều chip** — `neuroedge new --layout host+mcu` trả lời câu "tổ chức dự án Pi + ESP32 thế nào", Blueprint đóng gói từ khung này (TSK-I2e-14); (d) **không làm quản lý đội thiết bị** (OTA, giám sát, cấp nguồn lại), kể cả tích hợp, trước khi người dùng thật đòi; I9 giữ nguyên chỗ. **Lý do:** người làm thật đã tự chia việc đúng như vỏ não / tuỷ sống nhưng tự chế giao thức và quên phản xạ mất liên lạc — đúng chỗ NeuroEdge có giá trị; hạm đội chỉ suy luận thì NeuroEdge không thêm gì. Ràng buộc "chỉ kết nối ra" của khách hàng xác nhận thiết kế kênh của Q-74. **Hệ quả đã chấp nhận:** I3a thêm bốn task, cần mua bo DevKitC; thư viện Arduino là bề mặt thứ hai phải giữ tương đương target (FR-TGT-04). |
| **Q-76** | Bộ não NeuroEdge: một worker siêu nhẹ kiểu PicoClaw, tự host trên board rẻ hoặc dùng NeuroEdge Cloud, mỗi người một instance cách ly (bổ sung Q-72, Q-74) | **ĐÃ CHỐT HƯỚNG** *(2026-10-12, chủ sản phẩm)* | **Bộ não NeuroEdge** là LLM worker của Q-72: trò chuyện qua kênh chat, gọi LLM, trí nhớ dạng tệp đọc được, lịch và heartbeat, biến lời nói thành *đề xuất*. Nó **không tin cậy** và chạm thế giới **chỉ qua MCP** tới runtime tin cậy tại nhà; không có `exec`, công cụ phần cứng hay tệp ngoài vùng của nó. **Một phần mềm, hai cách chạy:** (1) **tự host** — trên board Linux rẻ (khoảng $10, chục MB RAM) hoặc cùng Pi, add-on Home Assistant với runtime, dưới một user hệ điều hành riêng không có quyền phần cứng; (2) **NeuroEdge Cloud** — cùng phần mềm đó, NeuroEdge vận hành hộ: cổng kênh chat dùng chung chỉ định tuyến, mỗi người một instance cách ly (microVM), ngủ khi không có tin nhắn, trí nhớ mã hoá riêng; hộp tại nhà mở kết nối ra tới đúng instance của mình. Cloud vì vậy là *tiện lợi* (không phải cài), không phải *năng lực riêng*. **Nền mã:** bản rút gọn của PicoClaw (MIT): giữ kênh chat, nhà cung cấp LLM, trí nhớ, cron, heartbeat, MCP client; bỏ `exec`, `i2c`/`spi`/`serial`, công cụ tệp. Worker khác (PicoClaw gốc, Claude Desktop, OpenClaw) vẫn dùng được qua cùng bộ tool MCP. Trên ESP32, "não" là bậc nhỏ của Q-74 (kiểu zclaw, walker nhúng cùng chip), không phải bộ não này. **Lời duyệt không đi qua não:** việc không hoàn tác được duyệt bằng chữ ký trên điện thoại (passkey, mở từ nút trong chat) mà hộp tại nhà tự kiểm, hoặc duyệt tại chỗ trong mạng nhà; mỗi cách mang nhãn rủi ro (Q-73). Cổng kênh chung của cloud chuyển tin nhưng **không giả được** lời duyệt (FR-CH-08). **Lý do:** bộ não đã là hàng hoá (họ OpenClaw, PicoClaw, zclaw, ESP-Claw); tự viết hai bản (tại nhà và cloud) là trùng công. Một phần mềm cho cả hai giữ lựa chọn tự host miễn phí và để thuê bao trả cho sự tiện lợi, nhiều nhà, nhiều người, bot duyệt được quản lý. **Hệ quả đã chấp nhận:** phụ thuộc một fork phải tự theo dõi bản gốc (PicoClaw ghi chưa dùng cho production trước v1.0) và rà soát bảo mật trước khi host cho người khác (TSK-I2f-06); cần nghĩa vụ ghi nhận nguồn MIT (roadmap §3.9); phần mềm chạy nhiều người (cổng kênh, relay, microVM) là việc vận hành mới cho đội một người + AI. Việc: TSK-I2d-22 → TSK-I2d-24, TSK-I2f-02, TSK-I2f-07 → TSK-I2f-09. **Sửa bởi Q-80 (2026-10-13):** bộ não không còn là bản rút gọn; NeuroClaw giữ đủ năng lực PicoClaw, shell và công cụ phần cứng là lựa chọn có nhãn; "chỉ qua MCP" còn đúng cho thiết bị của nhà. |
| **Q-77** | Gọn roadmap: bỏ thoại, NeuroEdge Lab, mở danh sách target và mọi increment sau Beta (đảo một phần Q-44, Q-52, Q-55; thay Q-40) | **ĐÃ CHỐT** *(2026-10-12, chủ sản phẩm)* | Roadmap còn khoảng 197 task chưa xong cho một người + AI, phần lớn không phục vụ hướng hiện tại (maker và nhà ở, ra lệnh qua chat, bộ não là hàng hoá, tuỷ sống ở nhà, Blueprint — Q-72, Q-74, Q-76). **Bỏ khỏi roadmap:** thoại I4, I5 (mã thoại trên host giữ nguyên); NeuroEdge Lab I4a, I5a (bộ tool MCP chuẩn TSK-I2d-23 thay vòng ①); mở danh sách target cho bên thứ ba (V1a, TSK-I2c-13, I2c-17); I9 provider tự host và Fleet OS (khớp Q-75); I10 Registry; I13 bộ port cộng đồng; I14 robot phân tầng; I16 Jetson; I17 đa phương thức; I18 hệ sinh thái thiết bị; Khối 4, Khối 5. Task của chúng còn một dòng mỗi task ở roadmap §6 để mã và tài liệu tra được; mỗi mục có mốc mở lại. **MVP v1.0 sau Q-77:** `sim`, `linux`, `esp32s3`; bốn gói nguyên thủy mở rộng; kit mẫu; nền tảng mở; nhiệm vụ 24/7 qua chat, bộ não qua MCP, Blueprint; OTA có ký. A6 đo 24 giờ không thoại; A11 bỏ cùng Lab. **Lý do:** tập trung vào thứ đem đi đo ở cổng nhu cầu 2026-12-06; mọi thứ bỏ đều đảo lại được bằng một `Q-N` mới kèm số đo. **Hệ quả đã chấp nhận:** mất demo "nói chuyện với con chip $5" và vòng dựng hợp đồng riêng của Lab; NeuroEdge không còn kế hoạch cho robot, Jetson hay dịch vụ đội thiết bị. |
| **Q-78** | NeuroClaw: bộ não NeuroEdge là một fork cứng của PicoClaw, repo riêng MIT (cụ thể hoá Q-76) | **ĐÃ CHỐT** *(2026-10-13, chủ sản phẩm)* | Demo chat đèn và cửa (2026-10-13) cho thấy ba chỗ PicoClaw gốc không hợp vai bộ não: client MCP không trình được chứng chỉ client nên phải có cầu nối mTLS; "tắt shell" chỉ là cấu hình, lật lại được qua cron (`allow_command` mặc định bật), hook tiến trình hoặc biến môi trường `PICOCLAW_TOOLS_*`; và câu hỏi `ask` của hộp chỉ là một kết quả tool bình thường. **Chốt:** fork cứng PicoClaw v0.3.1 thành **NeuroClaw**, repo riêng [`letrongminh/neuroclaw`](https://github.com/letrongminh/neuroclaw), giấy phép MIT như gốc (mã của PicoClaw buộc giữ MIT; MIT cũng để cộng đồng dùng và đóng góp). Ba bản vá: (1) mTLS cho MCP qua HTTP (`tls.ca_file`, `cert_file`, `key_file`), bỏ cầu nối; (2) khoá cứng: `exec`, i2c, spi, serial, cài skill, lệnh trong cron, hook tiến trình, theo dõi USB, registry skill và MCP stdio luôn tắt, cấu hình hay biến môi trường đều không bật lại được; (3) `BLOCK` kèm `confirmation` được nói rõ với LLM: chưa làm, chỉ chủ nhà ở nhà duyệt được, không gọi lại. Bỏ web console. **Đánh đổi đã chấp nhận:** tự gánh bảo trì, không nhận tự động bản sửa của PicoClaw (fork cứng, không theo upstream); tên NeuroClaw đã có người dùng (một báo cáo arXiv 2026 về thần kinh học, một nhóm tích hợp OpenClaw, vài repo nhỏ), chưa tra nhãn hiệu. **Không đổi:** Q-76 (một phần mềm, hai cách chạy; bộ não chỉ chạm thế giới qua MCP); worker khác (PicoClaw gốc, Claude Desktop) vẫn cắm được qua `cau-noi.py`. Việc: TSK-I2d-22; FR-AGT-12; demo `demo/i2f-chat-den-cua/`. **Sửa bởi Q-80 (2026-10-13):** bản vá (2) khoá cứng và việc bỏ web console được gỡ; (1) mTLS và (3) lời dặn khi `BLOCK` giữ nguyên. |
| **Q-79** | Bộ não và gate chung một chip ESP32-S3, kèm nhãn rủi ro: cách chạy thứ ba của bộ não (bổ sung Q-76; ngoại lệ có nhãn của Q-72 cho vi điều khiển) | **ĐÃ CHỐT** *(2026-10-13, chủ sản phẩm)* | Q-76 cho bộ não hai cách chạy: tự host trên board Linux rẻ và NeuroEdge Cloud (microVM). Chủ sản phẩm muốn thêm cách thứ ba: chỉ một ESP32-S3 (vài đô la), chat và duyệt trên Telegram, như zclaw và MimiClaw. Trên vi điều khiển không có tách tiến trình, nên chip đơn **không** có ranh giới cô lập bộ não không tin cậy khỏi gate mà Q-72 đòi; lỗi bộ nhớ trong mã bộ não (TLS, parser JSON) nằm cùng không gian địa chỉ với walker. Nói "triệt tiêu hoàn toàn rủi ro" là quá: các biện pháp dưới đây chỉ giảm nó. **Chốt:** cho phép, có nhãn rủi ro theo Q-73, không cấm. (1) Mọi tool call của LLM đi qua một hàng đợi có kiểu vào `ne_gate` (walker `NETR`, sổ token); không có đường LLM → GPIO. (2) Việc không hoàn tác cần nút vật lý trên bo hoặc callback Telegram từ đúng owner ID; chip nói thẳng với API Telegram qua TLS, không qua relay, nên không cần passkey như cloud (FR-CH-08). (3) Chip đơn mang nhãn `risk=single_chip` khi ghép đôi và trong `status`; bí mật ở dạng rõ khi chưa bật flash encryption mang nhãn `risk=readable_flash`. (4) Port mã C của zclaw (MIT) có ghi nguồn; **không** port vòng agent và tool GPIO của nó, nơi LLM bật chân trực tiếp. **Giai đoạn:** 1, làm ngay, chạy trên QEMU: boot guard, cấu hình và bí mật trong phân vùng NVS riêng (mã hoá dưới `sdkconfig.secure`), bảng điều khiển serial, stack guard trong CI (TSK-I2f-10). 2: Wi-Fi và client Telegram trên chip, chỉ owner ID (TSK-I2f-11). 3: vòng LLM trên chip, tool call qua `ne_gate`, duyệt bằng nút hoặc callback (TSK-I2f-12). Giai đoạn 2 và 3 cần bo DevKitC N16R8 (TSK-I3a-08). **Đánh đổi đã chấp nhận:** chip đơn cô lập kém hơn hai cách chạy kia; ba task này mở trước cổng nhu cầu 2026-12-06, ngoài điều kiện Q-74 của I2f (phần còn lại của I2f vẫn ⏸); bo chưa bật flash encryption giữ token ở dạng đọc được. **Không đổi:** Q-76 (hai cách chạy kia vẫn là đường chính), Q-78 (NeuroClaw cho Linux và cloud), Q-72 trên `sim` và `linux`. Việc: TSK-I2f-10 → I2f-12; `targets/esp32s3/`. |
| **Q-80** | NeuroClaw có đủ năng lực PicoClaw: gỡ khoá cứng, thay bằng nhãn rủi ro (sửa Q-76, Q-78 theo Q-73) | **ĐÃ CHỐT** *(2026-10-13, chủ sản phẩm)* | Khoá cứng của Q-78 làm NeuroClaw kém PicoClaw ở mọi việc ngoài nhà NeuroEdge: không shell, không cài skill, không lệnh trong cron, không hook, không MCP stdio, không web console, phát hành chỉ ba nền tảng. Chủ sản phẩm muốn NeuroClaw không kém PicoClaw ở điểm nào. **Chốt:** gỡ khoá cứng; mặc định như PicoClaw v0.3.1 (`exec`, lệnh cron, cài skill, registry bật; `i2c`/`spi`/`serial`, hook tiến trình, MCP stdio tắt nhưng bật được); mỗi năng lực đang bật được ghi lúc khởi động là `NeuroClaw risk=<tên>` (`shell`, `cron_shell`, `hardware_bus`, `skill_install`, `process_hooks`, `usb_monitor`, `stdio_mcp`) theo Q-73; khôi phục web console, launcher và phát hành đủ nền tảng (goreleaser: Linux, Windows, macOS, FreeBSD, NetBSD × amd64, arm64, riscv64, loong64, arm, s390x, mipsle; deb/rpm, ảnh Docker GHCR, DMG, nightly). Giữ: mTLS cho MCP, lời dặn khi `BLOCK`, NeuroClaw-ESP. **Nhà NeuroEdge** muốn bộ não khoanh vùng thì tắt trong `config.json` (demo `i2f-chat-den-cua` làm vậy); bộ não có shell chung máy với runtime thì cô lập worker (TSK-I2d-24) giữ thiết bị khỏi nó. **Đánh đổi đã chấp nhận:** "cấu hình nào cũng không có shell" không còn là bảo đảm của mã mà là lựa chọn của người dùng; một bộ não mở bị prompt injection chạy được lệnh trên máy của nó. **Không đổi:** Q-72 (gate là nơi duy nhất quyết việc thiết bị của nhà), Q-79 (chip không có shell). Việc: TSK-I2d-22; FR-AGT-12; demo `demo/i2f-chat-den-cua/`. |
| **Q-81** | Hộp + NeuroClaw vào cổng nhu cầu 8 tuần và thẻ định vị, ngưỡng giữ nguyên (bổ sung Q-72, TODOS #67) | **ĐÃ CHỐT** *(2026-10-14, chủ sản phẩm)* | **Chốt phương án B.** (1) Điều kiện ① (B6) đếm cả "hộp + NeuroClaw, điều khiển ít nhất một thiết bị qua chat, có vết ghi" như một Blueprint mẫu *trợ lý nhà qua chat*; ② (B7) đếm khi hộp chạy trên G2 hoặc G3 như mọi Blueprint; ngưỡng ở §11.2 không đổi. (2) `phong-van.md` §5c thêm thẻ D: "Nhắn tin cho nhà: việc thường thì làm, việc khó thì hỏi bạn." (3) `demo.md` có màn chat cho Maker. (4) Task mới TSK-I2d-25: gói cài hộp + NeuroClaw cho người ngoài. I2f giữ ⏸ (Q-74). **Vì sao:** cổng đo tới 2026-12-06, mà Blueprint (I2e) và agent vận hành (phần lớn I2d) chưa có mã; hộp + NeuroClaw đã chạy (NeuroClaw v0.2.x phát hành, demo `demo/i2f-chat-den-cua/` đủ sáu màn). Đo thêm thứ chạy được hôm nay, không hạ ngưỡng, không bỏ Blueprint. **Đã cân nhắc:** A — giữ như Q-72 (B6 đo thứ chưa có mã, dễ trượt vì thiếu sản phẩm chứ không vì thiếu nhu cầu); C — đổi trục sang chat-first (đảo Q-72 khi chưa có số liệu người nghe; trùng hạng mục "agent" của ESP-Claw, OpenClaw). **Cái giá:** TSK-I2d-25 phải xong trước người thử đầu tiên — khoá và token hôm nay là của script demo, hạn 30 ngày; cuộc phỏng vấn nào đã dùng ba thẻ thì ghi `M-MSG` riêng, không gộp với bốn thẻ. |

---

# Appendices

## Appendix A — Requirements Traceability Matrix

### A.1 Product Goal Traceability

Traceability from product goals to requirements and acceptance criteria.

| Mục tiêu | Yêu cầu chi phối | Chỉ số | Tiêu chí nghiệm thu |
|:---|:---|:---|:---|
| **M1** — TTFV under 10 minutes | FR-DX-01, FR-DX-02, FR-TGT-01, FR-TGT-06, FR-CLI-01 | Median TTFV | A1 |
| **M2** — All actions through contracts | FR-ACE-01→10, FR-MDL-10→12, FR-GATE-01→10, FR-HAL-07, FR-CLI-12 | Number of shortcuts to actuators | A3, A4, A5 |
| **M3** — Consistency across Tier 1 environments | FR-TGT-01→05, FR-CI-07, FR-HAL-06 | `neuroedge verify` results | A2 |
| **M4** — Field incident reproduction | FR-CI-01, FR-CI-02, FR-TRC-01→08, FR-FLT-05 | Time from incident to reproduction | A7, C7 |
| **M5** — Safe large-scale updates | FR-OTA-01→04, FR-FLT-02 | Number of bricked devices | C1 |
| **M6** — Third parties connect without modifying core | FR-EXT-01→09 | Time to author bridge; commands to wrap MCP server | A13 |
| **M7** — A single sentence into a contracted device | FR-MSN-01→14, FR-DX-09, FR-DX-10, FR-CLI-15 | Percentage of contradictory contracts caught; violating commands blocked | A15, A17, A21 |
| **M8** — Proactive operator agent with cost ceiling | FR-AGT-01→09, FR-CH-01→05, FR-EGR-01→05, FR-TRC-11→13 | 30-day LLM cost; correct trend detection | A16, A18, A19, A20, A22 |
| **M9** — Blueprint installable, someone wants to sell | FR-BP-01→10, FR-CLI-13 | Install time on clean machine; makers wanting to sell | A14, B6, B7, B8 |

### A.2 Invariant Principle Traceability

| Nguyên tắc | Yêu cầu hiện thực hóa | Yêu cầu kiểm chứng |
|:---|:---|:---|
| **P-1** Typed standard contracts | FR-ACE-01, FR-ACE-02, FR-ACE-03, FR-ACE-08→10, FR-MDL-10→12, FR-HAL-07, FR-CH-02, FR-AGT-02 | A3, A20, A21 |
| **P-2** Execution targets are peers | FR-TGT-01→05, FR-TGT-08 | A2 *(binding on Tier 1)* |
| **P-3** Value centers on product creators *(Q-72)* | FR-OTA-04, FR-BP-07, FR-BP-08, FR-BP-10, NFR-COMP-02, NFR-COMP-03 | Audit boundary of §6.4 in source document and §8.4 of this document; C6 |
| **P-4** AI models are replaceable components — cloud-first, provider-pluggable | FR-MDL-01→04, FR-MDL-07→09, FR-PER-07, FR-GW-01→07 | Test suites switching models and STT/TTS providers purely via configuration without modifying agent code |
| **P-5** Network effects from sharing gates, extension components, and NeuroEdge Blueprints | FR-GATE-05→08, FR-REG-01, FR-REG-04, FR-REG-08, FR-BP-01→05, FR-BP-09 | B3, B6, B8, C5 |

### A.3 Non-Functional Requirements Traceability

Non-functional requirements **are not traced via roadmap tasks** but via acceptance criteria and periodic reviews — because they are cross-cutting system properties, not disjoint work items. This table is the sole bridge linking NFRs to verification evidence.

| Nhóm | Yêu cầu | Cách kiểm chứng | Tiêu chí nghiệm thu |
|:---|:---|:---|:---:|
| **NFR-PERF** | 01→03, 05, 07 | Measured on real traffic, broken down by task category | C2, C3, C4 |
| **NFR-PERF** | 04 | Measure `SystemOne` decision latency via FR-TEL-06 | C8 |
| **NFR-PERF** | 06 | Measure Action CI execution time for sample project in CI | — *(internal metric)* |
| **NFR-RES** | 01 | 24-hour stress test on reference board | A6 |
| **NFR-RES** | 02, 03 | Measure memory and firmware size in CI; thresholds decided in Q-3 | A6 |
| **NFR-RES** | 04 | Degraded scenario suite: network loss, timeout, invalid model data | A4 |
| **NFR-REL** | 01 | 1,000-device canary OTA campaign | C1 |
| **NFR-REL** | 02 | Degraded scenario suite — shared mechanism with NFR-RES-04 | A4 |
| **NFR-REL** | 03 | Nightly test logs on real hardware | A2 |
| **NFR-REL** | 04 | Re-run regression trace suite after every minor version upgrade | A7 |
| **NFR-REL** | 05, 06 | G1 scenario network loss, LLM loss, dead worker; 2 weeks continuous run on G2 or G3 | A16, B7 |
| **NFR-SEC** | 01 | Code audit and penetration testing searching for shortcuts to actuators | A3 |
| **NFR-SEC** | 02, 03 | Audit Secure Boot, flash encryption, TPM configuration, and physical microphone kill switch on reference board | **criteria needed** *(no measurable milestone A/C criteria yet)* |
| **NFR-SEC** | 06 | Flashing unsigned or improperly signed firmware → rejected | Criteria for FR-OTA-03 · **milestone criteria needed** |
| **NFR-SEC** | 04, 05 | Audit TLS 1.3, mTLS, certificate pinning, and per-device individual certificates (tied to FR-FLT-01, v1.1) | **criteria needed** |
| **NFR-SEC** | 08 | Audit TLS 1.3 channel to provider; verify provider recorded in trace | **criteria needed** *(provider resides in `system_two_call` event data; `trace.v1.json` lacks dedicated provider field)* |
| **NFR-SEC** | 07 | Sandbox testing with third-party code | — *(v1.1, tied to FR-REG-07)* |
| **NFR-SEC** | 09 | Test untrusted caller (`docs/spec/threat_model.md` §2b) and `fixtures/tool_calls/` corpus | A3 |
| **NFR-SEC** | 11, 12, 13 | Undeclared destination scenarios, worker network, chat approval scenario suite; audit storage of keys and bot tokens | A18, A20 |
| **NFR-SEC** | 14 | Install mismatched digest package, package declaring `safe_state` in wrong place | A14, A21 |
| **NFR-SEC** | 15 | Audit relay design: no decryption, encrypted backup | **criteria needed** *(P1 relay, no milestone criteria yet)* |
| **NFR-PRIV** | 01, 03, 04 | Audit content of trace files generated in default mode | A7 |
| **NFR-PRIV** | 02 | Audit on-device vs cloud processing boundary per P-4 | — *(architectural review)* |
| **NFR-PRIV** | 05 | Audit data sharing destinations disabled by default | — *(P2, post-8-week gate)* |
| **NFR-OBS** | 01→03 | Validate trace files via `neuroedge trace validate` | A7 |
| **NFR-OBS** | 04 | Measure 30-day trace size on G1; mid-segment power loss scenario | A22 |
| **NFR-COST** | 01, 02 | 30-day scenario on G1, count costs and messages by category | A19 |
| **NFR-COMP** | 01→04 | Audit boundary between core and commercial services (`docs/architecture/vi/15-target-architecture.md` §3.4) | A9 |
| **NFR-COMP** | 05, 06 | Platform matrix executed in CI | A2 |

### A.4 Remaining Functional Requirements Traceability

A.1 traces against **product goals**, A.2 against **invariant principles**. Several functional requirement groups do not fall along those two axes but must still maintain verification pathways; this table covers the remainder.

| Nhóm | Yêu cầu | Vai trò | Tiêu chí nghiệm thu |
|:---|:---|:---|:---:|
| **FR-HAL** | 01→05 | Capability contracts and build-time reconciliation | A2, A3 |
| **FR-PER** | 01→06 | Voice processing pipeline and conversation state machine | A6, C2 |
| **FR-CI** | 03→06 | Assertion libraries, golden baselines, CI execution, nightly | A2, A7 |
| **FR-CI-LVL** | L1→L3 | Three assurance levels: L1 exact replay, L2 schema + `confidence` match, L3 assert gate verdicts and GPIO only | A2 *(L1, L2)* · lint FR-DX-07 *(L3)* |
| **FR-TRC** | 09, 10 | Trace path conventions; SchemaStore registration | A7 · A9 *(10)* |
| **FR-GOV** | 01→04 | Open schema governance and RFC process | A9 |
| **FR-CLI** | 02→08 | Command-line interface surface | A1, A8 |
| **FR-CLI** | 09→12 | `gate lint`, `gate resolve`, `board`, `mcp` | A5 *(09, 10)* · A2 *(11)* · A3 *(12)* |
| **FR-DX** | 03→07 | Project templates, sample examples, error messages | A1, A8 |
| **FR-EXT** | 01→09 | Standalone core usage, plug points, conformance, proxy, remote actuators, distribution | A13, A3 |
| **FR-TGT** | 07 | Degraded scenario simulation in `sim`; multi-day mission scenarios with physical models (Q-72) | A4, A16, A19 |
| **FR-MDL** | 05, 06 | Declarative routing and S1/S2 ratio recording | C4 |
| **FR-FLT** | 01, 03, 04, 06 | Provisioning, monitoring, remote configuration, virtual devices | C1, roadmap TR-7 |
| **FR-REG** | 02, 03, 05, 06 | Manifests, capability declarations, identifiers, measurement | C5, roadmap TR-4, TR-5 |
| **FR-REG** | 07 | Permissions and sandboxing for third-party code | — *(v1.1, verified via NFR-SEC-07)* |
| **FR-TEL** | 01→06 | Telemetry and measurement | B4, B5, §12.2 of this document |
| **FR-TEL** | 07, 08 | 8-week demand gate milestones; kit affiliate reporting | B6, B7, C6 |
| **FR-MSN** | 01→14 | Mission contracts: clauses, layered compilation, conflicts, approval summaries | A15, A17, A21 |
| **FR-AGT** | 01→09 | Operator agent: runtime, LLM worker, scheduling, detectors, cost ceilings, error branches | A16, A19 |
| **FR-CH** | 01→05 | Chat channels, pairing, approval records | A20 |
| **FR-EGR** | 01→05 | Exfiltration-resistant data egress, relay | A18 · relay: **criteria needed** |
| **FR-BP** | 01→07 | NeuroEdge Blueprint, pack/install, evidence, static index, kit | A14, A21, A22 |
| **FR-BP** | 08→10 | Licenses, consented data, monetized Hub | — *(post-8-week gate)* |
| **FR-TRC** | 11→13 | Segmented traces, recording and retention, new events | A22 |
| **FR-CLI** | 13→15 | `blueprint`, `chat`, `mission`, `agent` | A14, A15 |

**Traceability coverage:** across A.1 through A.4, every FR and NFR requirement in this document has at least one verification pathway, **except rows marked "criteria needed"** (NFR-SEC-02→06, 08, 15; FR-EGR-05) — known traceability debt that must be completed prior to closing v1.0. The three appendices following A.1 exist because of three distinct traceability axes — goals, principles, and system attributes — and a requirement may appear along multiple axes.

---

## Phụ lục B — Danh mục mã lỗi chuẩn

Mọi mã lỗi **BẮT BUỘC** nêu đủ ba thành phần: sai ở đâu, vì sao, và cách xử lý (FR-DX-04).

**Nơi duy nhất của *cấu trúc*** — mã nào tồn tại, tên lớp, quan hệ cha con, trạng thái (`stable` · `reserved`), khoá thêm của `as_dict()` — là danh mục máy đọc được [`schemas/error-codes.v1.json`](../schemas/error-codes.v1.json) (RFC-0015, Q-66); hình dạng một lỗi đã tuần tự hoá là [`schemas/error.v1.json`](../schemas/error.v1.json). Phụ lục này giữ **lời**: thời điểm, nguyên nhân, hành vi hệ thống (FR-DX-04). Test `python/tests/test_error_catalog.py` buộc hai chiều cặp (lớp, mã) của bảng dưới ↔ danh mục, danh mục ↔ `errors.py` và mọi mã `NE…` trong `targets/`. Mọi lớp kế thừa `NeuroEdgeError`; thêm một mã là thêm một hàng ở đây **và** một mục ở danh mục. Dòng ghi *(dự kiến)* chưa có trong mã.

`NE0000` và `NE2000` là mã **chung** (`general: true` trong danh mục): người nhận **không được** rẽ nhánh theo chúng. Lớp con dùng chung mã của lớp cha (`aliases` trong danh mục; hiện chỉ `NE5001`) không có hàng riêng: hàng của lớp cha nêu tên chúng.

| Mã lỗi | Mã | Thời điểm phát sinh | Nguyên nhân | Hành vi hệ thống |
|:---|:---:|:---|:---|:---|
| `NeuroEdgeError` | NE0000 | Bất kỳ | Lỗi không phân loại: lớp gốc của mọi lỗi NeuroEdge, được dựng trực tiếp ở nơi chưa có lớp riêng (CLI, Studio, phiên mô phỏng, trình sinh firmware). Mã **chung**: không rẽ nhánh theo nó | Ném ngoại lệ ba thành phần; không đổi gì ở phần cứng. Cấp mã riêng cho từng chỗ là việc sau, và là thay đổi nới lỏng (RFC-0015 §10 mục 9) |
| `ActionContractViolation` | NE1001 | Chạy | Gọi hành động vật lý không qua `c.do()` / thiếu chữ ký gate hợp lệ | Ném ngoại lệ, chân GPIO không được kích |
| `TokenReplayError` | NE1002 | Chạy | Token phán quyết bị dùng lại (`token_replayed`), quá TTL = p95 × 3 hoặc do tiến trình khác phát hành (`token_expired`); lease của kênh `motion.*` đã dùng một lệnh (`lease_used`) hoặc quá `lease_ms` (`lease_expired`, RFC-0011 §3c) | Ném ngoại lệ (vi phạm hợp đồng, không thử lại), chân GPIO không được kích, ghi `actuator_command_rejected` (TSK-S2-05) |
| `EnvelopeRefusedError` | NE1003 | Chạy | Phong bì an toàn của chân hoặc kênh từ chối lệnh bật (`reason`): `window_budget` (hết ngân sách `max_on_ms_per_window` của cửa sổ), `min_interval_ms` (chưa đủ giãn cách từ lúc lần bật trước kết thúc), `already_on` (chân đang bật hoặc có lệnh chờ bật: không bật lại để kéo dài), `window_unreadable` (bản ghi on-time thiếu, hỏng hoặc không ghi được: coi cả cửa sổ đã dùng hết), `supervisor_unavailable` (`linux`: tiến trình giám sát line không chạy), và `max_continuous_ms` (dành cho PWM, RFC-0010 §3d: lệnh có `duration_ms` vượt trần bị từ chối; `digital.out` thì tự tắt tại trần, không từ chối). Với **cơ cấu chấp hành từ xa** (RFC-0018 §3g), chốt trạng thái từ chối trước phong bì: `actuator_state_unknown` (HAL không biết thiết bị đang tắt: lệnh trước mơ hồ, mất kênh đọc lại, lần đọc cũ hơn 2 s, vừa khởi động), `actuator_quarantined` (thiết bị đã vi phạm mức tự tắt nó khai; chỉ người vận hành gỡ) và `already_on` (lần đọc thấy đang bật mà NeuroEdge không bật). Lớp con của `ActionContractViolation` (RFC-0007 §3d, §3e) | Ném ngoại lệ, chân không được kích, token không bị tiêu, ghi sự kiện `envelope_refused`. Lệnh về phía an toàn (`digital.out` `off`, tự tắt, `hal.close()`, `off` tới cơ cấu từ xa) không bao giờ bị từ chối |
| `ToolCallError` | NE1004 | Chạy | `ToolCall` dựng với `source` không thuộc tập nguồn dispatcher gán (`docs/spec/tool_calling.md` §5): lỗi lập trình, không phải phán quyết. Cũng là `ValueError` (tương thích bản 0.1). NE1003 dành cho `EnvelopeRefusedError` (RFC-0007) | Ném ngoại lệ lúc dựng, không có lời gọi nào chạy; nêu `source` sai và các nguồn hợp lệ (TSK-I6-06) |
| `GateError` | NE2000 | Build hoặc chạy | Lớp gốc của lỗi soạn, thẩm định và phân giải gate. Mã **chung**: không rẽ nhánh theo nó, các lớp con có mã riêng (NE2001 → NE2003) | Từ chối phân giải, nêu gate và lý do |
| `GateNotFoundError` | NE2001 | Build hoặc chạy | URI hoặc đường dẫn gate không phân giải được thành tài liệu gate | Từ chối phân giải, nêu URI/đường dẫn |
| `GateSchemaError` | NE2002 | Build, `gate lint`, `gate resolve` | Gate vi phạm `schemas/gate.v1.json` hoặc tập toán tử Phụ lục B | Từ chối, nêu trường sai |
| `GateInheritanceError` | NE2003 | Build, `gate lint`, `gate resolve` | Chuỗi `extends` vi phạm nguyên tắc B.5: nới lỏng `allow_when`/`budget`/`on_block` (Q-18), `allow_when` dạng chuỗi trong chuỗi kế thừa, vượt 3 cấp, hoặc vòng lặp | Từ chối phân giải, nêu chuỗi kế thừa và dòng `rule` chỉ nguyên tắc B.5 bị vi phạm |
| `BoardCapabilityError` | NE3001 | Nạp bo mạch / Build | Khai báo bo mạch sai, hoặc agent yêu cầu năng lực bo mạch không cung cấp. Lúc nạp `board.toml` (RFC-0007, RFC-0010, RFC-0011, RFC-0012, RFC-0013): chân `digital_out` không thuộc `signal_pins` mà thiếu phong bì; `signal_pins`, `enable_pin` hoặc kênh nêu tên chưa khai; giá trị ngoài lược đồ (địa chỉ I2C ngoài 0x03..0x77, `min` ≥ `max`, `window_s` hoặc `max_continuous_ms` ≤ 0, `tolerance` vượt trần cứng); khoá năng lực gõ sai; profile khai `mirrors`. Lúc build: gate của một action `motion:<kênh>` có `p95_latency_ms` > `lease_ms / 2` của kênh (RFC-0011 §3c, §9 mục 2; `neuroedge gate lint` không đổi); `neuroedge build` không `--board` mà bo mặc định của target không thoả `[requires]` (RFC-0013 §3e). Cơ cấu chấp hành từ xa (RFC-0018 §3k): `safe_off` khai vượt `safe_off_level` của plugin; cơ cấu không hoàn tác mà plugin dưới L2 hoặc không đọc lại được; `max_continuous_ms` không lớn hơn `tolerance_ms` của plugin; `[actuators]` với target `esp32s3`; `pwm` hay `motion` nêu tên một cơ cấu từ xa | Dừng build, không sinh firmware, chỉ rõ dòng mã gọi. Build không `--board`: lỗi 3 phần nêu năng lực thiếu, bo mặc định cung cấp gì và liệt kê các bo tham chiếu của target thoả `[requires]` (hoặc nói rõ không bo nào thoả); không bao giờ tự chọn bo khác |
| `AgentManifestError` | NE3002 | Build | `agent.toml` sai cấu trúc, thiếu `[requires]`, hoặc một `@action` cần năng lực / gate mà manifest không khai. `guard.toml` sai (RFC-0016). `[plugins]` và bộ nạp plugin (RFC-0016 §3d): bản phân phối đã bật chưa cài, không import được, `sdk_requires` không tương thích, ghim phiên bản lệch, hai bản phân phối cùng tên entry point, factory sai hình dạng hay từ chối `config`. `[actuators.<tên>]` (RFC-0018 §3b, §3f): thiếu `plugin`/`safe_off`/`envelope`, mức lạ, khoá lạ, bí mật viết thẳng, tên trùng chân của bo hay không có trong `[requires] "digital.out".pins`, plugin không thuộc bản phân phối đã bật, và luật D5 — cơ cấu không hoàn tác khai `safe_off` dưới L2 | Dừng build, nêu `file:line` của hành động (TSK-S2-02) |
| `BuildFailed` | NE3003 | Build | `neuroedge build` gặp ≥ 1 vấn đề | Gom **mọi** vấn đề, in từng cái đủ 3 thành phần, thoát mã 1, không ghi artifact nào |
| `TraceValidationError` | NE4001 | `neuroedge trace validate` · `record --target esp32s3 --port` | Tệp vết ghi không hợp lệ theo `schemas/trace.v1.json`; hoặc dòng `NE1` từ UART hỏng, thiếu khung phiên, đếm lệch (`docs/spec/simulation_coverage.md` §4) | Báo lỗi kèm đường dẫn trường sai, hoặc `nguồn:dòng`; không ghi tệp nào |
| *(không phải exception — phán quyết)* | — | Chạy | Gate không thẩm định được trong ngân sách hoặc bộ thẩm định không tới được, và `fail: closed` | `BLOCK` với `reason: budget_exceeded` / `gate_unreachable`, `action: deny`, ghi vào vết ghi (TSK-S2-03). Fail-closed là phán quyết để phát lại được, không phải lỗi |
| `SafetyRegressionError` | NE4002 | `neuroedge replay`, `verify`, `assert_matches_golden` | Phán quyết gate hoặc lệnh chân của phiên replay lệch golden — kể cả lệch giữa các target (thay `TargetEquivalenceError` dự kiến); suy luận mô hình thị giác trên một target lệch golden host quá sai số `vision_in.tolerance` của bo mạch (RFC-0012 §3f) | Mã 1, chỉ rõ sự kiện và trường lệch đầu tiên; gắn nhãn *SAFETY REGRESSION* khi BLOCK thành ALLOW hoặc có lệnh chân mới (TSK-S3-04). Cũng là `AssertionError` để pytest báo test trượt |
| `ReplayError` | NE4003 | `neuroedge replay` · `verify --targets esp32s3` | Vết ghi không replay được với agent này: không biết action nào sau một gate, hoặc target không có HAL; hoặc thiết bị không có phiên replay vết ghi đó, hay replay vết ghi / gate cũ hơn checkout (firmware cũ) | Mã 1, lỗi 3 thành phần (TSK-S3-02, TSK-S4-09) |
| `VerificationError` | NE4004 | `neuroedge verify` | Một loại artifact quét được 0 — không gate nào phân giải, không vết ghi chuẩn mực nào thẩm định, không lượt replay nào — thư mục không tồn tại, hoặc một bo tham chiếu của target được yêu cầu không có lượt replay hay không có vết ghi chuẩn mực nào áp được (RFC-0013 §3f) | Mã 1, lỗi 3 thành phần nêu thư mục và `NEUROEDGE_ROOT`; quét 0 artifact không bao giờ là đạt, kể cả với một bo tham chiếu (FR-CLI-03, TSK-S3-19, RFC-0013 §3f) |
| `PerceptionUnavailableError` | NE5001 | Nạp / build / chạy (đọc HAL) | Thành phần nhận thức không dựng được: tệp ngữ pháp lệnh thiếu hoặc sai, fallback không xác định. Lúc chạy (RFC-0007 §3e): một lần đọc HAL hỏng — `digital.in`, bus I2C NACK hay timeout, `analog.in`, cảm biến mất — hoặc mốc đọc sau thời điểm lượng giá | Báo lỗi 3 thành phần. Lúc chạy, nhà cung cấp chính và fallback đều không trả lời được **không** ném lỗi: là phán quyết `Unavailable` → `gate_unreachable` / `criterion_unavailable`, áp `fail` của gate (TSK-S2-08). Lần đọc HAL hỏng thì ném lỗi này ⇒ tiêu chí chưa quyết ⇒ BLOCK `criterion_unavailable`, không bao giờ ALLOW. Lớp con dùng chung mã `NE5001`, không có hàng riêng: `CameraUnavailable` (camera không giao được khung hình), `MalformedResponse` (nhà cung cấp trả lời không phải một chat completion), `ProviderUnavailable` (nhà cung cấp không trả lời được), `SpeechUnavailable` (nhà cung cấp STT/TTS không trả lời được), `VisionUnavailable` (mô hình thị giác không trả lời được) |

## Phụ lục C — Quy ước định danh và phiên bản

| Đối tượng | Quy ước | Ví dụ |
|:---|:---|:---|
| Agent | `<tên>@<semver>` | `villa-concierge@0.3.1` |
| Gate | `<tên>@<semver>.yaml` | `unlock_door@1.2.0.yaml` |
| Gate trên Registry | `neuroedge://gates/<nhóm>/<tên>@<semver>` | `neuroedge://gates/hospitality/dual-auth-lock@1.0.0` |
| Bo mạch | `<tên>-<phiên-bản>` | `villa-panel-v2` |
| Phiên tương tác | `sess_<8 ký tự hex>` | `sess_8f9a2b1c` |
| Vết ghi thường | `traces/<mô-tả>.json` | `traces/happy-path.json` |
| Vết ghi sự cố | `traces/incidents/<session_id>.json` | `traces/incidents/sess_8f9a2b1c.json` |
| Golden Reference | `traces/golden/<kịch-bản>.json` | `traces/golden/unlock-denied.json` |
| Lược đồ công khai | `https://schema.neuroedge.dev/<loại>/v<n>.json` | `https://schema.neuroedge.dev/trace/v1.json` |
| NeuroEdge Blueprint trên index *(dự kiến, Q-72 — chốt ở RFC `blueprint.v1`)* | `neuroedge://blueprints/<tác-giả>/<tên>@<semver>` | `neuroedge://blueprints/maker/bao-ve-be-ca-nhiet-doi@1.2.0` |
| Hợp đồng nhiệm vụ *(dự kiến, Q-72 — chốt ở RFC `mission.v1`)* | `<tên>@<semver>.mission.yaml` | `trong-be-ca@0.1.0.mission.yaml` |
| Nguồn kênh chat *(dự kiến, Q-72 — chốt ở RFC nguồn `chat:<id>`)* | `chat:<id>` — `<id>` là tài khoản đã ghép đôi, do runtime gán | `chat:<id>` của tài khoản Telegram đã ghép |
| Đoạn vết ghi của runtime 24/7 *(dự kiến, Q-72 — chốt ở RFC `trace.v1`)* | `traces/runtime/<session_id>/<ngày>.json` | `traces/runtime/sess_8f9a2b1c/2026-10-11.json` |

## Phụ lục D — Cấu trúc Monorepo và Giao thức Truyền dẫn

### D.1 Bố cục Monorepo tiêu chuẩn

Bố cục kho và thủ tục sửa từng thư mục: **[`CONTRIBUTING.md` §6](../CONTRIBUTING.md#6-cấu-trúc-kho)** — nơi duy nhất.

### D.2 Giao thức Truyền dẫn & Định dạng Vết ghi (Wire Protocol)

1. **Giao thức mạng Wi-Fi / LAN:** `WebSocket` bảo mật truyền luồng âm thanh Opus (Binary Frame) và sự kiện vết ghi JSON (Text Frame).
2. **Giao thức cổng nối tiếp UART** (921600 baud): vết ghi là JSON Lines, mỗi dòng mang tiền tố `NE1 ` để tách khỏi log firmware (TSK-S4-09); khung phiên, giới hạn dòng và cách host dựng vết ghi: `docs/spec/simulation_coverage.md` §4. Khung nhị phân, nếu cần, đóng gói `SLIP`.
3. **Định dạng âm thanh nén:** Opus Voice Mode (16 kbps, 16 kHz mono, kích thước khung 20 ms = 320 mẫu). Cùng một định dạng cho mọi target; `sim` phát lại tệp WAV qua đúng đường mã hóa này để giữ tương đương với phần cứng thật.

---

*Hết tài liệu*
