"""
The `[system_two]` and `[system_one]` tables of `agent.toml` — which models answer
(Q-4, Q-10, Q-12, FR-MDL-04).

    [system_two]
    provider    = "litellm"                    # or "python:my_pkg.llm:make_provider"
    model       = "anthropic/claude-sonnet-5"  # a LiteLLM model name
    api_key_env = "ANTHROPIC_API_KEY"          # the NAME of the variable, never the key
    # api_base = "http://localhost:11434"  · timeout_s = 20 · max_tokens = 512 · temperature = 0.2
    # [system_two.options]                 # passed to a custom adapter only

    [system_one]
    provider    = "systemone"                  # or "python:my_pkg.s1:make_source"
    model       = "typesafe/jev-1.13"          # Jev (Q-4), through OpenRouter
    api_key_env = "OPENROUTER_API_KEY"
    criteria    = ["request_kind"]             # the ONLY criteria the model may decide
    # api_base = "https://openrouter.ai/api/v1" · threshold = 0.8 (≥ 0.5) · timeout_ms = 1500
    # [system_one.options]                 # passed to a custom adapter only

No table ⇒ that system stays as before: System 2 offline, System 1 on the local
command grammar alone (Q-14). What the tables share — no key in the file, a
refused value never repeated, one endpoint check, the adapter loader — is
`common.py`. `[system_one]` names its criteria explicitly: a model reading what a
person said never decides a criterion nobody delegated to it, and the build refuses
one the agent computes itself or its gates cannot ask (`engine/compiler.py`). Its
`api_base` is https (or this machine) even without a key: a man in the middle
would decide the gate's facts.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ...errors import AgentManifestError
from .common import (
    ADAPTER,
    ENV_NAME,
    KEY_LIKE,
    MODEL_ID,
    NAME,
    PYTHON_PREFIX,
    SECRET,
    AdapterConfig,
    bounded,
    endpoint,
    is_loopback,
    key_env,
    load_adapter,
    looks_like_key,
    model_id,
    number,
    options,
    provider_of,
    refuse_secrets,
    refuse_unknown,
    secret_fields,
    shown,
)

__all__ = [
    "ADAPTER",
    "ENV_NAME",
    "KEY_LIKE",
    "MODEL_ID",
    "PYTHON_PREFIX",
    "SECRET",
    "AdapterConfig",
    "SystemOneConfig",
    "SystemTwoConfig",
    "is_loopback",
    "load_adapter",
    "load_system_one_config",
    "load_system_two_config",
    "number",
    "parse_system_one",
    "parse_system_two",
    "secret_fields",
    "shown",
]

LITELLM = "litellm"
SYSTEMONE = "systemone"
DEFAULT_TIMEOUT_S = 20.0
MAX_TIMEOUT_S = 120.0
KEYS = (
    "provider",
    "model",
    "api_key_env",
    "api_base",
    "timeout_s",
    "max_tokens",
    "temperature",
    "options",
)
# `[system_one]`: the System One API (TypeSafe's, served by OpenRouter at the same path).
SYSTEM_ONE_KEYS = (
    "provider",
    "model",
    "api_key_env",
    "api_base",
    "criteria",
    "threshold",
    "timeout_ms",
    "options",
)
DEFAULT_SYSTEM_ONE_BASE = "https://openrouter.ai/api/v1"
DEFAULT_THRESHOLD = 0.8
# The lowest threshold `[system_one]` accepts. At 0.5 a choice's winner holds at least
# half the probability — more than all the other options together — and a noul is at
# least 3:1 (P ≥ 0.75 or ≤ 0.25); TypeSafe calls anything under 0.5 "genuinely unsure"
# (docs.typesafe.ai/confidence). A gate that needs more says so with `confidence_gte`.
MIN_THRESHOLD = 0.5
DEFAULT_TIMEOUT_MS = 1500.0
MAX_TIMEOUT_MS = 10_000.0
# Set by the dispatcher (Q-24): who called is never a model's judgment.
RUNTIME_CRITERIA = frozenset({"call_source"})
_KEY_ENV_BY_PREFIX = {
    "anthropic/": "ANTHROPIC_API_KEY",
    "claude": "ANTHROPIC_API_KEY",
    "openai/": "OPENAI_API_KEY",
    "gpt-": "OPENAI_API_KEY",
    "gemini/": "GEMINI_API_KEY",
}


@dataclass(frozen=True)
class SystemTwoConfig:
    provider: str = LITELLM
    model: str = ""
    api_key_env: str | None = None
    api_base: str | None = None
    timeout_s: float = DEFAULT_TIMEOUT_S
    max_tokens: int | None = None
    temperature: float | None = None
    options: dict[str, Any] = field(default_factory=dict)
    source: Path | None = None

    @property
    def where(self) -> str:
        return f"{self.source} -> [system_two]" if self.source else "[system_two]"

    @property
    def adapter(self) -> str | None:
        """``pkg.mod:factory`` for a custom adapter, else None."""
        if self.provider.startswith(PYTHON_PREFIX):
            return self.provider[len(PYTHON_PREFIX) :]
        return None


@dataclass(frozen=True)
class SystemOneConfig:
    """`[system_one]`: the cloud primary of `SystemOne`; the grammar stays its fallback."""

    provider: str = SYSTEMONE
    model: str = ""
    api_key_env: str | None = None
    api_base: str | None = None
    criteria: tuple[str, ...] = ()
    threshold: float = DEFAULT_THRESHOLD
    timeout_ms: float = DEFAULT_TIMEOUT_MS
    options: dict[str, Any] = field(default_factory=dict)
    source: Path | None = None

    @property
    def where(self) -> str:
        return f"{self.source} -> [system_one]" if self.source else "[system_one]"

    @property
    def adapter(self) -> str | None:
        """``pkg.mod:factory`` for a custom adapter, else None."""
        if self.provider.startswith(PYTHON_PREFIX):
            return self.provider[len(PYTHON_PREFIX) :]
        return None

    @property
    def endpoint(self) -> str:
        """``POST`` here: ``{api_base}/systemone`` (TypeSafe and OpenRouter alike)."""
        return f"{(self.api_base or DEFAULT_SYSTEM_ONE_BASE).rstrip('/')}/systemone"


def suggested_key_env(model: Any) -> str:
    for prefix, name in _KEY_ENV_BY_PREFIX.items():
        if isinstance(model, str) and model.startswith(prefix):
            return name
    return "OPENAI_API_KEY"


def suggested_system_one_key_env(api_base: Any) -> str:
    """TypeSafe's own endpoint takes its key; OpenRouter (the default) takes OpenRouter's."""
    if isinstance(api_base, str) and "typesafe.ai" in api_base:
        return "TYPESAFE_API_KEY"
    return "OPENROUTER_API_KEY"


def _table(table: Any, where: str, name: str, how: str) -> dict[str, Any]:
    if not isinstance(table, dict):
        raise AgentManifestError(where=where, why=f"[{name}] must be a table", how=how)
    return table


def parse_system_two(table: Any, source: Path | None = None) -> SystemTwoConfig:
    """A validated `SystemTwoConfig`; `AgentManifestError` naming the first bad field."""
    where = f"{source} -> [system_two]" if source else "[system_two]"
    table = _table(table, where, "system_two", 'write [system_two] with model = "…"')
    suggestion = suggested_key_env(table.get("model", ""))
    refuse_secrets(table, where, suggestion)
    refuse_unknown(
        table,
        where,
        "system_two",
        KEYS,
        "remove them, or put adapter settings under [system_two.options]",
    )
    provider = provider_of(
        table,
        where,
        LITELLM,
        "any model LiteLLM routes",
        "python:my_llm.adapter:make_provider",
    )
    how_model = 'write model = "anthropic/claude-sonnet-5" (or "openai/gpt-4o-mini")'
    model = model_id(
        table,
        where,
        required=provider == LITELLM,
        why="the LiteLLM provider needs a string `model`",
        how=how_model,
    )
    api_key_env = key_env(table, where, suggestion)
    api_base = endpoint(
        table,
        where,
        "api_base",
        default=None,
        example="http://localhost:11434",
        keyed=api_key_env is not None,
    )
    if provider == LITELLM and api_key_env is None and api_base is None:
        raise AgentManifestError(
            where=f"{where} api_key_env",
            why="a cloud model needs a key, and [system_two] does not say where to read it",
            how=f'add api_key_env = "{suggestion}" (a keyless local server: set api_base instead)',
        )
    timeout = bounded(
        table,
        where,
        "timeout_s",
        default=DEFAULT_TIMEOUT_S,
        low=0,
        high=MAX_TIMEOUT_S,
        unit="a number of seconds",
    )
    max_tokens = table.get("max_tokens")
    if max_tokens is not None and (
        isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or max_tokens <= 0
    ):
        raise AgentManifestError(
            where=f"{where} max_tokens",
            why=f"max_tokens must be a positive integer, found {shown(max_tokens)}",
            how="write max_tokens = 512, or remove it",
        )
    temperature = None
    if "temperature" in table:
        temperature = bounded(
            table,
            where,
            "temperature",
            default=0.2,
            low=0,
            high=2,
            unit="a number",
            low_inclusive=True,
        )
    return SystemTwoConfig(
        provider=provider,
        model=model,
        api_key_env=api_key_env,
        api_base=api_base,
        timeout_s=timeout,
        max_tokens=max_tokens,
        temperature=temperature,
        options=options(table, where, "system_two", "LiteLLM" if provider == LITELLM else None),
        source=source,
    )


def _criteria(table: dict[str, Any], where: str) -> tuple[str, ...]:
    criteria = table.get("criteria")
    if (
        not isinstance(criteria, list)
        or not criteria
        or not all(
            isinstance(name, str) and NAME.fullmatch(name) and not looks_like_key(name)
            for name in criteria
        )
    ):
        raise AgentManifestError(
            where=f"{where} criteria",
            why="[system_one] must list the gate criteria the model may decide, as a non-empty "
            "list of criterion names — nothing is delegated to a cloud model by default",
            how='write criteria = ["request_kind"] with criteria of your gates that the words '
            "alone can settle. Never delegate identity, authorization or booking criteria "
            "(guest_authenticated, staff_co_authorized, room_matches): they are session facts "
            "from the property system — facts in the context always win over the model, and one "
            "missing from it would otherwise be decided from the person's words",
        )
    repeated = sorted({name for name in criteria if criteria.count(name) > 1})
    if repeated:
        raise AgentManifestError(
            where=f"{where} criteria",
            why=f"{repeated} are listed more than once",
            how="list each criterion once",
        )
    runtime = sorted(set(criteria) & RUNTIME_CRITERIA)
    if runtime:
        raise AgentManifestError(
            where=f"{where} criteria",
            why=f"{runtime} is set by the dispatcher for every tool call (Q-24); who called is "
            "never a model's judgment",
            how=f"remove {runtime[0]!r} from criteria",
        )
    return tuple(criteria)


def parse_system_one(table: Any, source: Path | None = None) -> SystemOneConfig:
    """A validated `SystemOneConfig`; `AgentManifestError` naming the first bad field."""
    where = f"{source} -> [system_one]" if source else "[system_one]"
    table = _table(
        table, where, "system_one", 'write [system_one] with model = "typesafe/jev-1.13"'
    )
    suggestion = suggested_system_one_key_env(table.get("api_base"))
    refuse_secrets(table, where, suggestion)
    refuse_unknown(
        table,
        where,
        "system_one",
        SYSTEM_ONE_KEYS,
        "remove them, or put adapter settings under [system_one.options]",
    )
    provider = provider_of(
        table,
        where,
        SYSTEMONE,
        "the System One API of TypeSafe / OpenRouter",
        "python:my_s1.adapter:make_source",
    )
    model = model_id(
        table,
        where,
        required=provider == SYSTEMONE,
        why="the System One provider needs a string `model`",
        how=f'write model = "typesafe/jev-1.13" (Q-4) and api_key_env = "{suggestion}"',
    )
    api_key_env = key_env(table, where, suggestion)
    api_base = endpoint(
        table,
        where,
        "api_base",
        default=None,
        example=DEFAULT_SYSTEM_ONE_BASE,
        keyed=api_key_env is not None,
        tls_always=True,
        exposes="what the person said and the answers that decide gate facts (which anyone on "
        "the path could forge)",
    )
    if provider == SYSTEMONE and api_key_env is None and api_base is None:
        raise AgentManifestError(
            where=f"{where} api_key_env",
            why="a cloud model needs a key, and [system_one] does not say where to read it",
            how=f'add api_key_env = "{suggestion}" (a keyless local server: set api_base instead)',
        )
    criteria = _criteria(table, where)
    threshold = bounded(
        table,
        where,
        "threshold",
        default=DEFAULT_THRESHOLD,
        low=MIN_THRESHOLD,
        high=1,
        unit="a confidence",
        low_inclusive=True,
        why="below it the model's answer is not used and the command grammar is asked instead; "
        f"under {MIN_THRESHOLD:g} the model is unsure by its own account",
    )
    timeout = bounded(
        table,
        where,
        "timeout_ms",
        default=DEFAULT_TIMEOUT_MS,
        low=0,
        high=MAX_TIMEOUT_MS,
        unit="a number of milliseconds",
    )
    return SystemOneConfig(
        provider=provider,
        model=model,
        api_key_env=api_key_env,
        api_base=api_base,
        criteria=criteria,
        threshold=threshold,
        timeout_ms=timeout,
        options=options(
            table, where, "system_one", "System One" if provider == SYSTEMONE else None
        ),
        source=source,
    )


def load_system_two_config(manifest: Any) -> SystemTwoConfig | None:
    """The agent's `[system_two]`, or None when it has none (System 2 stays offline)."""
    document = tomllib.loads(manifest.source.read_text(encoding="utf-8"))
    if "system_two" not in document:
        return None
    return parse_system_two(document["system_two"], manifest.source)


def load_system_one_config(manifest: Any) -> SystemOneConfig | None:
    """The agent's `[system_one]`, or None when it has none (the grammar alone, Q-14)."""
    document = tomllib.loads(manifest.source.read_text(encoding="utf-8"))
    if "system_one" not in document:
        return None
    return parse_system_one(document["system_one"], manifest.source)
