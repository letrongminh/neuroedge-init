#!/usr/bin/env bash
# The partner guides, executed (TSK-I2c-19, Q-70): every command block of the three guides in
# docs/user/doi-tac/ runs, in order, in a clean venv installed from a wheel, against local doubles
# (a double of Home Assistant's MCP server and a device HTTP API), and the outputs the guides promise
# are checked. Any mismatch exits 1 naming the guide and the step.
#
#   scripts/partner_guides_check.sh <wheel> [python]
#
# The marker syntax that makes a block runnable (or skipped, with a reason) is documented at the top
# of scripts/guide_runner.py; python/tests/test_partner_guides.py holds the guides to it without a wheel.
# Needs: bash, curl, awk, python 3.11+; port 8787 free (the default of `proxy http`).
set -euo pipefail

WHEEL=${1:-}
PY=${2:-python3}
[ -f "$WHEEL" ] || { echo "usage: $0 <wheel.whl> [python]" >&2; exit 2; }
WHEEL=$(cd "$(dirname "$WHEEL")" && pwd)/$(basename "$WHEEL")
REPO=$(cd "$(dirname "$0")/.." && pwd)
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

"$PY" -m venv "$WORK/venv"
"$WORK/venv/bin/pip" install -q "$WHEEL[mcp]"
echo "wheel: $(basename "$WHEEL") · $("$WORK/venv/bin/neuroedge" --help >/dev/null && echo installed)"

GUIDES="$REPO/docs/user/doi-tac"
"$WORK/venv/bin/python" "$REPO/scripts/guide_runner.py" \
  --venv "$WORK/venv" --work "$WORK/run" \
  "$GUIDES/home-assistant-mcp.md" "$GUIDES/guard-python.md" "$GUIDES/proxy-http.md" \
  --also-check "$GUIDES/README.md"
