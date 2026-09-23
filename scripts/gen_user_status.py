#!/usr/bin/env python3
"""Sinh docs/user/trang-thai.md từ neuroedge-roadmap.md §0.

Trạng thái dự án chỉ có một nơi (CONTRIBUTING.md §8.1): neuroedge-roadmap.md §0.
Tệp sinh ra là bản sao máy đọc cho người dùng — không được sửa tay.

    python3 scripts/gen_user_status.py           # ghi tệp
    python3 scripts/gen_user_status.py --check   # không ghi; thoát 1 nếu lệch

Chạy --check ở CI (xem python/tests/test_user_status_fresh.py) để tài liệu
không lệch khỏi nguồn. Ngày in ra lấy từ chính nguồn, không lấy đồng hồ máy —
nhờ vậy kết quả tất định và --check không báo lệch mỗi ngày.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "neuroedge-roadmap.md"
TARGET = ROOT / "docs" / "user" / "trang-thai.md"

STATUS_LABELS = (
    "Pha đang thực thi",
    "Sprint hiện hành",
    "Cột mốc tiếp theo",
    "Trạng thái CI Lõi",
    "Chặn ngoài tầm kỹ thuật",
    "Lần cập nhật cuối",
)

MATRIX_HEADER = "| Mốc | Sprint / Giai đoạn |"
MATRIX_COLUMNS = (0, 1, 2, 4, 5)

LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")


def strip_links(text: str) -> str:
    return LINK.sub(r"\1", text)


def split_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def section(lines: list[str], start_marker: str, end_marker: str) -> list[str]:
    start = next(i for i, line in enumerate(lines) if line.startswith(start_marker))
    end = next(i for i, line in enumerate(lines) if line.startswith(end_marker))
    return lines[start:end]


def parse_status_rows(lines: list[str]) -> dict[str, str]:
    rows: dict[str, str] = {}
    for line in lines:
        if not line.startswith("| **") or line.startswith("|:--"):
            continue
        cells = split_row(line)
        label = cells[0].strip("* ")
        if label in STATUS_LABELS:
            rows[label] = strip_links(cells[1])
    missing = [label for label in STATUS_LABELS if label not in rows]
    if missing:
        raise SystemExit(f"neuroedge-roadmap.md §0.1 thiếu dòng: {', '.join(missing)}")
    return rows


def parse_matrix(lines: list[str]) -> list[list[str]]:
    start = next(i for i, line in enumerate(lines) if line.startswith(MATRIX_HEADER))
    rows: list[list[str]] = []
    for line in lines[start + 2 :]:
        if not line.startswith("|"):
            break
        cells = split_row(line)
        rows.append([strip_links(cells[i]) for i in MATRIX_COLUMNS])
    if not rows:
        raise SystemExit("neuroedge-roadmap.md §0.2 không có dòng nào")
    return rows


def render() -> str:
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    status = parse_status_rows(section(lines, "### 0.1", "### 0.2"))
    matrix = parse_matrix(section(lines, "### 0.2", "### 0.3"))

    out = [
        "<!-- SINH TỰ ĐỘNG từ neuroedge-roadmap.md §0 — đừng sửa tay.",
        "     Chạy lại: python3 scripts/gen_user_status.py (kiểm tra: --check) -->",
        "",
        "# Trạng thái dự án",
        "",
        "> Sinh tự động từ [`neuroedge-roadmap.md`](../../neuroedge-roadmap.md) §0 —",
        f"> nguồn sự thật duy nhất về tiến độ. Cập nhật nguồn: {status['Lần cập nhật cuối']}.",
        "",
        "## Điều hành",
        "",
        "| Chỉ số | Trạng thái hiện hành |",
        "|:---|:---|",
    ]
    for label in STATUS_LABELS:
        out.append(f"| {label} | {status[label]} |")
    out += [
        "",
        "## Tiến độ các mốc",
        "",
        "| Mốc | Sprint / Giai đoạn | Thời gian | Tiến độ | Trạng thái |",
        "|:---:|:---|:---|:---:|:---:|",
    ]
    for milestone, sprint, period, progress, state in matrix:
        out.append(f"| {milestone} | {sprint} | {period} | {progress} | {state} |")
    out += [
        "",
        "Chi tiết, ghi chú và caveat về lịch: "
        "[`neuroedge-roadmap.md`](../../neuroedge-roadmap.md) §0.",
        "",
    ]
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="không ghi; thoát 1 nếu tệp đã cũ")
    args = parser.parse_args()

    content = render()
    if args.check:
        current = TARGET.read_text(encoding="utf-8") if TARGET.exists() else ""
        if current != content:
            print(
                f"{TARGET.relative_to(ROOT)} đã cũ so với {SOURCE.name} §0.\n"
                "Chạy: python3 scripts/gen_user_status.py",
                file=sys.stderr,
            )
            return 1
        print(f"{TARGET.relative_to(ROOT)} khớp nguồn")
        return 0

    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(content, encoding="utf-8")
    print(f"Đã ghi {TARGET.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
