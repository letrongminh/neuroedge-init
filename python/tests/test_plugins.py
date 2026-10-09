"""
TSK-I2c-16 — the plugin loader of RFC-0016 §3d, for the kind it implements (actuators): discovery
imports nothing, only what `[plugins] enable` names is imported, any failure stops the start with
NE3002 three parts, provenance goes to stderr and into every trace.
"""

from __future__ import annotations

import sys

import pytest
from typer.testing import CliRunner

from neuroedge.cli.main import app
from neuroedge.errors import AgentManifestError, BuildFailed
from neuroedge.plugins import discover, load_enabled, parse_plugins

from .plugin_support import REFERENCE, install, on_path, write_distribution
from .remote_support import actuator_toml, write_agent

runner = CliRunner()

ENTRY = "neuroedge.actuators"
GOOD = "from neuroedge_ref_actuators import l1 as make\nsdk_requires = (1, 0)\n"


def _load(*enable: str):
    return load_enabled(parse_plugins({"enable": list(enable)}, "agent.toml"))


def _refused(*enable: str) -> AgentManifestError:
    with pytest.raises(AgentManifestError) as refused:
        _load(*enable)
    error = refused.value
    assert error.code == "NE3002" and error.where and error.why and error.how
    return error


def test_listing_plugins_imports_nothing(tmp_path):
    write_distribution(
        tmp_path,
        "explodes-on-import",
        "0.1",
        {ENTRY: {"boom": "boom_pkg:make"}},
        {"boom_pkg/__init__.py": "raise RuntimeError('imported')\n"},
    )
    with on_path(tmp_path):
        listed = [e for e in discover() if e.distribution == "explodes-on-import"]
        result = runner.invoke(app, ["plugin", "list", "--json"])
        assert "boom_pkg" not in sys.modules
    assert [(e.kind, e.name, e.version) for e in listed] == [("actuator", "boom", "0.1")]
    assert result.exit_code == 0 and '"name": "boom"' in result.output


def test_an_installed_plugin_that_is_not_enabled_never_loads(tmp_path, fresh_actions):
    install(REFERENCE, tmp_path)
    with on_path(tmp_path):
        assert _load() == {}
        assert "neuroedge_ref_actuators" not in sys.modules
        agent = write_agent(tmp_path / "agent", actuator_toml(), enable=())
        from neuroedge.engine.compiler import build

        with pytest.raises(BuildFailed) as failed:
            build(agent, target="sim")
        assert any("not an entry point of an enabled" in p.why for p in failed.value.problems)
        assert "neuroedge_ref_actuators" not in sys.modules, "installed is not enabled"


def test_a_plugin_that_fails_to_import_refuses_start_and_starts_nothing(tmp_path, fresh_actions):
    write_distribution(
        tmp_path,
        "broken-plugin",
        "1.0",
        {ENTRY: {"garden": "broken_plugin:make"}},
        {"broken_plugin/__init__.py": "import a_module_that_is_not_there\n"},
    )
    install(REFERENCE, tmp_path)
    with on_path(tmp_path):
        error = _refused("neuroedge-ref-actuators", "broken-plugin")
        assert "does not import" in error.why and "ModuleNotFoundError" in error.why
        from neuroedge.guard import Guard

        started: list[str] = []
        import neuroedge.guard as guard_module

        real = guard_module.build_hal
        guard_module.build_hal = lambda *a, **k: started.append("hal") or real(*a, **k)
        try:
            with pytest.raises(AgentManifestError):
                Guard([], board="sim-default", plugins=["broken-plugin"])
            guard = Guard([], board="sim-default", plugins=["neuroedge-ref-actuators"])
            guard.close()
        finally:
            guard_module.build_hal = real
        assert started == ["hal"], "nothing was built for the broken one; the good one builds"


def test_an_sdk_mismatch_refuses_start(tmp_path):
    for required, verdict in (((2, 0), False), ((1, 9), False), ((1, 0), True), ("1.0", False)):
        target = tmp_path / str(required).replace(" ", "")
        install(REFERENCE, target)
        write_distribution(
            target,
            "sdk-check",
            "1.0",
            {ENTRY: {"sdk_check": "sdk_check:make"}},
            {
                "sdk_check.py": f"from neuroedge_ref_actuators import l1 as make\nsdk_requires = {required!r}\n"
            },
        )
        with on_path(target):
            if verdict:
                assert set(_load("sdk-check")) == {"sdk_check"}
            else:
                assert "asks for SDK" in _refused("sdk-check").why


