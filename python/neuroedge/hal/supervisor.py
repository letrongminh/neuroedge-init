"""
Out-of-process supervision of the actuator lines on `linux` (RFC-0007 §3d, TSK-N2-02).

The auto-off timer of `LinuxHAL` lives in the runtime process, and a runtime that is frozen
(SIGSTOP, a hung thread, a debugger) runs no timer. So the lines of the pins that have an
envelope are not held by the runtime at all: a **supervisor process** requests them, and the
runtime commands them over a pipe and sends a heartbeat. The supervisor drops a line

* when its deadline passes — the reserved on-time plus a margin, the backstop behind the
  runtime's own timer, which normally wins;
* when the heartbeat has not come for `heartbeat_timeout_ms` while a line is on — the runtime
  is frozen or gone; and
* when the pipe closes — the runtime died.

So a runtime stopped with SIGSTOP while a line is on sees that line down within
`heartbeat_timeout_ms` plus the supervisor's polling margin (`POLL_MARGIN_MS`), whatever the
reserved on-time was. The supervisor runs in a session of its own (`start_new_session`), so a
stop sent to the runtime's process group does not stop it too. It is a command toward the safe
state and so is never refused; a drop is reported to the runtime on its next message, and the
runtime records it (`actuator_command`, `off`, `cause`).

Two classes: `LineSupervisor` is the logic, with an injected clock and line setter, tested
without a process; `SupervisorClient` starts the process and speaks the pipe protocol
(newline-delimited JSON); `main()` is the process.
"""

from __future__ import annotations

import contextlib
import json
import os
import select
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Mapping
from typing import Any

from ..errors import BoardCapabilityError

__all__ = [
    "HEARTBEAT_TIMEOUT_MS",
    "POLL_MARGIN_MS",
    "LineSupervisor",
    "SupervisorClient",
]

# A runtime that is silent this long, with a line on, is treated as frozen. The heartbeat is
# sent four times as often, so one late beat is not a drop.
HEARTBEAT_TIMEOUT_MS = 1000.0
# What the supervisor adds when it sleeps until the next due time; the guarantee a test asserts
# is "within the timeout plus this margin plus a scheduling allowance".
POLL_MARGIN_MS = 50.0
# The deadline a line gets beyond the reserved on-time: the runtime's own timer must win.
DEADLINE_MARGIN_MS = 250.0
START_TIMEOUT_S = 10.0


def _monotonic_ms() -> float:
    return time.monotonic() * 1000.0


class LineSupervisor:
    """
    The decisions of the supervisor, with no process and no gpiod in them: `set_line(pin,
    active)` drives a line, `clock` is in milliseconds. A command is also a heartbeat. A line
    that is on is dropped at its deadline, or as soon as the heartbeat has lapsed; a command to
    turn a line off is always carried out.
    """

    def __init__(
        self,
        set_line: Callable[[str, bool], None],
        *,
        clock: Callable[[], float] = _monotonic_ms,
        heartbeat_timeout_ms: float = HEARTBEAT_TIMEOUT_MS,
    ) -> None:
        self._set_line = set_line
        self.clock = clock
        self.heartbeat_timeout_ms = heartbeat_timeout_ms
        self.last_beat = clock()
        self._on: dict[str, float | None] = {}  # pin -> its deadline, None = none
        self.dropped: list[dict[str, str]] = []  # drops the runtime has not been told about

    def beat(self) -> None:
        self.last_beat = self.clock()

    def command(self, pin: str, active: bool, limit_ms: float | None = None) -> None:
        """Turn a line on until `limit_ms` from now at the latest, or off. A command is a beat."""
        self.beat()
        self._set_line(pin, active)
        if active:
            self._on[pin] = None if limit_ms is None else self.clock() + limit_ms
        else:
            self._on.pop(pin, None)

    def is_on(self, pin: str) -> bool:
        return pin in self._on

    def tick(self) -> None:
        """Drop every line whose deadline has passed, or all of them when the heartbeat lapsed."""
        now = self.clock()
        frozen = bool(self._on) and now - self.last_beat >= self.heartbeat_timeout_ms
        for pin, deadline in list(self._on.items()):
            if frozen:
                self._drop(pin, "heartbeat")
            elif deadline is not None and now >= deadline:
                self._drop(pin, "deadline")

    def _drop(self, pin: str, cause: str) -> None:
        try:
            self._set_line(pin, False)
        except OSError:
            return  # try again on the next tick: the line stays in `_on`
        del self._on[pin]
        self.dropped.append({"pin": pin, "cause": cause})

    def drop_all(self, cause: str) -> None:
        """The runtime is gone or is closing: every line that is on goes off."""
        for pin in list(self._on):
            self._drop(pin, cause)

    def next_due_ms(self) -> float | None:
        """How long until `tick()` has something to do, or None when no line is on."""
        if not self._on:
            return None
        now = self.clock()
        due = [self.last_beat + self.heartbeat_timeout_ms]
        due += [deadline for deadline in self._on.values() if deadline is not None]
        return max(0.0, min(due) - now)

    def take_dropped(self) -> list[dict[str, str]]:
        dropped, self.dropped = self.dropped, []
        return dropped


