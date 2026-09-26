#!/usr/bin/env bash
# Boot an ESP-IDF build of the firmware on Espressif QEMU and read its UART
# (TSK-S4-08, TSK-I3-01). Used by .github/workflows/firmware-qemu.yml.
#
#   scripts/qemu_boot.sh <build dir> [seconds]     # default 120 s
#
# Needs the ESP-IDF environment (`. $IDF_PATH/export.sh`) with qemu-xtensa installed.
# Writes <build dir>/uart.log and prints it. Exit 0 only when the UART says
# `NE_SELFTEST PASS` and then `NE_TRACE DONE`, the device's last line; a
# `NE_SELFTEST FAIL`, an emulator that stops, or nothing within the time is exit 1 —
# never a pass.
set -euo pipefail

build=${1:?usage: qemu_boot.sh <build dir> [seconds]}
seconds=${2:-120}
cd "$build"
esptool.py --chip esp32s3 merge_bin --fill-flash-size 16MB -o flash.bin @flash_args
rm -f uart.log
qemu-system-xtensa -machine esp32s3 -display none -monitor none -no-reboot \
  -drive file=flash.bin,if=mtd,format=raw \
  -serial file:uart.log &
qemu=$!
verdict=""
for _ in $(seq 1 "$seconds"); do
  if grep -q 'NE_SELFTEST FAIL' uart.log 2>/dev/null; then verdict=fail; break; fi
  # PASS comes first; NE_TRACE DONE is the device's last line (TSK-S4-09).
  if grep -q 'NE_TRACE DONE' uart.log 2>/dev/null; then
    if grep -q 'NE_SELFTEST PASS' uart.log; then verdict=pass; fi
    break
  fi
  if ! kill -0 "$qemu" 2>/dev/null; then break; fi
  sleep 1
done
kill "$qemu" 2>/dev/null || true
wait "$qemu" 2>/dev/null || true
cat uart.log 2>/dev/null || true
line="$(grep -o 'NE_SELFTEST .*' uart.log 2>/dev/null | head -n1 || true)"
if [ "$verdict" != pass ]; then
  echo "::error::no NE_SELFTEST PASS then NE_TRACE DONE on the UART (${line:-nothing within ${seconds} s})"
  exit 1
fi
echo "  ok  $line"
