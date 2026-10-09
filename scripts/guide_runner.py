#!/usr/bin/env python3
"""
Extracts and runs the command blocks of the partner guides (`docs/user/doi-tac/`, TSK-I2c-19).

The guides are executable: every fenced block of shell or Python in them is either run here, in
order, against local doubles, or explicitly skipped with a stated reason. `partner_guides_check.sh`
installs a wheel into a clean venv and calls this; `python/tests/test_partner_guides.py` imports
`extract` (no wheel, no network) so CI catches a guide that drifts from the rules below.

MARKERS. A fenced block is marked by an HTML comment on the line right before it (invisible when
the guide is rendered):

    <!-- guide: run expect="BLOCK" expect="criterion_unavailable" -->
    ```bash
    neuroedge proxy http --config plug/guard.toml
    ```

Rules, enforced by `extract`:

* every block whose language is bash/sh/shell/zsh/python/py has a marker, and that marker is `run`
  or `skip reason="..."` — no unmarked command block, no silent skip;
* blocks of any other language (toml, yaml, json, text…) are shown as they are; a marker is optional.

Words of a marker (shell-style quoting; a word may repeat where it says so):

    run                    run it (bash -e -o pipefail, or the venv's python for a python block)
    skip reason="..."      do not run it; the reason is printed
    exit=N                 the exit status it must end with (default 0; `exit=1` for a failure a guide shows)
    expect="text"          the output (stdout + stderr) must contain text; repeatable
    bg=NAME                start it in the background under NAME (a server); needs wait=
    wait="host:port"       with bg: wait until that address accepts connections
    stop=NAME              before this block, stop the background process NAME (SIGTERM; waits for it)
    log_has="VAR|text"     after it, the file named by environment variable VAR (a double's request
    log_lacks="VAR|text"   log) must contain / must not contain text; repeatable

Every command runs in a directory of its own per guide, with the venv first on PATH and the doubles'
addresses in the environment (HA_MCP_URL, HA_AUTH, DEVICE_URL, HA_LOG, DEVICE_LOG).
"""

from __future__ import annotations

import argparse
import os
import re
import secrets
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

SHELL = ("bash", "sh", "shell", "zsh")
PYTHON = ("python", "py")
MARKER = re.compile(r"^<!--\s*guide:(.*?)-->\s*$")
FENCE = re.compile(r"^```([A-Za-z0-9_+-]*)\s*$")
TIMEOUT_S = 180
PROXY_PORT = (
    8787  # the default `listen` of `proxy http`, which the guides use as written
)


@dataclass
class Block:
    path: Path
    line: int  # the line of the opening fence
    lang: str
    code: str
    kind: str = ""  # "run" | "skip" | "" (shown only)
    expect: list[str] = field(default_factory=list)
    exit: int = 0
    bg: str = ""
    wait: str = ""
    stop: str = ""
    reason: str = ""
    log_has: list[str] = field(default_factory=list)
    log_lacks: list[str] = field(default_factory=list)

    @property
    def runnable_language(self) -> bool:
        return self.lang in SHELL + PYTHON

    def label(self) -> str:
        return f"{self.path.name}:{self.line}"


def parse_marker(text: str, path: Path, line: int) -> dict:
    attrs: dict = {"expect": [], "log_has": [], "log_lacks": []}
    for word in shlex.split(text):
        key, equals, value = word.partition("=")
        if key in ("run", "skip") and not equals:
            attrs["kind"] = key
        elif key in ("expect", "log_has", "log_lacks") and equals:
            attrs[key].append(value)
        elif key == "exit" and value.isdigit():
            attrs["exit"] = int(value)
        elif key in ("bg", "wait", "stop", "reason") and equals and value:
            attrs[key] = value
        else:
            raise ValueError(f"{path.name}:{line}: unknown marker word {word!r}")
    return attrs


