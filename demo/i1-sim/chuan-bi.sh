#!/usr/bin/env bash
set -euo pipefail

# Demo environment setup for increment I1 (sim target).
# Decision Q-49: every increment has a reproducible demo.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

echo "==> NeuroEdge i1-sim: Setting up the demo environment..."

# 1. Create the virtual environment if missing and install the package
VENV_DIR="$REPO_ROOT/python/.venv"
if [[ ! -d "$VENV_DIR" ]]; then
  echo "==> Creating the Python virtual environment at $VENV_DIR..."
  python3 -m venv "$VENV_DIR"
fi

NE_PYTHON="$VENV_DIR/bin/python"
NE_BIN="$VENV_DIR/bin/neuroedge"

echo "==> Installing neuroedge with the [dev,mcp] extras (editable mode)..."
"$NE_PYTHON" -m pip install -e "$REPO_ROOT/python[dev,mcp]"

# 2. Set up the demo directory and check it is safe to wipe
DEMO="${DEMO:-/tmp/neuroedge-demo}"

# Refuse if DEMO is not under /tmp, is /tmp or /tmp/ itself, or contains ..
if [[ "$DEMO" != /tmp/* ]] || [[ "$DEMO" == "/tmp" ]] || [[ "$DEMO" == "/tmp/" ]] || [[ "$DEMO" =~ \.\. ]]; then
  echo "Error: DEMO must be under /tmp (path: '$DEMO')" >&2
  exit 1
fi

echo "==> Wiping and recreating the demo directory at $DEMO..."
rm -rf "$DEMO"
mkdir -p "$DEMO"

# 3. Create the three sample projects
for tmpl in villa-concierge home-voice factory-monitor; do
  echo "==> Creating sample project '$tmpl' from template '$tmpl'..."
  (cd "$DEMO" && "$NE_BIN" new "$tmpl" --template "$tmpl")
done

# 4. Run gate lint and the tests in each project
for tmpl in villa-concierge home-voice factory-monitor; do
  echo "==> Checking project '$tmpl' (gate lint)..."
  (cd "$DEMO/$tmpl" && "$NE_BIN" gate lint gates)
  echo "==> Checking project '$tmpl' (test)..."
  (cd "$DEMO/$tmpl" && "$NE_BIN" test)
done

echo ""
echo "==> The I1 demo environment is ready at $DEMO!"
echo "==> Next, to run the demo:"
echo "    cd $DEMO && alias ne=\"$NE_BIN\""
echo "    # Read the demo script at: $REPO_ROOT/demo/i1-sim/kich-ban.md"