def test_a_factory_of_the_wrong_shape_refuses_start(tmp_path):
    install(REFERENCE, tmp_path)
    write_distribution(
        tmp_path,
        "wrong-shape",
        "1.0",
        {ENTRY: {"wants_hal": "wrong_shape:make"}},
        {"wrong_shape.py": "sdk_requires = (1, 0)\ndef make(config, hal=None):\n    return None\n"},
    )
    with on_path(tmp_path):
        error = _refused("wrong-shape")
        assert "exactly one argument" in error.why and "no HAL" in error.why
    # and a factory of the right shape that builds no Actuator is refused when it is built
    from neuroedge.hal.board import load_board_by_id
    from neuroedge.plugins.actuators import remote_setup

    write_distribution(
        tmp_path / "b",
        "no-actuator",
        "1.0",
        {ENTRY: {"nothing": "no_actuator:make"}},
        {"no_actuator.py": "sdk_requires = (1, 0)\ndef make(config):\n    return object()\n"},
    )
    with on_path(tmp_path / "b"):
        setup = remote_setup(
            {
                "plugins": {"enable": ["no-actuator"]},
                "actuators": {
                    "garden_valve": {
                        "plugin": "nothing",
                        "safe_off": "L1",
                        "reversible": True,
                        "envelope": {
                            "window_s": 60,
                            "max_on_ms_per_window": 6000,
                            "min_interval_ms": 0,
                            "max_continuous_ms": 3000,
                        },
                    }
                },
            },
            where="agent.toml",
            target="sim",
            board=load_board_by_id("sim-default"),
            requires={"digital.out": {"pins": ["garden_valve"]}},
        )
    (problem,) = setup.problems
    assert problem.code == "NE3002" and "safe_off_level" in problem.why


def test_two_enabled_distributions_with_one_entry_point_name_refuse_start(tmp_path):
    install(REFERENCE, tmp_path)
    write_distribution(
        tmp_path,
        "copycat",
        "1.0",
        {ENTRY: {"ref_l1": "copycat:make"}},
        {"copycat.py": GOOD},
    )
    with on_path(tmp_path):
        error = _refused("neuroedge-ref-actuators", "copycat")
        assert "both give the actuator entry point 'ref_l1'" in error.why
        assert set(_load("neuroedge-ref-actuators")) == {"ref_l0", "ref_l1", "ref_l2", "ref_l3"}


def test_a_version_pin_that_does_not_match_refuses_start(tmp_path):
    install(REFERENCE, tmp_path)
    with on_path(tmp_path):
        error = _refused("neuroedge-ref-actuators==0.9.0")
        assert "pins version 0.9.0 and 1.0.0 is installed" in error.why
        assert set(_load("Neuroedge_Ref.Actuators==1.0.0")), "PEP 503: one name, written any way"
        assert "not installed" in _refused("neuroedge-other").why
    with pytest.raises(AgentManifestError):
        parse_plugins({"enable": ["not a name"]}, "agent.toml")
    with pytest.raises(AgentManifestError):
        parse_plugins({"enable": ["dup", "DUP"]}, "agent.toml")


async def test_provenance_is_printed_and_recorded_in_the_trace_metadata(
    tmp_path, fresh_actions, ref_plugins, capsys
):
    from neuroedge.sim.session import SimSession
    from neuroedge.testing import TraceRecorder
    from neuroedge.trace import validate_trace

    recorder = TraceRecorder()
    session = SimSession.load(write_agent(tmp_path / "agent", actuator_toml()), events=recorder)
    await session.handle("water the garden")
    session.close()
    trace = recorder.to_trace()
    validate_trace(trace)
    plugins = trace["metadata"]["plugins"]
    assert {p["name"] for p in plugins} == {"ref_l0", "ref_l1", "ref_l2", "ref_l3"}
    for record in plugins:
        assert record["kind"] == "actuator"
        assert record["distribution"] == "neuroedge-ref-actuators" and record["version"] == "1.0.0"
        assert record["files_sha256"].startswith("sha256:") and "editable" not in record
    loaded = [e["data"] for e in trace["events"] if e["type"] == "plugin_loaded"]
    assert loaded == plugins
    printed = capsys.readouterr().err
    assert "plugin actuator 'ref_l2' from neuroedge-ref-actuators 1.0.0 (sha256:" in printed


