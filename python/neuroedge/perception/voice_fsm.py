"""
The conversation state machine — Python implementation (TSK-S3-11).

The normative definition is docs/spec/voice_fsm.md; this module implements it
for `sim` and `linux`, and `fixtures/compliance/voice/` (TSK-S3-10) is how it
proves it. The C/C++ implementation for `esp32s3` (TSK-S5-03) must pass the
same corpus. Row ids `T01`…`T14` below are the rows of the table in §4.

Shape of the design follows Pipecat's frame-driven pipeline (input events in,
effects out, one processor owning turn state); no Pipecat code is copied and
nothing is imported from it.

Determinism (§2): the machine reads time only from the clock of its `EventLog`
— injected, in ms — and changes state only on an input (a method call below) or
on a deadline the caller reaches with `fire_due()`. It never evaluates a gate
and never drives a pin; on barge-in it cancels *pending* commands only (§5).

Conventions the corpus fixes where §4 leaves an order open (§9.1):

* a row's effects are recorded before its `voice_state_changed` — as §5.2 puts
  the abort, the token close and the TTS stop before the state change;
* rows that stay in the same state (T02, T03, T09) record no `voice_state_changed`.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from ..engine.trace_sink import EventLog
from ..hal.sim import ABORTED_BY_BARGE_IN


class VoiceState(StrEnum):
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    THINKING = "THINKING"
    SPEAKING = "SPEAKING"
    BARGE_IN = "BARGE_IN"


# `trigger` of `voice_state_changed` (§8).
TRIGGERS = (
    "wake_word",
    "speech_start",
    "turn_end",
    "listen_timeout",
    "transcript_empty",
    "reply_start",
    "reply_empty",
    "reply_end",
    "ask_asked",
    "barge_in",
)


@dataclass(frozen=True)
class VoiceParams:
    """§6. Tunable, not a safety contract; each corpus case states the values it uses."""

    end_of_turn_silence_ms: int = 700
    listen_timeout_ms: int = 8000
    # §6 "theo provider": `[system_two] timeout_s` × GRACE; 20 s × 1.25 when unset.
    think_timeout_ms: int = 25000
    max_reprompts: int = 1
    # T01: `audio_in_vad_start` opens a turn from IDLE only when the device enables it.
    vad_activation: bool = False

    @classmethod
    def from_mapping(cls, values: dict[str, Any]) -> VoiceParams:
        known = set(cls.__dataclass_fields__)
        unknown = set(values) - known
        if unknown:
            raise ValueError(f"unknown voice parameters {sorted(unknown)}; known: {sorted(known)}")
        return cls(**values)


class VoiceStateMachine:
    """
    Five states, the table of §4 and the abort contract of §5.2.

    `pending_commands` returns the physical commands not yet delivered to a pin
    (`SimHAL.pending_commands`); `close_token` is `TokenLedger.close`;
    `stop_speech` flushes the audio output (`VoiceSession` cuts the reply playing
    on the speaker, TSK-S3-13). All three are optional: a target with no
    scheduled commands has nothing to cancel.
    """

    def __init__(
        self,
        params: VoiceParams | None = None,
        *,
        events: EventLog,
        pending_commands: Callable[[], Iterable[Any]] | None = None,
        close_token: Callable[[Any], None] | None = None,
        stop_speech: Callable[[], None] | None = None,
    ) -> None:
        self.params = params or VoiceParams()
        self.events = events
        self.clock = events.clock
        self._pending_commands = pending_commands or (lambda: ())
        self._close_token = close_token
        self._stop_speech = stop_speech
        self.state = VoiceState.IDLE
        self.turn = 0
        # Deadlines, in clock ms; None when not running.
        self._end_of_turn_at: float | None = None
        self._listen_until: float | None = None
        self._think_until: float | None = None
        self._transcript_taken = False  # the current THINKING turn has its transcript
        self._reply_is_ask = False
        self._reply_started_at: float | None = None
        # The turn opened out of speaking a question — T11, or T13 → T14 over it: the one
        # turn in which a spoken yes / no may answer that question (§5.4, Q-46 (D3)).
        self.answer_turn: int | None = None
        self._empty_in_a_row = 0
        # Commands this machine cancelled, oldest first (the corpus reuses their tokens).
        self.aborted: list[Any] = []

    # -- deadlines -------------------------------------------------------------
    def next_deadline(self) -> float | None:
        due = [
            d
            for d in (self._end_of_turn_at, self._listen_until, self._think_until)
            if d is not None
        ]
        return min(due) if due else None

    def fire_due(self) -> list[str]:
        """
        Fire every deadline that has passed on the clock, earliest first. Returns
        what the caller must act on: ``"turn_end"`` means the turn closed — send
        its audio to STT (T04); ``"think_timeout"`` means say the offline line
        now (T09, §7).
        """
        signals: list[str] = []
        now = self.clock()
        while True:
            deadline = self.next_deadline()
            if deadline is None or deadline > now:
                return signals
            if deadline == self._end_of_turn_at:
                self._end_of_turn_at = None
                self._to(VoiceState.THINKING, "turn_end")  # T04
                signals.append("turn_end")
            elif deadline == self._listen_until:
                self._listen_until = None
                self._to(VoiceState.IDLE, "listen_timeout")  # T05
            else:
                self._think_until = None
                signals.append("think_timeout")  # T09: THINKING stays THINKING

    # -- inputs (§8) -------------------------------------------------------------
    def wake_word(self) -> None:
        if self.state is VoiceState.IDLE:
            self._open_turn("wake_word", speech=False)  # T01

    def vad_start(self) -> None:
        state = self.state
        if state is VoiceState.IDLE:
            if self.params.vad_activation:
                self._open_turn("speech_start", speech=True)  # T01
        elif state is VoiceState.LISTENING:
            self._listen_until = None
            self._end_of_turn_at = None  # T03: a pause to think, not the end of the turn
        elif state in (VoiceState.THINKING, VoiceState.SPEAKING):
            self._barge_in()  # T10, T13, then T14

    def vad_end(self) -> None:
        if self.state is VoiceState.LISTENING:
            self._end_of_turn_at = self.clock() + self.params.end_of_turn_silence_ms  # T02

    @property
    def transcript_taken(self) -> bool:
        """The current thinking turn already has its transcript."""
        return self._transcript_taken

    def accepts(self, turn: int) -> bool:
        """A result (transcript, model reply) for `turn` may still act: its turn is thinking."""
        return self.state is VoiceState.THINKING and turn == self.turn

    def transcript(self, turn: int, text: str) -> bool:
        """
        `stt_result` for `turn`. True when the caller must now run the turn on
        `text`; False when the result is dropped (late, §5.2 step 4) or empty.
        """
        if not self.accepts(turn) or self._transcript_taken:
            return False
        if text.strip():
            self._transcript_taken = True
            self._empty_in_a_row = 0
            return True
        self._empty_in_a_row += 1  # T06, FR-PER-05
        if self._empty_in_a_row <= self.params.max_reprompts:
            self.events.emit("voice_reprompt", {"turn": self.turn, "count": self._empty_in_a_row})
        self._to(VoiceState.IDLE, "transcript_empty")
        return False

    def reply_started(self, *, ask: bool) -> None:
        """`tts_stream_start` of the current turn's reply (T07)."""
        if self.state is VoiceState.THINKING:
            self._reply_is_ask = ask
            self._reply_started_at = self.clock()
            self._to(VoiceState.SPEAKING, "reply_start")

    def reply_empty(self) -> None:
        """The turn concluded with nothing to say (T08)."""
        if self.state is VoiceState.THINKING:
            self._to(VoiceState.IDLE, "reply_empty")

    def reply_ended(self, reason: str = "done") -> None:
        """
        `tts_stream_end` with `done` or `error` while speaking (T11, T12). A question
        whose stream ended with `error` was never heard: it opens no answer turn (T12,
        Q-46 (D3)).
        """
        if self.state is not VoiceState.SPEAKING:
            return
        if self._reply_is_ask and reason != "error":
            self._open_turn("ask_asked", speech=False)  # T11
            self.answer_turn = self.turn
        else:
            self._to(VoiceState.IDLE, "reply_end")  # T12

    # -- the abort contract (§5.2) -----------------------------------------------
    def _barge_in(self) -> None:
        was = self.state
        # 1. cancel every pending command, before anything waits on the speaker.
        for command in list(self._pending_commands()):
            if getattr(command, "delivered", True) or getattr(command, "cancelled", False):
                continue  # §5.3: a delivered command runs to the end
            command.cancel(ABORTED_BY_BARGE_IN)
            self.aborted.append(command)
            # 2. close its token (§5.2). `c.do()` has already closed it when the action
            # returned, and delivery does not consult the ledger: the barrier that keeps
            # the pin still is the cancel above (`run_due` skips a cancelled command).
            token = getattr(command, "token", None)
            if token is not None and self._close_token is not None:
                self._close_token(token)
        # 3. stop TTS — only when a reply is playing (THINKING is silent, §3).
        if was is VoiceState.SPEAKING:
            if self._stop_speech is not None:
                self._stop_speech()
            started = self._reply_started_at if self._reply_started_at is not None else self.clock()
            self.events.emit(
                "tts_stream_end",
                {"duration_ms": max(0, int(self.clock() - started)), "reason": "barge_in"},
            )
        # 4. the replaced turn is dropped: `accepts()` is False for it from here on.
        # 5. record the state changes.
        self._to(VoiceState.BARGE_IN, "barge_in")
        self._open_turn("barge_in", speech=True)  # T14
        if was is VoiceState.SPEAKING and self._reply_is_ask:
            self.answer_turn = self.turn  # speech over the question may be its answer (§5.4)

    # -- transitions -------------------------------------------------------------
    def _open_turn(self, trigger: str, *, speech: bool) -> None:
        self.turn += 1
        self.answer_turn = None  # T11 and T14 over a question set it again
        self._to(VoiceState.LISTENING, trigger)
        if not speech:
            self._listen_until = self.clock() + self.params.listen_timeout_ms

    def _to(self, state: VoiceState, trigger: str) -> None:
        was = self.state
        self._end_of_turn_at = None
        self._listen_until = None
        self._think_until = None
        if state is VoiceState.THINKING:
            self._transcript_taken = False
            self._think_until = self.clock() + self.params.think_timeout_ms
        self.state = state
        self.events.emit(
            "voice_state_changed",
            {"from": str(was), "to": str(state), "trigger": trigger, "turn": self.turn},
        )
