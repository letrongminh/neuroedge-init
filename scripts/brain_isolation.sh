#!/usr/bin/env bash
# The brain's own OS user, kept apart from the box (Q-83 DP-A-03, TC-A-03-2). Used by
# .github/workflows/ci-sim-linux.yml job `linux-hal`, after the LinuxHAL tests, on a runner
# where scripts/setup_gpio_sim.sh made a virtual GPIO chip (NEUROEDGE_GPIO_SIM_CHIP).
#
#   bash scripts/brain_isolation.sh
#
# Needs sudo. It changes the machine the way a home box is set up (docs/spec/deployment_profiles.md
# DP-A-03): the chip goes to group `gpio` (0660), a system user `neuroclaw` with no groups is made,
# and /proc is remounted with hidepid=2. Then, as that user, for real:
#
#   * opening the GPIO chip and reading the box's key fail with EACCES;
#   * the box's local page link file (ui.json) cannot be read;
#   * POST /confirm to the running page is 403 — no key, no answer;
#   * `neuroedge doctor` named /proc before the remount and finds nothing after it.
#
# Any other outcome is exit 1. Never run it on a machine you care about.
set -euo pipefail

fail() {
  printf '::error::%s\n' "$*" >&2
  exit 1
}
ok() { printf '  ok  %s\n' "$*"; }

chip=${NEUROEDGE_GPIO_SIM_CHIP:?run scripts/setup_gpio_sim.sh first}
brain=neuroclaw
repo=$(cd "$(dirname "$0")/.." && pwd)
work=$(mktemp -d)
page_pid=
cleanup() {
  [ -n "$page_pid" ] && kill "$page_pid" 2>/dev/null || true
  pkill -P $$ -x sleep 2>/dev/null || true # the `sleep 600` that holds the page's stdin
  rm -rf "$work"
}
trap cleanup EXIT
trap 'exit 130' INT # through the EXIT trap: the page never outlives the script
trap 'exit 143' TERM
chmod 755 "$work" # the brain may enter it; what is inside decides the rest

# --- the machine as a box keeps it --------------------------------------------------------------
sudo groupadd -f gpio
sudo chgrp gpio "$chip"
sudo chmod 660 "$chip"
# The runner's other device nodes (setup_i2c_stub.sh opens them to everyone): a box's are not.
sudo groupadd -f i2c
for node in /dev/i2c-* /dev/spidev*; do
  [ -e "$node" ] || continue
  sudo chgrp i2c "$node"
  sudo chmod 660 "$node"
done
id "$brain" >/dev/null 2>&1 || sudo useradd --system --no-create-home --shell /usr/sbin/nologin "$brain"
[ "$(id -Gn "$brain")" = "$brain" ] || fail "$brain is in groups: $(id -Gn "$brain")"

keys="$work/keys"
neuroedge pair init --out "$keys" --audience https://localhost:8443/mcp >/dev/null

# --- doctor: /proc first, then nothing ---------------------------------------------------------
set +e
before=$(neuroedge doctor --brain-user "$brain" --keys "$keys" 2>&1)
status=$?
set -e
[ "$status" = 1 ] || fail "doctor before hidepid: exit $status, expected 1: $before"
grep -q "hidepid" <<<"$before" || fail "doctor did not name /proc: $before"
ok "doctor names /proc without hidepid"
sudo mount -o remount,hidepid=2 /proc
neuroedge doctor --brain-user "$brain" --keys "$keys" || fail "doctor still finds a problem after the remount"
ok "doctor: $brain is kept apart"

# --- as the brain, for real ---------------------------------------------------------------------
as_brain() { sudo -u "$brain" -- "$@"; }
probe='import errno, sys
try:
    open(sys.argv[1], "rb").close()
except OSError as e:
    sys.exit(0 if e.errno == errno.EACCES else 2)
sys.exit(1)'
for target in "$chip" "$keys/issuer.key" "$keys/hop.key"; do
  as_brain python3 -c "$probe" "$target" || fail "$brain could open $target (or failed other than EACCES)"
  ok "$brain cannot open $target (EACCES)"
done

# The box's own page, as the box's user; the brain is on the same machine.
export XDG_STATE_HOME="$work/state"
sleep 600 | neuroedge mcp serve --ui --agent "$repo/fixtures/agents/chat-den-cua/agent.toml" \
  >"$work/page.log" 2>&1 &
page_pid=$!
link="$XDG_STATE_HOME/neuroedge/ui.json"
for _ in $(seq 1 100); do
  [ -s "$link" ] && break
  sleep 0.1
done
[ -s "$link" ] || fail "the page wrote no $link: $(cat "$work/page.log")"
chmod 755 "$XDG_STATE_HOME" # even with the parent open, the directory and file stay the box's
as_brain cat "$link" >/dev/null 2>&1 && fail "$brain could read the page's link file"
ok "$brain cannot read the page's link file"
url=$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["url"].split("#")[0])' "$link")
origin=${url%/}
code=$(as_brain curl -s -o /dev/null -w '%{http_code}' -X POST -H "Origin: $origin" \
  -H 'Content-Type: application/json' -d '{"id":"confirm_1","answer":"yes"}' "${origin}/confirm")
[ "$code" = 403 ] || fail "POST /confirm as $brain: HTTP $code, expected 403"
ok "POST /confirm as $brain: 403"
echo "TC-A-03-2: $brain is kept apart from the box"
