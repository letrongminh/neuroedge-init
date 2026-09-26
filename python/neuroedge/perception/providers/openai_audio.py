"""
STT and TTS over the OpenAI audio API — the default speech contract (Q-12).

    POST {base_url}/audio/transcriptions   multipart: file, model, language?, response_format=json
    POST {base_url}/audio/speech           json: model, voice, input, response_format=wav

One adapter for every server that speaks it, chosen by `base_url` in `[stt]` /
`[tts]` (FR-MDL-09): OpenAI, Groq (``https://api.groq.com/openai/v1``),
faster-whisper-server / speaches, Kokoro-FastAPI (``http://localhost:8880/v1``).

This module is the protocol mapping only. The HTTP — no redirect, no proxy, the
answer read against a deadline, a size cap, a key that is a key — is
`neuroedge.net`, shared with System 1's model. Every failure raises
`SpeechUnavailable` saying what to do; the voice driver turns it into voice_fsm.md
§7. Before any network call the key's variable must be set, or nothing is sent. The
key goes only in the ``Authorization`` header and is never in an error: a network
failure is reported by its class name. A response body is never quoted in an error —
it may echo what was said, and errors reach the trace, where `--anonymize` hashes
only the text fields.
"""

from __future__ import annotations

import asyncio
import http.client
import json
import os
import time
import urllib.error
import uuid
from collections.abc import Mapping
from typing import Any

from ... import net
from ...hal.audio import read_wav_bytes
from .base import AudioClip, Speech, SpeechUnavailable, Transcript, clean_transcript
from .config import SpeechConfig

GRACE = 1.25  # the whole call may take timeout_s × GRACE before it is abandoned
MIN_CLIP_MS = 100  # the API refuses shorter audio; a clip this short holds no words
USER_AGENT = "neuroedge-speech/1"
MAX_ANSWER_BYTES = {"stt": 1 << 20, "tts": 32 << 20}  # a transcript; ~10 min of 24 kHz speech


def _failure(status: int | None) -> tuple[str, str]:
    """(why, how) for an HTTP status, or for no answer at all (None)."""
    if status is None:
        return "the server could not be reached", "check the network and base_url"
    if status in (401, 403):
        return f"the server rejected the API key (HTTP {status})", "check the key in api_key_env"
    if status == 404:
        return (
            "the server has no such endpoint or model (HTTP 404)",
            "check base_url (it usually ends in /v1) and model",
        )
    if status == 413:
        return "the audio is too large for the server (HTTP 413)", "speak in shorter turns"
    if status == 429:
        return "the server is rate limiting this key (HTTP 429)", "wait, or check the plan's quota"
    if 300 <= status < 400:
        return (
            f"the server redirected the request (HTTP {status}); a key never follows a redirect",
            "set base_url to the final URL",
        )
    if 400 <= status < 500:
        return f"the server refused the request (HTTP {status})", "check model, voice and language"
    return f"the server failed (HTTP {status})", "try again; check the provider's status"


