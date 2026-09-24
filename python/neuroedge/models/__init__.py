"""
Model interfaces (L2): SystemOne, SystemTwo and the local command grammar.

SystemTwo's providers (LiteLLM, extra `neuroedge[cloud]`, or a custom adapter)
live in `neuroedge.models.providers` (TSK-S2-11); nothing here imports a provider SDK.
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
