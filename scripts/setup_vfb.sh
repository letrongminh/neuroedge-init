#!/usr/bin/env bash
# A real Linux framebuffer with no panel: the kernel's vfb or vkms driver (TSK-S5-09).
#
# Both give a framebuffer device backed by memory: it answers the same ioctls
# and takes the same writes as a Pi's /dev/fb0, so LinuxHAL's framebuffer
# backend runs against the kernel. vfb is set to the linux-rpi5 display,
# 800x480 at 16 bits per pixel; vkms (whose fbdev emulation is the device)
# keeps its own mode. GitHub's linux-azure builds vkms but not vfb.
#
# Prints, and appends to $GITHUB_ENV when set:
#   NEUROEDGE_VFB_DEVICE   /dev/fbN of the virtual framebuffer
#
# Usage: sudo is used where needed; run as a user who may sudo.
set -euo pipefail

WIDTH=800
HEIGHT=480
DEPTH=16

try_vfb() { sudo modprobe vfb vfb_enable=1 videomemorysize=$((WIDTH * HEIGHT * 4 * 2)); }
try_vkms() { sudo modprobe vkms; }
if ! try_vfb 2>/dev/null && ! try_vkms 2>/dev/null; then
  sudo apt-get update -qq
  sudo apt-get install -y -qq "linux-modules-extra-$(uname -r)"
  try_vfb 2>/dev/null || try_vkms
fi

find_device() {
  for fb in /sys/class/graphics/fb*; do
    case "$(cat "$fb/name" 2>/dev/null)" in
      "Virtual FB" | vkms*) echo "/dev/${fb##*/}" ;;
    esac
  done
}
DEVICE=""
for _ in $(seq 50); do
  DEVICE=$(find_device | head -1)
  [ -n "$DEVICE" ] && [ -e "$DEVICE" ] && break
  sleep 0.1
done
if [ -z "$DEVICE" ] || [ ! -e "$DEVICE" ]; then
  echo "::error::no virtual framebuffer (vfb or vkms) after modprobe" >&2
  for fb in /sys/class/graphics/*; do echo "  $fb: $(cat "$fb/name" 2>/dev/null)"; done
  ls -l /dev/fb* /dev/dri 2>&1 || true
  exit 1
fi
SYSFS=/sys/class/graphics/${DEVICE##*/}

if [ "$(cat "$SYSFS/name")" = "Virtual FB" ]; then
  command -v fbset >/dev/null || {
    sudo apt-get update -qq
    sudo apt-get install -y -qq fbset
  }
  sudo fbset -fb "$DEVICE" -g "$WIDTH" "$HEIGHT" "$WIDTH" "$HEIGHT" "$DEPTH"
fi
# The test process writes frames as the runner user, not root.
sudo chmod a+rw "$DEVICE"

echo "NEUROEDGE_VFB_DEVICE=$DEVICE"
if [ -n "${GITHUB_ENV:-}" ]; then
  echo "NEUROEDGE_VFB_DEVICE=$DEVICE" >>"$GITHUB_ENV"
fi
for attribute in name virtual_size bits_per_pixel stride; do
  echo "  $attribute: $(cat "$SYSFS/$attribute" 2>/dev/null || echo '?')"
done
