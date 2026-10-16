# Releasing `neuroedge`

**Policy (Q-39):** every increment ends with a tag; the tag for each increment is listed in
`neuroedge-roadmap.md` §0.2. **Before I6, all tags are internal** — nothing is pushed to any index.
The first external release is **I6 — Public**, onto PyPI; the steps below use its
version number (`0.6.0`).

The workflow is [`.github/workflows/release-pypi.yml`](../.github/workflows/release-pypi.yml)
(`TSK-S3-14`). It has six jobs:

| Job | Runs on | What it does |
|:---|:---|:---|
| `build` | every run | sdist, then wheel built **from** sdist; `twine check --strict` (README renders on PyPI); for tags, verifies tag equals `v` + `version` in `python/pyproject.toml` |
| `sbom` | every run, after `build` | CycloneDX SBOM of wheel installed per `requirements-lock.txt` (`scripts/sbom.sh`, artifact `sbom`, `TSK-W0-02`). Separate job: SBOM tools installed from index cannot touch `dist` signed by `attest` |
| `smoke` | every run | clean runner downloads the exact built wheel, runs `scripts/wheel_smoke.sh --wheel` on Python 3.11 and 3.13 |
| `attest` | tags, and manual runs **from `main`**; never PRs | signs build provenance for wheel, sdist, and SBOM (Sigstore), then `gh attestation verify` each file (`TSK-W2-07`) — manual run serves as dry run |
| `publish-testpypi` | pre-release tags (`v0.6.0rc1`, `v0.7.0b1`…) **and** `PUBLISH_ENABLED == 'true'` | pushes to test.pypi.org |
| `publish-pypi` | release tags (`v0.6.0`) **and** `PUBLISH_ENABLED == 'true'` | pushes to pypi.org |
| `github-release` | after either `publish-*` job succeeds | creates GitHub Release for the tag, attaches wheel, sdist, and SBOM |

Publishing to indexes uses trusted publishing (OIDC): the repository holds no PyPI tokens. When
`PUBLISH_ENABLED` is unset, even if someone pushes a tag, both `publish-*` jobs and `github-release` are skipped.
Pull requests modifying packaging files run `build`, `sbom`, and `smoke`, never reaching `attest` or `publish-*`.
**Keep `PUBLISH_ENABLED` unset until I6.**

## Internal tags (I1–I3a, I2a–I2f)

The example below is I1 (`v0.1.0`). The repository is public (since 2026-09-25), but nothing is on an index yet: wheels only go to people in the organization or
testers handed them directly by the team (I1: on-site TTFV test session, `TSK-I1-02`).

- **Version PR.** Update `version` in `python/pyproject.toml` (I1: `0.1.0`); change the heading
  `### [Unreleased]` in `CHANGELOG.md` §1 to `### [0.1.0] — YYYY-MM-DD — internal`, add an
  empty `### [Unreleased]` above it. Do not add a version link at the end of the file — internal tags have no public release page. CI passes, merge.
- **Tag.** `git tag v0.1.0 && git push origin v0.1.0`. Since `PUBLISH_ENABLED` is not set, only
  `build`, `sbom`, `smoke`, and `attest` run; `publish-*` and `github-release` are skipped.
- **Internal GitHub Release** attaching the exact wheel verified by `smoke`, and its SBOM:

  ```bash
  gh run download <run-id> --name dist --dir dist   # run for tag v0.1.0
  gh run download <run-id> --name sbom --dir sbom
  # --source-ref: manual run from main also has provenance; only tags are release builds
  gh attestation verify dist/*.whl --repo letrongminh/neuroedge-init --source-ref refs/tags/v0.1.0
  gh release create v0.1.0 dist/* sbom/* --title "v0.1.0 — internal (I1)" \
      --notes "Internal preview, not released externally. Changes: CHANGELOG.md [0.1.0]."
  ```

- **Acceptance.** The passing `smoke` job on the tag run proves `wheel_smoke.sh --wheel` ran
  on that exact wheel (I1 criterion 5). Update roadmap per `CONTRIBUTING.md` §8.

