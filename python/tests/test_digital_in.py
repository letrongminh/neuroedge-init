"""
TSK-I2a-02 — `digital.in` on `sim` (RFC-0007 §3a, §3e, §7, §9 items 4, 10, 11; Q-62).

A declared input line is read as a logic level. The level reaches the gate as a `bool` fact
carrying the HAL's read mark: the engine ages it against the verdict, a level read more than
`DIGITAL_IN_MAX_AGE_MS` before it (or after it) is unavailable, and a line that cannot be read
is unavailable too — never a level that was not read, and not even under `fail: open`.
`[sim.digital_facts]` binds a criterion to a pin (RFC-0007 binds none; it follows
`[sim.sensor_facts]`); the `linux` half is `test_digital_in_linux.py`.
"""

from __future__ import annotations

import json

import pytest
import yaml

from neuroedge import digital
from neuroedge.engine import ActionContractEngine, EventLog, Fact, GateVerdict, Reason
from neuroedge.engine.compiler import build, load_agent_manifest
from neuroedge.engine.gate_resolver import resolve_gate_document
from neuroedge.engine.verdict import DIGITAL_IN_MAX_AGE_MS, DIGITAL_IN_SOURCE
from neuroedge.errors import (
    AgentManifestError,
    BoardCapabilityError,
    BuildFailed,
    NeuroEdgeError,
    PerceptionUnavailableError,
)
from neuroedge.hal import HardwareAbstractionLayer
from neuroedge.hal.board import load_board_by_id
from neuroedge.hal.sim import SimHAL
from neuroedge.sim import SimSession
from neuroedge.testing import TracePlayer
from neuroedge.testing.recorder import TraceRecorder

BOARD = "sim-rpi5"

SHUT_GATE = """\
schema: neuroedge.gate/v1
name: shut
version: 1.0.0
evaluate:
  door_closed:
    type: bool
    instructions: the door contact reads closed
allow_when:
  door_closed: true
on_block:
  action: deny
budget:
  p95_latency_ms: 100
  fail: {fail}
"""
OPEN_GATE = """\
schema: neuroedge.gate/v1
name: free
version: 1.0.0
evaluate:
  call_source:
    type: choice
    options: [local_grammar, system_one, system_two, mcp, test]
    instructions: who called
allow_when:
  call_source: { in: [local_grammar] }
on_block:
  action: deny
budget:
  p95_latency_ms: 100
  fail: closed
"""
LEVEL_GATE = SHUT_GATE.replace("type: bool", "type: level\n    levels: [low, high]")


class FakeClock:
    def __init__(self, start: float = 1000.0) -> None:
        self.now = float(start)

    def __call__(self) -> float:
        return self.now

    def advance(self, ms: float) -> None:
        self.now += ms


def agent(
    tmp_path,
    *,
    pins='["door_contact_raw", "limit_switch"]',
    inputs="door_contact_raw = true\nlimit_switch = false",
    facts='door_closed = { pin = "door_contact_raw" }',
    gate=SHUT_GATE.replace("{fail}", "closed"),
):
    """`đóng cổng` behind the door gate; `đọc công tắc` reads a line inside its action body."""
    name = f"din_{abs(hash(str(tmp_path)))}"  # @action names are process-wide
    (tmp_path / "actions").mkdir(parents=True, exist_ok=True)
    (tmp_path / "actions" / "gate.py").write_text(
        "from neuroedge import action\n"
        "from neuroedge.hal import digital\n\n"
        f'@action(name="{name}_shut", requires="digital.out:gate_relay", gate="shut")\n'
        "def shut() -> None:\n"
        '    digital.out("gate_relay").on()\n\n'
        f'@action(name="{name}_read", gate="free",\n'
        '        requires=["digital.out:gate_relay", "digital.in:limit_switch"])\n'
        "def read() -> None:\n"
        '    if digital.input("limit_switch").level():\n'
        '        digital.out("gate_relay").on()\n'
        "    else:\n"
        '        digital.out("gate_relay").off()\n',
        encoding="utf-8",
    )
    (tmp_path / "shut.yaml").write_text(gate, encoding="utf-8")
    (tmp_path / "free.yaml").write_text(OPEN_GATE, encoding="utf-8")
    (tmp_path / "commands.toml").write_text(
        '[grammar]\nversion = 1\n\n[[command]]\nintent = "shut"\npatterns = ["đóng cổng"]\n'
        f'tool = "{name}_shut"\n\n[[command]]\nintent = "read"\npatterns = ["đọc công tắc"]\n'
        f'tool = "{name}_read"\n',
        encoding="utf-8",
    )
    (tmp_path / "agent.toml").write_text(
        '[agent]\nname = "digital-in-test"\nversion = "0.1.0"\n\n'
        f'[requires]\n"digital.out" = {{ pins = ["gate_relay"] }}\n'
        f'"digital.in" = {{ pins = {pins} }}\n\n'
        '[gates]\nshut = "shut.yaml"\nfree = "free.yaml"\n\n'
        f"[sim.inputs]\n{inputs}\n\n[sim.digital_facts]\n{facts}\n",
        encoding="utf-8",
    )
    return tmp_path / "agent.toml"


