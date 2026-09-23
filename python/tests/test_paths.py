"""
TSK-S3-17 — finding the assets: a checkout first, then the copy packaged in the
wheel, and an error rather than a guess when there is neither.

The installed-wheel journey itself is `scripts/wheel_smoke.sh` (CI job `wheel-smoke`).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from neuroedge.errors import NeuroEdgeError
from neuroedge.paths import PACKAGED, resolve_root


def tree(root: Path) -> Path:
    for marker in ("schemas", "fixtures"):
        (root / marker).mkdir(parents=True)
    return root


def test_the_override_wins(tmp_path):
    assert resolve_root(str(tmp_path), [tmp_path / "x"], packaged=tmp_path / "none") == tmp_path


def test_an_empty_override_is_ignored(tmp_path):
    checkout = tree(tmp_path / "repo")
    found = resolve_root("", [checkout / "python" / "neuroedge" / "paths.py"], tmp_path / "none")
    assert found == checkout


def test_a_checkout_beats_the_packaged_copy(tmp_path):
    checkout = tree(tmp_path / "repo")
    packaged = tree(tmp_path / "site" / "neuroedge" / "_data")
    module = checkout / "python" / "neuroedge" / "paths.py"
    assert resolve_root(None, [module], packaged) == checkout


def test_an_installed_wheel_uses_its_packaged_copy(tmp_path):
    packaged = tree(tmp_path / "site" / "neuroedge" / "_data")
    module = tmp_path / "site" / "neuroedge" / "paths.py"
    project = tree(tmp_path / "someone-elses-project")  # must not be picked over the package
    assert resolve_root(None, [module, project / "_"], packaged) == packaged


def test_the_working_directory_is_the_last_resort(tmp_path):
    here = tree(tmp_path / "work")
    assert (
        resolve_root(None, [tmp_path / "site" / "paths.py", here / "_"], tmp_path / "none") == here
    )


def test_nothing_found_is_a_three_part_error(tmp_path):
    with pytest.raises(NeuroEdgeError) as raised:
        resolve_root(None, [tmp_path / "a" / "b.py", tmp_path / "c" / "_"], tmp_path / "none")
    assert "NEUROEDGE_ROOT" in raised.value.how
    assert "packaged assets" in raised.value.why


def test_the_packaged_path_is_inside_the_package():
    assert PACKAGED.parent.name == "neuroedge" and PACKAGED.name == "_data"