def extract(path: Path) -> tuple[list[Block], list[str]]:
    """The fenced blocks of one guide, and every way they break the rules (empty: it is clean)."""
    blocks: list[Block] = []
    problems: list[str] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    pending: dict | None = None
    pending_line = 0
    index = 0
    while index < len(lines):
        text = lines[index]
        marker = MARKER.match(text)
        if marker:
            if pending is not None:
                problems.append(
                    f"{path.name}:{pending_line}: a marker with no block after it"
                )
            try:
                pending, pending_line = (
                    parse_marker(marker.group(1), path, index + 1),
                    index + 1,
                )
            except ValueError as error:
                problems.append(str(error))
                pending = None
            index += 1
            continue
        fence = FENCE.match(text)
        if fence:
            start = index + 1
            body: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].startswith("```"):
                body.append(lines[index])
                index += 1
            block = Block(path, start, fence.group(1).lower(), "\n".join(body) + "\n")
            if pending is not None:
                for key, value in pending.items():
                    setattr(block, key, value)
            blocks.append(block)
            pending = None
            index += 1
            continue
        if text.strip() and pending is not None:
            problems.append(
                f"{path.name}:{pending_line}: the marker is not right before a block"
            )
            pending = None
        index += 1
    if pending is not None:
        problems.append(
            f"{path.name}:{pending_line}: a marker at the end with no block"
        )
    for block in blocks:
        if (
            block.runnable_language
            and block.kind not in ("run", "skip")
            and not block.stop
        ):
            problems.append(
                f"{block.label()}: an unmarked {block.lang} block (mark it run, or skip with a reason)"
            )
        if block.kind == "skip" and not block.reason:
            problems.append(f"{block.label()}: skip needs reason=")
        if block.kind == "run" and not block.runnable_language:
            problems.append(
                f"{block.label()}: `run` on a {block.lang or 'plain'} block"
            )
        if block.bg and not block.wait:
            problems.append(f"{block.label()}: bg= needs wait=")
    return blocks, problems


# --- running ---------------------------------------------------------------------------------------


class GuideFailure(Exception):
    pass


def free_port() -> int:
    with socket.socket() as spare:
        spare.bind(("127.0.0.1", 0))
        return int(spare.getsockname()[1])


def wait_port(address: str, timeout: float = 60.0) -> bool:
    host, _, port = address.rpartition(":")
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            socket.create_connection((host, int(port)), timeout=0.3).close()
            return True
        except OSError:
            time.sleep(0.1)
    return False


class Doubles:
    """The local stand-ins the guides talk to: Home Assistant's MCP server and a device API."""

    def __init__(self, root: Path, python: str, work: Path) -> None:
        self.root, self.python, self.work = root, python, work
        self.procs: list[subprocess.Popen] = []
        token = secrets.token_hex(12)
        ha_port, device_port = free_port(), free_port()
        self.ha_log, self.device_log = work / "ha.log", work / "device.log"
        self.env = {
            "HA_MCP_URL": f"http://127.0.0.1:{ha_port}/mcp",
            "HA_AUTH": f"Bearer {token}",
            "DEVICE_URL": f"http://127.0.0.1:{device_port}",
            "HA_LOG": str(self.ha_log),
            "DEVICE_LOG": str(self.device_log),
        }
        self._token, self._ports = token, (ha_port, device_port)

    def start(self) -> None:
        ha_port, device_port = self._ports
        base = dict(os.environ)
        self.procs.append(
            subprocess.Popen(
                [
                    self.python,
                    str(self.root / "fixtures/ha_mcp_double/server.py"),
                    str(ha_port),
                ],
                env={
                    **base,
                    "HA_DOUBLE_TOKEN": self._token,
                    "UPSTREAM_LOG": str(self.ha_log),
                },
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )  # fmt: skip
        )
        self.procs.append(
            subprocess.Popen(
                [
                    self.python,
                    str(self.root / "fixtures/http_upstream/server.py"),
                    str(device_port),
                ],
                env={**base, "UPSTREAM_LOG": str(self.device_log)},
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )  # fmt: skip
        )
        for port in (ha_port, device_port):
            if not wait_port(f"127.0.0.1:{port}"):
                raise GuideFailure(f"a double did not start on port {port}")

    def reset_logs(self) -> None:
        for log in (self.ha_log, self.device_log):
            log.write_text("", encoding="utf-8")

    def stop(self) -> None:
        for proc in self.procs:
            proc.terminate()
        for proc in self.procs:
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()


