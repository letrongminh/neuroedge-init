"""
Model providers for `SystemTwo` and `SystemOne` (TSK-S2-11, TSK-I4-02, Q-4, Q-10, Q-12,
FR-MDL-04/07/08).

The only place a provider is named. System 2, chosen in `agent.toml` `[system_two]`
(`config.py`):

* ``provider = "litellm"`` — `LiteLLMProvider`: any model LiteLLM routes
  (``anthropic/claude-sonnet-5``, ``openai/gpt-4o-mini``, an OpenAI-compatible
  ``api_base``…). Extra ``neuroedge[cloud]``; LiteLLM is imported on first use.
* ``provider = "python:pkg.mod:factory"`` — a custom adapter: ``factory(config)``
  returns a provider (`base.Provider`). It runs without touching NeuroEdge.

The contract every System 2 provider meets is in `base.py`.

System 1's cloud primary, chosen in `[system_one]`; the command grammar stays its
fallback (Q-14):

* ``provider = "systemone"`` — `SystemOneApi`: Jev (``typesafe/jev-1.13``) or any
  model behind the System One API, ``POST {api_base}/systemone``. Standard library
  only, so no extra.
* ``provider = "python:pkg.mod:factory"`` — a custom adapter: ``factory(config)``
  returns a `FactSource`, held to the same checks (`systemone_api.TracedSource`).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ...errors import AgentManifestError
from .base import Provider, ProviderUnavailable, scrub
from .config import (
    LITELLM,
    SYSTEMONE,
    SystemOneConfig,
    SystemTwoConfig,
    load_adapter,
    load_system_one_config,
    load_system_two_config,
    parse_system_one,
    parse_system_two,
)
from .litellm_provider import LiteLLMProvider
from .openai_chat import from_response, to_messages
from .systemone_api import SystemOneApi, TracedSource

__all__ = [
    "LITELLM",
    "SYSTEMONE",
    "LiteLLMProvider",
    "Provider",
    "ProviderUnavailable",
    "SystemOneApi",
    "SystemOneConfig",
    "SystemTwoConfig",
    "TracedSource",
    "from_response",
    "load_adapter",
    "load_system_one_config",
    "load_system_two_config",
    "make_provider",
    "make_system_one_source",
    "parse_system_one",
    "parse_system_two",
    "scrub",
    "system_one_for",
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


def make_system_one_source(
    config: SystemOneConfig, root: Path | None = None, events: Any = None
) -> Any:
    """The `FactSource` `config` names; a custom adapter's factory is called with `config`."""
    if config.adapter is None:
        return SystemOneApi(config, events=events)
    factory = load_adapter(config, root)
    try:
        source = factory(config)
    except Exception as exc:
        raise AgentManifestError(
            where=f"{config.where} provider",
            why=f"the adapter factory {config.adapter!r} raised {type(exc).__name__}: {exc}",
            how="fix the adapter; it is called once, with the [system_one] config",
        ) from exc
    if not callable(getattr(source, "adjudicate", None)):
        raise AgentManifestError(
            where=f"{config.where} provider",
            why=f"the adapter factory {config.adapter!r} returned {type(source).__name__}, "
            "not a FactSource",
            how="return an object with async adjudicate(criterion, definition, state, "
            "deadline_ms) -> Fact | Unavailable (neuroedge.engine.gate.FactSource)",
        )
    return TracedSource(source, config, events)


def system_one_for(manifest: Any, events: Any = None, *, fallback: Any = None) -> Any:
    """
    The agent's `SystemOne` from `[system_one]`: the cloud primary for the listed
    criteria, `fallback` (the command grammar) for everything else and whenever the
    primary cannot answer, a circuit breaker in front of the primary, every call
    traced to `events`. None when the agent has no `[system_one]` (the grammar alone).
    """
    from ...engine.circuit_breaker import DegradationBreaker
    from ...engine.trace_sink import monotonic_ms
    from ..system import SystemOne

    config = load_system_one_config(manifest)
    if config is None:
        return None
    primary = make_system_one_source(config, manifest.root, events)
    clock = events.clock if events is not None else monotonic_ms
    return SystemOne(
        config.model or config.provider,
        primary=primary,
        fallback=fallback,
        network="online",
        events=events,
        breaker=DegradationBreaker(clock=clock, events=events),
        criteria=config.criteria,
        timeout_ms=config.timeout_ms,
    )
