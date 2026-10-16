#!/usr/bin/env bash
# The full fish tank on the virtual board `sim-virtual`, driven by kich-ban.md's steps.
#
#   bash demo/i2d-be-ca-day-du/chay-sim.sh                 # a REPL in the terminal, you type
#   bash demo/i2d-be-ca-day-du/chay-sim.sh --ui            # and on the live page (127.0.0.1:8765)
#
# Typed by hand: the presenter sets `:sensor ph 6.2` and says the commands of kich-ban.md at their
# own pace (each output pin wants min_interval_ms = 2 s between commands). The trace of the session
# is replayed at the end: the same facts in, the same decisions out. The board is rebuilt from the
# agent for the replay and its digest must match (VP-VB-06).
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/../.." && pwd)"
NE="$ROOT/python/.venv/bin/neuroedge"
AGENT="$ROOT/fixtures/agents/aquarium-full/agent.toml"
TRACE="${NEUROEDGE_DEMO_TRACE:-${TMPDIR:-/tmp}/be-ca-day-du.json}"

"$NE" run --agent "$AGENT" --trace-out "$TRACE" "$@"
echo
echo "--- replay of $TRACE: the same facts in, the same decisions and pin commands out"
"$NE" replay "$TRACE" --agent "$AGENT"
