"""
`[stt]`, `[tts]` and `[wake_word]` of `agent.toml` — which provider hears, which
speaks, and which listens for the wake word (TSK-S3-13, TSK-I4-01, FR-MDL-09,
FR-PER-01, Q-7, Q-12).

    [stt]
    base_url    = "https://api.openai.com/v1"   # default; Groq, faster-whisper, … by URL
    model       = "whisper-1"
    language    = "vi"                          # ISO-639-1, optional
    timeout_s   = 15
    api_key_env = "OPENAI_API_KEY"              # the NAME of the variable, never the key

    [stt.fallback]                              # used when the primary is unavailable (Q-14)
    base_url    = "http://localhost:8000/v1"    # e.g. a local faster-whisper / speaches server
    model       = "Systran/faster-whisper-small"
    timeout_s   = 5

    [tts]
    base_url    = "http://localhost:8880/v1"    # e.g. Kokoro; a local server needs no key
    model       = "kokoro"
    voice       = "af_heart"
    timeout_s   = 15

    [wake_word]                                 # optional; without it a turn opens on VAD (T01)
    provider      = "openwakeword"              # or "python:pkg.mod:factory"
    model         = "models/hey_neuro.onnx"     # YOUR wake-word model; NeuroEdge ships none (Q-45)
    melspectrogram = "models/melspectrogram.onnx"   # openWakeWord's feature models are YOURS too:
    embedding     = "models/embedding_model.onnx"   # it ships none, and nothing is downloaded
    threshold     = 0.5
    word          = "hey neuro"                 # the label in wake_word_detected; default: file stem

`provider` is ``"openai"`` (the default: the OpenAI audio API, `openai_audio.py`)
or ``"python:pkg.mod:factory"`` — an adapter of your own, handed this config
and its `[stt.options]` / `[tts.options]` (FR-MDL-08, as `[system_two]`). The
wake-word provider is ``"openwakeword"`` (optional extra `neuroedge[wake]`) or a
``python:`` adapter; its `model` must be a file that exists — all of openWakeWord's
pre-trained models are CC BY-NC-SA 4.0 (non-commercial), so NeuroEdge ships and
downloads none, and the `.model` field is never fetched from the network.

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
    looks_like_key,
    model_id,
    options,
    plain_text,
    provider_of,
    refuse_secrets,
    refuse_unknown,
    secret_fields,
)

OPENAI = "openai"
OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_TIMEOUT_S = 15.0
MAX_TIMEOUT_S = 120.0
ROLES = ("stt", "tts")
KEYS = {
    "stt": (
        "provider",
        "base_url",
        "model",
        "language",
        "timeout_s",
        "api_key_env",
        "fallback",
        "options",
    ),
    "tts": ("provider", "base_url", "model", "voice", "timeout_s", "api_key_env", "options"),
}
EXAMPLE_MODEL = {"stt": "whisper-1", "tts": "gpt-4o-mini-tts"}
LANGUAGE = re.compile(r"^[a-z]{2,3}$")
# `[wake_word]`: openWakeWord (Apache-2.0 code) with models of your own. No model
# of openWakeWord's ships or is ever downloaded: every one it publishes is
# CC BY-NC-SA 4.0 or of unestablished licence (Q-45). The three files are the
# wake-word model and the two feature models `Model` always loads.
OPENWAKEWORD = "openwakeword"
WAKE_KEYS = ("provider", "model", "melspectrogram", "embedding", "word", "threshold", "options")
DEFAULT_WAKE_THRESHOLD = 0.5


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
    # The table it was parsed from: "stt" or "stt.fallback" (TSK-I4-01)
    name: str = ""
    # `[stt.fallback]`: the STT endpoint the driver calls when the primary is
    # unavailable (Q-14). Only the primary carries one; a fallback has none.
    fallback: SpeechConfig | None = None

    @property
    def table(self) -> str:
        return self.name or self.role

    @property
    def where(self) -> str:
        return f"{self.source} -> [{self.table}]" if self.source else f"[{self.table}]"

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


def parse_speech(
    role: str, table: Any, source: Path | None = None, *, name: str | None = None
) -> SpeechConfig:
    """
    A validated `SpeechConfig`; `AgentManifestError` naming the first bad field.
    `name` is ``"stt.fallback"`` for `[stt.fallback]` (never nested further).
    """
    if role not in ROLES:
        raise ValueError(f"role must be one of {ROLES}")
    label = name or role
    where = f"{source} -> [{label}]" if source else f"[{label}]"
    if not isinstance(table, dict):
        raise AgentManifestError(
            where=where, why=f"[{label}] must be a table", how=f"write [{label}]"
        )
    refuse_secrets(table, where, "OPENAI_API_KEY")
    keys = KEYS[role] if label == role else tuple(k for k in KEYS[role] if k != "fallback")
    refuse_unknown(table, where, label, keys, _unknown_hint(role, table))
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
        why=f"the OpenAI audio API needs a string `model` in [{label}]",
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
            why=f"[{label}] speaks to OpenAI's cloud, which needs a key, and does not say where to "
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
    fallback = None
    if role == "stt" and label == role and "fallback" in table:
        fallback = parse_speech("stt", table["fallback"], source, name="stt.fallback")
    return SpeechConfig(
        role=role,
        provider=provider,
        base_url=(base_url or OPENAI_BASE_URL).rstrip("/"),
        model=model,
        voice=voice,
        language=language,
        timeout_s=timeout,
        api_key_env=api_key_env,
        options=options(table, where, label, "OpenAI audio" if not custom else None),
        source=source,
        name=label,
        fallback=fallback,
    )


def load_speech_configs(manifest: Any) -> tuple[SpeechConfig | None, SpeechConfig | None]:
    """The agent's `[stt]` and `[tts]`; None for a table it does not have."""
    document = tomllib.loads(manifest.source.read_text(encoding="utf-8"))
    return tuple(  # type: ignore[return-value]
        parse_speech(role, document[role], manifest.source) if role in document else None
        for role in ROLES
    )


