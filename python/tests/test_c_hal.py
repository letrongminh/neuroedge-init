"""
TSK-S4-01 (first slice), DP-B-08 — on the device a pin goes active only on a token.

`targets/esp32s3/components/ne_hal/` is the one door from firmware to a `digital.out` pin:
`ne_hal_on` asks the ledger (`ne_token_authorize`) and writes nothing on a refusal; `ne_hal_off`
is the safe state and needs no token, as on the host. Compiled here with AddressSanitizer and
UndefinedBehaviorSanitizer against a fake writer that records every level.
"""

from __future__ import annotations

import re
import subprocess

from .test_c_walker import STACK_LIMIT, STRICT, cc

SAN = ["-fsanitize=address,undefined", "-fno-sanitize-recover=all", "-fno-omit-frame-pointer"]


def components(root):
    return root / "targets" / "esp32s3" / "components"


def test_a_pin_moves_only_on_its_own_live_token(root, tmp_path):
    """TC-B-08-1: no token, a closed token, another pin's token -> refused, the pin unchanged."""
    base = components(root)
    exe = tmp_path / "hal"
    command = [
        cc(),
        *STRICT,
        "-O1",
        "-g",
        *SAN,
        "-I",
        str(base / "ne_hal" / "include"),
        "-I",
        str(base / "ne_gate" / "include"),
        str(base / "ne_hal" / "src" / "ne_hal.c"),
        str(base / "ne_gate" / "src" / "ne_token.c"),
        str(base / "ne_gate" / "src" / "ne_walker.c"),
        str(base / "ne_hal" / "test" / "test_hal_host.c"),
        "-o",
        str(exe),
    ]
    built = subprocess.run(command, capture_output=True, text=True)
    assert built.returncode == 0, built.stderr
    ran = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)
    assert ran.returncode == 0 and not ran.stderr, ran.stderr
    cases = {
        name: (int(status), reason, levels)
        for _, name, status, reason, levels in (
            line.split("\t") for line in ran.stdout.splitlines() if line.startswith("case")
        )
    }
    refused, ok, argument = 1, 0, 2
    assert cases == {
        "no token": (refused, "not_a_token", "000"),
        "another pin": (refused, "pin_not_granted", "000"),
        "its pin": (ok, "authorized", "100"),
        "again": (refused, "token_replayed", "100"),
        "off, no token": (ok, "authorized", "000"),  # the safe state is never refused
        "closed token": (refused, "token_replayed", "000"),
        "expired": (refused, "token_expired", "000"),
        "forged": (refused, "unknown_token", "000"),
        "no such pin": (argument, "not_a_token", "000"),
    }
    assert "writes\t2" in ran.stdout  # one on, one off: a refusal never reaches the writer


def test_the_hal_door_uses_no_static_ram_and_a_small_stack(root, tmp_path):
    base = components(root)
    obj = tmp_path / "ne_hal.o"
    command = [
        cc(),
        *STRICT,
        "-O2",
        "-fstack-usage",
        "-I",
        str(base / "ne_hal" / "include"),
        "-I",
        str(base / "ne_gate" / "include"),
        "-c",
        str(base / "ne_hal" / "src" / "ne_hal.c"),
        "-o",
        str(obj),
    ]
    result = subprocess.run(command, capture_output=True, text=True, cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    symbols = subprocess.run(["nm", str(obj)], capture_output=True, text=True, check=True).stdout
    assert not [line for line in symbols.splitlines() if re.search(r"\s[bBdDC]\s", line)]
    usage = (tmp_path / "ne_hal.su").read_text()
    frames = {m.group(1): int(m.group(2)) for m in re.finditer(r":(\w+)\s+(\d+)\s+\w+", usage)}
    assert {"ne_hal_on", "ne_hal_off"} <= frames.keys()
    assert max(frames.values()) <= STACK_LIMIT, frames
