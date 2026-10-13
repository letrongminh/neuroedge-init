"""
Q-79, TSK-I2f-10 — the ESP32-S3's standalone pieces decide exactly as tested.

`ne_boot_policy.c` (when a boot is in safe mode, the `NE_BOOT` line) and
`ne_config_keys.c` (which settings exist, what a value must look like, that a
secret is never shown) are pure C99, compiled here with AddressSanitizer and
UndefinedBehaviorSanitizer and driven by their host runners; exit 0 and the OK
line are the verdict. The ESP-IDF side — NVS, the console UART, the reboots —
runs on QEMU in CI (`firmware-qemu.yml`, scripts/qemu_console.py).

The rest pins what the firmware's structure promises: the boot is counted before
anything that could crash; safe mode runs no self-test, no network and never
confirms an update; the console has no command that moves a pin; the new
partitions move no existing offset; the ported code names its source.
"""

from __future__ import annotations

import csv
import re
import subprocess

import pytest

from .test_c_walker import STRICT, cc

SAN = ["-fsanitize=address,undefined", "-fno-sanitize-recover=all", "-fno-omit-frame-pointer"]

RUNNERS = [
    ("ne_boot", "ne_boot_policy.c", "test_boot_policy_host.c", "NE_BOOT_POLICY", 40),
    ("ne_config", "ne_config_keys.c", "test_config_keys_host.c", "NE_CONFIG_KEYS", 120),
]


@pytest.fixture
def firmware(root):
    return root / "targets" / "esp32s3"


@pytest.mark.parametrize(("component", "source", "runner", "tag", "minimum"), RUNNERS)
def test_the_decisions_pass_their_host_runner(
    firmware, tmp_path, component, source, runner, tag, minimum
):
    path = firmware / "components" / component
    binary = tmp_path / runner.removesuffix(".c")
    compiled = subprocess.run(
        [
            cc(),
            *STRICT[:-1],  # the test program itself is not held to -Wconversion
            "-O1",
            "-g",
            *SAN,
            "-I",
            str(path / "include"),
            str(path / "src" / source),
            str(path / "test" / runner),
            "-o",
            str(binary),
        ],
        capture_output=True,
        text=True,
    )
    assert compiled.returncode == 0, compiled.stderr
    result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    match = re.fullmatch(rf"{tag} OK checks=(\d+)", result.stdout.strip())
    assert match, result.stdout
    assert int(match.group(1)) >= minimum


@pytest.mark.parametrize("source", ["ne_boot_policy.c", "ne_config_keys.c"])
def test_the_pure_files_build_strict_c99(firmware, tmp_path, source):
    component = "ne_boot" if source.startswith("ne_boot") else "ne_config"
    path = firmware / "components" / component
    compiled = subprocess.run(
        [cc(), *STRICT, "-c", "-I", str(path / "include"), str(path / "src" / source)]
        + ["-o", str(tmp_path / "out.o")],
        capture_output=True,
        text=True,
    )
    assert compiled.returncode == 0, compiled.stderr


def _app_main(firmware) -> str:
    text = (firmware / "main" / "main.c").read_text(encoding="utf-8")
    return text[text.index("void app_main(void)") :]


def test_the_boot_is_counted_before_anything_that_could_crash(firmware):
    body = _app_main(firmware)
    begin = body.index("ne_boot_guard_begin()")
    for later in ("ne_ota_boot();", "run_gate_selftest(", "init_network_stack();", "ne_ota_run();"):
        assert begin < body.index(later), later
    assert body.index("init_nvs();") < begin  # the count needs NVS
    # Cleared only after the whole startup, update check included.
    assert body.index("ne_ota_run();") < body.index("ne_boot_guard_stable_after(")


def test_safe_mode_runs_the_console_and_nothing_else(firmware):
    body = _app_main(firmware)
    start = body.index("if (boot.safe_mode) {")
    block = body[start : body.index("\n    }\n", start)]
    assert "ne_console_start(true)" in block
    for forbidden in (
        "run_gate_selftest",
        "ne_ota_boot_confirmed",
        "ne_ota_run",
        "init_network_stack",
        "neuroedge_trace_vectors",
    ):
        assert forbidden not in block, forbidden
    assert "while (true)" in block  # it never falls through to the normal path


def test_the_console_cannot_move_a_pin_or_call_a_tool(firmware):
    source = (firmware / "components" / "ne_console" / "src" / "ne_console.c").read_text(
        encoding="utf-8"
    )
    for forbidden in ("gpio", "ne_agent", "ne_evaluate", "ne_token", "ledc", "i2c", "spi_"):
        assert forbidden not in source.lower(), forbidden
    commands = set(re.findall(r'\.command = "([a-z-]+)"', source))
    assert commands == {"status", "config", "bootguard", "reboot", "factory-reset"}


