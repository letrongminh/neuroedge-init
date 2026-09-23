#!/usr/bin/env bash
# Create virtual GPIO lines named after the linux-rpi5 board pins (Q-16, TSK-S3-05).
#
# gpio-sim (kernel >= 5.19) builds a GPIO chip from configfs. The lines are
# named door_lock / porch_light / gate_relay, which is how LinuxHAL finds them,
# so the HAL runs against the real kernel character device with no board.
#
# Prints, and appends to $GITHUB_ENV when set:
#   NEUROEDGE_GPIO_SIM_CHIP   /dev/gpiochipN of the virtual chip
#   NEUROEDGE_GPIO_SIM_SYSFS  /sys/devices/platform/<dev>/<chip> — sim_gpioN/value
#                             shows what each line is driven to, independent of
#                             the process driving it
#
# Usage: sudo is used where needed; run as a user who may sudo.
set -euo pipefail

DEVICE=neuroedge
PINS=(door_lock porch_light gate_relay)
CONFIGFS=/sys/kernel/config/gpio-sim

if ! sudo modprobe gpio-sim 2>/dev/null; then
  # Cloud kernels (GitHub's linux-azure) ship gpio-sim in the extra modules.
  sudo apt-get update -qq
  sudo apt-get install -y -qq "linux-modules-extra-$(uname -r)"
  sudo modprobe gpio-sim
fi
mountpoint -q /sys/kernel/config || sudo mount -t configfs none /sys/kernel/config

if [ -e "$CONFIGFS/$DEVICE/live" ] && [ "$(cat "$CONFIGFS/$DEVICE/live")" = 1 ]; then
  echo "gpio-sim device $DEVICE is already live"
else
  sudo mkdir -p "$CONFIGFS/$DEVICE/bank0"
  echo "${#PINS[@]}" | sudo tee "$CONFIGFS/$DEVICE/bank0/num_lines" >/dev/null
  echo "$DEVICE" | sudo tee "$CONFIGFS/$DEVICE/bank0/label" >/dev/null
  for i in "${!PINS[@]}"; do
    sudo mkdir -p "$CONFIGFS/$DEVICE/bank0/line$i"
    echo "${PINS[$i]}" | sudo tee "$CONFIGFS/$DEVICE/bank0/line$i/name" >/dev/null
  done
  echo 1 | sudo tee "$CONFIGFS/$DEVICE/live" >/dev/null
fi

DEV_NAME=$(cat "$CONFIGFS/$DEVICE/dev_name")
CHIP_NAME=$(cat "$CONFIGFS/$DEVICE/bank0/chip_name")
CHIP=/dev/$CHIP_NAME
SYSFS=/sys/devices/platform/$DEV_NAME/$CHIP_NAME

# The test process drives the lines as the runner user, not root.
sudo chmod a+rw "$CHIP"
sudo chmod -R a+r "$SYSFS" 2>/dev/null || true

echo "NEUROEDGE_GPIO_SIM_CHIP=$CHIP"
echo "NEUROEDGE_GPIO_SIM_SYSFS=$SYSFS"
if [ -n "${GITHUB_ENV:-}" ]; then
  echo "NEUROEDGE_GPIO_SIM_CHIP=$CHIP" >>"$GITHUB_ENV"
  echo "NEUROEDGE_GPIO_SIM_SYSFS=$SYSFS" >>"$GITHUB_ENV"
fi
for i in "${!PINS[@]}"; do
  echo "  line $i ${PINS[$i]}: $(cat "$SYSFS/sim_gpio$i/value" 2>/dev/null || echo '?')"
done