@dataclass(frozen=True)
class WakeWordConfig:
    """
    `[wake_word]` (TSK-I4-01, Q-7): the detector that opens a turn, or None when
    the agent declares none. For provider ``openwakeword``, `path`,
    `melspectrogram_path` and `embedding_path` are the three model files the user
    supplies (openWakeWord ships none; nothing is ever downloaded, Q-45);
    `word` is the label `wake_word_detected` carries and the only class allowed to
    open a turn.
    """

    provider: str = OPENWAKEWORD
    model: str = ""
    path: Path | None = None
    melspectrogram: str = ""
    melspectrogram_path: Path | None = None
    embedding: str = ""
    embedding_path: Path | None = None
    word: str = ""
    threshold: float = DEFAULT_WAKE_THRESHOLD
    options: dict[str, Any] = field(default_factory=dict)
    source: Path | None = None

    @property
    def where(self) -> str:
        return f"{self.source} -> [wake_word]" if self.source else "[wake_word]"

    @property
    def adapter(self) -> str | None:
        """``pkg.mod:factory`` for a custom adapter, else None."""
        if self.provider.startswith(PYTHON_PREFIX):
            return self.provider[len(PYTHON_PREFIX) :]
        return None

    @property
    def label(self) -> str:
        """Which model and threshold — never a key (the banner's line)."""
        if self.adapter is not None:
            return f"adapter {self.adapter} (threshold {self.threshold:g})"
        return f"{self.path.name} (threshold {self.threshold:g}, word {self.word!r})"

    def missing_models(self) -> list[tuple[str, Path | None]]:
        """
        The model files that are not on this machine, as ``(field, path)``, in the
        order they appear in `[wake_word]`. Empty for a custom adapter, whose
        files it owns.
        """
        if self.adapter is not None:
            return []
        return [
            (field, path)
            for field, path in (
                ("model", self.path),
                ("melspectrogram", self.melspectrogram_path),
                ("embedding", self.embedding_path),
            )
            if path is None or not path.is_file()
        ]


def _wake_path(
    table: dict[str, Any], where: str, field: str, root: Path | None, *, required: bool
) -> tuple[str, Path | None]:
    """One model path of `[wake_word]`: text, resolved against the agent's directory."""
    value = table.get(field, "")
    if not isinstance(value, str) or any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise AgentManifestError(
            where=f"{where} {field}",
            why=f"{field} must be the path to a model file, as text without control characters",
            how=f'write {field} = "models/<file>.onnx"',
        )
    value = value.strip()
    if not value:
        if required:
            raise AgentManifestError(
                where=f"{where} {field}",
                why=f"provider openwakeword needs {field}: a model of your own. NeuroEdge ships "
                "none — every model openWakeWord publishes is CC BY-NC-SA 4.0 (non-commercial) or "
                "of unestablished licence, and its downloader must never run (Q-45)",
                how=f"train or obtain your own {field} model and write {field} = "
                '"models/<file>.onnx", or use provider = "python:my_wake.adapter:make"',
            )
        return "", None
    if looks_like_key(value):
        raise AgentManifestError(
            where=f"{where} {field}",
            why=f"{field} looks like an API key, not a path — if it is a key, revoke it; nothing is "
            "downloaded from the network here",
            how=f'write the path of a model file you own, e.g. {field} = "models/<file>.onnx"',
        )
    path = Path(value)
    if not path.is_absolute() and root is not None:
        path = Path(root) / path
    return value, path


