#!/usr/bin/env bash
set -euo pipefail

# Chuẩn bị demo I4 — nói với agent qua micro laptop (TSK-I4-04, Q-50).
# Tạo agent home-voice trong $DEMO, thêm audio.in và voice.toml (STT, TTS, System 2 qua OpenRouter).

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HERE="$REPO_ROOT/demo/i4-thoai-laptop"
VENV_DIR="$REPO_ROOT/python/.venv"
NE_BIN="$VENV_DIR/bin/neuroedge"
DEMO="${DEMO:-/tmp/neuroedge-demo-voice}"

if [[ "$DEMO" != /tmp/* ]] || [[ "$DEMO" == "/tmp/" ]] || [[ "$DEMO" =~ \.\. ]]; then
  echo "Lỗi: DEMO bắt buộc phải nằm dưới /tmp (đường dẫn: '$DEMO')" >&2
  exit 1
fi

if [[ ! -d "$VENV_DIR" ]]; then
  echo "==> Tạo môi trường ảo Python tại $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi
echo "==> Cài neuroedge với extra [dev,mcp,cloud,audio] (litellm, sounddevice)"
"$VENV_DIR/bin/python" -m pip install -q -e "$REPO_ROOT/python[dev,mcp,cloud,audio]"

echo "==> Tạo lại $DEMO và agent 'nha' từ template home-voice"
rm -rf "$DEMO" && mkdir -p "$DEMO"
(cd "$DEMO" && "$NE_BIN" new nha --template home-voice)

echo "==> Thêm audio.in vào [requires] và nối voice.toml"
"$VENV_DIR/bin/python" - "$DEMO/nha/agent.toml" "$HERE/voice.toml" <<'PY'
import sys
agent, snippet = sys.argv[1], sys.argv[2]
text = open(agent, encoding="utf-8").read()
line = '"audio.out"   = {}\n'
if line not in text:
    sys.exit("agent.toml của template đã đổi: không tìm thấy dòng audio.out trong [requires]")
text = text.replace(line, '"audio.in"    = {}\n' + line, 1)
open(agent, "w", encoding="utf-8").write(text + open(snippet, encoding="utf-8").read())
PY

echo "==> Kiểm gate và build cho sim"
(cd "$DEMO/nha" && "$NE_BIN" gate lint gates && "$NE_BIN" build --target sim --board sim-default >/dev/null)

if [[ -z "${OPENROUTER_API_KEY:-}" ]]; then
  echo "!! Chưa có OPENROUTER_API_KEY trong shell này: export OPENROUTER_API_KEY=… trước khi chạy demo." >&2
fi

echo ""
echo "==> Sẵn sàng. Đeo tai nghe, rồi:"
echo "    cd $DEMO/nha && $NE_BIN run --mic"
echo "    (loa ngoài: thêm --half-duplex)"
