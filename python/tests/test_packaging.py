"""
Package metadata for the PyPI release (TSK-S3-14, TSK-S3-20).

The built artifacts themselves are checked by `scripts/wheel_smoke.sh` and
`.github/workflows/release-pypi.yml` (`twine check --strict`, tag == version).
"""

from __future__ import annotations

import tomllib


def _project(root) -> dict:
    return tomllib.loads((root / "python" / "pyproject.toml").read_text("utf-8"))["project"]


def test_the_packaged_licences_are_the_root_licences(root):
    # hatchling reads licence files only from inside python/, so python/ holds copies.
    for name in ("LICENSE", "LICENSES/Apache-2.0.txt"):
        assert (root / "python" / name).read_bytes() == (root / name).read_bytes(), name
    assert _project(root)["license-files"] == ["LICENSE", "LICENSES/Apache-2.0.txt"]


def test_the_licences_are_the_texts_the_metadata_declares(root):
    """Q-45: code under PolyForm Noncommercial 1.0.0, standards under Apache-2.0."""
    text = (root / "LICENSE").read_text("utf-8")
    assert text.startswith("Required Notice: Copyright 2026 NeuroEdge Contributors\n\n")
    assert "# PolyForm Noncommercial License 1.0.0" in text
    apache = (root / "LICENSES" / "Apache-2.0.txt").read_text("utf-8")
    assert "Apache License\n                           Version 2.0, January 2004" in apache
    assert _project(root)["license"] == "PolyForm-Noncommercial-1.0.0 AND Apache-2.0"
    assert not any(c.startswith("License ::") for c in _project(root)["classifiers"])


def test_the_pypi_page_is_the_root_readme(root):
    # `readme` is dynamic: hatch_build.ReadmeHook reads ../README.md (hatchling refuses
    # a static path outside python/). A static `readme` would bring back python/README.md.
    project = _project(root)
    assert "readme" not in project
    assert project["dynamic"] == ["readme"]
    assert "class ReadmeHook(MetadataHookInterface)" in (
        root / "python" / "hatch_build.py"
    ).read_text("utf-8")


def test_the_project_urls_point_at_the_repository(root):
    urls = _project(root)["urls"]
    assert set(urls) == {"Homepage", "Source", "Issues", "Changelog"}
    for url in urls.values():
        assert url.startswith("https://github.com/letrongminh/neuroedge-init")
