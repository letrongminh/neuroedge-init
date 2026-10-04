"""
RFC-0015 §3d — the machine-readable catalogue of `NE…` codes, and who is held to it.

`schemas/error-codes.v1.json` is the one place that says which codes exist, their classes, parents
and status. Three other places are *checked* against it, never trusted to agree: `errors.py` (and
the subclasses that share a code), the PRD's Phụ lục B (which keeps the wording), and the firmware
sources under `targets/`. `schemas/error.v1.json` is the shape of one serialised error.
"""

from __future__ import annotations

import importlib
import inspect
import json
import pkgutil
import re
from pathlib import Path

import jsonschema
import pytest

import neuroedge
from neuroedge import errors
from neuroedge.errors import NeuroEdgeError
from neuroedge.paths import repo_root

ROOT = repo_root()
CATALOG = json.loads((ROOT / "schemas" / "error-codes.v1.json").read_text(encoding="utf-8"))
ERROR_SCHEMA = json.loads((ROOT / "schemas" / "error.v1.json").read_text(encoding="utf-8"))
PRD = ROOT / "roadmap" / "neuroedge-prd.md"
BY_CODE = {entry["code"]: entry for entry in CATALOG["codes"]}
BY_NAME = {entry["name"]: entry for entry in CATALOG["codes"]}


def _package_error_classes() -> dict[str, type[NeuroEdgeError]]:
    """Every `NeuroEdgeError` subclass defined anywhere in the package, by name."""
    for module in pkgutil.walk_packages(neuroedge.__path__, "neuroedge."):
        if not module.name.endswith("__main__"):
            importlib.import_module(module.name)
    found: dict[str, type[NeuroEdgeError]] = {}
    pending = [NeuroEdgeError]
    while pending:
        cls = pending.pop()
        if cls.__name__ in found:
            continue
        found[cls.__name__] = cls
        pending.extend(cls.__subclasses__())
    return found


CLASSES = _package_error_classes()


def _validator(fragment: str | None = None) -> jsonschema.Draft202012Validator:
    if fragment is None:
        return jsonschema.Draft202012Validator(ERROR_SCHEMA)
    schema = {
        "$schema": ERROR_SCHEMA["$schema"],
        "$ref": f"#/$defs/{fragment}",
        "$defs": ERROR_SCHEMA["$defs"],
    }
    return jsonschema.Draft202012Validator(schema)


def test_the_catalog_validates_against_its_own_shape():
    _validator("catalog").validate(CATALOG)


def test_a_catalog_code_is_never_listed_twice_and_its_parent_is_in_the_catalog():
    codes = [entry["code"] for entry in CATALOG["codes"]]
    names = [entry["name"] for entry in CATALOG["codes"]]
    assert len(codes) == len(set(codes)) and len(names) == len(set(names))
    assert [e["name"] for e in CATALOG["codes"] if e["parent"] not in {*names, None}] == []
    assert [e["name"] for e in CATALOG["codes"] if e["parent"] is None] == ["NeuroEdgeError"]
    aliases = [alias for entry in CATALOG["codes"] for alias in entry.get("aliases", [])]
    assert len(aliases) == len(set(aliases)) and not set(aliases) & set(names)


def test_the_catalog_holds_seventeen_stable_codes_and_no_reserved_one():
    """
    RFC-0015 §10 #13 (which counts "20"; its own list, NE0000, NE1001→4, NE2000→3, NE3001→3,
    NE4001→4, NE5001, is 17). The `reserved` status stays in the schema for the next held code.
    """
    assert [e["code"] for e in CATALOG["codes"] if e["status"] == "reserved"] == []
    assert len([e for e in CATALOG["codes"] if e["status"] == "stable"]) == 17
    status = ERROR_SCHEMA["$defs"]["entry"]["properties"]["status"]
    assert status["enum"] == ["stable", "reserved"]


