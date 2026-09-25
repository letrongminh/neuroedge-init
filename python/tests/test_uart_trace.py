"""
TSK-S4-09 — reading a device's trace off its UART (FR-CI-01, FR-CLI-04).

`neuroedge.testing.uart` keeps the `NE1 ` lines among the firmware's log, checks
the session framing (`device_info` … `trace_end {events: N}`), and rebuilds one
validated `trace.v1` per session; `neuroedge record --target esp32s3 --port`
writes them. Every way a capture can be incomplete or garbled is an error with
its line number — never a shorter trace read as the truth. The three sources
(file, tcp://, serial through pyserial) are exercised for real.
"""

from __future__ import annotations

import json
import socket
import sys
import threading
import time

import pytest
import serial
from typer.testing import CliRunner

from neuroedge.cli.main import app
from neuroedge.errors import TraceValidationError
from neuroedge.testing import uart
from neuroedge.testing.uart import read_sessions, sessions_from_lines
from neuroedge.trace import load_trace, validate_trace

runner = CliRunner()


def ne1(offset: int, type: str, data: dict) -> str:
    return "NE1 " + json.dumps({"offset_ms": offset, "type": type, "data": data}) + "\n"


def device_info(boot="00002468", **extra) -> str:
    info = {
        "board_id": "esp32s3-box-3",
        "agent_version": "home-voice@0.1.0",
        "device_id": "qemu",
        "boot_id": boot,
        **extra,
    }
    return ne1(0, "device_info", info)


def gate(offset: int, verdict="ALLOW") -> list[str]:
    return [
        ne1(offset, "gate_evaluation_begin", {"gate": "light_on@1.0.0"}),
        ne1(offset + 1, "gate_facts", {"call_source": {"value": "local_grammar"}}),
        ne1(offset + 2, "gate_evaluation_result", {"verdict": verdict}),
    ]


def session(boot="00002468", evaluations=1, announce=None, **extra) -> list[str]:
    lines = [device_info(boot, **extra)]
    for i in range(evaluations):
        lines += gate(10 * (i + 1))
    lines.append(ne1(99, "trace_end", {"events": len(lines) if announce is None else announce}))
    return lines


BOOT_LOG = [
    "ESP-ROM:esp32s3-20210327\r\n",
    "I (31) boot: ESP-IDF v5.4 2nd stage bootloader\r\n",
    "\x1b[0;32mI (45) neuroedge_core: NeuroEdge memory feasibility spike\x1b[0m\r\n",
    "NE1001 is an error code, not a trace line\n",
    'NEUROEDGE_MEMORY_JSON {"checkpoint":"boot"}\n',
]


# --- framing ----------------------------------------------------------------------------------


def test_trace_lines_are_kept_and_every_other_line_is_dropped():
    lines = BOOT_LOG + session(evaluations=2) + ["NE_SELFTEST PASS walker=6 token=6\n"]
    [found] = sessions_from_lines(lines, "uart.log")
    trace = found.trace()
    validate_trace(trace, "uart.log")
    assert [e["type"] for e in trace["events"]] == [
        "device_info",
        *["gate_evaluation_begin", "gate_facts", "gate_evaluation_result"] * 2,
        "trace_end",
    ]
    assert found.line == len(BOOT_LOG) + 1


def test_the_host_adds_only_metadata():
    lines = [line.replace("\n", "\r\n") for line in session()]
    [found] = sessions_from_lines(lines, "uart.log")
    trace = found.trace()
    assert trace["metadata"]["session_id"] == "sess_0000246800"
    assert trace["metadata"]["target"] == "esp32s3"
    assert trace["metadata"]["board_id"] == "esp32s3-box-3"
    assert trace["metadata"]["agent_version"] == "home-voice@0.1.0"
    assert trace["metadata"]["device_id"] == "qemu"
    assert [json.loads(line[4:]) for line in lines] == trace["events"]  # offsets are the device's


def test_sessions_of_one_boot_and_of_two_boots_get_distinct_ids():
    lines = session() + session(replay_of="happy-path.json") + session(boot="0000abcd")
    found = sessions_from_lines(lines, "uart.log")
    assert [s.session_id for s in found] == [
        "sess_0000246800",
        "sess_0000246801",
        "sess_0000abcd00",
    ]
    assert found[1].replay_of == "happy-path.json"


