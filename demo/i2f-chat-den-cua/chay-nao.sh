#!/usr/bin/env bash
# Bộ não (§0.2 của kich-ban.md): PicoClaw v0.3.1 rút gọn + cầu nối mTLS tới hộp.
#
#   bash chay-nao.sh <host:port của hộp>                 # gateway: chat qua Telegram
#   bash chay-nao.sh <host:port của hộp> agent -m "..."  # một câu, không cần Telegram
#   bash chay-nao.sh <host:port của hộp> mcp test neuroedge
#
# Chạy được trên VPS (Linux) lẫn laptop (macOS). Đọc từ cùng thư mục với script:
#   .env.txt                  OPENROUTER_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_OWNER_ID
#   khoa/{ca.pem,nao.pem,nao.key,nao.token}
# (trong kho: .env.txt ở gốc kho, khoá ở ~/neuroedge-demo-khoa). Mọi trạng thái của bộ não —
# cấu hình, trí nhớ, phiên, cron — nằm ở $NAO_HOME (mặc định ~/.neuroedge-nao), giữ qua mỗi lần chạy lại.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
TARGET="${1:?cách dùng: chay-nao.sh <host:port của hộp> [lệnh picoclaw…]}"; shift
VERSION=v0.3.1

ENV="$HERE/.env.txt"; [ -f "$ENV" ] || ENV="$HERE/../../.env.txt"
set -a
# shellcheck source=/dev/null
. "$ENV"
set +a
K="$HERE/khoa"; [ -d "$K" ] || K="${NEUROEDGE_DEMO_KEYS:-$HOME/neuroedge-demo-khoa}"
NAO_HOME="${NAO_HOME:-$HOME/.neuroedge-nao}"
BIN="$NAO_HOME/bin/picoclaw"
mkdir -p "$NAO_HOME/bin" "$NAO_HOME/workspace"

if [ ! -x "$BIN" ]; then
  case "$(uname -s)/$(uname -m)" in
    Linux/x86_64) ASSET=picoclaw_Linux_x86_64 ;;
    Linux/aarch64|Linux/arm64) ASSET=picoclaw_Linux_arm64 ;;
    Darwin/arm64) ASSET=picoclaw_Darwin_arm64 ;;
    Darwin/x86_64) ASSET=picoclaw_Darwin_x86_64 ;;
    *) echo "chưa hỗ trợ $(uname -s)/$(uname -m)" >&2; exit 1 ;;
  esac
  curl -fsSL "https://github.com/sipeed/picoclaw/releases/download/$VERSION/$ASSET.tar.gz" \
    | tar xz -C "$NAO_HOME/bin" picoclaw
fi

# cấu hình: bản trong kho + token, chủ nhà, key LLM, bot và workspace. Bí mật nằm trong
# config.json của bộ não (quyền 600, ngoài kho), không trong .security.yml: định dạng YAML đó
# của v0.3.1 không bật được kênh Telegram khi thử (2026-10-13).
python3 - "$HERE/picoclaw/config.json" "$NAO_HOME" "$K/nao.token" <<'EOF'
import json, os, sys
source, home, token = sys.argv[1], sys.argv[2], open(sys.argv[3]).read().strip()
config = json.load(open(source))
config["agents"]["defaults"]["workspace"] = os.path.join(home, "workspace")
telegram = config["channel_list"]["telegram"]
telegram["allow_from"] = [os.environ["TELEGRAM_OWNER_ID"]]
telegram.setdefault("settings", {})["token"] = os.environ["TELEGRAM_BOT_TOKEN"]
for model in config["model_list"]:
    model["api_keys"] = [os.environ["OPENROUTER_API_KEY"]]
config["tools"]["mcp"]["servers"]["neuroedge"]["headers"]["Authorization"] = f"Bearer {token}"
path = os.path.join(home, "config.json")
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, "w") as f:
    json.dump(config, f, indent=2, ensure_ascii=False)
os.chmod(path, 0o600)
stale = os.path.join(home, ".security.yml")
if os.path.exists(stale):
    os.remove(stale)
EOF

# biến PICOCLAW_TOOLS_* ghi đè cấu hình: không chạy nếu còn biến nào
if env | grep -q '^PICOCLAW_TOOLS_'; then
  echo "bỏ các biến PICOCLAW_TOOLS_* trước khi chạy: $(env | grep -o '^PICOCLAW_TOOLS_[A-Z_]*')" >&2
  exit 1
fi

python3 "$HERE/cau-noi.py" --target "$TARGET" --server-name localhost \
  --ca "$K/ca.pem" --cert "$K/nao.pem" --key "$K/nao.key" &
BRIDGE=$!
trap 'kill $BRIDGE 2>/dev/null' EXIT
sleep 1

export PICOCLAW_HOME="$NAO_HOME" PICOCLAW_CONFIG="$NAO_HOME/config.json"
if [ $# -eq 0 ]; then set -- gateway; fi
"$BIN" "$@"