def test_an_editable_install_has_no_file_hash_and_doctor_warns(tmp_path):
    install(REFERENCE, tmp_path, editable=True)
    with on_path(tmp_path):
        record = _load("neuroedge-ref-actuators")["ref_l1"].record
        assert record.editable and record.files_sha256 is None
        assert record.as_data() == {
            "kind": "actuator",
            "name": "ref_l1",
            "distribution": "neuroedge-ref-actuators",
            "version": "1.0.0",
            "editable": True,
        }
        from neuroedge.proxy_mcp import _plugins

        config = type(
            "C",
            (),
            {"plugins": parse_plugins({"enable": ["neuroedge-ref-actuators"]}, "g"), "source": "g"},
        )()
        findings = _plugins(config)
    warned = [f.message for f in findings if f.level == "warning"]
    assert len(warned) == 4 and all("editable" in m for m in warned)
    assert any(f.level == "unverifiable" for f in findings), "and says what it cannot check"


def test_no_cli_flag_enables_a_plugin():
    from .test_cli_contract import snapshot

    for command, line in snapshot().items():
        for word in ("--plugin", "--enable", "--plugins"):
            assert word not in line, command


def test_a_plugin_config_with_a_literal_secret_is_refused():
    for config, where in (
        ({"ha": {"token": "x"}}, "config.ha token"),
        ({"ha": {"auth": {"password": "x"}}}, "config.ha auth.password"),
        ({"ha": {"token_env": "not a name"}}, "config.ha token_env"),
    ):
        with pytest.raises(AgentManifestError) as refused:
            parse_plugins({"enable": [], "config": config}, "guard.toml")
        assert where in refused.value.where
        assert "x" not in refused.value.why.split() and "not a name" not in refused.value.why
    parse_plugins({"enable": [], "config": {"ha": {"token_env": "NE_HA_TOKEN"}}}, "guard.toml")


def test_another_kind_is_refused_naming_its_task(tmp_path):
    write_distribution(
        tmp_path,
        "a-bridge",
        "1.0",
        {"neuroedge.bridges": {"muse": "a_bridge:make"}},
        {"a_bridge.py": "def make(config):\n    return None\n"},
    )
    write_distribution(tmp_path, "nothing-here", "1.0", {}, {"nothing_here.py": ""})
    with on_path(tmp_path):
        error = _refused("a-bridge")
        assert "bridge plugin" in error.why and "TSK-I2c-11" in error.why
        assert "a_bridge" not in sys.modules, "refused before it is imported"
        assert "gives no NeuroEdge entry point" in _refused("nothing-here").why
        # a plugin config for an entry point nobody enabled is a mistake too
        with pytest.raises(AgentManifestError, match="no enabled distribution"):
            load_enabled(parse_plugins({"config": {"ghost": {"a": 1}}}, "agent.toml"))


def test_an_actuator_is_reachable_only_through_the_hal(ref_plugins):
    """The core hands the driver to the HAL and to nobody else: not the session, not an action."""
    from .remote_support import Rig, declaration

    rig = Rig({"valve": declaration("ref_l1")})
    driver = rig.setup.checked.bound["valve"].driver
    referrers = [r for r in __import__("gc").get_referrers(driver) if isinstance(r, dict)]
    owners = {type(o).__name__ for r in referrers for o in __import__("gc").get_referrers(r)}
    assert owners <= {"RemoteActuator", "BoundActuator", "RemoteBinding", "_Spy", "Rig", "dict"}


def test_safe_off_needs_no_token_and_no_envelope(ref_plugins):
    import inspect

    from neuroedge.hal import _require_signature

    from .remote_support import Rig, declaration

    rig = Rig({"valve": declaration("ref_l1")})
    driver = rig.setup.checked.bound["valve"].driver
    assert list(inspect.signature(driver.safe_off).parameters) == []
    rig.on("valve")
    rig.hal.authorize = _require_signature
    rig.hal.envelope.reserve = None  # an off must never ask the envelope
    rig.off("valve")
    assert not rig.double("valve").state()