@pytest.mark.parametrize(
    ("lines", "where", "why"),
    [
        (session()[:2] + ["NE1 {not json\n"], ":3", "not JSON"),
        (
            session()[:1] + ['NE1 {"offset_ms":1,"type":"x","data":{},"extra":1}\n'],
            ":2",
            "one event",
        ),
        (session()[:1] + ['NE1 {"offset_ms":-1,"type":"x","data":{}}\n'], ":2", "offset_ms"),
        (session()[:1] + ['NE1 {"offset_ms":true,"type":"x","data":{}}\n'], ":2", "offset_ms"),
        (session()[:1] + ['NE1 {"offset_ms":1,"type":2,"data":{}}\n'], ":2", "type must be"),
        (session()[:1] + ["NE1 [1, 2]\n"], ":2", "one event"),
        (session()[:1] + [ne1(1, "x", {"pad": "y" * 600})], ":2", "longer than 512"),
        (session(announce=5), ":5", "wrote 5 line.*4 arrived"),
        (session()[:-1], ":1", "no trace_end"),
        (session()[:2] + session(), ":3", "before the one at line 1 ended"),
        (gate(1), ":1", "before any device_info"),
        ([ne1(0, "device_info", {"board_id": "b"})], ":1", "lacks agent_version"),
        ([device_info(boot="zz")], ":1", "must be hex"),
        ([ne1(3, "device_info", json.loads(device_info()[4:])["data"])], ":1", "offset_ms 0"),
    ],
)
def test_a_broken_capture_is_an_error_naming_its_line(lines, where, why):
    with pytest.raises(TraceValidationError, match=why) as caught:
        sessions_from_lines(lines, "uart.log")
    assert caught.value.where.endswith(where)
    assert caught.value.code == "NE4001"


def test_a_capture_with_no_session_is_an_error(tmp_path):
    log = tmp_path / "uart.log"
    log.write_text("".join(BOOT_LOG))
    with pytest.raises(TraceValidationError, match="no NE1 trace session"):
        read_sessions(str(log))


def test_anonymize_hashes_raw_text_at_the_source():
    lines = session()[:-1] + [ne1(50, "tts_stream_start", {"text": "Xin chào"})]
    lines.append(ne1(99, "trace_end", {"events": len(lines)}))
    [found] = sessions_from_lines(lines, "uart.log")
    hashed = found.recorder(anonymize=True).to_trace()
    assert "Xin chào" not in json.dumps(hashed, ensure_ascii=False)
    assert "Xin chào" in json.dumps(found.trace(), ensure_ascii=False)


# --- sources ----------------------------------------------------------------------------------


def test_a_file_is_read_by_path_or_file_url(tmp_path):
    log = tmp_path / "uart.log"
    log.write_text("".join(BOOT_LOG + session() + ["NE_TRACE DONE sessions=1\n"]))
    assert len(read_sessions(str(log))) == 1
    assert len(read_sessions(f"file:{log}")) == 1
    with pytest.raises(TraceValidationError, match="no such file"):
        read_sessions(str(tmp_path / "missing.log"))


def _serve(lines: list[str], hold: float):
    """A one-shot TCP server, as QEMU's -serial tcp::<port>,server: sends, then holds."""
    server = socket.create_server(("127.0.0.1", 0))
    port = server.getsockname()[1]

    def serve():
        connection, _ = server.accept()
        with connection:
            for line in lines:
                connection.sendall(line.encode("utf-8"))
                time.sleep(0.001)
            time.sleep(hold)
        server.close()

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    return f"tcp://127.0.0.1:{port}", thread


def test_tcp_stops_at_done_even_while_the_emulator_keeps_the_socket_open():
    port, thread = _serve(BOOT_LOG + session() + ["NE_TRACE DONE sessions=1\n"], hold=5)
    started = time.monotonic()
    assert len(read_sessions(port, timeout_s=10)) == 1
    assert time.monotonic() - started < 3


def test_tcp_gives_up_after_the_timeout_and_says_what_is_missing():
    port, thread = _serve(session()[:2], hold=5)
    started = time.monotonic()
    with pytest.raises(TraceValidationError, match="no trace_end"):
        read_sessions(port, timeout_s=0.5)
    assert time.monotonic() - started < 3


