#!/usr/bin/env python3
"""
Stack guard for the ESP32-S3 firmware (Q-79, TSK-I2f-10). Used by
.github/workflows/firmware-qemu.yml.

    python3 scripts/check_stack_usage.py <build dir> [--limit 1024]
    python3 scripts/check_stack_usage.py <build dir> --uart-log <build dir>/uart.log

Two checks, both needed: a frame can be small and the call chain still deep, and
a run only shows the paths it took.

1. **Frames** (the build): targets/esp32s3/CMakeLists.txt compiles with
   `-fstack-usage`, so every object has a `.su` file. Every function of
   NeuroEdge's own code (`main` and the `ne_*` components) must have a static
   frame of at most `--limit` bytes (default 1024). A dynamic frame (a VLA or
   alloca) is a failure even when GCC calls it bounded: on a 3.5-4 KB task
   stack the size must be known at build time. No `.su` file for one of those
   components is a failure too: nothing checked is not a pass.
2. **Run** (`--uart-log`, a QEMU UART log): the firmware prints
   `NE_STACK task=main free_min=<bytes> size=<bytes>` before NE_TRACE DONE, the
   main task's lowest free stack after the gate self-test and the trace
   replay. It must be at least `--floor` bytes (default 512). The console
   task's figure comes from scripts/qemu_console.py (`status`, after the
   deepest command).

Idea from zclaw scripts/check-stack-usage.sh (https://github.com/tnm/zclaw,
commit e3ad271, MIT, Copyright (c) 2026 Ted Nyman), which recompiles three
chosen functions with -fstack-usage; this checks every function of ours.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

DEFAULT_LIMIT = 1024
DEFAULT_FLOOR = 512
OURS = re.compile(r"^(main|ne_[a-z_]+)$")
STACK_LINE = re.compile(r"^NE_STACK task=main free_min=(\d+) size=(\d+)\r?$", re.MULTILINE)


@dataclass(frozen=True)
class Frame:
    component: str
    where: str  # file:line:column:function, as GCC writes it
    size: int
    kind: str  # static, dynamic, dynamic,bounded


def read_frames(build: Path) -> tuple[list[Frame], list[str]]:
    """Every frame of our components, and the components that have objects but no .su file."""
    frames: list[Frame] = []
    missing: list[str] = []
    components = sorted(
        p for p in (build / "esp-idf").glob("*") if p.is_dir() and OURS.match(p.name)
    )
    for component in components:
        su_files = sorted(component.rglob("*.su"))
        if not su_files:
            missing.append(component.name)
            continue
        for su in su_files:
            for line in su.read_text(errors="replace").splitlines():
                parts = line.split("\t")
                if len(parts) != 3 or not parts[1].isdigit():
                    raise ValueError(f"{su}: not a GCC stack-usage line: {line!r}")
                frames.append(Frame(component.name, parts[0], int(parts[1]), parts[2]))
    return frames, missing


def check_frames(build: Path, limit: int) -> list[str]:
    if not (build / "esp-idf").is_dir():
        return [f"{build}: not an ESP-IDF build directory (no esp-idf/)"]
    frames, missing = read_frames(build)
    errors = [
        f"{name}: no .su files — is -fstack-usage in targets/esp32s3/CMakeLists.txt?"
        for name in missing
    ]
    if not frames and not errors:
        errors.append(f"{build}: no main or ne_* component objects found")
    for frame in frames:
        if frame.kind != "static":
            errors.append(f"{frame.where}: {frame.kind} stack frame ({frame.size} B)")
        elif frame.size > limit:
            errors.append(f"{frame.where}: {frame.size} B frame, over the {limit} B limit")
    if frames:
        components = sorted({f.component for f in frames})
        print(f"stack frames: {len(frames)} functions in {', '.join(components)}")
        for frame in sorted(frames, key=lambda f: -f.size)[:5]:
            function = frame.where.rsplit(":", 1)[-1]
            print(f"  {frame.size:5d} B  {function}  ({frame.component})")
        print(f"  limit {limit} B per frame")
    return errors


def check_uart(log: Path, floor: int) -> list[str]:
    if not log.is_file():
        return [f"{log}: no UART log"]
    matches = STACK_LINE.findall(log.read_text(errors="replace"))
    if len(matches) != 1:
        return [f"{log}: expected one NE_STACK task=main line at column 0, found {len(matches)}"]
    free, size = (int(v) for v in matches[0])
    print(f"main task stack on QEMU: {free} of {size} B never used (floor {floor} B)")
    if free < floor:
        return [f"main task: {free} B of stack left at its lowest, under the {floor} B floor"]
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("build", type=Path, help="the ESP-IDF build directory")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="bytes per frame")
    parser.add_argument("--uart-log", type=Path, help="check NE_STACK in this UART log instead")
    parser.add_argument("--floor", type=int, default=DEFAULT_FLOOR, help="bytes left on QEMU")
    args = parser.parse_args(argv)
    try:
        if args.uart_log is not None:
            errors = check_uart(args.uart_log, args.floor)
        else:
            errors = check_frames(args.build, args.limit)
    except ValueError as error:
        errors = [str(error)]
    for error in errors:
        print(f"::error::{error}")
    if not errors:
        print("ok")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
