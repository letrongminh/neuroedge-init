"""
Project scaffolding for `neuroedge new` (TSK-S3-07, FR-DX-01).

Plain Python, deliberately: `copier` depends on the GPL3
`jinja2-ansible-filters`, which must not reach an MIT core (§3.10). A template
is a directory of `*.tmpl` files whose only placeholder is ``{{name}}``;
generating a project writes each file with the suffix dropped. The `.tmpl`
suffix keeps pytest and ruff from treating template code as package code.

`villa-concierge` adds its README and tests to a copy of
`fixtures/agents/villa-concierge/`, so the sample agent has one source. A wheel
carries that directory under `neuroedge/_data/` (TSK-S3-17), so the template
works from an installed package too.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..errors import AgentManifestError
from ..paths import fixtures_dir

TEMPLATES = ("minimal", "villa-concierge")
PLACEHOLDER = "{{name}}"
NAME = re.compile(r"^[a-z][a-z0-9_-]{0,62}$")
_HERE = Path(__file__).parent
_VILLA = "villa-concierge"


def _render(files: dict[Path, str], name: str) -> dict[Path, str]:
    return {path: text.replace(PLACEHOLDER, name) for path, text in files.items()}


def _template_files(template: str) -> dict[Path, str]:
    root = _HERE / template
    return {
        path.relative_to(root).with_suffix(""): path.read_text(encoding="utf-8")
        for path in sorted(root.rglob("*.tmpl"))
    }


def _villa_files(name: str) -> dict[Path, str]:
    source = fixtures_dir() / "agents" / _VILLA
    if not (source / "agent.toml").is_file():
        raise AgentManifestError(
            where=f"--template {_VILLA}",
            why=f"the sample agent is read from {source}, which this install does not have",
            how="reinstall neuroedge (the wheel ships the sample agent), or use --template minimal",
        )
    files = {
        path.relative_to(source): path.read_text(encoding="utf-8")
        for path in sorted(source.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    }
    manifest = Path("agent.toml")
    files[manifest] = re.sub(
        rf'^(name\s*=\s*)"{_VILLA}"', rf'\g<1>"{name}"', files[manifest], count=1, flags=re.M
    )
    return files


def scaffold(name: str, template: str = "minimal", parent: str | Path = ".") -> list[Path]:
    """Write a new agent project `parent/name` and return the files, relative to it."""
    if not NAME.match(name):
        raise AgentManifestError(
            where=f"neuroedge new {name!r}",
            why="a project name becomes [agent] name: lowercase letters, digits, '-' or '_', "
            "starting with a letter",
            how="pick a name such as villa-bot or door_agent",
        )
    if template not in TEMPLATES:
        raise AgentManifestError(
            where=f"--template {template}",
            why=f"unknown template; available: {list(TEMPLATES)}",
            how="use --template minimal (one action, one gate, one test) or villa-concierge",
        )
    target = Path(parent) / name
    if target.exists() and any(target.iterdir()):
        raise AgentManifestError(
            where=str(target),
            why="the directory already exists and is not empty; nothing was written",
            how="choose another name, or remove the directory first",
        )

    files = _template_files(template)
    if template == _VILLA:
        files = {**_villa_files(name), **files}
    for relative, text in _render(files, name).items():
        path = target / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return sorted(files)