def test_a_secret_is_never_taken_from_the_command_line_or_kept_in_history(firmware):
    source = (firmware / "components" / "ne_console" / "src" / "ne_console.c").read_text(
        encoding="utf-8"
    )
    assert '"inline_secret"' in source
    assert "read_hidden_line" in source
    assert 'strncmp(line, "config set", 10) != 0' in source
    assert "linenoiseHistorySave" not in source  # history never reaches flash


def test_the_new_partitions_move_nothing_that_was_there(firmware):
    rows = [
        [cell.strip() for cell in row]
        for row in csv.reader((firmware / "partitions.csv").read_text().splitlines())
        if row and not row[0].lstrip().startswith("#")
    ]
    table = {row[0]: row for row in rows}
    before = {
        "nvs": "0x9000",
        "otadata": "0xd000",
        "phy_init": "0xf000",
        "factory": "0x10000",
        "ota_0": "0x390000",
        "ota_1": "0x710000",
        "storage": "0xa90000",
    }
    for name, offset in before.items():
        assert table[name][3] == offset, name
    assert table["ne_config"][1:5] == ["data", "nvs", "0xf90000", "0x6000"]
    assert table["nvs_keys"][1:5] == ["data", "nvs_keys", "0xf96000", "0x1000"]
    assert table["nvs_keys"][5] == "encrypted"
    end = int(table["nvs_keys"][3], 16) + int(table["nvs_keys"][4], 16)
    assert end <= 16 * 1024 * 1024
    assert int(table["storage"][3], 16) + int(table["storage"][4], 16) <= int("0xf90000", 16)


def test_encryption_failure_never_falls_back_to_plaintext(firmware):
    source = (firmware / "components" / "ne_config" / "src" / "ne_config.c").read_text(
        encoding="utf-8"
    )
    encrypted = source[source.index("#if CONFIG_NVS_ENCRYPTION\n    const esp_err_t err") :]
    encrypted = encrypted[: encrypted.index("#else")]
    assert "open_encrypted()" in encrypted
    assert "open_plaintext" not in encrypted


def test_the_ported_files_name_their_source(root, firmware):
    for path in (
        firmware / "components" / "ne_boot" / "src" / "ne_boot_policy.c",
        firmware / "components" / "ne_boot" / "src" / "ne_boot_guard.c",
        firmware / "components" / "ne_config" / "src" / "ne_config.c",
        root / "scripts" / "check_stack_usage.py",
    ):
        text = path.read_text(encoding="utf-8")
        assert "https://github.com/tnm/zclaw" in text and "e3ad271" in text, path
    console = (firmware / "components" / "ne_console" / "src" / "ne_console.c").read_text()
    assert "https://github.com/memovai/mimiclaw" in console and "dcc1c8c" in console
    notice = (root / "NOTICE").read_text(encoding="utf-8")
    assert "https://github.com/tnm/zclaw" in notice
    assert "https://github.com/memovai/mimiclaw" in notice


def test_ci_runs_the_stack_guard_the_console_scenario_and_the_secure_build(root):
    workflow = (root / ".github" / "workflows" / "firmware-qemu.yml").read_text(encoding="utf-8")
    assert "scripts/check_stack_usage.py targets/esp32s3/build --limit 1024" in workflow
    assert "--uart-log targets/esp32s3/build/uart.log --floor 512" in workflow
    assert "python3 scripts/qemu_console.py targets/esp32s3/build" in workflow
    assert 'defaults="sdkconfig.defaults;sdkconfig.secure"' in workflow
    for script in ("scripts/check_stack_usage.py", "scripts/qemu_console.py"):
        assert workflow.count(f'- "{script}"') == 2, script  # pull_request and push


def test_the_qemu_ota_boots_clear_the_count_at_once(firmware):
    """Its boots stop seconds after their last marker: a 30 s window would never pass."""
    layer = (firmware / "sdkconfig.qemu_ota").read_text(encoding="utf-8")
    assert "CONFIG_NEUROEDGE_BOOT_GUARD_STABLE_MS=0" in layer
    secure = (firmware / "sdkconfig.secure").read_text(encoding="utf-8")
    assert "CONFIG_SECURE_FLASH_ENC_ENABLED=y" in secure
    assert "CONFIG_NVS_ENCRYPTION=y" in secure
