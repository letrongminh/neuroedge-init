#!/usr/bin/env python3
"""
One image of box and brain, inspected (Q-83 Profile B). Used by
.github/workflows/firmware-qemu.yml, job `brain-firmware`.

    python3 scripts/check_brain_image.py --symbols <nm output> --project <ESP-IDF project>

Two checks, both on what was built, not on what the docs say:

1. **Symbols** (TC-B-02-1, DP-B-02): `xtensa-esp32s3-elf-nm` of the image. Brain and gate talk
   through `nc_gate` function calls, so the image holds both ends (`neuroclaw_start`,
   `ne_bridge_call`) and no server: no HTTP server, no TLS server role, no MCP server.
2. **One owner of Wi-Fi** (TC-B-11-1, DP-B-11, the static half): NeuroClaw-ESP's sources never
   initialise or start Wi-Fi, and `main/brain.c` starts it exactly once. The QEMU half (one
   console with both command sets) is scripts/qemu_brain.py.

Any missing input is a failure: nothing checked is not a pass.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Both ends of `nc_gate` must be linked: otherwise this is not the combined image.
REQUIRED = ("neuroclaw_start", "ne_bridge_call", "ne_bridge_answer")
# A server of any kind on the chip: HTTP, TLS server handshake or session tickets, MCP.
FORBIDDEN = re.compile(
    r"^(httpd_start|httpd_ssl_start|mbedtls_ssl_handshake_server_step"
    r"|mbedtls_ssl_conf_session_tickets_cb|mbedtls_ssl_cookie_setup|mbedtls_ssl_ticket_setup"
    r"|.*mcp_?server.*)$",
    re.IGNORECASE,
)
WIFI_SETUP = re.compile(r"\besp_wifi_(init|start)\s*\(")
WIFI_START = re.compile(r"\besp_wifi_start\s*\(")


def symbols(text: str) -> set[str]:
    """Names from `nm` output: `<address> <type> <name>` or `<type> <name>` (undefined)."""
    names = set()
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 2 and len(parts[-2]) == 1:
            names.add(parts[-1])
    return names


def check_symbols(path: Path) -> list[str]:
    try:
        names = symbols(path.read_text(encoding="utf-8", errors="replace"))
    except OSError as error:
        return [f"{path}: {error}"]
    if not names:
        return [f"{path}: no symbols — not `nm` output of the image"]
    errors = [
        f"{name}: not linked, so this is not the image of box and brain"
        for name in REQUIRED
        if name not in names
    ]
    servers = sorted(n for n in names if FORBIDDEN.match(n))
    errors += [f"{name}: a server on the chip (DP-B-02 allows none)" for name in servers]
    if not errors:
        print(f"symbols: {len(names)}; {', '.join(REQUIRED)} linked; no server symbol")
    return errors


def check_wifi_owner(project: Path) -> list[str]:
    brain = project / "components" / "neuroclaw"
    main = project / "main" / "brain.c"
    if not brain.is_dir() or not main.is_file():
        return [f"{project}: no components/neuroclaw or main/brain.c — not a --brain project"]
    errors = []
    for source in sorted(brain.rglob("*.c")):
        if source.relative_to(brain).parts[0] == "test":
            continue
        for number, line in enumerate(source.read_text(errors="replace").splitlines(), 1):
            if WIFI_SETUP.search(line):
                errors.append(f"{source}:{number}: the brain sets Wi-Fi up itself (DP-B-11)")
    starts = len(WIFI_START.findall(main.read_text(errors="replace")))
    if starts != 1:
        errors.append(f"{main}: {starts} esp_wifi_start calls, one expected (DP-B-11)")
    if not errors:
        print("Wi-Fi: started once, by main/brain.c; never by NeuroClaw-ESP")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--symbols", type=Path, required=True, help="`nm` output of the .elf")
    parser.add_argument("--project", type=Path, required=True, help="the rendered project")
    args = parser.parse_args(argv)
    errors = check_symbols(args.symbols) + check_wifi_owner(args.project)
    for error in errors:
        print(f"::error::{error}")
    if not errors:
        print("ok")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
