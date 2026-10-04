"""
TSK-I6-06 (Q-63) — the public Python surface: `neuroedge.__all__`, pinned.

`docs/spec/python_api.md` says that what is public is `neuroedge.__all__` and what SemVer
promises about it. This file is the other half: a name added to or removed from `__all__`
turns CI red here, so a surface change is always a decision, never a side effect. It also
runs the exit criterion — a project outside this repository, using only `import neuroedge`,
builds a HAL, loads a gate, calls `dispatch` and serves MCP — as that project would.
"""

from __future__ import annotations

import ast
import inspect
import json
import re
import subprocess
import sys
import textwrap
from pathlib import Path

import anyio
import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

import neuroedge
from neuroedge.errors import BoardCapabilityError, NeuroEdgeError, ToolCallError
from neuroedge.hal import HardwareAbstractionLayer
from neuroedge.hal.linux import LinuxHAL, TypedLinuxHAL
from neuroedge.hal.sim import SimHAL

TIMEOUT = 60.0

# The whole public surface. Changing it is a SemVer decision (docs/spec/python_api.md §3):
# edit this list, the spec's table and the CHANGELOG entry in the same PR.
PUBLIC = [
    "ActionContractEngine",
    "ActionContractViolation",
    "ActionResult",
    "AgentManifestError",
    "BoardCapabilityError",
    "BoardProfile",
    "BuildFailed",
    "Conversation",
    "Fact",
    "Gate",
    "GateError",
    "GateInheritanceError",
    "GateNotFoundError",
    "GateRegistry",
    "GateResult",
    "GateSchemaError",
    "GateVerdict",
    "HardwareAbstractionLayer",
    "LinuxHAL",
    "NeuroEdgeError",
    "PerceptionUnavailableError",
    "PinAssertion",
    "Reason",
    "ReplayError",
    "ResolvedGate",
    "SafetyRegressionError",
    "SimHAL",
    "SimSession",
    "SystemOne",
    "SystemTwo",
    "TokenReplayError",
    "ToolCall",
    "ToolCallError",
    "ToolResult",
    "ToolSet",
    "TraceRecorder",
    "TraceValidationError",
    "TreeResult",
    "Turn",
    "VerificationError",
    "__version__",
    "action",
    "compile_tree",
    "digital",
    "dispatch",
    "load_board_by_id",
    "load_trace",
    "replay",
    "resolve_gate_file",
    "resolve_gate_uri",
    "scenario",
    "serve_mcp",
    "spec_of",
    "validate_trace",
    "walk",
]


# --- the pin ---------------------------------------------------------------------------------------


def test_all_is_exactly_the_public_surface():
    assert sorted(neuroedge.__all__) == PUBLIC


def test_all_has_no_duplicates_and_every_name_resolves():
    assert len(set(neuroedge.__all__)) == len(neuroedge.__all__)
    assert [name for name in neuroedge.__all__ if not hasattr(neuroedge, name)] == []


def test_a_star_import_brings_exactly_the_public_names():
    scope: dict = {}
    exec("from neuroedge import *", scope)
    assert sorted(set(scope) - {"__builtins__"}) == PUBLIC


def test_every_public_name_is_described_in_the_spec(root):
    spec = (root / "docs" / "spec" / "python_api.md").read_text(encoding="utf-8")
    described = set(re.findall(r"`([A-Za-z_][A-Za-z0-9_]*)`", spec))
    assert sorted(set(PUBLIC) - described) == []


def test_every_error_class_of_the_package_is_public():
    from neuroedge import errors

    classes = {
        name
        for name, value in vars(errors).items()
        if inspect.isclass(value) and issubclass(value, NeuroEdgeError)
    }
    assert sorted(classes - set(neuroedge.__all__)) == []


# --- the base HAL declares what the HALs implement -------------------------------------------------

AUDIO_METHODS = (
    "audio_in",
    "audio_out",
    "audio_file",
    "audio_source",
    "audio_sink",
    "speaker",
)


def _shape(function) -> list[tuple[str, object, object]]:
    return [
        (name, parameter.kind, parameter.default)
        for name, parameter in inspect.signature(function).parameters.items()
    ]


