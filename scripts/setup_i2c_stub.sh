#!/usr/bin/env bash
# A real hwmon temperature sensor with no board: i2c-stub + the lm75 driver (TSK-S5-09).
#
# i2c-stub is a fake SMBus adapter whose chip at $ADDR answers from a register
# table; binding the kernel's own lm75 driver to it creates
# /sys/class/hwmon/hwmonN (name "lm75", temp1_input in millidegrees), which is
# what LinuxHAL reads on a Pi. The temperature register is set with i2cset,
# so a test decides what the "sensor" measures and reads it back through the HAL.
#
# Prints, and appends to $GITHUB_ENV when set:
#   NEUROEDGE_I2C_STUB_BUS   the adapter number N (/dev/i2c-N, i2cset's bus)
#   NEUROEDGE_LM75_DEVICE    the kernel device, N-0048 (hwmon:lm75@N-0048/temp1)
#   NEUROEDGE_LM75_HWMON     /sys/class/hwmon/hwmonM of the bound driver
#
# Usage: sudo is used where needed; run as a user who may sudo.
set -euo pipefail

ADDR=0x48
# 25.0 °C: the LM75 register is big-endian 0x1900, an SMBus word is little-endian.
START_WORD=0x0019

load_modules() {
  sudo modprobe i2c-stub "chip_addr=$ADDR" && sudo modprobe i2c-dev && sudo modprobe lm75
}
if ! load_modules 2>/dev/null; then
  # Cloud kernels (GitHub's linux-azure) ship i2c-stub and lm75 in the extra modules.
  sudo apt-get update -qq
  sudo apt-get install -y -qq "linux-modules-extra-$(uname -r)"
  load_modules
fi
command -v i2cset >/dev/null || {
  sudo apt-get update -qq
  sudo apt-get install -y -qq i2c-tools
}

BUS=""
for adapter in /sys/bus/i2c/devices/i2c-*; do
  if [ "$(cat "$adapter/name")" = "SMBus stub driver" ]; then
    BUS=${adapter##*/i2c-}
  fi
done
[ -n "$BUS" ] || { echo "::error::no i2c-stub adapter after modprobe" >&2; exit 1; }
DEVICE=$BUS-00${ADDR#0x}

# The test process sets the register as the runner user, not root.
sudo chmod a+rw "/dev/i2c-$BUS"
i2cset -f -y "$BUS" "$ADDR" 0x00 "$START_WORD" w

if [ ! -e "/sys/bus/i2c/devices/$DEVICE" ]; then
  echo "lm75 $ADDR" | sudo tee "/sys/bus/i2c/devices/i2c-$BUS/new_device" >/dev/null
fi

HWMON=""
for _ in $(seq 50); do
  for dir in /sys/class/hwmon/hwmon*; do
    if [ "$(cat "$dir/name" 2>/dev/null)" = lm75 ] &&
      [ "$(basename "$(readlink -f "$dir/device")")" = "$DEVICE" ]; then
      HWMON=$dir
    fi
  done
  [ -n "$HWMON" ] && break
  sleep 0.1
done
[ -n "$HWMON" ] || { echo "::error::lm75 did not bind at $DEVICE (dmesg below)" >&2; sudo dmesg | tail -20; exit 1; }

echo "NEUROEDGE_I2C_STUB_BUS=$BUS"
echo "NEUROEDGE_LM75_DEVICE=$DEVICE"
echo "NEUROEDGE_LM75_HWMON=$HWMON"
if [ -n "${GITHUB_ENV:-}" ]; then
  echo "NEUROEDGE_I2C_STUB_BUS=$BUS" >>"$GITHUB_ENV"
  echo "NEUROEDGE_LM75_DEVICE=$DEVICE" >>"$GITHUB_ENV"
  echo "NEUROEDGE_LM75_HWMON=$HWMON" >>"$GITHUB_ENV"
fi
echo "  $HWMON/temp1_input: $(cat "$HWMON/temp1_input")"
