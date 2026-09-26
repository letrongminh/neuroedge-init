"""
PCM audio for `audio.in` / `audio.out` on a host (TSK-S3-13).

`sim` has no microphone and no speaker, so the two primitives run on files:

* **`audio.in`** — `WavSource` reads a WAV file of 16-bit PCM, mono, at the
  board's `audio_in.sample_rate_hz` (`boards/sim-default.toml`: the reference
  board's rate — never richer than it, CHANGELOG §3.3 #7) and yields it in
  20 ms frames. `EnergyVAD` marks where speech starts and ends, the part of
  `audio.in` the board's front end does (`audio_in.vad = true`).
* **`audio.out`** — `Speaker` is a timeline: each reply's audio is placed at
  the (virtual) time it plays, cut where barge-in stops it, and written to one
  WAV file at the end, at the board's `audio_out.sample_rate_hz`.

Only the standard library (`wave`, `array`), so `pip install neuroedge` stays as
it is (FR-DX-02). `linux` brings the same two roles on `sounddevice` (TSK-S5-08):
a source of `AudioFrame`s, and an output with `play()` / `stop()`.
"""

from __future__ import annotations

import hashlib
import math
import struct
import sys
import wave
from array import array
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from ..errors import BoardCapabilityError

FRAME_MS = 20  # one Opus frame (PRD Appendix D.2): the unit the board's front end works in
SAMPLE_WIDTH = 2  # 16-bit PCM
MAX_FILE_S = 600  # a voice file is read whole: ten minutes is 19 MB at 16 kHz
SILENCE_DB = -120.0  # the energy of digital silence, instead of -inf


def pcm_samples(pcm: bytes) -> array:
    """16-bit little-endian PCM (WAV's byte order) as native integers."""
    samples = array("h")
    samples.frombytes(pcm[: len(pcm) - len(pcm) % SAMPLE_WIDTH])
    if sys.byteorder == "big":
        samples.byteswap()
    return samples


def samples_pcm(samples: array) -> bytes:
    if sys.byteorder == "big":
        samples = array("h", samples)
        samples.byteswap()
    return samples.tobytes()


def energy_db(pcm: bytes) -> float:
    """RMS level of 16-bit PCM in dBFS, one decimal; digital silence is -120."""
    samples = pcm_samples(pcm)
    if not samples:
        return SILENCE_DB
    mean_square = math.fsum(s * s for s in samples) / len(samples)
    if mean_square <= 0:
        return SILENCE_DB
    return round(max(SILENCE_DB, 10 * math.log10(mean_square / 32768.0**2)), 1)


