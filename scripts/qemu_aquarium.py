#!/usr/bin/env python3
"""
The fish tank on one chip, on Espressif QEMU (demo/i2b-be-ca-gia-lap/, D3 and D5). Used by
.github/workflows/firmware-qemu.yml, job `aquarium-qemu`.

    python3 scripts/qemu_aquarium.py <build dir>

The build is `neuroedge build --target esp32s3 --brain neuroclaw` of fixtures/agents/aquarium
with sdkconfig.qemu: brain and gate in one image, no network in the emulator. The chip has no
water probe here: the console's `fact water_hot true|false|-` stands in for it (DP-B-05), and
`button` is the board's own way to call an action (DP-B-16). One boot, its log kept as
<build dir>/aquarium-test/boot-1.log, where the workflow reads the NE1 sessions back:

  * cool water: heater, air pump and light come on (`NE_PIN … level=1`);
  * warm water: the heater is refused, the air pump cannot be turned off and nothing is asked;
  * no reading: the heater is refused (`criterion_unavailable`);
  * cool again: turning the air pump off opens a question only the board's button answers;
    a yes turns it off.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from qemu_brain import output_of  # noqa: E402
from qemu_console import Boot, Fail, free_port  # noqa: E402


def press(b: Boot, line: str, *patterns: str) -> str:
    """One console line; every pattern must be in what it printed. Returns that output."""
    out = output_of(b, line)
    for pattern in patterns:
        if not re.search(pattern, out, re.MULTILINE):
            raise Fail(f"`{line}` printed no /{pattern}/ (log: {b.log}):\n{out}")
    return out


def result(tool: str, status: str) -> str:
    return rf'^NE_BUTTON \{{"tool":"{tool}","status":"{status}"'


def run(build: Path) -> list[str]:
    work = build / "aquarium-test"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    flash = work / "flash.bin"
    subprocess.run(
        ["esptool.py", "--chip", "esp32s3", "merge_bin", "--fill-flash-size", "16MB"]
        + ["-o", str(flash), "@flash_args"],
        cwd=build,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    evidence: list[str] = []
    b = Boot(flash, work / "boot-1.log", free_port())
    try:
        b.expect(r"^NE_RISK risk=single_chip$")
        b.expect(r"^NE_BRAIN SELFTEST PASS tools=6$")
        b.expect(r"^NE_CONSOLE READY mode=normal$")
        press(b, "fact owner_confirmed false", r"^NE_FACT owner_confirmed=false$")

        press(b, "fact water_hot false", r"^NE_FACT water_hot=false$")
        for tool, pin in (
            ("tank_heater_on", "gate_relay"),
            ("tank_aerator_on", "door_lock"),
            ("tank_light_on", "porch_light"),
        ):
            press(b, f"button {tool}", result(tool, "ALLOW"), rf"^NE_PIN pin={pin} level=1$")
        evidence.append("cool water: heater, air pump and light on")

        press(b, "fact water_hot true", r"^NE_FACT water_hot=true$")
        press(
            b,
            "button tank_heater_on",
            result("tank_heater_on", "BLOCK") + r'.*"failed_criterion":"water_hot"',
        )
        out = press(b, "button tank_aerator_off", result("tank_aerator_off", "BLOCK"))
        if '"confirmation"' in out or "NE_PIN" in out:
            raise Fail(f"warm water: the air pump question was opened or a pin moved:\n{out}")
        evidence.append("warm water: heater refused, air pump kept on, nothing asked")

        press(b, "fact water_hot -", r"^NE_FACT water_hot=-$")
        out = press(
            b,
            "button tank_heater_on",
            result("tank_heater_on", "BLOCK") + r'.*"reason":"criterion_unavailable"',
        )
        if "NE_PIN" in out:
            raise Fail(f"no reading: a pin moved:\n{out}")
        evidence.append("no reading: heater refused (criterion_unavailable)")

        press(b, "fact water_hot false", r"^NE_FACT water_hot=false$")
        out = press(
            b, "button tank_aerator_off", result("tank_aerator_off", "BLOCK"), r'"on_block":"ask"'
        )
        asked = re.search(r'"id":"(confirm_\d+)"', out)
        if asked is None or "NE_PIN" in out:
            raise Fail(f"cool water: no question for the air pump, or a pin moved:\n{out}")
        press(
            b,
            f"button {asked.group(1)} yes",
            result("tank_aerator_off", "ALLOW"),
            r"^NE_PIN pin=door_lock level=0$",
        )
        press(
            b,
            "button tank_heater_off",
            result("tank_heater_off", "ALLOW"),
            r"^NE_PIN pin=gate_relay level=0$",
        )
        evidence.append("cool water: the button's yes turned the air pump off; heater off")
    finally:
        b.stop()
    return evidence


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__.strip().splitlines()[4], file=sys.stderr)
        return 2
    try:
        evidence = run(Path(argv[1]).resolve())
    except (Fail, subprocess.CalledProcessError) as error:
        print(f"::error::{error}")
        return 1
    print("The fish tank on one chip, on QEMU: every step passed")
    for line in evidence:
        print(f"  {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
