"""
Q-79, TSK-I2f-10 — `scripts/check_stack_usage.py`: the stack guard, and never a pass it did not check.

Frames: every function of `main` and the `ne_*` components at most the limit, static only; a
component with objects but no `.su` file, or no component at all, fails. Run: exactly one
`NE_STACK task=main` line at column 0, at or above the floor. The `.su` lines are GCC's format
(`file:line:col:function<TAB>bytes<TAB>static`), as the ESP-IDF v5.4 build writes them.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def check(root):
    spec = importlib.util.spec_from_file_location(
        "check_stack_usage", root / "scripts" / "check_stack_usage.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # @dataclass looks its module up
    spec.loader.exec_module(module)
    yield module
    sys.modules.pop(spec.name, None)


def _build(tmp_path: Path, frames: dict[str, list[str]]) -> Path:
    build = tmp_path / "build"
    for component, lines in frames.items():
        objects = build / "esp-idf" / component / "CMakeFiles" / f"__idf_{component}.dir"
        objects.mkdir(parents=True)
        (objects / "x.c.obj").write_bytes(b"")
        if lines is not None:
            (objects / "x.c.su").write_text("".join(f"{line}\n" for line in lines))
    return build


def _run(check, capsys, *argv) -> tuple[int, str]:
    code = check.main([str(a) for a in argv])
    out = capsys.readouterr()
    return code, out.out + out.err


GOOD = {
    "main": ["/w/main/main.c:155:6:app_main\t240\tstatic"],
    "ne_boot": ["/w/ne_boot/src/ne_boot_guard.c:53:18:ne_boot_guard_begin\t160\tstatic"],
    "esp_wifi": ["/idf/wifi.c:1:1:huge\t9000\tdynamic"],  # not ours: never read
}


def test_small_static_frames_pass_and_the_largest_are_shown(check, capsys, tmp_path):
    code, out = _run(check, capsys, _build(tmp_path, GOOD))
    assert code == 0, out
    assert "2 functions in main, ne_boot" in out
    assert "240 B  app_main" in out
    assert "huge" not in out


def test_a_frame_over_the_limit_fails(check, capsys, tmp_path):
    frames = dict(GOOD, ne_console=["/w/c.c:1:1:print_value\t1040\tstatic"])
    code, out = _run(check, capsys, _build(tmp_path, frames))
    assert code == 1
    assert "print_value: 1040 B frame, over the 1024 B limit" in out
    code, out = _run(check, capsys, _build(tmp_path / "b", frames), "--limit", "2048")
    assert code == 0, out


@pytest.mark.parametrize("kind", ["dynamic", "dynamic,bounded"])
def test_a_dynamic_frame_fails_even_when_small(check, capsys, tmp_path, kind):
    frames = dict(GOOD, ne_config=[f"/w/k.c:1:1:vla\t32\t{kind}"])
    code, out = _run(check, capsys, _build(tmp_path, frames))
    assert code == 1
    assert f"vla: {kind} stack frame" in out


def test_a_component_built_without_stack_usage_fails(check, capsys, tmp_path):
    code, out = _run(check, capsys, _build(tmp_path, dict(GOOD, ne_ota=None)))
    assert code == 1
    assert "ne_ota: no .su files" in out


def test_nothing_to_check_is_not_a_pass(check, capsys, tmp_path):
    code, out = _run(check, capsys, _build(tmp_path, {"esp_wifi": GOOD["esp_wifi"]}))
    assert code == 1
    assert "no main or ne_* component objects" in out
    code, out = _run(check, capsys, tmp_path / "nowhere")
    assert code == 1
    assert "not an ESP-IDF build directory" in out


def test_a_line_that_is_not_gccs_format_fails(check, capsys, tmp_path):
    code, out = _run(check, capsys, _build(tmp_path, dict(GOOD, main=["garbage"])))
    assert code == 1
    assert "not a GCC stack-usage line" in out


def test_the_main_task_figure_from_qemu(check, capsys, tmp_path):
    log = tmp_path / "uart.log"
    log.write_text("I (1) x\r\nNE_STACK task=main free_min=1368 size=3584\r\nNE_TRACE DONE\r\n")
    code, out = _run(check, capsys, tmp_path, "--uart-log", log)
    assert code == 0, out
    assert "1368 of 3584 B" in out
    code, out = _run(check, capsys, tmp_path, "--uart-log", log, "--floor", "2048")
    assert code == 1
    assert "under the 2048 B floor" in out


@pytest.mark.parametrize(
    "text",
    [
        "NE_TRACE DONE sessions=4\n",  # missing
        "x NE_STACK task=main free_min=9999 size=3584\n",  # not at column 0
        "NE_STACK task=main free_min=9 size=1\nNE_STACK task=main free_min=9 size=1\n",  # two
    ],
)
def test_the_main_task_line_must_be_there_once(check, capsys, tmp_path, text):
    log = tmp_path / "uart.log"
    log.write_text(text)
    code, out = _run(check, capsys, tmp_path, "--uart-log", log)
    assert code == 1
    assert "expected one NE_STACK" in out


def test_the_firmware_builds_with_stack_usage(root):
    cmake = (root / "targets" / "esp32s3" / "CMakeLists.txt").read_text()
    assert 'idf_build_set_property(COMPILE_OPTIONS "-fstack-usage" APPEND)' in cmake
    assert cmake.index("-fstack-usage") < cmake.index("project(")


def test_the_bridge_alone_keeps_the_512_byte_rule(check, capsys, tmp_path):
    """TC-B-13-1 (DP-B-13): `ne_*` frames stay at 512 B with the brain in the image."""
    frames = dict(
        GOOD,
        ne_brain_bridge=["/w/b.c:1:1:decide_steps\t496\tstatic"],
        neuroclaw=["/w/nc.c:1:1:nc_loop\t2048\tstatic"],  # the brain's own: not this rule
    )
    build = _build(tmp_path, frames)
    code, out = _run(check, capsys, build, "--component", "^ne_brain_bridge$", "--limit", 512)
    assert code == 0, out
    assert "1 functions in ne_brain_bridge" in out
    over = _build(tmp_path / "over", dict(frames, ne_brain_bridge=["/w/b.c:1:1:f\t520\tstatic"]))
    code, out = _run(check, capsys, over, "--component", "^ne_brain_bridge$", "--limit", 512)
    assert code == 1 and "f: 520 B frame, over the 512 B limit" in out


def test_every_named_task_reports_its_stack_and_clears_the_floor(check, capsys, tmp_path):
    """TC-B-13-1: the console's `tasks` lines, the last one per task."""
    log = tmp_path / "uart.log"
    log.write_text(
        "NE_STACK task=main free_min=900 size=3584\n"
        "NE_STACK task=neuroclaw free_min=4000 size=8192\n"
        "NE_STACK task=ne_console free_min=700 size=4096\r\n"
        "NE_STACK task=neuroclaw free_min=300 size=8192\n"
    )
    code, out = _run(check, capsys, tmp_path, "--uart-log", log, "--task", "ne_console")
    assert code == 0, out
    assert "task ne_console: 700 of 4096 B" in out
    code, out = _run(check, capsys, tmp_path, "--uart-log", log, "--task", "neuroclaw")
    assert code == 1 and "task neuroclaw: 300 B of stack left" in out
    code, out = _run(check, capsys, tmp_path, "--uart-log", log, "--task", "tiT")
    assert code == 1 and "no NE_STACK line for task tiT" in out
