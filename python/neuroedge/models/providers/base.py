"""
The provider contract of `SystemTwo` (Q-12, FR-MDL-07/08).

A provider is any callable ``(task, name, state) -> answer``, sync or async:

* ``task`` — ``"respond"`` (a reply that may carry tool calls), ``"reply"``
  (text) or ``"extract"`` (text: the value of ``name``);
* ``state`` — what the session hands the model: ``task`` (converse, knowledge,
  news…), ``utterance``, ``instructions``, and for a tool turn ``tools`` (OpenAI
  function-calling list) and ``messages`` (the rounds so far); the knowledge
  task adds ``context``;
* the answer — for ``respond``, text or ``{"text": ..., "tool_calls": [...]}``
  (`neuroedge.actions.tools.parse_tool_calls` reads it); for ``reply`` and
  ``extract``, text.

A provider that cannot answer **raises**; `SystemTwo` turns that into
`PerceptionUnavailableError` and the agent says its offline line. It never
makes an answer up. A provider may expose ``name``, ``model`` and, after each
call, ``last_usage`` (``prompt_tokens``, ``completion_tokens``, ``cost_usd``)
— `SystemTwo` puts them in the `system_two_call` trace event (FR-MDL-06).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Protocol

from ...errors import PerceptionUnavailableError


class Provider(Protocol):
    def __call__(self, task: str, name: str | None, state: Mapping[str, Any] | None) -> Any: ...


ProviderFactory = Callable[..., Provider]


class ProviderUnavailable(PerceptionUnavailableError):
    """
    A provider could not answer. `called` is False when it gave up before
    reaching the model (extra missing, key missing) — then no model call is
    traced, because none was made.
    """

    # Same stable code as its parent (NE5001): a subclass, not a new error.

    def __init__(self, where: str, why: str, how: str, *, called: bool = True) -> None:
        self.called = called
        super().__init__(where=where, why=why, how=how)


def scrub(text: str, secret: str | None) -> str:
    """`text` with every occurrence of `secret` masked — an error must never carry a key."""
    if secret and len(secret) >= 4:
        text = text.replace(secret, "***")
    return text
