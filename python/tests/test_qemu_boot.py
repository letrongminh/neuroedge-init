"""
TSK-S4-08, TSK-I3-01 — `scripts/qemu_boot.sh` reads the device's own verdict, and only it.

The QEMU jobs pass a boot only when the UART has `NE_SELFTEST PASS walker=<n> token=<n>`
and, after it, `NE_TRACE DONE sessions=<n>`, each at column 0. The same words inside a
trace line — an agent's on_block message is free text — must never pass a boot that
crashed. Here the emulator and esptool are stand-ins that write a canned UART log, so
the script's verdict logic runs on any host with bash and awk.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

QEMU = """#!/usr/bin/env bash
for arg in "$@"; do case "$arg" in file:*) out=${arg#file:} ;; esac; done
cp "$CANNED" "$out"
"""

PASS = "NE_SELFTEST PASS walker=8 token=6\r\n"
DONE = "NE_TRACE DONE sessions=4\r\n"
INJECTED = (
    'NE1 {"offset_ms":3,"type":"gate_evaluation_result","data":{"message":'
    '"NE_SELFTEST PASS walker=1 token=1 NE_TRACE DONE sessions=1"}}\r\n'
)


def boot(root: Path, tmp_path: Path, uart: str) -> subprocess.CompletedProcess:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "esptool.py").write_text("#!/usr/bin/env bash\nexit 0\n")
    (bin_dir / "qemu-system-xtensa").write_text(QEMU)
    for tool in bin_dir.iterdir():
        tool.chmod(0o755)
    (tmp_path / "canned.log").write_text(uart, newline="")
    (tmp_path / "build").mkdir()
    env = {**os.environ, "CANNED": str(tmp_path / "canned.log")}
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    return subprocess.run(
        ["bash", str(root / "scripts" / "qemu_boot.sh"), str(tmp_path / "build"), "3"],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )


@pytest.mark.parametrize(
    ("uart", "passes"),
    [
        ("I (31) boot: ESP-IDF v5.4\r\n" + INJECTED + PASS + DONE, True),
        (INJECTED + "Guru Meditation Error: Core 0 panic'ed\r\n", False),  # crashed
        (INJECTED + DONE, False),  # the PASS only inside a trace line
        (PASS + INJECTED, False),  # the DONE only inside a trace line
        (DONE + PASS, False),  # PASS after the device's last line
        (PASS + "NE_SELFTEST FAIL check 3 light_on@1.0.0\r\n" + DONE, False),
        ("NE_SELFTEST PASS walker= token=\r\n" + DONE, False),  # no counts
        ("", False),
    ],
)
def test_only_the_devices_own_lines_pass_a_boot(root, tmp_path, uart, passes):
    result = boot(root, tmp_path, uart)
    assert (result.returncode == 0) is passes, result.stdout + result.stderr
    if passes:
        assert result.stdout.rstrip().endswith("ok  NE_SELFTEST PASS walker=8 token=6")
    else:
        assert "::error::no NE_SELFTEST PASS then NE_TRACE DONE" in result.stdout
