"""
The conversation state machine's compliance corpus (TSK-S3-10, docs/spec/voice_fsm.md §9).

An implementation is *compliant* when every case of `fixtures/compliance/voice/`
gives the events `expected_results.yaml` records for it. The corpus is language
independent: a case is JSON data — the agent, the §6 parameters, the world the
case runs in and the input events of §8 at virtual offsets — and the answer is a
list of observable events. The Python implementation (TSK-S3-11) runs it here;
the C/C++ one (TSK-S5-03) must pass the very same files.

A case (one `*.json` file):

    {
      "scenario": "V1",                        # §9 scenario, or "table" (rows only)
      "covers":   ["T01", "T02", …],           # §4 rows the case exercises
      "agent":    "voice-door",                # a directory of fixtures/agents/
      "params":   { "think_timeout_ms": 5000 },# §6, over the defaults of §9.1
      "world":    { "system_two": true },      # facts, unset_facts, sensors, system_two, facts_source
      "inputs":   [ { "offset_ms": 0, "type": "wake_word_detected", "data": {…} }, … ],
      "until_ms": 40000                        # run the clock to here, deadlines included
    }

The answer, under the file's name in `expected_results.yaml`: `proves` (one
sentence) and `events` — every observable event, in order, each with its
`offset_ms`. Which events are observable and which fields are compared is
`OBSERVED` below (§9.1 of the spec says the same in prose).
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ..errors import NeuroEdgeError
from ..paths import fixtures_dir
from ..perception import TRIGGERS, VirtualClock, VoiceParams, VoiceSession
from ..perception.voice_session import FACTS_SOURCES
from ..trace import validate_trace

EXPECTED_FILE = "expected_results.yaml"
SCENARIOS = ("V1", "V2", "V3", "V4", "V5", "V6", "V7")
CASE_KEYS = {"description", "scenario", "covers", "agent", "params", "world", "inputs", "until_ms"}
WORLD_KEYS = {"facts", "unset_facts", "sensors", "system_two", "facts_source"}

# §4, in table order: (from, to, trigger) — None where the row stays in its state
# and records no `voice_state_changed`.
ROWS: dict[str, tuple[str, str, str] | None] = {
    "T01": ("IDLE", "LISTENING", "wake_word|speech_start"),
    "T02": None,  # LISTENING audio_in_vad_end: start the end-of-turn count
    "T03": None,  # LISTENING audio_in_vad_start while counting: cancel it
    "T04": ("LISTENING", "THINKING", "turn_end"),
    "T05": ("LISTENING", "IDLE", "listen_timeout"),
    "T06": ("THINKING", "IDLE", "transcript_empty"),
    "T07": ("THINKING", "SPEAKING", "reply_start"),
    "T08": ("THINKING", "IDLE", "reply_empty"),
    "T09": None,  # THINKING think_timeout / system_two_unavailable: the offline line
    "T10": ("THINKING", "BARGE_IN", "barge_in"),
    "T11": ("SPEAKING", "LISTENING", "ask_asked"),
    "T12": ("SPEAKING", "IDLE", "reply_end"),
    "T13": ("SPEAKING", "BARGE_IN", "barge_in"),
    "T14": ("BARGE_IN", "LISTENING", "barge_in"),
}

# Input events a case may carry, with the `data` keys each must have.
INPUTS: dict[str, tuple[str, ...]] = {
    "wake_word_detected": ("word", "score"),
    "audio_in_vad_start": ("energy_db",),
    "audio_in_vad_end": (),
    "stt_result": ("turn", "text"),
    "system_two_reply": ("turn",),  # text?, tool_calls? — the scripted provider's answer
    "system_two_unavailable": ("task", "reason"),
    "tts_stream_end": ("reason",),  # "done" or "error"; "barge_in" is an output
    "reuse_token": ("pin",),  # drive the pin again with a cancelled command's token
}

# Observable events: `strict` fields always compared (absent = null); `optional`
# fields compared only when the expectation states them.
OBSERVED: dict[str, dict[str, tuple[str, ...]]] = {
    "voice_state_changed": {"strict": ("from", "to", "trigger", "turn"), "optional": ()},
    "action_requested": {"strict": ("action",), "optional": ()},
    "gate_evaluation_result": {"strict": ("verdict", "reason", "action"), "optional": ()},
    "actuator_command": {"strict": ("pin", "operation", "duration_ms"), "optional": ()},
    "actuator_aborted": {"strict": ("pin", "reason"), "optional": ()},
    "actuator_command_rejected": {"strict": ("pin", "reason"), "optional": ()},
    "tts_stream_start": {"strict": (), "optional": ("text",)},
    "tts_stream_end": {"strict": ("reason", "duration_ms"), "optional": ()},
    "tool_confirm_requested": {"strict": ("id",), "optional": ()},
    "tool_confirmed": {"strict": ("id", "source"), "optional": ()},
    "tool_confirm_declined": {"strict": ("id", "source"), "optional": ()},
    "tool_confirm_expired": {"strict": ("id",), "optional": ()},
    "voice_reprompt": {"strict": ("turn", "count"), "optional": ()},
    "voice_late_result_dropped": {"strict": ("turn", "input"), "optional": ()},
}


def corpus_dir() -> Path:
    return fixtures_dir() / "compliance" / "voice"


def _error(where: Path | str, why: str, how: str) -> NeuroEdgeError:
    return NeuroEdgeError(where=str(where), why=why, how=how)


@dataclass(frozen=True)
class VoiceCase:
    path: Path
    scenario: str
    covers: tuple[str, ...]
    agent: str
    params: VoiceParams
    world: dict[str, Any]
    inputs: tuple[dict[str, Any], ...]
    until_ms: int
    param_values: dict[str, Any] = field(default_factory=dict)

    @property
    def name(self) -> str:
        return self.path.name


def load_case(path: Path) -> VoiceCase:
    """One corpus file; `NeuroEdgeError` when it is not a well-formed case."""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise _error(path, f"not JSON: {exc}", "fix the file") from exc
    if not isinstance(document, dict):
        raise _error(path, "a case is a JSON object", "see neuroedge.testing.voice_corpus")
    unknown = set(document) - CASE_KEYS
    if unknown:
        raise _error(path, f"unknown keys {sorted(unknown)}", f"a case has {sorted(CASE_KEYS)}")
    scenario = document.get("scenario")
    if scenario not in (*SCENARIOS, "table"):
        raise _error(f"{path} -> scenario", f"{scenario!r}", f"use one of {[*SCENARIOS, 'table']}")
    covers = document.get("covers") or []
    if not covers or set(covers) - set(ROWS):
        raise _error(f"{path} -> covers", f"{covers!r}", f"list rows of §4: {list(ROWS)}")
    agent = document.get("agent")
    if (
        not isinstance(agent, str)
        or not (fixtures_dir() / "agents" / agent / "agent.toml").is_file()
    ):
        raise _error(f"{path} -> agent", f"{agent!r} is not an agent of fixtures/agents/", "fix")
    param_values = dict(document.get("params") or {})
    try:
        params = VoiceParams.from_mapping(param_values)
    except (TypeError, ValueError) as exc:
        raise _error(f"{path} -> params", str(exc), "use the parameters of §6") from exc
    world = dict(document.get("world") or {})
    if set(world) - WORLD_KEYS:
        raise _error(f"{path} -> world", f"unknown keys {sorted(set(world) - WORLD_KEYS)}", "fix")
    if world.get("facts_source", "local_grammar") not in FACTS_SOURCES:
        raise _error(f"{path} -> world.facts_source", repr(world["facts_source"]), "fix")
    inputs = document.get("inputs") or []
    last = 0
    for i, event in enumerate(inputs):
        where = f"{path} -> inputs[{i}]"
        if not isinstance(event, dict) or set(event) != {"offset_ms", "type", "data"}:
            raise _error(where, f"{event!r}", "an input is {offset_ms, type, data}")
        offset, kind, data = event["offset_ms"], event["type"], event["data"]
        if not isinstance(offset, int) or offset < last:
            raise _error(where, f"offset_ms {offset!r} before {last}", "inputs are in time order")
        last = offset
        if kind not in INPUTS:
            raise _error(where, f"{kind!r} is not an input", f"use one of {list(INPUTS)}")
        missing = [key for key in INPUTS[kind] if key not in data]
        if missing:
            raise _error(where, f"{kind} needs {missing}", "add them to data")
        if kind == "tts_stream_end" and data["reason"] not in ("done", "error"):
            raise _error(where, "only done/error end a stream as input", "barge_in is an output")
        if kind == "system_two_reply" and not world.get("system_two"):
            raise _error(where, "a System 2 reply in a world without one", "set world.system_two")
    until = document.get("until_ms")
    if not isinstance(until, int) or until < last:
        raise _error(f"{path} -> until_ms", f"{until!r}", "an integer at or after the last input")
    return VoiceCase(
        path=path,
        scenario=scenario,
        covers=tuple(covers),
        agent=agent,
        params=params,
        world=world,
        inputs=tuple(inputs),
        until_ms=until,
        param_values=param_values,
    )


def load_expected(root: Path | None = None) -> dict[str, dict[str, Any]]:
    root = root or corpus_dir()
    document = yaml.safe_load((root / EXPECTED_FILE).read_text(encoding="utf-8")) or {}
    if not isinstance(document, dict):
        raise _error(root / EXPECTED_FILE, "must map case files to answers", "fix")
    expected: dict[str, dict[str, Any]] = {}
    for name, entry in document.items():
        where = f"{EXPECTED_FILE} -> {name}"
        if not isinstance(entry, dict) or set(entry) != {"proves", "events"}:
            raise _error(where, "an answer is {proves, events}", "fix the entry")
        for i, event in enumerate(entry["events"] or []):
            if (
                not isinstance(event, dict)
                or set(event) != {"offset_ms", "type", "data"}
                or event["type"] not in OBSERVED
            ):
                raise _error(
                    f"{where} -> events[{i}]",
                    f"{event!r}",
                    f"an event is {{offset_ms, type, data}} of an observable type {list(OBSERVED)}",
                )
            spec = OBSERVED[event["type"]]
            extra = set(event["data"] or {}) - set(spec["strict"]) - set(spec["optional"])
            if extra:
                raise _error(
                    f"{where} -> events[{i}]",
                    f"fields {sorted(extra)} are not compared",
                    "drop them",
                )
        expected[name] = entry
    return expected


def case_files(root: Path | None = None) -> list[Path]:
    return sorted((root or corpus_dir()).glob("*.json"))


def closure_problems(root: Path | None = None) -> list[str]:
    """Every file has an answer and every answer a file (CONTRIBUTING §3)."""
    present = {path.name for path in case_files(root)}
    documented = set(load_expected(root))
    problems = [
        f"{n}: no entry in {EXPECTED_FILE} — say what it proves"
        for n in sorted(present - documented)
    ]
    problems += [
        f"{n}: an entry in {EXPECTED_FILE} with no file" for n in sorted(documented - present)
    ]
    return problems


def observe(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The observable part of an event log, in the answer's shape."""
    out = []
    for event in events:
        kind, data = event["type"], event["data"]
        if kind not in OBSERVED:
            continue
        if kind == "tts_stream_end" and data.get("reason") != "barge_in":
            continue  # done / error are inputs
        spec = OBSERVED[kind]
        keep = {k: data.get(k) for k in spec["strict"]}
        keep.update({k: data[k] for k in spec["optional"] if k in data})
        out.append({"offset_ms": event["offset_ms"], "type": kind, "data": keep})
    return out


