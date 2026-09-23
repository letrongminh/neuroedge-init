"""
`neuroedge run --target sim` (TSK-S3-06): the typed-text REPL over the sample agent.

The exit-code contract of test_cli.py holds: a BLOCK is the gate doing its job,
so `-c` exits 0 on it; only an agent that does not load (or a contract
violation) exits 1.
"""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from neuroedge.cli.main import app
from neuroedge.errors import AgentManifestError, BuildFailed
from neuroedge.sim import SimSession
from neuroedge.trace import load_trace

runner = CliRunner()


@pytest.fixture(scope="module")
def villa(root):
    return root / "fixtures" / "agents" / "villa-concierge" / "agent.toml"


def run(villa, *args, stdin=None):
    return runner.invoke(app, ["run", "--agent", str(villa), *args], input=stdin)


# --- one command (-c) -------------------------------------------------------------


def test_a_matching_command_is_allowed_and_pulses_the_lock(villa):
    result = run(villa, "-c", "mở cửa phòng 101")
    assert result.exit_code == 0, result.output
    assert "ALLOW" in result.output
    assert "unlock_door(guest_id='101')" in result.output
    assert "door_lock" in result.output
    assert "PULSED 30s" in result.output


def test_an_unknown_command_is_blocked_and_moves_nothing(villa):
    result = run(villa, "-c", "hát một bài")
    assert result.exit_code == 0, result.output
    assert "BLOCK" in result.output
    assert "not recognized" in result.output
    assert "ALLOW" not in result.output


def test_the_wrong_room_is_blocked_and_escalated(villa):
    result = run(villa, "-c", "mở cửa phòng 202")
    assert result.exit_code == 0, result.output
    assert "BLOCK" in result.output
    assert "room_matches" in result.output
    assert "escalate to human_receptionist" in result.output
    assert "PULSED" not in result.output


def test_a_known_intent_without_an_action_moves_nothing(villa):
    result = run(villa, "-c", "wifi là gì")
    assert result.exit_code == 0, result.output
    assert "faq" in result.output
    assert "no physical action" in result.output


def test_an_incompatible_board_exits_one_and_names_the_missing_aec(villa):
    result = run(villa, "--board", "linux-rpi5", "-c", "mở cửa phòng 101")
    assert result.exit_code == 1, result.output
    assert "NE3001" in result.output
    assert "aec" in result.output
    assert "ALLOW" not in result.output


def test_a_missing_agent_exits_one_with_a_three_part_diagnostic(tmp_path):
    result = runner.invoke(app, ["run", "--agent", str(tmp_path / "agent.toml"), "-c", "x"])
    assert result.exit_code == 1
    assert "NE3002" in result.output
    assert "why:" in result.output and "fix:" in result.output


def test_other_targets_exit_two_and_name_their_task(villa):
    result = run(villa, "--target", "linux", "-c", "mở cửa phòng 101")
    assert result.exit_code == 2
    assert "TSK-S3-05" in result.output


def test_the_default_agent_is_the_sample_in_a_checkout(root, monkeypatch):
    monkeypatch.chdir(root)
    result = runner.invoke(app, ["run", "-c", "mở cửa phòng 101"])
    assert result.exit_code == 0, result.output
    assert "ALLOW" in result.output


# --- trace ------------------------------------------------------------------------


def test_trace_out_writes_a_valid_trace_of_the_session(villa, tmp_path):
    out = tmp_path / "trace.json"
    result = run(villa, "-c", "mở cửa phòng 101", "--trace-out", str(out))
    assert result.exit_code == 0, result.output
    trace = load_trace(out)  # validates against schemas/trace.v1.json
    assert trace["metadata"]["target"] == "sim"
    assert trace["metadata"]["agent_version"] == "villa-concierge@0.1.0"
    types = [event["type"] for event in trace["events"]]
    assert types[:2] == ["text_input", "intent_extracted"]
    verdicts = [e["data"] for e in trace["events"] if e["type"] == "gate_evaluation_result"]
    assert [v["verdict"] for v in verdicts] == ["ALLOW"]
    assert "actuator_command" in types


def test_a_blocked_session_trace_has_no_actuator_command(villa, tmp_path):
    out = tmp_path / "trace.json"
    run(villa, "-c", "mở cửa phòng 202", "--trace-out", str(out))
    types = [event["type"] for event in json.loads(out.read_text("utf-8"))["events"]]
    assert "gate_evaluation_result" in types
    assert "actuator_command" not in types


# --- the REPL ---------------------------------------------------------------------


