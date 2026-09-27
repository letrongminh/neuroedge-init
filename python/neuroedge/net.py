"""
The one way NeuroEdge talks HTTP to a provider — System 1's model (Jev), STT, TTS
(TSK-I4-02, TSK-S3-13). The standard library only, so `pip install neuroedge`
gains no dependency (FR-DX-02). Each adapter keeps only its protocol mapping.

What every request gets here, and none may skip:

* **no redirect** — urllib would resend the ``Authorization`` header to wherever the
  server points; a 3xx comes back as its status;
* **no proxy** — never ``http_proxy`` / ``https_proxy`` from the environment: through a
  proxy, a request to ``http://localhost`` would carry the key to another machine in
  clear text;
* **a deadline** — the answer is read a chunk at a time against it, and the socket
  timeout never outlasts it, so a server that trickles bytes cannot hold the worker
  thread past it;
* **a size cap** — more than `max_bytes` is not an answer;
* **a key that is a key** (`env_key`) — stripped, and never one holding control
  characters: a trailing newline would end up in a header, and in the error that
  quotes it.

HTTP errors are statuses, not exceptions; an error body is never read (it may echo
what was said). Network failures are raised as they are, and a caller reports them
by class name only.
"""

from __future__ import annotations

import asyncio
import contextlib
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from typing import Any

CHUNK = 64 << 10


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """A redirect is refused, not followed: urllib then raises HTTPError with the 3xx status."""

    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


def make_opener() -> urllib.request.OpenerDirector:
    """urllib's opener without redirects and without any proxy."""
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect)


class DeadlineExceeded(TimeoutError):
    """The answer did not finish arriving before the deadline."""


class TooLarge(ValueError):
    """The answer is larger than any answer of this kind."""


class KeyUnusable(ValueError):
    """The key's variable holds control characters or spaces inside the key."""


def env_key(environ: Mapping[str, str], name: str) -> str | None:
    """
    The key in variable `name`, stripped; None when unset or blank. `KeyUnusable`
    when what is left holds whitespace or control characters — its message never
    repeats the value.
    """
    key = environ.get(name, "").strip()
    if not key:
        return None
    if any(ch.isspace() or ord(ch) < 32 or ord(ch) == 127 for ch in key):
        raise KeyUnusable(f"{name} holds spaces or control characters inside the key")
    return key


def _socket(response: Any) -> Any:
    """The socket under an `http.client.HTTPResponse`, when it can be reached."""
    raw = getattr(getattr(response, "fp", None), "raw", None)
    return getattr(raw, "_sock", None)


def post(
    url: str,
    headers: Mapping[str, str],
    body: bytes,
    *,
    timeout_s: float,
    deadline: float,
    max_bytes: int,
    opener: Any = None,
) -> tuple[int, bytes]:
    """
    POST `body` and return ``(status, answer)``. `deadline` is `time.monotonic()`
    seconds; `timeout_s` bounds each socket operation, and never goes past the
    deadline. A non-2xx answer is its status with an empty body. Raises
    `DeadlineExceeded`, `TooLarge`, or the network error (`URLError`, `OSError`,
    `http.client.HTTPException`, `TimeoutError`).
    """
    request = urllib.request.Request(url, data=body, headers=dict(headers), method="POST")
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise DeadlineExceeded("no time left before the deadline")
    try:
        response = (opener or make_opener()).open(request, timeout=min(timeout_s, remaining))
    except urllib.error.HTTPError as error:
        error.close()  # the error body is not read, and never quoted
        return int(error.code), b""
    with response:
        chunks: list[bytes] = []
        size = 0
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise DeadlineExceeded("the answer was still arriving at the deadline")
            # Two guards, either enough alone: the check above between chunks, and a
            # socket timeout that never reaches past the deadline within one.
            sock = _socket(response)
            if sock is not None:
                with contextlib.suppress(OSError, ValueError):
                    sock.settimeout(max(min(timeout_s, remaining), 0.001))
            chunk = response.read1(CHUNK)
            if not chunk:
                break
            size += len(chunk)
            if size > max_bytes:
                raise TooLarge(f"the answer is larger than {max_bytes} bytes")
            chunks.append(chunk)
        status = getattr(response, "status", None)
        return (int(status) if isinstance(status, int) else 200), b"".join(chunks)


def in_daemon_thread(function: Callable[..., Any], *args: Any, name: str) -> asyncio.Future:
    """
    Run a blocking call off the loop, in a daemon thread named `name`. Not the default
    executor: a loop that closes after a timeout (each REPL turn is its own loop, and
    `asyncio.run` joins its executor) must not wait for a request still in flight.
    """
    loop = asyncio.get_running_loop()
    future: asyncio.Future = loop.create_future()

    def deliver(setter: str, value: Any) -> None:
        if not future.done():  # abandoned: the caller has moved on
            getattr(future, setter)(value)

    def run() -> None:
        try:
            result = function(*args)
        except BaseException as exc:  # handed to the awaiting coroutine
            setter, value = "set_exception", exc
        else:
            setter, value = "set_result", result
        with contextlib.suppress(RuntimeError):  # the loop is gone: its caller timed out
            loop.call_soon_threadsafe(deliver, setter, value)

    threading.Thread(target=run, name=name, daemon=True).start()
    return future
