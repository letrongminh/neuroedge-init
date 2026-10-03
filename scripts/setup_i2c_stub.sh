#!/usr/bin/env bash
# Real hwmon sensors with no board: i2c-stub + the lm75 driver (TSK-S5-09), and the
# ads7828 ADC driver for analog.in (TSK-I2a-04, folded in from the TSK-N3-03 spike).
#
# i2c-stub is a fake SMBus adapter whose chip at $ADDR answers from a register
# table; binding the kernel's own lm75 driver to it creates
# /sys/class/hwmon/hwmonN (name "lm75", temp1_input in millidegrees), which is
# what LinuxHAL reads on a Pi. The temperature register is set with i2cset,
# so a test decides what the "sensor" measures and reads it back through the HAL.
#
# The ads7828 (8-channel, 12-bit, internal 2.5 V reference) sits at 0x4a and reads channel 0
# from the register the driver addresses with command byte 0x8c. i2cset writes the 12-bit code
# 0x800 there (an SMBus word is little-endian, so 0x0008), which the driver reports as
# in0_input = round(2048 * (2500000 / 4096 rounded down = 610) / 1000) = 1249 mV. A test that
# wants another voltage writes another code to the same register.
#
# Prints, and appends to $GITHUB_ENV when set:
#   NEUROEDGE_I2C_STUB_BUS   the adapter number N (/dev/i2c-N, i2cset's bus)
#   NEUROEDGE_LM75_DEVICE    the kernel device, N-0048 (hwmon:lm75@N-0048/temp1)
#   NEUROEDGE_LM75_HWMON     /sys/class/hwmon/hwmonM of the bound driver
#   NEUROEDGE_ADS7828_DEVICE the kernel device, N-004a (hwmon:ads7828@N-004a/in0)
#   NEUROEDGE_ADS7828_HWMON  /sys/class/hwmon/hwmonM of the bound ads7828
#
# Usage: sudo is used where needed; run as a user who may sudo.
set -euo pipefail

ADDR=0x48
ADS_ADDR=0x4a
# 25.0 °C: the LM75 register is big-endian 0x1900, an SMBus word is little-endian.
START_WORD=0x0019

load_modules() {
  sudo modprobe i2c-stub "chip_addr=$ADDR,$ADS_ADDR" && sudo modprobe i2c-dev &&
    sudo modprobe lm75 && sudo modprobe ads7828
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

# --- ads7828 (analog.in) ------------------------------------------------------------------
ADS_DEVICE=$BUS-00${ADS_ADDR#0x}
i2cset -f -y "$BUS" "$ADS_ADDR" 0x8c 0x0008 w
if [ ! -e "/sys/bus/i2c/devices/$ADS_DEVICE" ]; then
  echo "ads7828 $ADS_ADDR" | sudo tee "/sys/bus/i2c/devices/i2c-$BUS/new_device" >/dev/null
fi

ADS_HWMON=""
for _ in $(seq 50); do
  for dir in /sys/class/hwmon/hwmon*; do
    if [ "$(cat "$dir/name" 2>/dev/null)" = ads7828 ] &&
      [ "$(basename "$(readlink -f "$dir/device")")" = "$ADS_DEVICE" ]; then
      ADS_HWMON=$dir
    fi
  done
  [ -n "$ADS_HWMON" ] && break
  sleep 0.1
done
[ -n "$ADS_HWMON" ] || { echo "::error::ads7828 did not bind at $ADS_DEVICE (dmesg below)" >&2; sudo dmesg | tail -20; exit 1; }

echo "NEUROEDGE_I2C_STUB_BUS=$BUS"
echo "NEUROEDGE_LM75_DEVICE=$DEVICE"
echo "NEUROEDGE_LM75_HWMON=$HWMON"
echo "NEUROEDGE_ADS7828_DEVICE=$ADS_DEVICE"
echo "NEUROEDGE_ADS7828_HWMON=$ADS_HWMON"
if [ -n "${GITHUB_ENV:-}" ]; then
  {
    echo "NEUROEDGE_I2C_STUB_BUS=$BUS"
    echo "NEUROEDGE_LM75_DEVICE=$DEVICE"
    echo "NEUROEDGE_LM75_HWMON=$HWMON"
    echo "NEUROEDGE_ADS7828_DEVICE=$ADS_DEVICE"
    echo "NEUROEDGE_ADS7828_HWMON=$ADS_HWMON"
  } >>"$GITHUB_ENV"
fi
echo "  $HWMON/temp1_input: $(cat "$HWMON/temp1_input")"
echo "  $ADS_HWMON/in0_input: $(cat "$ADS_HWMON/in0_input")"
