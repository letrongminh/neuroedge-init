"""
The host package's dependency graph, as docs/architecture/vi/03-component-host-c4l3.md §2 draws
it. A new edge between subpackages is an architecture decision: add it here and to that page in
the same change, or do not add it.

Only relative imports inside `neuroedge` are counted. A module-level import is an edge; an import
inside a function (a lazy import) is allowed only where the table below names it, because each one
is a deliberate exception (the build-time checks of `engine/compiler.py`, optional SDKs).
"""

from __future__ import annotations

import ast
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1] / "neuroedge"

# unit -> the units it may import at module level
ALLOWED: dict[str, set[str]] = {
    "errors": set(),
    "net": set(),
    "paths": {"errors"},
    "trace": {"errors", "paths"},
    "hal": {"errors", "paths"},
    "engine": {"errors", "paths", "trace", "hal"},
    # `paths`: `actions/tools.py::result_schema` reads schemas/tool-result.v1.json (RFC-0015)
    "actions": {"engine", "errors", "hal", "paths"},
    "models": {"engine", "errors", "net"},
    "mcp_desktop": {"errors"},
    "mcp_host": {"actions", "errors"},
    "mcp_server": {"actions", "errors"},
    # the network door (TSK-P2-04): the same server as stdio's, behind TLS and token checks
    "mcp_http": {"errors", "mcp_server"},
    "viz": {"errors", "hal", "trace"},
    "templates": {"errors", "paths"},
    "sim": {
        "actions",
        "engine",
        "errors",
        "hal",
        "mcp_host",
        "mcp_http",
        "mcp_server",
        "models",
        "trace",
        "viz",
    },
    "perception": {"actions", "engine", "errors", "hal", "models", "net", "sim"},
    # the SDK surface: two data types and a version, no other layer (RFC-0016 §3c)
    "sdk": {"errors"},
    # the safety core without an agent (TSK-I2c-07): it builds the same HAL as a session, so it
    # sits beside `sim`, above `actions`/`engine`/`hal`; `__init__` is read for `__version__` only
    "guard": {"actions", "engine", "errors", "hal", "models", "sdk", "sim", "trace"},
    "testing": {"actions", "engine", "errors", "hal", "paths", "perception", "trace"},
    # The studio (TSK-I1-04) shows every capability, so it reads every layer below the CLI.
    "studio": {
        "actions",
        "engine",
        "errors",
        "hal",
        "mcp_server",
        "models",
        "paths",
        "perception",
        "sim",
        "testing",
        "trace",
        "viz",
    },
    "cli": {"actions", "engine", "errors", "hal", "models", "paths", "perception", "sim", "trace"},
    "__init__": {"actions", "engine", "errors", "hal", "models", "sim", "testing", "trace"},
    "__main__": {"cli"},
}
# the engine's pure core: only engine/compiler.py matches the agent against a board
HAL_IN_ENGINE = {"engine/compiler.py"}
# module -> units it may import lazily (inside a function) beyond its module-level set
LAZY: dict[str, set[str]] = {
    "engine/compiler.py": {"actions", "mcp_host", "models", "perception"},
    "cli/main.py": {
        "mcp_desktop",
        "mcp_host",
        "mcp_http",
        "mcp_server",
        "studio",
        "templates",
        "testing",
        "viz",
    },
    "mcp_host.py": {"mcp_server"},
    # `serve_mcp` records the session only when asked to: the recorder is `testing`'s
    "sim/serve.py": {"testing"},
    # `[vision]` (TSK-V1b-01/02): `perception` sits above `sim` (the voice session wraps a
    # `SimSession`), so a session that reads a camera imports the vision pipeline only when the
    # agent declares `[vision]`, inside the function that wires it
    "sim/session.py": {"perception"},
    "sim/vision/feed.py": {"perception"},
    # the studio shows the same desktop entry and template list as the CLI, and reads no unit above it
    "studio/api_agent.py": {"mcp_desktop", "templates"},
    "testing/tool_corpus.py": {"sim"},
    "testing/voice_corpus.py": {"sim"},
    "testing/player.py": {"sim", "guard"},
    "testing/__init__.py": {"sim"},
}


def _unit(rel: Path) -> str:
    return rel.parts[0] if len(rel.parts) > 1 else rel.stem


def _target(rel: Path, node: ast.ImportFrom) -> str | None:
    """The unit a relative `from … import …` names, or None when it stays inside its own package."""
    package = list(rel.parts[:-1])
    base = package[: len(package) - (node.level - 1)] if node.level > 1 else package
    parts = base + (node.module.split(".") if node.module else [])
    if not parts:  # `from ... import net`: a root module, or else a name from the root __init__
        name = node.names[0].name
        return (
            name if (PACKAGE / f"{name}.py").is_file() or (PACKAGE / name).is_dir() else "__init__"
        )
    return parts[0]


def _edges():
    for path in sorted(PACKAGE.rglob("*.py")):
        rel = path.relative_to(PACKAGE)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        top = {id(n) for n in tree.body}
        for (
            statement
        ) in tree.body:  # imports guarded by `if TYPE_CHECKING:` or `try:` at module level
            if isinstance(statement, ast.If | ast.Try):
                top |= {id(n) for n in ast.walk(statement)}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level > 0:
                if [a.name for a in node.names] == ["__version__"]:
                    continue  # the version string for a User-Agent, not a layer edge
                target = _target(rel, node)
                if target and target != _unit(rel):
                    yield rel.as_posix(), _unit(rel), target, id(node) in top


def test_every_module_level_import_is_an_allowed_layer_edge() -> None:
    wrong = [
        f"{module} imports {target} ({unit} may import only {sorted(ALLOWED.get(unit, set()))})"
        for module, unit, target, top in _edges()
        if top and target not in ALLOWED.get(unit, set())
    ]
    assert not wrong, (
        "new layer edge — update ALLOWED and 03-component-host-c4l3.md:\n  " + "\n  ".join(wrong)
    )


def test_the_engine_core_never_imports_the_hal() -> None:
    wrong = [
        module
        for module, unit, target, _ in _edges()
        if unit == "engine" and target == "hal" and module not in HAL_IN_ENGINE
    ]
    assert not wrong, f"only {sorted(HAL_IN_ENGINE)} may use the HAL inside engine/: {wrong}"


def test_every_lazy_import_is_a_named_exception() -> None:
    wrong = [
        f"{module} lazily imports {target}"
        for module, unit, target, top in _edges()
        if not top
        and target not in ALLOWED.get(unit, set())
        and target not in LAZY.get(module, set())
    ]
    assert not wrong, (
        "lazy import outside the named exceptions — add it to LAZY with a reason:\n  "
        + "\n  ".join(wrong)
    )


def test_the_hal_is_a_leaf() -> None:
    assert ALLOWED["hal"] == {"errors", "paths"}
    wrong = [
        f"{m} imports {t}" for m, u, t, _ in _edges() if u == "hal" and t not in ALLOWED["hal"]
    ]
    assert not wrong, wrong