def load(tmp_path, **kwargs):
    options = {key: kwargs.pop(key) for key in ("clock", "events") if key in kwargs}
    return SimSession.load(agent(tmp_path, **kwargs), board_id=BOARD, **options)


# --- the board's input pins, and the HAL primitive ---------------------------------------


def test_the_sim_hal_reads_a_declared_input_as_a_level_and_records_it():
    events = EventLog()
    hal = SimHAL(load_board_by_id(BOARD), events=events)
    hal.set_digital_in("limit_switch", True)
    assert hal.digital_in("limit_switch", called_from="test") is True
    hal.set_digital_in("limit_switch", False)
    assert hal.digital_in("limit_switch", called_from="test") is False
    assert [e["data"] for e in events.events if e["type"] == "digital_in"] == [
        {"pin": "limit_switch", "value": True},
        {"pin": "limit_switch", "value": False},
    ]


def test_an_undeclared_pin_is_refused_with_three_parts_and_nothing_is_read_or_recorded():
    events = EventLog()
    hal = SimHAL(load_board_by_id(BOARD), events=events)
    with pytest.raises(BoardCapabilityError) as raised:
        hal.digital_in("door_lock", called_from="actions/a.py:3")  # an output, not an input
    error = raised.value
    assert "actions/a.py:3" in error.where and "door_contact_raw" in error.why
    assert "[capabilities.digital_in]" in error.how
    with pytest.raises(BoardCapabilityError):
        hal.set_digital_in("nope", True)
    assert not [e for e in events.events if e["type"] == "digital_in"]


def test_an_input_nobody_set_is_a_failed_read_not_a_level():
    events = EventLog()
    hal = SimHAL(load_board_by_id(BOARD), events=events)
    with pytest.raises(PerceptionUnavailableError) as raised:
        hal.digital_in("limit_switch", called_from="test")
    assert raised.value.code == "NE5001"
    (event,) = [e["data"] for e in events.events if e["type"] == "digital_in"]
    assert event["pin"] == "limit_switch" and "no level set" in event["reason"]
    assert "value" not in event


@pytest.mark.parametrize("level", [1, 0, "high", None])
def test_a_level_is_a_bool(level):
    hal = SimHAL(load_board_by_id(BOARD))
    with pytest.raises(BoardCapabilityError, match="not a logic level"):
        hal.set_digital_in("limit_switch", level)


def test_the_read_mark_is_taken_on_the_event_log_clock_before_the_read():
    clock = FakeClock(5000.0)
    hal = SimHAL(load_board_by_id(BOARD), events=EventLog(clock))
    hal.set_digital_in("limit_switch", True)
    clock.advance(37)
    reading = hal.digital_reading("limit_switch", called_from="test")
    assert reading.value is True and reading.read_ms == 5037.0


def test_a_board_without_digital_in_refuses_every_pin():
    hal = SimHAL(load_board_by_id("sim-default"))
    with pytest.raises(BoardCapabilityError, match="no digital.in pins"):
        hal.digital_in("door_contact_raw", called_from="test")


def test_a_target_whose_hal_has_no_digital_in_says_so():
    hal = HardwareAbstractionLayer(target="esp32s3", board=load_board_by_id(BOARD))
    with pytest.raises(BoardCapabilityError, match="not implemented on target 'esp32s3'"):
        hal.digital_in("limit_switch", called_from="test")


