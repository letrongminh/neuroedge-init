"""
`neuroedge add` (TSK-I2b-04, FR-DX-08, I2b exit criterion 3): an action, its gate, a two-way
test and the `[requires]` declaration, for every primitive, into a project `neuroedge new`
made — and never over a file that exists.

Each primitive runs the whole journey: `new`, `add`, `gate lint`, `build --target sim`, then
the generated project's own tests in a fresh interpreter (a project's @action is registered
process-wide, and a fresh interpreter is what a user gets). The tests the add wrote must hold
an ALLOW case and a BLOCK case: two mutations of the gate show they notice a gate that blocks
everything and one that allows everything.
"""

from __future__ import annotations

import hashlib
import os
import tomllib
from pathlib import Path

import pytest
from typer.testing import CliRunner

from neuroedge.actions import REGISTRY
from neuroedge.cli.main import app
from neuroedge.hal.board import REQUIRABLE_PRIMITIVES
from neuroedge.templates.add import ADD_DIR, PRIMITIVES, Edit, edit_manifest

from .test_cli_new import _pytest

runner = CliRunner()


@pytest.fixture(autouse=True)
def fresh_registry():
    """A new project defines `operate_hardware` again: every test starts on an empty registry."""
    saved = dict(REGISTRY)
    REGISTRY.clear()
    yield
    REGISTRY.clear()
    REGISTRY.update(saved)


def invoke(project: Path, *args: str):
    cwd = Path.cwd()
    os.chdir(project)
    try:
        return runner.invoke(app, list(args))
    finally:
        os.chdir(cwd)


def new_project(tmp_path: Path, template: str = "minimal") -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        result = runner.invoke(app, ["new", "proj", "--template", template])
    finally:
        os.chdir(cwd)
    assert result.exit_code == 0, result.output
    return tmp_path / "proj"


