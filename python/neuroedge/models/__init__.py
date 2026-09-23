"""
Model interfaces (L2): SystemOne, SystemTwo and the local command grammar.

Provider connectors (LiteLLM behind `neuroedge.models.providers`, extra
`neuroedge[cloud]`) arrive with TSK-S2-11; this package imports no provider SDK.
"""

from .doubles import ScriptedSource
from .grammar import BACKEND, Command, CommandGrammar, GrammarAdjudicator, Recognition, normalise
from .system import SystemOne, SystemTwo

__all__ = [
    "BACKEND",
    "Command",
    "CommandGrammar",
    "GrammarAdjudicator",
    "Recognition",
    "ScriptedSource",
    "SystemOne",
    "SystemTwo",
    "normalise",
]
