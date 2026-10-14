"""
TSK-I2f-12, Q-83 — the brain bridge of Profile B speaks the box's own contract.

`targets/esp32s3/components/ne_brain_bridge/` is what NeuroClaw-ESP calls on one chip, by
function call, instead of MCP (docs/spec/deployment_profiles.md, DP-B-02 → DP-B-07, DP-COM-01,
DP-COM-02, DP-COM-09). It is compiled here with AddressSanitizer and UndefinedBehaviorSanitizer,
with the `ne_agent` component `neuroedge build --target esp32s3` generates for an agent, and
driven by a script (`test/test_bridge_host.c`). The same calls go through the box
(`SimSession.call_tool`, source `mcp`): the tool list, and every result object, must be the
same — only `confirmation.who` names the chip's own human channel.

Two agents: the NeuroClaw demo `fixtures/agents/chat-den-cua` (lights and the front door), and
`fixtures/agents/contract-bench`, one gate per kind of block: a numeric reading, a confidence
floor, `escalate`, `degrade` with a fallback, and an action whose arguments are required.
"""

from __future__ import annotations

import asyncio
import json
import random
import re
import subprocess
import tomllib
from pathlib import Path

import jsonschema
import pytest

from neuroedge.actions.tools import ToolCall
from neuroedge.engine.compiler import build
from neuroedge.engine.firmware import COMPONENT, PROJECT_DIR
from neuroedge.paths import repo_root
from neuroedge.sim import SimSession

from .test_c_walker import STACK_LIMIT, STRICT, cc

ROOT = repo_root()
COMPONENTS = ROOT / "targets" / "esp32s3" / "components"
BRIDGE = COMPONENTS / "ne_brain_bridge"
SAN = [
    "-fsanitize=address,undefined,float-cast-overflow",
    "-fno-sanitize-recover=all",
    "-fno-omit-frame-pointer",
]
WHO = "the owner, on the board's button or in Telegram; not this caller"  # NE_BRIDGE_WHO
RESULT_SCHEMA = json.loads((ROOT / "schemas" / "tool-result.v1.json").read_text(encoding="utf-8"))


def sources(agent: Path) -> list[str]:
    return [
        str(COMPONENTS / "ne_gate" / "src" / "ne_walker.c"),
        str(COMPONENTS / "ne_gate" / "src" / "ne_token.c"),
        str(BRIDGE / "src" / "ne_brain_bridge.c"),
        str(agent / "ne_agent.c"),
    ]


def includes(agent: Path) -> list[str]:
    out = []
    for path in (
        COMPONENTS / "ne_gate" / "include",
        COMPONENTS / "ne_trace" / "include",
        agent / "include",
        BRIDGE / "include",
    ):
        out += ["-I", str(path)]
    return out