# --- [requires]: precise per pin, at build -------------------------------------------------


def test_an_undeclared_pin_in_requires_is_refused_at_build(tmp_path):
    path = agent(tmp_path, pins='["limit_switch", "button_boot"]')
    with pytest.raises(BuildFailed) as raised:
        build(path, target="sim", board_id=BOARD)
    refused = [p for p in raised.value.problems if isinstance(p, BoardCapabilityError)]
    assert any("digital.in:button_boot" in p.where for p in refused)
    assert any("limit_switch" in p.why and "door_contact_raw" in p.why for p in refused)


def test_the_default_sim_board_has_no_inputs_and_the_build_names_the_board_that_has(tmp_path):
    path = agent(tmp_path)
    with pytest.raises(BuildFailed) as raised:
        build(path, target="sim")
    text = " ".join(f"{p.why} {p.how}" for p in raised.value.problems)
    assert "digital.in" in text and "sim-rpi5" in text


def test_an_agent_that_declares_the_pins_builds_on_both_boards_that_have_them(tmp_path):
    path = agent(tmp_path)
    build(path, target="sim", board_id=BOARD)
    build(path, target="linux", board_id="linux-rpi5")


def test_requires_pins_must_be_a_list_of_names(tmp_path):
    path = agent(tmp_path, pins='"limit_switch"')
    with pytest.raises(BuildFailed) as raised:
        build(path, target="sim", board_id=BOARD)
    assert any("list of input pin names" in p.why for p in raised.value.problems)


def test_an_action_may_require_only_a_pin_requires_declares(tmp_path):
    path = agent(tmp_path, pins='["door_contact_raw"]')  # the read action needs limit_switch
    with pytest.raises(BuildFailed) as raised:
        build(path, target="sim", board_id=BOARD)
    assert any("digital.in:limit_switch" in p.where for p in raised.value.problems)


def test_an_extension_primitive_no_slice_has_built_yet_cannot_be_required(tmp_path):
    path = agent(tmp_path)
    text = path.read_text(encoding="utf-8").replace('"digital.in"', '"i2c" = {}\n"digital.in"', 1)
    path.write_text(text, encoding="utf-8")
    with pytest.raises(AgentManifestError, match=r"\['i2c'\] cannot be required"):
        load_agent_manifest(path)


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"facts": 'door_closed = { pin = "button_boot" }'}, "button_boot"),
        (
            {"facts": 'door_closed = { pin = "limit_switch" }', "pins": '["door_contact_raw"]'},
            "does not declare",
        ),
        (
            {"facts": 'ghost = { pin = "door_contact_raw" }'},
            "no gate of the agent evaluates 'ghost'",
        ),
        ({"facts": 'door_closed = { pin = "door_contact_raw", equals = 1 }'}, "equals"),
        ({"facts": 'door_closed = { pin = "door_contact_raw", gte = 1 }'}, "string `pin`"),
        ({"facts": 'door_closed = "door_contact_raw"'}, "string `pin`"),
        ({"inputs": "button_boot = true"}, "button_boot"),
        ({"inputs": "door_contact_raw = 1"}, "not a logic level"),
        (
            {
                "gate": LEVEL_GATE.replace("{fail}", "closed").replace(
                    "door_closed: true", "door_closed: { lte: low }"
                )
            },
            "a digital.in level is a bool fact",
        ),
    ],
    ids=[
        "undeclared-pin",
        "pin-not-in-requires",
        "no-such-criterion",
        "equals-not-bool",
        "unknown-key",
        "not-a-table",
        "input-undeclared",
        "input-not-bool",
        "level-criterion",
    ],
)
def test_a_binding_the_board_or_the_gate_cannot_serve_is_refused_at_build(tmp_path, kwargs, match):
    path = agent(tmp_path, **kwargs)
    with pytest.raises((BuildFailed, AgentManifestError)) as raised:
        build(path, target="sim", board_id=BOARD)
    problems = getattr(raised.value, "problems", [raised.value])
    assert any(match in f"{p.where} {p.why}" for p in problems), [p.why for p in problems]