def test_only_the_two_unclassified_codes_are_general():
    """RFC-0015 §10 #9: a receiver must not branch on NE0000 or NE2000."""
    assert {e["code"] for e in CATALOG["codes"] if e.get("general")} == {"NE0000", "NE2000"}


def test_the_error_catalog_and_errors_py_agree_both_ways():
    for entry in CATALOG["codes"]:
        if entry["status"] != "stable":
            continue
        cls = getattr(errors, entry["name"], None)
        assert cls is not None, f"{entry['name']} is in the catalogue and not in errors.py"
        assert cls.code == entry["code"], entry["name"]
        parent = cls.__mro__[1]
        expected_parent = entry["parent"]
        assert (parent.__name__ if expected_parent else None) == expected_parent or (
            expected_parent in {base.__name__ for base in cls.__mro__[1:]}
        ), f"{entry['name']}: parent is {parent.__name__}, catalogue says {expected_parent}"
        extra = {base.__name__ for base in cls.__mro__[1:]} - {
            b.__name__ for b in NeuroEdgeError.__mro__
        }
        in_catalog = {b for b in extra if b in BY_NAME}
        python_only = extra - in_catalog
        assert python_only <= set(entry.get("also_a", [])) | {"object"}, (
            f"{entry['name']}: bases {sorted(python_only)} are not in `also_a`"
        )
        for alias in entry.get("aliases", []):
            sub = CLASSES.get(alias)
            assert sub is not None and issubclass(sub, cls), f"{alias} is not a {entry['name']}"
            assert sub.code == entry["code"], f"{alias} has its own code"
    # the other way: every class of errors.py with a code of its own is in the catalogue
    own = {
        name
        for name, value in vars(errors).items()
        if inspect.isclass(value) and issubclass(value, NeuroEdgeError)
    }
    assert sorted(own - set(BY_NAME)) == []


def test_every_error_class_of_the_package_has_a_catalog_entry():
    """A public class is an entry or an alias; a private one still emits a code of the catalogue."""
    aliases = {alias for entry in CATALOG["codes"] for alias in entry.get("aliases", [])}
    problems = []
    for name, cls in sorted(CLASSES.items()):
        if name.startswith("_"):
            if cls.code not in BY_CODE:
                problems.append(f"{name}: emits {cls.code}, which the catalogue lacks")
        elif name not in BY_NAME and name not in aliases:
            problems.append(f"{name}: no entry and no alias in schemas/error-codes.v1.json")
    assert problems == []


def test_an_alias_shares_the_code_of_the_entry_that_lists_it():
    for entry in CATALOG["codes"]:
        for alias in entry.get("aliases", []):
            assert CLASSES[alias].code == entry["code"]


def _reserved_problems(codes: list[dict], classes: dict[str, type]) -> list[str]:
    """What is wrong with the `reserved` entries of `codes`: a held code has no class yet."""
    return [
        f"{entry['code']}: reserved, but {cls.__name__} already carries it"
        for entry in codes
        if entry["status"] == "reserved"
        for cls in classes.values()
        if getattr(cls, "code", None) == entry["code"] or cls.__name__ == entry["name"]
    ]


def test_a_reserved_code_has_no_class():
    assert _reserved_problems(CATALOG["codes"], CLASSES) == []
    # The check is not vacuous: held back to a code that a class already carries, it fires.
    held = [{"code": "NE1004", "name": "SomethingElse", "parent": None, "status": "reserved"}]
    assert _reserved_problems(held, CLASSES) == [
        "NE1004: reserved, but ToolCallError already carries it"
    ]


def _prd_error_table() -> dict[str, str]:
    text = PRD.read_text(encoding="utf-8")
    appendix = text[text.index("## Phụ lục B") : text.index("## Phụ lục C")]
    return dict(re.findall(r"^\| `(\w+)` \| (NE\d{4}) \|", appendix, flags=re.MULTILINE))


def test_the_prd_error_table_and_the_catalog_agree_on_class_and_code():
    """The PRD keeps the wording; the pair (class, code) of each row is the catalogue's."""
    assert _prd_error_table() == {entry["name"]: entry["code"] for entry in CATALOG["codes"]}


