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
    # the local page's link file (DP-A-10) is the test's own, and the URL is printed
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    for name in ("STATE_DIRECTORY", "INVOCATION_ID", "NEUROEDGE_SERVICE"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def fresh_actions():
    """
    For a test that copies an agent into its own tmp dir: the same @action names then come from
    a new path, and the action registry is per process. Isolate it for that test, as
    `tests/conftest.py::fresh_actions` does for the host suite. Not autouse: tests that load an
    agent already imported (the canonical traces) need the registry as it is.
    """
    from neuroedge.actions import spec

    saved = dict(spec.REGISTRY)
    spec.REGISTRY.clear()
    yield
    spec.REGISTRY.clear()
    spec.REGISTRY.update(saved)