def test_one_criterion_has_one_source(tmp_path):
    path = agent(tmp_path)
    path.write_text(
        path.read_text(encoding="utf-8")
        + '\n[sim.sensor_facts]\ndoor_closed = { sensor = "door_contact" }\n',
        encoding="utf-8",
    )
    with pytest.raises(BuildFailed) as raised:
        build(path, target="sim", board_id=BOARD)
    assert any("one criterion, one source" in p.why for p in raised.value.problems)


def test_a_fixed_fact_for_a_criterion_a_pin_decides_is_refused(tmp_path):
    path = agent(tmp_path)
    with pytest.raises(AgentManifestError, match="would never be used"):
        SimSession.load(path, board_id=BOARD, facts={"door_closed": True})


# --- the level enters the gate as a fact: ALLOW and BLOCK both ways --------------------------


async def test_a_closed_door_allows_and_an_open_one_blocks(tmp_path):
    session = load(tmp_path)
    session.set_digital_in("door_contact_raw", False)
    blocked = await session.handle("đóng cổng")
    assert not blocked.allowed and blocked.result.gate.reason == "condition_not_met"
    assert session.hal.pin("gate_relay").never_pulsed()

    session.set_digital_in("door_contact_raw", True)
    allowed = await session.handle("đóng cổng")
    assert allowed.allowed and session.hal.pin("gate_relay").commands == [("on", 0)]


async def test_equals_false_reads_the_line_low_as_the_fact(tmp_path):
    session = load(tmp_path, facts='door_closed = { pin = "door_contact_raw", equals = false }')
    assert not (await session.handle("đóng cổng")).allowed  # high: the fact is False
    session.set_digital_in("door_contact_raw", False)
    assert (await session.handle("đóng cổng")).allowed


async def test_the_fact_carries_its_source_and_read_marks_into_the_trace(tmp_path):
    clock = FakeClock()
    session = load(tmp_path, clock=clock)
    clock.advance(40)
    await session.handle("đóng cổng")
    facts = session.events.of_type("gate_facts")[-1]["door_closed"]
    assert facts["value"] is True and facts["source"] == DIGITAL_IN_SOURCE
    assert facts["eval_offset_ms"] - facts["read_offset_ms"] == facts["age_ms"] == 0
    assert facts["read_offset_ms"] == 40
    read = list(session.events.of_type("digital_in"))
    assert read == [{"pin": "door_contact_raw", "value": True, "use": "fact"}]


TWO_FACTS_GATE = SHUT_GATE.replace("{fail}", "closed").replace(
    "allow_when:",
    "  not_open:\n    type: bool\n    instructions: the door contact does not read open\nallow_when:\n  not_open: true",
)


async def test_two_facts_of_one_pin_come_from_one_read(tmp_path):
    session = load(
        tmp_path,
        gate=TWO_FACTS_GATE,
        facts='door_closed = { pin = "door_contact_raw" }\nnot_open = { pin = "door_contact_raw" }',
    )
    assert (await session.handle("đóng cổng")).allowed
    assert len(session.events.of_type("digital_in")) == 1
    facts = session.events.of_type("gate_facts")[-1]
    assert facts["door_closed"]["read_offset_ms"] == facts["not_open"]["read_offset_ms"]


async def test_set_fact_refuses_a_criterion_a_pin_decides(tmp_path):
    session = load(tmp_path)
    with pytest.raises(NeuroEdgeError, match="read from input pin 'door_contact_raw'") as raised:
        session.set_fact("door_closed", True)
    assert ":input door_contact_raw" in raised.value.how


# --- freshness: DIGITAL_IN_MAX_AGE_MS, in code, never a gate key -------------------------------


def engine_for(clock, fail="closed"):
    gate = resolve_gate_document(yaml.safe_load(SHUT_GATE.replace("{fail}", fail)), "test")
    return ActionContractEngine({"shut": gate}, clock=clock, events=EventLog(clock))


async def verdict_of(fact, *, advance=0.0, fail="closed"):
    clock = FakeClock(1000.0)
    engine = engine_for(clock, fail)
    if isinstance(fact, Fact) and fact.read_ms is not None:
        fact = Fact(fact.value, source=fact.source, read_ms=1000.0 + fact.read_ms)
    clock.advance(advance)
    return await engine.evaluate("shut", {"door_closed": fact}), engine


