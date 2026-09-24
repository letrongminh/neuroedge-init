"""
`python -m neuroedge` — the CLI, for launchers that need an absolute interpreter (Claude
Desktop, see `neuroedge mcp desktop-config`). Unlike `-m neuroedge.cli.main` it does not
load the CLI module twice, so nothing but the command's own output reaches stderr.
"""

from .cli.main import app

app(prog_name="neuroedge")
