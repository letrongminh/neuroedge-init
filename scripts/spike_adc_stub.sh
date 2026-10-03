#!/usr/bin/env bash
# Spike TSK-N3-03: can CI test analog.in on linux with no board?
#
# RFC-0007 §3c: analog.in on linux is tested in CI only if an I2C ADC with a
# kernel hwmon driver binds to i2c-stub and reads back a known value. The
# runner kernel is not assumed to have IIO, so the candidates are hwmon drivers:
#
#   ads7828  8-channel 12-bit ADC, internal 2.5 V reference by default
#   ina219   bus and shunt voltage monitor (driver ina2xx)
#
# Each candidate gets its own i2c-stub address. The script writes a known
# register value with i2cset, binds the kernel driver, and checks the hwmon
# millivolt attribute against the value the datasheet formula gives. It prints
# one RESULT line per candidate, and exits 0 when at least one candidate reads
# back exactly; the spike report quotes these lines.
#
# Usage: sudo is used where needed; run as a user who may sudo.
set -euo pipefail

ADS7828_ADDR=0x4a
INA219_ADDR=0x40

echo "kernel: $(uname -r)"
config=/boot/config-$(uname -r)
if [ -r "$config" ]; then
  grep -E '^(# )?CONFIG_(IIO|SENSORS_ADS7828|SENSORS_INA2XX|I2C_STUB)[ =]' "$config" || true
fi

load_modules() {
  sudo modprobe i2c-stub "chip_addr=$ADS7828_ADDR,$INA219_ADDR" && sudo modprobe i2c-dev
}
if ! load_modules 2>/dev/null; then
  # Cloud kernels (GitHub's linux-azure) ship i2c-stub and hwmon drivers in the extra modules.
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
sudo chmod a+rw "/dev/i2c-$BUS"
echo "i2c-stub bus: $BUS"

# hwmon_dir NAME DEVICE: the hwmon directory of driver NAME bound at DEVICE, or nothing.
hwmon_dir() {
  local dir
  for _ in $(seq 50); do
    for dir in /sys/class/hwmon/hwmon*; do
      if [ "$(cat "$dir/name" 2>/dev/null)" = "$1" ] &&
        [ "$(basename "$(readlink -f "$dir/device")")" = "$2" ]; then
        echo "$dir"
        return 0
      fi
    done
    sleep 0.1
  done
  return 1
}

# bind DRIVER MODULE ADDR: load MODULE and instantiate DRIVER at ADDR; prints the hwmon dir.
bind() {
  local device=$BUS-00${3#0x}
  sudo modprobe "$2" || return 1
  if [ ! -e "/sys/bus/i2c/devices/$device" ]; then
    echo "$1 $3" | sudo tee "/sys/bus/i2c/devices/i2c-$BUS/new_device" >/dev/null || return 1
  fi
  hwmon_dir "$1" "$device"
}

# check NAME FILE EXPECTED: compare one hwmon attribute with the expected millivolts.
check() {
  local got
  got=$(cat "$2" 2>/dev/null) || got="<unreadable>"
  if [ "$got" = "$3" ]; then
    echo "RESULT $1 PASS $2 = $got mV (expected $3)"
    return 0
  fi
  echo "RESULT $1 FAIL $2 = $got mV (expected $3)"
  return 1
}

passed=0

# --- ads7828 ----------------------------------------------------------------------
# The driver reads channel 0, single-ended, internal reference, with command byte
# 0x8c (SD=1, C=000, PD=11) through 16-bit regmap over SMBus word reads, which
# swap bytes: the stub word 0x0008 is the 12-bit code 0x800 = 2048.
# in0_input = round(2048 * (2500000 / 4096 rounded down = 610) / 1000) = 1249 mV.
if i2cset -f -y "$BUS" "$ADS7828_ADDR" 0x8c 0x0008 w && dir=$(bind ads7828 ads7828 "$ADS7828_ADDR"); then
  check ads7828 "$dir/in0_input" 1249 && passed=$((passed + 1)) || true
else
  echo "RESULT ads7828 FAIL driver did not bind at $BUS-00${ADS7828_ADDR#0x}"
  sudo dmesg | tail -5
fi

# --- ina219 -----------------------------------------------------------------------
# Probe writes the configuration and calibration registers, which the stub keeps.
# Bus voltage register 0x02: bits 15..3 count 4 mV steps; 12000 mV = 3000 << 3 =
# 0x5dc0, stored byte-swapped as 0xc05d. in1_input is the bus voltage in mV.
if i2cset -f -y "$BUS" "$INA219_ADDR" 0x02 0xc05d w && dir=$(bind ina219 ina2xx "$INA219_ADDR"); then
  check ina219 "$dir/in1_input" 12000 && passed=$((passed + 1)) || true
else
  echo "RESULT ina219 FAIL driver did not bind at $BUS-00${INA219_ADDR#0x}"
  sudo dmesg | tail -5
fi

echo "candidates that read back exactly: $passed of 2"
[ "$passed" -gt 0 ]
