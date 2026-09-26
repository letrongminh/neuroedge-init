"""
TSK-S4-11 — `scripts/check_firmware_size.py`: the Q-3 budget, and never a pass it did not measure.

Inputs are real ESP-IDF v5.4 reports of this firmware (`tests/firmware/size/`: `idf.py size
--format json2`, part of `idf.py size-components --format json2`) and the heap line the firmware
prints on QEMU. Checked: the flash budget as before; the static RAM left for the heap against the
120 KB floor; the boot heap against it; whether ESP-SR is linked, and `--require-esp-sr` failing
when it is not. Every input that cannot be read — no region, a count that is not one, no heap
line, two of them — is exit 1.
"""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

SIZE = Path(__file__).parent / "firmware" / "size"
HEAP = (
    'NEUROEDGE_HEAP_JSON {"schema":"neuroedge.heap/v1","checkpoint":"gate_runtime_ready",'
    '"idf_version":"v5.4","qemu":true,"internal_free_bytes":383664,'
    '"internal_largest_block_bytes":319488,"internal_min_ever_bytes":383364,'
    '"psram_free_bytes":0,"q3_min_internal_sram_bytes":122880}'
)


@pytest.fixture(scope="module")
def check(root):
    spec = importlib.util.spec_from_file_location(
        "check_firmware_size", root / "scripts" / "check_firmware_size.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _layout() -> dict:
    return json.loads((SIZE / "size.json").read_text())


def _write(tmp_path: Path, name: str, data) -> Path:
    path = tmp_path / name
    path.write_text(data if isinstance(data, str) else json.dumps(data))
    return path


def _run(check, capsys, *argv) -> tuple[int, str]:
    code = check.main([str(a) for a in argv])
    out = capsys.readouterr()
    return code, out.out + out.err


def test_the_thresholds_are_q3s_and_the_probes(check, root):
    probe = (root / "targets" / "esp32s3" / "main" / "memory_probe.h").read_text()
    assert check.Q3_MIN_INTERNAL_SRAM_BYTES == 120 * 1024
    assert "NEUROEDGE_Q3_MIN_INTERNAL_SRAM_BYTES (120 * 1024)" in probe
    assert f"NEUROEDGE_Q3_MAX_FIRMWARE_BYTES      ({check.Q3_MAX_FIRMWARE_BYTES})" in probe


def test_the_measured_firmware_passes_and_says_esp_sr_is_not_linked(check, capsys):
    code, out = _run(
        check,
        capsys,
        "--size-json",
        SIZE / "size.json",
        "--components-json",
        SIZE / "size-components.json",
    )
    assert code == 0, out
    assert "left for the heap: 231,556 bytes" in out
    assert ".data:           20,300 bytes" in out and ".bss:            16,432 bytes" in out
    assert "ESP-SR:            NOT linked" in out and "TODOS.md #17" in out
    assert "✓ PASS" in out and "not the Q-3 verdict" in out


def test_static_ram_under_the_floor_fails(check, capsys, tmp_path):
    report = _layout()
    diram = next(r for r in report["layout"] if r["name"] == "DIRAM")
    diram["used"] = diram["total"] - (120 * 1024 - 1)
    diram["free"] = 120 * 1024 - 1
    code, out = _run(check, capsys, "--size-json", _write(tmp_path, "s.json", report))
    assert code == 1
    assert "under the Q-3 floor" in out and "do not lower the floor" in out


def test_exactly_the_floor_passes(check, capsys, tmp_path):
    report = _layout()
    diram = next(r for r in report["layout"] if r["name"] == "DIRAM")
    diram["used"], diram["free"] = diram["total"] - 120 * 1024, 120 * 1024
    code, _ = _run(check, capsys, "--size-json", _write(tmp_path, "s.json", report))
    assert code == 0


def _broken(report: dict, how: str) -> dict | str:
    report = copy.deepcopy(report)
    diram = next(r for r in report["layout"] if r["name"] == "DIRAM")
    if how == "not json":
        return "{ nope"
    if how == "no layout":
        return {"version": "1.0"}
    if how == "no data RAM region":
        report["layout"] = [r for r in report["layout"] if r["name"] != "DIRAM"]
    elif how == "free is not total - used":
        diram["free"] += 1
    elif how == "a count that is not one":
        diram["used"] = "110204"
    elif how == "a negative count":
        diram["total"], diram["used"], diram["free"] = -1, 0, -1
    elif how == "a part without a size":
        diram["parts"][".bss"] = {}
    elif how == "no parts":
        del diram["parts"]
    return report


@pytest.mark.parametrize(
    "how",
    [
        "not json",
        "no layout",
        "no data RAM region",
        "free is not total - used",
        "a count that is not one",
        "a negative count",
        "a part without a size",
        "no parts",
    ],
)
def test_a_report_that_cannot_be_read_fails_closed(check, capsys, tmp_path, how):
    path = _write(tmp_path, "s.json", _broken(_layout(), how))
    code, out = _run(check, capsys, "--size-json", path)
    assert code == 1, (how, out)
    assert "never reported as met" in out
    assert "PASS" not in out


def test_a_missing_report_fails(check, capsys, tmp_path):
    code, out = _run(check, capsys, "--size-json", tmp_path / "nowhere.json")
    assert code == 1 and "not a readable" in out


def test_esp_sr_linked_is_reported_and_satisfies_the_hook(check, capsys, tmp_path):
    components = json.loads((SIZE / "size-components.json").read_text())
    components["libespressif__esp-sr.a"] = {"abbrev_name": "libespressif__esp-sr.a", "size": 4096}
    components["libesp_audio_front_end.a"] = {"size": 90_000}
    path = _write(tmp_path, "c.json", components)
    code, out = _run(
        check,
        capsys,
        "--size-json",
        SIZE / "size.json",
        "--components-json",
        path,
        "--require-esp-sr",
    )
    assert code == 0, out
    assert "ESP-SR:            linked (libesp_audio_front_end.a, libespressif__esp-sr.a)" in out


@pytest.mark.parametrize("linked_size", [None, 0])
def test_require_esp_sr_fails_when_it_is_not_linked(check, capsys, tmp_path, linked_size):
    components = json.loads((SIZE / "size-components.json").read_text())
    if linked_size is not None:  # in the build, but nothing of it linked
        components["libespressif__esp-sr.a"] = {"size": linked_size}
    path = _write(tmp_path, "c.json", components)
    code, out = _run(
        check,
        capsys,
        "--size-json",
        SIZE / "size.json",
        "--components-json",
        path,
        "--require-esp-sr",
    )
    assert code == 1
    assert "--require-esp-sr: no ESP-SR archive is linked" in out


def test_require_esp_sr_without_the_components_report_fails(check, capsys):
    code, out = _run(check, capsys, "--size-json", SIZE / "size.json", "--require-esp-sr")
    assert code == 1 and "needs --components-json" in out


def test_an_unreadable_components_report_fails(check, capsys, tmp_path):
    path = _write(tmp_path, "c.json", {"libmain.a": {"abbrev_name": "libmain.a"}})
    code, out = _run(check, capsys, "--size-json", SIZE / "size.json", "--components-json", path)
    assert code == 1 and "no `size`" in out


# --- the boot heap -------------------------------------------------------------------------------


def _log(tmp_path: Path, *lines: str) -> Path:
    return _write(tmp_path, "uart.log", "\n".join(["I (31) boot: ESP-IDF v5.4", *lines, ""]))


def test_the_qemu_boot_heap_clears_the_floor(check, capsys, tmp_path):
    code, out = _run(check, capsys, "--heap-log", _log(tmp_path, HEAP, "NE_TRACE DONE sessions=4"))
    assert code == 0, out
    assert "internal free:     383,664 bytes" in out
    assert "PSRAM:             not measured" in out and "not the Q-3 verdict" in out


def test_a_boot_heap_under_the_floor_fails(check, capsys, tmp_path):
    low = HEAP.replace('"internal_free_bytes":383664', '"internal_free_bytes":122879')
    code, out = _run(check, capsys, "--heap-log", _log(tmp_path, low))
    assert code == 1 and "the board can only have less" in out


@pytest.mark.parametrize(
    ("lines", "why"),
    [
        ((), "no NEUROEDGE_HEAP_JSON line"),
        ((HEAP, HEAP), "2 heap lines"),
        (("NEUROEDGE_HEAP_JSON {nope",), "not JSON"),
        ((HEAP.replace("neuroedge.heap/v1", "other/v1"),), "not a neuroedge.heap/v1 line"),
        ((HEAP.replace('"internal_free_bytes":383664', '"internal_free_bytes":-5'),), "byte count"),
        ((HEAP.replace('"internal_min_ever_bytes":383364,', ""),), "internal_min_ever_bytes"),
        ((HEAP.replace('"qemu":true', '"qemu":"yes"'),), "qemu: not a boolean"),
    ],
)
def test_a_heap_log_that_cannot_be_read_fails_closed(check, capsys, tmp_path, lines, why):
    code, out = _run(check, capsys, "--heap-log", _log(tmp_path, *lines))
    assert code == 1, out
    assert why in out and "PASS" not in out


def test_flash_budget_is_unchanged(check, capsys, tmp_path):
    image = tmp_path / "app.bin"
    image.write_bytes(b"\0" * 1024)
    code, out = _run(check, capsys, image)
    assert code == 0 and "smallest app slot: 3,670,016 bytes" in out
    code, out = _run(check, capsys, image, "--max-bytes", 1000)
    assert code == 1 and "cannot be flashed" in out
    code, out = _run(check, capsys, tmp_path / "missing.bin")
    assert code == 1 and "firmware image not found" in out


def test_every_check_runs_and_one_failure_fails_the_run(check, capsys, tmp_path):
    image = tmp_path / "app.bin"
    image.write_bytes(b"\0" * 1024)
    low = HEAP.replace('"internal_free_bytes":383664', '"internal_free_bytes":1')
    code, out = _run(
        check, capsys, image, "--size-json", SIZE / "size.json", "--heap-log", _log(tmp_path, low)
    )
    assert code == 1
    assert "== flash" in out and "== static RAM" in out and "== boot heap" in out


def test_nothing_to_check_is_a_usage_error(check, capsys):
    with pytest.raises(SystemExit) as caught:
        check.main([])
    assert caught.value.code == 2