class _OpenAIAudio:
    role = ""
    name = "openai"

    def __init__(
        self,
        config: SpeechConfig,
        *,
        environ: Mapping[str, str] | None = None,
        opener: Any = None,
    ) -> None:
        if config.role != self.role:
            raise ValueError(f"{type(self).__name__} takes a [{self.role}] config")
        self.config = config
        self.model = config.model
        self.environ = os.environ if environ is None else environ
        self._opener = opener if opener is not None else net.make_opener()

    @property
    def where(self) -> str:
        return f"{self.role.upper()}(openai:{self.model} at {self.config.base_url})"

    def _unavailable(self, why: str, how: str, *, called: bool = True) -> SpeechUnavailable:
        # `why` is what the trace records (`*_unavailable.reason`): it says what to do too.
        return SpeechUnavailable(
            where=self.where, why=f"{why} — {how}", how=how, role=self.role, called=called
        )

    def _timed_out(self) -> SpeechUnavailable:
        return self._unavailable(
            f"the server did not answer within {self.config.timeout_s:g} s",
            f"try again, or raise timeout_s in [{self.role}]",
        )

    def _key(self) -> str | None:
        name = self.config.api_key_env
        if name is None:
            return None  # a keyless server
        try:
            key = net.env_key(self.environ, name)
        except net.KeyUnusable:
            raise self._unavailable(
                f"{name} holds spaces or control characters inside the key (nothing was sent)",
                f"export {name} again with the key alone, on one line",
                called=False,
            ) from None
        if key is None:
            raise self._unavailable(
                f"{name} is not set (nothing was sent)",
                f"export {name}=<your key>, or remove [{self.role}]",
                called=False,
            )
        return key

    def _send(
        self, path: str, body: bytes, content_type: str, key: str | None, deadline: float
    ) -> bytes:
        """POST, in a worker thread: the body of a 2xx answer, or `SpeechUnavailable`."""
        headers = {"Content-Type": content_type, "User-Agent": USER_AGENT}
        if key is not None:
            headers["Authorization"] = f"Bearer {key}"
        limit = MAX_ANSWER_BYTES[self.role]
        try:
            status, data = net.post(
                f"{self.config.base_url}{path}",
                headers,
                body,
                timeout_s=self.config.timeout_s,
                deadline=deadline,
                max_bytes=limit,
                opener=self._opener,
            )
        except net.TooLarge:
            raise self._unavailable(
                f"the server's answer is larger than {limit >> 20} MB", "check base_url and model"
            ) from None
        except TimeoutError:
            raise self._timed_out() from None
        except (urllib.error.URLError, OSError, http.client.HTTPException) as exc:
            reason = getattr(exc, "reason", exc)
            if isinstance(reason, TimeoutError):
                raise self._timed_out() from None
            why, how = _failure(None)
            raise self._unavailable(f"{why} ({type(reason).__name__})", how) from None
        if not 200 <= status < 300:
            why, how = _failure(status)
            raise self._unavailable(why, how)
        return data

    async def _post(self, path: str, body: bytes, content_type: str) -> bytes:
        """
        The request in a daemon thread, awaited for at most `timeout_s` × GRACE. On
        a timeout nothing waits for the thread — not this call, not `asyncio.run` at
        exit — and the thread itself ends at that deadline (`net.post`).
        """
        key = self._key()
        budget = self.config.timeout_s * GRACE
        pending = net.in_daemon_thread(
            self._send,
            path,
            body,
            content_type,
            key,
            time.monotonic() + budget,
            name=f"neuroedge-{self.role}",
        )
        try:
            return await asyncio.wait_for(pending, timeout=budget)
        except TimeoutError:
            raise self._timed_out() from None


def multipart(fields: Mapping[str, str], file_name: str, file: bytes, file_type: str):
    """(body, content type) of a multipart/form-data upload with one file."""
    boundary = f"neuroedge-{uuid.uuid4().hex}"
    parts: list[bytes] = [
        f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
        for name, value in fields.items()
    ]
    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{file_name}"\r\n'
        f"Content-Type: {file_type}\r\n\r\n".encode()
        + file
        + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


class OpenAITranscriber(_OpenAIAudio):
    """STT: ``await transcriber.transcribe(clip)`` → `Transcript`."""

    role = "stt"

    async def transcribe(self, clip: AudioClip) -> Transcript:
        if clip.duration_ms < MIN_CLIP_MS:
            return Transcript("")  # too short to hold a word: heard nothing, nothing sent
        fields = {"model": self.model, "response_format": "json"}
        if self.config.language:
            fields["language"] = self.config.language
        body, content_type = multipart(fields, f"turn-{clip.turn}.wav", clip.wav(), "audio/wav")
        data = await self._post("/audio/transcriptions", body, content_type)
        try:
            answer = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise self._unavailable(
                "the server's answer is not JSON", "check base_url: it must serve the OpenAI API"
            ) from None
        if not isinstance(answer, dict) or "text" not in answer:
            raise self._unavailable(
                "the server's answer has no `text`", "check base_url: it must serve the OpenAI API"
            )
        return Transcript(clean_transcript(answer["text"], self.where))


class OpenAISpeaker(_OpenAIAudio):
    """TTS: ``await speaker.synthesize(text)`` → `Speech` (16-bit PCM from a WAV answer)."""

    role = "tts"

    async def synthesize(self, text: str) -> Speech:
        request = {
            "model": self.model,
            "voice": self.config.voice,
            "input": text,
            "response_format": "wav",
        }
        body = json.dumps(request, ensure_ascii=False).encode("utf-8")
        data = await self._post("/audio/speech", body, "application/json")
        try:
            pcm, rate, channels, width = read_wav_bytes(data)
        except ValueError as exc:
            # `read_wav_bytes` words its own errors; the response body is never quoted.
            raise self._unavailable(
                f"the server's answer is not a PCM WAV file ({exc})", "check base_url and model"
            ) from None
        if width != 2:
            raise self._unavailable(
                f"the server sent {8 * width}-bit audio; the speaker plays 16-bit PCM",
                "choose a model or server that returns 16-bit WAV",
            )
        return Speech(pcm, rate, channels, width)
