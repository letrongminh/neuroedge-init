"""
What every provider table of agent.toml shares — `[system_two]`, `[system_one]`,
`[stt]` and `[tts]` (TSK-S2-11, TSK-I4-02, TSK-S3-13, Q-12, FR-DX-04).

One set of checks, so the four tables cannot disagree:

* **no key in the file** — a field named like a secret, or a value shaped like a
  key (`KEY_LIKE`, matched anywhere in it), is refused, and a refused value is
  **never repeated** in the error: it may be a live key (`shown`);
* **one endpoint check** (`endpoint`) — an http(s) URL with a host and a valid
  port; no credentials, query, fragment or key-shaped part; and never clear text
  to another machine when it would carry a key (or, for `[system_one]`, at all:
  a man in the middle would decide the gate's facts). "This machine" is
  `localhost` or a loopback IP literal (`is_loopback`), never a DNS name that
  merely starts with ``127.``;
* **one adapter loader** (`load_adapter`, `call_adapter`) for
  ``provider = "python:pkg.mod:factory"`` (FR-MDL-08).

Every check raises `AgentManifestError` with where / why / how.
"""

from __future__ import annotations

import importlib
import ipaddress
import math
import re
import sys
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlsplit

from ...errors import AgentManifestError

PYTHON_PREFIX = "python:"
ADAPTER = re.compile(r"^[A-Za-z_][\w.]*:[A-Za-z_]\w*$")
ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
# Field names that hold a secret. Checked in the table and in `options`.
SECRET = re.compile(r"(^|_)(api_?key|key|secret|token|password)$", re.IGNORECASE)
# A value shaped like an API key, anywhere in a string: OpenAI / Anthropic /
# OpenRouter `sk-…`, Groq `gsk_…`, Hugging Face `hf_…`, `pk-`/`rk-`, or one run of
# 40+ token characters (a bare token). Model ids, voices and hosts are shorter.
KEY_LIKE = re.compile(
    r"(?<![A-Za-z0-9])(?:sk|gsk|pk|rk|hf)[-_][A-Za-z0-9_-]{8,}|[A-Za-z0-9_-]{40,}"
)
# A model id: `typesafe/jev-1.13`, `anthropic/claude-sonnet-5`, `whisper-1`,
# `bedrock/anthropic.claude-3-sonnet-20240229-v1:0`. No space, no CR/LF.
MODEL_ID = re.compile(r"[A-Za-z0-9_.:/@+-]{1,128}")
# A field or criterion name that is safe to repeat in an error.
NAME = re.compile(r"[A-Za-z0-9_.-]{1,64}")


class AdapterConfig(Protocol):
    """A config that may name a custom adapter: every provider config is one."""

    @property
    def adapter(self) -> str | None: ...

    @property
    def where(self) -> str: ...


def looks_like_key(value: Any) -> bool:
    return isinstance(value, str) and KEY_LIKE.search(value) is not None


def shown(value: Any) -> str:
    """A number as written; anything else by its type only — a pasted key is never echoed."""
    if isinstance(value, int | float):
        return repr(value)
    return f"a {type(value).__name__}"


def safe_name(value: Any) -> str:
    """A name as written when it is plainly a name; otherwise said without repeating it."""
    if isinstance(value, str) and NAME.fullmatch(value) and not looks_like_key(value):
        return repr(value)
    return "a name not repeated here (it may be a key)"


