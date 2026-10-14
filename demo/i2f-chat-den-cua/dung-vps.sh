#!/usr/bin/env bash
# Stand up the brain on a VPS from the laptop, one command (§0.2 of kich-ban.md):
#
#   bash demo/i2f-chat-den-cua/dung-vps.sh            # install, upload, enable the neuroedge-nao service
#   bash demo/i2f-chat-den-cua/dung-vps.sh stop       # step 4: cut the cloud
#   bash demo/i2f-chat-den-cua/dung-vps.sh restart    # K2: restart, memory survives
#   bash demo/i2f-chat-den-cua/dung-vps.sh logs       # K1: the brain's log
#
# No VPS: set VPS_ORB=<machine name> in .env.txt to use an OrbStack Linux machine on this very
# Mac (`orb create ubuntu neuroedge-nao`). Then neither SSH nor Tailscale is needed: the brain
# calls the box through host.orb.internal, and the box runs with `chay-hop.sh --local`.
#
# Reads .env.txt at the repo root. Uploads to the VPS exactly what the brain needs: three variables
# (LLM key, Telegram bot, owner ID) and four key files (ca.pem, nao.pem, nao.key, nao.token) — never
# issuer.key or hop.key. The box must have run once (chay-hop.sh) so the keys exist.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
set -a
# shellcheck source=/dev/null
. "${NEUROEDGE_DEMO_ENV:-$ROOT/.env.txt}"
set +a
K="${NEUROEDGE_DEMO_KEYS:-$HOME/neuroedge-demo-khoa}"
REMOTE=/opt/neuroedge-nao
# a non-root user (Google Cloud, Oracle, AWS) sends every system command through sudo
SUDO=""; [ -n "${VPS_ORB:-}" ] || [ "${VPS_USER:-root}" = root ] || SUDO="sudo"

remote() {  # run one command line on the brain's machine
  if [ -n "${VPS_ORB:-}" ]; then
    orb -m "$VPS_ORB" -u root bash -c "$1"
  else
    ssh -i "${VPS_SSH_KEY/#\~/$HOME}" -o StrictHostKeyChecking=accept-new "$VPS_USER@$VPS_HOST" "$1"
  fi
}

case "${1:-up}" in
  stop|restart|start) remote "$SUDO systemctl $1 neuroedge-nao && $SUDO systemctl --no-pager status neuroedge-nao | head -3"; exit ;;
  logs) remote "$SUDO journalctl -u neuroedge-nao -n ${2:-100} --no-pager"; exit ;;
  up) ;;
  *) echo "usage: dung-vps.sh [up|stop|start|restart|logs [n]]" >&2; exit 2 ;;
esac

NEEDED=(OPENROUTER_API_KEY TELEGRAM_BOT_TOKEN TELEGRAM_OWNER_ID)
[ -n "${VPS_ORB:-}" ] || NEEDED+=(VPS_HOST VPS_SSH_KEY TAILSCALE_AUTHKEY)
for name in "${NEEDED[@]}"; do
  [ -n "${!name:-}" ] || { echo "set $name in .env.txt" >&2; exit 1; }
done
[ -f "$K/nao.token" ] || { echo "no keys at $K yet: run chay-hop.sh once first" >&2; exit 1; }
if [ -n "${VPS_ORB:-}" ]; then
  HOP=host.orb.internal
else
  command -v tailscale >/dev/null || { echo "the laptop needs tailscale" >&2; exit 1; }
  HOP="$(tailscale status --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["Self"]["DNSName"].rstrip("."))')"
fi

STAGE="$(mktemp -d)"; trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$STAGE/khoa"
cp "$HERE/chay-nao.sh" "$STAGE/"
cp -r "$HERE/neuroclaw" "$STAGE/"
cp "$K/ca.pem" "$K/nao.pem" "$K/nao.key" "$K/nao.token" "$STAGE/khoa/"
printf 'OPENROUTER_API_KEY=%s\nTELEGRAM_BOT_TOKEN=%s\nTELEGRAM_OWNER_ID=%s\n' \
  "$OPENROUTER_API_KEY" "$TELEGRAM_BOT_TOKEN" "$TELEGRAM_OWNER_ID" > "$STAGE/.env.txt"
chmod 600 "$STAGE/.env.txt" "$STAGE/khoa/"*

remote "$SUDO mkdir -p $REMOTE && $SUDO chmod 700 $REMOTE"
# COPYFILE_DISABLE: macOS tar would add extended attributes that Linux tar does not understand
COPYFILE_DISABLE=1 tar --no-xattrs -C "$STAGE" -czf - . | remote "$SUDO tar -C $REMOTE -xzf -"

remote "$SUDO bash -s -- '${TAILSCALE_AUTHKEY:-}' '$HOP' '$REMOTE'" <<'EOF'
set -euo pipefail
AUTHKEY="$1"; HOP="$2"; REMOTE="$3"
command -v python3 >/dev/null || { apt-get update -qq && apt-get install -y -qq python3; }
if [ -n "$AUTHKEY" ]; then  # real VPS: join the tailnet; OrbStack: already sees the Mac through host.orb.internal
  command -v tailscale >/dev/null || curl -fsSL https://tailscale.com/install.sh | sh
  tailscale status >/dev/null 2>&1 || tailscale up --authkey "$AUTHKEY" --hostname neuroedge-nao
fi
cat > /etc/systemd/system/neuroedge-nao.service <<UNIT
[Unit]
Description=NeuroEdge brain (NeuroClaw) for the chat-den-cua demo
After=network-online.target tailscaled.service
Wants=network-online.target

[Service]
Environment=NAO_HOME=/var/lib/neuroedge-nao
Environment=HOME=/var/lib/neuroedge-nao
ExecStart=/bin/bash $REMOTE/chay-nao.sh $HOP:8443 gateway
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now neuroedge-nao
systemctl restart neuroedge-nao
sleep 5
systemctl --no-pager status neuroedge-nao | head -5
EOF
echo "done: the brain on ${VPS_ORB:-$VPS_HOST} calls the box $HOP:8443. Message the Telegram bot to try it." >&2
