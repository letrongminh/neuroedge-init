"""
TSK-I3-01 — `neuroedge build --target esp32s3` writes the agent's firmware (FR-CLI-02, FR-TGT-03).

The build writes `<out>/esp32s3/`: the firmware sources of `targets/esp32s3/` and one
generated component, `components/ne_agent/` — the agent's gates as NETR trees, its pins,
its actions with the gate and pins of each, and the boot self-test's checks with the host
engine's verdicts (`python/neuroedge/engine/firmware.py`). Checked here, without ESP-IDF:

* the component of a fixture agent against its golden files, byte for byte;
* two builds are the same bytes; a rebuild removes only what a build wrote;
* every action's token grants exactly the pins of that action, through its own gate;
* the generated project compiles on this host (strict, ASan + UBSan) and its self-test
  passes — and every deliberate bug in the generated tables makes it fail;
* a build that cannot produce a firmware exits 1 and writes nothing.

The ESP-IDF build and the boot on QEMU are CI's (`firmware-qemu.yml`, job `agent-firmware`).
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from neuroedge.cli.main import app
from neuroedge.engine import firmware
from neuroedge.engine.compiler import build, load_actions, load_agent_manifest, resolve_gates
from neuroedge.engine.gate_resolver import resolve_gate_document
from neuroedge.errors import AgentManifestError, BoardCapabilityError, BuildFailed, NeuroEdgeError

from .test_c_walker import STRICT, cc

runner = CliRunner()
HERE = Path(__file__).parent / "firmware"
FIXTURE = HERE / "agent" / "agent.toml"
GOLDEN = HERE / "golden"
SAN = ["-fsanitize=address,undefined", "-fno-sanitize-recover=all", "-fno-omit-frame-pointer"]

DRIVER = r"""
#include <stdio.h>
#include "gate_selftest.h"
static unsigned state = 1u;
static void fill(void *buf, size_t len) {
    unsigned char *p = buf;
    for (size_t i = 0; i < len; i++) { state = state * 1103515245u + 12345u; p[i] = (unsigned char)(state >> 16); }
}
int main(void) {
    char line[96];
    int rc = neuroedge_gate_selftest(&ne_agent_linked, fill, 0x2468u, 1000u, line, sizeof line,
                                     NULL);
    printf("%s\n%s\n", ne_agent_linked.version, line);
    return rc;
}
"""


def _parts(agent_toml: Path):
    manifest = load_agent_manifest(agent_toml)
    gates, problems = resolve_gates(manifest)
    assert problems == []
    return manifest, gates, load_actions(manifest)


def selftest_counts(agent_toml: Path) -> tuple[int, int]:
    """(walker, token): what `NE_SELFTEST PASS` must say for this agent's firmware."""
    manifest, gates, specs = _parts(agent_toml)
    walker = sum(len(firmware.checks(key, gate)) for key, gate in gates.items())
    pins = len(manifest.requires.get("digital.out", {}).get("pins", []))
    last = min(pins, firmware.MAX_PINS - 1)
    token = 1 if gates else 0  # the full ledger fails closed
    for _, _, mask in firmware.action_table(manifest, gates, specs):
        token += 2 + sum(2 if (mask >> pin) & 1 else 1 for pin in range(last + 1))
    return walker, token


def render_component(agent_toml: Path) -> dict[str, str]:
    manifest, gates, specs = _parts(agent_toml)
    return firmware.render_component(manifest, "esp32s3-box-3", gates, specs)


def regenerate() -> None:
    """Rewrite the golden files: `.venv/bin/python -c "from tests.test_firmware_build import regenerate; regenerate()"`."""
    for path in sorted(GOLDEN.rglob("*"), reverse=True):
        if path.is_file():
            path.unlink()
    for name, text in render_component(FIXTURE).items():
        (GOLDEN / name).parent.mkdir(parents=True, exist_ok=True)
        (GOLDEN / name).write_text(text, encoding="utf-8")


def files_under(folder: Path) -> dict[str, bytes]:
    return {
        path.relative_to(folder).as_posix(): path.read_bytes()
        for path in sorted(folder.rglob("*"))
        if path.is_file()
    }


