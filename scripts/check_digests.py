#!/usr/bin/env python3
"""
Khoá digest của gate chuẩn mực trong kho (TSK-S3-16).

    python scripts/check_digests.py --check                 # CI, job Frozen artifacts
    python scripts/check_digests.py --update                # chỉ thêm tệp mới vào lock
    python scripts/check_digests.py --accept <tệp> --rfc 0007

Phạm vi: mọi tệp trong `gates/**`, `fixtures/gates/valid/**`,
`fixtures/gates/registry/**`. Digest là `engine/canonical.py` `digest()` của tài
liệu YAML **đã parse** (JCS, RFC 8785), không phải byte thô: sửa thụt lề, thứ tự
khoá hay comment không phải là thay đổi.

Ba trạng thái, ba cách xử lý:

  * tệp **mới** (chưa có trong lock) — PR thường: `--update` thêm nó vào;
  * tệp **đổi** digest, hoặc **bị xoá** — cần RFC: `--accept <tệp> --rfc NNNN`, chỉ
    nhận khi `docs/rfc/NNNN-*.md` tồn tại, và ghi mã RFC vào mục đó;
  * còn lại khớp — không làm gì.

`--update` không bao giờ ghi đè một digest đã khoá. Mã thoát: 0 khớp, 1 lệch.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from neuroedge.engine.canonical import digest

REPO_ROOT = Path(__file__).resolve().parents[1]
LOCK_NAME = "digests.lock"
SCOPE = ("gates", "fixtures/gates/valid", "fixtures/gates/registry")
HEADER = """\
# digests.lock — digest của gate chuẩn mực (TSK-S3-16). Sinh bởi
# scripts/check_digests.py; không sửa tay. Digest là canonical.digest() của
# YAML đã parse: đổi định dạng hay comment không đổi digest.
# Tệp mới: --update. Tệp đổi hoặc bị xoá: cần RFC, --accept <tệp> --rfc NNNN.
"""


def file_digest(path: Path) -> str:
    return digest(yaml.safe_load(path.read_text(encoding="utf-8")))


def scan(root: Path) -> dict[str, str]:
    """Digest của mọi tệp trong phạm vi, khoá bằng đường dẫn POSIX tương đối."""
    found: dict[str, str] = {}
    for part in SCOPE:
        for path in sorted((root / part).rglob("*")):
            if path.is_file():
                found[path.relative_to(root).as_posix()] = file_digest(path)
    return dict(sorted(found.items()))


def load_lock(root: Path) -> dict[str, dict]:
    path = root / LOCK_NAME
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return dict(data.get("files") or {})


def write_lock(root: Path, entries: dict[str, dict]) -> None:
    body = yaml.safe_dump(
        {"version": 1, "files": dict(sorted(entries.items()))},
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )
    (root / LOCK_NAME).write_text(HEADER + body, encoding="utf-8")


def compare(root: Path) -> tuple[list[str], list[str], list[str]]:
    """(mới, đổi, bị xoá) so với lock."""
    lock = load_lock(root)
    tree = scan(root)
    new, changed, deleted = [], [], []
    for name, value in tree.items():
        entry = lock.get(name)
        if entry is None:
            new.append(name)
        elif entry.get("deleted") or entry.get("digest") != value:
            changed.append(name)
    for name, entry in lock.items():
        if name not in tree and not entry.get("deleted"):
            deleted.append(name)
    return new, changed, deleted


def check(root: Path) -> int:
    new, changed, deleted = compare(root)
    for name in new:
        print(
            f"✗ {name}: tệp mới, chưa có trong {LOCK_NAME}.\n"
            "  sửa: python scripts/check_digests.py --update (PR thường, không cần RFC)"
        )
    for name in changed:
        print(
            f"✗ {name}: digest đổi so với {LOCK_NAME} — gate chuẩn mực đã khoá, cần RFC.\n"
            "  sửa: hoàn nguyên tệp, hoặc viết docs/rfc/NNNN-*.md rồi chạy "
            f"python scripts/check_digests.py --accept {name} --rfc NNNN"
        )
    for name in deleted:
        print(
            f"✗ {name}: tệp bị xoá nhưng còn khoá trong {LOCK_NAME} — cần RFC.\n"
            "  sửa: khôi phục tệp, hoặc viết docs/rfc/NNNN-*.md rồi chạy "
            f"python scripts/check_digests.py --accept {name} --rfc NNNN"
        )
    problems = len(new) + len(changed) + len(deleted)
    if problems:
        print(f"{problems} tệp lệch {LOCK_NAME}.")
        return 1
    print(f"✓ {len(scan(root))} tệp khớp {LOCK_NAME}.")
    return 0


def update(root: Path) -> int:
    new, _, _ = compare(root)
    if not new:
        print(f"Không có tệp mới; {LOCK_NAME} giữ nguyên.")
        return 0
    lock = load_lock(root)
    tree = scan(root)
    for name in new:
        lock[name] = {"digest": tree[name]}
        print(f"+ {name}")
    write_lock(root, lock)
    print(f"Đã thêm {len(new)} tệp vào {LOCK_NAME}. Digest đổi hay tệp bị xoá vẫn cần --accept.")
    return 0


def accept(root: Path, name: str, rfc: str) -> int:
    number = rfc.removeprefix("RFC-").zfill(4)
    if not number.isdigit() or not list((root / "docs" / "rfc").glob(f"{number}-*.md")):
        print(
            f"✗ --rfc {rfc}: không có docs/rfc/{number}-*.md.\n"
            "  sửa: sửa gate chuẩn mực cần một RFC đã viết (CONTRIBUTING.md §3); "
            "thêm tệp RFC trước, rồi chạy lại"
        )
        return 1
    name = Path(name).as_posix().removeprefix("./")
    _, changed, deleted = compare(root)
    lock = load_lock(root)
    if name in changed:
        lock[name] = {"digest": scan(root)[name], "rfc": number}
        print(f"✓ {name}: nhận digest mới theo RFC-{number}.")
    elif name in deleted:
        lock[name] = {"deleted": True, "digest": lock[name]["digest"], "rfc": number}
        print(f"✓ {name}: nhận việc xoá theo RFC-{number}.")
    else:
        print(
            f"✗ {name}: không phải tệp đổi hay bị xoá so với {LOCK_NAME}; không có gì để nhận.\n"
            "  sửa: tệp mới thì chạy --update; xem trạng thái bằng --check"
        )
        return 1
    write_lock(root, lock)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="so cây với lock; lệch thì thoát 1")
    mode.add_argument("--update", action="store_true", help="thêm tệp mới vào lock")
    mode.add_argument("--accept", metavar="TỆP", help="nhận một tệp đổi hoặc bị xoá, cần --rfc")
    parser.add_argument("--rfc", metavar="NNNN", help="số RFC cho --accept")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if args.accept:
        if not args.rfc:
            parser.error("--accept cần --rfc NNNN: sửa gate chuẩn mực cần RFC")
        return accept(root, args.accept, args.rfc)
    if args.update:
        return update(root)
    return check(root)


if __name__ == "__main__":
    sys.exit(main())
