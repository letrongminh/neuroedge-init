#!/usr/bin/env bash
#
# demo/i3-firmware-qemu/run.sh
#
# Firmware demo on Espressif QEMU without a physical board (Task A2, TSK-I3-01, TSK-S6-01..04).
# Mirrors .github/workflows/firmware-qemu.yml and ci-sim-linux.yml (job ui-golden).
#
# Usage:
#   ./demo/i3-firmware-qemu/run.sh ui
#   ./demo/i3-firmware-qemu/run.sh boot
#   ./demo/i3-firmware-qemu/run.sh agent
#   ./demo/i3-firmware-qemu/run.sh ota
#   ./demo/i3-firmware-qemu/run.sh all
#
set -euo pipefail

# 0. Enforce running from repo root
if [ ! -f "targets/esp32s3/CMakeLists.txt" ]; then
    echo "error: run this script from the repository root (e.g. ./demo/i3-firmware-qemu/run.sh <subcommand>)" >&2
    exit 1
fi

DOCKER_IMAGE="espressif/idf:v5.4"
CCACHE_VOLUME="neuroedge-ccache"
VENV_VOLUME="neuroedge-demo-venv"

run_docker() {
    local script="$1"
    docker run --rm \
        -v "$PWD":/work \
        -w /work \
        -v "$CCACHE_VOLUME":/root/.ccache \
        -e IDF_CCACHE_ENABLE=1 \
        -v "$VENV_VOLUME":/opt/neuroedge \
        "$DOCKER_IMAGE" \
        bash -c "$script"
}

usage() {
    cat <<'EOF'
Usage: ./demo/i3-firmware-qemu/run.sh <subcommand>

Subcommands:
  ui     Run LVGL device UI golden comparison (66 screens in vi and en)
  boot   Build base firmware, boot on QEMU, self-test gate, and verify canonical traces
  agent  Build and boot a user agent into firmware on QEMU, self-test, and record traces
  ota    Run signed A/B OTA update and rollback test on QEMU (phases a-g)
  all    Run ui, boot, agent, ota in order

Requirements:
  - Docker running on the host (Apple Silicon Mac or Linux x86_64/arm64)
  - Image espressif/idf:v5.4 (pulled automatically or via docker pull)
EOF
}

cmd_ui() {
    echo "==> Màn 1: So sánh ảnh golden giao diện thiết bị LVGL (66 ảnh vi/en)..."
    if run_docker '
        set -euo pipefail
        git config --global --add safe.directory "*"
        . "$IDF_PATH/export.sh"
        bash scripts/run_ui_golden.sh
    '; then
        echo "✓ ui: 66 ảnh golden khớp hoàn toàn (vi và en)"
    else
        echo "✗ ui: so sánh ảnh golden thất bại" >&2
        return 1
    fi
}

