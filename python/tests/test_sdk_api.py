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
    assert sdk.__all__ == ["SDK_VERSION", "Outcome", "ToolRequest"]
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
    for name in public - exported - {"annotations", "Mapping", "Any", "dataclass", "field"}:
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
