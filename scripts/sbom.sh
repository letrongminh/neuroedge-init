#!/usr/bin/env bash
# CycloneDX SBOM of the wheel as a user installs it (TSK-W0-02).
#
#   bash scripts/sbom.sh <wheel> <out.cdx.json>
#
# Installs the wheel into an empty virtualenv (no pip, no setuptools), holding every
# dependency to python/requirements-lock.txt, then describes that environment with
# cyclonedx-py (the `cyclonedx-bom` package must be installed in the calling Python).
# The lock also holds the dev tools; only what the wheel pulls in lands in the SBOM.
#
# Deterministic, so two releases diff cleanly: --output-reproducible drops the random
# serial number, and the timestamp is the commit time (SOURCE_DATE_EPOCH), not now.
#
# Fails if the environment holds a dependency the lock does not pin: the SBOM would
# then describe a version chosen on the day of the build, not the pinned set
# (§3.9 obligation 5).
set -euo pipefail

wheel="${1:?usage: sbom.sh <wheel> <out.cdx.json>}"
out="${2:?usage: sbom.sh <wheel> <out.cdx.json>}"
root="$(cd "$(dirname "$0")/.." && pwd)"
lock="$root/python/requirements-lock.txt"
python="${PYTHON:-python3}"

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

"$python" -m venv --without-pip "$work/env"
"$python" -m pip --python "$work/env/bin/python" install --quiet --disable-pip-version-check \
  -c "$lock" "$wheel"

# Every installed distribution except the product itself must be pinned by the lock,
# at the installed version. Names compared PEP 503-normalised.
"$python" -m pip --python "$work/env/bin/python" list --format=freeze --disable-pip-version-check \
  > "$work/installed.txt"
"$python" - "$lock" "$work/installed.txt" <<'PY'
import re
import sys


def pins(path):
    out = {}
    for line in open(path, encoding="utf-8"):
        line = line.split("#", 1)[0].strip()
        if line:
            name, _, version = line.partition("==")
            out[re.sub(r"[-_.]+", "-", name).lower()] = version
    return out


lock, installed = pins(sys.argv[1]), pins(sys.argv[2])
installed.pop("neuroedge", None)
bad = [
    f"{name}=={version} (lock: {lock.get(name, 'absent')})"
    for name, version in sorted(installed.items())
    if lock.get(name) != version
]
if bad:
    sys.exit(
        "::error::the wheel's environment is not the pinned set — regenerate "
        "python/requirements-lock.txt (its header says how):\n  " + "\n  ".join(bad)
    )
print(f"  ok  {len(installed)} dependencies, all pinned by the lock")
PY

SOURCE_DATE_EPOCH="$(git -C "$root" log -1 --format=%ct)" \
  "$python" -m cyclonedx_py environment \
  --pyproject "$root/python/pyproject.toml" \
  --mc-type library \
  --spec-version 1.6 \
  --output-reproducible \
  --output-file "$out" \
  "$work/env/bin/python"
echo "  ok  SBOM written to $out"
