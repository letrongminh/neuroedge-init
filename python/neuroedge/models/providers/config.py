"""
The `[system_two]` table of `agent.toml` — which model answers System 2 (Q-4, Q-10, Q-12).

    [system_two]
    provider    = "litellm"                    # or "python:my_pkg.llm:make_provider"
    model       = "anthropic/claude-sonnet-5"  # a LiteLLM model name
    api_key_env = "ANTHROPIC_API_KEY"          # the NAME of the variable, never the key
    # api_base = "http://localhost:11434"  · timeout_s = 20 · max_tokens = 512 · temperature = 0.2
    # [system_two.options]                 # passed to a custom adapter only

No table ⇒ System 2 stays offline, exactly as before. The key itself never
goes in `agent.toml`: the file is committed and shared, so a key field is a
build error that does not repeat the value.
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


def suggested_key_env(model: str) -> str:
    for prefix, name in _KEY_ENV_BY_PREFIX.items():
        if model.startswith(prefix):
            return name
    return "OPENAI_API_KEY"


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


def parse_system_two(table: Any, source: Path | None = None) -> SystemTwoConfig:
    """A validated `SystemTwoConfig`; `AgentManifestError` naming the first bad field."""
    where = f"{source} -> [system_two]" if source else "[system_two]"
    if not isinstance(table, dict):
        raise AgentManifestError(where=where, why="[system_two] must be a table", how="")
    secrets = _secret_fields(table)
    if secrets:
        # Never repeat the value: it may be a live key.
        raise AgentManifestError(
            where=f"{where} {secrets[0]}",
            why="an API key must never be written in agent.toml — the file is committed and "
            "shared, so the key would leak with it",
            how=f"delete `{secrets[0]}`, put the key in an environment variable and name it: "
            f'api_key_env = "{suggested_key_env(str(table.get("model", "")))}"',
        )
    unknown = sorted(set(table) - set(KEYS))
    if unknown:
        raise AgentManifestError(
            where=f"{where} {unknown[0]}",
            why=f"{unknown} are not fields of [system_two]; it takes {list(KEYS)}",
            how="remove them, or put adapter settings under [system_two.options]",
        )
    provider = table.get("provider", LITELLM)
    if not isinstance(provider, str) or not (
        provider == LITELLM
        or (provider.startswith(PYTHON_PREFIX) and ADAPTER.match(provider[len(PYTHON_PREFIX) :]))
    ):
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
    api_key_env = table.get("api_key_env")
    if api_key_env is not None and (
        not isinstance(api_key_env, str) or not ENV_NAME.match(api_key_env)
    ):
        # Not echoed: a value that is not a variable name may be the key itself.
        raise AgentManifestError(
            where=f"{where} api_key_env",
            why="api_key_env must be the NAME of an environment variable (letters, digits, _); "
            "the value given is not one — if it is the key itself, revoke it",
            how=f'write api_key_env = "{suggested_key_env(model)}" and export the key in that variable',
        )
    api_base = table.get("api_base")
    if api_base is not None and (
        not isinstance(api_base, str) or not api_base.startswith(("http://", "https://"))
    ):
        raise AgentManifestError(
            where=f"{where} api_base",
            why="api_base must be an http(s) URL",
            how='write api_base = "http://localhost:11434", or remove it',
        )
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
    options = table.get("options", {})
    if not isinstance(options, dict):
        raise AgentManifestError(
            where=f"{where} options",
            why="options must be a table",
            how="write [system_two.options]",
        )
    if options and provider == LITELLM:
        raise AgentManifestError(
            where=f"{where} options",
            why="[system_two.options] is for a custom adapter; the LiteLLM provider takes only "
            "the fields of [system_two]",
            how='remove [system_two.options], or use provider = "python:..."',
        )
    return SystemTwoConfig(
        provider=provider,
        model=model,
        api_key_env=api_key_env,
        api_base=api_base,
        timeout_s=float(timeout),
        max_tokens=max_tokens,
        temperature=None if temperature is None else float(temperature),
        options=dict(options),
        source=source,
    )


def load_system_two_config(manifest: Any) -> SystemTwoConfig | None:
    """The agent's `[system_two]`, or None when it has none (System 2 stays offline)."""
    document = tomllib.loads(manifest.source.read_text(encoding="utf-8"))
    if "system_two" not in document:
        return None
    return parse_system_two(document["system_two"], manifest.source)


def load_adapter(config: SystemTwoConfig, root: Path | None = None) -> Any:
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
