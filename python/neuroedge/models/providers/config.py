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
    # api_base = "https://openrouter.ai/api/v1" · threshold = 0.8 · timeout_ms = 1500
    # [system_one.options]                 # passed to a custom adapter only

No table ⇒ that system stays as before: System 2 offline, System 1 on the local
command grammar alone (Q-14). The key itself never goes in `agent.toml`: the file
is committed and shared, so a key field is a build error that does not repeat the
value. `[system_one]` names its criteria explicitly — a model reading what a guest
said never decides a criterion nobody delegated to it (the build checks each name
against the agent's gates, `engine/compiler.py`).
"""

from __future__ import annotations

import importlib
import math
import re
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ...errors import AgentManifestError

LITELLM = "litellm"
SYSTEMONE = "systemone"
PYTHON_PREFIX = "python:"
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
DEFAULT_TIMEOUT_MS = 1500.0
MAX_TIMEOUT_MS = 10_000.0
# Set by the dispatcher (Q-24): who called is never a model's judgment.
RUNTIME_CRITERIA = frozenset({"call_source"})
# Field names that hold a secret. Checked in the table and in `options`.
SECRET = re.compile(r"(^|_)(api_?key|key|secret|token|password)$", re.IGNORECASE)
ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
ADAPTER = re.compile(r"^[A-Za-z_][\w.]*:[A-Za-z_]\w*$")
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


def suggested_key_env(model: str) -> str:
    for prefix, name in _KEY_ENV_BY_PREFIX.items():
        if model.startswith(prefix):
            return name
    return "OPENAI_API_KEY"


def suggested_system_one_key_env(api_base: Any) -> str:
    """TypeSafe's own endpoint takes its key; OpenRouter (the default) takes OpenRouter's."""
    if isinstance(api_base, str) and "typesafe.ai" in api_base:
        return "TYPESAFE_API_KEY"
    return "OPENROUTER_API_KEY"


def _secret_fields(table: dict[str, Any], prefix: str = "") -> list[str]:
    found = []
    for key, value in table.items():
        if key == "api_key_env":
            continue
        if SECRET.search(key):
            found.append(prefix + key)
        elif isinstance(value, dict):
            found += _secret_fields(value, f"{prefix}{key}.")
    return found


def _number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _shown(value: Any) -> str:
    """A number as written; anything else by its type only — a pasted key is never echoed."""
    return repr(value) if isinstance(value, int | float) else f"a {type(value).__name__}"


def _is_adapter(provider: Any) -> bool:
    return (
        isinstance(provider, str)
        and provider.startswith(PYTHON_PREFIX)
        and ADAPTER.match(provider[len(PYTHON_PREFIX) :]) is not None
    )


def _refuse_secrets(table: dict[str, Any], where: str, key_env: str) -> None:
    secrets = _secret_fields(table)
    if secrets:
        # Never repeat the value: it may be a live key.
        raise AgentManifestError(
            where=f"{where} {secrets[0]}",
            why="an API key must never be written in agent.toml — the file is committed and "
            "shared, so the key would leak with it",
            how=f"delete `{secrets[0]}`, put the key in an environment variable and name it: "
            f'api_key_env = "{key_env}"',
        )


def _key_env(table: dict[str, Any], where: str, key_env: str) -> str | None:
    api_key_env = table.get("api_key_env")
    if api_key_env is not None and (
        not isinstance(api_key_env, str) or not ENV_NAME.match(api_key_env)
    ):
        # Not echoed: a value that is not a variable name may be the key itself.
        raise AgentManifestError(
            where=f"{where} api_key_env",
            why="api_key_env must be the NAME of an environment variable (letters, digits, _); "
            "the value given is not one — if it is the key itself, revoke it",
            how=f'write api_key_env = "{key_env}" and export the key in that variable',
        )
    return api_key_env


def _api_base(table: dict[str, Any], where: str, example: str) -> str | None:
    api_base = table.get("api_base")
    if api_base is not None and (
        not isinstance(api_base, str) or not api_base.startswith(("http://", "https://"))
    ):
        raise AgentManifestError(
            where=f"{where} api_base",
            why="api_base must be an http(s) URL",
            how=f'write api_base = "{example}", or remove it',
        )
    return api_base


def _options(table: dict[str, Any], where: str, name: str, builtin: str | None) -> dict:
    """`[<name>.options]`: a table, and only for a custom adapter (`builtin` is the other)."""
    options = table.get("options", {})
    if not isinstance(options, dict):
        raise AgentManifestError(
            where=f"{where} options",
            why="options must be a table",
            how=f"write [{name}.options]",
        )
    if options and builtin is not None:
        raise AgentManifestError(
            where=f"{where} options",
            why=f"[{name}.options] is for a custom adapter; the {builtin} provider takes only "
            f"the fields of [{name}]",
            how=f'remove [{name}.options], or use provider = "python:..."',
        )
    return dict(options)


def parse_system_two(table: Any, source: Path | None = None) -> SystemTwoConfig:
    """A validated `SystemTwoConfig`; `AgentManifestError` naming the first bad field."""
    where = f"{source} -> [system_two]" if source else "[system_two]"
    if not isinstance(table, dict):
        raise AgentManifestError(where=where, why="[system_two] must be a table", how="")
    _refuse_secrets(table, where, suggested_key_env(str(table.get("model", ""))))
    unknown = sorted(set(table) - set(KEYS))
    if unknown:
        raise AgentManifestError(
            where=f"{where} {unknown[0]}",
            why=f"{unknown} are not fields of [system_two]; it takes {list(KEYS)}",
            how="remove them, or put adapter settings under [system_two.options]",
        )
    provider = table.get("provider", LITELLM)
    if provider != LITELLM and not _is_adapter(provider):
        raise AgentManifestError(
            where=f"{where} provider",
            why=f'provider must be "{LITELLM}" or "{PYTHON_PREFIX}<module>:<factory>", '
            f"found {provider!r}",
            how='write provider = "litellm", or provider = "python:my_llm.adapter:make_provider" '
            "for your own adapter (FR-MDL-08)",
        )
    model = table.get("model", "")
    if not isinstance(model, str) or (provider == LITELLM and not model.strip()):
        raise AgentManifestError(
            where=f"{where} model",
            why="the LiteLLM provider needs a string `model`",
            how='write model = "anthropic/claude-sonnet-5" (or "openai/gpt-4o-mini")',
        )
    api_key_env = _key_env(table, where, suggested_key_env(model))
    api_base = _api_base(table, where, "http://localhost:11434")
    if provider == LITELLM and api_key_env is None and api_base is None:
        raise AgentManifestError(
            where=f"{where} api_key_env",
            why="a cloud model needs a key, and [system_two] does not say where to read it",
            how=f'add api_key_env = "{suggested_key_env(model)}" (a keyless local server: set '
            "api_base instead)",
        )
    timeout = table.get("timeout_s", DEFAULT_TIMEOUT_S)
    if not _number(timeout) or not 0 < timeout <= MAX_TIMEOUT_S:
        raise AgentManifestError(
            where=f"{where} timeout_s",
            why=f"timeout_s must be a number of seconds in (0, {MAX_TIMEOUT_S:g}], found {timeout!r}",
            how=f"write timeout_s = {DEFAULT_TIMEOUT_S:g}",
        )
    max_tokens = table.get("max_tokens")
    if max_tokens is not None and (
        isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or max_tokens <= 0
    ):
        raise AgentManifestError(
            where=f"{where} max_tokens",
            why=f"max_tokens must be a positive integer, found {max_tokens!r}",
            how="write max_tokens = 512, or remove it",
        )
    temperature = table.get("temperature")
    if temperature is not None and (not _number(temperature) or not 0 <= temperature <= 2):
        raise AgentManifestError(
            where=f"{where} temperature",
            why=f"temperature must be a number from 0 to 2, found {temperature!r}",
            how="write temperature = 0.2, or remove it",
        )
    options = _options(table, where, "system_two", "LiteLLM" if provider == LITELLM else None)
    return SystemTwoConfig(
        provider=provider,
        model=model,
        api_key_env=api_key_env,
        api_base=api_base,
        timeout_s=float(timeout),
        max_tokens=max_tokens,
        temperature=None if temperature is None else float(temperature),
        options=options,
        source=source,
    )


def _criteria(table: dict[str, Any], where: str) -> tuple[str, ...]:
    criteria = table.get("criteria")
    if (
        not isinstance(criteria, list)
        or not criteria
        or not all(isinstance(name, str) and name.strip() for name in criteria)
    ):
        raise AgentManifestError(
            where=f"{where} criteria",
            why="[system_one] must list the gate criteria the model may decide, as a non-empty "
            "list of names — nothing is delegated to a cloud model by default",
            how='write criteria = ["request_kind"] with criteria of your gates that the words '
            "alone can settle; session facts (identity, booking) stay in the property system",
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
    if not isinstance(table, dict):
        raise AgentManifestError(
            where=where,
            why="[system_one] must be a table",
            how='write [system_one] with model = "typesafe/jev-1.13"',
        )
    key_env = suggested_system_one_key_env(table.get("api_base"))
    _refuse_secrets(table, where, key_env)
    unknown = sorted(set(table) - set(SYSTEM_ONE_KEYS))
    if unknown:
        raise AgentManifestError(
            where=f"{where} {unknown[0]}",
            why=f"{unknown} are not fields of [system_one]; it takes {list(SYSTEM_ONE_KEYS)}",
            how="remove them, or put adapter settings under [system_one.options]",
        )
    provider = table.get("provider", SYSTEMONE)
    if provider != SYSTEMONE and not _is_adapter(provider):
        raise AgentManifestError(
            where=f"{where} provider",
            why=f'provider must be "{SYSTEMONE}" (the System One API of TypeSafe / OpenRouter) '
            f'or "{PYTHON_PREFIX}<module>:<factory>", found {provider!r}',
            how='write provider = "systemone", or provider = "python:my_s1.adapter:make_source" '
            "for your own adapter (FR-MDL-08)",
        )
    model = table.get("model", "")
    if not isinstance(model, str) or (provider == SYSTEMONE and not model.strip()):
        raise AgentManifestError(
            where=f"{where} model",
            why="the System One provider needs a string `model`",
            how='write model = "typesafe/jev-1.13" (Q-4)',
        )
    api_key_env = _key_env(table, where, key_env)
    api_base = _api_base(table, where, DEFAULT_SYSTEM_ONE_BASE)
    if provider == SYSTEMONE and api_key_env is None and api_base is None:
        raise AgentManifestError(
            where=f"{where} api_key_env",
            why="a cloud model needs a key, and [system_one] does not say where to read it",
            how=f'add api_key_env = "{key_env}" (a keyless local server: set api_base instead)',
        )
    criteria = _criteria(table, where)
    threshold = table.get("threshold", DEFAULT_THRESHOLD)
    if not _number(threshold) or not 0 < threshold <= 1:
        raise AgentManifestError(
            where=f"{where} threshold",
            why=f"threshold must be a confidence in (0, 1], found {_shown(threshold)}; below it the "
            "model's answer is not used and the command grammar is asked instead",
            how=f"write threshold = {DEFAULT_THRESHOLD:g}",
        )
    timeout = table.get("timeout_ms", DEFAULT_TIMEOUT_MS)
    if not _number(timeout) or not 0 < timeout <= MAX_TIMEOUT_MS:
        raise AgentManifestError(
            where=f"{where} timeout_ms",
            why=f"timeout_ms must be a number of milliseconds in (0, {MAX_TIMEOUT_MS:g}], "
            f"found {_shown(timeout)}",
            how=f"write timeout_ms = {DEFAULT_TIMEOUT_MS:g}",
        )
    options = _options(table, where, "system_one", "System One" if provider == SYSTEMONE else None)
    return SystemOneConfig(
        provider=provider,
        model=model,
        api_key_env=api_key_env,
        api_base=api_base,
        criteria=criteria,
        threshold=float(threshold),
        timeout_ms=float(timeout),
        options=options,
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


def load_adapter(config: SystemTwoConfig | SystemOneConfig, root: Path | None = None) -> Any:
    """
    The factory named by ``provider = "python:pkg.mod:factory"``. The module is
    imported as is, or from the agent's directory (`root`) — an adapter the user
    wrote runs without touching NeuroEdge (FR-MDL-08).
    """
    spec = config.adapter
    if spec is None:
        raise ValueError("not a custom adapter")
    module_name, _, attribute = spec.partition(":")
    where = f"{config.where} provider"
    added = root is not None and str(root) not in sys.path
    if added:
        sys.path.insert(0, str(root))
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        raise AgentManifestError(
            where=where,
            why=f"cannot import the adapter module {module_name!r}: {type(exc).__name__}: {exc}",
            how="put the module next to agent.toml or install it, and check the dotted path",
        ) from exc
    finally:
        if added:
            sys.path.remove(str(root))
    factory = getattr(module, attribute, None)
    if not callable(factory):
        raise AgentManifestError(
            where=where,
            why=f"{module_name!r} has no callable {attribute!r}",
            how=f"define def {attribute}(config): return <a provider> in {module_name}",
        )
    return factory
