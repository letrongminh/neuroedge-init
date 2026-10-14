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
    # In a git worktree `.git` is a file pointing at the main repository's git
    # directory; mount that directory at the same path so git works inside.
    local git_mount=()
    if [ -f .git ]; then
        local common
        common="$(cd "$(git rev-parse --git-common-dir)" && pwd)"
        git_mount=(-v "$common":"$common")
    fi
    docker run --rm \
        -v "$PWD":/work \
        ${git_mount[@]+"${git_mount[@]}"} \
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
    echo "==> Screen 1: Compare the golden screenshots of the LVGL device UI (66 images, vi/en)..."
    if run_docker '
        set -euo pipefail
        git config --global --add safe.directory "*"
        . "$IDF_PATH/export.sh"
        bash scripts/run_ui_golden.sh
    '; then
        echo "✓ ui: all 66 golden screenshots match (vi and en)"
    else
        echo "✗ ui: golden screenshot comparison failed" >&2
        return 1
    fi
}

cmd_boot() {
    echo "==> Screen 2: The chip boots on Espressif QEMU and self-tests the gate..."
    if run_docker '
        set -euo pipefail
        git config --global --add safe.directory "*"
        . "$IDF_PATH/export.sh"

        echo "--- 1. Configure and build the base firmware with sdkconfig.qemu"
        cd targets/esp32s3
        idf.py -D SDKCONFIG_DEFAULTS="sdkconfig.defaults;sdkconfig.qemu" set-target esp32s3
        idf.py build
        grep -q "^CONFIG_NEUROEDGE_SKIP_NETWORK=y" sdkconfig
        grep -q "^CONFIG_NEUROEDGE_QEMU=y" sdkconfig
        grep -q "^CONFIG_NEUROEDGE_REPLAY_VECTORS=y" sdkconfig
        cd ../..

        echo "--- 2. Install Espressif QEMU"
        python "$IDF_PATH/tools/idf_tools.py" install qemu-xtensa
        . "$IDF_PATH/export.sh"

        echo "--- 3. Boot on QEMU and read the UART (120 s)"
        scripts/qemu_boot.sh targets/esp32s3/build 120

        echo "--- 4. Set up the Python venv in the container (/opt/neuroedge)"
        if [ ! -x /opt/neuroedge/bin/neuroedge ]; then
            python3 -m venv /opt/neuroedge
            /opt/neuroedge/bin/python -m pip install --upgrade pip
        fi
        /opt/neuroedge/bin/python -m pip install ./python
        # Absolute path, never PATH: idf.py must keep running on the ESP-IDF python.
        NE=/opt/neuroedge/bin/neuroedge

        echo "--- 5. Record the UART trace (record) and check it against the golden reference (verify)"
        rm -rf /tmp/demo-boot-traces
        mkdir -p /tmp/demo-boot-traces
        "$NE" record --target esp32s3 --port targets/esp32s3/build/uart.log --out /tmp/demo-boot-traces
        "$NE" trace validate /tmp/demo-boot-traces/*.json
        "$NE" verify --targets esp32s3 --port targets/esp32s3/build/uart.log
    '; then
        echo "✓ boot: firmware booted on QEMU, the self-test passed and verify matched the 3 normative traces"
    else
        echo "✗ boot: the boot check on QEMU failed" >&2
        return 1
    fi
}

cmd_agent() {
    echo "==> Screen 3: A user's agent is generated into firmware and boots on QEMU..."
    if run_docker '
        set -euo pipefail
        git config --global --add safe.directory "*"
        . "$IDF_PATH/export.sh"

        echo "--- 1. Set up neuroedge in the container (/opt/neuroedge)"
        if [ ! -x /opt/neuroedge/bin/neuroedge ]; then
            python3 -m venv /opt/neuroedge
            /opt/neuroedge/bin/python -m pip install --upgrade pip
        fi
        /opt/neuroedge/bin/python -m pip install ./python
        # Absolute path, never PATH: idf.py must keep running on the ESP-IDF python.
        NE=/opt/neuroedge/bin/neuroedge

        SCRATCH_DIR="/tmp/demo-agent-scratch"
        rm -rf "$SCRATCH_DIR"
        mkdir -p "$SCRATCH_DIR"
        cd "$SCRATCH_DIR"

        echo "--- 2. Create a new agent: neuroedge new demo-agent"
        "$NE" new demo-agent
        cd demo-agent

        echo "--- 3. Sinh firmware ESP-IDF: neuroedge build --target esp32s3 --board esp32s3-box-3"
        "$NE" build --target esp32s3 --board esp32s3-box-3

        echo "--- 4. Configure and build the agent firmware with sdkconfig.qemu"
        cd build/esp32s3
        idf.py -D SDKCONFIG_DEFAULTS="sdkconfig.defaults;sdkconfig.qemu" set-target esp32s3
        idf.py build
        grep -q "^CONFIG_NEUROEDGE_QEMU=y" sdkconfig

        echo "--- 5. Install Espressif QEMU"
        python "$IDF_PATH/tools/idf_tools.py" install qemu-xtensa
        . "$IDF_PATH/export.sh"

        echo "--- 6. Boot the agent firmware on QEMU (120 s)"
        target_build="$SCRATCH_DIR/demo-agent/build/esp32s3/build"
        bash /work/scripts/qemu_boot.sh "$target_build" 120
        log="$target_build/uart.log"

        echo "--- 7. Check the self-test verdict line (NE_SELFTEST PASS)"
        line="$(grep -oE "^NE_SELFTEST PASS walker=[0-9]+ token=[0-9]+" "$log" | head -n1)"
        walker="$(echo "$line" | sed -E "s/.*walker=([0-9]+).*/\1/")"
        if [ "${walker:-0}" -lt 1 ]; then
            echo "::error::the self-test checked no gate: $line" >&2
            exit 1
        fi
        echo "$line"

        echo "--- 8. Record the UART trace (record) and validate the session"
        "$NE" record --target esp32s3 --port "$log" --out "$SCRATCH_DIR/agent-traces/"
        "$NE" trace validate "$SCRATCH_DIR/agent-traces/"*.json
    '; then
        echo "✓ agent: demo-agent was generated into firmware, booted on QEMU and passed the self-test"
    else
        echo "✗ agent: building or booting the agent on QEMU failed" >&2
        return 1
    fi
}

cmd_ota() {
    echo "==> Screen 4: Signed OTA update and automatic rollback on QEMU (phases a–g)..."
    if run_docker '
        set -euo pipefail
        git config --global --add safe.directory "*"
        . "$IDF_PATH/export.sh"

        echo "--- 1. Install Espressif QEMU"
        python "$IDF_PATH/tools/idf_tools.py" install qemu-xtensa
        . "$IDF_PATH/export.sh"

        echo "--- 2. Run the whole end-to-end OTA scenario (scripts/qemu_ota.sh)"
        scripts/qemu_ota.sh
    '; then
        echo "✓ ota: all OTA update and rollback phases (a–g) passed on QEMU"
    else
        echo "✗ ota: the OTA check on QEMU failed" >&2
        return 1
    fi
}

cmd_all() {
    echo "==> Starting all firmware demo screens that need no board (ui, boot, agent, ota)..."
    cmd_ui
    echo ""
    cmd_boot
    echo ""
    cmd_agent
    echo ""
    cmd_ota
    echo ""
    echo "✓ all: all firmware demo screens completed successfully"
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