def compile_bridge(agent: Path, out: Path) -> Path:
    command = [
        cc(),
        *STRICT,
        "-O1",
        "-g",
        *SAN,
        *includes(agent),
        *sources(agent),
        str(BRIDGE / "test" / "test_bridge_host.c"),
        "-o",
        str(out),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return out


class Bridge:
    """The compiled harness of one agent, and that agent's manifest for the box."""

    def __init__(self, exe: Path, manifest: Path, work: Path) -> None:
        self.exe, self.manifest, self.work = exe, manifest, work

    def run(self, *lines: str) -> list[str]:
        script = self.work / "script.txt"
        script.write_text("\n".join(lines) + "\n", encoding="utf-8")
        result = subprocess.run(
            [str(self.exe), str(script)], capture_output=True, text=True, timeout=120
        )
        out = result.stdout.splitlines()
        # a crash or a sanitizer report is a failure, never a pass
        assert result.returncode == 0 and not result.stderr, result.stderr[-3000:]
        assert not [line for line in out if line.startswith("error")], out
        return out

    def results(self, *lines: str) -> list[dict]:
        out = []
        for line in self.run(*lines):
            if line.startswith("result\t"):
                _, status, text = line.split("\t", 2)
                result = json.loads(text)
                assert result["status"] == status
                out.append(result)
        return out


def built(tmp: Path, agent: Path) -> Bridge:
    out = tmp / "out"
    build(agent / "agent.toml", target="esp32s3", board_id="esp32s3-box-3", out_dir=str(out))
    component = out / PROJECT_DIR / COMPONENT
    return Bridge(compile_bridge(component, tmp / "bridge"), agent / "agent.toml", tmp)


@pytest.fixture(scope="module")
def demo(tmp_path_factory) -> Bridge:
    """The NeuroClaw demo agent, built for the chip as it is for the box."""
    return built(tmp_path_factory.mktemp("demo"), ROOT / "fixtures" / "agents" / "chat-den-cua")


@pytest.fixture(scope="module")
def bench(tmp_path_factory) -> Bridge:
    """`fixtures/agents/contract-bench`: one gate per kind of block (deny, escalate, degrade)."""
    return built(tmp_path_factory.mktemp("bench"), ROOT / "fixtures" / "agents" / "contract-bench")


def through_the_box(manifest: Path, steps: list[tuple]) -> list[dict]:
    """The same steps on the box: ("fact", name, value) and ("call", tool, arguments)."""
    session = SimSession.load(manifest)
    out = []
    for step in steps:
        if step[0] == "fact":
            session.set_fact(step[1], step[2])
        else:
            call = ToolCall(step[1], step[2], source="mcp")
            out.append(asyncio.run(session.call_tool(call)).content())
    return out


def through_the_bridge(bridge: Bridge, steps: list[tuple]) -> list[dict]:
    """The same steps on the bridge, after the agent's `[sim.facts]`, as the box starts from."""
    with bridge.manifest.open("rb") as handle:
        sim_facts = tomllib.load(handle).get("sim", {}).get("facts", {})
    steps = [("fact", name, value) for name, value in sim_facts.items()] + list(steps)
    lines = []
    for step in steps:
        if step[0] == "fact":
            value = step[2]
            lines.append(
                f"fact {step[1]} {json.dumps(value) if not isinstance(value, str) else value}"
            )
        else:
            lines.append(f"call {step[1]} {json.dumps(step[2], ensure_ascii=False)}")
    return bridge.results(*lines)


def same_contract(box: list[dict], chip: list[dict]) -> None:
    assert len(box) == len(chip)
    for mine, theirs in zip(chip, box, strict=True):
        jsonschema.validate(mine, RESULT_SCHEMA)
        jsonschema.validate(theirs, RESULT_SCHEMA)
        mine, theirs = dict(mine), dict(theirs)
        if "confirmation" in mine:
            assert mine["confirmation"].pop("who") == WHO
            theirs["confirmation"] = {
                k: v for k, v in theirs.get("confirmation", {}).items() if k != "who"
            }
        assert mine == theirs


# --- the tools (DP-B-03, DP-COM-02) ------------------------------------------------------


def test_the_bridge_offers_the_tools_the_box_lists_over_mcp(demo):
    """TC-B-03-1: the same names, descriptions and input schemas, generated at build time."""
    chip = [line.split("\t")[1:] for line in demo.run("tools") if line.startswith("tool\t")]
    box = SimSession.load(demo.manifest).tools.mcp()
    assert sorted(
        (name, description, json.loads(schema)) for name, description, schema in chip
    ) == sorted((t["name"], t["description"], t["inputSchema"]) for t in box)
    assert [name for name, _, _ in chip] == sorted(name for name, _, _ in chip)


# --- the same calls, the same results (DP-COM-01, DP-B-06) -----------------------------


DEMO_STEPS = [
    ("fact", "light_fault_free", True),
    ("fact", "daytime", True),
    ("fact", "owner_confirmed", False),
    ("call", "living_light_on", {}),
    ("call", "front_door_unlock", {"duration_s": 10}),
    ("call", "front_door_unlock", {}),
    ("call", "front_door_unlock", {"duration_s": 45}),
    ("call", "front_door_unlock", {"duration_s": "12"}),
    ("call", "front_door_unlock", {"duration_s": 2.5}),
    ("call", "front_door_unlock", {"duration_s": True}),
    ("call", "front_door_unlock", {"duration_s": "mười"}),
    ("call", "front_door_unlock", {"x": 1, "duration_s": 3, "a b": None}),
    ("call", "open_garage", {}),
    ("call", "front_door_unlock", {"duration_s": 20}),
    ("call", "front_door_unlock", {"duration_s": 5}),  # a fifth question: budget_exceeded
    ("fact", "daytime", False),
    ("call", "front_door_unlock", {"duration_s": 5}),
    ("fact", "light_fault_free", False),
    ("call", "living_light_off", {}),
]


def test_the_same_calls_give_the_same_results_through_mcp_and_through_the_bridge(demo):
    """TC-COM-01-2: one brain code path reads both profiles; every result is tool-result.v1."""
    chip = through_the_bridge(demo, DEMO_STEPS)
    same_contract(through_the_box(demo.manifest, DEMO_STEPS), chip)
    statuses = [r["status"] for r in chip]
    assert statuses.count("ALLOW") == 1 and statuses.count("REJECTED") == 5
    assert [r["reason"] for r in chip if r["status"] == "BLOCK"] == [
        "condition_not_met",
        "condition_not_met",
        "argument_out_of_range",
        "condition_not_met",
        "condition_not_met",
        "budget_exceeded",
        "condition_not_met",
        "condition_not_met",
    ]


BENCH_STEPS = [
    ("fact", "lamp_ok", True),
    ("fact", "armed", False),
    ("call", "siren_on", {}),  # degrade: the lamp comes on instead
    ("fact", "lamp_ok", False),
    ("call", "siren_on", {}),  # degrade: the lamp is blocked too
    ("call", "guest_unlock", {}),  # a reading without a confidence: confidence_unavailable
    ("call", "heater_on", {"level": 9}),  # argument_out_of_range before any reading
    ("call", "heater_on", {"level": 1e300}),  # an integer for Python too: out of range
    ("call", "heater_on", {"level": "2.0"}),  # int("2.0") fails: a problem
    ("call", "heater_on", {"temperature": "1e3"}),  # float("1e3"): no reading, unavailable
    ("call", "arm_zone", {}),
    ("call", "arm_zone", {"code": 1234, "zone": "2", "force": "TRUE", "extra": [1, 2]}),
    ("call", "arm_zone", {"code": "x", "zone": 1.5, "force": 1}),
]


def test_every_kind_of_block_maps_to_the_same_result_on_both(bench):
    """TC-COM-01-2 on the bench agent: escalate, degrade with a fallback, confidence, problems."""
    chip = through_the_bridge(bench, BENCH_STEPS)
    same_contract(through_the_box(bench.manifest, BENCH_STEPS), chip)
    assert chip[0]["fallback"] == {"tool": "porch_lamp_on", "status": "ALLOW"}
    assert chip[1]["fallback"]["status"] == "BLOCK"
    assert chip[2]["reason"] == "confidence_unavailable" and chip[2]["on_block"] == "escalate"
    assert chip[2]["escalated_to"] == "night_manager"


def test_every_reason_and_on_block_action_maps_to_a_valid_result(bench):
    """TC-B-06-1: each ne_result reason, each on_block action -> tool-result.v1."""
    results = bench.results(
        "fact lamp_ok true",
        "fact armed false",
        "call siren_on",  # degrade
        "fact guest_ok true",
        "call guest_unlock",  # escalate, confidence_unavailable
        "fact guest_ok true@0.5",
        "call guest_unlock",  # condition_not_met (below the floor)
        "fact guest_ok -",
        "call guest_unlock",  # criterion_unavailable
        'call heater_on {"level": 9}',  # argument_out_of_range, deny
        "fact temperature 99",
        "call heater_on",  # value_out_of_range
        "fact temperature 25",
        "degraded unreachable",
        "call heater_on",  # gate_unreachable
        "degraded budget",
        "call heater_on",  # budget_exceeded
        "degraded none",
        "call heater_on",  # ALLOW
    )
    for result in results:
        jsonschema.validate(result, RESULT_SCHEMA)
    reasons = [r.get("reason") for r in results]
    assert reasons == [
        "condition_not_met",
        "confidence_unavailable",
        "condition_not_met",
        "criterion_unavailable",
        "argument_out_of_range",
        "value_out_of_range",
        "gate_unreachable",
        "budget_exceeded",
        None,
    ]
    assert [r.get("on_block") for r in results] == [
        "degrade",
        "escalate",
        "escalate",
        "escalate",
        "deny",
        "deny",
        "deny",
        "deny",
        None,
    ]
    assert results[1]["escalated_to"] == "night_manager" and results[-1]["status"] == "ALLOW"
    assert results[4]["failed_criterion"] == "level"


# --- arguments (DP-B-04) and facts (DP-B-05) -----------------------------------------------


def test_bad_arguments_are_rejected_before_any_gate(bench):
    """TC-B-04-1: unknown, missing, wrongly typed -> REJECTED with problems; nothing read or run."""
    out = bench.run(
        "fact lamp_ok true",
        'call arm_zone {"zone": 1, "nope": 2}',
        'call arm_zone {"code": "a", "zone": "two"}',
        'call arm_zone {"code": "a", "zone": 1, "zone": 2}',
        "call arm_zone [1, 2]",
        'call arm_zone {"code": "a",',
        "call arm_zone " + json.dumps({"code": "x" * 300, "zone": 1}),
        "reads",
    )
    results = [json.loads(line.split("\t", 2)[2]) for line in out if line.startswith("result")]
    assert [r["status"] for r in results] == ["REJECTED"] * 6
    assert results[0]["problems"] == [
        "unknown argument 'nope'; arm_zone takes ['code', 'force', 'zone']",
        "missing required argument 'code'",
    ]
    assert results[1]["problems"] == ["argument 'zone' must be integer, got 'two'"]
    assert results[2]["problems"] == ["an argument is given twice"]
    assert results[3]["problems"] == ["the arguments are not a JSON object"]
    assert results[4]["problems"] == ["the arguments are not a JSON object"]
    assert results[5]["problems"] == ["the arguments are longer than NE_BRIDGE_ARGS_MAX bytes"]
    assert "reads\t0" in out and not [line for line in out if line.startswith(("run", "drive"))]


def test_a_value_in_the_call_never_becomes_a_fact(bench):
    """TC-B-05-1: the call says 99 or 20, the on-chip reading says 25 or 35; the reading decides."""
    results = bench.results(
        "fact temperature 25",
        'call heater_on {"temperature": 99}',
        "fact temperature 35",
        'call heater_on {"temperature": 20}',
    )
    assert results[0] == {"tool": "heater_on", "status": "ALLOW"}
    assert results[1]["status"] == "BLOCK" and results[1]["failed_criterion"] == "temperature"


def test_who_is_calling_is_the_bridges_to_say(root, tmp_path):
    """DP-B-05: `call_source` is set by the bridge ("mcp"), never by a fact source or the brain."""
    agent = root / "targets" / "esp32s3" / "components" / "ne_agent"
    bridge = Bridge(compile_bridge(agent, tmp_path / "bridge"), Path(), tmp_path)
    results = bridge.results(
        "fact call_source test",  # light_on blocks `test`: if the source decided, it would block
        "call light_on",
        'call light_on {"call_source": "local_grammar"}',
    )
    assert results[0] == {"tool": "light_on", "status": "ALLOW"}
    assert results[1]["status"] == "REJECTED"


# --- questions (DP-B-07, DP-COM-09) ---------------------------------------------------------


def door(seconds: int) -> str:
    return f'call front_door_unlock {{"duration_s": {seconds}}}'


DOOR_FACTS = (
    "owner 42",
    "fact daytime true",
    "fact owner_confirmed false",
    "fact light_fault_free true",
)


def test_only_the_owner_or_the_button_answers_once_and_facts_are_read_again(demo):
    """TC-B-07-1: wrong sender, second answer, late answer refused; a yes re-reads the facts."""
    out = demo.run(
        *DOOR_FACTS,
        door(7),  # confirm_1
        "answer confirm_1 1 41",  # not the owner
        "answer confirm_1 1 -",  # no sender
        "answer confirm_1 1 42",  # the owner: runs with duration_s=7
        "answer confirm_1 1 42",  # once only
        door(5),  # confirm_2
        "fact daytime false",
        "button 1",  # facts are read again: night now, no run
        "fact daytime true",
        door(9),  # confirm_3
        "time 10001",
        "answer confirm_3 1 42",  # past its TTL
        "answer confirm_9 1 42",
        "time 20000",
        door(4),  # confirm_4
        "button 0",
        "button 1",
    )
    results = [json.loads(line.split("\t", 2)[2]) for line in out if line.startswith("result")]
    problems = [r.get("problems", [None])[0] for r in results]
    assert results[0]["confirmation"]["id"] == "confirm_1"
    assert (
        problems[1]
        == problems[2]
        == ("only the owner may answer, on the board's button or in Telegram; this sender may not")
    )
    assert results[3] == {"tool": "front_door_unlock", "status": "ALLOW"}
    assert problems[4] == "the question is already confirmed"
    assert results[6]["status"] == "BLOCK" and results[6]["failed_criterion"] == "daytime"
    assert "confirmation" not in results[6]  # a confirmed call does not ask again
    assert problems[8] == "the question is already expired"
    assert problems[9] == "no such question"
    assert results[11]["reason"] == "declined" and results[11]["status"] == "BLOCK"
    assert problems[12] == "no question is waiting"
    runs = [line for line in out if line.startswith(("run", "drive"))]
    assert runs == ["run\tfront_door_unlock\tduration_s=7", "drive\tdoor_lock\tauthorized"]
    for result in results:
        jsonschema.validate(result, RESULT_SCHEMA)


def test_four_questions_wait_at_most_and_allow_still_runs(demo):
    """TC-COM-09-2: the bridge's table holds four; tokens for an ALLOW are not taken by them."""
    out = demo.run(
        *DOOR_FACTS,
        *(door(s) for s in (1, 2, 3, 4, 5)),
        "waiting",
        "call living_light_on",
        "button 1",  # the latest waiting: confirm_4, duration 4
        door(6),  # a place is free again: confirm_5
        "waiting",
    )
    results = [json.loads(line.split("\t", 2)[2]) for line in out if line.startswith("result")]
    assert [r.get("confirmation", {}).get("id") for r in results[:5]] == [
        "confirm_1",
        "confirm_2",
        "confirm_3",
        "confirm_4",
        None,
    ]
    assert results[4]["reason"] == "budget_exceeded"
    assert results[5] == {"tool": "living_light_on", "status": "ALLOW"}
    assert results[6] == {"tool": "front_door_unlock", "status": "ALLOW"}
    assert results[7]["confirmation"]["id"] == "confirm_5"
    assert [line for line in out if line.startswith("waiting")] == ["waiting\t4", "waiting\t4"]
    assert "run\tfront_door_unlock\tduration_s=4" in out


# --- untrusted input -------------------------------------------------------------------------


def test_any_arguments_get_an_answer_and_never_a_crash(bench):
    """What the LLM sends is untrusted: every input gets one valid result, under the sanitizers."""
    rng = random.Random(83)
    pieces = [
        "{",
        "}",
        "[",
        "]",
        '"',
        "\\",
        ":",
        ",",
        "true",
        "null",
        "-0",
        "1e999",
        '"\\u',
        "d83d",
        '"code"',
        '"zone"',
        '"force"',
        " ",
        "é",
        "\x01",
        '"\\ud83d\\ude00"',
        "0.5",
        '{"a":',
    ]
    lines = []
    for _ in range(400):
        text = "".join(rng.choice(pieces) for _ in range(rng.randint(0, 24)))
        lines.append(f"call {rng.choice(['arm', 'heater_on', 'porch_lamp_on', 'x'])} {text}")
    lines += [
        f'call heater_on {{"level": {v}, "temperature": {v}}}'
        for v in ("1e999", "-1e999", "1e300", "2.0", '"9e15"')
    ]
    lines += [
        "call arm_zone " + "[" * 200 + "]" * 200,
        'call arm_zone {"code": "' + "\\u00e9" * 40 + '"}',
    ]
    results = bench.results("fact lamp_ok true", "fact temperature 20", *lines)
    assert len(results) == len(lines)
    for result in results:
        jsonschema.validate(result, RESULT_SCHEMA)


# --- the static budget (C2) -----------------------------------------------------------------


def test_the_bridge_uses_no_static_ram_and_a_small_stack(tmp_path):
    agent = COMPONENTS / "ne_agent"
    obj = tmp_path / "ne_brain_bridge.o"
    command = [
        cc(),
        *STRICT,
        "-O2",
        "-fstack-usage",
        *includes(agent),
        "-c",
        str(BRIDGE / "src" / "ne_brain_bridge.c"),
        "-o",
        str(obj),
    ]
    result = subprocess.run(command, capture_output=True, text=True, cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    symbols = subprocess.run(["nm", str(obj)], capture_output=True, text=True, check=True).stdout
    writable = [line for line in symbols.splitlines() if re.search(r"\s[bBdDC]\s", line)]
    assert writable == [], f"the bridge must hold no .data/.bss state: {writable}"
    usage = (tmp_path / "ne_brain_bridge.su").read_text()
    frames = {m.group(1): int(m.group(2)) for m in re.finditer(r":(\w+)\s+(\d+)\s+\w+", usage)}
    assert "ne_bridge_call" in frames, usage
    assert max(frames.values()) <= STACK_LIMIT, frames
