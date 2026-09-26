"""
`VoiceSession` — the conversation state machine driving an agent (TSK-S3-11),
and the audio path around it (TSK-S3-13).

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

Without providers, transcripts, wake words, VAD edges and the end of a reply
arrive as the input events of §8 (`feed`) — how the corpus drives it. Given an
STT and a TTS provider (`perception.providers`, `[stt]` / `[tts]`), the session
hears and speaks itself:

    audio.in frames ─► EnergyVAD ─► audio_in_vad_start / _end ─► machine
         └─► pre-roll + the turn's audio ─► T04 ─► STT ─► stt_result | stt_unavailable
    the turn's reply (tts_stream_start) ─► TTS ─► speaker ─► tts_stream_end done | error
    barge-in ─► §5.2: cancel pending commands, close tokens, stop the speaker

An STT or TTS call is awaited where it starts, and its answer is delivered as
an input `latency` ms later on the session's clock — a real call's latency timed
on `stopwatch`, a simulated one's as it reports. (System 2 is not: with
`system_two=True` its answers arrive as `system_two_reply` inputs, as the corpus
scripts them; otherwise `SimSession.handle` asks the model inline, at the
transcript's time.) Audio that arrives meanwhile is heard first, so speech while STT or System 2 works replaces the turn and the
late answer is dropped (§5.2 step 4). Every provider failure takes the degraded
path of §7 — the offline line, or a reply shown but not heard — and never a
`c.do()`: a transcript reaches a pin only the way a typed line does. The STT
wait is the turn's `perception` stage (`turn_latency`, tool_calling.md §7.1).
"""

from __future__ import annotations

import asyncio
import contextlib
import heapq
import inspect
import itertools
import math
import threading
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..actions.tools import ToolCall
from ..engine.trace_sink import monotonic_ms
from ..hal.audio import MAX_REPLY_MS, AudioFrame, EnergyVAD, Playback, pcm_digest, to_speaker
from ..models import SystemOne
from ..sim.session import SimSession, Turn, answer_word
from .providers.base import AudioClip, Speech, SpeechUnavailable, Transcript, clean_transcript
from .voice_fsm import VoiceParams, VoiceState, VoiceStateMachine

FACTS_SOURCES = ("local_grammar", "unreachable")
PREROLL_MS = 300  # audio kept from before speech starts, so a turn's first syllable is in it (RB-2)
MAX_CLIP_MS = 120_000  # a turn longer than this goes to STT cut at this length
DEFAULT_RATE_HZ = 16000
SETTLE_STEPS = 100_000  # `settle()` stops after this many deadlines, whatever is left
# A provider call is abandoned after its table's `timeout_s` × GRACE, plus a margin so
# an adapter that times itself out (the OpenAI one does) says so first. A provider
# without a `config.timeout_s` gets the think timeout: STT still silent then has
# failed anyway (voice_fsm.md §7).
GRACE = 1.25
MARGIN_S = 1.0


def _positive(value: Any) -> bool:
    return (
        isinstance(value, int | float)
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value > 0
    )


class VirtualClock:
    """A clock in ms that moves only when told to (§2)."""

    def __init__(self, start_ms: float = 0.0) -> None:
        self.now = float(start_ms)

    def __call__(self) -> float:
        return self.now


@dataclass(order=True)
class _Due:
    """A provider's answer (or the end of a reply) waiting for its time on the clock."""

    at_ms: float
    seq: int
    type: str = field(compare=False)
    data: dict[str, Any] = field(compare=False)


@dataclass(frozen=True)
class VoiceTurn:
    """What one turn heard and did: for the CLI and tests. `heard` is None if STT failed."""

    turn: int
    heard: str | None
    result: Turn
    stt_failure: str | None = None