def level(read_ms=0.0, value=True, source=DIGITAL_IN_SOURCE):
    return Fact(value, source=source, read_ms=read_ms)


async def test_a_level_exactly_as_old_as_the_ceiling_passes_and_one_ms_older_does_not():
    assert DIGITAL_IN_MAX_AGE_MS == 100
    on_time, engine = await verdict_of(level(0.0), advance=DIGITAL_IN_MAX_AGE_MS)
    assert on_time.verdict is GateVerdict.ALLOW
    entry = engine.events.of_type("gate_facts")[-1]["door_closed"]
    assert entry["age_ms"] == 100
    stale, _ = await verdict_of(level(0.0), advance=DIGITAL_IN_MAX_AGE_MS + 1)
    assert stale.verdict is GateVerdict.BLOCK and stale.reason is Reason.CRITERION_UNAVAILABLE


async def test_a_level_read_after_the_verdict_is_unavailable():
    result, _ = await verdict_of(level(50.0), advance=0.0)  # read_ms later than the evaluation
    assert result.verdict is GateVerdict.BLOCK and result.reason is Reason.CRITERION_UNAVAILABLE


@pytest.mark.parametrize(
    "read_ms", [None, float("nan"), float("inf"), "now", True, [1.0]], ids=repr
)
async def test_a_level_without_a_usable_read_mark_is_unavailable(read_ms):
    clock = FakeClock()
    engine = engine_for(clock)
    result = await engine.evaluate(
        "shut", {"door_closed": Fact(True, source=DIGITAL_IN_SOURCE, read_ms=read_ms)}
    )
    assert result.verdict is GateVerdict.BLOCK and result.reason is Reason.CRITERION_UNAVAILABLE


async def test_a_source_cannot_state_the_age_of_its_own_level():
    clock = FakeClock()
    engine = engine_for(clock)
    fact = Fact(True, source=DIGITAL_IN_SOURCE, age_ms=0)  # claims fresh, carries no mark
    result = await engine.evaluate("shut", {"door_closed": fact})
    assert result.reason is Reason.CRITERION_UNAVAILABLE


async def test_a_plain_bool_fact_has_no_age_and_the_canonical_path_is_untouched():
    clock = FakeClock()
    engine = engine_for(clock)
    result = await engine.evaluate("shut", {"door_closed": True})
    assert result.verdict is GateVerdict.ALLOW
    entry = engine.events.of_type("gate_facts")[-1]["door_closed"]
    assert set(entry) == {"value", "confidence", "source"}


async def test_a_stale_level_in_a_session_blocks_criterion_unavailable(tmp_path):
    clock = FakeClock()
    session = load(tmp_path, clock=clock)
    gather = session.gate_facts

    def slow(recognition):
        facts = gather(recognition)
        clock.advance(DIGITAL_IN_MAX_AGE_MS + 1)  # whatever took the time between read and verdict
        return facts

    session.gate_facts = slow
    turn = await session.handle("đóng cổng")
    assert not turn.allowed and turn.result.gate.reason == "criterion_unavailable"
    assert session.hal.pin("gate_relay").never_pulsed()


# --- a read that fails is BLOCK criterion_unavailable, never ALLOW --------------------------------


@pytest.mark.parametrize("fail", ["closed", "open"])
async def test_an_input_nobody_set_blocks_criterion_unavailable(tmp_path, fail):
    gate = SHUT_GATE.replace("{fail}", fail)
    session = load(tmp_path, gate=gate)
    del session.hal._levels["door_contact_raw"]
    turn = await session.handle("đóng cổng")
    assert not turn.allowed
    assert turn.result.gate.reason == "criterion_unavailable"
    assert session.hal.pin("gate_relay").never_pulsed()
    facts = session.events.of_type("gate_facts")[-1]["door_closed"]
    assert facts["value"] is None and facts["source"] == DIGITAL_IN_SOURCE
    assert "reason" in session.events.of_type("digital_in")[-1]