def compile_selftest(project: Path, out: Path, sanitize: bool = True) -> Path:
    """The generated project's self-test, compiled on this host as the firmware compiles it."""
    driver = out.parent / f"{out.name}_driver.c"
    driver.write_text(DRIVER)
    components = project / "components"
    command = [
        cc(),
        *STRICT,
        "-O1",
        "-g",
        *(SAN if sanitize else []),
        *("-I", str(components / "ne_gate" / "include")),
        *("-I", str(components / "ne_trace" / "include")),
        *("-I", str(components / "ne_agent" / "include")),
        *("-I", str(project / "main")),
        str(components / "ne_gate" / "src" / "ne_walker.c"),
        str(components / "ne_gate" / "src" / "ne_token.c"),
        str(components / "ne_trace" / "src" / "ne_trace.c"),
        str(components / "ne_agent" / "ne_agent.c"),
        str(project / "main" / "gate_selftest.c"),
        str(driver),
        "-o",
        str(out),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return out


def run_selftest(exe: Path) -> subprocess.CompletedProcess:
    return subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)


@pytest.fixture(scope="module")
def fixture_build(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("fixture-build")
    build(FIXTURE, target="esp32s3", board_id="esp32s3-box-3", out_dir=out)
    return out


# --- what is generated ---------------------------------------------------------------------------


def test_the_generated_component_matches_its_golden_files():
    rendered = render_component(FIXTURE)
    golden = {name: data.decode("utf-8") for name, data in files_under(GOLDEN).items()}
    hint = (
        "the firmware component of tests/firmware/agent changed. If intended, run from "
        'python/: .venv/bin/python -c "from tests.test_firmware_build import regenerate; '
        'regenerate()" and review the diff'
    )
    assert sorted(rendered) == sorted(golden), hint  # closed both ways
    for name, text in rendered.items():
        assert text == golden[name], f"{name}: {hint}"


def test_the_repositorys_firmware_is_the_home_voice_build(root, tmp_path):
    # targets/esp32s3/components/ne_agent/ is what the CLI writes for home-voice, as is.
    agent = root / "fixtures" / "agents" / "home-voice" / "agent.toml"
    build(agent, target="esp32s3", board_id="esp32s3-box-3", out_dir=tmp_path)
    component = firmware.COMPONENT
    assert files_under(tmp_path / "esp32s3" / component) == files_under(
        root / "targets" / "esp32s3" / component
    )


def test_the_project_is_the_firmware_sources_and_the_agent(root, fixture_build):
    project = fixture_build / "esp32s3"
    written = files_under(project)
    source = root / "targets" / "esp32s3"
    copied = {
        name: data for name, data in written.items() if not name.startswith("components/ne_agent/")
    }
    del copied[firmware.MANIFEST]
    for name, data in copied.items():
        assert (source / name).read_bytes() == data, name
    # Every firmware source is there; no host tooling, no build output.
    for name in ("main/main.c", "main/gate_selftest.c", "main/trace_vectors.c", "partitions.csv"):
        assert name in copied
    assert not [
        n for n in written if n.endswith("Makefile") or "/test/" in n or n.startswith("build/")
    ]
    agent = {
        name.removeprefix("components/ne_agent/"): data.decode("utf-8")
        for name, data in written.items()
        if name.startswith("components/ne_agent/")
    }
    assert agent == render_component(FIXTURE)
    # The manifest lists exactly what was written.
    listing = written[firmware.MANIFEST].decode("utf-8").splitlines()
    assert listing[:2] == [firmware.MANIFEST_HEADER, "agent firmware-fixture@0.2.0"]
    assert sorted(listing[2:]) == sorted(name for name in written if name != firmware.MANIFEST)


def test_the_tree_in_the_firmware_is_the_tree_the_build_writes(fixture_build):
    for key in ("open_door", "buzz", "announce"):
        linked = fixture_build / "esp32s3" / "components" / "ne_agent" / "gates" / f"{key}.netree.h"
        assert linked.read_bytes() == (fixture_build / "gates" / f"{key}.netree.h").read_bytes()


def test_two_builds_are_the_same_bytes(tmp_path):
    for name in ("a", "b"):
        build(FIXTURE, target="esp32s3", board_id="esp32s3-box-3", out_dir=tmp_path / name)
    first, second = files_under(tmp_path / "a"), files_under(tmp_path / "b")
    assert first == second
    assert len(first) > 20


def test_a_rebuild_replaces_only_what_a_build_wrote(root, tmp_path):
    home = root / "fixtures" / "agents" / "home-voice" / "agent.toml"
    build(home, target="esp32s3", board_id="esp32s3-box-3", out_dir=tmp_path)
    project = tmp_path / "esp32s3"
    # What idf.py leaves in the project is not the build's to remove.
    (project / "sdkconfig").write_text("CONFIG_X=y\n")
    (project / "build").mkdir()
    (project / "build" / "app.bin").write_bytes(b"\0")
    build(FIXTURE, target="esp32s3", board_id="esp32s3-box-3", out_dir=tmp_path)
    agent_gates = sorted(p.name for p in (project / "components" / "ne_agent" / "gates").iterdir())
    assert agent_gates == ["announce.netree.h", "buzz.netree.h", "open_door.netree.h"]
    assert (project / "sdkconfig").read_text() == "CONFIG_X=y\n"
    assert (project / "build" / "app.bin").is_file()
    fresh = tmp_path / "fresh"
    build(FIXTURE, target="esp32s3", board_id="esp32s3-box-3", out_dir=fresh)
    rebuilt = {
        n: d
        for n, d in files_under(project).items()
        if n != "sdkconfig" and not n.startswith("build/")
    }
    assert rebuilt == files_under(fresh / "esp32s3")


def test_only_esp32s3_writes_a_firmware(tmp_path):
    build(FIXTURE, target="sim", board_id="sim-default", out_dir=tmp_path)
    assert not (tmp_path / "esp32s3").exists()


# --- no pin without its gate ---------------------------------------------------------------------


def test_every_action_drives_only_its_own_pins_through_its_own_gate():
    manifest, gates, specs = _parts(FIXTURE)
    table = {
        name: (gate, mask) for name, gate, mask in firmware.action_table(manifest, gates, specs)
    }
    keys = list(gates)
    pins = manifest.requires["digital.out"]["pins"]
    by_name = {spec.name: spec for spec in specs}
    assert sorted(table) == sorted(by_name)
    for name, (gate, mask) in table.items():
        spec = by_name[name]
        assert keys[gate] == spec.gate
        assert {pins[i] for i in range(len(pins)) if (mask >> i) & 1} == set(spec.pins)
    assert table["fixture_announce"][1] == 0  # speech only: its token grants no pin
    porch = 1 << pins.index("porch_light")
    assert not any(mask & porch for _, mask in table.values())  # declared, driven by nothing


def test_the_self_test_checks_carry_the_host_engines_verdicts(root):
    """
    The rows the old hand-written home-voice self-test asserted, now generated: a
    `test` caller refused; someone in the room ⇒ BLOCK that a person may answer; their
    "có" stands in for room_empty only; a missing reading never reads as "empty".
    """
    manifest, gates, _ = _parts(root / "fixtures" / "agents" / "home-voice" / "agent.toml")
    on = {row.note: row.expected for row in firmware.checks("light_on", gates["light_on"])}
    off = {row.note: row.expected for row in firmware.checks("light_off", gates["light_off"])}
    ALLOW, BLOCK = 0, 1
    NOT_MET, UNAVAILABLE, UNREACHABLE = 1, 2, 5
    assert on["baseline"][0] == ALLOW
    assert on["call_source = test"][:4] == (BLOCK, NOT_MET, 1, 0)
    assert on["call_source missing"][:2] == (BLOCK, UNAVAILABLE)
    assert off["room_empty = false"] == (BLOCK, NOT_MET, 1, 1, 1, 0, 0)  # answerable
    assert off["room_empty = false, confirmed"] == (ALLOW, 0, 0, 0, 0, 0, 1 << 1)
    assert off["room_empty missing"][:4] == (BLOCK, UNAVAILABLE, 1, 1)
    assert "call_source = test, confirmed" not in off  # a person cannot admit the caller
    # fail: closed — an offline source blocks, and skips on_block (Q-17).
    assert off["a fact missing and its source offline"] == (BLOCK, UNREACHABLE, 0, 0, 0, 2, 0)


def test_fail_open_argument_limits_and_confidence_floors_are_checked():
    manifest, gates, _ = _parts(FIXTURE)
    buzz = {row.note: row for row in firmware.checks("buzz", gates["buzz"])}
    # fail: open — the unreachable source is excused, ALLOW with the degraded reason.
    assert buzz["a fact missing and its source offline"].expected[:2] == (0, 5)
    assert buzz["a fact missing and its source offline"].expected[5] == 1
    door = {row.note for row in firmware.checks("open_door", gates["open_door"])}
    assert {
        "face_match: no confidence",
        "face_match: confidence below the floor",
        "face_match: confidence at the floor",
        "face_match: confidence outside [0, 1]",
        "risk = high",
        "channel outside its domain",
        "resident_home = false, confirmed",
    } <= door


# --- the self-test on this host ------------------------------------------------------------------


@pytest.mark.parametrize("agent", ["fixture", "home-voice"])
def test_the_generated_firmware_passes_its_self_test_on_this_host(root, tmp_path, agent):
    toml = FIXTURE if agent == "fixture" else root / "fixtures" / "agents" / agent / "agent.toml"
    build(toml, target="esp32s3", board_id="esp32s3-box-3", out_dir=tmp_path)
    result = run_selftest(compile_selftest(tmp_path / "esp32s3", tmp_path / "selftest"))
    assert result.returncode == 0, result.stdout + result.stderr
    walker, token = selftest_counts(toml)
    version = load_agent_manifest(toml).label
    assert result.stdout.splitlines() == [
        version,
        f"NE_SELFTEST PASS walker={walker} token={token}",
    ]


AGENT_C = "components/ne_agent/ne_agent.c"
WALKER_C = "components/ne_gate/src/ne_walker.c"
TOKEN_C = "components/ne_gate/src/ne_token.c"
SELFTEST_C = "main/gate_selftest.c"
# One check of the fixture, "face_match = false": the host says BLOCK, condition_not_met,
# criterion 3. Each field changed must fail the self-test: every comparison is live.
ROW = "{0u, 3u, 0u, 0u, 1u, 1u, 1u, 3u, 0u, 0u, 0x0u, {1u, 1u, 0u, 1u, 1.0}}"
ASKED = "{0u, 0u, 0u, 0u, 1u, 1u, 1u, 0u, 1u, 0u, 0x0u, {1u, 1u, 0u, 1u, 1.0}}"
OPEN = "{1u, 0u, 0u, 1u, 0u, 5u, 0u, 0u, 0u, 1u, 0x0u,"
CONFIRMED = "{0u, 255u, 1u, 0u, 0u, 0u, 0u, 0u, 0u, 0u, 0x1u,"


def _row(verdict=1, reason=1, kind=1, index=3) -> str:
    return (
        f"{{0u, 3u, 0u, 0u, {verdict}u, {reason}u, {kind}u, {index}u, 0u, 0u, 0x0u, "
        "{1u, 1u, 0u, 1u, 1.0}}"
    )


# label -> edits (path, old, new): each a bug in the generated tables, the self-test, or the
# image's walker and ledger, that must not pass. Every `old` occurs exactly once.
MUTANTS = {
    "a check's expected verdict": [(AGENT_C, ROW, _row(verdict=0))],
    "a check's expected reason": [(AGENT_C, ROW, _row(reason=2))],
    "a check's failing kind": [(AGENT_C, ROW, _row(kind=2))],
    "a check's failing criterion": [(AGENT_C, ROW, _row(index=2))],
    "a check's answerable": [
        (AGENT_C, ASKED, ASKED.replace("0u, 1u, 0u, 0x0u", "0u, 0u, 0u, 0x0u"))
    ],
    "a check's fail mode": [(AGENT_C, OPEN, OPEN.replace("0u, 1u, 0x0u,", "0u, 2u, 0x0u,"))],
    "a check's confirmed criteria": [(AGENT_C, CONFIRMED, CONFIRMED.replace("0x1u", "0x3u"))],
    "a check varying a criterion the gate lacks": [
        (AGENT_C, OPEN, OPEN.replace("{1u, 0u, 0u, 1u,", "{1u, 7u, 0u, 1u,"))
    ],
    "a baseline fact": [
        (
            AGENT_C,
            "ne_agent_baseline_1[1] = {{1u, 1u, 1u, 1u, 1.0}}",
            "ne_agent_baseline_1[1] = {{1u, 1u, 0u, 1u, 1.0}}",
        )
    ],
    "an argument value that no longer fits": [
        (AGENT_C, '{1u, 0u, 5u, "front", 0.0}', '{1u, 0u, 4u, "fron", 0.0}')
    ],
    "two gates' trees swapped": [
        (
            AGENT_C,
            '{"buzz@1.0.0", ne_tree_buzz, (uint32_t)sizeof ne_tree_buzz,',
            '{"buzz@1.0.0", ne_tree_announce, (uint32_t)sizeof ne_tree_announce,',
        )
    ],
    "a digest in the gate table": [(AGENT_C, "{0x10, 0xfa, 0x42,", "{0x11, 0xfa, 0x42,")],
    "a gate's number of criteria": [(AGENT_C, "     4u, {NULL,", "     3u, {NULL,")],
    "an action's pins past the pin table": [
        (AGENT_C, '{"fixture_buzz", 1u, 0x2u}', '{"fixture_buzz", 1u, 0xau}')
    ],
    "an action guarded by no gate": [
        (AGENT_C, '{"fixture_announce", 2u, 0x0u}', '{"fixture_announce", 3u, 0x0u}')
    ],
    "the self-test ignores a confirmation": [
        (SELFTEST_C, "g->args, k->confirmed,", "g->args, 0,"),
    ],
    "the self-test ignores degraded gathering": [
        (SELFTEST_C, "(ne_degraded)k->degraded, &r)", "NE_DEGRADED_NONE, &r)")
    ],
    "the walker ignores the confidence floor": [
        (WALKER_C, "|| (floor > 0.0 && fact->confidence < floor))", "|| 0)")
    ],
    "the walker ignores a confirmation": [
        (
            WALKER_C,
            "if (r != NE_REASON_NONE && ((waived >> i) & 1u) == 0u) {",
            "if (r != NE_REASON_NONE && ((waived >> i) & 0u) == 0u) {",
        )
    ],
    "the ledger forgets a consumed pin": [
        (TOKEN_C, "slot->consumed_mask |= 1u << pin;", "(void)0;")
    ],
    "the ledger grants any pin": [
        (
            TOKEN_C,
            "if (pin >= NE_MAX_PINS || (token->pin_mask & (1u << pin)) == 0u)",
            "if (pin >= NE_MAX_PINS)",
        )
    ],
}


def _mutated_project(fixture_build: Path, work: Path, edits) -> Path:
    project = work / "esp32s3"
    for name, data in files_under(fixture_build / "esp32s3").items():
        (project / name).parent.mkdir(parents=True, exist_ok=True)
        (project / name).write_bytes(data)
    for path, old, new in edits:
        target = project / path
        text = target.read_text()
        assert text.count(old) == 1, (path, old)
        target.write_text(text.replace(old, new))
    return project


def test_every_deliberate_bug_fails_the_self_test(fixture_build, tmp_path):
    survivors = []
    for label, edits in MUTANTS.items():
        work = tmp_path / re.sub(r"\W+", "_", label)
        project = _mutated_project(fixture_build, work, edits)
        result = run_selftest(compile_selftest(project, work / "selftest", sanitize=False))
        if result.returncode == 0 or "NE_SELFTEST FAIL" not in result.stdout:
            survivors.append(label)
    assert survivors == [], f"these bugs pass the self-test: {survivors}"
    assert len(MUTANTS) >= 20


def test_a_corrupted_tree_in_flash_stops_the_gate_runtime(fixture_build, tmp_path):
    header = "components/ne_agent/gates/open_door.netree.h"
    edit = (header, "0x4e, 0x45, 0x54, 0x52, 0x01", "0x4e, 0x45, 0x54, 0x52, 0x02")  # NETR v2
    project = _mutated_project(fixture_build, tmp_path, [edit])
    result = run_selftest(compile_selftest(project, tmp_path / "selftest", sanitize=False))
    assert result.returncode != 0
    assert "NE_SELFTEST FAIL load open_door@1.0.0" in result.stdout


# --- nothing written when the firmware cannot be built (an incompatible board: FR-HAL-04) --------


AGENT = """
[agent]
name = "tmp-agent"
version = "0.0.1"

[requires]
"digital.out" = {{ pins = [{pins}] }}

[gates]
{gates}

[targets]
supported = ["esp32s3"]
"""
GATE = """
schema: neuroedge.gate/v1
name: g
version: 1.0.0
evaluate:
  ok: {type: bool, instructions: "ok"}
allow_when:
  ok: true
on_block: {action: deny}
budget: {p95_latency_ms: 100, fail: closed}
"""


def _tmp_agent(tmp_path: Path, pins='"door_lock"', gates: tuple[str, ...] = ("lock",)) -> Path:
    (tmp_path / "gates").mkdir(exist_ok=True)
    (tmp_path / "gates" / "g.yaml").write_text(GATE)
    body = AGENT.format(pins=pins, gates="\n".join(f'{key} = "gates/g.yaml"' for key in gates))
    (tmp_path / "agent.toml").write_text(body)
    return tmp_path / "agent.toml"


def _refused(agent: Path, out: Path) -> list:
    with pytest.raises(BuildFailed) as excinfo:
        build(agent, target="esp32s3", board_id="esp32s3-box-3", out_dir=out)
    assert not out.exists() or not any(out.iterdir()), "a failed build wrote something"
    return excinfo.value.problems


def test_an_incompatible_board_writes_no_firmware(tmp_path):
    problems = _refused(_tmp_agent(tmp_path, pins='"garage_door"'), tmp_path / "out")
    assert [type(p) for p in problems] == [BoardCapabilityError]


def _document(evaluate: dict, allow_when: dict) -> dict:
    return {
        "schema": "neuroedge.gate/v1",
        "name": "g",
        "version": "1.0.0",
        "evaluate": evaluate,
        "allow_when": allow_when,
        "on_block": {"action": "deny"},
        "budget": {"p95_latency_ms": 100, "fail": "closed"},
    }


def test_a_gate_the_device_layout_cannot_hold_is_a_build_problem(tmp_path):
    many = {f"c{i}": {"type": "bool", "instructions": "x"} for i in range(33)}
    gate = resolve_gate_document(_document(many, dict.fromkeys(many, True)))
    manifest = load_agent_manifest(_tmp_agent(tmp_path))
    (problem,) = firmware.firmware_problems(manifest, {"big": gate})
    assert "exceed the device layout's limit of 32" in problem.why


def test_an_index_macro_two_names_would_share_is_defined_for_neither(tmp_path):
    evaluate = {
        "room": {"type": "choice", "options": ["empty", "full"], "instructions": "x"},
        "room_empty": {"type": "bool", "instructions": "x"},
    }
    gate = resolve_gate_document(
        _document(evaluate, {"room": {"in": ["empty"]}, "room_empty": True})
    )
    manifest = load_agent_manifest(_tmp_agent(tmp_path))
    text = firmware._indices(manifest, {"g": gate})
    assert "#define NE_GATE_G_ROOM_EMPTY " not in text
    assert "/* NE_GATE_G_ROOM_EMPTY: two names share it, so it is not defined */" in text
    assert "#define NE_GATE_G_ROOM_FULL 1u" in text and "#define NE_PIN_DOOR_LOCK 0u" in text


# --- the project directory: only the build's own paths, never through a link ------------------


def _marked(project: Path, *names: str) -> None:
    """A project an earlier build wrote: its MANIFEST, listing `names`."""
    project.mkdir(parents=True, exist_ok=True)
    listing = [firmware.MANIFEST_HEADER, "agent earlier@1", *names]
    (project / firmware.MANIFEST).write_text("\n".join(listing) + "\n")


def _victim(tmp_path: Path) -> Path:
    victim = tmp_path / "elsewhere" / "victim.txt"
    victim.parent.mkdir(parents=True, exist_ok=True)
    victim.write_text("keep")
    return victim


@pytest.mark.parametrize(
    "plant",
    [
        "partitions.csv",  # a file the build writes, as a link
        "main",  # a directory it writes into
        "components",
        "components/ne_agent",
        "components/ne_agent/gates",
        "main/main.c",
    ],
)
def test_a_link_in_the_project_is_never_written_through(tmp_path, plant):
    victim = _victim(tmp_path)
    project = tmp_path / "out" / "esp32s3"
    _marked(project, "partitions.csv")
    link = project / plant
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(victim if "." in plant else victim.parent, target_is_directory="." not in plant)
    before = sorted(p.name for p in victim.parent.iterdir())
    with pytest.raises(BuildFailed) as excinfo:
        build(
            _tmp_agent(tmp_path), target="esp32s3", board_id="esp32s3-box-3", out_dir=project.parent
        )
    (problem,) = excinfo.value.problems
    assert "symbolic link" in problem.why and problem.how
    assert victim.read_text() == "keep"
    assert sorted(p.name for p in victim.parent.iterdir()) == before  # nothing written there
    assert not (project.parent / "gates").exists()  # nothing written at all


def test_a_dangling_link_is_refused_before_anything_is_written(tmp_path):
    # A link to a file that does not exist yet: writing through it would create that file.
    target = tmp_path / "elsewhere" / "created-by-the-build.txt"
    target.parent.mkdir()
    project = tmp_path / "out" / "esp32s3"
    _marked(project)
    (project / "main").mkdir()
    (project / "main" / "main.c").symlink_to(target)
    (problem,) = _refused_into(tmp_path, project.parent)
    assert "symbolic link" in problem.why and "main.c" in problem.where
    assert not target.exists()
    assert not (project.parent / "gates").exists()


def test_a_linked_project_directory_is_never_written(tmp_path):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (tmp_path / "out").mkdir()
    (tmp_path / "out" / "esp32s3").symlink_to(elsewhere, target_is_directory=True)
    (problem,) = _refused_into(tmp_path, tmp_path / "out")
    assert "symbolic link" in problem.why
    assert list(elsewhere.iterdir()) == []


def _refused_into(tmp_path: Path, out: Path) -> list:
    with pytest.raises(BuildFailed) as excinfo:
        build(_tmp_agent(tmp_path), target="esp32s3", board_id="esp32s3-box-3", out_dir=out)
    return excinfo.value.problems


def test_a_link_planted_after_the_checks_is_refused_before_anything_changes(root, tmp_path):
    # The race: project_problem passed, then a link appears. write_project checks again.
    manifest, gates, specs = _parts(FIXTURE)
    files = firmware.render_project(manifest, "esp32s3-box-3", gates, specs)
    project = tmp_path / "out" / "esp32s3"
    _marked(project, "main/main.c")
    victim = _victim(tmp_path)
    (project / "partitions.csv").symlink_to(victim)
    with pytest.raises(NeuroEdgeError, match="symbolic link"):
        firmware.write_project(project, files)
    assert victim.read_text() == "keep"
    assert not (project / "main").exists()  # checked before the first write


def test_a_manifest_names_nothing_outside_the_firmware_layout(tmp_path):
    project = tmp_path / "out" / "esp32s3"
    victim = _victim(tmp_path)
    (project / "main").mkdir(parents=True)
    (project / "main" / "notes.txt").write_text("mine")
    (project / "main" / "extra.c").write_text("mine")
    _marked(
        project,
        "../../elsewhere/victim.txt",
        str(victim),
        "main/notes.txt",  # in main/, but no source pattern names it
        "main/sub/extra.c",
        "main//extra.c",
        "main/extra.c",  # a source name: an earlier build's file, removed
    )
    assert firmware.previous_files(project) == ["main/extra.c"]
    build(FIXTURE, target="esp32s3", board_id="esp32s3-box-3", out_dir=project.parent)
    assert victim.read_text() == "keep"
    assert (project / "main" / "notes.txt").read_text() == "mine"
    assert not (project / "main" / "extra.c").exists()


@pytest.mark.parametrize(
    ("name", "owned"),
    [
        ("main/main.c", True),
        ("components/ne_agent/gates/open_door.netree.h", True),
        (firmware.MANIFEST, True),
        ("main/../main/main.c", False),
        ("/etc/passwd", False),
        ("main/notes.txt", False),
        ("main/vectors/x/y.h", False),
        ("build/app.bin", False),
        ("sdkconfig", False),
        ("components/other/x.c", False),
        ("main/a .c", False),
        ("", False),
    ],
)
def test_only_names_of_the_firmware_layout_are_the_builds(name, owned):
    assert firmware.owned(name) is owned


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("version", "0.0.1\nmain/notes.txt"),
        ("version", "0.0.1\rmain/notes.txt"),
        ("name", "tmp agent"),
        ("name", "tmp\u0085agent"),
        ("version", "0.0.1‮"),
    ],
)
def test_a_label_that_breaks_a_line_is_refused(tmp_path, field, value):
    # A newline in [agent] version once put `main/notes.txt` into MANIFEST, and the next
    # build removed that file of the user's.
    agent = _tmp_agent(tmp_path)
    text = agent.read_text()
    quoted = "".join(c if " " <= c <= "~" and c not in '"\\' else f"\\u{ord(c):04X}" for c in value)
    old = 'name = "tmp-agent"' if field == "name" else 'version = "0.0.1"'
    agent.write_text(text.replace(old, f'{field} = "{quoted}"'))
    assert getattr(load_agent_manifest(agent), field) == value
    problems = _refused(agent, tmp_path / "out")
    (problem,) = [p for p in problems if f"[agent] {field}" in p.where]
    assert isinstance(problem, AgentManifestError)
    assert "control or line-break character" in problem.why and problem.how


