"""
Package metadata for the PyPI release (TSK-S3-14, TSK-S3-20).

The built artifacts themselves are checked by `scripts/wheel_smoke.sh` and
`.github/workflows/release-pypi.yml` (`twine check --strict`, tag == version).
"""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path

from neuroedge.engine import firmware


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


def test_the_wheel_carries_exactly_the_firmware_sources_a_build_copies(root):
    """
    TSK-I3-01: `neuroedge build --target esp32s3` from an installed wheel copies the
    firmware sources the wheel carries — the same patterns, no more: a vendored
    third-party component (ESP-SR, `TODOS.md` #17) must never reach the package.
    """
    tree = ast.parse((root / "python" / "hatch_build.py").read_text("utf-8"))
    values = {
        node.targets[0].id: ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
    }
    assert values["FIRMWARE"] == "targets/esp32s3"
    assert values["FIRMWARE_SOURCES"] == firmware.SOURCES
    # A build made inside an asset (an agent's build/esp32s3/, idf.py's output) never ships.
    assert {"build", "managed_components", "__pycache__"} <= set(values["EXCLUDED_DIRS"])
    assert {"sdkconfig", "sdkconfig.old", "dependencies.lock"} <= set(values["EXCLUDED_FILES"])
    assert not {"sdkconfig.defaults", "sdkconfig.qemu"} & set(values["EXCLUDED_FILES"])
    for pattern in firmware.SOURCES:
        assert ".." not in pattern and not pattern.startswith("components/*"), pattern
        assert pattern.startswith(("main/", "components/ne_")) or "/" not in pattern, pattern


def _hook_filter(root):
    """`shipped()` of hatch_build.py, run without hatchling (a build-time dependency only)."""
    tree = ast.parse((root / "python" / "hatch_build.py").read_text("utf-8"))
    keep = [
        node
        for node in tree.body
        if (isinstance(node, ast.FunctionDef) and node.name == "shipped")
        or (
            isinstance(node, ast.Assign)
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id.startswith("EXCLUDED_")
        )
    ]
    namespace = {"Path": Path}
    exec(compile(ast.Module(body=keep, type_ignores=[]), "hatch_build.py", "exec"), namespace)
    return namespace["shipped"]


def test_build_output_inside_an_asset_is_never_shipped(root, tmp_path):
    shipped = _hook_filter(root)
    agent = tmp_path / "fixtures" / "agents" / "home-voice"
    keep = [agent / "agent.toml", tmp_path / "targets" / "esp32s3" / "sdkconfig.defaults"]
    drop = [
        agent / "build" / "esp32s3" / "main" / "main.c",
        agent / "build" / "esp32s3" / ".neuroedge-build",
        agent / "managed_components" / "espressif__esp-sr" / "x.a",
        agent / "sdkconfig",
        agent / "sdkconfig.old",
        agent / "dependencies.lock",
        agent / "actions" / "__pycache__" / "lights.cpython-311.pyc",
    ]
    for path in keep + drop:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x")
    assert [p for p in keep if not shipped(p, tmp_path)] == []
    assert [p for p in drop if shipped(p, tmp_path)] == []