def test_the_repl_runs_lines_until_exit(villa):
    result = run(villa, stdin="mở cửa phòng 101\nmở cửa phòng 202\nexit\n")
    assert result.exit_code == 0, result.output
    assert "neuroedge>" in result.output
    assert result.output.count("ALLOW") == 1
    assert result.output.count("✗ BLOCK") == 1


def test_ctrl_d_leaves_the_repl_with_exit_zero(villa):
    result = run(villa, stdin="")
    assert result.exit_code == 0, result.output
    assert "door_lock" in result.output  # the initial pin table


def test_set_false_turns_an_allow_into_a_block(villa):
    stdin = ":set guest_authenticated false\nmở cửa phòng 101\nquit\n"
    result = run(villa, stdin=stdin)
    assert result.exit_code == 0, result.output
    assert "guest_authenticated = false" in result.output
    assert "criterion: guest_authenticated" in result.output
    assert "ALLOW" not in result.output


def test_unset_makes_a_fact_undecided_which_blocks(villa):
    result = run(villa, stdin=":unset risk_level\nmở cửa phòng 101\nexit\n")
    assert result.exit_code == 0, result.output
    assert "criterion_unavailable" in result.output


def test_facts_and_help_describe_the_session(villa):
    result = run(villa, stdin=":facts\n:help\n:nope\nexit\n")
    assert result.exit_code == 0, result.output
    assert "guest_authenticated" in result.output
    assert "from slot {room}" in result.output
    assert ":unset" in result.output
    assert "unknown command :nope" in result.output


def test_repl_trace_records_every_turn(villa, tmp_path):
    out = tmp_path / "trace.json"
    stdin = "mở cửa phòng 101\nhát một bài\nexit\n"
    result = run(villa, "--trace-out", str(out), stdin=stdin)
    assert result.exit_code == 0, result.output
    types = [event["type"] for event in load_trace(out)["events"]]
    assert types.count("text_input") == 2
    assert "command_not_recognized" in types


# --- SimSession -------------------------------------------------------------------


async def test_a_bare_command_leaves_the_slot_fact_undecided(villa):
    session = SimSession.load(villa)
    turn = await session.handle("mở cửa")
    assert turn.result.blocked
    assert turn.result.gate.failed_criterion == "room_matches"
    assert session.hal.pin("door_lock").never_pulsed()


async def test_facts_override_the_manifest(villa):
    session = SimSession.load(villa, facts={"risk_level": "high"})
    turn = await session.handle("mở cửa phòng 101")
    assert turn.result.blocked
    assert turn.result.gate.failed_criterion == "risk_level"


def _agent(tmp_path, *, sim: str = "", command_extra: str = "") -> object:
    # @action names are process-global, so each temporary project gets its own.
    name = f"blink_{abs(hash(str(tmp_path)))}"
    (tmp_path / "actions").mkdir()
    (tmp_path / "actions" / "blink.py").write_text(
        "from neuroedge import action\n"
        "from neuroedge.hal import digital\n\n"
        f'@action(name="{name}", requires="digital.out:porch_light", gate="g")\n'
        "def blink() -> None:\n"
        '    digital.out("porch_light").pulse(seconds=1)\n',
        encoding="utf-8",
    )
    (tmp_path / "gate.yaml").write_text(
        "schema: neuroedge.gate/v1\nname: g\nversion: 1.0.0\n"
        "evaluate:\n  ok:\n    type: bool\n    instructions: ok\n"
        "allow_when:\n  ok: true\n"
        "on_block:\n  action: deny\n"
        "budget:\n  p95_latency_ms: 100\n  fail: closed\n",
        encoding="utf-8",
    )
    (tmp_path / "commands.toml").write_text(
        '[grammar]\nversion = 1\n\n[[command]]\nintent = "blink"\npatterns = ["blink"]\n'
        + command_extra,
        encoding="utf-8",
    )
    (tmp_path / "agent.toml").write_text(
        '[agent]\nname = "session-test"\nversion = "0.1.0"\n\n'
        '[requires]\n"digital.out" = { pins = ["porch_light"] }\n\n'
        '[gates]\ng = "gate.yaml"\n' + sim,
        encoding="utf-8",
    )
    return tmp_path / "agent.toml"


def test_a_command_naming_an_unknown_action_fails_the_build(tmp_path):
    agent = _agent(tmp_path, command_extra='action = "no_such_action"\n')
    with pytest.raises(BuildFailed) as failed:
        SimSession.load(agent)
    assert any("no_such_action" in problem.why for problem in failed.value.problems)


def test_a_malformed_slot_fact_is_a_manifest_error(tmp_path):
    agent = _agent(tmp_path, sim='\n[sim.slot_facts]\nok = "yes"\n')
    with pytest.raises(AgentManifestError, match="slot fact"):
        SimSession.load(agent)