def duration_ms(pcm: bytes, sample_rate_hz: int) -> int:
    """Whole milliseconds of mono 16-bit PCM."""
    return (len(pcm) // SAMPLE_WIDTH) * 1000 // sample_rate_hz


def pcm_digest(pcm: bytes) -> str:
    return "sha256:" + hashlib.sha256(pcm).hexdigest()


def to_mono(pcm: bytes, channels: int) -> bytes:
    """Average interleaved 16-bit channels into one."""
    if channels == 1:
        return pcm
    samples = pcm_samples(pcm)
    frames = len(samples) // channels
    mono = array(
        "h", (sum(samples[i * channels : (i + 1) * channels]) // channels for i in range(frames))
    )
    return samples_pcm(mono)


def resample(pcm: bytes, from_hz: int, to_hz: int) -> bytes:
    """
    Mono 16-bit PCM from one rate to another by linear interpolation — enough to
    bring a TTS reply (24 kHz from most providers) to the board's speaker rate.
    """
    if from_hz == to_hz:
        return pcm
    samples = pcm_samples(pcm)
    if not samples:
        return b""
    count = len(samples) * to_hz // from_hz
    out = array("h", bytes(2 * count))
    last = len(samples) - 1
    step = from_hz / to_hz
    for i in range(count):
        position = i * step
        left = int(position)
        if left >= last:
            out[i] = samples[last]
            continue
        fraction = position - left
        out[i] = int(round(samples[left] + (samples[left + 1] - samples[left]) * fraction))
    return samples_pcm(out)


@dataclass(frozen=True)
class AudioFrame:
    """`duration_ms` of mono 16-bit PCM starting `start_ms` into its source."""

    pcm: bytes
    start_ms: int
    duration_ms: int
    sample_rate_hz: int

    @property
    def end_ms(self) -> int:
        return self.start_ms + self.duration_ms


@dataclass(frozen=True)
class WavSource:
    """A WAV file as `audio.in`: read whole, checked against the board, then framed."""

    path: Path
    pcm: bytes
    sample_rate_hz: int

    @property
    def duration_ms(self) -> int:
        return duration_ms(self.pcm, self.sample_rate_hz)

    @classmethod
    def open(cls, path: str | Path, *, sample_rate_hz: int, called_from: str) -> WavSource:
        """
        `BoardCapabilityError` for anything the board's `audio.in` would not take:
        a file that is not PCM WAV, another rate, more than one channel, another
        sample width — the reference board does not resample, so neither does `sim`.
        """
        path = Path(path)
        where = f"{called_from} -> audio.in {path}"
        convert = (
            f"convert it: ffmpeg -i <in> -ar {sample_rate_hz} -ac 1 -c:a pcm_s16le {path.name}"
        )
        try:
            with wave.open(str(path), "rb") as wav:
                channels = wav.getnchannels()
                width = wav.getsampwidth()
                rate = wav.getframerate()
                frames = wav.getnframes()
                if frames > MAX_FILE_S * rate:
                    raise BoardCapabilityError(
                        where=where,
                        why=f"the file is {frames / rate:.0f} s long; a voice file is read whole, "
                        f"up to {MAX_FILE_S} s",
                        how="cut it into shorter files",
                    )
                pcm = wav.readframes(frames)
        except FileNotFoundError as exc:
            raise BoardCapabilityError(
                where=where, why="no such file", how="pass the path of a .wav file"
            ) from exc
        except (wave.Error, EOFError) as exc:
            raise BoardCapabilityError(
                where=where, why=f"not a PCM WAV file ({exc})", how=convert
            ) from exc
        except OSError as exc:
            raise BoardCapabilityError(
                where=where,
                why=f"cannot read the file ({exc.strerror or exc})",
                how="check the path",
            ) from exc
        wanted = (1, SAMPLE_WIDTH, sample_rate_hz)
        if (channels, width, rate) != wanted:
            raise BoardCapabilityError(
                where=where,
                why=f"the board's audio.in takes {sample_rate_hz} Hz mono 16-bit PCM; the file is "
                f"{rate} Hz, {channels} channel(s), {8 * width}-bit",
                how=convert,
            )
        return cls(path, pcm, rate)

    def frames(self, frame_ms: int = FRAME_MS) -> Iterator[AudioFrame]:
        size = self.sample_rate_hz * frame_ms // 1000 * SAMPLE_WIDTH
        for index, offset in enumerate(range(0, len(self.pcm), size)):
            chunk = self.pcm[offset : offset + size]
            yield AudioFrame(
                chunk,
                index * frame_ms,
                duration_ms(chunk, self.sample_rate_hz),
                self.sample_rate_hz,
            )


class EnergyVAD:
    """
    Voice activity from frame energy: speech starts after `start_ms` of frames at
    or above `threshold_db`, and ends after `end_ms` below it. The end of the
    *turn* is the conversation state machine's business (`end_of_turn_silence_ms`,
    docs/spec/voice_fsm.md §6); this only says where sound is.

    Deterministic on its input — no clock, no randomness — so a voice file gives
    the same edges on every run.
    """

    def __init__(
        self,
        threshold_db: float = -40.0,
        *,
        start_ms: int = 60,
        end_ms: int = 200,
        frame_ms: int = FRAME_MS,
    ) -> None:
        self.threshold_db = threshold_db
        self._start_frames = max(1, math.ceil(start_ms / frame_ms))
        self._end_frames = max(1, math.ceil(end_ms / frame_ms))
        self.speaking = False
        self._run = 0  # consecutive frames on the other side of the threshold

    def push(self, frame: AudioFrame) -> tuple[str, float] | None:
        """``("start", energy_db)`` or ``("end", energy_db)`` when this frame is an edge."""
        energy = energy_db(frame.pcm)
        loud = energy >= self.threshold_db
        if loud == self.speaking:
            self._run = 0
            return None
        self._run += 1
        if self._run < (self._end_frames if self.speaking else self._start_frames):
            return None
        self._run = 0
        self.speaking = loud
        return ("start" if loud else "end"), energy

    def flush(self) -> bool:
        """The input ended: True when speech was still on (the caller ends it)."""
        speaking, self.speaking, self._run = self.speaking, False, 0
        return speaking


@dataclass
class Playback:
    """One reply on the speaker, from `start_ms`; `stop()` cuts it."""

    start_ms: float
    pcm: bytes
    sample_rate_hz: int
    stopped_at_ms: float | None = None

    @property
    def duration_ms(self) -> int:
        return duration_ms(self.pcm, self.sample_rate_hz)

    @property
    def played(self) -> bytes:
        """The PCM that reached the speaker: all of it, or up to where it was stopped."""
        if self.stopped_at_ms is None:
            return self.pcm
        elapsed = max(0.0, self.stopped_at_ms - self.start_ms)
        samples = int(elapsed * self.sample_rate_hz / 1000)
        return self.pcm[: samples * SAMPLE_WIDTH]


@dataclass
class Speaker:
    """
    `audio.out` as a timeline at the board's output rate. `play()` places a reply;
    `stop()` flushes what has not played yet (barge-in, docs/spec/voice_fsm.md
    §5.2 step 3); `write()` renders the whole session, silence between replies.
    """

    sample_rate_hz: int
    playbacks: list[Playback] = field(default_factory=list)

    def play(self, pcm: bytes, start_ms: float) -> Playback:
        playback = Playback(float(start_ms), pcm, self.sample_rate_hz)
        self.playbacks.append(playback)
        return playback

    def stop(self, at_ms: float) -> None:
        for playback in self.playbacks:
            if playback.stopped_at_ms is None and at_ms < playback.start_ms + playback.duration_ms:
                playback.stopped_at_ms = max(playback.start_ms, float(at_ms))

    def render(self) -> bytes:
        out = bytearray()
        for playback in sorted(self.playbacks, key=lambda p: p.start_ms):
            start = int(playback.start_ms * self.sample_rate_hz / 1000) * SAMPLE_WIDTH
            if start > len(out):
                out.extend(bytes(start - len(out)))
            played = playback.played
            out[start : start + len(played)] = played
        return bytes(out)

    def write(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(SAMPLE_WIDTH)
            wav.setframerate(self.sample_rate_hz)
            wav.writeframes(self.render())
        return path


def wav_bytes(pcm: bytes, sample_rate_hz: int) -> bytes:
    """Mono 16-bit PCM as a WAV file in memory — what an STT upload carries."""
    import io

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(SAMPLE_WIDTH)
        wav.setframerate(sample_rate_hz)
        wav.writeframes(pcm)
    return buffer.getvalue()


def read_wav_bytes(data: bytes) -> tuple[bytes, int, int, int]:
    """
    (pcm, sample_rate_hz, channels, sample_width) of a PCM WAV file in memory.
    Tolerant of the headers a streaming server writes before it knows the length
    (a `data` size of 0 or 0xFFFFFFFF): the data then runs to the end of the
    bytes. `ValueError` for anything that is not PCM WAV.
    """
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise ValueError("not a RIFF/WAVE file")
    position, fmt = 12, None
    while position + 8 <= len(data):
        chunk = data[position : position + 4]
        size = int.from_bytes(data[position + 4 : position + 8], "little")
        body = position + 8
        if chunk == b"fmt ":
            if size < 16 or body + 16 > len(data):
                raise ValueError("truncated fmt chunk")
            tag, channels, rate, _, _, bits = struct.unpack("<HHIIHH", data[body : body + 16])
            if tag == 0xFFFE and size >= 40:  # WAVE_FORMAT_EXTENSIBLE: the sub-format says
                tag = int.from_bytes(data[body + 24 : body + 26], "little")
            if tag != 1:
                raise ValueError(f"format tag {tag} is not PCM")
            fmt = (rate, channels, bits // 8)
        elif chunk == b"data":
            if fmt is None:
                raise ValueError("data before fmt")
            end = len(data) if size in (0, 0xFFFFFFFF) or body + size > len(data) else body + size
            rate, channels, width = fmt
            if channels < 1 or width < 1 or rate < 1:
                raise ValueError("invalid fmt chunk")
            pcm = data[body:end]
            return pcm[: len(pcm) - len(pcm) % (channels * width)], rate, channels, width
        if size == 0xFFFFFFFF:
            break
        position = body + size + (size & 1)
    raise ValueError("no data chunk")