@pytest.mark.parametrize("fail", ["closed", "open"])
@pytest.mark.parametrize(
    "error",
    [
        PerceptionUnavailableError(where="w", why="chip gone", how="h"),
        BoardCapabilityError(where="w", why="refused", how="h"),
        OSError(5, "I/O error"),
    ],
    ids=["perception", "capability", "oserror"],
)
async def test_any_failed_read_blocks_even_a_gate_that_fails_open(tmp_path, fail, error):
    session = load(tmp_path, gate=SHUT_GATE.replace("{fail}", fail))

    def broken(pin, called_from="<unknown>", use=None):
        raise error

    session.hal.digital_reading = broken
    turn = await session.handle("đóng cổng")
    assert not turn.allowed and turn.result.gate.reason == "criterion_unavailable"
    assert session.hal.pin("gate_relay").never_pulsed()


async def test_a_gate_that_fails_open_still_excuses_what_it_always_did(tmp_path):
    """The fail-closed rule above is for lost inputs only: an unrelated degraded source still opens."""
    from neuroedge.engine.decision_tree import compile_tree, known_failure

    gate = resolve_gate_document(yaml.safe_load(SHUT_GATE.replace("{fail}", "open")), "test")
    tree = compile_tree(gate)
    assert known_failure(tree, {}) is None  # no fact at all: what open excuses
    lost = {"door_closed": Fact(None, source=DIGITAL_IN_SOURCE)}
    assert known_failure(tree, lost) == (Reason.CRITERION_UNAVAILABLE, "door_closed")


# --- replay recomputes from the recorded readings --------------------------------------------------


async def recorded_session(tmp_path, steps):
    path = agent(tmp_path)
    recorder = TraceRecorder()
    session = SimSession.load(path, board_id=BOARD, events=recorder)
    for text, pin, value in steps:
        if pin is not None:
            session.set_digital_in(pin, value)
        await session.handle(text)
    out = tmp_path / "trace.json"
    session.write_trace(out)
    return path, out, session


async def test_replay_reproduces_the_verdicts_and_the_pin_commands(tmp_path):
    path, out, session = await recorded_session(
        tmp_path,
        [
            ("đóng cổng", "door_contact_raw", False),
            ("đóng cổng", "door_contact_raw", True),
            ("đóng cổng", None, None),
        ],
    )
    result = await TracePlayer(out, agent=path, board_id=BOARD).replay()
    assert result.recorded_verdicts == ["BLOCK", "ALLOW", "ALLOW"]
    assert result.verdicts == result.recorded_verdicts
    assert not result.divergences and not result.warnings
    assert result.pin("gate_relay").commands == session.hal.pin("gate_relay").commands
    replayed = [e["data"] for e in result.replayed["events"] if e["type"] == "gate_facts"]
    assert all(f["door_closed"]["source"] == DIGITAL_IN_SOURCE for f in replayed)
    assert all(f["door_closed"]["age_ms"] >= 0 for f in replayed)


async def test_replay_of_a_failed_read_blocks_again(tmp_path):
    path = agent(tmp_path)
    recorder = TraceRecorder()
    session = SimSession.load(path, board_id=BOARD, events=recorder)
    del session.hal._levels["door_contact_raw"]
    await session.handle("đóng cổng")
    out = tmp_path / "trace.json"
    session.write_trace(out)
    result = await TracePlayer(out, agent=path, board_id=BOARD).replay()
    assert result.recorded_verdicts == result.verdicts == ["BLOCK"]
    assert result.gate_results[0]["reason"] == "criterion_unavailable"


async def test_replay_does_not_trust_an_age_the_trace_cannot_account_for(tmp_path):
    path, out, _ = await recorded_session(tmp_path, [("đóng cổng", None, None)])
    trace = json.loads(out.read_text(encoding="utf-8"))
    for event in trace["events"]:
        if event["type"] == "gate_facts":
            event["data"]["door_closed"]["age_ms"] = 7  # not eval - read
    out.write_text(json.dumps(trace), encoding="utf-8")
    result = await TracePlayer(out, agent=path, board_id=BOARD).replay()
    assert result.recorded_verdicts == ["ALLOW"] and result.verdicts == ["BLOCK"]
    assert any("door_closed" in warning for warning in result.warnings)


async def test_replay_with_the_network_down_keeps_the_devices_own_levels(tmp_path):
    path, out, _ = await recorded_session(tmp_path, [("đóng cổng", None, None)])
    result = await TracePlayer(out, agent=path, board_id=BOARD, network="offline").replay()
    assert result.verdicts == ["ALLOW"]


