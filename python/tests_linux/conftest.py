"""Shared by the `linux-hal` tests: each test is a new rig for the safety envelope."""

import pytest


@pytest.fixture(autouse=True)
def envelope_state(tmp_path, monkeypatch):
    """
    A `linux` session keeps the on-time of its pins in a state directory, and a pin with no
    record refuses every on (RFC-0007 §3d). A test starts a new rig in a directory of its own, so
    that no test inherits another's on-time or its `min_interval_ms` wait after a restart. Child
    processes read `os.environ` when they start (`child_env()`), so they get it too.
    """
    monkeypatch.setenv("NEUROEDGE_LINUX_ENVELOPE_STATE", str(tmp_path / "envelope-state"))
    monkeypatch.setenv("NEUROEDGE_LINUX_ENVELOPE_INIT", "1")


@pytest.fixture(autouse=True)
def fresh_actions():
    """
    Many tests here copy an agent into their own tmp dir, so the same @action names come from a
    new path each time; the action registry is per process. Isolate it per test, as
    `tests/conftest.py::fresh_actions` does for the host suite.
    """
    from neuroedge.actions import spec

    saved = dict(spec.REGISTRY)
    spec.REGISTRY.clear()
    yield
    spec.REGISTRY.clear()
    spec.REGISTRY.update(saved)
