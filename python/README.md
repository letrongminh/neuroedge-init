# NeuroEdge Python SDK — for contributors

Typed Action Contract Platform for Physical AI — reference implementation of the
NeuroEdge core: the Hardware Abstraction Layer (HAL), the Action Contract Engine,
the gate resolver, and the Action CI test harness.

This page is for working on NeuroEdge from a checkout. To *use* it, install from
PyPI as the root [`README.md`](../README.md) says — that file is also the package's
PyPI page (`hatch_build.py` reads it in). Releasing: [`docs/release.md`](../docs/release.md).

Everything else has one home in the repository root, and this page only points there:

| You need | Read |
|:---|:---|
| Set up, run the tests, every command and its expected output | [`CHANGELOG.md` §2](../CHANGELOG.md#2-cách-vận-hành) |
| What lives where (this package included) | [`CONTRIBUTING.md` §6](../CONTRIBUTING.md#6-cấu-trúc-kho) |
| How to contribute, and what needs an RFC | [`CONTRIBUTING.md`](../CONTRIBUTING.md) |
| Architecture, requirements, plan | [`neuroedge-proposal.md`](../neuroedge-proposal.md) · [`neuroedge-prd.md`](../neuroedge-prd.md) · [`neuroedge-roadmap.md`](../neuroedge-roadmap.md) |

Quick start from a checkout:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest -q          # expect: 0 failed, 0 skipped
```
