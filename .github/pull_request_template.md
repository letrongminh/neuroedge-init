## Task

<!-- Increment · task ID / decision / RFC, e.g.: I3 · TSK-S4-01 · Q-17 -->

## Changes

<!-- One to three sentences: observable changes. Put long rationales here, not in the changelog. -->

## Task completion — `CONTRIBUTING.md` §8

- [ ] Clean CI: `pytest -q` (0 failed, 0 skipped) · `ruff check .` · `ruff format --check .` (in `python/`) · `neuroedge gate lint` · new/modified gates: `scripts/check_digests.py`
- [ ] Roadmap: task row (single status glyph) · exit criteria with evidence · §0.2 if progress or forecast changes (forecast changes require evidence and moving dependent increments) · §0.1, §0.3 (replace, do not append)
- [ ] Demo (Q-49): script `demo/<increment>/` added or re-run, recording commit — or: *not applicable*
- [ ] `CHANGELOG.md` `[Unreleased]`: single entry ≤ 3 lines (update existing entry if present) · §2 if commands or outputs changed
- [ ] Spec / PRD §15 / RFC (`CONTRIBUTING.md` §3) — only if behavior or decisions changed, or: *not applicable*
- [ ] `TODOS.md`: add deferred work with milestone, delete completed items, review milestones mentioning this task — or: *not applicable*
- [ ] Grepped for stale references of every fact just changed
