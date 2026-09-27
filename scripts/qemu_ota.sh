#!/usr/bin/env bash
# OTA end-to-end on Espressif QEMU (TSK-S6-01/02/04; FR-OTA-01..04).
# Used by .github/workflows/firmware-qemu.yml job `ota-rollback`.
#
#   scripts/qemu_ota.sh
#
# Needs the ESP-IDF environment (`. $IDF_PATH/export.sh`, v5.4) with
# qemu-xtensa installed — run it in the `espressif/idf:v5.4` container:
#
#   docker run --rm -v "$PWD":/work -w /work espressif/idf:v5.4 \
#     bash -c '. $IDF_PATH/export.sh && scripts/qemu_ota.sh'
#
# It builds four images of the firmware (the same sources; the app version and
# a test-only flag differ), signs them with throwaway RSA-3072 keys made under
# targets/esp32s3/build/ (git-ignored; real keys never belong in the
# repository), serves them over HTTP from the host QEMU reaches at 10.0.2.2
# and drives the whole story with scripts/ota_markers.sh. Each boot is its own
# QEMU process: QEMU 9.0's esp32s3 flash model cannot survive a warm reset
# after an update's flash writes, so the emulator — not the firmware — is
# restarted wherever the device resets itself; the UART logs still read as one
# continuous story:
#
#   a  factory 0.1.0 boots, self-test passes, the remote is already running
#      (SKIP same_version) — a failed update could never have lost this slot;
#   b  0.2.0 is fetched, verified, switched to and marked VALID after its own
#      self-test (the NVS high-water mark);
#   c  an image signed with a different key is REJECTED before boot: no
#      switch, no reboot, the device stays on 0.2.0, and the slot it wrote is
#      erased so it can never be fallen back to (NE_OTA ERASED);
#   d  a broken signed image (resets before it can be marked valid) is rolled
#      back by the bootloader; the device runs 0.2.0 again by itself;
#   e  an image whose self-test fails marks itself INVALID and reboots into
#      the previous app (NEUROEDGE_OTA_TEST_FAIL_SELFTEST);
#   f  an unsigned image (no signature block) is REJECTED reason=signature;
#   g  a correctly signed but lower version is refused as a downgrade
#      (SKIP reason=downgrade) by the high-water mark from boot b.
#
# Any missing marker, wrong order, marker that must not appear, unexpected
# QEMU exit or timeout is exit 1. The QEMU UART logs and the HTTP server log
# stay under targets/esp32s3/build/ota-test/logs/.
set -euo pipefail

project=$(cd "$(dirname "$0")/../targets/esp32s3" && pwd)
repo=$(cd "$(dirname "$0")/.." && pwd)
work=${NEUROEDGE_OTA_WORK:-"$project/build/ota-test"}
timeout_s=${NEUROEDGE_OTA_TIMEOUT:-240}
port=8070

source "$repo/scripts/ota_markers.sh"

logs="$work/logs"
images="$work/images"
serve="$work/serve"
flash="$work/a/flash.bin"

say() { printf '  %s\n' "$*"; }
fail() {
  printf '::error::%s\n' "$*" >&2
  exit 1
}

