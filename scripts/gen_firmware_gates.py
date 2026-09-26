#!/usr/bin/env python3
"""Sinh targets/esp32s3/components/ne_agent/ từ fixtures/agents/home-voice (TSK-I3-01).

Firmware của kho là firmware mà `neuroedge build --target esp32s3` sinh cho agent mẫu
home-voice: cùng mã nguồn, và component `ne_agent` (gate `NETR` v1, bảng gate, chân,
action, các phép kiểm self-test kèm phán quyết của engine host — `engine/firmware.py`)
chép nguyên văn từ `<out>/esp32s3/` của lần build đó vào `targets/esp32s3/` và commit,
vì CI firmware chỉ có ESP-IDF, không có Python của repo. Script chỉ còn là lớp mỏng quanh
`build`: không có header nào sinh riêng ở đây nữa.

    python/.venv/bin/python scripts/gen_firmware_gates.py           # ghi tệp
    python/.venv/bin/python scripts/gen_firmware_gates.py --check   # thoát 1 nếu lệch

`python/tests/test_c_token.py` chạy `--check`: đổi gate, action hay bộ sinh mà quên sinh
lại là fail.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from neuroedge.engine.compiler import build
from neuroedge.engine.firmware import COMPONENT, PROJECT_DIR
from neuroedge.paths import repo_root

ROOT = repo_root()
AGENT = ROOT / "fixtures" / "agents" / "home-voice"
TARGET = ROOT / "targets" / "esp32s3" / COMPONENT


def render() -> dict[str, bytes]:
    """Every file of components/ne_agent/, as `neuroedge build --target esp32s3` writes it."""
    with tempfile.TemporaryDirectory() as out:
        build(AGENT / "agent.toml", target="esp32s3", board_id="esp32s3-box-3", out_dir=out)
        component = Path(out) / PROJECT_DIR / COMPONENT
        return {
            path.relative_to(component).as_posix(): path.read_bytes()
            for path in sorted(component.rglob("*"))
            if path.is_file()
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="không ghi; thoát 1 nếu lệch")
    args = parser.parse_args()
    files = render()
    stale = [
        name
        for name, data in files.items()
        if not (TARGET / name).is_file() or (TARGET / name).read_bytes() != data
    ]
    extra = (
        sorted(
            p.relative_to(TARGET).as_posix()
            for p in TARGET.rglob("*")
            if p.is_file() and p.relative_to(TARGET).as_posix() not in files
        )
        if TARGET.exists()
        else []
    )
    if args.check:
        for name in stale + extra:
            print(f"lệch: targets/esp32s3/{COMPONENT}/{name}")
        return 1 if stale or extra else 0
    for name, data in files.items():
        (TARGET / name).parent.mkdir(parents=True, exist_ok=True)
        (TARGET / name).write_bytes(data)
    for name in extra:
        (TARGET / name).unlink()
    print(f"đã ghi {len(files)} tệp vào targets/esp32s3/{COMPONENT}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
