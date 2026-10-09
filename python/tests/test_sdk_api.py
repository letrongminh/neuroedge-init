"""
`neuroedge.sdk` (RFC-0016 §3c, §3e): the surface an extension may rely on, pinned the way
`test_public_api.py` pins `neuroedge.__all__`. A change to any line here is a decision about the
SDK's own SemVer, not a refactor.
"""

from __future__ import annotations

import dataclasses
import inspect

import pytest

import neuroedge
from neuroedge import sdk
from neuroedge.errors import ToolCallError


def test_the_sdk_surface_is_pinned():
    assert sdk.__all__ == [
        "SDK_VERSION",
        "Actuator",
        "ActuatorError",
        "Ambiguous",
        "Command",
        "DeviceDouble",
        "NotSent",
        "Outcome",
        "ReadFailed",
        "Rejected",
        "ToolRequest",
    ]
    assert sorted(n for n in vars(sdk) if not n.startswith("_") and n in sdk.__all__) == sorted(
        sdk.__all__
    )
    request = {f.name: f.default for f in dataclasses.fields(sdk.ToolRequest)}
    assert list(request) == ["name", "arguments", "id"], "tool-call.v1#/$defs/request, no `source`"
    assert [f.name for f in dataclasses.fields(sdk.Outcome)] == ["status", "content"]
    assert str(inspect.signature(sdk.ToolRequest)) == (
        "(name: 'str', arguments: 'Mapping[str, Any]' = <factory>, id: 'str' = '') -> None"
    )
    assert sdk.ToolRequest.__dataclass_params__.frozen and sdk.Outcome.__dataclass_params__.frozen
    assert sdk.SDK_VERSION == (1, 0)
    # a request is data: it takes name, arguments and id, and refuses anything else
    with pytest.raises(TypeError):
        sdk.ToolRequest("x", {}, "", "bridge:other")  # type: ignore[call-arg]
    with pytest.raises(ToolCallError):
        sdk.ToolRequest("x", ["not", "a", "mapping"])  # type: ignore[arg-type]


def test_the_request_fields_are_the_request_of_the_tool_call_schema(root):
    import json

    schema = json.loads((root / "schemas" / "tool-call.v1.json").read_text(encoding="utf-8"))
    assert set(schema["$defs"]["request"]["properties"]) == {
        f.name for f in dataclasses.fields(sdk.ToolRequest)
    }


def test_the_sdk_version_is_not_the_package_version():
    assert isinstance(sdk.SDK_VERSION, tuple) and all(isinstance(n, int) for n in sdk.SDK_VERSION)
    assert len(sdk.SDK_VERSION) == 2
    assert ".".join(map(str, sdk.SDK_VERSION)) != neuroedge.__version__
    assert not hasattr(sdk, "__version__")
    assert neuroedge.__version__ == "0.1.0" and sdk.SDK_VERSION == (1, 0)  # independent numbers


def test_the_sdk_exports_no_hal_name_and_no_name_of_all():
    exported = set(sdk.__all__)
    assert not exported & set(neuroedge.__all__)
    hal_names = {"SimHAL", "LinuxHAL", "HardwareAbstractionLayer", "digital", "motion", "hal"}
    assert not exported & hal_names
    # nothing in the module namespace gives a route to the core either
    public = {n for n, v in vars(sdk).items() if not n.startswith("_")}
    helpers = {"annotations", "Mapping", "Any", "Literal", "Protocol", "runtime_checkable"}
    for name in public - exported - helpers - {"dataclass", "field"}:
        value = getattr(sdk, name)
        assert not getattr(value, "__module__", "").startswith("neuroedge.hal"), name
        assert name not in {"Guard", "Conversation", "dispatch", "TokenLedger"}, name


def test_the_sdk_imports_nothing_of_the_core_but_errors():
    import ast
    from pathlib import Path

    source = Path(sdk.__file__).read_text(encoding="utf-8")
    imported = {
        node.module
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom) and node.level > 0
    }
    assert imported == {"errors"}


def test_the_actuator_protocol_signature_is_pinned():
    """RFC-0018 §3c is the one source of these signatures; the SDK re-exports them."""
    members = {
        name
        for name in vars(sdk.Actuator)
        if not name.startswith("_") and name not in ("_is_protocol", "_is_runtime_protocol")
    }
    assert members == {"apply", "safe_off", "read_state", "probe"}
    assert sdk.Actuator.__annotations__ == {
        "safe_off_level": "Literal['L0', 'L1', 'L2', 'L3']",
        "readback": "Literal['push', 'poll', 'none']",
        "tolerance_ms": "int",
        "command_timeout_ms": "int",
        "max_lease_ms": "int | None",
    }
    signatures = {
        name: str(inspect.signature(getattr(sdk.Actuator, name)))
        for name in ("apply", "safe_off", "read_state", "probe")
    }
    assert signatures == {
        "apply": "(self, command: 'Command') -> 'None'",
        "safe_off": "(self) -> 'None'",
        "read_state": "(self) -> 'tuple[bool, int]'",
        "probe": "(self) -> 'DeviceDouble'",
    }
    double = {
        name: str(inspect.signature(getattr(sdk.DeviceDouble, name)))
        for name in ("state", "cut_link", "heal_link", "advance")
    }
    assert double == {
        "state": "(self) -> 'bool'",
        "cut_link": "(self) -> 'None'",
        "heal_link": "(self) -> 'None'",
        "advance": "(self, ms: 'int') -> 'None'",
    }
    assert [(f.name, f.default) for f in dataclasses.fields(sdk.Command)] == [
        ("id", dataclasses.MISSING),
        ("operation", dataclasses.MISSING),
        ("duration_ms", None),
        ("lease_ms", None),
    ]
    assert sdk.Command.__dataclass_params__.frozen
    # the four errors: one base, none of them a NeuroEdgeError (no NE code, RFC-0018 §3k)
    from neuroedge.errors import NeuroEdgeError

    for error in (sdk.NotSent, sdk.Rejected, sdk.Ambiguous, sdk.ReadFailed):
        assert issubclass(error, sdk.ActuatorError) and error.__bases__ == (sdk.ActuatorError,)
        assert not issubclass(error, NeuroEdgeError)
    assert sdk.ActuatorError.__bases__ == (Exception,)
