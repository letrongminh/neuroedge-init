"""
The parts catalogue and `[sim.parts]` (docs/spec/virtual_parts.md §3.2, Q-84 phase B, TSK-I2d-30).

A part says what a pin or a sensor of the agent is, in people's words: a kind of the catalogue
(`neuroedge/hal/parts.toml`), the target it is wired to, an optional label. Parts describe and
never add a requirement; on `sim-virtual` they give an output pin its envelope. Each test names
the test case of the specification it implements.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tomllib
import urllib.request
from pathlib import Path

import pytest
from typer.testing import CliRunner

import neuroedge
from neuroedge.cli.main import app, part_context
from neuroedge.engine.compiler import build, load_agent_manifest
from neuroedge.errors import AgentManifestError, BuildFailed, NeuroEdgeError
from neuroedge.hal.board import ALL_PRIMITIVES, load_board_by_id
from neuroedge.hal.parts import SIM_PRIMITIVES, agent_parts, catalogue, parse_parts, part_envelopes
from neuroedge.hal.virtual_board import VirtualBoard
from neuroedge.paths import repo_root
from neuroedge.sim import SimSession
from neuroedge.sim.ui import SessionServer, describe_agent
from neuroedge.templates.add_part import plan_part

from .test_virtual_board import make_agent

runner = CliRunner()
ROOT = repo_root()
SPEC = ROOT / "docs" / "spec" / "virtual_parts.md"
AQUARIUM = ROOT / "fixtures" / "agents" / "aquarium" / "agent.toml"

HEATER = 'kind = "heater"\npin = "heater"\n'


@pytest.fixture(autouse=True)
def own_actions():
    """These agents register their @actions process-wide; put the registry back after each test."""
    from neuroedge.actions import REGISTRY

    saved, modules = dict(REGISTRY), set(sys.modules)
    REGISTRY.pop("operate_hardware", None)  # `neuroedge new` defines it again at a new path
    yield
    REGISTRY.clear()
    REGISTRY.update(saved)
    for module in set(sys.modules) - modules:
        if module.startswith("neuroedge_agent_"):
            del sys.modules[module]


def with_parts(tmp_path: Path, name: str, parts: str, *, board_line: bool = True) -> Path:
    """The `heater` + `ph` agent of the virtual-board tests, with `[sim.parts]` text appended."""
    agent = make_agent(tmp_path / name, name, board_line=board_line)
    text = agent.read_text(encoding="utf-8")
    if not board_line:
        text += "\n[sim]\n"
    agent.write_text(text + "\n" + parts, encoding="utf-8")
    return agent


def parsed(parts: str, requires: str | None = None) -> dict:
    """`[sim.parts]` text, as `parse_parts` reads it next to a `[requires]` of heater and ph."""
    requires = requires or (
        '[requires]\n"digital.out" = { pins = ["heater"] }\n"sensor.read" = { sensors = ["ph"] }\n'
    )
    return parse_parts(Path("agent.toml"), tomllib.loads(requires + "\n" + parts))


# --- TC-PT-01: one declared, checked shape ------------------------------------------------

VALID = [
    "[sim.parts.heater]\n" + HEATER,
    '[sim.parts.heater]\nkind = "heater"\npin = "heater"\nlabel = "Máy sưởi"\nmax_continuous_ms = 30000\n',
    '[sim.parts.probe]\nkind = "ph"\nsensor = "ph"\nrange = [0, 10]\n',
    '[sim.parts.probe]\nkind = "sensor"\nsensor = "ph"\nunit = "pH"\nrange = [0, 14]\n',
    '[sim.parts.screen]\nkind = "display"\n',
    "",
]
# (part table, a word that the error must contain, besides the part's name)
INVALID = [
    ('[sim.parts.heater]\nkind = "heater"\npin = "heater"\ncolour = "red"\n', "colour"),
    ('[sim.parts.heater]\nkind = "toaster"\npin = "heater"\n', "toaster"),
    ('[sim.parts.heater]\nkind = "heater"\n', "missing"),
    ('[sim.parts.heater]\nkind = "heater"\npin = "heater"\nsensor = "ph"\n', "twice"),
    ('[sim.parts.heater]\nkind = "heater"\nsensor = "ph"\n', "sensor"),  # wrong primitive
    ('[sim.parts.heater]\npin = "heater"\n', "kind"),
    ('[sim.parts.probe]\nkind = "ph"\nsensor = "ph"\nrange = [14, 0]\n', "range"),
    ('[sim.parts.screen]\nkind = "display"\npin = "heater"\n', "no pin"),
]


@pytest.mark.parametrize("table", VALID)
def test_a_valid_parts_table_loads(table):
    # TC-PT-01-1
    requires = (
        '[requires]\n"digital.out" = { pins = ["heater"] }\n"sensor.read" = { sensors = ["ph"] }\n'
        '"display" = {}\n'
    )
    assert isinstance(parsed(table, requires), dict)


@pytest.mark.parametrize(("table", "word"), INVALID)
def test_an_invalid_part_fails_naming_the_part(table, word):
    # TC-PT-01-1
    name = re.search(r"\[sim\.parts\.(\w+)\]", table).group(1)
    with pytest.raises(AgentManifestError) as failed:
        parsed(
            table,
            '[requires]\n"digital.out" = { pins = ["heater"] }\n'
            '"sensor.read" = { sensors = ["ph"] }\n"display" = {}\n',
        )
    text = f"{failed.value.where} {failed.value.why}"
    assert name in text and word in text


def test_a_bad_part_fails_the_build_on_every_target(tmp_path):
    # TC-PT-01-1: validation runs where agent.toml is loaded for builds and sessions
    agent = with_parts(tmp_path, "pt_bad", '[sim.parts.heater]\nkind = "toaster"\npin = "heater"\n')
    for target in ("sim", "linux"):
        with pytest.raises((BuildFailed, AgentManifestError)) as failed:
            build(agent, target=target, board_id="sim-virtual" if target == "sim" else None)
        assert "heater" in str(getattr(failed.value, "problems", failed.value)) or "toaster" in str(
            failed.value.__dict__
        )
    with pytest.raises(NeuroEdgeError):
        SimSession.load(agent)


# --- TC-PT-02: the catalogue is one data file of the kinds of §4.2 -----------------------------


def test_the_catalogue_is_the_kinds_of_the_spec_and_each_names_one_primitive():
    # TC-PT-02-1
    section = SPEC.read_text(encoding="utf-8").split("### 4.2", 1)[1].split("### 4.3", 1)[0]
    in_spec = re.findall(r"^\| `(\w+)` \|", section, flags=re.MULTILINE)
    assert len(in_spec) == 17
    assert list(catalogue()) == in_spec  # every kind of §4.2, nothing else, in the spec's order
    rich = load_board_by_id("sim-rpi5")
    for kind in catalogue().values():
        assert kind.primitive in SIM_PRIMITIVES and kind.primitive in ALL_PRIMITIVES
        assert rich.supports(kind.primitive)  # what `SimHAL` can serve
        assert (kind.target is None) == (kind.primitive == "display")


# --- TC-PT-03: a part's target is in [requires] -------------------------------------------


def test_a_part_on_a_pin_requires_lacks_fails_naming_both():
    # TC-PT-03-1
    with pytest.raises(AgentManifestError) as failed:
        parsed('[sim.parts.pump]\nkind = "pump"\npin = "air_pump"\n')
    text = f"{failed.value.where} {failed.value.why}"
    assert "pump" in text and "air_pump" in text and "digital.out" in text


def test_a_part_on_a_sensor_requires_lacks_fails_even_when_a_pin_has_that_name():
    # TC-PT-03-1: the primitive counts, not only the name
    with pytest.raises(AgentManifestError) as failed:
        parsed('[sim.parts.probe]\nkind = "ph"\nsensor = "heater"\n')
    assert "heater" in failed.value.why and "sensor.read" in failed.value.why


# --- TC-PT-04: the envelope preset, tightened, never loosened ----------------------------


def envelope_of(agent: Path, pin: str) -> dict:
    return VirtualBoard(load_agent_manifest(agent)).document["capabilities"]["digital_out"][
        "envelope"
    ][pin]


def test_the_preset_applies_and_a_part_can_only_tighten_it(tmp_path):
    # TC-PT-04-1
    plain = with_parts(tmp_path, "pt_env_a", "[sim.parts.heater]\n" + HEATER)
    assert envelope_of(plain, "heater") == {
        "window_s": 3600,
        "max_on_ms_per_window": 600000,
        "max_continuous_ms": 60000,
        "min_interval_ms": 2000,
    }
    tight = with_parts(
        tmp_path, "pt_env_b", "[sim.parts.heater]\n" + HEATER + "max_continuous_ms = 5000\n"
    )
    assert envelope_of(tight, "heater")["max_continuous_ms"] == 5000
    pause = with_parts(
        tmp_path, "pt_env_c", "[sim.parts.heater]\n" + HEATER + "min_interval_ms = 5000\n"
    )
    assert envelope_of(pause, "heater")["min_interval_ms"] == 5000  # a longer pause is stricter
    light = with_parts(tmp_path, "pt_env_d", '[sim.parts.heater]\nkind = "light"\npin = "heater"\n')
    assert envelope_of(light, "heater")["max_continuous_ms"] == 600000  # the light's preset
    assert part_envelopes(load_agent_manifest(tight))["heater"]["max_continuous_ms"] == 5000


@pytest.mark.parametrize("field", ["max_continuous_ms = 90000", "min_interval_ms = 500"])
def test_a_looser_value_fails_at_load(tmp_path, field):
    # TC-PT-04-1
    agent = with_parts(tmp_path, "pt_env_loose", "[sim.parts.heater]\n" + HEATER + field + "\n")
    with pytest.raises((AgentManifestError, BuildFailed)) as failed:
        SimSession.load(agent)
    text = str(failed.value.__dict__)
    assert "looser" in text and "heater" in text


def test_on_the_reference_board_a_part_leaves_the_envelope_unchanged():
    # TC-PT-04-1: the aquarium's parts sit on sim-default pins; parts never move a reference envelope
    reference = load_board_by_id("sim-default")
    session = SimSession.load(AQUARIUM)
    try:
        for pin in ("gate_relay", "door_lock", "porch_light"):
            assert session.hal.board.envelope(pin) == reference.envelope(pin)
    finally:
        session.hal.close()
    # and `part_envelopes` is what only the virtual board reads
    assert set(part_envelopes(load_agent_manifest(AQUARIUM))) == {
        "gate_relay",
        "door_lock",
        "porch_light",
    }


# --- TC-PT-05: a typed value stays inside the part's range --------------------------------


def test_a_value_outside_the_range_is_refused_from_the_repl_and_the_page(tmp_path):
    # TC-PT-05-1
    agent = with_parts(tmp_path, "pt_range", '[sim.parts.probe]\nkind = "ph"\nsensor = "ph"\n')
    session = SimSession.load(agent)
    server = SessionServer(session, port=0)
    try:
        with pytest.raises(NeuroEdgeError) as refused:  # `:sensor` of the REPL
            session.set_sensor("ph", 15)
        assert "0…14" in refused.value.why
        page = server.command(":sensor ph 15")  # "Đặt" on the page sends this line
        assert page["ok"] is False and "0…14" in page["error"]["why"]
        assert server.command(":sensor ph -0.5")["ok"] is False
        assert server.command(":sensor ph 7.2")["ok"] is True
        assert session.hal.sensor_values()["ph"][0] == 7.2  # refused values changed nothing
        for lost in ("lỗi", "nan"):  # "Mất tín hiệu" sends a word, not a number
            assert server.command(f":sensor ph {lost}")["ok"] is True
    finally:
        session.hal.close()


def test_a_reading_the_session_holds_is_never_changed_by_the_range(tmp_path):
    # TC-PT-05-1
    agent = with_parts(tmp_path, "pt_held", '[sim.parts.probe]\nkind = "ph"\nsensor = "ph"\n')
    text = agent.read_text(encoding="utf-8")
    agent.write_text(text + '\n[sim.sensors]\nph = { value = 20, unit = "pH" }\n', encoding="utf-8")
    session = SimSession.load(agent)
    try:
        assert session.hal.sensor_values()["ph"][0] == 20
        with pytest.raises(NeuroEdgeError):
            session.set_sensor("ph", 30)
        assert session.hal.sensor_values()["ph"][0] == 20
    finally:
        session.hal.close()


def test_a_sensor_without_a_part_has_no_range(tmp_path):
    # TC-PT-05-1: agents written before B are unchanged
    agent = with_parts(tmp_path, "pt_norange", "")
    session = SimSession.load(agent)
    try:
        session.set_sensor("ph", 99)
        assert session.hal.sensor_values()["ph"][0] == 99
    finally:
        session.hal.close()


# --- TC-PT-06: the page speaks the part's words ------------------------------------------


def test_the_page_describes_each_part_and_ui_labels_win(tmp_path):
    # TC-PT-06-2
    agent = with_parts(
        tmp_path,
        "pt_page",
        '[sim.parts.heater]\nkind = "heater"\npin = "heater"\nlabel = "Máy sưởi"\n\n'
        '[sim.parts.probe]\nkind = "ph"\nsensor = "ph"\n\n[ui.labels]\nheater = "Sưởi bể"\n',
    )
    session = SimSession.load(agent)
    server = SessionServer(session, port=0).start()
    try:
        described = describe_agent(session)
        with urllib.request.urlopen(server.url, timeout=5) as response:
            body = response.read().decode("utf-8")
    finally:
        server.stop()
        session.hal.close()
    parts = {part["target"]: part for part in described["parts"]}
    assert parts["heater"]["kind"] == "heater" and parts["heater"]["label"] == "Máy sưởi"
    assert parts["ph"]["label"] == "Độ pH"  # the kind's word when the part has no label
    assert parts["ph"]["unit"] == "pH" and parts["ph"]["range"] == [0, 14]
    assert described["labels"]["heater"] == "Sưởi bể"  # `[ui.labels]` wins for the same name
    assert described["labels"]["ph"] == "Độ pH"
    assert "Độ pH" in body and "Sưởi bể" in body  # the page carries them, in one offline file
    assert not re.search(r"""(src|href)\s*=\s*["']https?://""", body)


