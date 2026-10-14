<!-- GENERATED from neuroedge-roadmap.md §0 — do not edit by hand.
     Regenerate: python3 scripts/gen_user_status.py (check: --check) -->

# Project status

> Generated from [`neuroedge-roadmap.md`](../../roadmap/neuroedge-roadmap.md) §0 —
> the single source of truth for progress. Source last updated: **2026-10-14**.

## Executive status

| Indicator | Current status |
|:---|:---|
| Current phase | 🟡 **Phase MVP (§0.5)**, sequence per Q-72 — I2d then I2e (fish tank NeuroEdge Blueprint traversing all three loops on simulation) before the 8-week demand gate; remainder of I1, I2a, I2c interleaved; partner trial (Q-70) in parallel; voice (I4, I5) and Studio paused, not cut |
| Open increment | 🟡 **I2d — Missions and operator agents** (Q-72) — tasks begin once Step 0 (documentation sync per Q-72) is done |
| Next milestone | **8-week demand gate (Q-72, B6–B8)** — ≥ 3 external users independently install Blueprint and get it running, ≥ 1 user runs continuously for 2 weeks on G2 or G3, ≥ 1 maker wants to sell (PRD §11.2) |
| Core CI status | ✅ **PASS 5062/5062 · SKIP 0** |
| Non-technical blockers | 🟡 **2 blocking items** |
| Last updated | **2026-10-14** |

## Increments

| Milestone | Increment | Forecast | Progress | Status | Release |
|:---:|:---|:---|:---:|:---|:---|
| **Internal 0.x** | **I0 — Contract core on `sim`** | ✅ 2026-09-24 | **42 / 42** | ✅ Done | historical |
|  | **I1 — Internal preview on `sim`** | 2026-11-15 | **4 / 6** | 🟡 In progress — TSK-I1-02 deferred (internal development) | tag `v0.1.0` (internal) |
|  | **I2 — `linux` at parity with `sim`** | 2026-11-29 | **3 / 4** | 🟡 Interactive session, sensors, display complete on gpio-sim + i2c-stub; nightly RPi 5 remaining | tag `v0.2.0` (internal) |
|  | **I2a — Extended primitives on `sim` and `linux`** | 2026-12-06 | **22 / 27** | 🟡 Six RFCs approved; numeric criteria and `NETR` v2; `board.v1` declares all extended primitives, `sim-rpi5`; safety envelope, `digital.in`, read-only I2C, `analog.in`, vision (virtual camera, V4L2, models, traces, sample gates) complete on `sim` and on kernel (`linux-hal` job, CI run 37153005998: gpio-sim, `i2c-stub`, `vivid`; `verify --targets sim,linux` replays sensor and vision corpus); PWM and `motion.*` complete on `sim`, `enable` line green on gpio-sim. **Remaining:** `verify` has not replayed `fan-pwm` and `rover` agents (I2a criterion 3); camera dropped mid-session on kernel (criterion 5); physical PWM channels and real actuators; vision inference golden; `esp32s3` cell of coverage matrix (TSK-I3a-01) | tag `v0.2.1` (internal) |
|  | **I2b — Starter kits and rapid assembly** | 2026-12-20 | **4 / 4** | 🟡 Five kits, gate library, `neuroedge add` complete (criteria 1, 3, 4); remaining TTFV measurement with humans (criterion 2) and building kits on physical hardware | tag `v0.2.2` (internal) |
|  | **I2c — Open platform** | 2026-12-27 | **11 / 20** | 🟡 Q-67, design, corpus licensing complete; RFC-0002, RFC-0016 → RFC-0018 signed (Q-68); `neuroedge.guard` (TSK-I2c-07), `proxy mcp` + `guard init --mcp` (TSK-I2c-14), `proxy http` (TSK-I2c-15), remote actuators + Home Assistant plugin (TSK-I2c-16), partner trial documentation package (TSK-I2c-19) and half (a) of RFC-0017 complete; partner trial proceeds from here (Q-70); target list opening and two paused tasks dropped per Q-77 (§6) | tag `v0.2.3` (internal) · wheel for one partner team — private trial, not waiting for boards (Q-70) |
|  | **I2d — Missions and operator agents** | 2026-11-11 | **1 / 41** | 🟡 Open — Step 0 (documentation sync per Q-72) in progress, tasks begin once complete; five planned RFCs and RFC for `TODOS.md` #58 awaiting tech lead signature | tag `v0.2.4` (internal) |
|  | **I2e — Minimal NeuroEdge Blueprint** | 2026-11-25 | **0 / 15** | ⏳ Not started | tag `v0.2.5` (internal) · direct hand-off wheel for external testers, no index (like Q-70); PyPI remains at I6 (Q-39) |
|  | **I2f — NeuroEdge Cloud and ESP32 home box** | after 8-week gate (branch) | **1 / 17** | ⏸ Waiting for demand gate outcome 2026-12-06 (Q-74); exception Q-79: TSK-I2f-10 complete, I2f-11 → I2f-13 awaiting boards | optional service + ESP32 box firmware |
|  | **I3 — Gate on real Box-3** | after I2e | **6 / 16** | 🟡 Boardless portion complete (including firmware generated for agent on QEMU, LVGL interface with golden images); awaiting boards | tag `v0.3.0` + firmware (internal) |
|  | **I3a — Extended primitives on `esp32s3`** | after I2e | **0 / 11** | ⏳ Not started | tag `v0.3.1` + firmware (internal) |
| **Public** | **I6 — Public launch** | after I2e | **7 / 11** | 🟡 Secret scanning, SBOM, public Python API, network MCP with authentication, integrator contracts in `schemas/` (RFC-0015) complete; RFC-0014 approved (Q-65); awaiting I3a | PyPI `v0.6.0` — first external release |
| **v1.0 = MVP** | **I7 — v1.0** | after I2e | **4 / 12** | 🟡 Action pinning, attestation complete; signed A/B OTA + rollback complete on QEMU; awaiting I6 | `v1.0.0` |
| **Beta** | **I8 — Developer Beta** | after I2e | **0 / 1** | ⏳ Not started | `1.0.x` (patches only) |

Capabilities, dependencies and assumptions behind the forecast dates: [`neuroedge-roadmap.md`](../../roadmap/neuroedge-roadmap.md) §0.
