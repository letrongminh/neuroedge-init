#!/usr/bin/env bash
# The box at home (§0.1 of kich-ban.md): create the keys if missing, then run `mcp serve --http --ui`.
#
#   bash demo/i2f-chat-den-cua/chay-hop.sh            # listen on the Tailscale IP (the VPS calls in)
#   bash demo/i2f-chat-den-cua/chay-hop.sh --local    # listen on 127.0.0.1 (brain on the laptop, §5)
#   NEUROEDGE_DEMO_AGENT=fixtures/agents/aquarium/agent.toml bash demo/i2f-chat-den-cua/chay-hop.sh --local
#                                                     # another agent: the fish tank (demo/i2b-be-ca-gia-lap/)
#
# Reads .env.txt at the repo root (TAILSCALE_TAILNET). Keys live in ~/neuroedge-demo-khoa, the trace in
# ~/neuroedge-demo-vet-ghi.json (written on Ctrl-C).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
set -a; [ -f "$ROOT/.env.txt" ] && . "$ROOT/.env.txt"; set +a
K="${NEUROEDGE_DEMO_KEYS:-$HOME/neuroedge-demo-khoa}"
PY="$ROOT/python/.venv/bin/python"

if [ "${1:-}" = "--local" ]; then
  HOST=127.0.0.1
  NAME=localhost
else
  command -v tailscale >/dev/null || { echo "tailscale is required: https://tailscale.com/download" >&2; exit 1; }
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

echo "box: $HOST:8443, audience $AUDIENCE; the at-home page is printed below" >&2
exec "$ROOT/python/.venv/bin/neuroedge" mcp serve --http --ui --target sim \
  --agent "$ROOT/${NEUROEDGE_DEMO_AGENT:-fixtures/agents/chat-den-cua/agent.toml}" \
  --host "$HOST" --port 8443 \
  --tls-cert "$K/hop.pem" --tls-key "$K/hop.key" --client-ca "$K/ca.pem" \
  --issuer "$ISSUER" --audience "$AUDIENCE" --jwks "$K/jwks.json" \
  --trace-out "${NEUROEDGE_DEMO_TRACE:-$HOME/neuroedge-demo-vet-ghi.json}"
