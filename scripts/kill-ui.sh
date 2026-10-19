#!/usr/bin/env bash
# Stop every leftover local page: `neuroedge run ... --ui` (with --all, also `mcp serve ... --ui`
# and `studio`). A page started in the background by a script that then exits is left to PID 1
# and serves until killed; on 2026-10-19 44 of them held ~2.8 GB. Pages started from now on in
# scripts and checks pass --exit-with-parent / --idle-timeout (`neuroedge run --help`).
#
#   bash scripts/kill-ui.sh          # SIGTERM (trace written, ui.json removed), SIGKILL after 5 s
#   bash scripts/kill-ui.sh --all    # also `mcp serve --ui` and `studio` — Claude Desktop's
#                                    # connector included: check --list first
#   bash scripts/kill-ui.sh --list   # show them, stop nothing
set -euo pipefail

pattern='neuroedge(\.cli\.main)? run .*--ui'
list=0
for arg in "$@"; do
  case "$arg" in
    --all) pattern='neuroedge(\.cli\.main)? (run .*--ui|mcp serve .*--ui|studio)' ;;
    --list) list=1 ;;
    *)
      echo "usage: $0 [--all] [--list]" >&2
      exit 2
      ;;
  esac
done

pids() { pgrep -f -- "$pattern" | grep -vx "$$" || true; }

found=$(pids)
if [ -z "$found" ]; then
  echo "no neuroedge page running"
  exit 0
fi
for pid in $found; do
  ps -o pid=,ppid=,etime=,command= -p "$pid" 2>/dev/null || true
done
[ "$list" -eq 1 ] && exit 0

for pid in $found; do kill -TERM "$pid" 2>/dev/null || true; done
for _ in $(seq 1 50); do
  [ -z "$(pids)" ] && break
  sleep 0.1
done
for pid in $(pids); do
  echo "still running after SIGTERM, sending SIGKILL: $pid"
  kill -KILL "$pid" 2>/dev/null || true
done
echo "stopped $(echo "$found" | wc -w | tr -d ' ') page(s)"
