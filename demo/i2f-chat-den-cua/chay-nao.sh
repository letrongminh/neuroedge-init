#!/usr/bin/env bash
# The brain (§0.2 of kich-ban.md): NeuroClaw (Q-78) connects straight to the box over mTLS.
#
#   bash chay-nao.sh <box host:port>                      # gateway: chat over Telegram
#   bash chay-nao.sh <box host:port> agent -m "..."       # one sentence, no Telegram needed
#   bash chay-nao.sh <box host:port> mcp test neuroedge
#
# Runs on a VPS (Linux) and on a laptop (macOS). Reads from the same directory as the script:
#   .env.txt                  OPENROUTER_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_OWNER_ID
#   khoa/{ca.pem,nao.pem,nao.key,nao.token}
# (in the repo: .env.txt at the repo root, keys in ~/neuroedge-demo-khoa). All of the brain's state —
# config, memory, sessions, cron — lives in $NAO_HOME (default ~/.neuroedge-nao) and survives every re-run.
# NEUROCLAW_BIN=<path> uses an existing NeuroClaw build instead of downloading a release.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
TARGET="${1:?usage: chay-nao.sh <box host:port> [neuroclaw command…]}"; shift
VERSION=v0.2.2

ENV="$HERE/.env.txt"; [ -f "$ENV" ] || ENV="$HERE/../../.env.txt"
set -a
# shellcheck source=/dev/null
. "$ENV"
set +a
K="$HERE/khoa"; [ -d "$K" ] || K="${NEUROEDGE_DEMO_KEYS:-$HOME/neuroedge-demo-khoa}"
K="$(cd "$K" && pwd)"
NAO_HOME="${NAO_HOME:-$HOME/.neuroedge-nao}"
mkdir -p "$NAO_HOME/bin" "$NAO_HOME/workspace"

BIN="${NEUROCLAW_BIN:-$NAO_HOME/bin/neuroclaw}"
if [ ! -x "$BIN" ]; then
  case "$(uname -s)/$(uname -m)" in
    Linux/x86_64) ASSET=neuroclaw_Linux_x86_64 ;;
    Linux/aarch64|Linux/arm64) ASSET=neuroclaw_Linux_arm64 ;;
    Darwin/arm64) ASSET=neuroclaw_Darwin_arm64 ;;
    Darwin/x86_64) ASSET=neuroclaw_Darwin_x86_64 ;;
    *) echo "no NeuroClaw build for $(uname -s)/$(uname -m)" >&2; exit 1 ;;
  esac
  URL="https://github.com/letrongminh/neuroclaw/releases/download/$VERSION"
  TMP="$(mktemp -d)"
  curl -fsSL -o "$TMP/$ASSET.tar.gz" "$URL/$ASSET.tar.gz"
  curl -fsSL -o "$TMP/sums.txt" "$URL/neuroclaw_${VERSION#v}_checksums.txt"
  # the downloaded file must match the release checksums
  WANT="$(awk -v f="$ASSET.tar.gz" '$2 == f {print $1}' "$TMP/sums.txt")"
  GOT="$( (sha256sum "$TMP/$ASSET.tar.gz" 2>/dev/null || shasum -a 256 "$TMP/$ASSET.tar.gz") | cut -d' ' -f1)"
  [ -n "$WANT" ] && [ "$WANT" = "$GOT" ] || { echo "checksum of $ASSET.tar.gz does not match" >&2; exit 1; }
  tar xzf "$TMP/$ASSET.tar.gz" -C "$NAO_HOME/bin" neuroclaw
  rm -rf "$TMP"
fi

# config: the copy in the repo + the box address, mTLS keys, token, owner, LLM key, bot and workspace.
# Secrets go into the brain's config.json (mode 600, outside the repo).
python3 - "$HERE/neuroclaw/config.json" "$NAO_HOME" "$K" "$TARGET" <<'EOF'
import json, os, sys
source, home, keys, target = sys.argv[1:]
config = json.load(open(source))
config["agents"]["defaults"]["workspace"] = os.path.join(home, "workspace")
telegram = config["channel_list"]["telegram"]
telegram["allow_from"] = [os.environ["TELEGRAM_OWNER_ID"]]
telegram.setdefault("settings", {})["token"] = os.environ["TELEGRAM_BOT_TOKEN"]
for model in config["model_list"]:
    model["api_keys"] = [os.environ["OPENROUTER_API_KEY"]]
box = config["tools"]["mcp"]["servers"]["neuroedge"]
box["url"] = f"https://{target}/mcp"
box["headers"]["Authorization"] = "Bearer " + open(os.path.join(keys, "nao.token")).read().strip()
for field, name in (("ca_file", "ca.pem"), ("cert_file", "nao.pem"), ("key_file", "nao.key")):
    box["tls"][field] = os.path.join(keys, name)
path = os.path.join(home, "config.json")
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, "w") as f:
    json.dump(config, f, indent=2, ensure_ascii=False)
os.chmod(path, 0o600)
EOF

export NEUROCLAW_HOME="$NAO_HOME" NEUROCLAW_CONFIG="$NAO_HOME/config.json"
if [ $# -eq 0 ]; then set -- gateway; fi
exec "$BIN" "$@"