cleanup() {
  if [ -n "${qemu_pid:-}" ] && kill -0 "$qemu_pid" 2>/dev/null; then
    kill "$qemu_pid" 2>/dev/null || true
    wait "$qemu_pid" 2>/dev/null || true
  fi
  if [ -n "${server_pid:-}" ] && kill -0 "$server_pid" 2>/dev/null; then
    kill "$server_pid" 2>/dev/null || true
    wait "$server_pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT

for tool in idf.py esptool.py espsecure.py qemu-system-xtensa; do
  command -v "$tool" >/dev/null 2>&1 || fail "$tool not found: run inside espressif/idf:v5.4 with $IDF_PATH/export.sh sourced"
done

# Never remove anything outside the build tree this script owns.
case "$work" in
  "$project"/build/*) ;;
  *) fail "refusing to work outside $project/build: NEUROEDGE_OTA_WORK=$work" ;;
esac
rm -rf -- "$work"
mkdir -p "$logs" "$images" "$serve"

# --- build and sign ----------------------------------------------------------------------------

app_bin() { # the app binary of a build (flash_args names it; it is not always app.bin)
  awk '$1 == "0x10000" { print $2; exit }' "$1/flash_args"
}

build_variant() { # <name> <version> <sdkconfig defaults> [extra layer ...]
  local name=$1 version=$2 defaults=$3
  shift 3
  local build="$work/$name" config="$work/sdkconfig.$name"
  local layer
  for layer in "$@"; do
    defaults="$defaults;$layer"
  done
  say "build $name (version $version)"
  {
    if [ -f "$build/CMakeCache.txt" ]; then
      # Same project, another app version (PROJECT_VER is a CMake variable, not
      # sdkconfig): reconfigure — set-target would fullclean the shared cache.
      idf.py -C "$project" -B "$build" -D SDKCONFIG="$config" -D SDKCONFIG_DEFAULTS="$defaults" \
        -D PROJECT_VER="$version" reconfigure
    else
      idf.py -C "$project" -B "$build" -D SDKCONFIG="$config" -D SDKCONFIG_DEFAULTS="$defaults" \
        -D PROJECT_VER="$version" set-target esp32s3
    fi
    # Every -D on every call: the config chain must never fall back to the
    # project's own sdkconfig (a rebuild once lost SPIRAM_IGNORE_NOTFOUND that
    # way, and the emulator then aborted on the missing PSRAM).
    idf.py -C "$project" -B "$build" -D SDKCONFIG="$config" -D SDKCONFIG_DEFAULTS="$defaults" \
      -D PROJECT_VER="$version" build
  } >"$logs/build.$name.log" 2>&1 || {
    tail -n 30 "$logs/build.$name.log"
    fail "build $name failed (full log: $logs/build.$name.log)"
  }
}

sign_image() { # <key> <in> <out>
  espsecure.py sign_data --version 2 --keyfile "$1" -o "$3" "$2" >/dev/null 2>&1 ||
    fail "could not sign $2 with $1"
}

size_check() { # <name> <build> <image>
  local name=$1 build=$2 image=$3
  idf.py -C "$project" -B "$build" size --format json2 --output-file "$build/size.json" \
    >/dev/null 2>&1 || fail "idf.py size failed for $name"
  python3 "$repo/scripts/check_firmware_size.py" "$image" --size-json "$build/size.json" ||
    fail "$name does not fit the Q-3 flash budget"
}

defaults="sdkconfig.defaults;sdkconfig.qemu;sdkconfig.ota;sdkconfig.qemu_ota"
espsecure.py generate_signing_key --version 2 --scheme rsa3072 "$work/key-a.pem" >/dev/null
espsecure.py generate_signing_key --version 2 --scheme rsa3072 "$work/key-b.pem" >/dev/null

build_variant a 0.1.0 "$defaults"
sign_image "$work/key-a.pem" "$work/a/$(app_bin "$work/a")" "$images/a.bin"
cp -f "$images/a.bin" "$work/a/$(app_bin "$work/a")"
(cd "$work/a" && esptool.py --chip esp32s3 merge_bin --fill-flash-size 16MB -o flash.bin @flash_args) \
  >/dev/null 2>&1 || fail "could not merge the flash image"
size_check "qemu OTA build" "$work/a" "$images/a.bin"

build_variant a 0.2.0 "$defaults"
sign_image "$work/key-a.pem" "$work/a/$(app_bin "$work/a")" "$images/b.bin"

printf 'CONFIG_NEUROEDGE_OTA_TEST_BOOTLOOP=y\n' >"$work/sdkconfig.bootloop"
build_variant c 0.3.0 "$defaults" "$work/sdkconfig.bootloop"
cp -f "$work/c/$(app_bin "$work/c")" "$images/c-unsigned.bin"
sign_image "$work/key-a.pem" "$work/c/$(app_bin "$work/c")" "$images/c-good.bin"
sign_image "$work/key-b.pem" "$work/c/$(app_bin "$work/c")" "$images/c-bad.bin"

printf 'CONFIG_NEUROEDGE_OTA_TEST_FAIL_SELFTEST=y\n' >"$work/sdkconfig.fail"
build_variant c2 0.3.1 "$defaults" "$work/sdkconfig.fail"
sign_image "$work/key-a.pem" "$work/c2/$(app_bin "$work/c2")" "$images/c2.bin"

# The board OTA image (Wi-Fi linked, no QEMU layer) is the one that ships: check
# it fits an A/B slot with room for the Q-3 floor. The key is a throwaway, like
# the others.
printf 'CONFIG_SECURE_BOOT_SIGNING_KEY="build/ota-test/board-key.pem"\n' >"$work/sdkconfig.board-key"
espsecure.py generate_signing_key --version 2 --scheme rsa3072 "$work/board-key.pem" >/dev/null
build_variant board 0.1.0 "sdkconfig.defaults;sdkconfig.ota" "$work/sdkconfig.board-key"
size_check "board OTA build" "$work/board" "$work/board/$(app_bin "$work/board")"

# --- the HTTP endpoint --------------------------------------------------------------------------

cp -f "$images/a.bin" "$serve/app.bin"
python3 -m http.server "$port" --directory "$serve" --bind 127.0.0.1 >"$logs/http.log" 2>&1 &
server_pid=$!
sleep 1
kill -0 "$server_pid" 2>/dev/null || fail "the HTTP server did not start on 127.0.0.1:$port"

# --- QEMU ----------------------------------------------------------------------------------------
# One boot per process. QEMU 9.0's esp32s3 model cannot survive a warm reset
# after the flash writes of an update (its flash state corrupts and the process
# segfaults on a later boot), and its panic handler hangs instead of printing;
# so the emulator is stopped right after the device asks for a reset (its ROM
# `rst:` line) and started again. The UART log is one file per phase, joined
# across the boots, so the ordered verdict still reads one continuous story.
# The board does not restart the emulator: this is a QEMU workaround
# (docs/spec/simulation_coverage.md §4).

start_qemu() { # <log> [extra qemu args ...]
  local log=$1
  shift
  qemu-system-xtensa -machine esp32s3 -display none -monitor none \
    -drive "file=$flash,if=mtd,format=raw" \
    -nic user,model=open_eth \
    -serial "file:$log" "$@" &
  qemu_pid=$!
}

# A terminated child stays a zombie until `wait`, and `kill -0` cannot tell a
# zombie from a live process; the job list can.
qemu_alive() {
  jobs -pr | grep -qx "${qemu_pid:-none}"
}

stop_qemu() {
  if [ -n "${qemu_pid:-}" ] && qemu_alive; then
    kill "$qemu_pid" 2>/dev/null || true
  fi
  wait "$qemu_pid" 2>/dev/null || true
  qemu_pid=
}

# One boot, one UART log ($logs/<phase>-<n>.log). mode `exit`: the device is
# expected to reset itself — the marker must appear, then the ROM's `rst:` line
# of the reset, and QEMU is stopped right after it (a clean SIGTERM flushes the
# flash writes; `-no-reboot`'s exit path loses them, which once made a pending
# image boot twice). mode `idle`: a settle window, then stop.
qemu_once() { # <phase> <n> <regex> <exit|idle> [grace]
  local phase=$1 n=$2 pattern=$3 mode=$4 grace=${5:-4}
  local log="$logs/$phase-$n.log"
  local deadline=$((SECONDS + timeout_s))
  say "phase $phase.$n: waiting for /$pattern/ ($mode)"
  : >"$log"
  start_qemu "$log"
  while :; do
    if [ "$(ota_first "$log" "$pattern")" != 0 ]; then
      if [ "$mode" = exit ]; then
        local reset_deadline=$((SECONDS + 30))
        # The probe is expected to fail until the reset; keep it quiet.
        while ! ota_has_after "$log" "$pattern" '^rst:0[xX]' 2>/dev/null; do
          if ! qemu_alive; then
            wait "$qemu_pid" 2>/dev/null || true
            qemu_pid=
            # An emulator that died is not the reset the device asked for.
            fail "$phase.$n: QEMU exited without the device's reset line (log: $log)"
          fi
          [ "$SECONDS" -lt "$reset_deadline" ] ||
            fail "$phase.$n: no reset after /$pattern/ (log: $log)"
          sleep 0.02
        done
      else
        sleep "$grace"
      fi
      stop_qemu
      return 0
    fi
    if ! qemu_alive; then
      wait "$qemu_pid" 2>/dev/null || true
      qemu_pid=
      fail "$phase.$n: QEMU exited before /$pattern/ (log: $log)"
    fi
    if [ "$SECONDS" -ge "$deadline" ]; then
      fail "$phase.$n: no /$pattern/ within ${timeout_s}s (log: $log)"
    fi
    sleep 0.02
  done
}

# The boots of one phase, in order, as one log for the ordered verdict.
join_boots() { # <phase>
  cat "$logs/$1"-*.log >"$logs/$1.log"
}

serve() { # <image>
  cp -f "$1" "$serve/app.bin"
  say "serving $(basename "$1")"
}

assert() { # run one ota_* helper, naming the phase on failure
  local phase=$1
  shift
  "$@" || fail "$phase: $(tail -n 5 "$logs/$phase.log" | tr -d '\r' | tr '\n' ' ')"
}

URL='http://10\.0\.2\.2:8070/app\.bin'

# (a) the factory image boots, passes its self-test, and the remote is the
# version it already runs: nothing is fetched, and the running slot is safe.
serve "$images/a.bin"
qemu_once a 1 '^NE_OTA SKIP reason=same_version version=0\.1\.0$' idle
join_boots a
assert a ota_ordered "$logs/a.log" \
  '^NE_SELFTEST PASS walker=[0-9]+ token=[0-9]+' \
  '^NE_TRACE DONE sessions=[0-9]+' \
  "^NE_OTA CHECK url=$URL\$" \
  '^NE_OTA SKIP reason=same_version version=0\.1\.0$'
assert a ota_forbid "$logs/a.log" '^NE_OTA (SWITCH|ROLLBACK|REJECTED|DOWNLOADED)'
assert a ota_count_is "$logs/a.log" '^NE_SELFTEST PASS' 1

# (b) a signed newer image is fetched and switched to; on its first boot it
# passes the gate self-test and is marked VALID (its own boot, fresh process).
serve "$images/b.bin"
qemu_once b 1 '^NE_OTA SWITCH partition=ota_0$' idle 0
qemu_once b 2 '^NE_OTA SKIP reason=same_version version=0\.2\.0$' idle
join_boots b
assert b ota_ordered "$logs/b.log" \
  "^NE_OTA CHECK url=$URL\$" \
  '^NE_OTA DOWNLOADED bytes=[1-9][0-9]* version=0\.2\.0$' \
  '^NE_OTA SWITCH partition=ota_0$' \
  '^NE_SELFTEST PASS walker=[0-9]+ token=[0-9]+' \
  '^NE_OTA VALID partition=ota_0$' \
  '^NE_OTA SKIP reason=same_version version=0\.2\.0$'
assert b ota_forbid "$logs/b.log" '^NE_OTA (REJECTED|ROLLBACK)'
assert b ota_count_is "$logs/b.log" '^NE_SELFTEST PASS' 2

# (c) an image signed with a different key is refused before anything is
# switched: no SWITCH, no reboot, the device stays on 0.2.0.
serve "$images/c-bad.bin"
qemu_once c 1 '^NE_OTA REJECTED reason=signature$' idle 10
join_boots c
assert c ota_ordered "$logs/c.log" \
  '^NE_SELFTEST PASS walker=[0-9]+ token=[0-9]+' \
  "^NE_OTA CHECK url=$URL\$" \
  '^NE_OTA REJECTED reason=signature$'
assert c ota_forbid "$logs/c.log" '^NE_OTA (DOWNLOADED|SWITCH|VALID|ROLLBACK)'
assert c ota_count_is "$logs/c.log" '^NE_SELFTEST PASS' 1
# The device must still be on B: nothing after the refusal but idle.
assert c ota_nothing_after "$logs/c.log" '^NE_OTA REJECTED reason=signature$' '^NE_SELFTEST PASS'

# (d) a broken signed image resets itself before it can be marked valid
# (FR-OTA-02, the crash/boot-loop path); the bootloader abandons it and rolls
# back to 0.2.0. Boot 3 is the one where the bootloader marks the broken slot
# ABORTED; QEMU's flash cache does not show that write to the app in the same
# process, and the app would fetch the broken image again — so boot 3 is
# stopped at the self-test line, before it reaches the network, and boot 4 (a
# fresh process, fresh cache) reads the rollback and refuses that version.
serve "$images/c-good.bin"
qemu_once d 1 '^NE_OTA SWITCH partition=ota_1$' idle 0
qemu_once d 2 '^NE_OTA TEST BOOTLOOP$' exit
qemu_once d 3 '^NE_SELFTEST PASS walker=[0-9]+ token=[0-9]+$' idle 0
qemu_once d 4 '^NE_OTA SKIP reason=rolled_back version=0\.3\.0$' idle
join_boots d
assert d ota_ordered "$logs/d.log" \
  "^NE_OTA CHECK url=$URL\$" \
  '^NE_OTA DOWNLOADED bytes=[1-9][0-9]* version=0\.3\.0$' \
  '^NE_OTA SWITCH partition=ota_1$' \
  '^NE_OTA TEST BOOTLOOP$' \
  '^NE_OTA ROLLBACK from=ota_1 to=ota_0$' \
  '^NE_SELFTEST PASS walker=[0-9]+ token=[0-9]+' \
  '^NE_OTA SKIP reason=rolled_back version=0\.3\.0$'
assert d ota_forbid "$logs/d.log" '^NE_OTA VALID partition=ota_1'
assert d ota_count_is "$logs/d.log" '^NE_OTA ROLLBACK from=ota_1 to=ota_0' 1

# (e) an image whose gate self-test fails marks itself INVALID and reboots
# (the self-test path of FR-OTA-02); the bootloader rolls back to 0.2.0 again.
serve "$images/c2.bin"
qemu_once e 1 '^NE_OTA SWITCH partition=ota_1$' idle 0
qemu_once e 2 '^NE_OTA INVALID partition=ota_1$' exit
qemu_once e 3 '^NE_OTA SKIP reason=rolled_back version=0\.3\.1$' idle
join_boots e
assert e ota_ordered "$logs/e.log" \
  "^NE_OTA CHECK url=$URL\$" \
  '^NE_OTA DOWNLOADED bytes=[1-9][0-9]* version=0\.3\.1$' \
  '^NE_OTA SWITCH partition=ota_1$' \
  '^NE_SELFTEST FAIL test image NEUROEDGE_OTA_TEST_FAIL_SELFTEST$' \
  '^NE_OTA INVALID partition=ota_1$' \
  '^NE_OTA ROLLBACK from=ota_1 to=ota_0$' \
  '^NE_OTA SKIP reason=rolled_back version=0\.3\.1$'
assert e ota_forbid "$logs/e.log" '^NE_OTA VALID partition=ota_1'
assert e ota_count_is "$logs/e.log" '^NE_SELFTEST FAIL test image' 1

# (f) an unsigned image is refused: no signature block, no switch, and the
# slot it was written to is erased.
: >"$logs/f.log"
serve "$images/c-unsigned.bin"
qemu_once f 1 '^NE_OTA REJECTED reason=signature$' idle 10
join_boots f
assert f ota_ordered "$logs/f.log" \
  "^NE_OTA CHECK url=$URL\$" \
  '^NE_OTA REJECTED reason=signature$' \
  '^NE_OTA ERASED partition=ota_1$'
# The boot reports phase e's aborted slot once, before the check; nothing may
# switch, confirm or roll back after it.
assert f ota_forbid "$logs/f.log" '^NE_OTA (SWITCH|VALID)'
assert f ota_count_is "$logs/f.log" '^NE_OTA ROLLBACK' 1
assert f ota_count_is "$logs/f.log" '^NE_OTA ROLLBACK from=ota_1 to=ota_0$' 1
assert f ota_nothing_after "$logs/f.log" "^NE_OTA CHECK url=$URL\$" '^NE_OTA ROLLBACK'
assert f ota_count_is "$logs/f.log" '^NE_SELFTEST PASS' 1

# (g) a correctly signed lower version is a downgrade: the high-water mark
# (0.2.0, set when b was confirmed) refuses it, and the device stays put.
: >"$logs/g.log"
serve "$images/a.bin"
qemu_once g 1 '^NE_OTA SKIP reason=downgrade version=0\.1\.0$' idle
join_boots g
assert g ota_ordered "$logs/g.log" \
  '^NE_SELFTEST PASS walker=[0-9]+ token=[0-9]+' \
  "^NE_OTA CHECK url=$URL\$" \
  '^NE_OTA SKIP reason=downgrade version=0\.1\.0$'
assert g ota_forbid "$logs/g.log" '^NE_OTA (DOWNLOADED|SWITCH|REJECTED)'
assert g ota_count_is "$logs/g.log" '^NE_OTA ROLLBACK' 1
assert g ota_count_is "$logs/g.log" '^NE_OTA ROLLBACK from=ota_1 to=ota_0$' 1
assert g ota_nothing_after "$logs/g.log" "^NE_OTA CHECK url=$URL\$" '^NE_OTA ROLLBACK'
assert g ota_count_is "$logs/g.log" '^NE_SELFTEST PASS' 1

# --- evidence -----------------------------------------------------------------------------------

echo
echo "OTA on QEMU: all phases passed (logs in $logs)"
for phase in a b c d e f g; do
  echo "--- $phase"
  grep -aE '^(NE_SELFTEST|NE_OTA|Guru Meditation)' "$logs/$phase.log" | tr -d '\r'
done
