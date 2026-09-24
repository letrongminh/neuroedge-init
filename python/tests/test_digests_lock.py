"""
`digests.lock` khoá gate chuẩn mực (TSK-S3-16): sửa hay xoá một gate đã khoá cần
RFC, thêm một gate mới thì không. Các test phản chứng chạy trên bản sao trong
`tmp_path`, không bao giờ trên cây thật.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "check_digests.py"
GATE = "gates/unlock_door@1.2.0.yaml"


def run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), *args],
        capture_output=True,
        text=True,
    )


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    """Bản sao của phạm vi khoá, lock, và một RFC có thật."""
    for part in ("gates", "fixtures/gates/valid", "fixtures/gates/registry"):
        shutil.copytree(REPO_ROOT / part, tmp_path / part)
    shutil.copy(REPO_ROOT / "digests.lock", tmp_path / "digests.lock")
    (tmp_path / "docs" / "rfc").mkdir(parents=True)
    shutil.copy(
        REPO_ROOT / "docs" / "rfc" / "0004-ke-thua-budget-on-block.md",
        tmp_path / "docs" / "rfc" / "0004-ke-thua-budget-on-block.md",
    )
    return tmp_path


def test_the_lock_matches_the_tree() -> None:
    result = run(REPO_ROOT, "--check")
    assert result.returncode == 0, (
        "digests.lock lệch cây. Tệp mới: python scripts/check_digests.py --update; "
        f"tệp đổi hoặc bị xoá: cần RFC.\n{result.stdout}{result.stderr}"
    )


def test_a_formatting_only_edit_is_not_a_change(tree: Path) -> None:
    path = tree / GATE
    path.write_text(
        "# chỉ thêm comment và dòng trống\n\n" + path.read_text(encoding="utf-8") + "\n\n",
        encoding="utf-8",
    )
    assert run(tree, "--check").returncode == 0


def test_a_new_file_asks_for_update_and_update_adds_only_it(tree: Path) -> None:
    shutil.copy(tree / GATE, tree / "gates" / "unlock_door@9.9.9.yaml")
    result = run(tree, "--check")
    assert result.returncode == 1
    assert "unlock_door@9.9.9.yaml: tệp mới" in result.stdout
    assert "--update" in result.stdout
    assert "digest đổi" not in result.stdout and "bị xoá" not in result.stdout

    assert run(tree, "--update").returncode == 0
    assert run(tree, "--check").returncode == 0


def test_a_changed_digest_needs_an_rfc_and_update_does_not_hide_it(tree: Path) -> None:
    lock_before = (tree / "digests.lock").read_text(encoding="utf-8")
    path = tree / GATE
    path.write_text(path.read_text(encoding="utf-8").replace("1.2.0", "1.2.1", 1), encoding="utf-8")
    result = run(tree, "--check")
    assert result.returncode == 1
    assert f"{GATE}: digest đổi" in result.stdout and "cần RFC" in result.stdout

    run(tree, "--update")
    assert (tree / "digests.lock").read_text(encoding="utf-8") == lock_before
    assert run(tree, "--check").returncode == 1


def test_a_deleted_file_needs_an_rfc(tree: Path) -> None:
    (tree / GATE).unlink()
    result = run(tree, "--check")
    assert result.returncode == 1
    assert f"{GATE}: tệp bị xoá" in result.stdout and "cần RFC" in result.stdout


def test_accept_without_an_existing_rfc_is_refused(tree: Path) -> None:
    path = tree / GATE
    path.write_text(path.read_text(encoding="utf-8").replace("1.2.0", "1.2.1", 1), encoding="utf-8")
    assert run(tree, "--accept", GATE).returncode == 2  # thiếu --rfc: lỗi dùng lệnh
    missing = run(tree, "--accept", GATE, "--rfc", "0099")
    assert missing.returncode == 1
    assert "docs/rfc/0099-*.md" in missing.stdout
    assert run(tree, "--check").returncode == 1


def test_accept_with_an_rfc_records_it(tree: Path) -> None:
    import yaml

    path = tree / GATE
    path.write_text(path.read_text(encoding="utf-8").replace("1.2.0", "1.2.1", 1), encoding="utf-8")
    other = "gates/unlock_door_night@1.0.0.yaml"
    (tree / other).unlink()

    assert run(tree, "--accept", GATE, "--rfc", "0004").returncode == 0
    assert run(tree, "--accept", other, "--rfc", "RFC-0004").returncode == 0
    assert run(tree, "--check").returncode == 0

    files = yaml.safe_load((tree / "digests.lock").read_text(encoding="utf-8"))["files"]
    assert files[GATE]["rfc"] == "0004"
    assert files[other] == {**files[other], "deleted": True, "rfc": "0004"}


def test_accept_refuses_a_file_that_did_not_change(tree: Path) -> None:
    result = run(tree, "--accept", GATE, "--rfc", "0004")
    assert result.returncode == 1
    assert "không có gì để nhận" in result.stdout
