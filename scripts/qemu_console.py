#!/usr/bin/env python3
"""
Boot guard, safe mode, the owner's settings and the serial console on Espressif
QEMU (Q-79, TSK-I2f-10). Used by .github/workflows/firmware-qemu.yml.

    python3 scripts/qemu_console.py <build dir>

Needs the ESP-IDF environment (`. $IDF_PATH/export.sh`, v5.4) with qemu-xtensa
installed; the build is the QEMU one (sdkconfig.defaults;sdkconfig.qemu). One
flash image, one QEMU process per boot, the UART on a TCP socket so the script
can type at the console:

  1-3  three boots that never stay up: each counts itself (NE_BOOT count=1..3,
       mode=normal) and is stopped right after its startup, before the stable
       window — power lost, as far as the chip can tell;
  4    the fourth starts in safe mode: no gate self-test, the console only.
       The owner sets the bot token at the hidden prompt (an inline secret is
       refused), an owner id (a malformed one is refused), an http:// LLM URL
       (stored, labelled risk=cleartext_url), reads the token back as
       <secret>, clears the boot guard and reboots;
  5    a normal boot again (count=1, self-test, NE_TRACE DONE); the settings
       survived the reboot; the console task's free stack clears the floor;
       `factory-reset confirm` erases them;
  6    the token is gone.

The token never appears in any UART log: not echoed, not printed back. Each
boot's log is kept as <build dir>/console-test/boot-<n>.log. Any missing line,
line that must not appear, or timeout is exit 1.

QEMU 9.0's esp32s3 model loses flash writes on `-no-reboot`'s exit path and
cannot survive a warm reset after flash writes (scripts/qemu_ota.sh): the
emulator is stopped with SIGTERM after the device's own reset line, and started
again for the next boot.
"""

from __future__ import annotations

import re
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

TIMEOUT_S = 90.0
STACK_FLOOR = 512  # bytes the console task must still have free after `config set`
# Made up for the test: the shape of a BotFather token, no real bot.
TOKEN = "7000000001:AAQemuOnlyNotARealTokenxxxxxxxxxxxx"
OWNER = "123456789"
LLM_URL = "http://10.0.2.2:11434/v1/chat/completions"


class Fail(Exception):
    pass