def number(value: Any) -> bool:
    """A finite int or float — not a bool, NaN or inf."""
    return (
        isinstance(value, int | float)
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def secret_fields(table: Mapping[str, Any], prefix: str = "") -> list[str]:
    """Every field (in `options` too) named like a secret, other than `api_key_env`."""
    found = []
    for key, value in table.items():
        if key == "api_key_env":
            continue
        if SECRET.search(str(key)):
            found.append(prefix + str(key))
        elif isinstance(value, Mapping):
            found += secret_fields(value, f"{prefix}{key}.")
    return found


def refuse_secrets(table: Mapping[str, Any], where: str, key_env: str) -> None:
    secrets = secret_fields(table)
    if secrets:
        # Never repeat the value: it may be a live key.
        raise AgentManifestError(
            where=f"{where} {secrets[0]}",
            why="an API key must never be written in agent.toml — the file is committed and "
            "shared, so the key would leak with it",
            how=f"delete `{secrets[0]}`, put the key in an environment variable and name it: "
            f'api_key_env = "{key_env}"',
        )


def refuse_unknown(
    table: Mapping[str, Any], where: str, name: str, keys: Iterable[str], how: str
) -> None:
    keys = tuple(keys)
    unknown = sorted((str(key) for key in set(table) - set(keys)), key=str)
    if unknown:
        listed = ", ".join(safe_name(key) for key in unknown)
        first = unknown[0] if NAME.fullmatch(unknown[0]) and not looks_like_key(unknown[0]) else "?"
        raise AgentManifestError(
            where=f"{where} {first}",
            why=f"{listed}: not fields of [{name}]; it takes {list(keys)}",
            how=how,
        )


def key_env(table: Mapping[str, Any], where: str, suggestion: str) -> str | None:
    """`api_key_env`: the NAME of a variable, or None. Never echoed when it is not one."""
    value = table.get("api_key_env")
    if value is not None and (not isinstance(value, str) or not ENV_NAME.match(value)):
        raise AgentManifestError(
            where=f"{where} api_key_env",
            why="api_key_env must be the NAME of an environment variable (letters, digits, _); "
            "the value given is not one — if it is the key itself, revoke it",
            how=f'write api_key_env = "{suggestion}" and export the key in that variable',
        )
    return value


def is_adapter(provider: Any) -> bool:
    return (
        isinstance(provider, str)
        and provider.startswith(PYTHON_PREFIX)
        and ADAPTER.match(provider[len(PYTHON_PREFIX) :]) is not None
    )


def provider_of(
    table: Mapping[str, Any], where: str, builtin: str, what: str, example_adapter: str
) -> str:
    """`provider`: `builtin` (the default) or ``python:<module>:<factory>``. Never echoed."""
    provider = table.get("provider", builtin)
    if provider != builtin and not is_adapter(provider):
        raise AgentManifestError(
            where=f"{where} provider",
            why=f'provider must be "{builtin}" ({what}) or "{PYTHON_PREFIX}<module>:<factory>", '
            "and the value given is neither (not repeated here: it may be a key)",
            how=f'write provider = "{builtin}", or provider = "{example_adapter}" for your own '
            "adapter (FR-MDL-08)",
        )
    return provider


def model_id(table: Mapping[str, Any], where: str, *, required: bool, why: str, how: str) -> str:
    """`model`: a model id (`MODEL_ID`), never shaped like a key; "" only when not required."""
    model = table.get("model", "")
    if not isinstance(model, str) or (required and not model.strip()):
        raise AgentManifestError(where=f"{where} model", why=why, how=how)
    if model and (not MODEL_ID.fullmatch(model) or looks_like_key(model)):
        # The model is printed and traced: a key pasted here would leak with it.
        raise AgentManifestError(
            where=f"{where} model",
            why="model must be a model id (letters, digits and . _ : / @ + -, no spaces or line "
            "breaks); the value given is not one, or looks like an API key — if it is the key "
            "itself, revoke it",
            how=how,
        )
    return model


def plain_text(
    table: Mapping[str, Any], where: str, field: str, *, required: bool, why: str, how: str
) -> str | None:
    """A short name that is not an id (a TTS voice, ``af_bella+af_sky``): no control
    characters, at most 100 characters, never shaped like a key."""
    value = table.get(field)
    if value is None and not required:
        return None
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > 100
        or any(ord(ch) < 32 or ord(ch) == 127 for ch in value)
        or looks_like_key(value)
    ):
        raise AgentManifestError(where=f"{where} {field}", why=why, how=how)
    return value


def bounded(
    table: Mapping[str, Any],
    where: str,
    field: str,
    *,
    default: float,
    low: float,
    high: float,
    unit: str,
    low_inclusive: bool = False,
    why: str = "",
) -> float:
    """A number in (low, high] — or [low, high] — else an error that shows it only if it is one."""
    value = table.get(field, default)
    inside = number(value) and (value >= low if low_inclusive else value > low) and value <= high
    if not inside:
        interval = f"{'[' if low_inclusive else '('}{low:g}, {high:g}]"
        raise AgentManifestError(
            where=f"{where} {field}",
            why=f"{field} must be {unit} in {interval}, found {shown(value)}"
            + (f"; {why}" if why else ""),
            how=f"write {field} = {default:g}",
        )
    return float(value)


