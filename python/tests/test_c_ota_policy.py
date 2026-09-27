"""
TSK-S6-01/02/04 — the OTA decisions refuse and report exactly as tested.

`targets/esp32s3/components/ne_ota/src/ne_ota_policy.c` holds every decision of
the OTA component that carries no ESP-IDF state: install or not (including
unreadable versions and the version the device rolled back from), the boot
action that ties marking an image valid to the gate self-test, URL sanitising
(credentials never reach the UART) and the anchored markers, line for line. It
is compiled on this host with AddressSanitizer and UndefinedBehaviorSanitizer
and driven by `test/test_ota_policy_host.c`; exit 0 and its `NE_OTA_POLICY OK`
line are the whole verdict.

The ESP-IDF side (`src/ne_ota.c`) and the QEMU story (sign a newer image, serve
it over HTTP, refuse a wrong key, roll back a broken image) are CI's
(`firmware-qemu.yml`, job `ota-rollback`; scripts/qemu_ota.sh).
"""

from __future__ import annotations

import re
import subprocess

from .test_c_walker import STRICT, cc

SAN = ["-fsanitize=address,undefined", "-fno-sanitize-recover=all", "-fno-omit-frame-pointer"]


def test_the_ota_decisions_pass_their_host_runner(root, tmp_path):
    component = root / "targets" / "esp32s3" / "components" / "ne_ota"
    runner = tmp_path / "test_ota_policy_host"
    command = [
        cc(),
        *STRICT[:-1],  # the test program itself is not held to -Wconversion
        "-O1",
        "-g",
        *SAN,
        "-I",
        str(component / "include"),
        str(component / "src" / "ne_ota_policy.c"),
        str(component / "test" / "test_ota_policy_host.c"),
        "-o",
        str(runner),
    ]
    compiled = subprocess.run(command, capture_output=True, text=True)
    assert compiled.returncode == 0, compiled.stderr
    result = subprocess.run([str(runner)], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    match = re.fullmatch(r"NE_OTA_POLICY OK checks=(\d+)", result.stdout.strip())
    assert match, result.stdout
    assert int(match.group(1)) >= 100  # decision table, versions, URL rules, every marker


def test_turning_ota_on_requires_signature_and_rollback(root):
    """
    The component refuses to build an update path that is not verified and not
    rollback-able: the Kconfig option depends on both, and the source has an
    #error for a hand-edited sdkconfig that keeps NEUROEDGE_OTA=y without them
    (review of wave3/ota, P1).
    """
    kconfig = (root / "targets" / "esp32s3" / "components" / "ne_ota" / "Kconfig").read_text(
        encoding="utf-8"
    )
    assert "depends on SECURE_SIGNED_ON_UPDATE && BOOTLOADER_APP_ROLLBACK_ENABLE" in kconfig
    source = (
        root / "targets" / "esp32s3" / "components" / "ne_ota" / "src" / "ne_ota.c"
    ).read_text(encoding="utf-8")
    assert "#error" in source
    assert "CONFIG_SECURE_SIGNED_ON_UPDATE" in source
    assert "CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE" in source