@pytest.mark.parametrize("method", AUDIO_METHODS)
def test_the_base_hal_declares_the_audio_signatures_the_hals_implement(method):
    base = getattr(HardwareAbstractionLayer, method)
    # `sim` implements all six; `linux` the four device and file ones, its typed variant the
    # two text ones. Whoever overrides a method keeps the signature the base declares.
    assert getattr(SimHAL, method) is not base
    for hal in (SimHAL, LinuxHAL, TypedLinuxHAL):
        implemented = getattr(hal, method)
        if implemented is not base:
            assert _shape(implemented) == _shape(base), f"{hal.__name__}.{method}"


@pytest.mark.parametrize("method", AUDIO_METHODS)
def test_a_hal_without_an_audio_primitive_refuses_with_a_three_part_error(method):
    hal = HardwareAbstractionLayer(target="esp32s3")
    arguments = {"audio_out": ("hello",), "audio_file": ("x.wav",)}.get(method, ())
    with pytest.raises(BoardCapabilityError) as excinfo:
        getattr(hal, method)(*arguments, called_from="test")
    assert excinfo.value.code == "NE3001"
    assert "test -> audio." in excinfo.value.where
    assert "esp32s3" in excinfo.value.why and excinfo.value.how


# --- ToolCall reports a bad source with an NE error ------------------------------------------------


def test_an_unknown_tool_call_source_is_an_ne_error_with_three_parts():
    with pytest.raises(ToolCallError) as excinfo:
        neuroedge.ToolCall("light_on", source="internet")
    error = excinfo.value
    assert (error.code, isinstance(error, NeuroEdgeError)) == ("NE1004", True)
    assert "internet" in error.why and "mcp" in error.how
    assert "light_on" in error.where


def test_the_tool_call_error_is_still_a_value_error_for_0_1_callers():
    with pytest.raises(ValueError, match="source"):
        neuroedge.ToolCall("light_on", source="internet")


# --- a base install: no gpiod, no MCP SDK ----------------------------------------------------------


def run_python(code: str, *, cwd: Path) -> subprocess.CompletedProcess[str]:
    """`code` in a fresh interpreter that reads neither the working directory nor PYTHONPATH."""
    return subprocess.run(
        [sys.executable, "-I", "-c", textwrap.dedent(code)],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
    )


