#!/usr/bin/env python3
"""
Check a built firmware against the Q-3 budget: flash, static RAM, and boot heap.

Three independent checks; each one runs when its input is given, and any of them
failing fails the script (exit 1). An input that cannot be read or parsed is a
failure too — a budget that could not be measured never reads as met.

1. **Flash** (`image.bin`): the image must fit the smallest A/B app slot of
   `targets/esp32s3/partitions.csv`, and Q-3's 3.5 MB (TSK-S1-12). An image larger
   than the slot cannot be flashed at all, so exceeding it breaks OTA outright.

2. **Static RAM** (`--size-json`, from `idf.py size --format json2`, TSK-S4-11):
   what `.data`, `.bss` and IRAM code placed in shared SRAM leave free of the
   internal data RAM (`DIRAM`, `DRAM`) must be at least the Q-3 floor (120 KB).
   It is the ceiling of the heap before anything runs: the heap at boot, the
   network and the audio stack only take more, so passing here is necessary, not
   sufficient (the Q-3 verdict is the board's, TSK-S1-10).

   With `--components-json` (`idf.py size-components --format json2`) the check also
   says whether ESP-SR is linked. Today it is not (`TODOS.md` #17: its licence is not
   verified yet), so the figure is the floor *without* the audio front end. The hook
   for when it is: `--require-esp-sr` fails unless an ESP-SR archive is linked, so a
   build that silently dropped it cannot pass for one that measured it.

3. **Boot heap** (`--heap-log`, a UART log): the firmware prints one
   `NEUROEDGE_HEAP_JSON {...}` line once the gate runtime is up (main.c). Internal
   free heap there must already clear the Q-3 floor. On Espressif QEMU this is the
   only runtime figure there is: no PSRAM, Wi-Fi or I2S (TSK-S4-08), so it is a floor
   before the network and the audio stack, never the Q-3 verdict.

    python scripts/check_firmware_size.py build/app.bin
    python scripts/check_firmware_size.py build/app.bin --size-json build/size.json \\
        --components-json build/size-components.json
    python scripts/check_firmware_size.py --heap-log build/uart.log
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

# Q-3: firmware <= 3.5 MB; internal SRAM >= 120 KB for the application. Kept identical
# to NEUROEDGE_Q3_MAX_FIRMWARE_BYTES and NEUROEDGE_Q3_MIN_INTERNAL_SRAM_BYTES in
# targets/esp32s3/main/memory_probe.h.
Q3_MAX_FIRMWARE_BYTES = 3_670_016
Q3_MIN_INTERNAL_SRAM_BYTES = 120 * 1024

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PARTITIONS = REPO_ROOT / "targets" / "esp32s3" / "partitions.csv"

# The internal data RAM regions of `idf.py size --format json2` (esp32s3: DIRAM).
DATA_RAM_REGIONS = ("DIRAM", "DRAM")
# Archives of the ESP-SR component (espressif/esp-sr): the AFE, WakeNet, MultiNet.
ESP_SR_ARCHIVE = re.compile(
    r"esp[-_]sr|esp_audio_front_end|esp_audio_processor|wakenet|multinet", re.IGNORECASE
)
HEAP_PREFIX = "NEUROEDGE_HEAP_JSON "
HEAP_SCHEMA = "neuroedge.heap/v1"


class Unreadable(Exception):
    """An input that could not be read as what it claims to be."""


def _parse_size(raw: str) -> int:
    """Parse a partition-table size cell: hex (0x380000), decimal, or 1M/64K."""
    value = raw.strip()
    match = re.fullmatch(r"(?i)(0x[0-9a-f]+|\d+)([KMkm])?", value)
    if match is None:
        raise ValueError(f"unrecognised size {raw!r}")
    number = int(match.group(1), 0)
    suffix = (match.group(2) or "").upper()
    return number * {"": 1, "K": 1024, "M": 1024 * 1024}[suffix]


def smallest_app_slot(partitions: Path) -> int | None:
    """
    Size of the smallest `app` partition, which is the real ceiling.

    Read from the table rather than hard-coded, so that repartitioning cannot
    silently diverge from the check that is supposed to guard it.
    """
    if not partitions.is_file():
        return None

    sizes: list[int] = []
    with partitions.open(encoding="utf-8") as handle:
        for row in csv.reader(handle):
            cells = [cell.strip() for cell in row]
            if len(cells) < 5 or not cells[0] or cells[0].startswith("#"):
                continue
            if cells[1].lower() != "app":
                continue
            try:
                sizes.append(_parse_size(cells[4]))
            except ValueError:
                continue
    return min(sizes) if sizes else None


def _kib(value: int) -> str:
    return f"{value:,} bytes ({value / 1024:.1f} KiB)"


# --- 1. flash ----------------------------------------------------------------------------------


def check_flash(image: Path, partitions: Path, max_bytes: int) -> bool:
    if not image.is_file():
        raise Unreadable(f"firmware image not found: {image}")
    size = image.stat().st_size
    slot = smallest_app_slot(partitions)
    budget = min(max_bytes, slot) if slot else max_bytes

    print("== flash (Q-3: firmware <= 3.5 MB, and the smallest A/B app slot)")
    print(f"image:             {image}")
    print(f"size:              {size:,} bytes ({size / 1024 / 1024:.2f} MiB)")
    print(f"Q-3 budget:        {max_bytes:,} bytes")
    if slot:
        print(f"smallest app slot: {slot:,} bytes (from {partitions.name})")
    print(f"effective budget:  {budget:,} bytes")
    if size > budget:
        over = size - budget
        print(
            f"✗ FAIL — image exceeds the budget by {_kib(over)}.\n"
            "  This is not a warning: the image cannot be flashed to an A/B OTA slot at this "
            "size.\n  Q-3 requires firmware <= 3.5 MB. Reduce the image, or escalate as a "
            "re-plan decision (Q-N, Q-44) — do not raise the budget here.",
            file=sys.stderr,
        )
        return False
    print(f"✓ PASS — {_kib(budget - size)} of headroom.")
    return True


# --- 2. static RAM -----------------------------------------------------------------------------


def _load_json(path: Path, what: str):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Unreadable(f"{path}: not a readable {what}: {error}") from error


def _count(value, where: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise Unreadable(f"{where}: {value!r} is not a byte count")
    return value


def static_ram(size_json: Path) -> dict[str, int]:
    """
    The internal data RAM of an `idf.py size --format json2` report: total, used,
    free and the `.data` / `.bss` / `.text` parts, summed over DIRAM and DRAM.
    Anything unexpected — no such region, a count that is not one, `free` not
    `total - used` — is Unreadable: the check fails rather than guesses.
    """
    report = _load_json(size_json, "idf.py size --format json2 report")
    layout = report.get("layout") if isinstance(report, dict) else None
    if not isinstance(layout, list):
        raise Unreadable(f"{size_json}: no `layout` list (is it `idf.py size --format json2`?)")
    sums = {"total": 0, "used": 0, "free": 0, ".data": 0, ".bss": 0, ".text": 0}
    found = []
    for region in layout:
        if not isinstance(region, dict) or region.get("name") not in DATA_RAM_REGIONS:
            continue
        name = region["name"]
        where = f"{size_json} -> layout[{name}]"
        total = _count(region.get("total"), f"{where}.total")
        used = _count(region.get("used"), f"{where}.used")
        free = _count(region.get("free"), f"{where}.free")
        if free != total - used:
            raise Unreadable(f"{where}: free {free} is not total {total} - used {used}")
        parts = region.get("parts")
        if not isinstance(parts, dict):
            raise Unreadable(f"{where}: no `parts`")
        for section in (".data", ".bss", ".text"):
            entry = parts.get(section, {"size": 0})
            size = entry.get("size") if isinstance(entry, dict) else None
            sums[section] += _count(size, f"{where}.parts[{section}].size")
        sums["total"] += total
        sums["used"] += used
        sums["free"] += free
        found.append(name)
    if not found:
        raise Unreadable(
            f"{size_json}: no internal data RAM region ({' / '.join(DATA_RAM_REGIONS)}) in the "
            "report — the static budget cannot be measured"
        )
    return sums


def esp_sr_archives(components_json: Path) -> list[str]:
    """ESP-SR archives linked with a non-zero size, from `idf.py size-components --format json2`."""
    report = _load_json(components_json, "idf.py size-components --format json2 report")
    if not isinstance(report, dict) or not report:
        raise Unreadable(f"{components_json}: not an archive -> sizes mapping")
    linked = []
    for archive, entry in report.items():
        if not isinstance(entry, dict) or "size" not in entry:
            raise Unreadable(f"{components_json} -> {archive!r}: no `size`")
        if ESP_SR_ARCHIVE.search(archive) and _count(entry["size"], archive) > 0:
            linked.append(archive)
    return sorted(linked)


def check_static_ram(
    size_json: Path, components_json: Path | None, require_esp_sr: bool, floor: int
) -> bool:
    ram = static_ram(size_json)
    print("\n== static RAM (Q-3: internal SRAM >= 120 KB for the application, TSK-S4-11)")
    print(f"report:            {size_json}")
    print(f"internal data RAM: {_kib(ram['total'])}")
    print(f"  .data:           {_kib(ram['.data'])}")
    print(f"  .bss:            {_kib(ram['.bss'])}")
    print(f"  IRAM code:       {_kib(ram['.text'])} (.text placed in shared SRAM)")
    print(f"  used, static:    {_kib(ram['used'])}")
    print(f"left for the heap: {_kib(ram['free'])}")
    print(f"Q-3 floor:         {_kib(floor)}")
    ok = True
    if components_json is None:
        print("ESP-SR:            not checked (no --components-json)")
        if require_esp_sr:
            print("✗ FAIL — --require-esp-sr needs --components-json.", file=sys.stderr)
            ok = False
    else:
        linked = esp_sr_archives(components_json)
        if linked:
            print(f"ESP-SR:            linked ({', '.join(linked)})")
        else:
            print(
                "ESP-SR:            NOT linked — this is the budget without the audio front "
                "end (AFE), whose licence is not verified yet (TODOS.md #17, TSK-S1-10)"
            )
            if require_esp_sr:
                print(
                    "✗ FAIL — --require-esp-sr: no ESP-SR archive is linked, so this build "
                    "cannot stand for one that measured the audio front end.",
                    file=sys.stderr,
                )
                ok = False
    if ram["free"] < floor:
        short = floor - ram["free"]
        print(
            f"✗ FAIL — static RAM leaves {_kib(ram['free'])}, {_kib(short)} under the Q-3 floor.\n"
            "  The heap cannot be larger than this before a single task starts. Reduce .data/"
            ".bss or IRAM code, or escalate as a re-plan decision (Q-N, Q-44) — do not lower "
            "the floor here.",
            file=sys.stderr,
        )
        return False
    if ok:
        print(
            f"✓ PASS — {_kib(ram['free'] - floor)} above the floor (static; not the Q-3 verdict)."
        )
    return ok


# --- 3. boot heap ------------------------------------------------------------------------------


def boot_heap(log: Path) -> dict:
    try:
        text = log.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        raise Unreadable(f"{log}: {error}") from error
    lines = [
        (number, line[line.index(HEAP_PREFIX) + len(HEAP_PREFIX) :])
        for number, line in enumerate(text.splitlines(), 1)
        if HEAP_PREFIX in line
    ]
    if not lines:
        raise Unreadable(
            f"{log}: no {HEAP_PREFIX.strip()} line — the firmware did not reach the gate "
            "runtime, or it is older than TSK-S4-11"
        )
    if len(lines) > 1:
        numbers = ", ".join(str(number) for number, _ in lines)
        raise Unreadable(
            f"{log}: {len(lines)} heap lines (lines {numbers}): did the device reboot?"
        )
    number, payload = lines[0]
    where = f"{log}:{number}"
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as error:
        raise Unreadable(f"{where}: not JSON: {error}") from error
    if not isinstance(data, dict) or data.get("schema") != HEAP_SCHEMA:
        raise Unreadable(f"{where}: not a {HEAP_SCHEMA} line")
    for key in ("internal_free_bytes", "internal_largest_block_bytes", "internal_min_ever_bytes"):
        _count(data.get(key), f"{where} -> {key}")
    if not isinstance(data.get("qemu"), bool):
        raise Unreadable(f"{where} -> qemu: not a boolean")
    data["where"] = where
    return data


def check_boot_heap(log: Path, floor: int) -> bool:
    heap = boot_heap(log)
    print("\n== boot heap (Q-3 floor at the gate runtime, before network and audio — TSK-S4-11)")
    print(f"line:              {heap['where']} (checkpoint {heap.get('checkpoint')!r})")
    print(f"device:            {'Espressif QEMU' if heap['qemu'] else 'board'}")
    print(f"internal free:     {_kib(heap['internal_free_bytes'])}")
    print(f"  largest block:   {_kib(heap['internal_largest_block_bytes'])}")
    print(f"  low-water mark:  {_kib(heap['internal_min_ever_bytes'])}")
    if heap["qemu"]:
        print("PSRAM:             not measured — QEMU does not emulate the Box-3's octal PSRAM")
    print(f"Q-3 floor:         {_kib(floor)}")
    free = heap["internal_free_bytes"]
    if free < floor:
        print(
            f"✗ FAIL — {_kib(free)} of internal heap before the network and the audio stack, "
            f"under the Q-3 floor by {_kib(floor - free)}: the board can only have less.",
            file=sys.stderr,
        )
        return False
    print(
        f"✓ PASS — {_kib(free - floor)} above the floor before network and audio "
        "(not the Q-3 verdict: TSK-S1-10 measures that on the board)."
    )
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[1], formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("firmware", type=Path, nargs="?", help="The built application .bin")
    parser.add_argument(
        "--partitions",
        type=Path,
        default=DEFAULT_PARTITIONS,
        help="Partition table to read the slot size from",
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=Q3_MAX_FIRMWARE_BYTES,
        help="Override the Q-3 flash budget (for experiments only; do not use in CI)",
    )
    parser.add_argument("--size-json", type=Path, help="`idf.py size --format json2` output")
    parser.add_argument(
        "--components-json", type=Path, help="`idf.py size-components --format json2` output"
    )
    parser.add_argument(
        "--require-esp-sr",
        action="store_true",
        help="Fail unless ESP-SR is linked (for the build that measures the audio front end)",
    )
    parser.add_argument("--heap-log", type=Path, help="UART log with a NEUROEDGE_HEAP_JSON line")
    args = parser.parse_args(argv)
    if args.firmware is None and args.size_json is None and args.heap_log is None:
        parser.error("nothing to check: give an image, --size-json or --heap-log")
    if args.components_json is not None and args.size_json is None:
        parser.error("--components-json goes with --size-json")

    ok = True
    try:
        if args.firmware is not None:
            ok &= check_flash(args.firmware, args.partitions, args.max_bytes)
        if args.size_json is not None:
            ok &= check_static_ram(
                args.size_json,
                args.components_json,
                args.require_esp_sr,
                Q3_MIN_INTERNAL_SRAM_BYTES,
            )
        if args.heap_log is not None:
            ok &= check_boot_heap(args.heap_log, Q3_MIN_INTERNAL_SRAM_BYTES)
    except Unreadable as error:
        print(f"\n✗ FAIL — {error}", file=sys.stderr)
        print(
            "  An input that cannot be read is a failure: a budget that was not measured is "
            "never reported as met.",
            file=sys.stderr,
        )
        return 1
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
