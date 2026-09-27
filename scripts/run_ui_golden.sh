#!/usr/bin/env bash
#
# Build the device UI host harness and compare every screen x language with its
# golden image (TSK-S4-10, FR-CI-05). The CI job `ui-golden`
# (.github/workflows/ci-sim-linux.yml) runs exactly this script; run it locally
# the same way:
#
#     bash scripts/run_ui_golden.sh            # verify; never writes a golden
#     bash scripts/run_ui_golden.sh --update   # rewrite goldens, then verify
#
# Verify mode copies targets/esp32s3/ui/golden/ into the build directory and
# runs there: a difference leaves <case>_err.png in the build directory, and the
# committed goldens are never written outside --update. Exit status is non-zero
# if any screen differs, any golden is missing, or the harness cannot build.
#
# cmake is found in PATH, in python/.venv/bin (pip install cmake), or through
# NE_UI_CMAKE; without one, the script re-runs itself in the espressif/idf:v5.4
# container, which has cmake 3.30. LVGL v9.6.0 is fetched by the CMake project,
# pinned by URL and SHA-256. The runner is built with ASan+UBSan
# (NE_UI_SANITIZE=ON): the UI handles untrusted agent text, so a read past a
# buffer must fail here. LVGL is never deinitialised in this harness, so leak
# detection is off.
set -euo pipefail

export ASAN_OPTIONS="${ASAN_OPTIONS:-detect_leaks=0:abort_on_error=1}"
export UBSAN_OPTIONS="${UBSAN_OPTIONS:-print_stacktrace=1}"

ROOT=$(cd "$(dirname "$0")/.." && pwd)
HOST="$ROOT/targets/esp32s3/ui/host"
UI="$ROOT/targets/esp32s3/ui"
GOLDEN="$UI/golden"
BUILD="${NE_UI_BUILD_DIR:-$HOST/build}"

UPDATE=0
for arg in "$@"; do
    case "$arg" in
        --update) UPDATE=1 ;;
        *)
            echo "usage: $0 [--update]" >&2
            exit 2
            ;;
    esac
done

find_cmake() {
    if [ -n "${NE_UI_CMAKE:-}" ]; then
        printf '%s' "$NE_UI_CMAKE"
        return 0
    fi
    if command -v cmake >/dev/null 2>&1; then
        command -v cmake
        return 0
    fi
    if [ -x "$ROOT/python/.venv/bin/cmake" ]; then
        printf '%s' "$ROOT/python/.venv/bin/cmake"
        return 0
    fi
    return 1
}

if ! CMAKE=$(find_cmake); then
    if command -v docker >/dev/null 2>&1; then
        echo "cmake not found: building in espressif/idf:v5.4 (first run pulls the image)"
        exec docker run --rm -v "$ROOT":/work -w /work espressif/idf:v5.4 \
            bash /work/scripts/run_ui_golden.sh "$@"
    fi
    echo "error: cmake is not installed and docker is not available" >&2
    echo "  pip install cmake        (then: python/.venv/bin/cmake, or put it in PATH)" >&2
    echo "  apt-get install cmake    (Debian/Ubuntu)" >&2
    exit 1
fi

configure_and_build() {
    local update="$1"
    local on_off="OFF"
    [ "$update" -eq 1 ] && on_off="ON"
    echo "== cmake: $CMAKE (NE_UI_UPDATE_GOLDEN=$on_off) =="
    "$CMAKE" -S "$HOST" -B "$BUILD" \
        -DCMAKE_BUILD_TYPE=Release \
        -DNE_UI_UPDATE_GOLDEN="$on_off" >/dev/null
    "$CMAKE" --build "$BUILD" --parallel
}

# verify: run in a scratch copy of the goldens, so nothing writes them back.
verify() {
    rm -rf "$BUILD/golden"
    mkdir -p "$BUILD/golden"
    cp -R "$GOLDEN/." "$BUILD/golden/"
    echo "== comparing ${GOLDEN} =="
    (cd "$BUILD" && ./ne_ui_golden)
    local errors
    errors=$(find "$BUILD/golden" -name '*_err.png' | sort)
    if [ -n "$errors" ]; then
        echo "differences rendered next to the reference copy:"
        printf '  %s\n' $errors
    fi
}

if [ "$UPDATE" -eq 1 ]; then
    echo "== rewriting $GOLDEN =="
    # The harness writes through LVGL's FS layer into ./golden; a scratch
    # directory keeps it and its <case>_err.png files out of the repository.
    rm -rf "$BUILD/update"
    mkdir -p "$BUILD/update/golden/vi" "$BUILD/update/golden/en"
    configure_and_build 1
    (cd "$BUILD/update" && "$BUILD/ne_ui_golden")
    stale=$(find "$BUILD/update/golden" -name '*_err.png' | sort)
    if [ -n "$stale" ]; then
        echo "error: the update left error images behind: $stale" >&2
        exit 1
    fi
    rm -rf "$GOLDEN"
    mkdir -p "$GOLDEN"
    cp -R "$BUILD/update/golden/." "$GOLDEN/"
    echo "== verifying the rewritten goldens =="
fi

configure_and_build 0
verify
echo "ui-golden: every screen matches its golden"