async def test_a_level_read_in_an_action_body_is_recorded_and_replayed(tmp_path):
    path = agent(tmp_path)
    recorder = TraceRecorder()
    session = SimSession.load(path, board_id=BOARD, events=recorder)
    session.set_digital_in("limit_switch", True)
    await session.handle("đọc công tắc")
    session.set_digital_in("limit_switch", False)
    await session.handle("đọc công tắc")
    reads = [
        e["data"] for e in recorder.events if e["type"] == "digital_in" and "use" not in e["data"]
    ]
    assert reads == [
        {"pin": "limit_switch", "value": True},
        {"pin": "limit_switch", "value": False},
    ]
    out = tmp_path / "trace.json"
    session.write_trace(out)
    result = await TracePlayer(out, agent=path, board_id=BOARD).replay()
    assert result.pin("gate_relay").commands == [("on", 0), ("off", 0)]
    assert result.pin("gate_relay").commands == session.hal.pin("gate_relay").commands


async def test_replay_never_reads_further_than_the_trace_recorded():
    events = EventLog()
    hal = SimHAL(load_board_by_id(BOARD), events=events)
    hal.script_digital_in("limit_switch", [True, None])
    assert hal.digital_in("limit_switch") is True
    with pytest.raises(PerceptionUnavailableError):  # recorded as a failed read
        hal.digital_in("limit_switch")
    with pytest.raises(PerceptionUnavailableError):  # past the end: not the last level again
        hal.digital_in("limit_switch")


def test_digital_input_outside_an_action_is_a_contract_violation():
    from neuroedge.errors import ActionContractViolation

    with pytest.raises(ActionContractViolation, match="no HAL is active"):
        digital.input("limit_switch").level()


# --- the REPL and the page set a level -----------------------------------------------------------


def test_the_repl_sets_and_shows_input_levels(tmp_path):
    from typer.testing import CliRunner

    from neuroedge.cli.main import app

    path = agent(tmp_path)
    stdin = (
        ":inputs\n:input door_contact_raw low\nđóng cổng\n:input door_contact_raw 1\nđóng cổng\n"
        ":input door_contact_raw maybe\n:input button_boot 1\n:inputs\nexit\n"
    )
    result = CliRunner().invoke(app, ["run", "--agent", str(path), "--board", BOARD], input=stdin)
    assert result.exit_code == 0, result.output
    out = result.output
    assert "Simulated input lines" in out and "door_contact_raw" in out
    assert "door_contact_raw = low" in out and "door_contact_raw = high" in out
    assert "✗ BLOCK" in out and "✓ ALLOW" in out
    assert "'maybe' is not a level" in out or "maybe is not a level" in out
    assert "button_boot" in out  # the refusal names the pin


def test_the_page_sets_a_level_with_the_same_command(tmp_path):
    from neuroedge.sim.ui import SessionServer

    session = load(tmp_path)
    server = SessionServer(session, port=0)
    try:
        assert server.command(":input door_contact_raw false") == {
            "ok": True,
            "input": "door_contact_raw",
        }
        assert session.hal.digital_in_values()["door_contact_raw"] is False
        assert server.command(":input door_contact_raw high")["ok"] is True
        assert session.hal.digital_in_values()["door_contact_raw"] is True
        assert server.command(":input door_contact_raw maybe")["ok"] is False
        assert server.command(":input button_boot 1")["ok"] is False
        sets = [e["data"] for e in session.events.events if e["type"] == "digital_in_set"]
        assert sets == [
            {"pin": "door_contact_raw", "value": False},
            {"pin": "door_contact_raw", "value": True},
        ]
    finally:
        server.httpd.server_close()


def test_the_page_shows_the_declared_input_lines():
    from neuroedge.viz import board_info

    assert board_info(BOARD)["inputs"] == ["door_contact_raw", "limit_switch"]
    assert board_info("sim-default")["inputs"] == []


def test_the_page_script_reads_the_input_level_events():
    from neuroedge.viz import page

    html = page(title="t", meta={}, events=[], board=board_info_for_page())
    assert "digital_in_set" in html and '"inputs"' in html


def board_info_for_page():
    from neuroedge.viz import board_info

    return board_info(BOARD)