class Boot:
    """One QEMU process on the shared flash image, its UART on a TCP socket."""

    def __init__(self, flash: Path, log: Path, port: int) -> None:
        self.log = log
        self.text = ""
        self.pos = 0  # what expect() has consumed
        self.proc = subprocess.Popen(
            [
                "qemu-system-xtensa",
                "-machine",
                "esp32s3",
                "-display",
                "none",
                "-monitor",
                "none",
                "-drive",
                f"file={flash},if=mtd,format=raw",
                "-serial",
                f"tcp:127.0.0.1:{port},server=on,wait=on",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        deadline = time.monotonic() + 30
        while True:
            try:
                self.sock = socket.create_connection(("127.0.0.1", port), timeout=1)
                break
            except OSError:
                if self.proc.poll() is not None or time.monotonic() > deadline:
                    raise Fail(f"QEMU did not open the UART socket: {self._stderr()}") from None
                time.sleep(0.1)
        self.sock.settimeout(0.1)

    def _stderr(self) -> str:
        if self.proc.poll() is None or self.proc.stderr is None:
            return ""
        return self.proc.stderr.read().decode(errors="replace").strip()

    def _pump(self) -> None:
        try:
            data = self.sock.recv(4096)
        except TimeoutError:
            return
        except OSError:
            data = b""
        if data:
            self.text += data.decode(errors="replace").replace("\r", "")
            self.log.write_text(self.text)
        elif self.proc.poll() is not None:
            raise Fail(f"QEMU exited (log: {self.log})")
        else:
            time.sleep(0.05)

    def expect(self, pattern: str, timeout: float = TIMEOUT_S) -> re.Match[str]:
        """The first line matching `pattern` (anchored at column 0) after the last match."""
        regex = re.compile(pattern, re.MULTILINE)
        deadline = time.monotonic() + timeout
        while True:
            match = regex.search(self.text, self.pos)
            if match:
                self.pos = match.end()
                return match
            if time.monotonic() > deadline:
                tail = self.text[-600:]
                raise Fail(f"no /{pattern}/ within {timeout:.0f}s (log: {self.log})\n{tail}")
            self._pump()

    def send(self, line: str) -> None:
        # One byte at a time, like a person at a terminal: QEMU's UART FIFO is small.
        for byte in (line + "\r").encode():
            self.sock.sendall(bytes([byte]))
            time.sleep(0.002)

    def command(self, line: str, pattern: str) -> re.Match[str]:
        self.expect(r"neuroedge(\(safe\))?> ")
        self.send(line)
        return self.expect(pattern)

    def forbid(self, pattern: str) -> None:
        if re.search(pattern, self.text, re.MULTILINE):
            raise Fail(f"/{pattern}/ must not appear (log: {self.log})")

    def stop(self) -> None:
        """SIGTERM: QEMU flushes the flash file on a clean stop."""
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()
        self.sock.close()


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def run(build: Path) -> list[str]:
    work = build / "console-test"
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
        # 1-3: boots that never stay up.
        for n in (1, 2, 3):
            b = boot(n)
            note(b, b.expect(rf"^NE_BOOT count={n} max=4 mode=normal reason=\w+$"))
            b.expect(r"^NE_SELFTEST PASS walker=\d+ token=\d+")
            b.expect(r"^NE_TRACE DONE sessions=\d+")
            b.expect(r"^NE_CONSOLE READY mode=normal$")
            b.stop()

        # 4: safe mode, the console only.
        b = boot(4)
        note(b, b.expect(r"^NE_BOOT count=4 max=4 mode=safe reason=\w+$"))
        note(b, b.expect(r"^NE_CONFIG STORAGE plaintext risk=readable_flash$"))
        note(b, b.expect(r"^NE_CONSOLE READY mode=safe$"))
        note(b, b.command("status", r"^NE_STATUS mode=safe boot=4/4 storage=plaintext .*$"))
        note(
            b,
            b.command(
                f"config set telegram.token {TOKEN[:12]}",
                r"^NE_CONFIG REFUSED key=telegram\.token reason=inline_secret$",
            ),
        )
        b.expect(r"neuroedge\(safe\)> ")
        b.send("config set telegram.token")
        b.expect(r"telegram\.token \(hidden, Enter to finish\): ")
        b.send(TOKEN)
        note(
            b,
            b.expect(r"^NE_CONFIG SET key=telegram\.token storage=plaintext risk=readable_flash$"),
        )
        note(
            b,
            b.command(
                "config set telegram.owner 12ab",
                r"^NE_CONFIG REFUSED key=telegram\.owner reason=format$",
            ),
        )
        note(
            b,
            b.command(
                f"config set telegram.owner {OWNER}",
                r"^NE_CONFIG SET key=telegram\.owner storage=plaintext$",
            ),
        )
        note(
            b,
            b.command(
                f"config set llm.url {LLM_URL}",
                r"^NE_CONFIG SET key=llm\.url storage=plaintext risk=cleartext_url$",
            ),
        )
        note(b, b.command("config get telegram.token", r"^telegram\.token = <secret>$"))
        note(b, b.command("bootguard clear", r"^NE_BOOT CLEARED$"))
        b.command("reboot", r"^NE_CONSOLE REBOOT$")
        b.expect(r"^rst:0[xX]")
        b.forbid(r"^NE_SELFTEST ")
        b.stop()

        # 5: normal again, the settings survived; then a factory reset.
        b = boot(5)
        note(b, b.expect(r"^NE_BOOT count=1 max=4 mode=normal reason=\w+$"))
        b.expect(r"^NE_SELFTEST PASS walker=\d+ token=\d+")
        b.expect(r"^NE_TRACE DONE sessions=\d+")
        b.expect(r"^NE_CONSOLE READY mode=normal$")
        note(b, b.command("config get telegram.owner", rf"^telegram\.owner = {OWNER}$"))
        note(b, b.command("config get telegram.token", r"^telegram\.token = <secret>$"))
        b.command("config set wifi.pass", r"wifi\.pass \(hidden, Enter to finish\): ")
        b.send("not-the-token-1")
        b.expect(r"^NE_CONFIG SET key=wifi\.pass storage=plaintext risk=readable_flash$")
        status = b.command("status", r"^NE_STATUS mode=normal .* stack_free=(\d+) stack=(\d+)$")
        note(b, status)
        if int(status.group(1)) < STACK_FLOOR:
            raise Fail(
                f"the console task has {status.group(1)} of {status.group(2)} bytes of stack "
                f"left after `config set`, under the {STACK_FLOOR}-byte floor"
            )
        note(b, b.command("factory-reset", r"^Type `factory-reset confirm` to go ahead\.$"))
        b.command("factory-reset confirm", r"^NE_CONSOLE FACTORY_RESET$")
        b.expect(r"^rst:0[xX]")
        b.stop()

        # 6: everything the owner stored is gone.
        b = boot(6)
        note(b, b.expect(r"^NE_BOOT count=1 max=4 mode=normal reason=\w+$"))
        b.expect(r"^NE_CONSOLE READY mode=normal$")
        note(b, b.command("config get telegram.token", r"^telegram\.token = <unset>$"))
        note(b, b.command("config get telegram.owner", r"^telegram\.owner = <unset>$"))
        b.stop()
    finally:
        for b in boots:
            b.stop()

    for b in boots:
        for secret in (TOKEN, TOKEN.split(":", 1)[1], "not-the-token-1"):
            if secret in b.text:
                raise Fail(f"a secret reached the UART (log: {b.log})")
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
    print("Boot guard, safe mode and console on QEMU: all boots passed")
    for line in evidence:
        print(f"  {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
