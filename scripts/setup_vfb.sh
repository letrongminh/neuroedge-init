#!/usr/bin/env bash
# A real Linux framebuffer with no panel: the kernel's vfb driver (TSK-S5-09).
#
# vfb ("Virtual FB") is a framebuffer device backed by memory: it answers the
# same ioctls and takes the same writes as a Pi's /dev/fb0, so LinuxHAL's
# framebuffer backend runs against the kernel. It is set to the linux-rpi5
# display, 800x480, at 16 bits per pixel.
#
# Prints, and appends to $GITHUB_ENV when set:
#   NEUROEDGE_VFB_DEVICE   /dev/fbN of the virtual framebuffer
#
# Usage: sudo is used where needed; run as a user who may sudo.
set -euo pipefail

WIDTH=800
HEIGHT=480
DEPTH=16

load() { sudo modprobe vfb vfb_enable=1 videomemorysize=$((WIDTH * HEIGHT * 4 * 2)); }
if ! load 2>/dev/null; then
  # Cloud kernels (GitHub's linux-azure) ship vfb in the extra modules.
  sudo apt-get update -qq
  sudo apt-get install -y -qq "linux-modules-extra-$(uname -r)"
  load
fi
command -v fbset >/dev/null || {
  sudo apt-get update -qq
  sudo apt-get install -y -qq fbset
}

DEVICE=""
for fb in /sys/class/graphics/fb*; do
  if [ "$(cat "$fb/name" 2>/dev/null)" = "Virtual FB" ]; then
    DEVICE=/dev/${fb##*/}
  fi
done
[ -n "$DEVICE" ] || { echo "::error::no Virtual FB device after modprobe vfb" >&2; exit 1; }

sudo fbset -fb "$DEVICE" -g "$WIDTH" "$HEIGHT" "$WIDTH" "$HEIGHT" "$DEPTH"
# The test process writes frames as the runner user, not root.
sudo chmod a+rw "$DEVICE"

echo "NEUROEDGE_VFB_DEVICE=$DEVICE"
if [ -n "${GITHUB_ENV:-}" ]; then
  echo "NEUROEDGE_VFB_DEVICE=$DEVICE" >>"$GITHUB_ENV"
fi
fbset -fb "$DEVICE" -i | sed 's/^/  /'
