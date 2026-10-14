#!/usr/bin/env bash
set -euo pipefail

# Prepare demo I4 — talk to the agent through the laptop microphone (TSK-I4-04, Q-50).
# Creates the home-voice agent in $DEMO, adds audio.in and voice.toml (STT, TTS, System 2 via OpenRouter).

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HERE="$REPO_ROOT/demo/i4-thoai-laptop"
VENV_DIR="$REPO_ROOT/python/.venv"
NE_BIN="$VENV_DIR/bin/neuroedge"
DEMO="${DEMO:-/tmp/neuroedge-demo-voice}"

if [[ "$DEMO" != /tmp/* ]] || [[ "$DEMO" == "/tmp/" ]] || [[ "$DEMO" =~ \.\. ]]; then
  echo "Error: DEMO must be under /tmp (path: '$DEMO')" >&2
  exit 1
fi

if [[ ! -d "$VENV_DIR" ]]; then
  echo "==> Creating the Python virtual environment at $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi
echo "==> Installing neuroedge with the [dev,mcp,cloud,audio] extras (litellm, sounddevice)"
"$VENV_DIR/bin/python" -m pip install -q -e "$REPO_ROOT/python[dev,mcp,cloud,audio]"

echo "==> Recreating $DEMO and the agent 'nha' from the home-voice template"
rm -rf "$DEMO" && mkdir -p "$DEMO"
(cd "$DEMO" && "$NE_BIN" new nha --template home-voice)

echo "==> Adding audio.in to [requires] and appending voice.toml"
"$VENV_DIR/bin/python" - "$DEMO/nha/agent.toml" "$HERE/voice.toml" <<'PY'
import sys
agent, snippet = sys.argv[1], sys.argv[2]
text = open(agent, encoding="utf-8").read()
line = '"audio.out"   = {}\n'
if line not in text:
    sys.exit("the template's agent.toml changed: no audio.out line found in [requires]")
text = text.replace(line, '"audio.in"    = {}\n' + line, 1)
open(agent, "w", encoding="utf-8").write(text + open(snippet, encoding="utf-8").read())
PY

echo "==> Checking the gates and building for sim"
(cd "$DEMO/nha" && "$NE_BIN" gate lint gates && "$NE_BIN" build --target sim --board sim-default >/dev/null)

if [[ -z "${OPENROUTER_API_KEY:-}" ]]; then
  echo "!! OPENROUTER_API_KEY is not set in this shell: export OPENROUTER_API_KEY=… before running the demo." >&2
fi

echo ""
echo "==> Ready. Put on headphones, then:"
echo "    cd $DEMO/nha && $NE_BIN run --mic"
echo "    (external speakers: add --half-duplex)"