cmd_boot() {
    echo "==> Màn 2: Con chip boot trên Espressif QEMU và tự kiểm gate..."
    if run_docker '
        set -euo pipefail
        git config --global --add safe.directory "*"
        . "$IDF_PATH/export.sh"

        echo "--- 1. Cấu hình và biên dịch firmware cơ sở với sdkconfig.qemu"
        cd targets/esp32s3
        idf.py -D SDKCONFIG_DEFAULTS="sdkconfig.defaults;sdkconfig.qemu" set-target esp32s3
        idf.py build
        grep -q "^CONFIG_NEUROEDGE_SKIP_NETWORK=y" sdkconfig
        grep -q "^CONFIG_NEUROEDGE_QEMU=y" sdkconfig
        grep -q "^CONFIG_NEUROEDGE_REPLAY_VECTORS=y" sdkconfig
        cd ../..

        echo "--- 2. Cài đặt Espressif QEMU"
        python "$IDF_PATH/tools/idf_tools.py" install qemu-xtensa
        . "$IDF_PATH/export.sh"

        echo "--- 3. Khởi động trên QEMU và đọc UART (120 s)"
        scripts/qemu_boot.sh targets/esp32s3/build 120

        echo "--- 4. Thiết lập môi trường Python venv trong container (/opt/neuroedge)"
        if [ ! -x /opt/neuroedge/bin/neuroedge ]; then
            python3 -m venv /opt/neuroedge
            /opt/neuroedge/bin/python -m pip install --upgrade pip
        fi
        /opt/neuroedge/bin/python -m pip install ./python
        export PATH="/opt/neuroedge/bin:$PATH"

        echo "--- 5. Ghi lại vết UART (record) và đối chiếu với golden reference (verify)"
        rm -rf /tmp/demo-boot-traces
        mkdir -p /tmp/demo-boot-traces
        neuroedge record --target esp32s3 --port targets/esp32s3/build/uart.log --out /tmp/demo-boot-traces
        neuroedge trace validate /tmp/demo-boot-traces/*.json
        neuroedge verify --targets esp32s3 --port targets/esp32s3/build/uart.log
    '; then
        echo "✓ boot: firmware boot thành công trên QEMU, self-test đạt và verify khớp 3 vết ghi chuẩn mực"
    else
        echo "✗ boot: kiểm tra boot trên QEMU thất bại" >&2
        return 1
    fi
}

cmd_agent() {
    echo "==> Màn 3: Agent của người dùng được sinh thành firmware và boot trên QEMU..."
    if run_docker '
        set -euo pipefail
        git config --global --add safe.directory "*"
        . "$IDF_PATH/export.sh"

        echo "--- 1. Thiết lập neuroedge trong container (/opt/neuroedge)"
        if [ ! -x /opt/neuroedge/bin/neuroedge ]; then
            python3 -m venv /opt/neuroedge
            /opt/neuroedge/bin/python -m pip install --upgrade pip
        fi
        /opt/neuroedge/bin/python -m pip install ./python
        export PATH="/opt/neuroedge/bin:$PATH"

        SCRATCH_DIR="/tmp/demo-agent-scratch"
        rm -rf "$SCRATCH_DIR"
        mkdir -p "$SCRATCH_DIR"
        cd "$SCRATCH_DIR"

        echo "--- 2. Tạo agent mới: neuroedge new demo-agent"
        neuroedge new demo-agent
        cd demo-agent

        echo "--- 3. Sinh firmware ESP-IDF: neuroedge build --target esp32s3 --board esp32s3-box-3"
        neuroedge build --target esp32s3 --board esp32s3-box-3

        echo "--- 4. Cấu hình và biên dịch firmware của agent với sdkconfig.qemu"
        cd build/esp32s3
        idf.py -D SDKCONFIG_DEFAULTS="sdkconfig.defaults;sdkconfig.qemu" set-target esp32s3
        idf.py build
        grep -q "^CONFIG_NEUROEDGE_QEMU=y" sdkconfig

        echo "--- 5. Cài đặt Espressif QEMU"
        python "$IDF_PATH/tools/idf_tools.py" install qemu-xtensa
        . "$IDF_PATH/export.sh"

        echo "--- 6. Khởi động firmware của agent trên QEMU (120 s)"
        target_build="$SCRATCH_DIR/demo-agent/build/esp32s3/build"
        bash /work/scripts/qemu_boot.sh "$target_build" 120
        log="$target_build/uart.log"

        echo "--- 7. Kiểm tra dòng phán quyết self-test (NE_SELFTEST PASS)"
        line="$(grep -oE "^NE_SELFTEST PASS walker=[0-9]+ token=[0-9]+" "$log" | head -n1)"
        walker="$(echo "$line" | sed -E "s/.*walker=([0-9]+).*/\1/")"
        if [ "${walker:-0}" -lt 1 ]; then
            echo "::error::the self-test checked no gate: $line" >&2
            exit 1
        fi
        echo "$line"

        echo "--- 8. Ghi lại vết UART (record) và thẩm định phiên"
        neuroedge record --target esp32s3 --port "$log" --out "$SCRATCH_DIR/agent-traces/"
        neuroedge trace validate "$SCRATCH_DIR/agent-traces/"*.json
    '; then
        echo "✓ agent: agent demo-agent được sinh firmware, boot trên QEMU và vượt qua self-test"
    else
        echo "✗ agent: build hoặc boot agent trên QEMU thất bại" >&2
        return 1
    fi
}

cmd_ota() {
    echo "==> Màn 4: Cập nhật OTA có chữ ký và tự rollback trên QEMU (pha a–g)..."
    if run_docker '
        set -euo pipefail
        git config --global --add safe.directory "*"
        . "$IDF_PATH/export.sh"

        echo "--- 1. Cài đặt Espressif QEMU"
        python "$IDF_PATH/tools/idf_tools.py" install qemu-xtensa
        . "$IDF_PATH/export.sh"

        echo "--- 2. Chạy toàn bộ kịch bản OTA đầu-cuối (scripts/qemu_ota.sh)"
        scripts/qemu_ota.sh
    '; then
        echo "✓ ota: toàn bộ các pha cập nhật OTA và rollback (a–g) đạt yêu cầu trên QEMU"
    else
        echo "✗ ota: kiểm tra OTA trên QEMU thất bại" >&2
        return 1
    fi
}

cmd_all() {
    echo "==> Bắt đầu chạy toàn bộ các màn demo firmware không cần bo mạch (ui, boot, agent, ota)..."
    cmd_ui
    echo ""
    cmd_boot
    echo ""
    cmd_agent
    echo ""
    cmd_ota
    echo ""
    echo "✓ all: toàn bộ các màn demo firmware đã hoàn thành thành công"
}

case "${1:-}" in
    ui)
        cmd_ui
        ;;
    boot)
        cmd_boot
        ;;
    agent)
        cmd_agent
        ;;
    ota)
        cmd_ota
        ;;
    all)
        cmd_all
        ;;
    -h|--help|help)
        usage
        exit 0
        ;;
    "")
        usage
        exit 1
        ;;
    *)
        echo "error: unknown subcommand '$1'" >&2
        usage
        exit 1
        ;;
esac