def parse_wake_word(
    table: Any,
    source: Path | None = None,
    root: Path | None = None,
    *,
    check_files: bool = False,
) -> WakeWordConfig:
    """
    A validated `WakeWordConfig`; `AgentManifestError` naming the first bad field:
    a threshold outside (0, 1], a key written in the table, or an adapter that is
    not one. `root` resolves a relative model path (the agent's directory, where
    the user's models sit next to `agent.toml`).

    `check_files=False` (a build, a typed session) validates the table's *shape*
    only: the models may live on the device, not on this machine. A voice session
    loads with `check_files=True`, before any GPIO line, and a missing file is an
    error then — openWakeWord 0.6 downloads its models when a path is missing, and
    that must never happen (Q-45).
    """
    where = f"{source} -> [wake_word]" if source else "[wake_word]"
    if not isinstance(table, dict):
        raise AgentManifestError(
            where=where, why="[wake_word] must be a table", how="write [wake_word]"
        )
    secrets = secret_fields(table)
    if secrets:
        # Never repeat the value: it may be a live key.
        raise AgentManifestError(
            where=f"{where} {secrets[0]}",
            why="a key must never be written in agent.toml — the file is committed and shared, so "
            "it would leak with it; a wake word reads local model files and needs no key",
            how=f"delete `{secrets[0]}`; [wake_word] takes provider, model, melspectrogram, "
            "embedding, word and threshold",
        )
    refuse_unknown(
        table,
        where,
        "wake_word",
        WAKE_KEYS,
        "remove them, or put adapter settings under [wake_word.options]",
    )
    provider = provider_of(
        table,
        where,
        OPENWAKEWORD,
        "openWakeWord with models of your own (Apache-2.0 code; no model ships or downloads)",
        "python:my_wake.adapter:make",
    )
    custom = provider != OPENWAKEWORD
    model, path = _wake_path(table, where, "model", root, required=not custom)
    melspectrogram, melspectrogram_path = _wake_path(
        table, where, "melspectrogram", root, required=not custom
    )
    embedding, embedding_path = _wake_path(table, where, "embedding", root, required=not custom)
    if check_files:
        config = WakeWordConfig(
            provider=provider,
            model=model,
            path=path,
            melspectrogram=melspectrogram,
            melspectrogram_path=melspectrogram_path,
            embedding=embedding,
            embedding_path=embedding_path,
            source=source,
        )
        missing = config.missing_models()
        if missing:
            field, missing_path = missing[0]
            raise AgentManifestError(
                where=f"{where} {field}",
                why=f"no model file at {missing_path}; openWakeWord ships none and its downloader "
                "must never run (every model it publishes is CC BY-NC-SA 4.0 or of unestablished "
                "licence — Q-45)",
                how=f"put your own {field} file there (a path relative to the agent's directory "
                'is taken from there), or use provider = "python:my_wake.adapter:make"',
            )
    word = plain_text(
        table,
        where,
        "word",
        required=False,
        why="word must be a short label (no control characters, at most 100 characters), not "
        "shaped like a key",
        how='write word = "hey neuro", or remove it to use the model file\'s name',
    )
    threshold = bounded(
        table,
        where,
        "threshold",
        default=DEFAULT_WAKE_THRESHOLD,
        low=0,
        high=1,
        unit="a confidence in (0, 1]",
        why="a score at or above it opens a turn (a wake_word_detected event)",
    )
    return WakeWordConfig(
        provider=provider,
        model=model,
        path=path,
        melspectrogram=melspectrogram,
        melspectrogram_path=melspectrogram_path,
        embedding=embedding,
        embedding_path=embedding_path,
        word=word or (path.stem if path is not None else "wake"),
        threshold=threshold,
        options=options(table, where, "wake_word", "openWakeWord" if not custom else None),
        source=source,
    )


def load_wake_word_config(manifest: Any, *, check_files: bool = False) -> WakeWordConfig | None:
    """The agent's `[wake_word]`, or None when it declares none (VAD opens turns, T01)."""
    document = tomllib.loads(manifest.source.read_text(encoding="utf-8"))
    if "wake_word" not in document:
        return None
    return parse_wake_word(
        document["wake_word"], manifest.source, manifest.root, check_files=check_files
    )
