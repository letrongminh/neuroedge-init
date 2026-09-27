"""
TSK-S6-01/02 — the OTA component's boot path must compile with OTA off.

`ne_ota.c`'s boot path (rollback state, NVS marks, mark-valid) runs in every
image; the HTTP stack sits under `#if CONFIG_NEUROEDGE_OTA`. A header needed by
the boot path once lived inside that guard, and the three non-OTA firmware jobs
(`sdkconfig.defaults;sdkconfig.qemu`, the board default, the generated agent
project) failed to compile while the OTA layer hid it. ESP-IDF is not on this
host, so this test strips the OTA-only blocks and pins every IDF symbol family
the remaining code uses to a header included outside them — the same mistake
(a new `esp_*`/`nvs_*` call with its header under the guard) fails here.
"""

from __future__ import annotations

import re

# Symbol family -> the header that declares it, for the IDF API the boot path
# may use. A call whose family is not here is fine; add it with its header.
FAMILIES = {
    "esp_ota_": "esp_ota_ops.h",
    "ESP_OTA_IMG_": "esp_ota_ops.h",
    "esp_partition_": "esp_partition.h",
    "esp_image_": "esp_image_format.h",
    "esp_app_": "esp_app_desc.h",
    "esp_err_": "esp_err.h",
    "esp_restart": "esp_system.h",
    "nvs_": "nvs.h",
    "ESP_ERR_NVS_": "nvs.h",
}
# Used only inside the OTA block: its absence outside proves the stripper works.
OTA_ONLY = "esp_https_ota_begin"


def _outside_ota(text: str) -> tuple[str, list[str]]:
    """
    The file with `#if CONFIG_NEUROEDGE_OTA … #endif` regions removed (nested
    conditionals handled), and the quoted includes seen outside them.
    """
    stack: list[bool] = []
    outside: list[str] = []
    includes: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(("#if", "#ifdef", "#ifndef")):
            guarded = "CONFIG_NEUROEDGE_OTA" in stripped and not stripped.startswith(
                ("#ifndef", "#elif")
            )
            stack.append(guarded)
            continue
        if stripped.startswith("#elif"):
            if stack:
                stack[-1] = "CONFIG_NEUROEDGE_OTA" in stripped
            continue
        if stripped.startswith("#else"):
            if stack:
                stack[-1] = False
            continue
        if stripped.startswith("#endif"):
            if stack:
                stack.pop()
            continue
        if any(stack):
            continue
        outside.append(line)
        match = re.match(r'\s*#include\s+"([^"]+)"', line)
        if match:
            includes.append(match.group(1))
    return "\n".join(outside), includes


def test_ota_guard_is_where_this_test_thinks_it_is(root):
    text = (root / "targets" / "esp32s3" / "components" / "ne_ota" / "src" / "ne_ota.c").read_text(
        encoding="utf-8"
    )
    outside, _ = _outside_ota(text)
    assert "#if CONFIG_NEUROEDGE_OTA" in text
    assert OTA_ONLY not in outside  # stripped: the stripper found the guard
    assert OTA_ONLY in text


def test_every_boot_path_symbol_has_its_header_outside_the_guard(root):
    component = root / "targets" / "esp32s3" / "components" / "ne_ota"
    text = (component / "src" / "ne_ota.c").read_text(encoding="utf-8")
    outside, includes = _outside_ota(text)
    identifiers = set(re.findall(r"\b(?:[A-Za-z_][A-Za-z0-9_]*)\b", outside))
    missing = {
        header
        for family, header in FAMILIES.items()
        if any(name == family or name.startswith(family) for name in identifiers)
        and header not in includes
    }
    assert not missing, (
        f"ne_ota.c uses {sorted(missing)} families outside #if CONFIG_NEUROEDGE_OTA but does not "
        f"include their headers outside it: {sorted(includes)}"
    )
    # The two that broke the non-OTA builds are pinned explicitly.
    assert "nvs.h" in includes and "esp_system.h" in includes


def test_the_boot_path_really_uses_the_guarded_headers(root):
    component = root / "targets" / "esp32s3" / "components" / "ne_ota"
    outside, includes = _outside_ota((component / "src" / "ne_ota.c").read_text(encoding="utf-8"))
    # A symbol from each of the two regressed families, to prove the check has
    # something to guard: the functions the boot path calls.
    assert "nvs_open" in outside or "nvs_get_str" in outside
    assert "esp_restart" in outside
    assert "nvs.h" in includes and "esp_system.h" in includes
