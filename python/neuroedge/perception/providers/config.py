"""
`[stt]` and `[tts]` of `agent.toml` — which provider hears and which speaks
(TSK-S3-13, FR-MDL-09, Q-12).

    [stt]
    base_url    = "https://api.openai.com/v1"   # default; Groq, faster-whisper, … by URL
    model       = "whisper-1"
    language    = "vi"                          # ISO-639-1, optional
    timeout_s   = 15
    api_key_env = "OPENAI_API_KEY"              # the NAME of the variable, never the key

    [tts]
    base_url    = "http://localhost:8880/v1"    # e.g. Kokoro; a local server needs no key
    model       = "kokoro"
    voice       = "af_heart"
    timeout_s   = 15

`provider` is ``"openai"`` (the default: the OpenAI audio API, `openai_audio.py`)
or ``"python:pkg.mod:factory"`` — an adapter of your own, handed this config
and its `[stt.options]` / `[tts.options]` (FR-MDL-08, as `[system_two]`).

No table ⇒ no provider: `sim` stays on typed input, exactly as before (Q-15).
The key never goes in `agent.toml` — the same checks as `[system_two]`
(`models/providers/config.py`), and one more: a key is never sent over plain
``http://`` to a machine other than this one.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from ...errors import AgentManifestError
from ...models.providers.config import (
    ADAPTER,
    ENV_NAME,
    PYTHON_PREFIX,
    _number,
    _secret_fields,
)

OPENAI = "openai"
OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_TIMEOUT_S = 15.0
MAX_TIMEOUT_S = 120.0
ROLES = ("stt", "tts")
KEYS = {
    "stt": ("provider", "base_url", "model", "language", "timeout_s", "api_key_env", "options"),
    "tts": ("provider", "base_url", "model", "voice", "timeout_s", "api_key_env", "options"),
}
EXAMPLE_MODEL = {"stt": "whisper-1", "tts": "gpt-4o-mini-tts"}
LANGUAGE = re.compile(r"^[a-z]{2,3}$")
LOOPBACK = ("localhost", "127.0.0.1", "::1")


@dataclass(frozen=True)
class SpeechConfig:
    role: str  # "stt" | "tts"
    provider: str = OPENAI
    base_url: str = OPENAI_BASE_URL
    model: str = ""
    voice: str | None = None
    language: str | None = None
    timeout_s: float = DEFAULT_TIMEOUT_S
    api_key_env: str | None = None
    options: dict[str, Any] = field(default_factory=dict)
    source: Path | None = None

    @property
    def where(self) -> str:
        return f"{self.source} -> [{self.role}]" if self.source else f"[{self.role}]"

    @property
    def adapter(self) -> str | None:
        """``pkg.mod:factory`` for a custom adapter, else None."""
        if self.provider.startswith(PYTHON_PREFIX):
            return self.provider[len(PYTHON_PREFIX) :]
        return None

    @property
    def label(self) -> str:
        """Which provider, model and key — never the key (the banner's line)."""
        if self.adapter is not None:
            return f"adapter {self.adapter}"
        key = f"key from ${self.api_key_env}" if self.api_key_env else "no key"
        voice = f", voice {self.voice}" if self.voice else ""
        return f"{self.model}{voice} at {self.base_url} ({key})"


def _http_url(url: Any) -> bool:
    """An http(s) URL with a host and, if any, a valid port."""
    if not isinstance(url, str):
        return False
    try:
        parts = urlsplit(url)
        parts.port  # noqa: B018 — raises ValueError for a port that is not one
    except ValueError:
        return False
    return parts.scheme in ("http", "https") and bool(parts.hostname)


def _is_loopback(url: str) -> bool:
    host = (urlsplit(url).hostname or "").lower()
    return host in LOOPBACK or host.startswith("127.")


def parse_speech(role: str, table: Any, source: Path | None = None) -> SpeechConfig:
    """A validated `SpeechConfig`; `AgentManifestError` naming the first bad field."""
    if role not in ROLES:
        raise ValueError(f"role must be one of {ROLES}")
    name = f"[{role}]"
    where = f"{source} -> {name}" if source else name
    if not isinstance(table, dict):
        raise AgentManifestError(where=where, why=f"{name} must be a table", how=f"write {name}")
    secrets = _secret_fields(table)
    if secrets:
        # Never repeat the value: it may be a live key.
        raise AgentManifestError(
            where=f"{where} {secrets[0]}",
            why="an API key must never be written in agent.toml — the file is committed and "
            "shared, so the key would leak with it",
            how=f"delete `{secrets[0]}`, put the key in an environment variable and name it: "
            'api_key_env = "OPENAI_API_KEY"',
        )
    unknown = sorted(set(table) - set(KEYS[role]))
    if unknown:
        hint = (
            "the OpenAI speech API has no language field — pick a voice that speaks it, or pass "
            f"it to your adapter under [{role}.options]"
            if role == "tts" and "language" in unknown
            else f"remove them, or put adapter settings under [{role}.options]"
        )
        raise AgentManifestError(
            where=f"{where} {unknown[0]}",
            why=f"{unknown} are not fields of {name}; it takes {list(KEYS[role])}",
            how=hint,
        )
    provider = table.get("provider", OPENAI)
    if not isinstance(provider, str) or not (
        provider == OPENAI
        or (provider.startswith(PYTHON_PREFIX) and ADAPTER.match(provider[len(PYTHON_PREFIX) :]))
    ):
        raise AgentManifestError(
            where=f"{where} provider",
            why=f'provider must be "{OPENAI}" (the OpenAI audio API: OpenAI, Groq, faster-whisper, '
            f'Kokoro… by base_url) or "{PYTHON_PREFIX}<module>:<factory>", found {provider!r}',
            how=f'write provider = "{OPENAI}", or provider = "python:my_speech.adapter:make" for '
            "your own adapter (FR-MDL-09)",
        )
    custom = provider != OPENAI
    base_url = table.get("base_url", OPENAI_BASE_URL)
    if not _http_url(base_url):
        raise AgentManifestError(
            where=f"{where} base_url",
            why="base_url must be an http(s) URL with a host",
            how=f'write base_url = "{OPENAI_BASE_URL}" (or a local server, '
            '"http://localhost:8000/v1"), or remove it',
        )
    parts = urlsplit(base_url)
    if parts.username or parts.password or parts.query or parts.fragment:
        # Not echoed: a URL with credentials or a query may carry the key itself.
        raise AgentManifestError(
            where=f"{where} base_url",
            why="base_url must not carry credentials, a query or a fragment — the URL is shown in "
            "errors and banners, so a key in it would leak",
            how='write the plain endpoint ("https://host/v1") and name the key\'s variable in '
            "api_key_env",
        )
    base_url = base_url.rstrip("/")
    model = table.get("model", "")
    if not isinstance(model, str) or (not custom and not model.strip()):
        raise AgentManifestError(
            where=f"{where} model",
            why=f"the OpenAI audio API needs a string `model` in {name}",
            how=f'write model = "{EXAMPLE_MODEL[role]}" (or the model name your server serves)',
        )
    voice = table.get("voice")
    if role == "tts" and (
        (voice is not None and (not isinstance(voice, str) or not voice.strip()))
        or (voice is None and not custom)
    ):
        raise AgentManifestError(
            where=f"{where} voice",
            why="the OpenAI speech API needs a string `voice`",
            how='write voice = "alloy" (OpenAI), or the voice your server has (Kokoro: "af_heart")',
        )
    language = table.get("language")
    if language is not None and (not isinstance(language, str) or not LANGUAGE.match(language)):
        raise AgentManifestError(
            where=f"{where} language",
            why=f'language must be an ISO-639-1 code such as "vi" or "en", found {language!r}',
            how='write language = "vi", or remove it to let the model detect it',
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
            how='write api_key_env = "OPENAI_API_KEY" and export the key in that variable',
        )
    if not custom and api_key_env is None and "base_url" not in table:
        raise AgentManifestError(
            where=f"{where} api_key_env",
            why=f"{name} speaks to OpenAI's cloud, which needs a key, and does not say where to "
            "read it",
            how='add api_key_env = "OPENAI_API_KEY" (a keyless local server: set base_url instead)',
        )
    if (
        api_key_env is not None
        and urlsplit(base_url).scheme == "http"
        and not _is_loopback(base_url)
    ):
        raise AgentManifestError(
            where=f"{where} base_url",
            why="with api_key_env set, the key would cross the network in clear text to "
            f"{urlsplit(base_url).hostname}",
            how="use https://, or a server on this machine (http://localhost…), or drop "
            "api_key_env for a keyless server",
        )
    timeout = table.get("timeout_s", DEFAULT_TIMEOUT_S)
    if not _number(timeout) or not 0 < timeout <= MAX_TIMEOUT_S:
        raise AgentManifestError(
            where=f"{where} timeout_s",
            why=f"timeout_s must be a number of seconds in (0, {MAX_TIMEOUT_S:g}], found {timeout!r}",
            how=f"write timeout_s = {DEFAULT_TIMEOUT_S:g}",
        )
    options = table.get("options", {})
    if not isinstance(options, dict):
        raise AgentManifestError(
            where=f"{where} options", why="options must be a table", how=f"write [{role}.options]"
        )
    if options and not custom:
        raise AgentManifestError(
            where=f"{where} options",
            why=f"[{role}.options] is for a custom adapter; the OpenAI audio provider takes only "
            f"the fields of {name}",
            how=f'remove [{role}.options], or use provider = "python:..."',
        )
    return SpeechConfig(
        role=role,
        provider=provider,
        base_url=base_url,
        model=model,
        voice=voice,
        language=language,
        timeout_s=float(timeout),
        api_key_env=api_key_env,
        options=dict(options),
        source=source,
    )


def load_speech_configs(manifest: Any) -> tuple[SpeechConfig | None, SpeechConfig | None]:
    """The agent's `[stt]` and `[tts]`; None for a table it does not have."""
    document = tomllib.loads(manifest.source.read_text(encoding="utf-8"))
    return tuple(  # type: ignore[return-value]
        parse_speech(role, document[role], manifest.source) if role in document else None
        for role in ROLES
    )
