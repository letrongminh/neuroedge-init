# CLAUDE.md — NeuroEdge

Instructions for coding agents working on this repository.

**Read `CHANGELOG.md` §3 (context handoff) before starting a new session.** Sources
of truth and order of precedence on divergence: §3.1 of that file. Progress: `roadmap/neuroedge-roadmap.md`
§0. Decisions: `roadmap/neuroedge-prd.md` §15 (`Q-N`). Intentionally deferred work: `TODOS.md`. Symbol decoding
(`FR-*`, `Q-N`, `A1`, `CEO-X1`…): `docs/user/thuat-ngu.md`. Repository structure:
`CONTRIBUTING.md` §6.

Two most common mistakes:

- **Certain changes strictly require an RFC** — `schemas/`, gate resolution semantics, the three
  normative traces, gates locked in `digests.lock`, `NETR` layout. Complete, sole
  list: `CONTRIBUTING.md` §3.
- **Schema validation is not sufficient to conclude a gate is safe.** The verification gate is
  `neuroedge gate lint` (resolution) — invariant `CHANGELOG.md` §3.3 #1.

## Testing

```bash
cd python && .venv/bin/python -m pytest -q      # expected: 0 failed, 0 skipped
```

Framework: **pytest**. `testpaths = ["tests"]` in `python/pyproject.toml`;
`python/tests_linux/` runs separately on gpio-sim (`linux-hal` job). Installed package (wheel, non-editable)
is verified with `scripts/wheel_smoke.sh` — run it when touching `paths.py`,
`hatch_build.py`, `README.md`, or paths to `schemas/`, `boards/`, `gates/`.

Two non-negotiable rules, detailed in `CONTRIBUTING.md`:

- **No tests may be skipped** (§5). CI fails the build on any skip.
- **Every corpus is bidirectionally closed** (§3): one expected entry per file, one file per entry —
  `expected_errors.yaml` for gates and traces, `expected_results.yaml` for tool calls.

Current test count lives in `roadmap/neuroedge-roadmap.md` §0.1, not recorded here.

## Completing a Task

Follow **`CONTRIBUTING.md` §8**, in the same PR as code: progress in roadmap, one entry
in `CHANGELOG.md` `[Unreleased]`, specification if behavior changed. Every truth has
exactly one place (§8.1) — other places reference codes, do not duplicate. Run `ruff check .` and
`ruff format --check .` (in `python/`) before committing; CI blocks on both.

## Skill routing

When the user's request matches an available skill, invoke it via the Skill tool. When in doubt, invoke the skill.

Key routing rules:
- Product ideas/brainstorming → invoke /office-hours
- Strategy/scope → invoke /plan-ceo-review
- Architecture → invoke /plan-eng-review
- Design system/plan review → invoke /design-consultation or /plan-design-review
- Full review pipeline → invoke /autoplan
- Bugs/errors → invoke /investigate
- QA/testing site behavior → invoke /qa or /qa-only
- Code review/diff check → invoke /review
- Visual polish → invoke /design-review
- Ship/deploy/PR → invoke /ship or /land-and-deploy
- Save progress → invoke /context-save
- Resume context → invoke /context-restore
- Author a backlog-ready spec/issue → invoke /spec
