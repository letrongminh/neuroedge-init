#!/usr/bin/env bash
# Build the project `neuroedge build --target esp32s3` wrote with the OTA layer
# (TSK-S6-01/02/04, FR-OTA-01..04). Used by .github/workflows/firmware-qemu.yml
# job `agent-firmware`, after the same project's QEMU-layer build in build/:
# different sdkconfig layers need different build dirs, so this one uses
# <project>/build-ota and leaves the other build's sdkconfig and artifacts alone.
#
#   scripts/build_ota_layer.sh <project-dir> [expected MAJOR.MINOR.PATCH version]
#
# Run it in the espressif/idf:v5.4 container with the IDF environment sourced:
#
#   docker run --rm -v "$PWD":/work -v neuroedge-ccache:/root/.ccache \
#     -e IDF_CCACHE_ENABLE=1 -w /work espressif/idf:v5.4 \
#     bash -c '. $IDF_PATH/export.sh && scripts/build_ota_layer.sh <project-dir> 0.1.0'
#
# A throwaway RSA-3072 signing key is made in the project when there is none
# (git-ignored; real keys never belong in the repository). The script fails
# unless the layer really enabled OTA, signature-on-update and rollback, and
# unless the version the image reports came from version.txt: a generated
# project outside git that falls back to app version "1" would skip every
# update as same-version and could not tell an upgrade from a downgrade.
set -euo pipefail

usage() {
  echo "usage: build_ota_layer.sh <project-dir> [expected MAJOR.MINOR.PATCH version]" >&2
  exit 2
}

say() { printf '  %s\n' "$*"; }
fail() {
  printf '::error::%s\n' "$*" >&2
  exit 1
}

[ $# -ge 1 ] && [ $# -le 2 ] || usage
project=$(cd "$1" 2>/dev/null && pwd) || fail "project directory $1 not found"
expected=${2:-}
build="$project/build-ota"
sdkconfig="$build/sdkconfig"
key="$project/secure_boot_signing_key.pem"
defaults="sdkconfig.defaults;sdkconfig.ota"

for tool in idf.py espsecure.py; do
  command -v "$tool" >/dev/null 2>&1 ||
    fail "$tool not found: run inside espressif/idf:v5.4 with \$IDF_PATH/export.sh sourced"
done
[ -f "$project/CMakeLists.txt" ] || fail "$project is not an ESP-IDF project (no CMakeLists.txt)"
[ -f "$project/version.txt" ] ||
  fail "$project has no version.txt: \`neuroedge build --target esp32s3\` writes the agent's version"
version=$(tr -d '[:space:]' < "$project/version.txt")
if [ -n "$expected" ] && [ "$version" != "$expected" ]; then
  fail "version.txt holds $version, expected $expected"
fi

if [ ! -f "$key" ]; then
  say "throwaway RSA-3072 signing key: $key"
  espsecure.py generate_signing_key --version 2 "$key" >/dev/null
fi

say "build $defaults (app version $version)"
cd "$project"
idf.py -B build-ota -D SDKCONFIG="$sdkconfig" -D SDKCONFIG_DEFAULTS="$defaults" set-target esp32s3
idf.py -B build-ota -D SDKCONFIG="$sdkconfig" -D SDKCONFIG_DEFAULTS="$defaults" build

for setting in CONFIG_NEUROEDGE_OTA=y CONFIG_SECURE_SIGNED_ON_UPDATE_NO_SECURE_BOOT=y \
  CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE=y; do
  grep -q "^$setting$" "$sdkconfig" || fail "$sdkconfig lacks $setting: the OTA layer did not take"
done
app=$(awk '$1 == "0x10000" { print $2; exit }' "$build/flash_args")
[ -n "$app" ] && [ -f "$build/$app" ] || fail "no app binary in $build/flash_args"
# The version the image itself reports: the app descriptor at 0x20 of the first
# segment (esp_app_desc_t: magic, secure_version, reserved, version[32]).
if ! built=$(python3 - "$build/$app" <<'PY'
import struct
import sys

data = open(sys.argv[1], "rb").read()
(magic,) = struct.unpack_from("<I", data, 0x20)
if magic != 0xABCD5432:
    sys.exit(2)
print(data[0x30:0x50].split(b"\0", 1)[0].decode())
PY
); then
  fail "no app descriptor in $app"
fi
[ "$built" = "$version" ] ||
  fail "the image reports version $built, expected $version from version.txt"
espsecure.py verify_signature --version 2 --keyfile "$key" "$build/$app" >/dev/null ||
  fail "$app is not signed with $key"
say "ok  OTA layer: app version $built, signed; OTA + rollback enabled"
