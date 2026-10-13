#!/usr/bin/env bash
# Hộp tại nhà (§0.1 của kich-ban.md): tạo khoá nếu chưa có, rồi chạy `mcp serve --http --ui`.
#
#   bash demo/i2f-chat-den-cua/chay-hop.sh            # nghe trên IP Tailscale (VPS gọi tới)
#   bash demo/i2f-chat-den-cua/chay-hop.sh --local    # nghe trên 127.0.0.1 (bộ não trên laptop, §5)
#
# Đọc .env.txt ở gốc kho (TAILSCALE_TAILNET). Khoá ở ~/neuroedge-demo-khoa, vết ghi ở
# ~/neuroedge-demo-vet-ghi.json (ghi khi Ctrl-C).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
set -a; [ -f "$ROOT/.env.txt" ] && . "$ROOT/.env.txt"; set +a
K="${NEUROEDGE_DEMO_KEYS:-$HOME/neuroedge-demo-khoa}"
PY="$ROOT/python/.venv/bin/python"

if [ "${1:-}" = "--local" ]; then
  HOST=127.0.0.1
  NAME=localhost
else
  command -v tailscale >/dev/null || { echo "cần tailscale: https://tailscale.com/download" >&2; exit 1; }
  HOST="$(tailscale ip -4)"
  NAME="$(tailscale status --json | "$PY" -c 'import json,sys; print(json.load(sys.stdin)["Self"]["DNSName"].rstrip("."))')"
fi
AUDIENCE="https://${HOP_NAME:-$NAME}:8443/mcp"

if [ ! -f "$K/hop.json" ]; then
  "$PY" "$ROOT/demo/i2f-chat-den-cua/tao-khoa.py" --out "$K" --audience "$AUDIENCE" \
    --host "$NAME" --host "$HOST"
fi
AUDIENCE="$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["audience"])' "$K/hop.json")"
ISSUER="$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["issuer"])' "$K/hop.json")"

echo "hộp: $HOST:8443, audience $AUDIENCE; trang tại nhà in ra bên dưới" >&2
exec "$ROOT/python/.venv/bin/neuroedge" mcp serve --http --ui --target sim \
  --agent "$ROOT/fixtures/agents/chat-den-cua/agent.toml" \
  --host "$HOST" --port 8443 \
  --tls-cert "$K/hop.pem" --tls-key "$K/hop.key" --client-ca "$K/ca.pem" \
  --issuer "$ISSUER" --audience "$AUDIENCE" --jwks "$K/jwks.json" \
  --trace-out "${NEUROEDGE_DEMO_TRACE:-$HOME/neuroedge-demo-vet-ghi.json}"
