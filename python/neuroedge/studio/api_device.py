"""`/api/device…` (docs/spec/studio.md §4). Slice S1c."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .. import paths
from ..engine.compiler import build as run_build
from ..errors import BuildFailed, NeuroEdgeError

# What scripts/qemu_ota.sh and scripts/ota_markers.sh treat as failure per phase.
OTA_FORBIDDEN = {
    "a": re.compile(r"^NE_OTA (SWITCH|ROLLBACK|REJECTED|DOWNLOADED)"),
    "b": re.compile(r"^NE_OTA (REJECTED|ROLLBACK)"),
    "c": re.compile(r"^NE_OTA (DOWNLOADED|SWITCH|VALID|ROLLBACK)"),
    "d": re.compile(r"^NE_OTA VALID partition=ota_1"),
    "e": re.compile(r"^NE_OTA VALID partition=ota_1"),
    "f": re.compile(r"^NE_OTA (SWITCH|VALID)"),
    "g": re.compile(r"^NE_OTA (DOWNLOADED|SWITCH|REJECTED)"),
}
# The marker each phase must end up with (the last `ota_ordered` pattern of the script).
OTA_REQUIRED = {
    "a": re.compile(r"^NE_OTA SKIP reason=same_version version=0\.1\.0$"),
    "b": re.compile(r"^NE_OTA VALID partition=ota_0$"),
    "c": re.compile(r"^NE_OTA REJECTED reason=signature$"),
    "d": re.compile(r"^NE_OTA SKIP reason=rolled_back version=0\.3\.0$"),
    "e": re.compile(r"^NE_OTA SKIP reason=rolled_back version=0\.3\.1$"),
    "f": re.compile(r"^NE_OTA ERASED partition=ota_1$"),
    "g": re.compile(r"^NE_OTA SKIP reason=downgrade version=0\.1\.0$"),
}
# Phases where the script counts exactly one `NE_OTA ROLLBACK from=ota_1 to=ota_0`.
OTA_ONE_ROLLBACK = {"d", "f", "g"}


def device(server: Any) -> dict[str, Any]:
    """Status of the device firmware, golden screens, QEMU and OTA test logs."""
    # 1. firmware: whether <agent_root>/build/esp32s3/ holds CMakeLists.txt
    firmware_dir = server.agent_root / "build" / "esp32s3"
    cmake_file = firmware_dir / "CMakeLists.txt"
    if cmake_file.is_file():
        file_count = sum(1 for p in firmware_dir.rglob("*") if p.is_file())
        firmware: dict[str, Any] = {"built": True, "dir": str(firmware_dir), "files": file_count}
    else:
        firmware = {"built": False}

    # Repository checkout check
    try:
        root: Path | None = paths.repo_root()
    except NeuroEdgeError:
        root = None

    is_checkout = root is not None and root != paths.PACKAGED

    # 2. screens: golden screens under targets/esp32s3/ui/golden/{vi,en}/*.png
    screens: list[dict[str, Any]] = []
    if is_checkout and root is not None:
        golden_base = root / "targets" / "esp32s3" / "ui" / "golden"
        if golden_base.is_dir():
            names = {p.stem for p in golden_base.glob("*/*.png")}
            for name in sorted(names):
                langs = [
                    lang for lang in ("vi", "en") if (golden_base / lang / f"{name}.png").is_file()
                ]
                if langs:
                    screens.append({"name": name, "langs": langs})

    # 3. golden: real result only (run_ui_golden.sh writes no output file)
    golden_status: dict[str, Any] = {}

    # 4. qemu: parse targets/esp32s3/build/uart.log
    qemu: dict[str, Any] | None = None
    if is_checkout and root is not None:
        uart_log = root / "targets" / "esp32s3" / "build" / "uart.log"
        if uart_log.is_file():
            text = uart_log.read_text(encoding="utf-8", errors="replace")
            lines = [line.rstrip("\r\n") for line in text.splitlines()]
            selftest = None
            trace_done = None
            for line in lines:
                if re.match(r"^NE_SELFTEST (PASS|FAIL) walker=\d+ token=\d+", line):
                    selftest = line
                elif re.match(r"^NE_TRACE DONE sessions=\d+", line):
                    trace_done = line
            qemu_data: dict[str, Any] = {"log": lines[-40:]}
            if selftest is not None:
                qemu_data["selftest"] = selftest
            if trace_done is not None:
                qemu_data["trace_done"] = trace_done
            qemu = qemu_data

    # 5. ota: parse targets/esp32s3/build/ota-test/logs/
    ota: dict[str, Any] | None = None
    if is_checkout and root is not None:
        ota_logs_dir = root / "targets" / "esp32s3" / "build" / "ota-test" / "logs"
        if ota_logs_dir.is_dir():
            phases: list[dict[str, Any]] = []
            for phase in ("a", "b", "c", "d", "e", "f", "g"):
                phase_log = ota_logs_dir / f"{phase}.log"
                if phase_log.is_file():
                    phase_files = [phase_log]
                else:
                    phase_files = sorted(ota_logs_dir.glob(f"{phase}-*.log"))

                if not phase_files:
                    phases.append({"phase": phase, "markers": [], "ok": False})
                    continue

                markers: list[str] = []
                for pfile in phase_files:
                    ptext = pfile.read_text(encoding="utf-8", errors="replace")
                    for line in ptext.splitlines():
                        clean = line.rstrip("\r\n")
                        if clean.startswith("NE_OTA "):
                            markers.append(clean)

                forbidden_pat = OTA_FORBIDDEN[phase]
                has_forbidden = any(forbidden_pat.search(m) for m in markers)
                ok = (
                    not has_forbidden
                    and any(OTA_REQUIRED[phase].search(m) for m in markers)
                    and (
                        phase not in OTA_ONE_ROLLBACK
                        or sum(m.startswith("NE_OTA ROLLBACK") for m in markers) == 1
                    )
                )
                phases.append({"phase": phase, "markers": markers, "ok": ok})
            ota = {"phases": phases}

    # 6. hint: how to produce missing pieces
    if not is_checkout:
        hint = (
            "device UI golden images live in the repository; "
            "produce missing pieces with demo/i3-firmware-qemu/run.sh boot|ota|ui (Docker)"
        )
    else:
        hint = "demo/i3-firmware-qemu/run.sh boot|ota|ui (Docker)"

    return {
        "ok": True,
        "firmware": firmware,
        "screens": screens,
        "golden": golden_status,
        "qemu": qemu,
        "ota": ota,
        "hint": hint,
    }


def build(server: Any) -> dict[str, Any]:
    """Generate the ESP-IDF project into `<agent_root>/build/`."""
    out_dir = server.agent_root / "build"
    try:
        # The same call as `neuroedge build --target esp32s3 --board esp32s3-box-3`; the CLI is a
        # layer above the studio, so it is not imported.
        report = run_build(
            server.agent_path, target="esp32s3", board_id="esp32s3-box-3", out_dir=out_dir
        )
    except BuildFailed as failed:
        return {
            "ok": False,
            "error": {
                **failed.as_dict(),
                "problems": [p.as_dict() for p in failed.problems],
            },
        }
    return {
        "ok": True,
        "built": True,
        "dir": str(report.firmware),
        "files": report.firmware_files,
        "checked": (
            f"{report.requirements} requirement(s), {report.actions} action(s), "
            f"{report.gates} gate(s)"
        ),
    }


def golden(server: Any, lang: str, name: str) -> tuple[bytes, str]:
    """The PNG as `(bytes, "image/png")`."""
    dev = device(server)
    screens = dev.get("screens", [])
    valid_names = {
        s["name"]: s.get("langs", []) for s in screens if isinstance(s, dict) and "name" in s
    }
    if name not in valid_names or lang not in valid_names[name]:
        raise NeuroEdgeError(
            where=f"/api/device/golden/{lang}/{name}.png",
            why=f"screen {name!r} not found for language {lang!r}",
            how="request a screen and language listed in /api/device screens",
        )
    try:
        root = paths.repo_root()
    except NeuroEdgeError as err:
        raise NeuroEdgeError(
            where=f"/api/device/golden/{lang}/{name}.png",
            why=err.why,
            how=err.how,
        ) from None

    target = root / "targets" / "esp32s3" / "ui" / "golden" / lang / f"{name}.png"
    if not target.is_file():
        raise NeuroEdgeError(
            where=f"/api/device/golden/{lang}/{name}.png",
            why=f"golden image file {target.name!r} does not exist",
            how="run scripts/run_ui_golden.sh or demo/i3-firmware-qemu/run.sh ui",
        )
    return target.read_bytes(), "image/png"