@pytest.mark.parametrize(
    ("gates", "why"),
    [
        (("unlock-door",), "is not a C identifier"),
        (('"2fa"',), "is not a C identifier"),
        (("Lock", "lock"), "differ only in case"),
    ],
)
def test_a_gate_key_the_firmware_cannot_name_is_refused(tmp_path, gates, why):
    (problem,) = _refused(_tmp_agent(tmp_path, gates=gates), tmp_path / "out")
    assert isinstance(problem, AgentManifestError)
    assert why in problem.why and "[gates]" in problem.where and problem.how


def test_a_directory_the_build_did_not_write_is_never_overwritten(tmp_path):
    out = tmp_path / "out"
    (out / "esp32s3").mkdir(parents=True)
    (out / "esp32s3" / "notes.txt").write_text("mine")
    with pytest.raises(BuildFailed) as excinfo:
        build(_tmp_agent(tmp_path), target="esp32s3", board_id="esp32s3-box-3", out_dir=out)
    (problem,) = excinfo.value.problems
    assert "was not written by `neuroedge build" in problem.why and problem.how
    assert sorted(p.name for p in out.rglob("*")) == ["esp32s3", "notes.txt"]


def test_without_the_firmware_sources_nothing_is_written(tmp_path, monkeypatch):
    monkeypatch.setattr(firmware, "firmware_root", lambda root=None: tmp_path / "nowhere")
    (problem,) = _refused(_tmp_agent(tmp_path), tmp_path / "out")
    assert "firmware sources are not here" in problem.why and "NEUROEDGE_ROOT" in problem.how


