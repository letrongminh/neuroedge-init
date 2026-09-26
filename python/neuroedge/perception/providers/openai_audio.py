"""
STT and TTS over the OpenAI audio API — the default speech contract (Q-12).

    POST {base_url}/audio/transcriptions   multipart: file, model, language?, response_format=json
    POST {base_url}/audio/speech           json: model, voice, input, response_format=wav

One adapter for every server that speaks it, chosen by `base_url` in `[stt]` /
`[tts]` (FR-MDL-09): OpenAI, Groq (``https://api.groq.com/openai/v1``),
faster-whisper-server / speaches, Kokoro-FastAPI (``http://localhost:8880/v1``).

The standard library only (`urllib`): no SDK to install, so `pip install
neuroedge` is unchanged (FR-DX-02). Every failure raises `SpeechUnavailable`
saying what to do; the voice driver turns it into voice_fsm.md §7. Before any
network call the key's variable must be set, or nothing is sent. The key goes
only in the ``Authorization`` header, is masked out of every error, and never
follows a redirect: redirects are refused, since urllib would forward the header
to wherever the server points. A response body is never quoted in an error — it
may echo what was said, and errors reach the trace, where `--anonymize` hashes
only the text fields.
"""

from __future__ import annotations

import asyncio
import http.client
import json
import os
import urllib.error
import urllib.request
import uuid
from collections.abc import Mapping
from typing import Any

from ...hal.audio import read_wav_bytes
from ...models.providers.base import scrub
from .base import AudioClip, Speech, SpeechUnavailable, Transcript, clean_transcript
from .config import SpeechConfig

GRACE = 1.25  # the whole call may take timeout_s × GRACE before it is abandoned
MIN_CLIP_MS = 100  # the API refuses shorter audio; a clip this short holds no words
USER_AGENT = "neuroedge-speech/1"
MAX_ANSWER_BYTES = {"stt": 1 << 20, "tts": 32 << 20}  # a transcript; ~10 min of 24 kHz speech


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # urllib then raises HTTPError with the 3xx status


def _opener() -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(_NoRedirect)


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
        self._opener = opener if opener is not None else _opener()

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
        key = self.environ.get(name, "")
        if not key.strip():
            raise self._unavailable(
                f"{name} is not set (nothing was sent)",
                f"export {name}=<your key>, or remove [{self.role}]",
                called=False,
            )
        return key

    def _send(self, path: str, body: bytes, content_type: str, key: str | None) -> bytes:
        """POST, in a worker thread: the body of a 2xx answer, or `SpeechUnavailable`."""
        request = urllib.request.Request(f"{self.config.base_url}{path}", data=body, method="POST")
        request.add_header("Content-Type", content_type)
        request.add_header("User-Agent", USER_AGENT)
        if key is not None:
            request.add_header("Authorization", f"Bearer {key}")
        limit = MAX_ANSWER_BYTES[self.role]
        try:
            with self._opener.open(request, timeout=self.config.timeout_s) as response:
                data = response.read(limit + 1)
        except urllib.error.HTTPError as exc:
            exc.close()  # the error body is not read, and never quoted (it may echo speech)
            why, how = _failure(exc.code)
            raise self._unavailable(why, how) from None
        except (TimeoutError, urllib.error.URLError, OSError, http.client.HTTPException) as exc:
            reason = getattr(exc, "reason", exc)
            if isinstance(reason, TimeoutError):
                raise self._timed_out() from None
            why, how = _failure(None)
            detail = scrub(f"{type(reason).__name__}: {reason}", key)[:160]
            raise self._unavailable(f"{why} ({detail})", how) from None
        if len(data) > limit:
            raise self._unavailable(
                f"the server's answer is larger than {limit >> 20} MB", "check base_url and model"
            )
        return data

    async def _post(self, path: str, body: bytes, content_type: str) -> bytes:
        key = self._key()
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self._send, path, body, content_type, key),
                timeout=self.config.timeout_s * GRACE,
            )
        except TimeoutError:
            # The worker thread ends on its own socket timeout; nothing waits for it.
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
        except ValueError:
            raise self._unavailable(
                "the server's answer is not a PCM WAV file", "check base_url and model"
            ) from None
        if width != 2:
            raise self._unavailable(
                f"the server sent {8 * width}-bit audio; the speaker plays 16-bit PCM",
                "choose a model or server that returns 16-bit WAV",
            )
        return Speech(pcm, rate, channels, width)
