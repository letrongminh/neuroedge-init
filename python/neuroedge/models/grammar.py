"""
Fixed-command grammar — the local fallback of SystemOne (Q-14) and the default
input of `sim` (Q-15).

A grammar is a TOML file listing commands and the phrases that trigger them:

    [grammar]
    version   = 1
    threshold = 0.80

    [[command]]
    intent   = "unlock"
    patterns = ["mở cửa phòng {room}", "mở cửa"]
    facts    = { command_recognized = true }   # optional

Matching is deterministic and needs no network and no model: normalise the
text, try every pattern as a template (``{slot}`` matches one word) — an exact
match scores 1.0 — otherwise score by `difflib` similarity. Below `threshold`
nothing is recognised, which blocks through the normal criteria rather than
guessing. The same grammar drives every target; on `esp32s3` the backend is
ESP-SR MultiNet or TFLite Micro, on `sim` it is this module over typed text.
"""

from __future__ import annotations

import difflib
import re
import tomllib
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..engine.verdict import Fact, Unavailable
from ..errors import PerceptionUnavailableError

BACKEND = "local/command-grammar"
_PUNCTUATION = re.compile(r"[^\w\s{}]", re.UNICODE)
_SLOT = re.compile(r"\{(\w+)\}")


def normalise(text: str) -> str:
    """NFC, casefold, drop punctuation, collapse spaces. Diacritics are kept."""
    text = unicodedata.normalize("NFC", text).casefold()
    return " ".join(_PUNCTUATION.sub(" ", text).split())


@dataclass(frozen=True)
class Command:
    intent: str
    patterns: tuple[str, ...]
    facts: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Recognition:
    intent: str | None
    confidence: float
    slots: dict[str, str] = field(default_factory=dict)
    facts: dict[str, Any] = field(default_factory=dict)

    @property
    def recognised(self) -> bool:
        return self.intent is not None


def _template(pattern: str) -> re.Pattern[str]:
    parts = _SLOT.split(normalise(pattern))
    # split() alternates literal text and slot names.
    regex = "".join(
        re.escape(part) if index % 2 == 0 else f"(?P<{part}>\\S+)"
        for index, part in enumerate(parts)
    )
    return re.compile(f"^{regex}$")


class CommandGrammar:
    def __init__(
        self, commands: list[Command], threshold: float = 0.8, source: str = "<memory>"
    ) -> None:
        if not commands:
            raise PerceptionUnavailableError(
                where=source,
                why="the command grammar declares no [[command]] entries",
                how="add at least one [[command]] with an intent and patterns",
            )
        self.commands = commands
        self.threshold = threshold
        self.source = source
        self._compiled = [
            (command, pattern, _template(pattern), _SLOT.sub("", normalise(pattern)).strip())
            for command in commands
            for pattern in command.patterns
        ]

    @property
    def intents(self) -> tuple[str, ...]:
        return tuple(command.intent for command in self.commands)

    @classmethod
    def load(cls, path: str | Path) -> CommandGrammar:
        path = Path(path)
        if not path.is_file():
            raise PerceptionUnavailableError(
                where=str(path),
                why="the command grammar file does not exist",
                how="create commands.toml next to agent.toml, or point the fallback at it",
            )
        try:
            document = tomllib.loads(path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as exc:
            raise PerceptionUnavailableError(
                where=str(path),
                why=f"the command grammar is not valid TOML: {exc}",
                how="repair the TOML syntax reported above",
            ) from exc
        return cls.from_document(document, source=str(path))

    @classmethod
    def from_document(cls, document: Mapping[str, Any], source: str = "<memory>") -> CommandGrammar:
        header = document.get("grammar", {})
        if header.get("version") != 1:
            raise PerceptionUnavailableError(
                where=f"{source} -> grammar.version",
                why=f"expected version = 1, found {header.get('version')!r}",
                how="add [grammar] with version = 1",
            )
        threshold = header.get("threshold", 0.8)
        if not isinstance(threshold, (int, float)) or not 0.0 < threshold <= 1.0:
            raise PerceptionUnavailableError(
                where=f"{source} -> grammar.threshold",
                why=f"threshold must lie in (0, 1], found {threshold!r}",
                how="use a value such as 0.80",
            )
        commands = []
        for index, raw in enumerate(document.get("command", [])):
            intent, patterns = raw.get("intent"), raw.get("patterns")
            if not isinstance(intent, str) or not patterns or not isinstance(patterns, list):
                raise PerceptionUnavailableError(
                    where=f"{source} -> command[{index}]",
                    why="every command needs a string `intent` and a non-empty `patterns` list",
                    how='write intent = "unlock" and patterns = ["mở cửa"]',
                )
            commands.append(Command(intent, tuple(patterns), dict(raw.get("facts", {}))))
        return cls(commands, float(threshold), source)

    def recognize(self, text: str) -> Recognition:
        """Best command for `text`; unrecognised below the threshold. Ties go to file order."""
        spoken = normalise(text)
        best: tuple[float, Command | None, dict[str, str]] = (0.0, None, {})
        for command, _pattern, template, literal in self._compiled:
            match = template.match(spoken)
            if match is not None:
                return Recognition(command.intent, 1.0, dict(match.groupdict()), command.facts)
            score = difflib.SequenceMatcher(None, spoken, literal).ratio() if spoken else 0.0
            if score > best[0]:
                best = (score, command, {})
        score, command, slots = best
        if command is None or score < self.threshold:
            return Recognition(None, round(score, 4))
        return Recognition(command.intent, round(score, 4), slots, command.facts)


class GrammarAdjudicator:
    """
    A `FactSource` over typed or transcribed text, reading `state["utterance"]`.

    It answers a `choice` criterion with the recognised intent, and any criterion
    the matched command declares under `facts`. Everything else is refused, so
    the gate blocks with `criterion_unavailable` instead of guessing.
    """

    def __init__(self, grammar: CommandGrammar) -> None:
        self.grammar = grammar

    async def adjudicate(
        self,
        criterion: str,
        definition: Mapping[str, Any],
        state: Mapping[str, Any] | None,
        deadline_ms: float | None = None,
    ) -> Fact | Unavailable:
        utterance = (state or {}).get("utterance", "")
        recognition = self.grammar.recognize(utterance)
        if not recognition.recognised:
            return Unavailable("empty", f"no command matched {utterance!r}")
        if criterion in recognition.facts:
            return Fact(recognition.facts[criterion], recognition.confidence, source=BACKEND)
        options = definition.get("options", ())
        if definition.get("type") == "choice" and recognition.intent in options:
            return Fact(recognition.intent, recognition.confidence, source=BACKEND)
        return Unavailable("refused", f"the grammar does not adjudicate {criterion!r}")