def compare(expected: list[dict[str, Any]], observed: list[dict[str, Any]]) -> list[str]:
    differences = []
    for i in range(max(len(expected), len(observed))):
        want = expected[i] if i < len(expected) else None
        got = observed[i] if i < len(observed) else None
        if want is None or got is None:
            differences.append(f"events[{i}]: expected {want}, got {got}")
            continue
        spec = OBSERVED[want["type"]]
        data = want["data"] or {}
        wanted = {k: data.get(k) for k in spec["strict"]}
        wanted.update({k: data[k] for k in spec["optional"] if k in data})
        actual = {k: got["data"].get(k) for k in wanted}
        if (want["offset_ms"], want["type"], wanted) != (got["offset_ms"], got["type"], actual):
            differences.append(f"events[{i}]: expected {want}, got {got}")
    return differences


def transitions(events: list[dict[str, Any]]) -> set[str]:
    """The §4 rows an answer shows (rows that record a state change)."""
    rows = set()
    for event in events:
        if event["type"] != "voice_state_changed":
            continue
        data = event["data"]
        for row, shape in ROWS.items():
            if shape is None:
                continue
            was, now, triggers = shape
            if (data["from"], data["to"]) == (was, now) and data["trigger"] in triggers.split("|"):
                rows.add(row)
    return rows