class VoiceSession:
    def __init__(
        self,
        session: SimSession,
        *,
        clock: VirtualClock,
        params: VoiceParams | None = None,
        system_two: bool = False,
        stt: Any = None,
        tts: Any = None,
        stopwatch: Callable[[], float] = monotonic_ms,
        vad: EnergyVAD | None = None,
        on_turn: Callable[[VoiceTurn], None] | None = None,
    ) -> None:
        self.session = session
        self.clock = clock
        self.events = session.events
        self.hal = session.hal
        # A provider is configured and answers asynchronously (`system_two_reply`).
        self.system_two = system_two
        # The TTL check of a scheduled command compares the HAL's clock with the one
        # that stamped the token: they must be the same clock.
        if session.conversation.ledger.clock is not clock:
            raise ValueError("VoiceSession: `clock` must be the clock the session was loaded with")
        self.hal.enable_scheduling(clock)
        self.fsm = VoiceStateMachine(
            params,
            events=self.events,
            pending_commands=self.hal.pending_commands,
            close_token=session.conversation.ledger.close,
            stop_speech=self._stop_speech,
        )
        self.stt = stt
        self.tts = tts
        self.stopwatch = stopwatch  # times real provider calls; a simulated one says its own
        self.vad = vad if vad is not None else EnergyVAD()
        self.on_turn = on_turn
        self.turns: list[VoiceTurn] = []
        self._awaiting: int | None = None  # the turn waiting for System 2
        self._transcript = ""
        # When the awaited transcript came in: the System 2 wait of that turn's
        # `turn_latency` runs from here (TSK-I4-03).
        self._heard_at: float | None = None
        # Provider answers and reply ends waiting for their time, earliest first.
        self._inbox: list[_Due] = []
        self._seq = itertools.count()
        # When each turn's audio went to STT: its wait is the turn's perception stage.
        self._stt_sent: dict[int, float] = {}
        # audio.in: frames before speech (pre-roll), and the audio of the turn listening.
        self._ring: deque[AudioFrame] = deque()
        self._clip_turn: int | None = None
        self._clip: list[bytes] = []
        self._clip_ms = 0
        self._rate = DEFAULT_RATE_HZ
        # The reply on the speaker: its playback (None when TTS failed) and its end.
        self._playing: tuple[Playback | None, list[_Due]] | None = None

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
        stt: Any = None,
        tts: Any = None,
        stopwatch: Callable[[], float] = monotonic_ms,
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
        return cls(
            session,
            clock=clock,
            params=params,
            system_two=system_two,
            stt=stt,
            tts=tts,
            stopwatch=stopwatch,
        )

    # -- time ----------------------------------------------------------------------
    def _next_deadline(self) -> float | None:
        due = [d for d in (self.hal.next_delivery_ms(), self.fsm.next_deadline()) if d is not None]
        return min(due) if due else None

    def next_event_ms(self) -> float | None:
        """When something is next due: a provider's answer, a delivery or a deadline."""
        due = [d for d in (self._next_deadline(), self._next_due()) if d is not None]
        return min(due) if due else None

    def _next_due(self) -> float | None:
        return self._inbox[0].at_ms if self._inbox else None

    async def advance(self, to_ms: float, *, inclusive: bool = False) -> None:
        """
        Move the clock to `to_ms`, firing what falls due on the way. At one ms a
        provider's answer comes first — it is an input — then deliveries, then the
        machine's deadlines. Anything at exactly `to_ms` waits for the caller's
        input at `to_ms` unless `inclusive` (the end of a case).
        """
        while True:
            answer, deadline = self._next_due(), self._next_deadline()
            nearest = min(d for d in (answer, deadline, float("inf")) if d is not None)
            if nearest > to_ms or (nearest == to_ms and not inclusive):
                break
            self.clock.now = max(self.clock.now, nearest)
            if answer is not None and answer <= nearest:
                await self._deliver(heapq.heappop(self._inbox))
                continue
            self.hal.run_due()
            for signal in self.fsm.fire_due():
                if signal == "turn_end":
                    await self._turn_ended()
                elif signal == "think_timeout":
                    await self._offline_reply()
        self.clock.now = max(self.clock.now, float(to_ms))

    @property
    def settled(self) -> bool:
        """Nothing left to happen: no turn open, no answer or command pending."""
        return (
            self.fsm.state is VoiceState.IDLE
            and not self._inbox
            and not self.hal.pending_commands()
        )

    async def settle(self, until_ms: float) -> None:
        """After the input ends: run the clock until the session settles, or `until_ms`."""
        for _ in range(SETTLE_STEPS):
            due = self.next_event_ms()
            if self.settled or due is None or due > until_ms:
                return
            await self.advance(due, inclusive=True)

    # -- audio.in (TSK-S3-13) --------------------------------------------------------
    async def feed_audio(self, frame: AudioFrame) -> None:
        """One frame of `audio.in`, at the current clock (the frame's end)."""
        self._rate = frame.sample_rate_hz
        edge = self.vad.push(frame)
        if edge is not None:
            kind, energy = edge
            if kind == "start":
                await self.feed("audio_in_vad_start", {"energy_db": energy})
            else:
                await self.feed("audio_in_vad_end", {})
        if self.fsm.state is VoiceState.LISTENING:
            if self._clip_turn != self.fsm.turn:
                # A new turn: it starts with the pre-roll, so its first syllable is in it.
                self._clip_turn = self.fsm.turn
                self._clip = [f.pcm for f in self._ring]
                self._clip_ms = sum(f.duration_ms for f in self._ring)
            if self._clip_ms < MAX_CLIP_MS:
                self._clip.append(frame.pcm)
                self._clip_ms += frame.duration_ms
        self._ring.append(frame)
        while sum(f.duration_ms for f in self._ring) > PREROLL_MS:
            self._ring.popleft()

    async def play(self, source: Any, *, settle_ms: float = 60_000) -> None:
        """
        A whole `audio.in` source (`SimHAL.audio_file`), frame by frame on the clock;
        then silence until the conversation settles — at most `settle_ms` more.
        """
        origin = self.clock.now
        for frame in source.frames():
            await self.advance(origin + frame.end_ms)
            await self.feed_audio(frame)
        if self.vad.flush():
            await self.feed("audio_in_vad_end", {})  # the input ended mid-speech
        await self.settle(self.clock.now + settle_ms)

    def _take_clip(self, turn: int) -> AudioClip:
        pcm = b"".join(self._clip) if self._clip_turn == turn else b""
        self._clip_turn, self._clip, self._clip_ms = None, [], 0
        return AudioClip(pcm, self._rate, turn)

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
        elif type == "stt_unavailable":
            await self._stt_failed(int(data["turn"]), str(data.get("reason", "")))
        elif type == "system_two_reply":
            await self._system_two_reply(
                int(data["turn"]), data.get("text") or None, data.get("tool_calls") or []
            )
        elif type == "system_two_unavailable":
            if self._awaiting is not None and self.fsm.accepts(self._awaiting):
                await self._offline_reply()  # T09
        elif type == "tts_stream_end":
            self._end_playback()  # the stream ended from outside: the speaker stops too
            self.fsm.reply_ended()
        else:
            raise ValueError(f"not a voice input event: {type!r}")

    async def deliver_due(self, type: str, data: Mapping[str, Any]) -> bool:
        """
        Deliver now the answer of `type` the session has scheduled for this ms —
        for `stt_*`, of the same turn. False when it has none. The corpus runs its
        vectors through fake providers this way (`testing.voice_corpus`): an input
        the providers produce is taken from them, at its place among the inputs.
        """
        match = next(
            (
                due
                for due in sorted(self._inbox)
                if due.at_ms == self.clock.now
                and due.type == type
                and (not type.startswith("stt_") or due.data.get("turn") == data.get("turn"))
            ),
            None,
        )
        if match is None:
            return False
        # What was scheduled before it at this ms goes first (a tts_unavailable before its end).
        ready = [due for due in sorted(self._inbox) if due.at_ms == match.at_ms and due <= match]
        self._cancel(ready)
        for due in ready:
            await self._deliver(due)
        return True

    def _schedule(self, at_ms: float, type: str, data: dict[str, Any]) -> _Due:
        due = _Due(max(float(at_ms), self.clock.now), next(self._seq), type, data)
        heapq.heappush(self._inbox, due)
        return due

    def _cancel(self, dues: list[_Due]) -> None:
        kept = [due for due in self._inbox if all(due is not d for d in dues)]
        if len(kept) != len(self._inbox):
            self._inbox = kept
            heapq.heapify(self._inbox)

    async def _deliver(self, due: _Due) -> None:
        """A scheduled answer at its time: recorded, then acted on, like an input."""
        self.events.emit(due.type, dict(due.data))
        if due.type == "stt_result":
            await self._stt_result(int(due.data["turn"]), str(due.data["text"]))
        elif due.type == "stt_unavailable":
            await self._stt_failed(int(due.data["turn"]), str(due.data["reason"]))
        elif due.type == "tts_stream_end":
            self._playing = None
            self.fsm.reply_ended()  # T11, T12
        # tts_unavailable: recorded only; its tts_stream_end {error} follows

    def _drop(self, turn: int, source: str) -> None:
        """§5.2 step 4: a result of a replaced or concluded turn never acts."""
        self.events.emit("voice_late_result_dropped", {"turn": turn, "input": source})

    # -- STT ---------------------------------------------------------------------------
    async def _turn_ended(self) -> None:
        """T04: the turn closed. Nothing from an earlier turn is awaited any more."""
        turn = self.fsm.turn
        self._transcript, self._awaiting, self._heard_at = "", None, None
        self._stt_sent.clear()
        clip = self._take_clip(turn)
        if self.stt is None:
            return  # the transcript arrives as an `stt_result` input
        self.events.emit(
            "audio_in_segment",
            {
                "sha256": clip.sha256,
                "duration_ms": clip.duration_ms,
                "sample_rate_hz": clip.sample_rate_hz,
            },
        )
        sent = self.clock.now
        self._stt_sent[turn] = sent
        started = self.stopwatch()
        declared: Any = None
        try:
            answer = await self._call(self.stt, "transcribe", clip, role="stt")
            transcript = answer if isinstance(answer, Transcript) else Transcript(answer)
            declared = transcript.latency_ms
            due = ("stt_result", {"turn": turn, "text": clean_transcript(transcript.text, "STT")})
        except SpeechUnavailable as exc:
            declared = exc.latency_ms if declared is None else declared
            due = ("stt_unavailable", {"turn": turn, "reason": exc.why})
        except Exception as exc:
            # An adapter's own bug takes the same degraded path, never a crash. Only the
            # type is kept: the message may carry what was said.
            due = (
                "stt_unavailable",
                {"turn": turn, "reason": f"the STT provider raised {type(exc).__name__} — fix it"},
            )
        latency, problem = self._latency(declared, started, "STT")
        if problem is not None:
            due = ("stt_unavailable", {"turn": turn, "reason": problem})
        self._schedule(sent + latency, *due)

    # -- provider calls ------------------------------------------------------------
    def _bound_s(self, provider: Any) -> float:
        """How long a call to `provider` may take, in wall-clock seconds."""
        timeout = getattr(getattr(provider, "config", None), "timeout_s", None)
        if _positive(timeout):
            return float(timeout) * GRACE + MARGIN_S
        return self.fsm.params.think_timeout_ms / 1000

    async def _call(self, provider: Any, method: str, argument: Any, *, role: str) -> Any:
        """
        ``provider.<method>(argument)``, bounded by `_bound_s`: a hung adapter is a
        failed one (voice_fsm.md §7), never a hung session. An ``async def`` method is
        awaited here; any other runs in a daemon thread, so a blocking one cannot stop
        the loop, and nothing — not `asyncio.run` at exit — waits for a thread that
        never returns. (An async method that blocks the loop itself cannot be bounded.)
        """
        call = getattr(provider, method)
        bound = self._bound_s(provider)
        try:
            if inspect.iscoroutinefunction(call):
                return await asyncio.wait_for(call(argument), timeout=bound)
            loop = asyncio.get_running_loop()
            started = loop.time()
            result = await asyncio.wait_for(_in_thread(loop, call, argument, role), bound)
            if inspect.isawaitable(result):
                left = max(0.0, bound - (loop.time() - started))
                result = await asyncio.wait_for(result, timeout=left)
            return result
        except TimeoutError:
            name = role.upper()
            raise SpeechUnavailable(
                where=f"{name}({type(provider).__name__})",
                why=f"the {name} provider did not answer within {bound:g} s — check it, or its "
                f"[{role}] timeout_s",
                how=f"check the {name} provider, or its [{role}] timeout_s",
                role=role,
            ) from None

    def _latency(self, declared: Any, started: float, name: str) -> tuple[float, str | None]:
        """
        The call's latency in ms on the session's clock: what a simulated provider
        declared, else the wall time measured. A declared value that is not a finite
        number ≥ 0 (NaN, infinity, a string) is refused — the call counts as failed,
        at its measured time — since it would put the answer nowhere on the clock.
        """
        measured = max(0.0, self.stopwatch() - started)
        if declared is None:
            return measured, None
        if (
            isinstance(declared, bool)
            or not isinstance(declared, int | float)
            or not math.isfinite(declared)
            or declared < 0
        ):
            return measured, (
                f"the {name} provider reported latency_ms={declared!r}, not a finite number of "
                "ms ≥ 0 — fix it"
            )
        return float(declared), None

    def _waits(self, turn: int) -> tuple[float | None, float]:
        """(when the turn's wait began, how much of it was STT) for its `turn_latency`."""
        sent = self._stt_sent.pop(turn, None)
        heard = self._heard_at if self._heard_at is not None else self.clock.now
        if sent is None:
            return self._heard_at, 0.0
        return sent, max(0.0, heard - sent)

    async def _stt_result(self, turn: int, text: str) -> None:
        if not self.fsm.accepts(turn) or self.fsm.transcript_taken:
            self._drop(turn, "stt_result")
            return
        if not self.fsm.transcript(turn, text):
            self._stt_sent.pop(turn, None)
            return  # empty: T06
        self._transcript = text
        s = self.session
        answers = s.pending_confirmation() is not None and answer_word(text) is not None
        if self.system_two and not answers and not s.grammar.recognize(text).recognised:
            self._awaiting = turn  # free phrasing: System 2 answers later, or times out
            self._heard_at = self.clock.now
            return
        started, heard_ms = self._waits(turn)
        before = len(self.hal.spoken)
        result = await s.handle(text, heard_after_ms=heard_ms if started is not None else 0.0)
        await self._conclude(turn, text, result, before)

    async def _stt_failed(self, turn: int, reason: str) -> None:
        """§7: STT gone or unusable — the offline line, from the device. Never a c.do()."""
        if not self.fsm.accepts(turn) or self.fsm.transcript_taken:
            self._drop(turn, "stt_unavailable")
            return
        started, heard_ms = self._waits(turn)
        before = len(self.hal.spoken)
        result = await self.session.say_offline(
            "", started_ms=started, perceived_ms=heard_ms, unheard=True
        )
        await self._conclude(turn, None, result, before, stt_failure=reason or "unavailable")

    # -- System 2 -----------------------------------------------------------------------
    async def _system_two_reply(self, turn: int, text: str | None, calls: list[Any]) -> None:
        if self._awaiting != turn or not self.fsm.accepts(turn):
            self._drop(turn, "system_two_reply")
            return
        self._awaiting = None
        tool_calls = [
            ToolCall(str(c["name"]), dict(c.get("arguments") or {}), source="system_two")
            for c in calls
        ]
        started, heard_ms = self._waits(turn)
        self._heard_at = None
        before = len(self.hal.spoken)
        result = await self.session.run_tool_calls(
            self._transcript, tool_calls, text, started_ms=started, perceived_ms=heard_ms
        )
        await self._conclude(turn, self._transcript, result, before)

    async def _offline_reply(self) -> None:
        """§7: provider gone or too slow — say the offline line, as any reply. Never a c.do()."""
        turn = self.fsm.turn
        self._awaiting = None
        if self.stt is not None and turn in self._stt_sent and self._heard_at is None:
            # The think timeout ran out while STT still worked: it is STT that failed. Its
            # answer, when it comes, finds the turn concluded and is dropped (§5.2 step 4).
            reason = "STT did not answer before the think timeout — check [stt] timeout_s"
            self.events.emit("stt_unavailable", {"turn": turn, "reason": reason})
            await self._stt_failed(turn, reason)
            return
        started, heard_ms = self._waits(turn)
        self._heard_at = None
        before = len(self.hal.spoken)
        result = await self.session.say_offline(
            self._transcript, started_ms=started, perceived_ms=heard_ms
        )
        await self._conclude(turn, self._transcript, result, before)

    # -- the reply ------------------------------------------------------------------------
    async def _conclude(
        self,
        turn: int,
        heard: str | None,
        result: Turn,
        spoken_before: int,
        *,
        stt_failure: str | None = None,
    ) -> None:
        record = VoiceTurn(turn, heard, result, stt_failure)
        self.turns.append(record)
        if self.on_turn is not None:
            self.on_turn(record)
        spoken = self.hal.spoken[spoken_before:]
        if not spoken:
            self.fsm.reply_empty()  # T08
            return
        # RFC-0006: a question a person may answer keeps the floor for the answer (T11).
        self.fsm.reply_started(ask=result.confirmation is not None)  # T07
        if self.tts is not None and self.fsm.state is VoiceState.SPEAKING:
            await self._speak(spoken)

    async def _speak(self, texts: list[str]) -> None:
        """
        The reply's sentences through TTS, back to back on the speaker; its end is
        scheduled when the audio runs out. A TTS failure ends the stream with
        ``error`` — the words were still shown (`tts_stream_start`) — never a retry.
        """
        start = self.clock.now
        speaker = self.hal.speaker(called_from="VoiceSession")
        pieces: list[bytes] = []
        latency = 0.0
        budget_ms = float(MAX_REPLY_MS)  # the whole reply, not each sentence
        failure: str | None = None
        for text in texts:
            started = self.stopwatch()
            took: Any = None
            try:
                speech = await self._call(self.tts, "synthesize", text, role="tts")
                if not isinstance(speech, Speech):
                    raise TypeError(f"synthesize() returned {type(speech).__name__}, not Speech")
                took = speech.latency_ms
                piece = self._for_speaker(speech, speaker.sample_rate_hz, budget_ms)
                budget_ms -= len(piece) / 2 * 1000 / speaker.sample_rate_hz
                pieces.append(piece)
            except SpeechUnavailable as exc:
                took = exc.latency_ms if took is None else took
                failure = exc.why
            except Exception as exc:
                failure = f"the TTS provider raised {type(exc).__name__} — fix it"
            spent, problem = self._latency(took, started, "TTS")
            latency += spent
            failure = failure or problem
            if failure is not None:
                break
        at = start + latency
        if failure is not None:
            dues = [
                self._schedule(at, "tts_unavailable", {"reason": failure}),
                self._schedule(
                    at, "tts_stream_end", {"duration_ms": int(at - start), "reason": "error"}
                ),
            ]
            self._playing = (None, dues)
            return
        pcm = b"".join(pieces)
        playback = speaker.play(pcm, at)
        end = at + playback.duration_ms
        data = {"duration_ms": int(end - start), "sha256": pcm_digest(pcm), "reason": "done"}
        self._playing = (playback, [self._schedule(end, "tts_stream_end", data)])

    @staticmethod
    def _for_speaker(speech: Speech, rate: int, budget_ms: float = MAX_REPLY_MS) -> bytes:
        """
        The sentence at the speaker's rate, or `SpeechUnavailable` — checked before
        any sample is converted (`hal.audio.to_speaker`): a header claiming 1 Hz, or a
        reply past its two minutes, costs nothing and never freezes the session.
        """
        if not isinstance(speech.pcm, bytes | bytearray):
            raise SpeechUnavailable(
                where="TTS",
                why=f"the audio is a {type(speech.pcm).__name__}, not bytes — fix the TTS provider",
                how="return Speech(pcm=bytes, …) (perception/providers/base.py)",
                role="tts",
            )
        try:
            return to_speaker(
                bytes(speech.pcm),
                speech.sample_rate_hz,
                speech.channels,
                speech.sample_width,
                to_hz=rate,
                max_ms=budget_ms,
            )
        except ValueError as exc:
            how = "choose a TTS model or voice that returns 16-bit PCM at 8–96 kHz, and shorter replies"
            raise SpeechUnavailable(
                where="TTS", why=f"{exc} — {how}", how=how, role="tts"
            ) from None

    def _stop_speech(self) -> None:
        """§5.2 step 3, called by the machine on barge-in: flush what has not played."""
        self._end_playback()

    def _end_playback(self) -> None:
        if self._playing is None:
            return
        playback, dues = self._playing
        self._playing = None
        if playback is not None:
            # The speaker's one stop rule (`Playback.stop`), for everything on it.
            self.hal.speaker(called_from="VoiceSession").stop(self.clock.now)
        self._cancel(dues)


def _in_thread(loop: asyncio.AbstractEventLoop, call: Any, argument: Any, role: str):
    """`call(argument)` in a daemon thread, as a future of this loop."""
    future: asyncio.Future[Any] = loop.create_future()

    def settle(result: Any, error: BaseException | None) -> None:
        if future.done():
            return  # abandoned: the session moved on
        if error is not None:
            future.set_exception(error)
        else:
            future.set_result(result)

    def work() -> None:
        try:
            outcome: tuple[Any, BaseException | None] = (call(argument), None)
        except BaseException as exc:  # handed to the loop, raised there
            outcome = (None, exc)
        with contextlib.suppress(RuntimeError):  # the loop is closed: nobody waits
            loop.call_soon_threadsafe(settle, *outcome)

    threading.Thread(target=work, name=f"neuroedge-{role}", daemon=True).start()
    return future
