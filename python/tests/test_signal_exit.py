"""
The bounded exit after SIGTERM (`sim/serve.py`): the graceful unwinding through `SystemExit`
can hang (the exception lands inside the event loop's machinery, or waits on the SDK's stdin
thread). With a close registered as the last resort, the process still closes and leaves with
the signal's code; without one, the old behaviour is unchanged.
"""

from __future__ import annotations

import signal
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

HANG_AFTER_SIGNAL = textwrap.dedent(
    """
    import sys, time
    from pathlib import Path
    from neuroedge.sim import serve

    serve.SIGNAL_EXIT_GRACE_S = 0.5
    marker = Path(sys.argv[1])
    if sys.argv[2] == "hook":
        serve._last_resort = lambda: marker.write_text("closed")
    serve.exit_on_signals()
    print("ready", flush=True)
    try:
        while True:
            time.sleep(0.05)
    except SystemExit:
        # What a stuck unwinding looks like from the outside: the exit never comes.
        while True:
            time.sleep(0.05)
    """
)


def _start(tmp_path: Path, mode: str) -> tuple[subprocess.Popen, Path]:
    marker = tmp_path / "closed.txt"
    process = subprocess.Popen(
        [sys.executable, "-c", HANG_AFTER_SIGNAL, str(marker), mode],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    assert process.stdout is not None and process.stdout.readline().strip() == b"ready"
    return process, marker


def test_a_stuck_unwinding_after_sigterm_still_closes_and_exits_with_143(tmp_path):
    process, marker = _start(tmp_path, "hook")
    try:
        began = time.monotonic()
        process.send_signal(signal.SIGTERM)
        assert process.wait(15) == 128 + signal.SIGTERM
        assert time.monotonic() - began < 10
        assert marker.read_text() == "closed"
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()


def test_without_a_registered_close_nothing_forces_the_exit(tmp_path):
    process, marker = _start(tmp_path, "none")
    try:
        process.send_signal(signal.SIGTERM)
        with pytest.raises(subprocess.TimeoutExpired):
            process.wait(2)
        assert not marker.exists()
    finally:
        process.kill()
        process.wait()