def coverage_problems(root: Path | None = None) -> list[str]:
    """§9: every scenario and every row of §4 has a case, and `covers` tells the truth."""
    expected = load_expected(root)
    problems: list[str] = []
    rows: set[str] = set()
    scenarios: set[str] = set()
    triggers: set[str] = set()
    for path in case_files(root):
        case = load_case(path)
        scenarios.add(case.scenario)
        rows |= set(case.covers)
        answer = expected.get(case.name)
        if answer is None:
            continue
        events = answer["events"] or []
        shown = transitions(events)
        declared = {r for r in case.covers if ROWS[r] is not None}
        if shown != declared:
            problems.append(
                f"{case.name}: covers {sorted(declared)} but its answer shows {sorted(shown)}"
            )
        triggers |= {e["data"]["trigger"] for e in events if e["type"] == "voice_state_changed"}
    problems += [f"no case for scenario {s}" for s in SCENARIOS if s not in scenarios]
    problems += [f"no case covers row {r} of §4" for r in ROWS if r not in rows]
    problems += [f"no case shows trigger {t!r}" for t in TRIGGERS if t not in triggers]
    return problems


def _reuse_token(voice: VoiceSession, pin: str) -> None:
    """
    V1: drive `pin` again with the token of the last command barge-in cancelled on
    it. A corpus input, not a device one: it calls the HAL directly, which only a
    test may do. The ledger must refuse it (`actuator_command_rejected`).
    """
    aborted = [c for c in voice.fsm.aborted if c.pin == pin]
    if not aborted:
        raise ValueError(f"reuse_token: no cancelled command on {pin!r} to reuse")
    command = aborted[-1]
    try:
        voice.hal.digital_out(
            pin,
            command.operation,
            command.duration_ms,
            signature=command.token,
            called_from="reuse_token",
        )
    except NeuroEdgeError:
        return
    raise AssertionError(f"the token of a command barge-in cancelled drove {pin!r} again")


async def execute(case: VoiceCase) -> VoiceSession:
    """The case through a fresh `VoiceSession`, input by input, in virtual time."""
    world = case.world
    voice = VoiceSession.load(
        fixtures_dir() / "agents" / case.agent / "agent.toml",
        params=case.params,
        clock=VirtualClock(),
        facts=world.get("facts") or {},
        unset_facts=tuple(world.get("unset_facts") or ()),
        sensors=world.get("sensors") or {},
        system_two=bool(world.get("system_two")),
        facts_source=world.get("facts_source", "local_grammar"),
    )
    for event in case.inputs:
        await voice.advance(event["offset_ms"])
        if event["type"] == "reuse_token":
            voice.events.emit(event["type"], dict(event["data"]))
            _reuse_token(voice, str(event["data"]["pin"]))
        else:
            await voice.feed(event["type"], event["data"])
    await voice.advance(case.until_ms, inclusive=True)
    validate_trace(voice.session.events.to_trace(), label=f"voice case {case.name}")
    return voice


def run_case(case: VoiceCase, expected: Mapping[str, Any]) -> list[str]:
    """Differences between the case's answer and what the implementation did."""
    voice = asyncio.run(execute(case))
    return compare(list(expected["events"] or []), observe(voice.events.events))
