#!/usr/bin/env bash
# Boot an ESP-IDF build of the firmware on Espressif QEMU and read its UART
# (TSK-S4-08, TSK-I3-01). Used by .github/workflows/firmware-qemu.yml.
#
#   scripts/qemu_boot.sh <build dir> [seconds]     # default 120 s
#
# Needs the ESP-IDF environment (`. $IDF_PATH/export.sh`) with qemu-xtensa installed.
# Writes <build dir>/uart.log and prints it. Exit 0 only when the UART has a line
# `NE_SELFTEST PASS walker=<n> token=<n>` and, after it, `NE_TRACE DONE sessions=<n>`,
# the device's last line — each at column 0, so the same words inside a trace line
# (an on_block message, say) are never read as the device's verdict. A
# `NE_SELFTEST FAIL`, an emulator that stops, or nothing within the time is exit 1 —
# never a pass.
set -euo pipefail

build=${1:?usage: qemu_boot.sh <build dir> [seconds]}
seconds=${2:-120}
PASS='^NE_SELFTEST PASS walker=[0-9]+ token=[0-9]+'
FAIL='^NE_SELFTEST FAIL'
DONE='^NE_TRACE DONE sessions=[0-9]+'

# The number of the first line of the log matching $1, 0 when there is none (or no log).
first() {
  if [ ! -f uart.log ]; then echo 0; return; fi
  awk -v re="$1" '$0 ~ re { print NR; found = 1; exit } END { if (!found) print 0 }' uart.log
}

cd "$build"
esptool.py --chip esp32s3 merge_bin --fill-flash-size 16MB -o flash.bin @flash_args
rm -f uart.log
qemu-system-xtensa -machine esp32s3 -display none -monitor none -no-reboot \
  -drive file=flash.bin,if=mtd,format=raw \
  -serial file:uart.log &
qemu=$!
for _ in $(seq 1 "$seconds"); do
  if [ "$(first "$FAIL")" != 0 ] || [ "$(first "$DONE")" != 0 ]; then break; fi
  if ! kill -0 "$qemu" 2>/dev/null; then break; fi
  sleep 1
done
kill "$qemu" 2>/dev/null || true
wait "$qemu" 2>/dev/null || true
cat uart.log 2>/dev/null || true

pass=$(first "$PASS")
done_at=$(first "$DONE")
failed=$(first "$FAIL")
line="$(grep -E '^NE_SELFTEST ' uart.log 2>/dev/null | head -n1 | tr -d '\r' || true)"
if [ "$failed" != 0 ] || [ "$pass" = 0 ] || [ "$done_at" = 0 ] || [ "$pass" -gt "$done_at" ]; then
  echo "::error::no NE_SELFTEST PASS then NE_TRACE DONE on the UART (${line:-nothing within ${seconds} s})"
  exit 1
fi
echo "  ok  $line"
