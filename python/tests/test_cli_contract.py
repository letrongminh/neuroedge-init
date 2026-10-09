"""
TSK-I6-06 (Q-63) — the CLI contract, pinned.

`docs/spec/python_api.md` §6 promises the command names, the option names and their kind, and
which arguments and options are required. This is the literal snapshot of that promise, read
from the Typer command tree: add, rename or remove a command or an option, make an argument
required, or turn a flag into a value option, and CI is red until the snapshot, the spec's
SemVer rule and the CHANGELOG entry move in the same PR. Exit codes are `CHANGELOG.md` §2.3;
their tests live with the commands.

Notation, one line per command (a group's subcommands are listed by their full path):

    <name> / [name]    a required / optional argument, in positional order; `...` takes many
    --long|-s          a flag;  `=` after it: it takes a value;  `*`: it may repeat
    !                  required;  `~`: hidden (a deprecated alias kept for one MINOR, §5)
"""

from __future__ import annotations

import typer.main

from neuroedge.cli.main import app

COMMANDS = {
    "add action": ("<name> --agent|-a= --board= --channel= --pin= --primitive="),
    "add device": ("<name> --agent|-a= --board= --device=! --register=! --width="),
    "add gate": "<name> --agent|-a= --fact=*",
    "add sensor": ("<name> --agent|-a= --board= --label= --pin= --primitive= --source="),
    "board list": "",
    "board show": "<board_id>",
    "build": "--agent|-a= --board|-b= --out|-o= --registry|-r= --target|-t=!",
    "gate add": "<uri>",
    "gate explain": "<target> --registry|-r=",
    "gate lint": "[directory] --registry|-r=",
    "gate publish": "<gate_file> --out|-o= --registry|-r=",
    "gate resolve": "<target> --json --registry|-r=",
    "guard init": "--dir= --env-from=* --header-env=* --http= --mcp= --name= --route=*",
    "mcp desktop-config": (
        "--agent|-a= --config-path= --name= --port= --raw --trace-out= --ui --write"
    ),
    "mcp serve": (
        "--agent|-a= --audience= --board|-b= --client-ca= --host= --http --init-timeout= "
        "--issuer= --jwks= --open --port= --raw --registry|-r= --required-scope= --target|-t= "
        "--tls-cert= --tls-key= --trace-out= --ui"
    ),
    "mcp tools": "--agent|-a= --external --json --openai",
    "new": "<name> --template=",
    "plugin doctor": "--config|-c= --json",
    "proxy http": "--config|-c= --trace-out=",
    "proxy mcp": "--config-path= --config|-c= --desktop-config --name= --trace-out= --write",
    "record": (
        "--agent|-a= --anonymize --baud= --board|-b= --command|-c= --out|-o= --port= --raw "
        "--registry|-r= --target|-t= --timeout= --voice-file= --voice-out="
    ),
    "replay": (
        "<trace_file> --agent|-a= --board|-b= --golden|-g= --raw --registry|-r= --target|-t= "
        "--trace-out="
    ),
    "run": (
        "--agent|-a= --board|-b= --command|-c= --half-duplex --mic --no-browser --port= --raw "
        "--registry|-r= --target|-t= --trace-out= --ui --voice-file= --voice-out="
    ),
    "studio": "--agent|-a= --half-duplex --mic --no-browser --port=",
    "test": "[path] --pytest-arg=*",
    "trace export": "<trace_file> --format|-f= --out|-o=",
    "trace show": "<trace_file>",
    "trace validate": "<trace_files>...",
    "trace view": "<trace_file> --open --out|-o=",
    "verify": "--baud= --port= --targets= --timeout=",
}


def _token(param) -> str:
    if type(param).__name__ == "TyperArgument":
        token = f"<{param.name}>" if param.required else f"[{param.name}]"
        return token + ("..." if param.nargs != 1 else "")
    names = [*param.opts, *param.secondary_opts]
    longs = sorted(name for name in names if name.startswith("--"))
    shorts = sorted(name for name in names if not name.startswith("--"))
    token = "|".join(longs + shorts)
    if not param.is_flag:
        token += "=" + ("*" if param.multiple else "")
    if param.required:
        token += "!"
    return ("~" if param.hidden else "") + token


def _leaves(command, path=()):
    if hasattr(command, "commands"):
        for name, sub in sorted(command.commands.items()):
            yield from _leaves(sub, (*path, name))
    else:
        yield path, command


def snapshot() -> dict[str, str]:
    commands = {}
    for path, command in _leaves(typer.main.get_command(app)):
        arguments = [_token(p) for p in command.params if type(p).__name__ == "TyperArgument"]
        options = sorted(_token(p) for p in command.params if type(p).__name__ != "TyperArgument")
        name = " ".join(path)
        commands[("~" if command.hidden else "") + name] = " ".join(arguments + options)
    return commands


def test_the_cli_contract_is_the_pinned_snapshot():
    # A mismatch is a SemVer decision (docs/spec/python_api.md §6): update this table, the
    # spec and the CHANGELOG entry in the same PR.
    assert snapshot() == COMMANDS


def test_the_snapshot_is_sorted_and_names_every_command_once():
    assert list(COMMANDS) == sorted(COMMANDS)
    assert len(snapshot()) == len(COMMANDS)
