# 11 · OEM HAL Port Guide

> Audience: hardware partners bringing NeuroEdge to new boards (U5).
> Port standard: FR-TGT-08 tier 3; increment I13 (after I11). Asset policy:
> proposal §1.7/`§6.4` (authors keep copyright, separate repos, NeuroEdge indexes).

## 1. Port contract (5 + 3 + 1)

```mermaid
flowchart TB
    P5[5 closed primitives<br/>audio.in/out · digital.out<br/>sensor.read · display]
    P3[3 safety duties<br/>refuse-all by default<br/>authorize(token) before any command<br/>logical pin names, never physical numbers]
    P1[1 compliance suite<br/>vectors + 3 golden traces<br/>verify must pass to claim a port]
    P5 --> P3 --> P1
```

- **No** target branching in agent logic (P-2); hardware differences live in
  `board.toml` + HAL, never in agent code.
- Tokens: single-use per pin, TTL=`p95×3`, refuse when full; mirror
  `ne_token.c` for C ports or `TokenLedger` for Python ones.
- On-device gates: walk trees (no JSON/CEL parsing on MCU); `ne_decide`
  semantics ≡ `engine/` (`05`).

## 2. Port checklist (all boxes before announcing)

| # | Work | Done when |
|:---:|---|:---|
| 1 | `board.toml` with full `board.v1` capabilities, shared logical pin names | `board list/show` + `build` green on sample agents |
| 2 | 5 primitives (or declared subset) + refuse-all + authorize | Internal pentest: no actuator bypass |
| 3 | Compliance vectors + 3 golden traces vs golden | `verify` green for the claimed port scope |
| 4 | NOTICE + pinned deps (port duties: `CONTRIBUTING.md` §4) | License review passes (no strong copyleft) |
| 5 | Nightly + board runbook | Nightly results public to port users |

Three control gates (proposal §1.7): compliance suite · permission sandbox ·
build-time capability check. Tier 3 never blocks core-team releases.