def test_the_page_script_picks_the_icon_by_kind_and_shows_unit_and_range():
    # TC-PT-06-2: the drawing is the page's; this pins that it reads the parts
    script = (Path(neuroedge.__file__).parent / "viz" / "assets" / "ui.js").read_text("utf-8")
    assert "agent.parts" in script and "partOf" in script and "icon(part.kind" in script
    assert "partHint" in script and "https://" not in script


# --- TC-PT-07: `neuroedge add part` ------------------------------------------------------


def _env() -> dict[str, str]:
    package_root = str(Path(neuroedge.__file__).resolve().parents[1])
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env["PYTHONPATH"] = package_root
    return env


def _project_test(project: Path) -> subprocess.CompletedProcess:
    """`neuroedge test` in the project, in a fresh interpreter (its @action registers process-wide)."""
    return subprocess.run(
        [
            sys.executable,
            "-c",
            "from neuroedge.cli.main import app; app()",
            "test",
            "--pytest-arg=-p",
            "--pytest-arg=no:cacheprovider",
        ],
        cwd=project,
        env=_env(),
        capture_output=True,
        text=True,
        timeout=180,
    )


def new_project(tmp_path: Path, name: str = "tank") -> Path:
    cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        result = runner.invoke(app, ["new", name])
    finally:
        os.chdir(cwd)
    assert result.exit_code == 0, result.output
    return tmp_path / name


