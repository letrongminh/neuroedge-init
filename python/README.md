# NeuroEdge Python SDK

Typed Action Contract Platform for Physical AI — reference implementation of the
NeuroEdge core: the Hardware Abstraction Layer (HAL), the Action Contract Engine,
the gate resolver, and the Action CI test harness.

The full product narrative lives in the repository root:

- [`neuroedge-proposal.md`](../neuroedge-proposal.md) — architecture and appendices
- [`neuroedge-prd.md`](../neuroedge-prd.md) — functional requirements (FR-*/NFR-*)
- [`neuroedge-roadmap.md`](../neuroedge-roadmap.md) — sprint plan and live status

## Install

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
```

Reproducible installs use the pinned set required by §3.9 obligation 5:

```bash
.venv/bin/python -m pip install -r requirements-lock.txt
```

## Layout

| Path | Role |
|:---|:---|
| `neuroedge/hal/` | L1 — the five immutable primitives and board capability model |
| `neuroedge/engine/` | L3 — Action Contract Engine, gate resolver, canonicalization |
| `neuroedge/perception/` | L2 — voice pipeline and conversation state machine |
| `neuroedge/testing/` | Action CI — `replay()`, `scenario()`, assertions |
| `neuroedge/cli/` | `neuroedge` command line interface |
| `tests/` | Schema, resolver, board and CLI test suites |

## Run the test suite

```bash
.venv/bin/python -m pytest -q
```
