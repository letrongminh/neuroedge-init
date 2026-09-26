"""
The examples every `--help` page ends with (TSK-I1-03, FR-CLI-07).

One entry per command and per command group, keyed by its path under `neuroedge`
(`""` is `neuroedge` itself). Each example is a real invocation of today's CLI,
written for the directory `neuroedge new my-agent` creates (it has `agent.toml`,
`gates/custom_lock@1.0.0.yaml` and `traces/`); a `neuroedge://` gate resolves from
any directory. `tests/test_cli_examples.py` requires an entry for every command,
parses every example with the real parser, and checks that `--help` shows it — a
new command without an example, or an example that names a flag that no longer
exists, fails CI.
"""

from __future__ import annotations

EXAMPLES: dict[str, tuple[str, ...]] = {
    "": (
        "neuroedge new my-agent",
        'neuroedge run -c "mở khoá"',
        "neuroedge verify",
    ),
    # -- gate -------------------------------------------------------------------------
    "gate": (
        "neuroedge gate lint gates",
        "neuroedge gate explain gates/custom_lock@1.0.0.yaml",
    ),
    "gate resolve": (
        "neuroedge gate resolve neuroedge://gates/unlock_door@1.2.0",
        "neuroedge gate resolve gates/custom_lock@1.0.0.yaml --json",
    ),
    "gate explain": (
        "neuroedge gate explain gates/custom_lock@1.0.0.yaml",
        "neuroedge gate explain neuroedge://gates/unlock_door_night@1.0.0",
    ),
    "gate lint": (
        "neuroedge gate lint gates",
        "neuroedge gate lint              # the gates NeuroEdge ships",
    ),
    "gate publish": (
        "neuroedge gate publish gates/custom_lock@1.0.0.yaml -o build/custom_lock.json",
    ),
    "gate add": ("neuroedge gate add neuroedge://gates/unlock_door@1.2.0",),
    # -- trace ------------------------------------------------------------------------
    "trace": (
        "neuroedge trace validate traces/session.json",
        "neuroedge trace show traces/session.json",
    ),
    "trace validate": (
        "neuroedge trace validate traces/session.json",
        "neuroedge trace validate traces/*.json",
    ),
    "trace view": ("neuroedge trace view traces/session.json --open",),
    "trace export": (
        "neuroedge trace export traces/session.json -f chrome -o traces/session.chrome.json",
    ),
    "trace show": ("neuroedge trace show traces/session.json",),
    # -- board ------------------------------------------------------------------------
    "board": (
        "neuroedge board list",
        "neuroedge board show esp32s3-box-3",
    ),
    "board list": ("neuroedge board list",),
    "board show": (
        "neuroedge board show sim-default",
        "neuroedge board show esp32s3-box-3",
    ),
    # -- mcp --------------------------------------------------------------------------
    "mcp": (
        "neuroedge mcp tools",
        "neuroedge mcp serve --ui",
    ),
    "mcp tools": (
        "neuroedge mcp tools",
        "neuroedge mcp tools --openai",
    ),
    "mcp serve": (
        "neuroedge mcp serve --agent agent.toml",
        "neuroedge mcp serve --ui --trace-out traces/mcp.json",
    ),
    "mcp desktop-config": (
        "neuroedge mcp desktop-config --agent agent.toml --ui",
        "neuroedge mcp desktop-config --agent agent.toml --ui --write",
    ),
    # -- top level --------------------------------------------------------------------
    "verify": (
        "neuroedge verify",
        "neuroedge verify --targets sim,linux",
    ),
    "replay": (
        "neuroedge replay traces/session.json --agent agent.toml",
        "neuroedge replay traces/session.json -a agent.toml --golden traces/golden/unlock.json",
    ),
    "new": (
        "neuroedge new my-agent",
        "neuroedge new my-home --template home-voice",
    ),
    "run": (
        'neuroedge run -c "mở khoá"',
        "neuroedge run                    # REPL: type a command, :help, exit",
        "neuroedge run --ui",
    ),
    "build": (
        "neuroedge build --target sim --board sim-default",
        "neuroedge build --target esp32s3 --board esp32s3-box-3   # + build/esp32s3/",
    ),
    "test": (
        "neuroedge test",
        "neuroedge test tests/ --pytest-arg=-x",
    ),
    "record": (
        'neuroedge record -c "mở khoá"   # writes traces/<session_id>.json',
        'neuroedge record -c "mở khoá" --out traces/session.json --anonymize',
    ),
}


def epilog(path: str) -> str:
    """The `Examples:` block of `neuroedge <path> --help`; a missing entry is a KeyError."""
    return "Examples:\n" + "\n".join(f"  {line}" for line in EXAMPLES[path])
