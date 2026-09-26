#!/usr/bin/env bash
# The stranger's journey on an installed package, outside any checkout (TSK-S3-17).
#
# Builds the sdist and the wheel *from* it (what PyPI users get), installs the
# wheel with the `mcp` extra into a clean venv, and runs the M1 path and the
# README quickstart from a temporary directory with NEUROEDGE_ROOT unset. Every
# step must exit 0; the canonical traces must replay to their golden decisions
# from the packaged copies.
#
#   scripts/wheel_smoke.sh [python]                 # default: python3
#   scripts/wheel_smoke.sh --wheel dist/X.whl [python]
#
# `--wheel` skips the build and tests that exact file: the release workflow
# (.github/workflows/release-pypi.yml) passes the artifact it would publish.
#
# Measured 2026-09-23 before this existed: `build`, `run`, `test` and
# `gate lint` all failed on an installed wheel while 573 editable tests passed.
set -euo pipefail

PY=python3
WHEEL=
while [ $# -gt 0 ]; do
  case "$1" in
    --wheel)
      [ -f "${2:-}" ] || { echo "::error::--wheel needs an existing .whl file"; exit 2; }
      WHEEL=$(cd "$(dirname "$2")" && pwd)/$(basename "$2")
      shift 2
      ;;
    *) PY=$1; shift ;;
  esac
done
REPO=$(cd "$(dirname "$0")/.." && pwd)
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
unset NEUROEDGE_ROOT

step() { echo "::group::neuroedge $*"; "$NE" "$@"; echo "::endgroup::"; }

if [ -z "$WHEEL" ]; then
  "$PY" -m venv "$WORK/build-env"
  "$WORK/build-env/bin/pip" install -q build
  "$WORK/build-env/bin/python" -m build -q --outdir "$WORK/dist" "$REPO/python" >/dev/null
  WHEEL=$(ls "$WORK"/dist/*.whl)
  echo "wheel (built from the sdist): $(basename "$WHEEL")"
else
  echo "wheel (given): $WHEEL"
fi

LISTING=$(unzip -l "$WHEEL")  # listed once: `unzip | grep -q` trips pipefail on SIGPIPE
for asset in schemas/trace.v1.json boards/sim-default.toml gates/unlock_door@1.2.0.yaml \
  fixtures/traces/happy-path.json fixtures/agents/villa-concierge/agent.toml \
  fixtures/agents/factory-monitor/agent.toml \
  fixtures/tool_calls/expected_results.yaml \
  targets/esp32s3/main/main.c targets/esp32s3/components/ne_gate/src/ne_walker.c; do
  case "$LISTING" in
    *"neuroedge/_data/$asset"*) ;;
    *) echo "::error::wheel lacks $asset"; exit 1 ;;
  esac
done
case "$LISTING" in
  *".dist-info/licenses/LICENSE"*) ;;
  *) echo "::error::wheel lacks its LICENSE"; exit 1 ;;
esac
# The firmware sources ship for `build --target esp32s3` (TSK-I3-01). ESP-SR never does
# (its licence is for Espressif chips only, TODOS.md #17), nor any build output.
case "$LISTING" in
  *esp-sr*|*esp_sr*|*managed_components*|*targets/esp32s3/build/*)
    echo "::error::the wheel carries firmware files it must not"; exit 1 ;;
esac

"$PY" -m venv "$WORK/venv"
"$WORK/venv/bin/pip" install -q "$WHEEL[mcp]" pytest
NE="$WORK/venv/bin/neuroedge"
cd "$WORK"

# The PyPI page is the root README (TSK-S3-20), byte for byte.
"$WORK/venv/bin/python" - "$REPO/README.md" <<'PY'
import sys
from importlib.metadata import metadata
from pathlib import Path

page = metadata("neuroedge").get_payload()
readme = Path(sys.argv[1]).read_text(encoding="utf-8")
if page.strip() != readme.strip():
    sys.exit("::error::the wheel's long description is not the root README.md")
print("long description = root README.md")
PY

step board list
step gate lint
step trace validate "$("$WORK/venv/bin/python" -c 'import neuroedge.paths as p; print(p.fixtures_dir())')/traces/happy-path.json"
step verify
step new my-agent
cd "$WORK/my-agent"
# The trace path convention (FR-TRC-09): `_common/` must ship in the wheel.
for kept in traces/README.md traces/incidents/.gitkeep traces/golden/.gitkeep; do
  [ -f "$kept" ] || { echo "::error::neuroedge new did not create $kept"; exit 1; }
done
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
step new plant --template factory-monitor
cd "$WORK/plant"
step build --target sim --board sim-default
step run -c "bật quạt"
step run -c "tắt quạt"
step run -c "tắt báo động"
step gate lint gates
step test
cd "$WORK"

# The README quickstart, as written (Desktop's config replaced by a scratch file).
step new my-home --template home-voice
cd "$WORK/my-home"
step build --target sim --board sim-default
# The agent's firmware from the packaged sources: a complete ESP-IDF project (TSK-I3-01).
step build --target esp32s3 --board esp32s3-box-3
for kept in CMakeLists.txt main/main.c components/ne_agent/ne_agent.c \
  components/ne_agent/include/ne_agent.h components/ne_agent/gates/light_on.netree.h; do
  [ -f "build/esp32s3/$kept" ] || { echo "::error::build --target esp32s3 did not write $kept"; exit 1; }
done
step run -c "bật đèn"
step run -c "wifi nhà mình là gì"
step gate lint gates
step mcp tools
step test
cd "$WORK"
DESKTOP="$WORK/claude_desktop_config.json"
step mcp desktop-config --agent my-home/agent.toml --ui --write --config-path "$DESKTOP"
"$WORK/venv/bin/python" - "$DESKTOP" "$WORK/my-home/agent.toml" <<'PY'
import json
import sys
from pathlib import Path

(entry,) = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["mcpServers"].values()
agent = str(Path(sys.argv[2]).resolve())
if agent not in entry["args"] or "env" in entry:
    sys.exit(f"::error::unexpected Desktop entry: {entry}")
print("Desktop entry: absolute agent path, no PYTHONPATH pin")
PY
echo "✓ the installed wheel runs the whole journey"