def test_the_prd_names_every_alias_of_a_code_in_that_codes_row():
    text = PRD.read_text(encoding="utf-8")
    appendix = text[text.index("## Phụ lục B") : text.index("## Phụ lục C")]
    rows = {m.group(1): m.group(0) for m in re.finditer(r"^\| `(\w+)` \|.*$", appendix, re.M)}
    for entry in CATALOG["codes"]:
        for alias in entry.get("aliases", []):
            assert alias in rows[entry["name"]], f"PRD row of {entry['name']} omits {alias}"


def test_every_error_code_in_targets_is_in_the_catalog():
    """The device speaks codes too (`ne_token.c`: NE1001, NE1002); none may be unknown."""
    skipped = {"build", "managed_components", "__pycache__", ".git"}
    seen: set[str] = set()
    for path in (ROOT / "targets").rglob("*"):
        if (
            path.is_file()
            and not skipped & set(path.parts)
            and path.suffix in {".c", ".h", ".cpp", ".txt", ".cmake", ".py", ".md", ".yml"}
        ):
            seen |= set(
                re.findall(r"\bNE[0-9]{4}\b", path.read_text(encoding="utf-8", errors="ignore"))
            )
    assert seen, (
        "targets/ no longer mentions any NE code: is this test still looking in the right place?"
    )
    assert sorted(seen - set(BY_CODE)) == []


# --- one serialised error validates against error.v1 ---------------------------------------------


def _sample(cls: type[NeuroEdgeError]) -> NeuroEdgeError:
    """An instance of `cls` built from sample data, whatever its constructor asks for."""
    values = {
        "where": "gates/unlock_door@1.2.0.yaml:12",
        "why": "the sample says what rule was broken",
        "how": "the sample says what to do next",
        "reason": "token_replayed",
        "principle": 2,
        "role": "stt",
        "problems": [NeuroEdgeError("a", "b", "c")],
    }
    parameters = inspect.signature(cls.__init__).parameters
    kwargs = {name: values[name] for name in parameters if name in values}
    return cls(**kwargs)


@pytest.mark.parametrize("name", sorted(CLASSES))
def test_every_serialised_error_validates_against_the_error_schema(name):
    cls = CLASSES[name]
    error = _sample(cls)
    data = error.as_dict()
    _validator().validate(data)
    assert data["code"] == cls.code
    # `as_dict` adds only the keys the catalogue declares for its code
    declared = {"code", "where", "why", "how", *BY_CODE[cls.code].get("fields", [])}
    assert set(data) <= declared, f"{name}: undeclared keys {sorted(set(data) - declared)}"
    assert isinstance(data.get("principle", ""), str)  # F5: a string, as it runs today


def test_the_error_schema_catches_what_the_rfc_names():
    schema = _validator()
    base = {"code": "NE4003", "where": "w", "why": "y", "how": "h"}
    assert schema.is_valid(base)
    assert not schema.is_valid({**base, "why": ""})
    assert not schema.is_valid({**base, "code": "E4003"})
    assert not schema.is_valid({**base, "code": "NE2003"})  # no principle
    assert not schema.is_valid({**base, "code": "NE2003", "principle": 2})  # a string, F5
    assert schema.is_valid({**base, "code": "NE2003", "principle": "2"})
    assert not schema.is_valid({**base, "code": "NE1002"})  # no reason
    assert schema.is_valid({**base, "code": "NE9999"})  # `code` is a pattern, not an enum


def test_the_error_classes_that_declare_a_field_really_emit_it():
    for entry in CATALOG["codes"]:
        for field in entry.get("fields", []):
            data = _sample(getattr(errors, entry["name"])).as_dict()
            assert field in data, f"{entry['name']}.as_dict() lacks the declared field {field!r}"


def test_the_catalog_file_is_the_one_the_wheel_would_ship(root: Path):
    assert (root / "schemas" / "error-codes.v1.json").is_file()
