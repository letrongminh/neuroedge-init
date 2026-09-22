"""Shared fixtures for the NeuroEdge test suite."""

from pathlib import Path

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
