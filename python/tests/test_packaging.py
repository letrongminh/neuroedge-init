"""
Package metadata for the PyPI release (TSK-S3-14, TSK-S3-20).

The built artifacts themselves are checked by `scripts/wheel_smoke.sh` and
`.github/workflows/release-pypi.yml` (`twine check --strict`, tag == version).
"""

from __future__ import annotations

import tomllib


def _project(root) -> dict:
    return tomllib.loads((root / "python" / "pyproject.toml").read_text("utf-8"))["project"]


def test_the_packaged_licence_is_the_root_licence(root):
    # hatchling reads licence files only from inside python/, so python/LICENSE is a copy.
    assert (root / "python" / "LICENSE").read_bytes() == (root / "LICENSE").read_bytes()
    assert _project(root)["license-files"] == ["LICENSE"]


def test_the_licence_is_the_mit_text_the_metadata_declares(root):
    text = (root / "LICENSE").read_text("utf-8")
    assert text.startswith("MIT License\n\nCopyright 2026 NeuroEdge Contributors\n")
    assert _project(root)["license"] == "MIT"


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
