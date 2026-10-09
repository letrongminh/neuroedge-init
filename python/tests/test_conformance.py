"""
TSK-I2c-16 (the actuator part of TSK-I2c-12) — `neuroedge conformance` (RFC-0016 §3g) with the
safe-off vectors of RFC-0018 §3e, on the corpus `fixtures/compliance/actuators/`.
"""

from __future__ import annotations

import json

import pytest
import yaml
from typer.testing import CliRunner

from neuroedge import __version__
from neuroedge.cli.main import app
from neuroedge.plugins.conformance import ACTUATOR_CHECKS, COMMON_CHECKS, run

from .plugin_support import ACTUATORS, FLAWED, REFERENCE, install, on_path, write_distribution

EXPECTED = yaml.safe_load((ACTUATORS / "expected_results.yaml").read_text(encoding="utf-8"))
CHECKS = (*COMMON_CHECKS, *ACTUATOR_CHECKS)
runner = CliRunner()


def _project_entry_points(project) -> set[str]:
    import tomllib

    meta = tomllib.loads((project / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    return set(meta["entry-points"]["neuroedge.actuators"])


def test_every_plugin_example_has_an_expectation_and_every_expectation_an_example():
    for kind in ("valid", "invalid"):
        folders = {p.name for p in (ACTUATORS / kind).iterdir() if p.is_dir()}
        assert folders == set(EXPECTED[kind]), kind
        for name, entry in EXPECTED[kind].items():
            assert set(entry["entry_points"]) == _project_entry_points(ACTUATORS / kind / name)
    assert set(EXPECTED) == {"valid", "invalid"}


@pytest.mark.usefixtures("flawed_plugins")
@pytest.mark.parametrize(
    ("kind", "name"), [(k, n) for k in ("valid", "invalid") for n in sorted(EXPECTED[k])]
)
def test_each_distribution_gets_exactly_its_expected_results(kind, name):
    expected = EXPECTED[kind][name]
    report = run(name)
    assert report.exit_code == expected["exit_code"]
    got: dict[str, dict[str, str]] = {}
    for result in report.results:
        got.setdefault(result.entry_point, {})[result.check] = result.result
        assert result.result == "pass" or result.detail, "a failure says why"
    assert set(got) == set(expected["entry_points"])
    for entry_point, wanted in expected["entry_points"].items():
        assert set(got[entry_point]) == set(CHECKS), entry_point
        failing = {c: r for c, r in got[entry_point].items() if r != "pass"}
        assert failing == wanted["results"], entry_point


def test_every_check_of_every_kind_catches_a_counter_example(flawed_plugins):
    report = run("neuroedge-ref-flawed")
    caught = {(r.entry_point, r.check) for r in report.results if r.result == "fail"}
    targets = {
        entry["targets"]: entry_point
        for entry_point, entry in EXPECTED["invalid"]["neuroedge-ref-flawed"][
            "entry_points"
        ].items()
        if entry["results"].get(entry["targets"]) == "fail"
    }
    assert set(targets) == set(CHECKS), "every check has a counter-example it catches"
    for check, entry_point in targets.items():
        assert (entry_point, check) in caught
    # and on the honest plugin, at every level, every check passes
    honest = run("neuroedge-ref-actuators")
    assert {r.result for r in honest.results} == {"pass"} and len(honest.results) == 4 * len(CHECKS)


def _result(report, entry_point, check):
    return next(r for r in report.results if (r.entry_point, r.check) == (entry_point, check))


def test_a_double_that_ignores_the_timer_fails_l2(flawed_plugins):
    result = _result(run("neuroedge-ref-flawed"), "ignores_timer", "actuator.level_proven")
    assert result.result == "fail" and result.detail.startswith("L2 (b)")


def test_a_double_that_ignores_the_lease_fails_l3(flawed_plugins):
    result = _result(run("neuroedge-ref-flawed"), "ignores_lease", "actuator.level_proven")
    assert result.result == "fail" and result.detail.startswith("L3 (a)")


def test_a_plugin_claiming_l2_without_duration_fails_l0_check(flawed_plugins):
    """
    The L0 row of RFC-0018 §3e: a plugin claims no level above what it has. This one claims L2
    and sends no duration — its device, honest otherwise, stays on with the link cut.
    """
    result = _result(run("neuroedge-ref-flawed"), "l2_without_duration", "actuator.level_proven")
    assert result.result == "fail" and "no duration" in result.detail


def test_l2_sends_a_duration_on_every_on_never_none(ref_plugins):
    from .remote_support import Rig, declaration

    rig = Rig({"valve": declaration("ref_l2")})
    for ask in (500, 20_000, 0):  # a pulse, one cut to max_continuous_ms, a bare `on`
        if ask:
            rig.pulse("valve", ask)
        else:
            rig.on("valve")
        rig.advance(12_000)  # past D + tolerance, and min_interval_ms after the known end
    durations = [
        e.get("duration_ms") for e in rig.of_type("remote_command_sent") if e["operation"] == "on"
    ]
    assert durations == [500, 10_000, 10_000]
    received = [m.get("duration_ms") for m in rig.double("valve").received if m["op"] == "on"]
    assert received == durations, "the device got each one"


def test_l3_stops_renewing_before_the_ceiling_and_a_frozen_runtime_loses_the_device(ref_plugins):
    from .remote_support import Rig, declaration

    rig = Rig({"valve": declaration("ref_l3", config={"max_lease_ms": 600})})
    start = rig.clock.now
    rig.pulse("valve", 3_000)
    rig.advance(3_200)
    sent = [e for e in rig.events.to_trace()["events"] if e["type"] == "remote_command_sent"]
    renewals = [e for e in sent if e["data"]["operation"] == "renew"]
    assert renewals and all(e["data"]["lease_ms"] == 600 for e in renewals)
    last = max(e["offset_ms"] for e in renewals)
    assert last <= rig.events.offset_of(start + 3_000 - 600), "never past start + D - lease"
    assert not rig.double("valve").state()
    # a frozen runtime: no tick, no renewal — the device drops by itself
    frozen = Rig({"valve": declaration("ref_l3", config={"max_lease_ms": 600})})
    frozen.pulse("valve", 3_000)
    frozen.double("valve").advance(600 + 50)
    assert not frozen.double("valve").state()


def test_a_distribution_with_no_neuroedge_entry_point_fails(tmp_path):
    write_distribution(
        tmp_path,
        "plain-tool",
        "1.0",
        {"console_scripts": {"plain": "plain:main"}},
        {"plain.py": ""},
    )
    with on_path(tmp_path):
        report = run("plain-tool")
        result = runner.invoke(app, ["conformance", "plain-tool"])
    assert report.results == [] and report.exit_code == 1
    assert result.exit_code == 1 and "scanning nothing is never a pass" in result.output


def test_conformance_exit_codes(tmp_path):
    install(REFERENCE, tmp_path)
    install(FLAWED, tmp_path)
    write_distribution(
        tmp_path,
        "a-bridge",
        "1.0",
        {"neuroedge.bridges": {"muse": "a_bridge:make"}},
        {"a_bridge.py": "def make(config):\n    return None\n"},
    )
    with on_path(tmp_path):
        codes = {
            name: runner.invoke(app, ["conformance", name]).exit_code
            for name in ("neuroedge-ref-actuators", "neuroedge-ref-flawed", "a-bridge", "nothing-x")
        }
        only_actuators = runner.invoke(app, ["conformance", "a-bridge", "--kind", "actuator"])
    assert codes == {
        "neuroedge-ref-actuators": 0,
        "neuroedge-ref-flawed": 1,
        "a-bridge": 2,  # a kind not checked yet
        "nothing-x": 1,  # not installed
    }
    assert only_actuators.exit_code == 1, "with the bridge left out, nothing was checked"


def test_the_report_names_sdk_core_and_file_hash(ref_plugins):
    result = runner.invoke(app, ["conformance", "neuroedge-ref-actuators", "--json"])
    assert result.exit_code == 0, result.output
    report = json.loads(result.output)
    assert report["distribution"] == "neuroedge-ref-actuators" and report["version"] == "1.0.0"
    assert report["sdk"] == "1.0" and report["core"] == __version__ and report["checker"]
    assert report["files_sha256"].startswith("sha256:") and len(report["files_sha256"]) == 71
    assert report["badge_eligible"] is True and report["editable"] is False
    entry = report["results"][0]
    assert set(entry) == {"entry_point", "check", "result", "detail"}


def test_an_editable_install_is_refused_a_badge(tmp_path):
    install(REFERENCE, tmp_path, editable=True)
    with on_path(tmp_path):
        report = run("neuroedge-ref-actuators")
    assert report.exit_code == 0, "the checks still pass"
    assert report.editable and report.files_sha256 is None
    assert report.badge_eligible is False
