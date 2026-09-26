"""Shared fixtures for the NeuroEdge test suite."""

import os
from pathlib import Path

# CLI output is asserted as plain text. A developer shell with FORCE_COLOR set
# makes rich emit ANSI codes and wrap lines, which fails those asserts for
# reasons unrelated to the code. The CLI consoles are created at import time,
# so this must run before anything imports neuroedge.cli.
os.environ.pop("FORCE_COLOR", None)
os.environ["NO_COLOR"] = "1"
os.environ["COLUMNS"] = "200"

import pytest
import yaml

from neuroedge.engine import GateRegistry
from neuroedge.paths import repo_root

ROOT = repo_root()


@pytest.fixture(scope="session")
def root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def schemas_dir() -> Path:
    return ROOT / "schemas"


@pytest.fixture(scope="session")
def gates_dir() -> Path:
    return ROOT / "gates"


@pytest.fixture(scope="session")
def boards_dir() -> Path:
    return ROOT / "boards"


@pytest.fixture(scope="session")
def traces_dir() -> Path:
    return ROOT / "fixtures" / "traces"


@pytest.fixture(scope="session")
def gate_fixtures_dir() -> Path:
    return ROOT / "fixtures" / "gates"


@pytest.fixture(scope="session")
def fixture_registry(gate_fixtures_dir: Path) -> GateRegistry:
    """Registry backed by fixtures/gates/registry/, isolated from gates/."""
    return GateRegistry(gate_fixtures_dir / "registry")


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def expected_gate_errors(gate_fixtures_dir: Path) -> dict:
    return _load_yaml(gate_fixtures_dir / "expected_errors.yaml")


@pytest.fixture(scope="session")
def expected_trace_errors(traces_dir: Path) -> dict:
    return _load_yaml(traces_dir / "expected_errors.yaml")


# --- shared by the provider tests (models/providers, perception/providers) ---------------------

PROXY_VARIABLES = (
    "http_proxy",
    "HTTP_PROXY",
    "https_proxy",
    "HTTPS_PROXY",
    "all_proxy",
    "ALL_PROXY",
)


@pytest.fixture
def fresh_actions():
    """A copied agent defines the same @action names at another path: isolate the registry."""
    from neuroedge.actions import spec

    saved = dict(spec.REGISTRY)
    spec.REGISTRY.clear()
    yield
    spec.REGISTRY.clear()
    spec.REGISTRY.update(saved)


@pytest.fixture
def copy_agent(tmp_path, fresh_actions):
    """
    `copy_agent(name, extra="", files=None)`: a fresh copy of `fixtures/agents/<name>`
    with `extra` appended to its agent.toml and each of `files` (path relative to the
    agent -> text) written over it; returns the agent.toml path.
    """
    import shutil

    def make(name: str, extra: str = "", files: dict[str, str] | None = None) -> Path:
        target = tmp_path / name
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(ROOT / "fixtures" / "agents" / name, target)
        for relative, text in (files or {}).items():
            (target / relative).write_text(text, encoding="utf-8")
        manifest = target / "agent.toml"
        manifest.write_text(manifest.read_text("utf-8") + extra, encoding="utf-8")
        return manifest

    return make


@pytest.fixture
def proxies(monkeypatch):
    """
    Every proxy variable unset, `no_proxy` too; `proxies(url)` then points all of them
    at `url` — what a shell behind a corporate proxy looks like.
    """
    for name in (*PROXY_VARIABLES, "no_proxy", "NO_PROXY"):
        monkeypatch.delenv(name, raising=False)

    def point(url: str) -> None:
        for name in PROXY_VARIABLES:
            monkeypatch.setenv(name, url)

    return point
