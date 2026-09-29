#!/usr/bin/env bash
set -euo pipefail

# Script chuẩn bị môi trường demo cho increment I1 (sim target).
# Quyết định Q-49: mỗi increment có một demo tái lập được.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

echo "==> NeuroEdge i1-sim: Bắt đầu thiết lập môi trường demo..."

# 1. Tạo môi trường ảo nếu chưa có và cài đặt gói
VENV_DIR="$REPO_ROOT/python/.venv"
if [[ ! -d "$VENV_DIR" ]]; then
  echo "==> Khởi tạo môi trường ảo Python tại $VENV_DIR..."
  python3 -m venv "$VENV_DIR"
fi

NE_PYTHON="$VENV_DIR/bin/python"
NE_BIN="$VENV_DIR/bin/neuroedge"

echo "==> Cài đặt neuroedge với các extra [dev,mcp] (chế độ editable)..."
"$NE_PYTHON" -m pip install -e "$REPO_ROOT/python[dev,mcp]"

# 2. Thiết lập thư mục demo và kiểm tra an toàn
DEMO="${DEMO:-/tmp/neuroedge-demo}"

# Từ chối nếu DEMO không nằm dưới /tmp, hoặc là chính /tmp, /tmp/, hoặc chứa ..
if [[ "$DEMO" != /tmp/* ]] || [[ "$DEMO" == "/tmp" ]] || [[ "$DEMO" == "/tmp/" ]] || [[ "$DEMO" =~ \.\. ]]; then
  echo "Lỗi: DEMO bắt buộc phải nằm dưới thư mục /tmp (đường dẫn: '$DEMO')" >&2
  exit 1
fi

echo "==> Làm sạch và tạo lại thư mục demo tại $DEMO..."
rm -rf "$DEMO"
mkdir -p "$DEMO"

# 3. Khởi tạo 3 dự án mẫu
for tmpl in villa-concierge home-voice factory-monitor; do
  echo "==> Khởi tạo dự án mẫu '$tmpl' bằng template '$tmpl'..."
  (cd "$DEMO" && "$NE_BIN" new "$tmpl" --template "$tmpl")
done

# 4. Kiểm tra gate lint và test trong từng dự án
for tmpl in villa-concierge home-voice factory-monitor; do
  echo "==> Kiểm tra dự án '$tmpl' (gate lint)..."
  (cd "$DEMO/$tmpl" && "$NE_BIN" gate lint)
  echo "==> Kiểm tra dự án '$tmpl' (test)..."
  (cd "$DEMO/$tmpl" && "$NE_BIN" test)
done

echo ""
echo "==> Môi trường demo I1 đã chuẩn bị sẵn sàng tại $DEMO!"
echo "==> Lệnh tiếp theo để chạy demo:"
echo "    cd $DEMO && alias ne=\"$NE_BIN\""
echo "    # Xem hướng dẫn kịch bản tại: $REPO_ROOT/demo/i1-sim/kich-ban.md"
