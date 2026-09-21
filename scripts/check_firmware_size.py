#!/usr/bin/env python3
"""
Check a built firmware image against the Q-3 flash budget.

Firmware size is a build-time figure, not a runtime one, so the on-device probe
cannot report it. This script closes that gap: nightly CI runs it against the
built `.bin` and fails the job when the image would no longer fit an OTA slot.

The budget is not a style preference. `targets/esp32s3/partitions.csv` gives
each of the two A/B application slots 0x380000 bytes; an image larger than that
cannot be flashed at all, so exceeding it breaks OTA outright (FR-OTA-*).
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

# Q-3: firmware <= 3.5 MB. Kept identical to NEUROEDGE_Q3_MAX_FIRMWARE_BYTES
# in targets/esp32s3/main/memory_probe.h.
Q3_MAX_FIRMWARE_BYTES = 3_670_016

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PARTITIONS = REPO_ROOT / "targets" / "esp32s3" / "partitions.csv"


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("firmware", type=Path, help="Path to the built .bin image")
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
        help="Override the Q-3 budget (for experiments only; do not use in CI)",
    )
    args = parser.parse_args()

    if not args.firmware.is_file():
        print(f"✗ firmware image not found: {args.firmware}", file=sys.stderr)
        return 2

    size = args.firmware.stat().st_size
    slot = smallest_app_slot(args.partitions)
    budget = min(args.max_bytes, slot) if slot else args.max_bytes

    print(f"image:            {args.firmware}")
    print(f"size:             {size:,} bytes ({size / 1024 / 1024:.2f} MiB)")
    print(f"Q-3 budget:       {args.max_bytes:,} bytes")
    if slot:
        print(f"smallest app slot: {slot:,} bytes (from {args.partitions.name})")
    print(f"effective budget: {budget:,} bytes")

    if size > budget:
        over = size - budget
        print(
            f"\n✗ FAIL — image exceeds the budget by {over:,} bytes "
            f"({over / 1024:.1f} KiB).",
            file=sys.stderr,
        )
        print(
            "  This is not a warning: the image cannot be flashed to an A/B OTA "
            "slot at this size.\n"
            "  Q-3 requires firmware <= 3.5 MB. Reduce the image, or escalate as "
            "a scope decision (roadmap §9) — do not raise the budget here.",
            file=sys.stderr,
        )
        return 1

    headroom = budget - size
    print(f"\n✓ PASS — {headroom:,} bytes ({headroom / 1024:.1f} KiB) of headroom.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