def snapshot(project: Path) -> dict[str, str]:
    """Every file of the project by digest: what "left untouched" means."""
    return {
        str(path.relative_to(project)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(project.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    }


# One entry per way to reach a primitive: (id, arguments, the board the test runs on, the files).
CASES = [
    ("digital.out", ["action", "open-gate", "--pin", "gate_relay"], "sim-default", "action"),
    (
        "audio.out",
        ["action", "say-open", "--primitive", "audio.out", "--pin", "gate_relay"],
        "sim-default",
        "action",
    ),
    (
        "motion-motor",
        ["action", "drive-wheel", "--primitive", "motion", "--channel", "wheel_left"],
        "sim-rpi5",
        "action",
    ),
    (
        "motion-servo",
        ["action", "lift-arm", "--primitive", "motion", "--channel", "gripper"],
        "sim-rpi5",
        "action",
    ),
    ("display", ["action", "show-status", "--primitive", "display"], "sim-default", "action"),
    (
        "sensor.read-temperature",
        ["sensor", "heat-guard", "--source", "temperature", "--pin", "porch_light"],
        "sim-default",
        "sensor",
    ),
    (
        "sensor.read-humidity",
        ["sensor", "damp-guard", "--source", "humidity", "--pin", "porch_light"],
        "sim-default",
        "sensor",
    ),
    (
        "sensor.read-door_contact",
        ["sensor", "door-guard", "--source", "door_contact", "--pin", "porch_light"],
        "sim-default",
        "sensor",
    ),
    (
        "sensor.read-motion",
        ["sensor", "still-guard", "--source", "motion", "--pin", "porch_light"],
        "sim-default",
        "sensor",
    ),
    (
        "digital.in",
        [
            "sensor",
            "limit-guard",
            "--primitive",
            "digital.in",
            "--source",
            "limit_switch",
            "--pin",
            "gate_relay",
        ],
        "sim-rpi5",
        "sensor",
    ),
    (
        "analog.in",
        [
            "sensor",
            "volt-guard",
            "--primitive",
            "analog.in",
            "--source",
            "adc0",
            "--pin",
            "gate_relay",
        ],
        "sim-rpi5",
        "sensor",
    ),
    (
        "vision.in",
        ["sensor", "watch-gate", "--primitive", "vision.in", "--pin", "porch_light"],
        "sim-rpi5",
        "sensor",
    ),
    (
        "audio.in",
        ["sensor", "hear-open", "--primitive", "audio.in", "--pin", "porch_light"],
        "sim-default",
        "sensor",
    ),
    (
        "i2c",
        ["device", "read-supply", "--device", "i2c1/ina219", "--register", "0x02"],
        "sim-rpi5",
        "device",
    ),
    (
        "gate",
        ["gate", "night-lock", "--fact", "user_verified", "--fact", "door_closed"],
        "sim-default",
        "gate",
    ),
]


def test_every_requirable_primitive_is_reached_by_some_subcommand():
    reached = {primitive for primitives, _ in PRIMITIVES.values() for primitive in primitives}
    assert reached == set(REQUIRABLE_PRIMITIVES)


def test_every_template_folder_is_used_and_every_case_names_a_primitive_it_reaches():
    folders = {path.name for path in ADD_DIR.iterdir() if path.is_dir()}
    assert folders == {
        "digital-out",
        "audio-in",
        "motion-motor",
        "motion-servo",
        "display",
        "sensor-read",
        "digital-in",
        "analog-in",
        "vision-in",
        "i2c",
        "gate",
    }
    for folder in folders:
        assert {p.name for p in (ADD_DIR / folder).iterdir()} <= {
            "action.py.tmpl",
            "gate.yaml.tmpl",
            "test.py.tmpl",
        }


@pytest.mark.parametrize(("case", "args", "board", "kind"), CASES, ids=[c[0] for c in CASES])
def test_the_whole_journey_for_each_primitive(tmp_path, case, args, board, kind):
    project = new_project(tmp_path)
    result = invoke(project, "add", *args)
    assert result.exit_code == 0, result.output
    name = args[1]
    ident = name.replace("-", "_")

    gate = project / "gates" / f"{name}@1.0.0.yaml"
    test = project / "tests" / f"test_{ident}.py"
    assert gate.is_file() and test.is_file()
    assert (project / "actions" / f"{ident}.py").is_file() == (kind != "gate")
    for path in (gate, test, project / "agent.toml", project / "commands.toml"):
        assert "{{" not in path.read_text(encoding="utf-8"), path
    manifest = tomllib.loads((project / "agent.toml").read_text(encoding="utf-8"))
    assert manifest["gates"][name] == f"gates/{name}@1.0.0.yaml"
    assert f'BOARD = "{board}"' in test.read_text(encoding="utf-8") or kind == "gate"

    # Safe by default: the gate is fail-closed and bounded, not merely present.
    gate_text = gate.read_text(encoding="utf-8")
    assert "fail:           closed" in gate_text
    if "numeric" in gate_text:
        assert "range:" in gate_text and "max_age_ms:" in gate_text

    assert invoke(project, "gate", "lint", "gates").exit_code == 0
    built = invoke(project, "build", "--target", "sim", "--board", board, "--out", "out")
    assert built.exit_code == 0, built.output
    ran = _pytest(project)
    assert ran.returncode == 0, ran.stdout + ran.stderr
    assert "passed" in ran.stdout and "failed" not in ran.stdout


def test_each_generated_test_holds_an_allow_and_a_block_case(tmp_path):
    for case, args, _board, _kind in CASES:
        project = new_project(tmp_path / case.replace(".", "_"))
        assert invoke(project, "add", *args).exit_code == 0
        text = (project / "tests" / f"test_{args[1].replace('-', '_')}.py").read_text("utf-8")
        allowing = (
            "turn.allowed" in text or "not action.blocked" in text or "GateVerdict.ALLOW" in text
        )
        blocking = ".blocked" in text or "GateVerdict.BLOCK" in text
        assert allowing and blocking, case


def test_the_generated_tests_notice_a_gate_that_blocks_everything(tmp_path):
    project = new_project(tmp_path)
    assert invoke(project, "add", "action", "open-gate", "--pin", "gate_relay").exit_code == 0
    gate = project / "gates" / "open-gate@1.0.0.yaml"
    gate.write_text(
        gate.read_text(encoding="utf-8").replace("user_verified: true", "user_verified: false"),
        encoding="utf-8",
    )
    ran = _pytest(project)
    assert ran.returncode != 0
    assert "test_open_gate_runs_for_a_verified_user" in ran.stdout


def test_the_generated_tests_notice_a_gate_that_allows_everything(tmp_path):
    project = new_project(tmp_path)
    assert invoke(project, "add", "action", "open-gate", "--pin", "gate_relay").exit_code == 0
    gate = project / "gates" / "open-gate@1.0.0.yaml"
    gate.write_text(
        """\
schema:  neuroedge.gate/v1
name:    open-gate
version: 1.0.0
arguments:
  duration_s: { type: integer, minimum: 1, maximum: 5 }
evaluate:
  call_source:
    type: choice
    options: [local_grammar, system_one, system_two, mcp, test]
    instructions: "Nguồn của tool call"
allow_when:
  call_source: { in: [local_grammar, system_one, system_two, mcp] }
on_block:
  action: deny
budget:
  p95_latency_ms: 150
  fail:           closed
""",
        encoding="utf-8",
    )
    ran = _pytest(project)
    assert ran.returncode != 0
    assert "test_open_gate_never_moves_the_pin_for_an_unverified_user" in ran.stdout


# -- never overwrites ------------------------------------------------------------------------


@pytest.mark.parametrize(("case", "args", "board", "kind"), CASES, ids=[c[0] for c in CASES])
def test_running_the_same_add_again_refuses_and_changes_no_byte(tmp_path, case, args, board, kind):
    project = new_project(tmp_path)
    assert invoke(project, "add", *args).exit_code == 0
    before = snapshot(project)
    again = invoke(project, "add", *args)
    assert again.exit_code == 1
    assert "why:" in again.output and "fix:" in again.output and "NE3002" in again.output
    assert snapshot(project) == before


def test_a_file_that_exists_is_never_overwritten_even_when_the_name_is_new_to_the_manifest(
    tmp_path,
):
    project = new_project(tmp_path)
    (project / "tests" / "test_open_gate.py").write_text("# mine\n", encoding="utf-8")
    before = snapshot(project)
    result = invoke(project, "add", "action", "open-gate", "--pin", "gate_relay")
    assert result.exit_code == 1 and "already exist" in result.output.replace("\n", " ")
    assert snapshot(project) == before


def test_a_name_an_action_or_a_command_already_uses_is_refused(tmp_path):
    project = new_project(tmp_path)
    before = snapshot(project)
    # `operate_hardware` is the template's own @action and tool; `custom_lock` its gate key.
    for taken in ("operate_hardware", "custom_lock"):
        assert invoke(project, "add", "action", taken, "--pin", "door_lock").exit_code == 1
    assert snapshot(project) == before


def test_outside_an_agent_project_it_says_so(tmp_path):
    result = invoke(tmp_path, "add", "action", "open-gate", "--pin", "door_lock")
    assert result.exit_code == 1
    flat = result.output.replace("\n", " ")
    assert "no agent.toml here" in flat and "neuroedge new" in flat
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("bad", ["Bad", "1abc", "pass", "a b", "x" * 80])
def test_a_name_is_validated_like_a_project_name(tmp_path, bad):
    project = new_project(tmp_path)
    before = snapshot(project)
    result = invoke(project, "add", "action", bad, "--pin", "door_lock")
    assert result.exit_code == 1 and "NE3002" in result.output
    assert snapshot(project) == before


@pytest.mark.parametrize(
    ("args", "why"),
    [
        (["action", "x"], "--pin is required"),
        (["action", "x", "--primitive", "motion"], "--channel is required"),
        (["action", "x", "--primitive", "i2c"], "is not one `add action` reaches"),
        (["action", "x", "--primitive", "digital.in", "--pin", "a"], "is not one"),
        (["sensor", "x", "--pin", "porch_light"], "--source is required"),
        (["sensor", "x", "--source", "radiation", "--pin", "porch_light"], "safe default rule"),
        (["sensor", "x", "--source", "motion"], "--pin is required"),
        (["device", "x", "--device", "nobus", "--register", "0x02"], "is not bus/device"),
        (["gate", "x", "--fact", "Bad Fact"], "is not a name"),
        (["gate", "x", "--fact", "a", "--fact", "a"], "names a fact twice"),
    ],
)
def test_a_missing_or_wrong_option_is_a_three_part_refusal_that_writes_nothing(tmp_path, args, why):
    project = new_project(tmp_path)
    before = snapshot(project)
    result = invoke(project, "add", *args)
    assert result.exit_code == 1, result.output
    assert why in result.output.replace("\n", " ")
    assert "fix:" in result.output
    assert snapshot(project) == before


def test_a_result_that_does_not_build_is_refused_and_leaves_the_project_as_it_was(tmp_path):
    project = new_project(tmp_path)
    before = snapshot(project)
    result = invoke(project, "add", "action", "ghost", "--pin", "no_such_pin")
    assert result.exit_code == 1
    assert "no_such_pin" in result.output and "neuroedge-add-" not in result.output
    assert snapshot(project) == before
    # nothing stays registered: the same name works once the pin is right
    assert invoke(project, "add", "action", "ghost", "--pin", "porch_light").exit_code == 0


def test_a_second_vision_add_is_refused_not_merged(tmp_path):
    project = new_project(tmp_path)
    args = ["sensor", "--primitive", "vision.in", "--pin", "porch_light"]
    assert invoke(project, "add", args[0], "watch-a", *args[1:]).exit_code == 0
    before = snapshot(project)
    again = invoke(project, "add", args[0], "watch-b", *args[1:])
    assert again.exit_code == 1 and "[vision]" in again.output
    assert snapshot(project) == before


def test_a_value_it_would_have_to_change_is_a_refusal_not_a_rewrite(tmp_path):
    project = new_project(tmp_path)
    manifest = project / "agent.toml"
    manifest.write_text(
        manifest.read_text(encoding="utf-8").replace(
            "[requires]", '[requires]\n"audio.in" = { sample_rate_hz = 8000 }'
        ),
        encoding="utf-8",
    )
    before = snapshot(project)
    result = invoke(
        project, "add", "sensor", "hear", "--primitive", "audio.in", "--pin", "door_lock"
    )
    assert result.exit_code == 1 and "never rewrites" in result.output.replace("\n", " ")
    assert snapshot(project) == before


# -- the manifest edit -----------------------------------------------------------------------


def test_the_manifest_keeps_its_comments_and_every_existing_line(tmp_path):
    project = new_project(tmp_path)
    old = (project / "agent.toml").read_text(encoding="utf-8")
    assert invoke(project, "add", "action", "open-gate", "--pin", "gate_relay").exit_code == 0
    new = (project / "agent.toml").read_text(encoding="utf-8")
    kept = [line for line in old.splitlines() if line.strip() and "digital.out" not in line]
    assert [line for line in new.splitlines() if line in kept] == kept
    document = tomllib.loads(new)
    assert document["requires"]["digital.out"]["pins"] == ["door_lock", "gate_relay"]
    assert document["sim"]["facts"] == {"user_verified": True}


def test_the_extension_board_is_set_in_the_tests_of_the_template_and_noted(tmp_path):
    project = new_project(tmp_path)
    result = invoke(
        project, "add", "sensor", "limit-guard", "--primitive", "digital.in",
        "--source", "limit_switch", "--pin", "gate_relay",
    )  # fmt: skip
    assert result.exit_code == 0
    flat = result.output.replace("\n", " ")
    assert "--board sim-rpi5" in flat and "esp32s3" in flat
    assert 'BOARD = "sim-rpi5"' in (project / "tests" / "test_agent.py").read_text("utf-8")


def test_a_sample_templates_tests_are_moved_to_the_board_the_agent_now_needs(tmp_path):
    project = new_project(tmp_path, "factory-monitor")
    result = invoke(
        project, "add", "action", "lift-arm", "--primitive", "motion", "--channel", "gripper"
    )
    assert result.exit_code == 0, result.output
    assert "tests/test_agent.py" in result.output  # listed among the updated files
    assert 'SimSession.load(AGENT, board_id="sim-rpi5"' in (
        project / "tests" / "test_agent.py"
    ).read_text(encoding="utf-8")
    ran = _pytest(project)
    assert ran.returncode == 0, ran.stdout + ran.stderr


def test_a_sample_agent_takes_an_add_and_its_tests_still_pass(tmp_path):
    project = new_project(tmp_path, "factory-monitor")
    result = invoke(project, "add", "action", "fan-two", "--pin", "gate_relay")
    assert result.exit_code == 0, result.output
    ran = _pytest(project)
    assert ran.returncode == 0, ran.stdout + ran.stderr


def test_two_sensors_may_read_the_same_source(tmp_path):
    project = new_project(tmp_path)
    for name in ("heat-a", "heat-b"):
        args = ["sensor", name, "--source", "temperature", "--pin", "porch_light"]
        assert invoke(project, "add", *args).exit_code == 0
    ran = _pytest(project)
    assert ran.returncode == 0, ran.stdout + ran.stderr


def test_a_missing_commands_file_is_created_not_assumed(tmp_path):
    project = new_project(tmp_path)
    (project / "commands.toml").unlink()
    assert invoke(project, "add", "action", "open-gate", "--pin", "gate_relay").exit_code == 0
    grammar = tomllib.loads((project / "commands.toml").read_text(encoding="utf-8"))
    assert [c["tool"] for c in grammar["command"]] == ["open-gate"]


def test_the_audio_in_command_proves_itself_to_the_gate(tmp_path):
    project = new_project(tmp_path)
    args = ["sensor", "hear-open", "--primitive", "audio.in", "--pin", "porch_light"]
    assert invoke(project, "add", *args).exit_code == 0
    grammar = tomllib.loads((project / "commands.toml").read_text(encoding="utf-8"))
    (command,) = [c for c in grammar["command"] if c["tool"] == "hear-open"]
    assert command["facts"] == {"command_recognized": True}
    requires = tomllib.loads((project / "agent.toml").read_text(encoding="utf-8"))["requires"]
    assert requires["audio.in"] == {"sample_rate_hz": 16000}


def test_edit_manifest_refuses_a_layout_it_cannot_edit_and_never_half_edits():
    from neuroedge.errors import AgentManifestError

    text = '[agent]\nname = "a"\n[ requires ]\nx = 1\n'  # a header spelt the editor does not know
    with pytest.raises(AgentManifestError, match="does not parse"):
        edit_manifest(text, [Edit(("requires",), "z", 1)], "agent.toml")


def test_edit_manifest_refuses_a_value_it_would_have_to_change():
    from neuroedge.errors import AgentManifestError

    text = '[requires]\n"audio.in" = { sample_rate_hz = 8000 }\n'
    edit = Edit(("requires",), "audio.in", {"sample_rate_hz": 16000})
    with pytest.raises(AgentManifestError, match="never rewrites"):
        edit_manifest(text, [edit], "agent.toml")


def test_edit_manifest_adds_a_value_to_a_list_and_keeps_the_trailing_comment_lines():
    text = '[requires]\n"digital.out" = { pins = ["a"] }\n\n# about gates\n[gates]\n'
    out = edit_manifest(text, [Edit(("requires",), "digital.out", {"pins": ["b"]})], "agent.toml")
    assert tomllib.loads(out)["requires"]["digital.out"]["pins"] == ["a", "b"]
    assert "# about gates\n[gates]" in out


@pytest.mark.parametrize("taken", ["action", "digital", "display", "i2c", "motion"])
def test_a_name_that_would_hide_an_import_of_the_action_module_is_refused(tmp_path, taken):
    project = new_project(tmp_path)
    before = snapshot(project)
    result = invoke(project, "add", "action", taken, "--primitive", "display")
    assert result.exit_code == 1 and "would hide it" in result.output.replace("\n", " ")
    assert snapshot(project) == before


def test_a_standalone_gate_sets_no_sim_fact_so_it_blocks_until_the_maker_says_otherwise(tmp_path):
    project = new_project(tmp_path)
    assert invoke(project, "add", "gate", "night-lock", "--fact", "door_closed").exit_code == 0
    facts = tomllib.loads((project / "agent.toml").read_text("utf-8"))["sim"]["facts"]
    assert "door_closed" not in facts


def test_the_manifest_may_have_another_name_than_agent_toml(tmp_path):
    project = new_project(tmp_path)
    (project / "agent.toml").rename(project / "other.toml")
    result = invoke(
        project, "add", "action", "open-gate", "--pin", "gate_relay", "--agent", "other.toml"
    )
    assert result.exit_code == 0, result.output
    assert "open-gate" in tomllib.loads((project / "other.toml").read_text("utf-8"))["gates"]
    assert not (project / "agent.toml").exists()


def test_edit_manifest_leaves_a_value_it_does_not_change_on_its_own_line():
    text = '[requires]\n"audio.in" = { sample_rate_hz = 16000 }  # the mic\n'
    edit = Edit(("requires",), "audio.in", {"sample_rate_hz": 16000})
    assert edit_manifest(text, [edit], "agent.toml") == text


def test_an_earlier_add_moves_to_the_extension_board_when_a_later_one_needs_it(tmp_path):
    project = new_project(tmp_path)
    assert invoke(project, "add", "action", "open-gate", "--pin", "gate_relay").exit_code == 0
    later = ["sensor", "limit-guard", "--primitive", "digital.in", "--source", "limit_switch"]
    assert invoke(project, "add", *later, "--pin", "gate_relay").exit_code == 0
    earlier = (project / "tests" / "test_open_gate.py").read_text(encoding="utf-8")
    assert 'BOARD = "sim-rpi5"' in earlier
    ran = _pytest(project)
    assert ran.returncode == 0, ran.stdout + ran.stderr
