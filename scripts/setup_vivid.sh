#!/usr/bin/env bash
# A real V4L2 capture device with no camera: the kernel's `vivid` driver (TSK-V1b-01).
#
# vivid ("Virtual Video Test Driver", in the kernel's media tree) creates /dev/videoN nodes that
# answer the same ioctls and stream the same mmap buffers as a USB or CSI camera: VIDIOC_S_FMT,
# S_PARM, REQBUFS, QBUF/DQBUF, STREAMON. `hal/v4l2.py` runs against it exactly as it will against a
# Pi's camera. Its test pattern carries a time stamp and a frame counter, so no two frames are
# the same (the perception refuses a frozen camera).
#
# One video-capture node is made (`node_types=0x1`, no output, VBI, radio or touch nodes), and
# found by name — vivid names its card "vivid" — never by its number: a runner may already have
# /dev/video0..N of its own.
#
# Prints, and appends to $GITHUB_ENV when set:
#   NEUROEDGE_LINUX_CAMERA   /dev/videoN of the virtual capture device (the variable LinuxHAL reads)
#
# Usage: sudo is used where needed; run as a user who may sudo.
set -euo pipefail

load() { sudo modprobe vivid n_devs=1 node_types=0x1 vid_cap_nr=42; }
if ! load 2>/dev/null; then
  # Cloud kernels (GitHub's linux-azure) ship vivid in the extra modules, as they do gpio-sim.
  sudo apt-get update -qq
  sudo apt-get install -y -qq "linux-modules-extra-$(uname -r)"
  load
fi

find_device() {
  for node in /sys/class/video4linux/video*; do
    [ -e "$node/name" ] || continue
    case "$(cat "$node/name")" in
      vivid*) echo "/dev/${node##*/}" ;;
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
  echo "::error::no vivid capture node after modprobe" >&2
  for node in /sys/class/video4linux/*; do echo "  $node: $(cat "$node/name" 2>/dev/null)"; done
  ls -l /dev/video* 2>&1 || true
  exit 1
fi

# The test process reads frames as the runner user, not root.
sudo chmod a+rw "$DEVICE"

echo "NEUROEDGE_LINUX_CAMERA=$DEVICE"
if [ -n "${GITHUB_ENV:-}" ]; then
  echo "NEUROEDGE_LINUX_CAMERA=$DEVICE" >>"$GITHUB_ENV"
fi
