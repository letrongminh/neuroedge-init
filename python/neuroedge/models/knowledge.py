"""
Local knowledge base: retrieval for System 2 (RAG), and the offline answer.

    [knowledge]
    version   = 1
    threshold = 0.55          # optional: minimum score for a passage to be context

    [[entry]]
    id        = "wifi"        # optional; defaults to entry-<n>
    questions = ["wifi nhà mình là gì", "mật khẩu wifi"]
    answer    = "Mạng NhaMinh, mật khẩu dán ở mặt dưới router."

A question the agent hears goes two ways at once:

* **routing** — every entry is a grammar command with intent ``knowledge``,
  matched like any command (`CommandGrammar`, threshold of `commands.toml`);
* **retrieval** — `retrieve()` scores every entry against the question,
  locally and deterministically, and returns the best few as context.

The session then asks System 2 to answer *from that context* (human-like, RAG).
When System 2 cannot answer — offline, no provider — the matched entry's own
`answer` is said instead. Either way the reply is speech: never gated, never
asserted on (FR-CI-LVL, L3). Only which entries were retrieved goes into the
trace (`knowledge_retrieved`), so a replay shows what the answer was based on.
"""

from __future__ import annotations

import difflib
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..errors import PerceptionUnavailableError
from .grammar import Command, CommandGrammar, normalise

KNOWLEDGE_INTENT = "knowledge"
KNOWLEDGE_TASK = "knowledge"


@dataclass(frozen=True)
class KnowledgeEntry:
    id: str
    questions: tuple[str, ...]
    answer: str

    def context(self) -> dict[str, Any]:
        return {"id": self.id, "question": self.questions[0], "answer": self.answer}


class KnowledgeBase:
    def __init__(
        self, entries: list[KnowledgeEntry], threshold: float = 0.55, source: str = "<memory>"
    ):
        self.entries = entries
        self.threshold = threshold
        self.source = source

    @classmethod
    def load(cls, path: str | Path) -> KnowledgeBase:
        path = Path(path)
        try:
            document = tomllib.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise PerceptionUnavailableError(
                where=str(path),
                why="the knowledge file does not exist",
                how="create knowledge.toml",
            ) from exc
        except tomllib.TOMLDecodeError as exc:
            raise PerceptionUnavailableError(
                where=str(path), why=f"not valid TOML: {exc}", how="repair the TOML syntax"
            ) from exc
        header = document.get("knowledge", {})
        if header.get("version") != 1:
            raise PerceptionUnavailableError(
                where=f"{path} -> knowledge.version",
                why=f"expected version = 1, found {header.get('version')!r}",
                how="add [knowledge] with version = 1",
            )
        threshold = header.get("threshold", 0.55)
        if not isinstance(threshold, (int, float)) or not 0.0 < threshold <= 1.0:
            raise PerceptionUnavailableError(
                where=f"{path} -> knowledge.threshold",
                why=f"threshold must lie in (0, 1], found {threshold!r}",
                how="use a value such as 0.55",
            )
        entries: list[KnowledgeEntry] = []
        seen: set[str] = set()
        for index, raw in enumerate(document.get("entry", [])):
            questions, answer = raw.get("questions"), raw.get("answer")
            entry_id = raw.get("id", f"entry-{index + 1}")
            if (
                not questions
                or not isinstance(questions, list)
                or not all(isinstance(q, str) and q.strip() for q in questions)
                or not isinstance(answer, str)
                or not answer.strip()
                or not isinstance(entry_id, str)
            ):
                raise PerceptionUnavailableError(
                    where=f"{path} -> entry[{index}]",
                    why="every entry needs a non-empty `questions` list and an `answer`",
                    how='write questions = ["wifi là gì"] and answer = "..."',
                )
            if entry_id in seen:
                raise PerceptionUnavailableError(
                    where=f"{path} -> entry[{index}].id",
                    why=f"id {entry_id!r} is used twice",
                    how="give every entry a unique id",
                )
            seen.add(entry_id)
            entries.append(KnowledgeEntry(entry_id, tuple(questions), answer))
        if not entries:
            raise PerceptionUnavailableError(
                where=str(path),
                why="the knowledge base has no [[entry]]",
                how="add at least one entry",
            )
        return cls(entries, float(threshold), str(path))

    def commands(self) -> list[Command]:
        """Routing: one grammar command per entry — ask System 2, fall back to the entry's answer."""
        return [
            Command(KNOWLEDGE_INTENT, entry.questions, ask=KNOWLEDGE_TASK, offline_say=entry.answer)
            for entry in self.entries
        ]

    def retrieve(self, question: str, k: int = 3) -> list[tuple[KnowledgeEntry, float]]:
        """The best `k` entries at or above the threshold, best first; ties keep file order."""
        asked = normalise(question)
        scored = []
        for order, entry in enumerate(self.entries):
            score = max(
                1.0
                if asked == normalise(q)
                else difflib.SequenceMatcher(None, asked, normalise(q)).ratio()
                for q in entry.questions
            )
            if score >= self.threshold:
                scored.append((-score, order, entry))
        scored.sort()
        return [(entry, round(-negative, 4)) for negative, _, entry in scored[:k]]


def load_agent_grammar(root: str | Path) -> tuple[CommandGrammar, KnowledgeBase | None]:
    """`commands.toml` of an agent, extended with `knowledge.toml` when present."""
    root = Path(root)
    grammar = CommandGrammar.load(root / "commands.toml")
    path = root / "knowledge.toml"
    if not path.is_file():
        return grammar, None
    knowledge = KnowledgeBase.load(path)
    return grammar.extended(knowledge.commands()), knowledge
