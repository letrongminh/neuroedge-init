#!/usr/bin/env bash
# Kịch bản nhà kính trên `sim-virtual`, gõ theo nhịp người trình bày, rồi phát lại (xem kich-ban.md).
#
#   bash demo/i2d-nha-kinh/chay-sim.sh                 # trong terminal
#   bash demo/i2d-nha-kinh/chay-sim.sh --ui            # và trên trang trực tiếp (127.0.0.1:8765)
#   PACE=3 bash demo/i2d-nha-kinh/chay-sim.sh          # chậm hơn, để vừa nói vừa chạy
#
# PACE phải lớn hơn min_interval_ms của rơ-le (2 s) và cả kịch bản phải nằm dưới max_continuous_ms
# (60 s với máy sưởi và bơm phun sương).
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/../.." && pwd)"
NE="$ROOT/python/.venv/bin/neuroedge"
AGENT="$ROOT/fixtures/agents/greenhouse/agent.toml"
TRACE="${NEUROEDGE_DEMO_TRACE:-${TMPDIR:-/tmp}/nha-kinh-mot-ngay.json}"
PACE="${PACE:-2.5}"

(while IFS= read -r line; do printf '%s\n' "$line"; sleep "$PACE"; done <"$DIR/mot-ngay.txt") |
  "$NE" run --agent "$AGENT" --trace-out "$TRACE" "$@"
echo
echo "--- phát lại $TRACE: cùng dữ kiện vào, cùng quyết định và lệnh chân ra"
"$NE" replay "$TRACE" --agent "$AGENT"