def test_import_neuroedge_works_without_gpiod_and_linux_hal_says_how_to_get_it(tmp_path):
    result = run_python(
        """
        import sys
        sys.modules["gpiod"] = None            # `import gpiod` raises ImportError
        import neuroedge
        assert neuroedge.LinuxHAL.__name__ == "LinuxHAL"
        assert sys.modules["gpiod"] is None, "something imported gpiod"
        try:
            neuroedge.LinuxHAL()
        except neuroedge.NeuroEdgeError as error:
            print(error.code, "gpiod" in error.why, "pip install" in error.how)
        """,
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["NE3001", "True", "True"]


def test_import_neuroedge_works_without_the_mcp_sdk_and_serve_mcp_says_how_to_get_it(tmp_path):
    result = run_python(
        """
        import sys
        sys.modules["mcp"] = None
        import neuroedge
        try:
            neuroedge.serve_mcp("agent.toml")
        except neuroedge.NeuroEdgeError as error:
            print("pip install 'neuroedge[mcp]'" in error.how, "MCP" in error.why)
        """,
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["True", "True"]


# --- the exit criterion: an external project, `import neuroedge` only ------------------------------

AGENT_TOML = """
[agent]
name    = "ext-agent"
version = "0.1.0"

[requires]
"digital.out" = { pins = ["door_lock"] }

[gates]
custom_lock = "gates/custom_lock@1.0.0.yaml"

[targets]
supported = ["sim", "linux", "esp32s3"]

[sim.facts]
user_verified = true
"""

COMMANDS_TOML = """
[grammar]
version   = 1
threshold = 0.80

[[command]]
intent   = "unlock"
patterns = ["unlock"]
facts    = { command_recognized = true }
tool     = "operate_hardware"
"""

GATE_YAML = """
schema:  neuroedge.gate/v1
name:    custom_lock
version: 1.0.0

evaluate:
  user_verified:
    type: bool
    instructions: "The user was verified in this session"
  command_recognized:
    type: bool
    instructions: "The command matched the fixed grammar"

allow_when:
  user_verified:      true
  command_recognized: true

on_block:
  action:  deny
  message: "Verify the user first."

budget:
  p95_latency_ms: 150
  fail:           closed
"""

ACTION_PY = """
import neuroedge


@neuroedge.action(name="operate_hardware", requires="digital.out:door_lock", gate="custom_lock")
def operate_hardware(duration_s: int = 5) -> None:
    \"\"\"Pulse the lock for `duration_s` seconds.\"\"\"
    neuroedge.digital.out("door_lock").pulse(seconds=duration_s)
"""

# Builds a HAL, loads a gate, calls dispatch twice, compiles and walks the tree.
DISPATCH_PY = """
import asyncio
import json

import neuroedge as ne


@ne.action(name="operate_hardware", requires="digital.out:door_lock", gate="custom_lock")
def operate_hardware(duration_s: int = 5) -> None:
    ne.digital.out("door_lock").pulse(seconds=duration_s)


events = ne.TraceRecorder()
gate = ne.resolve_gate_file("gates/custom_lock@1.0.0.yaml")
engine = ne.ActionContractEngine(events=events)
engine.register("custom_lock", gate)
hal = ne.SimHAL(events=events)
tools = ne.ToolSet([ne.spec_of(operate_hardware)])


def call(facts):
    conversation = ne.Conversation(engine=engine, hal=hal, facts=facts)
    call = ne.ToolCall("operate_hardware", {"duration_s": 3}, source="test")
    return asyncio.run(ne.dispatch(conversation, tools, call))


allowed = call({"user_verified": True, "command_recognized": True})
blocked = call({"user_verified": False, "command_recognized": True})

tree = ne.compile_tree(gate)
facts = {"user_verified": ne.Fact(False), "command_recognized": ne.Fact(True)}
walked = ne.walk(tree, facts)

try:
    ne.ToolCall("operate_hardware", source="internet")
except ne.NeuroEdgeError as error:
    refused = error.code

print(
    json.dumps(
        {
            "allowed": allowed.status,
            "blocked": blocked.status,
            "failed_criterion": blocked.content()["failed_criterion"],
            "pulses": hal.pin("door_lock").pulses,
            "walk": [str(walked.verdict), walked.failed_criterion],
            "refused": refused,
            "trace_events": len(events.to_trace()["events"]) > 0,
        }
    )
)
"""

SERVE_PY = """
import neuroedge

neuroedge.serve_mcp("agent.toml", trace_out="trace.json")
"""


@pytest.fixture
def project(tmp_path, root):
    """A minimal agent project in a directory outside this repository."""
    assert root not in tmp_path.parents, "the external project must live outside the repo"
    files = {
        "agent.toml": AGENT_TOML,
        "commands.toml": COMMANDS_TOML,
        "gates/custom_lock@1.0.0.yaml": GATE_YAML,
        "actions/operate_hardware.py": ACTION_PY,
        "dispatch.py": DISPATCH_PY,
        "serve.py": SERVE_PY,
    }
    for name, text in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(text).lstrip(), encoding="utf-8")
    return tmp_path


def test_the_external_project_uses_only_the_top_level_package(project):
    for script in ("dispatch.py", "serve.py", "actions/operate_hardware.py"):
        tree = ast.parse((project / script).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            assert not [n for n in names if n.startswith("neuroedge.")], (script, names)
            assert "neuroedge" not in names or isinstance(node, ast.Import), (script, names)


def test_an_external_project_builds_a_hal_loads_a_gate_and_dispatches(project):
    result = subprocess.run(
        [sys.executable, "-I", "dispatch.py"],
        cwd=project,
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "allowed": "ALLOW",
        "blocked": "BLOCK",
        "failed_criterion": "user_verified",
        "pulses": [3000],  # the blocked call moved nothing
        "walk": ["BLOCK", "user_verified"],
        "refused": "NE1004",
        "trace_events": True,
    }


def test_an_external_project_serves_mcp_through_the_gate_and_records_a_hashed_trace(project):
    params = StdioServerParameters(command=sys.executable, args=["-I", "serve.py"], cwd=project)

    async def session():
        with (project / "stderr.txt").open("w", encoding="utf-8") as errlog:
            async with (
                stdio_client(params, errlog=errlog) as (read, write),
                ClientSession(read, write) as client,
            ):
                with anyio.fail_after(TIMEOUT):
                    initialized = await client.initialize()
                    tools = await client.list_tools()
                    called = await client.call_tool("operate_hardware", {"duration_s": 2})
                    refused = await client.call_tool("operate_hardware", {"nope": 1})
        return initialized, tools, called, refused

    initialized, tools, called, refused = anyio.run(session)
    assert initialized.server_info.name == "neuroedge:ext-agent@0.1.0"
    assert [tool.name for tool in tools.tools] == ["operate_hardware"]
    # An MCP client cannot assert `command_recognized`: the gate has no answer, so it blocks.
    assert (called.is_error, called.structured_content["status"]) == (False, "BLOCK")
    assert called.structured_content["reason"] == "criterion_unavailable"
    assert (refused.is_error, refused.structured_content["status"]) == (True, "REJECTED")
    trace = json.loads((project / "trace.json").read_text(encoding="utf-8"))
    assert trace["metadata"]["anonymized"] is True  # NFR-PRIV-03: the default holds from Python too
    events = [event["type"] for event in trace["events"]]
    assert "gate_evaluation_result" in events
    assert "actuator_command" not in events  # the blocked call moved nothing
    assert (project / "stderr.txt").read_text(encoding="utf-8") == ""


def test_serve_mcp_with_raw_says_so(tmp_path):
    missing = tmp_path / "missing.toml"
    # No agent here, so it stops right after the warning.
    with (
        pytest.warns(UserWarning, match="anonymized = false"),
        pytest.raises(NeuroEdgeError),
    ):
        neuroedge.serve_mcp(missing, trace_out=tmp_path / "t.json", raw=True)


def test_serve_mcp_on_linux_puts_the_signal_handlers_back_when_it_cannot_start(root):
    import signal

    before = signal.getsignal(signal.SIGTERM)
    agent = root / "fixtures" / "agents" / "villa-concierge" / "agent.toml"
    # An unknown board stops it before any line is requested, on any machine.
    with pytest.raises(NeuroEdgeError):
        neuroedge.serve_mcp(agent, target="linux", board="no-such-board")
    assert signal.getsignal(signal.SIGTERM) is before


def test_serve_mcp_refuses_a_target_that_has_no_session(root):
    agent = root / "fixtures" / "agents" / "villa-concierge" / "agent.toml"
    with pytest.raises(BoardCapabilityError, match="esp32s3"):
        neuroedge.serve_mcp(agent, target="esp32s3")


# --- SimSession and Turn: the members spec §2.1 promises -------------------------------------------


def test_sim_session_load_keeps_its_promised_parameters():
    from neuroedge.engine.trace_sink import monotonic_ms

    parameters = [
        (name, parameter.kind.name, parameter.default)
        for name, parameter in inspect.signature(neuroedge.SimSession.load).parameters.items()
    ]
    assert parameters == [
        ("agent_toml", "POSITIONAL_OR_KEYWORD", "agent.toml"),
        ("board_id", "KEYWORD_ONLY", None),
        ("facts", "KEYWORD_ONLY", None),
        ("registry", "KEYWORD_ONLY", None),
        ("clock", "KEYWORD_ONLY", monotonic_ms),
        ("events", "KEYWORD_ONLY", None),
        ("slow", "KEYWORD_ONLY", None),
        ("target", "KEYWORD_ONLY", "sim"),
        ("target_options", "KEYWORD_ONLY", None),
    ]


def test_a_loaded_sim_session_has_the_promised_members(root):
    import asyncio
    import dataclasses

    agent = root / "fixtures" / "agents" / "villa-concierge" / "agent.toml"
    session = neuroedge.SimSession.load(agent)
    assert inspect.iscoroutinefunction(neuroedge.SimSession.handle)
    assert list(inspect.signature(neuroedge.SimSession.handle).parameters)[:2] == ["self", "text"]
    assert list(inspect.signature(neuroedge.SimSession.set_sensor).parameters) == [
        "self",
        "sensor",
        "value",
    ]
    assert isinstance(session.hal, HardwareAbstractionLayer)
    assert callable(session.events.of_type)

    turn = asyncio.run(session.handle("mở cửa phòng 101"))
    assert isinstance(turn, neuroedge.Turn)
    fields = {field.name for field in dataclasses.fields(neuroedge.Turn)}
    assert {"result", "reply_source", "confirmation"} <= fields
    assert isinstance(turn.allowed, bool) and isinstance(turn.recognised, bool)
    assert turn.allowed and session.hal.pin("door_lock").pulsed
    trace = session.trace()
    assert [e["type"] for e in trace["events"]].count("gate_evaluation_result") == 1


def test_sim_session_set_sensor_takes_a_reading(root):
    agent = root / "fixtures" / "agents" / "factory-monitor" / "agent.toml"
    session = neuroedge.SimSession.load(agent)
    session.set_sensor("temperature", 30)
    assert session.hal.sensor_read("temperature") == 30