def run_guide(
    path: Path,
    blocks: list[Block],
    env: dict[str, str],
    python: str,
    work: Path,
    doubles: Doubles,
) -> int:
    """Runs the blocks of one guide in order; the number of blocks run. Raises `GuideFailure`."""
    directory = work / path.stem
    shutil.rmtree(directory, ignore_errors=True)
    directory.mkdir(parents=True)
    doubles.reset_logs()
    background: dict[str, subprocess.Popen] = {}
    ran = 0

    def fail(block: Block, why: str, output: str = "") -> GuideFailure:
        shown = block.code.strip() or "(empty)"
        return GuideFailure(
            f"FAIL guide {block.path.name}, step at line {block.line}: {why}\n--- command ---\n{shown}\n--- output ---\n{output.strip()[-3000:]}"
        )

    try:
        for block in blocks:
            if block.stop:
                proc = background.pop(block.stop, None)
                if proc is None:
                    raise fail(
                        block, f"stop={block.stop}: nothing is running under that name"
                    )
                proc.send_signal(signal.SIGTERM)
                try:
                    proc.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    raise fail(
                        block, f"{block.stop} did not stop within 30 s on SIGTERM"
                    ) from None
            if block.kind == "skip":
                print(f"  skip {block.label()}: {block.reason}")
                continue
            if block.kind != "run":
                continue
            argv = (
                ["bash", "-e", "-o", "pipefail", "-c", block.code]
                if block.lang in SHELL
                else [python, "-"]
            )
            stdin = block.code if block.lang in PYTHON else None
            if block.bg:
                log = (directory / f"{block.bg}.out").open("w+")
                proc = subprocess.Popen(
                    argv,
                    cwd=directory,
                    env=env,
                    stdin=subprocess.PIPE if stdin else None,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                if stdin:
                    proc.stdin.write(stdin)  # type: ignore[union-attr]
                    proc.stdin.close()  # type: ignore[union-attr]
                background[block.bg] = proc
                if not wait_port(block.wait):
                    proc.kill()
                    log.seek(0)
                    raise fail(
                        block, f"nothing listens on {block.wait} after 60 s", log.read()
                    )
                print(f"  ok   {block.label()}: {block.bg} running")
                ran += 1
                continue
            try:
                done = subprocess.run(
                    argv,
                    cwd=directory,
                    env=env,
                    input=stdin,
                    capture_output=True,
                    text=True,
                    timeout=TIMEOUT_S,
                    check=False,
                )
            except subprocess.TimeoutExpired as timeout:
                raise fail(
                    block, f"no end after {TIMEOUT_S} s", str(timeout.stdout or "")
                ) from None
            output = done.stdout + done.stderr
            if done.returncode != block.exit:
                raise fail(
                    block,
                    f"exit {done.returncode}, the guide says {block.exit}",
                    output,
                )
            for wanted in block.expect:
                if wanted not in output:
                    raise fail(block, f"the output does not contain {wanted!r}", output)
            for spec, must in [(s, True) for s in block.log_has] + [
                (s, False) for s in block.log_lacks
            ]:
                var, _, text = spec.partition("|")
                content = Path(env[var]).read_text(encoding="utf-8")
                if (text in content) != must:
                    raise fail(
                        block, f"{var} {'lacks' if must else 'has'} {text!r}", content
                    )
            print(f"  ok   {block.label()}")
            ran += 1
    finally:
        for proc in background.values():
            proc.kill()
    if background:
        raise GuideFailure(
            f"guide {path.name}: a background process was never stopped: {sorted(background)}"
        )
    return ran


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "guides", nargs="+", type=Path, help="the guides, run in this order"
    )
    parser.add_argument(
        "--venv", type=Path, required=True, help="the venv the wheel is installed in"
    )
    parser.add_argument("--work", type=Path, required=True, help="a scratch directory")
    parser.add_argument(
        "--also-check",
        nargs="*",
        type=Path,
        default=[],
        help="extract-only: must be clean, never run",
    )
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    python = str(args.venv / "bin" / "python")
    problems: list[str] = []
    parsed = []
    for path in [*args.guides, *args.also_check]:
        blocks, found = extract(path)
        problems += found
        parsed.append((path, blocks))
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    if not wait_free(PROXY_PORT):
        print(
            f"FAIL: port {PROXY_PORT} (the default listen of `proxy http`, used by the guides) is busy; free it and run again",
            file=sys.stderr,
        )
        return 1
    args.work.mkdir(parents=True, exist_ok=True)
    doubles = Doubles(root, python, args.work)
    env = {
        **os.environ,
        **doubles.env,
        "PATH": f"{args.venv / 'bin'}{os.pathsep}{os.environ['PATH']}",
        "NO_COLOR": "1",
        "COLUMNS": "200",
    }
    env.pop("UPSTREAM_LOG", None)
    total = 0
    try:
        doubles.start()
        for path, blocks in parsed[: len(args.guides)]:
            print(f"guide {path.name}")
            total += run_guide(path, blocks, env, python, args.work, doubles)
    except GuideFailure as failure:
        print(failure, file=sys.stderr)
        return 1
    finally:
        doubles.stop()
    print(
        f"partner_guides_check: {total} steps in {len(args.guides)} guides ran and gave what the guides promise"
    )
    return 0


def wait_free(port: int) -> bool:
    with socket.socket() as probe:
        return probe.connect_ex(("127.0.0.1", port)) != 0


if __name__ == "__main__":
    sys.exit(main())
