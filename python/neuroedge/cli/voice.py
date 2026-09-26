"""
`neuroedge run --voice-file` / `record --voice-file` — speak to the agent on
`sim` (TSK-S3-13, FR-MDL-09, FR-PER-07).

The WAV file is `audio.in`: its frames go through VAD and the conversation state
machine on a virtual clock (`perception.VoiceSession.play`), each turn's audio
to the `[stt]` provider, each transcript down the typed line's path — command
grammar or System 2, `c.do()`, the gate — and each reply to the `[tts]` provider
and the speaker, which `--voice-out` writes as WAV. A provider's real latency is
measured and placed on that clock, so barge-in and `turn_latency` see it.

Typed input stays the default and keyless (Q-15): without `[stt]` this exits 1
and says so. A provider that fails takes voice_fsm.md §7 (the offline line);
the run still exits 0, as a BLOCK does — the device did its job.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.markup import escape

from ..errors import AgentManifestError, NeuroEdgeError
from ..perception import VirtualClock, VoiceParams, VoiceSession, VoiceTurn
from ..perception.providers import load_speech_configs, speech_for
from ..perception.providers.base import NoSpeech
from ..sim import SimSession
from .run import render_turn


def _error(err_console: Console, error: NeuroEdgeError) -> int:
    err_console.print(f"[bold red]✗ {error.code}[/bold red] [cyan]{escape(error.where)}[/cyan]")
    err_console.print(f"  why: {escape(error.why)}")
    err_console.print(f"  fix: {escape(error.how)}")
    return 1


def _printer(session: SimSession, clock: VirtualClock, console: Console):
    frames = {"before": len(session.hal.frames)}

    def show(turn: VoiceTurn) -> None:
        at = f"{clock.now / 1000:.1f} s"
        if turn.stt_failure is not None:
            console.print(
                f"[bold]turn {turn.turn}[/bold] · {at} · [yellow]STT unavailable:[/yellow] "
                f"{escape(turn.stt_failure)} — no transcript, no action (voice_fsm.md §7)"
            )
            if turn.result.reply is not None:
                console.print(
                    f"  [bold]says[/bold] [dim]({turn.result.reply_source})[/dim]: "
                    f"{escape(turn.result.reply)}"
                )
            return
        console.print(f"[bold]turn {turn.turn}[/bold] · {at} · heard: “{escape(turn.heard or '')}”")
        render_turn(turn.result, session, console, frames["before"])
        frames["before"] = len(session.hal.frames)

    return show


def run_voice(
    session: SimSession,
    clock: VirtualClock,
    voice_file: Path,
    voice_out: Path | None,
    trace_out: Path | None,
    console: Console,
    err_console: Console,
) -> int:
    """Play `voice_file` to the agent and return the exit code; the session is closed."""
    try:
        return _run(session, clock, voice_file, voice_out, console, err_console)
    finally:
        try:
            if trace_out is not None:
                written = session.write_trace(trace_out)
                console.print(f"trace: {escape(str(trace_out))} ({len(written['events'])} events)")
        finally:
            session.close()


def _run(
    session: SimSession,
    clock: VirtualClock,
    voice_file: Path,
    voice_out: Path | None,
    console: Console,
    err_console: Console,
) -> int:
    manifest = session.manifest
    try:
        stt_config, tts_config = load_speech_configs(manifest)
        if stt_config is None:
            raise AgentManifestError(
                where=f"{manifest.source} -> [stt]",
                why="--voice-file needs a speech-to-text provider, and the agent declares none",
                how="add [stt] with model and api_key_env, or the base_url of a local server "
                '(docs/user/huong-dan.md); or type the command: neuroedge run -c "…" (Q-15)',
            )
        if voice_out is not None and tts_config is None:
            raise AgentManifestError(
                where=f"{manifest.source} -> [tts]",
                why="--voice-out writes what the device said, and without [tts] it says nothing "
                "out loud — replies are shown only",
                how="add [tts] with base_url, model, voice (and api_key_env), or drop --voice-out",
            )
        stt, tts = speech_for(manifest)
        source = session.hal.audio_file(voice_file, called_from="neuroedge --voice-file")
    except NeuroEdgeError as error:
        return _error(err_console, error)
    console.print(
        f"[bold]{escape(manifest.label)}[/bold] on [cyan]{escape(session.target)}[/cyan] "
        f"([cyan]{escape(session.hal.board.id)}[/cyan]) · voice file {escape(str(voice_file))} "
        f"({source.duration_ms / 1000:.1f} s, {source.sample_rate_hz} Hz)"
    )
    console.print(f"  stt: {escape(stt_config.label)}")
    tts_line = tts_config.label if tts_config is not None else "none — replies are shown, not heard"
    console.print(f"  tts: {escape(tts_line)}")
    voice = VoiceSession(
        session,
        clock=clock,
        # sim has no wake-word model (TSK-I4-01): a voice file opens a turn by VAD (T01).
        params=VoiceParams(vad_activation=True),
        stt=stt,
        tts=tts if tts is not None else NoSpeech(),
        on_turn=_printer(session, clock, console),
    )
    try:
        asyncio.run(voice.play(source))
    except NeuroEdgeError as error:
        return _error(err_console, error)
    _summary(voice, console)
    if voice_out is not None:
        speaker = session.hal.speaker(called_from="neuroedge --voice-out")
        try:
            path = speaker.write(voice_out)
        except OSError as exc:
            return _error(
                err_console,
                NeuroEdgeError(
                    where=f"--voice-out {voice_out}",
                    why=f"cannot write the WAV file ({exc.strerror or exc})",
                    how="pass a writable path to a .wav file",
                ),
            )
        seconds = len(speaker.render()) / 2 / speaker.sample_rate_hz
        console.print(
            f"voice out: {escape(str(path))} ({seconds:.1f} s, {speaker.sample_rate_hz} Hz)"
        )
    return 0


def _summary(voice: VoiceSession, console: Console) -> None:
    events = voice.events
    count: dict[str, Any] = {
        "turns": len(voice.turns),
        "barge-in": sum(
            1 for e in events.of_type("tts_stream_end") if e.get("reason") == "barge_in"
        )
        + sum(
            1
            for e in events.of_type("voice_state_changed")
            if e["to"] == "BARGE_IN" and e["from"] == "THINKING"
        ),
        "STT unavailable": len(events.of_type("stt_unavailable")),
        "TTS unavailable": len(events.of_type("tts_unavailable")),
        "cancelled commands": len(events.of_type("actuator_aborted")),
    }
    console.print("voice: " + " · ".join(f"{value} {name}" for name, value in count.items()))
    if not voice.turns:
        console.print(
            "  [yellow]no turn was heard[/yellow]: the file is silent to the VAD "
            "(below −40 dBFS), or ends before a turn does"
        )
