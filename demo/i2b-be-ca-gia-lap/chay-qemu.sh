#!/usr/bin/env bash
# D3 and D5 of kich-ban.md: the fish tank on one chip (box and brain in one image) on Espressif QEMU,
# the same steps as the CI job `aquarium-qemu` (.github/workflows/firmware-qemu.yml).
#
#   bash demo/i2b-be-ca-gia-lap/chay-qemu.sh              # build, run the checked story, replay it
#   bash demo/i2b-be-ca-gia-lap/chay-qemu.sh --console    # then the chip's console, for you to type
#
# Docker with espressif/idf:v5.4 (amd64; Apple Silicon runs it emulated, slowly). Builds take minutes
# and fetch the pinned NeuroClaw-ESP: the CI job is the quicker way to show the result.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
docker run --rm -it --platform linux/amd64 -v "$ROOT":/work -w /work espressif/idf:v5.4 bash -c '
set -euo pipefail
git config --global --add safe.directory "*"
python3 -m venv /opt/neuroedge >/dev/null
/opt/neuroedge/bin/python -m pip install --quiet ./python
NE=/opt/neuroedge/bin/neuroedge
OUT=/tmp/aquarium
(cd fixtures/agents/aquarium && "$NE" build --target esp32s3 --board esp32s3-box-3 --brain neuroclaw --out "$OUT")
. "$IDF_PATH/export.sh" >/dev/null
P="$OUT/esp32s3"
D="sdkconfig.defaults;sdkconfig.qemu"
idf.py -C "$P" -B "$P/build" -D SDKCONFIG="$P/build/sdkconfig" -D SDKCONFIG_DEFAULTS="$D" set-target esp32s3 >/dev/null
idf.py -C "$P" -B "$P/build" -D SDKCONFIG="$P/build/sdkconfig" -D SDKCONFIG_DEFAULTS="$D" build >/dev/null
python "$IDF_PATH/tools/idf_tools.py" install qemu-xtensa >/dev/null
. "$IDF_PATH/export.sh" >/dev/null
python3 scripts/qemu_aquarium.py "$P/build"
rm -rf /tmp/aquarium-traces
"$NE" record --target esp32s3 --port "$P/build/aquarium-test/boot-1.log" --follow --out /tmp/aquarium-traces/
for t in /tmp/aquarium-traces/*.json; do "$NE" replay "$t" --agent fixtures/agents/aquarium/agent.toml | tail -1; done
if [ "${1:-}" = "--console" ]; then
  echo "--- the chip: try  fact water_hot true  then  button heater_on  (Ctrl-A X to leave)"
  qemu-system-xtensa -nographic -machine esp32s3 \
    -drive "file=$P/build/aquarium-test/flash.bin,if=mtd,format=raw"
fi
' bash "$@"
