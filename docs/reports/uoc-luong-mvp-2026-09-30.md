> **Superseded by Q-72/Q-77 for I3–I8 forecasts; historical evidence for TSK-I2a-01 only.**

# Re-estimating MVP Scope — 2026-09-30

Evidence for forecasted dates of I2a → I8 in [`roadmap/neuroedge-roadmap.md`](../../roadmap/neuroedge-roadmap.md) §0.2
(TSK-I2a-01, rule R5). Scope is the MVP of Q-52: I1 → I7, including I2a, I2b, I3a, I4a, I5a. Decisions:
[`roadmap/neuroedge-prd.md`](../../roadmap/neuroedge-prd.md) §15 (Q-52 → Q-57).

## 1. Velocity data

Counted on the roadmap task table as of 2026-09-30 (status cell ✅ with date):

| Completion date | Tasks |
|:---|---:|
| 2026-09-23 | 22 |
| 2026-09-24 | 11 |
| 2026-09-25 | 8 |
| 2026-09-26 | 13 |
| 2026-09-27 | 1 |
| undated | 12 |
| **Total** | **67** |

67 tasks completed between 2026-09-21 → 2026-09-29, or **~7 tasks per day** across the entire team. All those tasks were
host work (Python, C on host and QEMU, documentation), clearly specified, without waiting for hardware or third parties.

**Planning factor: divide by 4**, leaving **~1.75 tasks per day** for MVP host work. Reasons:

- new tasks are larger (new HAL primitives, vision pipeline, NeuroBrain) and touch safety layers;
- all code for new primitives awaits accepted RFCs (§2.3 roadmap), introducing a review queue;
- team has not done this type of work before, making I0 velocity an upper bound, not an expectation.

Hardware-dependent tasks and tasks requiring external parties are **not** calculated using this velocity: they are calculated by hardware arrival dates
and real measurement durations.

## 2. Breakdown of 106 open MVP tasks

Excluding TSK-I2a-01 (this task).

| Increment | Host | Requires hardware | Requires external party or third party | Total |
|:---|---:|---:|---:|---:|
| I1 | — | — | 2 (TSK-I1-02 TTFV measurement · TSK-I1-04 live microphone on presenter machine) | 2 |
| I2 | — | 1 (TSK-I2-01, Pi 5) | — | 1 |
| I2a | 23 (5 RFC/specs + 18 implementation) | 2 (TSK-N3-03 if spike fails · TSK-V1b-05 NPU) | — | 25 |
| I2b | 2 | 2 (TSK-I2b-01, I2b-02: BOM check and wiring diagrams on Pi) | — | 4 |
| I3 | — | 8 | — | 8 |
| I3a | — | 7 | — | 7 |
| I4 | — | 2 (TSK-S5-08 Pi + HAT · TSK-S3-13 real-time section) | 2 (TSK-I4-01 licensed wake-word model · TSK-I4-04 live microphone) | 4 |
| I4a | 33 | — | — | 33 |
| I5 | — | 7 | — | 7 |
| I5a | — | 2 | — | 2 |
| I6 | 1 (TSK-S3-09) | 1 (TSK-I6-03 video across three targets) | 3 (PyPI, domain, community channels) + license terms (`TODOS.md` #44) | 5 |
| I7 | 4 (TSK-S6-07, S6-08, W0-01, I7-01) | 3 (TSK-S6-03, S6-05, S6-06 24-hour run) | 1 (TSK-I7-02: A1 10 people, A9 third party) + A12 (5 people) | 8 |
| **Total** | **63** | **35** | **8** | **106** |

## 3. Assumptions

| # | Assumption | If incorrect |
|:---:|:---|:---|
| G1 | Box-3, RPi 5 and ESP32-S3 camera board arrive **before 2026-11-01**; camera board selected in TSK-I3a-01 **before 2026-10-09** in time to order — *selected M5Stack CoreS3 on 2026-10-01 (Q-61)* | All increments from I3 slip accordingly, day-for-day |
| G2 | Six RFCs (0007, 0009 → 0013) approved by tech lead **before 2026-10-09**; open questions decided (Q-57) — *approved 2026-10-01 (PR #75 → #80)* | I2a has ~3 weeks buffer before I2 dependency (2026-11-29) bounds date; past 2026-10-30 I2a slips |
| G3 | *Amended 2026-10-01 (Q-60, replacing fully-staffed assumption of Q-52):* one person + AI agent. Host lane runs at §1 velocity, measured on this exact setup; hardware-dependent or external tasks done by one person, AI agent prepares | Chip lane serializes on one person: compare at §5 when boards arrive, slip dates per R5 (roadmap §1.3) |
| G4 | Memory spike TSK-S1-10 passes Q-3 thresholds with voice + four packs | Open `Q-N` to re-plan I5, I3a; slip dates, do not cut (Q-44, Q-52) |
| G5 | `vision.in` runs on ESP32-S3 camera board within memory budget (TSK-I3a-01) | Apply option (b) or (c) of RFC-0013 §9; re-plan I3a |
| G6 | Commercial license terms (`TODOS.md` #44) ready before I6 | I6 and I7 slip |

## 4. Forecasted dates

Calculated by lanes: host lane uses §1 velocity; chip lane begins when boards arrive (G1); date of an increment cannot
precede dates of all increments it depends on (rule R3).

| Increment | Forecast | Calculation |
|:---|:---:|:---|
| I1, I2, I3, I4, I5 | unchanged | Scope unchanged. Calculated at planning under fully-staffed assumption (I3a chip lane does not take people from I3, I5); as of Q-60 this is first comparison point when boards arrive (§5) |
| **I2a** | **2026-12-06** | 18 implementation tasks post-RFC (G2) ≈ 10 working days at 1.75 tasks/day; NPU and ADC on hardware after 2026-11-01; bounded by I2 (2026-11-29) + one week integration |
| **I2b** | **2026-12-20** | Two weeks after I2a: five test kits on Pi, gate library, `neuroedge add` |
| **I3a** | **2027-01-10** | Four weeks after I3 (2026-12-13): C HAL for four packs, vision on camera board, power-loss tests during `motion.*` commands |
| **I4a** | **2027-01-03** | 33 host tasks, mostly doable before I2a; bounded by I4 (2026-12-13) and TSK-I4a-01 (requires all four packs of I2a) + three weeks covering four packs and drafting reviews |
| **I5a** | **2027-01-24** | Two weeks after I3a: lab actions, on-chip gates and envelopes |
| **I6** | **2027-01-31** | One week after I5a: PyPI, public schemas, video across three targets, license (G6) |
| **I7** | **2027-02-21** | Three weeks after I6: A1 (10 users installing from PyPI), A12 (5 users building kits), A9 (third party), 24-hour run, Secure Boot |
| **I8** | **2027-03-21** | Four weeks Beta after I7 (§5.4 roadmap) |

**Critical path:** boards arrive → TSK-S1-10 → I3 → I3a → I5a → I6 → I7. Compared to pre-scope expansion forecast
(v1.0 2027-01-24), v1.0 slips **four weeks**: host expansion runs in parallel outside the critical path, whereas chip lane
adds I3a and I5a.

## 5. When to re-estimate

- Any assumption G1 → G6 turns out false: re-estimate in the same PR with evidence (R5).
- On 2026-11-01: compare actual October host lane velocity against 1.75 tasks/day.
- When TSK-S1-10 obtains measurements and when TSK-I3a-01 completes camera board selection.
- When boards arrive (Q-60): measure days taken by one person to complete each hardware-dependent task in I3 during the first two weeks, then
  recalculate I3 → I7 for 35 hardware-dependent tasks executed serially.