## Go-live steps — at I6 (one-time setup)

Follow in exact order when I6 opens. Steps 1–4 are configuration; none of them releases anything yet.

1. **Repo is public** as of 2026-09-25 — the entire repository (Q-45, `TSK-I6-01`). Before releasing,
   gitleaks full-history scan must be clean (`TSK-W0-03`, I6 criterion 1). The PyPI page directs readers to
   `https://github.com/letrongminh/neuroedge-init/...` links in `README.md`; if the repo were private,
   all those links would return 404.
2. **Create pending trusted publishers** on both indexes. Go to
   <https://test.pypi.org/manage/account/publishing/> then
   <https://pypi.org/manage/account/publishing/>, under *Add a new pending publisher* → GitHub:

   | Field | test.pypi.org | pypi.org |
   |:---|:---|:---|
   | PyPI Project Name | `neuroedge` | `neuroedge` |
   | Owner | `letrongminh` | `letrongminh` |
   | Repository name | `neuroedge-init` | `neuroedge-init` |
   | Workflow name | `release-pypi.yml` | `release-pypi.yml` |
   | Environment name | `testpypi` | `pypi` |

   Pending publishers **do not reserve** names: the name belongs to you only after the first push.
3. **Create two environments** in GitHub → Settings → Environments: `testpypi` and `pypi`
   (names must match the table above). Recommended: set *Required reviewers* for `pypi` to yourself, and
   restrict *Deployment branches and tags* to `v*` tags only: release builds reach PyPI only when you click approve.
4. **Flip the switch:** Settings → Secrets and variables → Actions → *Variables* →
   `PUBLISH_ENABLED` = `true` (or `gh variable set PUBLISH_ENABLED --body true`).

## Each PyPI release (from I6 onward)

5. **Rehearse on TestPyPI first.** Open a PR updating `version` in `python/pyproject.toml` to
   `0.6.0rc1`, wait for CI to pass, merge. Pre-releases do not modify `CHANGELOG.md`. Then:

   ```bash
   git switch main && git pull
   git tag v0.6.0rc1 && git push origin v0.6.0rc1
   ```

   Wait for `build` → `smoke` → `publish-testpypi` to pass. Verify on a clean machine (or venv)
   outside any checkout — dependencies come from real PyPI because TestPyPI does not have them all:

   ```bash
   pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ \
       'neuroedge[mcp]==0.6.0rc1'
   neuroedge gate lint && neuroedge new my-home --template home-voice
   ```

6. **Production release.** A PR updating `version` to `0.6.0` **and** changing heading
   `### [Unreleased]` in `CHANGELOG.md` §1 to `### [0.6.0] — YYYY-MM-DD`, adding an empty
   `### [Unreleased]` above it, and adding the link at the end of the file
   `[0.6.0]: https://github.com/letrongminh/neuroedge-init/releases/tag/v0.6.0` (following the public repo
   from step 1). Merge, then `git tag v0.6.0 && git push origin v0.6.0`. Approve the `pypi` environment
   when prompted by GitHub. Acceptance for `TSK-S3-14`: `pip install 'neuroedge[mcp]==0.6.0'` in a
   clean venv, then `neuroedge gate lint` and `neuroedge trace validate` run green from the installed package.
7. **Post-release:** update `TSK-S3-14` and I6 criterion 3 in `neuroedge-roadmap.md`
   per `CONTRIBUTING.md` §8. A1 runs full measurements from the PyPI build at I7 (`TSK-I7-02`).

## Troubleshooting

- **Tag differs from `version`:** the `build` job halts with an error stating both values; nothing has been
  pushed. Delete the tag (`git push origin :refs/tags/vX`), fix `version` via PR, and re-tag.
- **Once a version reaches an index, it cannot be replaced.** PyPI forbids re-uploading the same
  version number, even after deletion. Fix issues with a new version number (`0.6.0rc2`, `0.6.1`).
- **Emergency cutoff:** set `PUBLISH_ENABLED` to a value other than `true` (or delete the variable). Both
  `publish-*` jobs will be skipped from the next run onward.