# -- the process ---------------------------------------------------------------------


def serve(stdin: int = 0, stdout: int = 1) -> int:
    """
    The supervisor process: read the `init` message, request the lines, then serve commands
    until the pipe closes. Replies are one JSON line each: ``{"ok": true, ...}`` or
    ``{"ok": false, "error": ...}``, plus ``"dropped"`` when lines went down on their own.
    """
    buffer = b""

    def read_line(timeout_s: float | None) -> bytes | None:
        nonlocal buffer
        while b"\n" not in buffer:
            ready, _, _ = select.select([stdin], [], [], timeout_s)
            if not ready:
                return None
            chunk = os.read(stdin, 65536)
            if not chunk:
                raise EOFError
            buffer += chunk
        line, _, buffer = buffer.partition(b"\n")
        return line

    def reply(message: Mapping[str, Any]) -> None:
        os.write(stdout, (json.dumps(message) + "\n").encode())

    try:
        init = json.loads(read_line(None) or b"{}")
    except (EOFError, ValueError):
        return 1
    supervisor: LineSupervisor | None = None
    requests: list[Any] = []
    try:
        import importlib

        gpiod = importlib.import_module(init.get("gpiod", "gpiod"))
        line = gpiod.line
        settings = gpiod.LineSettings(
            direction=line.Direction.OUTPUT, output_value=line.Value.INACTIVE
        )
        held: dict[str, tuple[Any, int]] = {}
        by_chip: dict[str, list[int]] = {}
        for path, offset in init["lines"].values():
            by_chip.setdefault(path, []).append(offset)
        chip_request: dict[str, Any] = {}
        for path, offsets in by_chip.items():
            chip_request[path] = gpiod.request_lines(
                path,
                consumer=init.get("consumer", "neuroedge-supervisor"),
                config={tuple(offsets): settings},
            )
            requests.append(chip_request[path])
        for pin, (path, offset) in init["lines"].items():
            held[pin] = (chip_request[path], offset)

        def set_line(pin: str, active: bool) -> None:
            request, offset = held[pin]
            request.set_value(offset, line.Value.ACTIVE if active else line.Value.INACTIVE)

        supervisor = LineSupervisor(
            set_line,
            heartbeat_timeout_ms=float(init.get("heartbeat_timeout_ms", HEARTBEAT_TIMEOUT_MS)),
        )
        reply({"ok": True})
    except Exception as exc:  # the lines could not be had: say so, hold nothing
        for request in requests:
            with contextlib.suppress(Exception):
                request.release()
        reply({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
        return 1

    status = 0
    try:
        while True:
            due = supervisor.next_due_ms()
            # A line that would not drop leaves `due` at 0: wait a little instead of spinning.
            timeout = None if due is None else max(due + POLL_MARGIN_MS / 4, 10.0) / 1000.0
            try:
                raw = read_line(timeout)
            except EOFError:
                break  # the runtime died: nothing stays on
            supervisor.tick()
            if raw is None:
                continue
            try:
                message = json.loads(raw)
                op = message["op"]
                answer: dict[str, Any] = {"ok": True}
                if op == "set":
                    supervisor.command(
                        message["pin"], bool(message["active"]), message.get("limit_ms")
                    )
                elif op == "get":
                    answer["active"] = supervisor.is_on(message["pin"])
                elif op == "beat":
                    supervisor.beat()
                elif op == "close":
                    supervisor.drop_all("close")
                    dropped = supervisor.take_dropped()
                    reply({"ok": True, "dropped": dropped} if dropped else {"ok": True})
                    break
                else:
                    answer = {"ok": False, "error": f"unknown op {op!r}"}
            except (KeyError, ValueError, OSError) as exc:
                answer = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
            dropped = supervisor.take_dropped()
            if dropped:
                answer["dropped"] = dropped
            reply(answer)
    finally:
        supervisor.drop_all("exit")
        for request in requests:
            try:
                request.release()
            except Exception:
                status = status or 1
    return status


# -- the runtime's end -----------------------------------------------------------------


class SupervisorClient:
    """
    The runtime's handle on the supervisor process: `set` and `get` a line, a heartbeat thread,
    `close`. `on_drop(pin, cause)` is called when the supervisor reports it took a line down
    by itself (``deadline``, ``heartbeat``), from whichever thread received the report.
    """

    def __init__(
        self,
        lines: Mapping[str, tuple[str, int]],
        *,
        consumer: str = "neuroedge",
        gpiod_module: str = "gpiod",
        heartbeat_timeout_ms: float = HEARTBEAT_TIMEOUT_MS,
        on_drop: Callable[[str, str], None] | None = None,
        env: Mapping[str, str] | None = None,
    ) -> None:
        self.lines = dict(lines)
        self.heartbeat_timeout_ms = heartbeat_timeout_ms
        self.on_drop = on_drop
        self._lock = threading.Lock()
        self._closed = False
        environment = {**os.environ, **(env or {})}
        self._process = subprocess.Popen(
            [sys.executable, "-c", "from neuroedge.hal.supervisor import main; main()"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            env=environment,
            start_new_session=True,  # a stop sent to the runtime's group does not stop it
        )
        try:
            answer = self._call(
                {
                    "op": "init",
                    "lines": {pin: list(where) for pin, where in self.lines.items()},
                    "consumer": f"{consumer}-supervisor",
                    "gpiod": gpiod_module,
                    "heartbeat_timeout_ms": heartbeat_timeout_ms,
                },
                timeout_s=START_TIMEOUT_S,
            )
        except BaseException:
            self._kill()
            raise
        if not answer.get("ok"):
            self._kill()
            raise BoardCapabilityError(
                where="LinuxHAL -> supervisor",
                why=f"the supervisor could not take the lines {sorted(self.lines)}: "
                f"{answer.get('error', 'no reason given')}",
                how="check the user may use the GPIO chip and that no other process holds the "
                "lines (an earlier `neuroedge mcp serve` still running)",
            )
        self._beat_thread = threading.Thread(
            target=self._beat, name="neuroedge-heartbeat", daemon=True
        )
        self._beat_thread.start()

    # -- the pipe ------------------------------------------------------------------
    def _call(self, message: Mapping[str, Any], timeout_s: float = 5.0) -> dict[str, Any]:
        with self._lock:
            if self._closed or self._process.poll() is not None:
                raise BoardCapabilityError(
                    where="LinuxHAL -> supervisor",
                    why="the supervisor process is not running, so its lines are down",
                    how="restart the session; lines are never driven without the supervisor",
                )
            stdin, stdout = self._process.stdin, self._process.stdout
            assert stdin is not None and stdout is not None
            try:
                stdin.write((json.dumps(message) + "\n").encode())
                stdin.flush()
                ready, _, _ = select.select([stdout], [], [], timeout_s)
                if not ready:
                    raise BoardCapabilityError(
                        where="LinuxHAL -> supervisor",
                        why=f"the supervisor did not answer {message.get('op')!r} in {timeout_s:g} s",
                        how="its lines drop on their own; restart the session",
                    )
                raw = stdout.readline()
            except OSError as exc:
                raise BoardCapabilityError(
                    where="LinuxHAL -> supervisor",
                    why=f"the supervisor pipe broke: {exc}",
                    how="restart the session; the supervisor drops its lines when the pipe closes",
                ) from exc
        answer = json.loads(raw) if raw else {"ok": False, "error": "the supervisor exited"}
        for drop in answer.pop("dropped", ()):
            if self.on_drop is not None:
                self.on_drop(drop["pin"], drop["cause"])
        return answer

    def _expect(self, message: Mapping[str, Any]) -> dict[str, Any]:
        answer = self._call(message)
        if not answer.get("ok"):
            raise BoardCapabilityError(
                where="LinuxHAL -> supervisor",
                why=f"the supervisor refused {message.get('op')!r}: {answer.get('error')}",
                how="the line is not driven; see the supervisor's error",
            )
        return answer

    def _beat(self) -> None:
        interval = self.heartbeat_timeout_ms / 4000.0
        while not self._closed:
            time.sleep(interval)
            try:
                self._call({"op": "beat"})
            except BoardCapabilityError:
                return  # the pipe is gone: the supervisor drops everything on its own

    # -- the lines -----------------------------------------------------------------
    def set(self, pin: str, active: bool, limit_ms: float | None = None) -> None:
        """Drive a line. `limit_ms` (when turning on): the longest it may stay on, from now."""
        self._expect({"op": "set", "pin": pin, "active": active, "limit_ms": limit_ms})

    def get(self, pin: str) -> bool:
        return bool(self._expect({"op": "get", "pin": pin})["active"])

    def alive(self) -> bool:
        """The process is running and not closed: its lines can be commanded."""
        return not self._closed and self._process.poll() is None

    def close(self) -> None:
        """Every line off, the lines released, the process gone. Idempotent."""
        if self._closed:
            return
        try:
            self._call({"op": "close"})
        except BoardCapabilityError:
            pass  # the supervisor is gone already, and it drops its lines as it goes
        finally:
            self._closed = True
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._kill()

    def _kill(self) -> None:
        self._closed = True
        self._process.kill()
        self._process.wait()


def main() -> None:  # pragma: no cover - the entry of the process the client starts
    sys.exit(serve())
