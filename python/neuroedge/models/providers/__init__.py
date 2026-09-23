"""
Model providers for `SystemTwo` (TSK-S2-11, Q-10, Q-12, FR-MDL-07/08).

The only place a provider SDK is named. Two kinds, chosen in `agent.toml`
`[system_two]` (`config.py`):

* ``provider = "litellm"`` — `LiteLLMProvider`: any model LiteLLM routes
  (``anthropic/claude-sonnet-5``, ``openai/gpt-4o-mini``, an OpenAI-compatible
  ``api_base``…). Extra ``neuroedge[cloud]``; LiteLLM is imported on first use.
* ``provider = "python:pkg.mod:factory"`` — a custom adapter: ``factory(config)``
  returns a provider (`base.Provider`). It runs without touching NeuroEdge.

The contract every provider meets is in `base.py`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ...errors import AgentManifestError
from .base import Provider, ProviderUnavailable, scrub
from .config import (
    LITELLM,
    SystemTwoConfig,
    load_adapter,
    load_system_two_config,
    parse_system_two,
)
from .litellm_provider import LiteLLMProvider
from .openai_chat import from_response, to_messages

__all__ = [
    "LITELLM",
    "LiteLLMProvider",
    "Provider",
    "ProviderUnavailable",
    "SystemTwoConfig",
    "from_response",
    "load_adapter",
    "load_system_two_config",
    "make_provider",
    "parse_system_two",
    "scrub",
    "system_two_for",
    "to_messages",
]


def make_provider(config: SystemTwoConfig, root: Path | None = None) -> Any:
    """The provider `config` names; a custom adapter's factory is called with `config`."""
    if config.adapter is None:
        return LiteLLMProvider(config)
    factory = load_adapter(config, root)
    try:
        provider = factory(config)
    except Exception as exc:
        raise AgentManifestError(
            where=f"{config.where} provider",
            why=f"the adapter factory {config.adapter!r} raised {type(exc).__name__}: {exc}",
            how="fix the adapter; it is called once, with the [system_two] config",
        ) from exc
    if not callable(provider):
        raise AgentManifestError(
            where=f"{config.where} provider",
            why=f"the adapter factory {config.adapter!r} returned {type(provider).__name__}, "
            "not a callable provider",
            how="return a callable (task, name, state) -> answer (models/providers/base.py)",
        )
    return provider


def system_two_for(manifest: Any, events: Any = None) -> Any:
    """
    The agent's `SystemTwo` from `[system_two]`, tracing each call to `events`;
    None when the agent has no `[system_two]` (System 2 stays offline).
    """
    from ..system import SystemTwo

    config = load_system_two_config(manifest)
    if config is None:
        return None
    provider = make_provider(config, manifest.root)
    return SystemTwo(config.model or config.provider, provider=provider, events=events)
