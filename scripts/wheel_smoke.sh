#!/usr/bin/env bash
# The stranger's journey on an installed package, outside any checkout (TSK-S3-17).
#
# Builds the sdist and the wheel *from* it (what PyPI users get), installs the
# wheel into a clean venv, and runs the M1 path from a temporary directory with
# NEUROEDGE_ROOT unset. Every step must exit 0; the canonical traces must
# replay to their golden decisions from the packaged copies.
#
#   scripts/wheel_smoke.sh [python]      # default: python3
#
# Measured 2026-09-23 before this existed: `build`, `run`, `test` and
# `gate lint` all failed on an installed wheel while 573 editable tests passed.
set -euo pipefail

PY=${1:-python3}
REPO=$(cd "$(dirname "$0")/.." && pwd)
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
unset NEUROEDGE_ROOT

step() { echo "::group::neuroedge $*"; "$NE" "$@"; echo "::endgroup::"; }

"$PY" -m venv "$WORK/build-env"
"$WORK/build-env/bin/pip" install -q build
"$WORK/build-env/bin/python" -m build -q --outdir "$WORK/dist" "$REPO/python" >/dev/null
WHEEL=$(ls "$WORK"/dist/*.whl)
echo "wheel (built from the sdist): $(basename "$WHEEL")"

LISTING=$(unzip -l "$WHEEL")  # listed once: `unzip | grep -q` trips pipefail on SIGPIPE
for asset in schemas/trace.v1.json boards/sim-default.toml gates/unlock_door@1.2.0.yaml \
  fixtures/traces/happy-path.json fixtures/agents/villa-concierge/agent.toml; do
  case "$LISTING" in
    *"neuroedge/_data/$asset"*) ;;
    *) echo "::error::wheel lacks $asset"; exit 1 ;;
  esac
done

"$PY" -m venv "$WORK/venv"
"$WORK/venv/bin/pip" install -q "$WHEEL" pytest
NE="$WORK/venv/bin/neuroedge"
cd "$WORK"

step board list
step gate lint
step trace validate "$("$WORK/venv/bin/python" -c 'import neuroedge.paths as p; print(p.fixtures_dir())')/traces/happy-path.json"
step verify
step new my-agent
cd "$WORK/my-agent"
step build --target sim --board sim-default
step run -c "mở khoá"
step record -c "mở khoá" --out traces/session.json
step replay traces/session.json --agent agent.toml
step trace view traces/session.json
step test
cd "$WORK"
step new villa --template villa-concierge
cd "$WORK/villa"
step run -c "mở cửa phòng 101"
step test
cd "$WORK"
step new nha --template home-voice
cd "$WORK/nha"
step run -c "bật đèn"
step run -c "wifi nhà mình là gì"
step test
echo "✓ the installed wheel runs the whole journey"