def test_tcp_with_nothing_listening_says_how_to_start_qemu():
    probe = socket.create_server(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    with pytest.raises(TraceValidationError, match="cannot connect") as caught:
        read_sessions(f"tcp://127.0.0.1:{port}", timeout_s=1)
    assert "-serial tcp::" in caught.value.how


def test_a_serial_device_is_read_through_pyserial(monkeypatch):
    device = serial.serial_for_url("loop://", timeout=0.2)
    device.write("".join(BOOT_LOG + session(evaluations=3) + ["NE_TRACE DONE\n"]).encode())
    opened = {}

    def serial_for_url(url, **kwargs):
        opened.update(url=url, **kwargs)
        return device

    monkeypatch.setattr(serial, "serial_for_url", serial_for_url)
    [found] = read_sessions("/dev/ttyACM0", baud=115200, timeout_s=5)
    assert opened["url"] == "/dev/ttyACM0" and opened["baudrate"] == 115200
    assert len(found.events) == 11


def test_a_serial_device_without_pyserial_names_the_extra(monkeypatch):
    monkeypatch.setitem(sys.modules, "serial", None)
    with pytest.raises(TraceValidationError, match="pyserial") as caught:
        read_sessions("/dev/ttyACM0", timeout_s=1)
    assert "neuroedge[serial]" in caught.value.how


def test_a_serial_device_that_does_not_open_is_an_error():
    with pytest.raises(TraceValidationError, match="cannot open the serial device"):
        read_sessions("/dev/neuroedge-no-such-tty", timeout_s=1)


def test_ports_are_told_apart_by_their_shape():
    assert uart.SERIAL.match("/dev/ttyUSB0") and uart.SERIAL.match("COM7")
    assert uart.SERIAL.match("loop://") and uart.SERIAL.match("rfc2217://host:2217")
    assert not uart.SERIAL.match("build/uart.log") and not uart.SERIAL.match("uart.log")


# --- neuroedge record --target esp32s3 --port ---------------------------------------------------


@pytest.fixture
def capture(tmp_path):
    log = tmp_path / "uart.log"
    log.write_text(
        "".join(BOOT_LOG + session(evaluations=2) + session(replay_of="happy-path.json"))
    )
    return log


def test_record_writes_one_validated_trace_per_session(capture, tmp_path):
    out = tmp_path / "traces"
    result = runner.invoke(
        app, ["record", "--target", "esp32s3", "--port", str(capture), "--out", str(out)]
    )
    assert result.exit_code == 0, result.output
    written = sorted(out.glob("*.json"))
    assert [p.name for p in written] == ["sess_0000246800.json", "sess_0000246801.json"]
    for path in written:
        assert load_trace(path)["metadata"]["device_id"] == "qemu"
    assert "2 gate evaluation(s), home-voice@0.1.0, device qemu" in result.output
    assert "happy-path.json" in result.output


def test_record_to_a_json_path_needs_exactly_one_session(capture, tmp_path):
    result = runner.invoke(
        app,
        [
            "record",
            "--target",
            "esp32s3",
            "--port",
            str(capture),
            "--out",
            str(tmp_path / "x.json"),
        ],
    )
    assert result.exit_code == 1
    assert "wrote 2 sessions" in result.output
    single = tmp_path / "one.log"
    single.write_text("".join(session()))
    out = tmp_path / "one.json"
    result = runner.invoke(
        app, ["record", "--target", "esp32s3", "--port", str(single), "--out", str(out)]
    )
    assert result.exit_code == 0, result.output
    assert load_trace(out)["metadata"]["session_id"] == "sess_0000246800"


@pytest.mark.parametrize(
    ("argv", "why"),
    [
        (["--target", "esp32s3"], "--port is needed"),
        (["--target", "sim", "--port", "uart.log"], "only esp32s3 has one"),
        (["--target", "esp32s3", "--port", "uart.log", "-c", "bật đèn"], "the firmware's"),
        (["--target", "esp32s3", "--port", "uart.log", "--board", "sim-default"], "--board says"),
    ],
)
def test_record_refuses_options_that_do_not_fit_a_device(capture, argv, why):
    argv = [str(capture) if arg == "uart.log" else arg for arg in argv]
    result = runner.invoke(app, ["record", *argv])
    assert result.exit_code == 1, result.output
    assert why in result.output


def test_record_of_a_broken_capture_writes_nothing(tmp_path):
    log = tmp_path / "uart.log"
    log.write_text("".join(session(announce=9)))
    out = tmp_path / "traces"
    result = runner.invoke(
        app, ["record", "--target", "esp32s3", "--port", str(log), "--out", str(out)]
    )
    assert result.exit_code == 1
    assert "NE4001" in result.output and "uart.log:5" in result.output
    assert not out.exists()
