<!-- GENERATED from neuroedge-roadmap.md §0 — do not edit by hand.
     Regenerate: python3 scripts/gen_user_status.py (check: --check) -->

# Project status

> Generated from [`neuroedge-roadmap.md`](../../roadmap/neuroedge-roadmap.md) §0 —
> the single source of truth for progress. Source last updated: **2026-10-20**.

## Executive status

| Indicator | Current status |
|:---|:---|
| Current phase | 🟡 **Phase MVP (§0.5)**, lean path of Q-92 — I2d (with its mission core) and I2e lead to the public launch (I6), with `esp32s3` verified on esp-emulator in I3, I3a; no demand gate; remainder of I1, I2a, I2c and Profile B in parallel; partner trial (Q-70) in parallel; voice (I4, I5) removed (Q-77, §6) |
| Open increment | 🟡 **I2d — Missions and operator agents** (Q-72) |
| Next milestone | **Public launch (I6, PyPI 0.6, free for non-commercial use)** — after I2d, I2e and I3a on esp-emulator (Q-92) |
| Core CI status | ✅ **PASS 5083/5083 · SKIP 0** |
| Non-technical blockers | 🟡 **1 blocking item, for v1.0 only** |
| Last updated | **2026-10-20** |

## Increments

| Milestone | Increment | Forecast | Progress | Status | Release |
|:---:|:---|:---|:---:|:---|:---|
| **Internal 0.x** | **I0 — Contract core on `sim`** | ✅ 2026-09-24 | **42 / 42** | ✅ Done | historical |
|  | **I1 — Internal preview on `sim`** | 2026-11-15 | **4 / 6** | 🟡 In progress — TSK-I1-02 deferred (internal development) | tag `v0.1.0` (internal) |
|  | **I2 — `linux` at parity with `sim`** | 2026-11-29 | **3 / 4** | 🟡 Interactive session, sensors, display complete on gpio-sim + i2c-stub; nightly RPi 5 remaining | tag `v0.2.0` (internal) |
|  | **I2a — Extended primitives on `sim` and `linux`** | 2026-12-06 | **22 / 27** | 🟡 Six RFCs approved; numeric criteria and `NETR` v2; `board.v1` declares all extended primitives, `sim-rpi5`; safety envelope, `digital.in`, read-only I2C, `analog.in`, vision (virtual camera, V4L2, models, traces, sample gates) complete on `sim` and on kernel (`linux-hal` job, CI run 37153005998: gpio-sim, `i2c-stub`, `vivid`; `verify --targets sim,linux` replays sensor and vision corpus); PWM and `motion.*` complete on `sim`, `enable` line green on gpio-sim. **Remaining:** `verify` has not replayed `fan-pwm` and `rover` agents (I2a criterion 3); camera dropped mid-session on kernel (criterion 5); physical PWM channels and real actuators; vision inference golden; `esp32s3` cell of coverage matrix (TSK-I3a-01) | tag `v0.2.1` (internal) |
|  | **I2b — Starter kits and rapid assembly** | 2026-12-20 | **4 / 4** | 🟡 Five kits, gate library, `neuroedge add` complete (criteria 1, 3, 4); remaining TTFV measurement with humans (criterion 2) and building kits on physical hardware | tag `v0.2.2` (internal) |
|  | **I2c — Open platform** | 2026-12-27 | **11 / 20** | 🟡 Q-67, design, corpus licensing complete; RFC-0002, RFC-0016 → RFC-0018 signed (Q-68); `neuroedge.guard` (TSK-I2c-07), `proxy mcp` + `guard init --mcp` (TSK-I2c-14), `proxy http` (TSK-I2c-15), remote actuators + Home Assistant plugin (TSK-I2c-16), partner trial documentation package (TSK-I2c-19) and half (a) of RFC-0017 complete; partner trial proceeds from here (Q-70); target list opening and two paused tasks dropped per Q-77 (§6) | tag `v0.2.3` (internal) · wheel for one partner team — private trial, not waiting for boards (Q-70) |
|  | **I2d — Missions and operator agents** | 2026-11-11 | **9 / 37** | 🟡 Open — the Q-83 brain and Q-84 parts tasks moved first: TSK-I2d-11 (RFC-0019 approved, PR #133, Q-89), I2d-24, I2d-26 → I2d-30, I2d-32, I2d-33 done (fish tank demos on simulation and emulation: TSK-I2d-28), I2d-31 deferred, I2d-22, I2d-25 in progress; TSK-I2d-12 unblocked; the mission core (TSK-I2d-01 → I2d-21) has not started; five planned RFCs and the RFC for `TODOS.md` #58 await the tech lead's signature, and reflex-tier terms wait for one more, the `NETR` RFC (§10.2); criteria 2 → 7 are a prerequisite of the public launch, not of I2e (Q-90, Q-92) | tag `v0.2.4` (internal) |
|  | **I2e — Minimal NeuroEdge Blueprint** | 2026-11-25 | **0 / 9** | ⏳ Not started; affiliate page, Home Assistant add-on, Pi SD image and Pi + ESP32 scaffold cut (Q-92 (2)) | tag `v0.2.5` (internal) · direct hand-off wheel for external testers, no index (like Q-70); PyPI at I6 (Q-39) |
|  | **I2f — NeuroEdge Cloud and ESP32 home box** | after I6 (Q-74) | **3 / 19** | ⏸ Cloud waits for launch data showing people stuck installing the box (Q-74, Q-92 (8)); exceptions Q-79, Q-83 continue in parallel (Q-92 (3)): TSK-I2f-10, I2f-14, I2f-16 complete (I2f-14, I2f-16 on QEMU); I2f-12, I2f-15 host and QEMU parts done; I2f-11, I2f-13 and the board parts await a DevKitC; I2f-17 is a decision note and needs no board (DP-BP-01); I2f-18 → I2f-20 add the screen and on-chip voice (Q-93); the web passkey (TSK-I2f-08) moved to I2g | optional service + ESP32 box firmware |
|  | **I2g — Box API and home web** | after I6 | **0 / 6** | ⏸ Opens after the public launch (Q-92 (8)) | box API + home web + four RFCs |
|  | **I2h — Native home app** | after I2g | **0 / 8** | ⏸ Opens after I2g (Q-92 (8)) | native app + NeuroClaw app channel |
|  | **I3 — Gate on `esp32s3`** | after I2e | **7 / 12** | 🟡 Boardless portion complete (firmware generated for agent on QEMU, LVGL interface with golden images); esp-emulator spike done (TSK-I3-02): same gate verdicts as QEMU; CI job next (TSK-I3-04); board tasks moved to I7 (Q-92 (5)) | tag `v0.3.0` + firmware (internal) |
|  | **I3a — Extended primitives on `esp32s3`** | after I2e | **0 / 9** | ⏳ Not started | tag `v0.3.1` + firmware (internal) |
| **Public** | **I6 — Public launch** | after I2d, I2e, I3a | **7 / 11** | 🟡 Secret scanning, SBOM, public Python API, network MCP with authentication, integrator contracts in `schemas/` (RFC-0015) complete; RFC-0014 approved (Q-65); awaiting I2d, I2e, I3a | PyPI `v0.6.0` — first external release |
| **v1.0 = MVP** | **I7 — v1.0** | after I6 | **4 / 20** | 🟡 Action pinning, attestation complete; signed A/B OTA + rollback complete on QEMU; awaiting I6 and boards | `v1.0.0` |
| **Beta** | **I8 — Developer Beta** | after I7 | **0 / 1** | ⏳ Not started | `1.0.x` (patches only) |

Capabilities, dependencies and assumptions behind the forecast dates: [`neuroedge-roadmap.md`](../../roadmap/neuroedge-roadmap.md) §0.