def options(table: Mapping[str, Any], where: str, name: str, builtin: str | None) -> dict[str, Any]:
    """`[<name>.options]`: a table, and only for a custom adapter (`builtin` is the other kind)."""
    value = table.get("options", {})
    if not isinstance(value, dict):
        raise AgentManifestError(
            where=f"{where} options", why="options must be a table", how=f"write [{name}.options]"
        )
    if value and builtin is not None:
        raise AgentManifestError(
            where=f"{where} options",
            why=f"[{name}.options] is for a custom adapter; the {builtin} provider takes only "
            f"the fields of [{name}]",
            how=f'remove [{name}.options], or use provider = "python:..."',
        )
    return dict(value)


# --- endpoints -------------------------------------------------------------------------------


def is_loopback(url: str) -> bool:
    """This machine: `localhost`, or an IP literal in 127.0.0.0/8 or ::1 — never a DNS
    name that merely starts with "127." (``127.0.0.1.example.com`` is someone else)."""
    try:
        host = (urlsplit(url).hostname or "").lower().rstrip(".")
    except ValueError:
        return False
    if host == "localhost":
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    mapped = getattr(address, "ipv4_mapped", None)
    return (mapped or address).is_loopback


def endpoint(
    table: Mapping[str, Any],
    where: str,
    field: str,
    *,
    default: str | None,
    example: str,
    keyed: bool,
    tls_always: bool = False,
    exposes: str = "the key",
) -> str | None:
    """
    `field` (`api_base`, `base_url`) as a checked http(s) URL, or `default` when absent.
    Refused: not a URL, no host, a port that is not one, credentials, a query, a
    fragment, a key-shaped part — and plain http:// to another machine when the call
    carries a key (`keyed`) or when `tls_always`. The value is never repeated.
    """
    if field not in table:
        return default
    url = table[field]
    bad = AgentManifestError(
        where=f"{where} {field}",
        why=f"{field} must be an http(s) URL with a host (and, if any, a valid port)",
        how=f'write {field} = "{example}", or remove it',
    )
    if not isinstance(url, str) or any(ord(ch) <= 32 or ord(ch) == 127 for ch in url):
        raise bad
    try:
        parts = urlsplit(url)
        parts.port  # noqa: B018 — raises ValueError for a port that is not one
    except ValueError:
        raise bad from None
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise bad
    if parts.username or parts.password or parts.query or parts.fragment or looks_like_key(url):
        # Not echoed: a URL with credentials or a query may carry the key itself.
        raise AgentManifestError(
            where=f"{where} {field}",
            why=f"{field} must not carry credentials, a query, a fragment or a key-shaped part — "
            "the URL is shown in errors and banners, so a key in it would leak",
            how=f'write the plain endpoint ("{example}") and name the key\'s variable in '
            "api_key_env",
        )
    if parts.scheme == "http" and not is_loopback(url) and (keyed or tls_always):
        raise AgentManifestError(
            where=f"{where} {field}",
            why=f"{field} is plain http:// to {parts.hostname}, another machine: {exposes} "
            "would cross the network in clear text",
            how="use https://, or a server on this machine (http://localhost…, http://127.0.0.1…)",
        )
    return url


# --- custom adapters (FR-MDL-08) ---------------------------------------------------------------


def load_adapter(config: AdapterConfig, root: Path | None = None) -> Callable[..., Any]:
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


def call_adapter(
    config: AdapterConfig,
    root: Path | None,
    *,
    table: str,
    accepts: Callable[[Any], bool],
    expected: str,
    how: str,
) -> Any:
    """
    ``factory(config)`` of a custom adapter, checked: a factory that raises, or returns
    what `accepts` refuses (it should be `expected`), is a three-part error at load time.
    """
    factory = load_adapter(config, root)
    try:
        made = factory(config)
    except Exception as exc:
        raise AgentManifestError(
            where=f"{config.where} provider",
            why=f"the adapter factory {config.adapter!r} raised {type(exc).__name__}: {exc}",
            how=f"fix the adapter; it is called once, with the [{table}] config",
        ) from exc
    if not accepts(made):
        raise AgentManifestError(
            where=f"{config.where} provider",
            why=f"the adapter factory {config.adapter!r} returned {type(made).__name__}, "
            f"not {expected}",
            how=how,
        )
    return made
