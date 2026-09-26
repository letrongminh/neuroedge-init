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
The checks are the ones every provider table shares (`models/providers/common.py`):
no key in the file, a refused value never repeated, one endpoint check — and a key
is never sent over plain ``http://`` to a machine other than this one.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ...errors import AgentManifestError
from ...models.providers.common import (
    PYTHON_PREFIX,
    bounded,
    endpoint,
    key_env,
    model_id,
    options,
    plain_text,
    provider_of,
    refuse_secrets,
    refuse_unknown,
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


def _unknown_hint(role: str, table: dict[str, Any]) -> str:
    if role == "tts" and "language" in table:
        return (
            "the OpenAI speech API has no language field — pick a voice that speaks it, or pass "
            f"it to your adapter under [{role}.options]"
        )
    if "api_base" in table:
        return f"the endpoint of [{role}] is `base_url` (`api_base` is its name in [system_two])"
    return f"remove them, or put adapter settings under [{role}.options]"


def parse_speech(role: str, table: Any, source: Path | None = None) -> SpeechConfig:
    """A validated `SpeechConfig`; `AgentManifestError` naming the first bad field."""
    if role not in ROLES:
        raise ValueError(f"role must be one of {ROLES}")
    name = f"[{role}]"
    where = f"{source} -> {name}" if source else name
    if not isinstance(table, dict):
        raise AgentManifestError(where=where, why=f"{name} must be a table", how=f"write {name}")
    refuse_secrets(table, where, "OPENAI_API_KEY")
    refuse_unknown(table, where, role, KEYS[role], _unknown_hint(role, table))
    provider = provider_of(
        table,
        where,
        OPENAI,
        "the OpenAI audio API: OpenAI, Groq, faster-whisper, Kokoro… by base_url",
        "python:my_speech.adapter:make",
    )
    custom = provider != OPENAI
    model = model_id(
        table,
        where,
        required=not custom,
        why=f"the OpenAI audio API needs a string `model` in {name}",
        how=f'write model = "{EXAMPLE_MODEL[role]}" (or the model name your server serves)',
    )
    voice = None
    if role == "tts":
        voice = plain_text(
            table,
            where,
            "voice",
            required=not custom,
            why="the OpenAI speech API needs a string `voice`: a name, no control characters, "
            "not shaped like a key",
            how='write voice = "alloy" (OpenAI), or the voice your server has (Kokoro: "af_heart")',
        )
    language = table.get("language")
    if language is not None and (not isinstance(language, str) or not LANGUAGE.match(language)):
        raise AgentManifestError(
            where=f"{where} language",
            why='language must be an ISO-639-1 code such as "vi" or "en", and it is not one',
            how='write language = "vi", or remove it to let the model detect it',
        )
    api_key_env = key_env(table, where, "OPENAI_API_KEY")
    base_url = endpoint(
        table,
        where,
        "base_url",
        default=OPENAI_BASE_URL,
        example=OPENAI_BASE_URL,
        keyed=api_key_env is not None,
        exposes="the key",
    )
    if not custom and api_key_env is None and "base_url" not in table:
        raise AgentManifestError(
            where=f"{where} api_key_env",
            why=f"{name} speaks to OpenAI's cloud, which needs a key, and does not say where to "
            "read it",
            how='add api_key_env = "OPENAI_API_KEY" (a keyless local server: set base_url instead)',
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
    return SpeechConfig(
        role=role,
        provider=provider,
        base_url=(base_url or OPENAI_BASE_URL).rstrip("/"),
        model=model,
        voice=voice,
        language=language,
        timeout_s=timeout,
        api_key_env=api_key_env,
        options=options(table, where, role, "OpenAI audio" if not custom else None),
        source=source,
    )


def load_speech_configs(manifest: Any) -> tuple[SpeechConfig | None, SpeechConfig | None]:
    """The agent's `[stt]` and `[tts]`; None for a table it does not have."""
    document = tomllib.loads(manifest.source.read_text(encoding="utf-8"))
    return tuple(  # type: ignore[return-value]
        parse_speech(role, document[role], manifest.source) if role in document else None
        for role in ROLES
    )
