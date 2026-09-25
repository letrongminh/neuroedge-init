"""
`VoiceSession` — the conversation state machine driving an agent (TSK-S3-11).

It puts `VoiceStateMachine` in front of a `SimSession`: the machine decides
which turn is current; the session runs a current turn's transcript through the
command grammar or System 2, `c.do()` and the gates, exactly as a typed line
(`SimSession.handle`). Nothing here decides a gate or drives a pin.

Time is virtual: the caller advances the injected clock with `advance()`, which
delivers scheduled commands (`SimHAL.run_due`) and fires the machine's
deadlines in time order. At one offset, inputs come before any deadline that
falls on that same offset — so a barge-in at the very ms a scheduled command is
due cancels it (fail-closed), and speech at the very ms the end-of-turn silence
runs out continues the turn (docs/spec/voice_fsm.md §9.1).

ASR, TTS and wake-word models are not here (TSK-S3-13, TSK-I4-01): transcripts,
wake words and VAD edges arrive as the events of §8.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ..actions.tools import ToolCall
from ..models import SystemOne
from ..sim.session import SimSession, Turn, _answer_word
from .voice_fsm import VoiceParams, VoiceStateMachine

FACTS_SOURCES = ("local_grammar", "unreachable")


class VirtualClock:
    """A clock in ms that moves only when told to (§2)."""

    def __init__(self, start_ms: float = 0.0) -> None:
        self.now = float(start_ms)

    def __call__(self) -> float:
        return self.now


class VoiceSession:
    def __init__(
        self,
        session: SimSession,
        *,
        clock: VirtualClock,
        params: VoiceParams | None = None,
        system_two: bool = False,
    ) -> None:
        self.session = session
        self.clock = clock
        self.events = session.events
        self.hal = session.hal
        # A provider is configured and answers asynchronously (`system_two_reply`).
        self.system_two = system_two
        self.hal.enable_scheduling(clock)
        self.fsm = VoiceStateMachine(
            params,
            events=self.events,
            pending_commands=self.hal.pending_commands,
            close_token=session.conversation.ledger.close,
        )
        self._awaiting: int | None = None  # the turn waiting for System 2
        self._transcript = ""

    @classmethod
    def load(
        cls,
        agent_toml: str | Path,
        *,
        params: VoiceParams | None = None,
        clock: VirtualClock | None = None,
        facts: Mapping[str, Any] | None = None,
        unset_facts: tuple[str, ...] = (),
        sensors: Mapping[str, Any] | None = None,
        system_two: bool = False,
        facts_source: str = "local_grammar",
    ) -> VoiceSession:
        """
        `facts_source="unreachable"`: the model that decides gate facts is offline
        and no local fallback can run — the Q-14 case that blocks with
        `gate_unreachable`.
        """
        if facts_source not in FACTS_SOURCES:
            raise ValueError(f"facts_source must be one of {FACTS_SOURCES}, not {facts_source!r}")
        clock = clock if clock is not None else VirtualClock()
        session = SimSession.load(agent_toml, facts=facts, clock=clock)
        for name in unset_facts:
            session.facts.pop(name, None)
        for sensor, value in (sensors or {}).items():
            session.set_sensor(sensor, value)
        if facts_source == "unreachable":
            engine = session.conversation.engine
            engine.facts_source = SystemOne("sim", network="offline", events=session.events)
        return cls(session, clock=clock, params=params, system_two=system_two)

    # -- time ----------------------------------------------------------------------
    def _next_deadline(self) -> float | None:
        due = [d for d in (self.hal.next_delivery_ms(), self.fsm.next_deadline()) if d is not None]
        return min(due) if due else None

    async def advance(self, to_ms: float, *, inclusive: bool = False) -> None:
        """
        Move the clock to `to_ms`, firing what falls due on the way: deliveries
        first, then the machine's deadlines. A deadline at exactly `to_ms` waits
        for the input at `to_ms` unless `inclusive` (the end of a case).
        """
        while True:
            deadline = self._next_deadline()
            if deadline is None or deadline > to_ms or (deadline == to_ms and not inclusive):
                break
            self.clock.now = max(self.clock.now, deadline)
            self.hal.run_due()
            for signal in self.fsm.fire_due():
                if signal == "think_timeout":
                    await self._offline_reply()
        self.clock.now = max(self.clock.now, float(to_ms))

    # -- inputs (§8, and the corpus's own) -------------------------------------------
    async def feed(self, type: str, data: Mapping[str, Any]) -> None:
        """One input event at the current clock. It is recorded, then acted on."""
        data = dict(data)
        self.events.emit(type, data)
        if type == "wake_word_detected":
            self.fsm.wake_word()
        elif type == "audio_in_vad_start":
            self.fsm.vad_start()
        elif type == "audio_in_vad_end":
            self.fsm.vad_end()
        elif type == "stt_result":
            await self._stt_result(int(data["turn"]), str(data["text"]))
        elif type == "system_two_reply":
            await self._system_two_reply(
                int(data["turn"]), data.get("text") or None, data.get("tool_calls") or []
            )
        elif type == "system_two_unavailable":
            if self._awaiting is not None and self.fsm.accepts(self._awaiting):
                await self._offline_reply()  # T09
        elif type == "tts_stream_end":
            self.fsm.reply_ended()
        else:
            raise ValueError(f"not a voice input event: {type!r}")

    def _drop(self, turn: int, source: str) -> None:
        """§5.2 step 4: a result of a replaced or concluded turn never acts."""
        self.events.emit("voice_late_result_dropped", {"turn": turn, "input": source})

    async def _stt_result(self, turn: int, text: str) -> None:
        if not self.fsm.accepts(turn) or self.fsm.transcript_taken:
            self._drop(turn, "stt_result")
            return
        if not self.fsm.transcript(turn, text):
            return  # empty: T06
        self._transcript = text
        s = self.session
        answers = s.pending_confirmation() is not None and _answer_word(text) is not None
        if self.system_two and not answers and not s.grammar.recognize(text).recognised:
            self._awaiting = turn  # free phrasing: System 2 answers later, or times out
            return
        before = len(self.hal.spoken)
        self._conclude(await s.handle(text), before)

    async def _system_two_reply(self, turn: int, text: str | None, calls: list[Any]) -> None:
        if self._awaiting != turn or not self.fsm.accepts(turn):
            self._drop(turn, "system_two_reply")
            return
        self._awaiting = None
        tool_calls = [
            ToolCall(str(c["name"]), dict(c.get("arguments") or {}), source="system_two")
            for c in calls
        ]
        before = len(self.hal.spoken)
        self._conclude(
            await self.session.run_tool_calls(self._transcript, tool_calls, text), before
        )

    def _conclude(self, turn: Turn, spoken_before: int) -> None:
        if len(self.hal.spoken) > spoken_before:
            # RFC-0006: a question a person may answer keeps the floor for the answer (T11).
            self.fsm.reply_started(ask=turn.confirmation is not None)  # T07
        else:
            self.fsm.reply_empty()  # T08

    async def _offline_reply(self) -> None:
        """§7: provider gone or too slow — say the offline line, as any reply. Never a c.do()."""
        self._awaiting = None
        await self.session.conversation.say(self.session.offline_help())
        self.fsm.reply_started(ask=False)
