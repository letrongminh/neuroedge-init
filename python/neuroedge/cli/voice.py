"""
`neuroedge run --voice-file` / `record --voice-file` — speak to the agent on
`sim` or `linux` (TSK-S3-13, TSK-S5-08, FR-MDL-09, FR-PER-07).

The WAV file is `audio.in`: its frames go through the wake word (when `[wake_word]`
is configured — TSK-I4-01) and VAD, and the conversation state machine on a virtual
clock (`perception.VoiceSession.play`), each turn's audio to the `[stt]` provider
(or `[stt.fallback]` when the primary is unavailable, Q-14), each transcript down
the typed line's path — command grammar or System 2, `c.do()`, the gate — and each
reply to the `[tts]` provider and the speaker, which `--voice-out` writes as WAV.
STT's and TTS's real latency is measured and placed on that clock, so barge-in and
`turn_latency` see it. A `[system_two]` model answers inline, at the transcript's
time: its wait is bounded by its own `timeout_s`, and neither the clock nor the
think timeout sees it.

Typed input stays the default and keyless (Q-15): without `[stt]` this exits 1
and says so. A provider that fails takes voice_fsm.md §7 (the offline line);
the run still exits 0, as a BLOCK does — the device did its job.
"""

from __future__ import annotations

import asyncio
import threading
from pathlib import Path

from rich.console import Console
from rich.markup import escape

from ..errors import AgentManifestError, NeuroEdgeError
from ..perception import VirtualClock, VoiceParams, VoiceSession, VoiceTurn
from ..perception.live_voice import build_live_voice, count_events
from ..perception.providers import (
    load_speech_configs,
    load_wake_word_config,
    make_speech,
    make_wake_word,
)
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
        # From the configs just read: agent.toml is parsed once per run.
        stt = make_speech(stt_config, manifest.root)
        stt_fallback = (
            None if stt_config.fallback is None else make_speech(stt_config.fallback, manifest.root)
        )
        tts = None if tts_config is None else make_speech(tts_config, manifest.root)
        wake_config = load_wake_word_config(manifest)
        wake = None if wake_config is None else make_wake_word(wake_config, manifest.root)
        source = session.hal.audio_file(voice_file, called_from="neuroedge --voice-file")
    except NeuroEdgeError as error:
        return _error(err_console, error)
    console.print(
        f"[bold]{escape(manifest.label)}[/bold] on [cyan]{escape(session.target)}[/cyan] "
        f"([cyan]{escape(session.hal.board.id)}[/cyan]) · voice file {escape(str(voice_file))} "
        f"({source.duration_ms / 1000:.1f} s, {source.sample_rate_hz} Hz)"
    )
    console.print(f"  stt: {escape(stt_config.label)}")
    if stt_fallback is not None:
        console.print(f"  stt fallback: {escape(stt_config.fallback.label)}")
    tts_line = tts_config.label if tts_config is not None else "none — replies are shown, not heard"
    console.print(f"  tts: {escape(tts_line)}")
    wake_line = (
        "none — a turn opens on speech (VAD, T01)" if wake_config is None else wake_config.label
    )
    console.print(f"  wake word: {escape(wake_line)}")
    voice = VoiceSession(
        session,
        clock=clock,
        # No wake word ⇒ VAD opens a turn (T01); with one, the word does and VAD
        # never opens one alone (TSK-I4-01).
        params=VoiceParams(vad_activation=wake is None),
        stt=stt,
        stt_fallback=stt_fallback,
        stt_label=f"stt ({stt_config.label})",
        stt_fallback_label=f"stt.fallback ({stt_config.fallback.label})"
        if stt_config.fallback is not None
        else "stt.fallback",
        tts=tts if tts is not None else NoSpeech(),
        wake_word=wake,
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


def run_voice_live(
    session: SimSession,
    clock: VirtualClock,
    *,
    half_duplex: bool = False,
    trace_out: Path | None = None,
    console: Console,
    err_console: Console,
    stop: threading.Event | None = None,
) -> int:
    """Run a live microphone voice session and return the exit code; the session is closed."""
    try:
        return _run_live(session, clock, half_duplex, console, err_console, stop=stop)
    finally:
        try:
            if trace_out is not None:
                written = session.write_trace(trace_out)
                console.print(f"trace: {escape(str(trace_out))} ({len(written['events'])} events)")
        finally:
            session.close()


def _run_live(
    session: SimSession,
    clock: VirtualClock,
    half_duplex: bool,
    console: Console,
    err_console: Console,
    *,
    stop: threading.Event | None = None,
) -> int:
    manifest = session.manifest
    try:
        parts = build_live_voice(session, clock, on_turn=_printer(session, clock, console))
        source = session.hal.audio_source(called_from="neuroedge run --mic")
        sink = session.hal.audio_sink(called_from="neuroedge run --mic")
    except NeuroEdgeError as error:
        return _error(err_console, error)
    voice, stt_config, tts_config, wake_config = parts
    stt_fallback = voice.stt_fallback

    in_device = getattr(source, "device", None) or "default"
    out_device = getattr(sink, "device", None) or "default"
    try:
        sd = session.hal._device()
        in_name = sd.query_devices(source.device, "input").get("name", in_device)
    except Exception:
        in_name = in_device
    try:
        sd = session.hal._device()
        out_name = sd.query_devices(sink.device, "output").get("name", out_device)
    except Exception:
        out_name = out_device

    console.print(
        f"[bold]{escape(manifest.label)}[/bold] on [cyan]{escape(session.target)}[/cyan] "
        f"([cyan]{escape(session.hal.board.id)}[/cyan]) · live audio"
    )
    console.print(f"  mic (input): {escape(str(in_name))}")
    console.print(f"  speaker (output): {escape(str(out_name))}")
    if not half_duplex:
        console.print(
            "  Dùng tai nghe — loa ngoài thì thêm --half-duplex (tắt micro khi agent đang nói, không cắt lời được)"
        )
    else:
        console.print("  half-duplex: bật (tắt micro khi agent đang nói, không cắt lời được)")
    console.print(f"  stt: {escape(stt_config.label)}")
    if stt_fallback is not None:
        console.print(f"  stt fallback: {escape(stt_config.fallback.label)}")
    tts_line = tts_config.label if tts_config is not None else "none — replies are shown, not heard"
    console.print(f"  tts: {escape(tts_line)}")
    wake_line = (
        "none — a turn opens on speech (VAD, T01)" if wake_config is None else wake_config.label
    )
    console.print(f"  wake word: {escape(wake_line)}")

    stop_event = stop if stop is not None else threading.Event()
    try:
        asyncio.run(voice.play_live(source, half_duplex=half_duplex, stop=stop_event))
    except KeyboardInterrupt:
        pass
    except NeuroEdgeError as error:
        return _error(err_console, error)
    _summary(voice, console)
    return 0


def _summary(voice: VoiceSession, console: Console) -> None:
    count = count_events(voice)
    console.print("voice: " + " · ".join(f"{value} {name}" for name, value in count.items()))
    if not voice.turns:
        console.print(
            "  [yellow]no turn was heard[/yellow]: the file is silent to the VAD "
            "(below −40 dBFS), or ends before a turn does"
        )