def snapshot(project: Path) -> dict[str, bytes]:
    return {
        str(p.relative_to(project)): p.read_bytes()
        for p in sorted(project.rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts and ".pytest_cache" not in p.parts
    }


def add_part(project: Path, *args: str):
    return runner.invoke(
        app, ["add", "part", *args, "--agent", str(project / "agent.toml")], env={"COLUMNS": "300"}
    )


def test_add_part_writes_the_part_its_requires_and_an_action_that_passes_its_tests(tmp_path):
    # TC-PT-07-1
    project = new_project(tmp_path)
    result = add_part(
        project, "heater", "tank-heater", "--pin", "gate_relay", "--label", "Máy sưởi"
    )
    assert result.exit_code == 0, result.output
    document = tomllib.loads((project / "agent.toml").read_text("utf-8"))
    assert document["sim"]["parts"]["tank-heater"] == {
        "kind": "heater",
        "pin": "gate_relay",
        "label": "Máy sưởi",
    }
    assert "gate_relay" in document["requires"]["digital.out"]["pins"]
    assert "tank-heater" in document["gates"]
    assert (project / "actions" / "tank_heater.py").is_file()
    assert (project / "gates" / "tank-heater@1.0.0.yaml").is_file()
    assert (project / "tests" / "test_tank_heater.py").is_file()
    assert [p.name for p in agent_parts(load_agent_manifest(project / "agent.toml")).values()]
    ran = _project_test(project)
    assert ran.returncode == 0, ran.stdout + ran.stderr


def test_add_part_for_a_sensor_kind_with_an_action(tmp_path):
    # TC-PT-07-1: the sensor machinery makes the action, gate and test
    project = new_project(tmp_path)
    result = add_part(
        project, "temperature", "water-temp", "--sensor", "temperature", "--drives", "porch_light"
    )
    assert result.exit_code == 0, result.output
    document = tomllib.loads((project / "agent.toml").read_text("utf-8"))
    assert document["sim"]["parts"]["water-temp"] == {
        "kind": "temperature",
        "sensor": "temperature",
    }
    assert (project / "tests" / "test_water_temp.py").is_file()
    ran = _project_test(project)
    assert ran.returncode == 0, ran.stdout + ran.stderr


def test_add_part_on_the_virtual_board_takes_a_pin_the_default_lacks(tmp_path):
    # TC-PT-07-1 with TC-PT-09-1's second way on
    project = new_project(tmp_path)
    result = add_part(project, "pump", "air-pump", "--pin", "air_pump", "--board", "sim-virtual")
    assert result.exit_code == 0, result.output
    document = tomllib.loads((project / "agent.toml").read_text("utf-8"))
    assert "board" not in document.get("sim", {})  # `add part` never switches the board itself
    ran = _project_test(project)
    assert ran.returncode == 0, ran.stdout + ran.stderr


def test_an_unknown_kind_or_a_failing_step_changes_nothing(tmp_path):
    # TC-PT-07-1
    project = new_project(tmp_path)
    before = snapshot(project)
    unknown = add_part(project, "toaster", "t", "--pin", "gate_relay")
    assert unknown.exit_code != 0
    assert all(kind in unknown.output for kind in catalogue())  # the catalogue is listed
    # a step that fails: the action name is taken by the project's own `operate_hardware`
    clash = add_part(project, "relay", "operate_hardware", "--pin", "gate_relay")
    assert clash.exit_code != 0
    wrong = add_part(project, "heater", "h", "--sensor", "temperature")  # the wrong target key
    assert wrong.exit_code != 0
    assert snapshot(project) == before


def test_add_part_list_prints_the_catalogue():
    # TC-PT-07-1
    result = runner.invoke(app, ["add", "part", "--list"], env={"COLUMNS": "300"})
    assert result.exit_code == 0, result.output
    for kind in catalogue():
        assert kind in result.output


# --- TC-PT-09: a board that lacks the target is told, not switched -----------------------


def test_a_pin_the_board_lacks_changes_nothing_and_names_the_two_ways_on(tmp_path):
    # TC-PT-09-1
    project = new_project(tmp_path)
    before = snapshot(project)
    result = add_part(project, "pump", "p", "--pin", "air_pump")
    assert result.exit_code != 0
    assert snapshot(project) == before
    with pytest.raises(AgentManifestError) as refused:
        plan_part(project, "pump", "p", pin="air_pump", **part_context())
    text = f"{refused.value.why} {refused.value.how}"
    assert "sim-default" in text and "air_pump" in text
    assert "--board sim-virtual" in text and "[targets.sim-default.pins]" in text
    assert snapshot(project) == before


# --- TC-PT-08: the aquarium declares its parts -------------------------------------------


def test_the_aquarium_declares_its_parts_on_its_existing_pins_and_changes_no_envelope():
    # TC-PT-08-1: test_aquarium.py passes unchanged beside this
    document = tomllib.loads(AQUARIUM.read_text("utf-8"))
    parts = {
        (part.kind.name, part.target): part.shown
        for part in agent_parts(load_agent_manifest(AQUARIUM)).values()
    }
    assert parts == {
        ("heater", "gate_relay"): "Máy sưởi",
        ("pump", "door_lock"): "Máy sục khí",
        ("light", "porch_light"): "Đèn bể",
        ("temperature", "temperature"): "Nhiệt độ nước",
    }
    # `[ui.labels]` keeps only the words for facts: no pin or sensor is named there any more
    labels = document.get("ui", {}).get("labels", {})
    assert set(labels) == {"water_hot", "owner_confirmed", "call_source"}
    session = SimSession.load(AQUARIUM)
    try:
        described = describe_agent(session)
        reference = load_board_by_id("sim-default")
        for pin in ("gate_relay", "door_lock", "porch_light"):
            assert session.hal.board.envelope(pin) == reference.envelope(pin)
    finally:
        session.hal.close()
    assert described["labels"]["gate_relay"] == "Máy sưởi"
    assert described["labels"]["temperature"] == "Nhiệt độ nước"
    assert described["labels"]["water_hot"].startswith("Nước đang ấm")


@pytest.mark.parametrize("target", ["linux", "esp32s3"])
def test_the_aquarium_still_builds_for_the_real_boards(tmp_path, target):
    # TC-PT-08-1: parts describe; they never add a requirement
    assert build(AQUARIUM, target=target, out_dir=tmp_path) is not None