def test_more_pins_than_a_token_mask_holds_is_refused(tmp_path):
    manifest = load_agent_manifest(_tmp_agent(tmp_path))
    manifest.requires["digital.out"]["pins"] = [f"p{i}" for i in range(firmware.MAX_PINS + 1)]
    (problem,) = firmware.firmware_problems(manifest, {})
    assert isinstance(problem, BoardCapabilityError) and "u32 mask" in problem.why


def test_the_cli_exits_1_and_writes_nothing_or_0_and_names_the_project(tmp_path):
    out = tmp_path / "out"
    (tmp_path / "bad").mkdir()
    bad = _tmp_agent(tmp_path / "bad", pins='"garage_door"')
    result = runner.invoke(app, ["build", "-t", "esp32s3", "-a", str(bad), "-o", str(out)])
    assert result.exit_code == 1 and "garage_door" in result.output
    assert not out.exists()
    result = runner.invoke(app, ["build", "-t", "esp32s3", "-a", str(FIXTURE), "-o", str(out)])
    assert result.exit_code == 0, result.output
    assert f"firmware: {out / 'esp32s3'}" in result.output
    assert "docs/user/nap-firmware.md" in result.output
    assert (out / "esp32s3" / "components" / "ne_agent" / "ne_agent.c").is_file()
