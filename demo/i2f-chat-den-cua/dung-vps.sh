#!/usr/bin/env bash
# Dựng bộ não trên VPS từ laptop, một lệnh (§0.2 của kich-ban.md):
#
#   bash demo/i2f-chat-den-cua/dung-vps.sh            # cài, chép, bật dịch vụ neuroedge-nao
#   bash demo/i2f-chat-den-cua/dung-vps.sh stop       # bước 4: cắt cloud
#   bash demo/i2f-chat-den-cua/dung-vps.sh restart    # K2: khởi động lại, trí nhớ còn
#   bash demo/i2f-chat-den-cua/dung-vps.sh logs       # K1: log của bộ não
#
# Không có VPS: đặt VPS_ORB=<tên máy> trong .env.txt để dùng một máy Linux của OrbStack trên
# chính Mac này (`orb create ubuntu neuroedge-nao`). Khi đó không cần SSH hay Tailscale: bộ não
# gọi hộp qua host.orb.internal, và hộp chạy với `chay-hop.sh --local`.
#
# Đọc .env.txt ở gốc kho. Chép lên VPS đúng những gì bộ não cần: ba biến (key LLM, bot
# Telegram, ID chủ nhà) và bốn tệp khoá (ca.pem, nao.pem, nao.key, nao.token) — không bao giờ
# issuer.key hay hop.key. Hộp phải đã chạy một lần (chay-hop.sh) để có khoá.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
set -a
# shellcheck source=/dev/null
. "${NEUROEDGE_DEMO_ENV:-$ROOT/.env.txt}"
set +a
K="${NEUROEDGE_DEMO_KEYS:-$HOME/neuroedge-demo-khoa}"
REMOTE=/opt/neuroedge-nao
# user không phải root (Google Cloud, Oracle, AWS) thì mọi lệnh hệ thống đi qua sudo
SUDO=""; [ -n "${VPS_ORB:-}" ] || [ "${VPS_USER:-root}" = root ] || SUDO="sudo"

remote() {  # một dòng lệnh trên máy bộ não
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
  *) echo "cách dùng: dung-vps.sh [up|stop|start|restart|logs [n]]" >&2; exit 2 ;;
esac

NEEDED=(OPENROUTER_API_KEY TELEGRAM_BOT_TOKEN TELEGRAM_OWNER_ID)
[ -n "${VPS_ORB:-}" ] || NEEDED+=(VPS_HOST VPS_SSH_KEY TAILSCALE_AUTHKEY)
for name in "${NEEDED[@]}"; do
  [ -n "${!name:-}" ] || { echo "điền $name trong .env.txt" >&2; exit 1; }
done
[ -f "$K/nao.token" ] || { echo "chưa có khoá ở $K: chạy chay-hop.sh một lần trước" >&2; exit 1; }
if [ -n "${VPS_ORB:-}" ]; then
  HOP=host.orb.internal
else
  command -v tailscale >/dev/null || { echo "laptop cần tailscale" >&2; exit 1; }
  HOP="$(tailscale status --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["Self"]["DNSName"].rstrip("."))')"
fi

STAGE="$(mktemp -d)"; trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$STAGE/khoa"
cp "$HERE/cau-noi.py" "$HERE/chay-nao.sh" "$STAGE/"
cp -r "$HERE/picoclaw" "$STAGE/"
cp "$K/ca.pem" "$K/nao.pem" "$K/nao.key" "$K/nao.token" "$STAGE/khoa/"
printf 'OPENROUTER_API_KEY=%s\nTELEGRAM_BOT_TOKEN=%s\nTELEGRAM_OWNER_ID=%s\n' \
  "$OPENROUTER_API_KEY" "$TELEGRAM_BOT_TOKEN" "$TELEGRAM_OWNER_ID" > "$STAGE/.env.txt"
chmod 600 "$STAGE/.env.txt" "$STAGE/khoa/"*

remote "$SUDO mkdir -p $REMOTE && $SUDO chmod 700 $REMOTE"
# COPYFILE_DISABLE: tar của macOS không kèm thuộc tính mở rộng mà tar của Linux không hiểu
COPYFILE_DISABLE=1 tar --no-xattrs -C "$STAGE" -czf - . | remote "$SUDO tar -C $REMOTE -xzf -"

remote "$SUDO bash -s -- '${TAILSCALE_AUTHKEY:-}' '$HOP' '$REMOTE'" <<'EOF'
set -euo pipefail
AUTHKEY="$1"; HOP="$2"; REMOTE="$3"
command -v python3 >/dev/null || { apt-get update -qq && apt-get install -y -qq python3; }
if [ -n "$AUTHKEY" ]; then  # VPS thật: vào tailnet; OrbStack: đã thấy Mac qua host.orb.internal
  command -v tailscale >/dev/null || curl -fsSL https://tailscale.com/install.sh | sh
  tailscale status >/dev/null 2>&1 || tailscale up --authkey "$AUTHKEY" --hostname neuroedge-nao
fi
cat > /etc/systemd/system/neuroedge-nao.service <<UNIT
[Unit]
Description=NeuroEdge brain (trimmed PicoClaw) for the chat-den-cua demo
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
echo "xong: bộ não trên ${VPS_ORB:-$VPS_HOST} gọi hộp $HOP:8443. Nhắn bot Telegram để thử." >&2
