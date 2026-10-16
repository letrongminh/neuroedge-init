#!/usr/bin/env bash
# D1 of kich-ban.md: one day of the fish tank on `sim`, typed at a presenter's pace, then replayed.
#
#   bash demo/i2b-be-ca-gia-lap/chay-sim.sh                 # in the terminal
#   bash demo/i2b-be-ca-gia-lap/chay-sim.sh --ui            # and on the live page (127.0.0.1:8765)
#   PACE=3 bash demo/i2b-be-ca-gia-lap/chay-sim.sh          # slower, to talk over it
#
# The day is mot-ngay.txt (python/tests/test_aquarium.py checks what each line does). PACE must stay
# above a relay's min_interval_ms (1 s) and the whole day under its max_continuous_ms (60 s).
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/../.." && pwd)"
NE="$ROOT/python/.venv/bin/neuroedge"
AGENT="$ROOT/fixtures/agents/aquarium/agent.toml"
TRACE="${NEUROEDGE_DEMO_TRACE:-${TMPDIR:-/tmp}/be-ca-mot-ngay.json}"
PACE="${PACE:-1.5}"

(while IFS= read -r line; do printf '%s\n' "$line"; sleep "$PACE"; done <"$DIR/mot-ngay.txt") |
  "$NE" run --agent "$AGENT" --trace-out "$TRACE" "$@"
echo
echo "--- replay of $TRACE: the same facts in, the same decisions and pin commands out"
"$NE" replay "$TRACE" --agent "$AGENT"
