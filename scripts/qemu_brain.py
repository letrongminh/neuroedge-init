#!/usr/bin/env python3
"""
One image of box and brain on Espressif QEMU (Q-83 Profile B, TSK-I2f-14/15/16). Used by
.github/workflows/firmware-qemu.yml, job `brain-firmware`.

    python3 scripts/qemu_brain.py <build dir>

The build is `neuroedge build --target esp32s3 --brain neuroclaw` of the demo agent
(fixtures/agents/chat-den-cua), with sdkconfig.qemu: no Wi-Fi in the emulator, so this is also
the image without a network (DP-B-16). Driven like scripts/qemu_console.py (one QEMU process
per boot, the UART on TCP); each boot's log is kept as <build dir>/brain-test/boot-<n>.log.

  1  a fresh flash: `risk=readable_flash` and `risk=single_chip` at boot and in `status`
     (TC-B-14-1); the bridge self-check passes before the update is kept (DP-B-15); one
     console holds the box's commands and the brain's (TC-B-11-1); the brain does not start
     without its settings. Offline, the board's buttons go through the gate: the light turns
     off, the door at night is refused, exactly as the box decides (TC-B-16-1), and each
     decision is an NE1 session (TC-B-12-1, replayed by the workflow). Then every setting
     the brain needs is stored, secrets at the hidden prompt after `config ack` (TC-B-10-1,
     TC-B-17-1), and the chip reboots;
  2  the brain starts from those settings (TC-B-10-1); `tasks` reports each task's stack
     (TC-B-13-1, checked by check_stack_usage.py --task).

No secret ever reaches the UART: not echoed, not printed back, not by the brain.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from qemu_console import Boot, Fail, free_port  # noqa: E402

# Made up for the test: shapes the checks accept, no real account.
TOKEN = "7000000002:AAQemuBrainNotARealTokenyyyyyyyyyyy"
OWNER = "123456789"
SECRETS = {
    "telegram.token": TOKEN,
    "llm.key": "sk-qemu-brain-not-a-real-key-1",
    "llm.fallback_key": "sk-qemu-brain-not-a-real-key-2",
    "search.key": "tvly-qemu-brain-not-a-real-key-3",
    "wifi.pass": "qemu-brain-not-a-wifi-pass",
}
SETTINGS = {
    "telegram.owner": OWNER,
    "llm.url": "https://10.0.2.2:8443/v1/chat/completions",
    "llm.model": "qemu-model",
    "llm.fallback_url": "https://10.0.2.2:8444/v1/chat/completions",
    "llm.fallback_model": "qemu-fallback",
    "tz": "ICT-7",
    "wifi.ssid": "qemu-home",
}
PROMPT = r"neuroedge> "


def after(b: Boot, mark: int, *patterns: str) -> list[re.Match[str]]:
    """Each pattern somewhere after `mark`, in any order: the console task and main print at once."""
    found = []
    for pattern in patterns:
        b.pos = mark
        found.append(b.expect(pattern))
    b.pos = max(m.end() for m in found)
    return found


def output_of(b: Boot, line: str) -> str:
    """Everything a command printed, up to the next prompt."""
    b.expect(PROMPT)
    start = len(b.text)
    b.send(line)
    b.expect(PROMPT)
    b.pos -= len(PROMPT)  # the prompt belongs to the next command
    return b.text[start : b.pos]


def run(build: Path) -> list[str]:
    work = build / "brain-test"
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
    boots: list[Boot] = []

    def boot(n: int) -> Boot:
        b = Boot(flash, work / f"boot-{n}.log", free_port())
        boots.append(b)
        return b

    def note(b: Boot, match: re.Match[str]) -> None:
        evidence.append(f"boot {boots.index(b) + 1}: {match.group(0).strip()}")

    try:
        b = boot(1)
        note(b, b.expect(r"^NE_CONFIG STORAGE plaintext risk=readable_flash$"))
        note(b, b.expect(r"^NE_RISK risk=single_chip$"))
        b.expect(r"^NE_SELFTEST PASS walker=\d+ token=\d+")
        note(b, b.expect(r"^NE_BRAIN SELFTEST PASS tools=[1-9]\d*$"))
        mark = b.expect(r"^NE_TRACE DONE sessions=\d+").end()
        # no settings yet: the brain does not start
        for match in after(
            b, mark, r"^NE_CONSOLE READY mode=normal$", r"^NE_WIFI OFF$", r"^NE_BRAIN OFF$"
        ):
            note(b, match)
        note(b, b.command("status", r"^NE_STATUS .*risk=readable_flash risk=single_chip .*$"))
        listed = output_of(b, "help")
        for command in ("config", "status", "button", "tasks", "memory_read", "diag"):
            if not re.search(rf"^{command}\b", listed, re.MULTILINE):
                raise Fail(f"`help` on the one console lacks {command} (log: {b.log})")
        evidence.append("boot 1: one console, the box's commands and the brain's")

        # Offline, the board's buttons (DP-B-16), as the box decides them.
        b.command("fact light_fault_free true", r"^NE_FACT light_fault_free=true$")
        b.command("fact daytime false", r"^NE_FACT daytime=false$")
        b.command("fact owner_confirmed false", r"^NE_FACT owner_confirmed=false$")
        note(
            b,
            b.command(
                "button living_light_off",
                r'^NE_BUTTON \{"tool":"living_light_off","status":"ALLOW"\}$',
            ),
        )
        note(
            b,
            b.command(
                "button front_door_unlock duration_s=10",
                r'^NE_BUTTON \{"tool":"front_door_unlock","status":"BLOCK","gate":"door@[^"]+",'
                r'"reason":"condition_not_met","failed_criterion":"daytime".*$',
            ),
        )
        note(
            b,
            b.command(
                "button nothing_here", r'^NE_BUTTON \{"tool":"nothing_here","status":"REJECTED".*$'
            ),
        )

        # Every setting the brain needs, secrets at the hidden prompt after the acknowledgement.
        b.command(
            "config set llm.key", r"^NE_CONFIG REFUSED key=llm\.key reason=risk_not_acknowledged$"
        )
        note(b, b.command("config ack readable_flash", r"^NE_CONFIG ACK risk=readable_flash$"))
        for key, value in SETTINGS.items():
            b.command(
                f"config set {key} {value}",
                rf"^NE_CONFIG SET key={re.escape(key)} storage=plaintext",
            )
        for key, value in SECRETS.items():
            b.command(f"config set {key}", rf"{re.escape(key)} \(hidden, Enter to finish\): ")
            b.send(value)
            b.expect(rf"^NE_CONFIG SET key={re.escape(key)} storage=plaintext risk=readable_flash$")
        evidence.append(f"boot 1: {len(SETTINGS) + len(SECRETS)} settings stored")
        b.command("reboot", r"^NE_CONSOLE REBOOT$")
        b.expect(r"^rst:0[xX]")
        b.stop()

        b = boot(2)
        b.expect(r"^NE_RISK risk=single_chip$")
        mark = b.expect(r"^NE_BRAIN SELFTEST PASS tools=[1-9]\d*$").end()
        for match in after(b, mark, r"^NE_CONSOLE READY mode=normal$", r"^NE_BRAIN STARTED$"):
            note(b, match)
        b.forbid(r"^NC_OFF missing=")
        note(b, b.command("config get telegram.token", r"^telegram\.token = <secret>$"))
        for task in ("neuroclaw", "ne_console"):
            note(b, b.command("tasks", rf"^NE_STACK task={task} free_min=\d+ size=\d+$"))
        b.stop()
    finally:
        for b in boots:
            b.stop()

    for b in boots:
        for secret in [*SECRETS.values(), TOKEN.split(":", 1)[1]]:
            if secret in b.text:
                raise Fail(f"a secret reached the UART (log: {b.log})")
    evidence.append("no secret in any boot log")
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
    print("Box and brain in one image on QEMU: all boots passed")
    for line in evidence:
        print(f"  {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
