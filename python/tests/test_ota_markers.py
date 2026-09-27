"""
TSK-S6-01/02/04 — `scripts/ota_markers.sh` passes only on the full story.

`scripts/qemu_ota.sh` proves the OTA story by reading QEMU's UART: a boot, an
update, a refusal, a rollback — in order, with markers that must not appear and
reboots that must not happen. The verdict helpers live in a sourced file so
this test can drive them on any host with bash, grep and awk: the emulator and
ESP-IDF are CI's business, the fail-closed reading is not.

A helper that passed on a missing marker, a wrong order or a truncated log
would let a broken firmware read as a verified one; each is asserted to fail.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

PASS = "NE_SELFTEST PASS walker=26 token=11"
CHECK = "NE_OTA CHECK url=http://10.0.2.2:8070/app.bin"
DOWNLOADED = "NE_OTA DOWNLOADED bytes=1234567 version=0.2.0"
SWITCH = "NE_OTA SWITCH partition=ota_0"
VALID = "NE_OTA VALID partition=ota_0"
REJECTED = "NE_OTA REJECTED reason=signature"
ROLLBACK = "NE_OTA ROLLBACK from=ota_1 to=ota_0"
INVALID = "NE_OTA INVALID partition=ota_1"
FAIL = "NE_SELFTEST FAIL test image NEUROEDGE_OTA_TEST_FAIL_SELFTEST"
ROTATED_ON = "rst:0xc"  # the ROM's reset line; the pattern is an ERE, so no ( ) in it

GOOD_UPDATE = "\n".join([CHECK, DOWNLOADED, SWITCH, PASS, VALID, ""])
STAYED = "\n".join([PASS, CHECK, REJECTED, ""])


def run(root: Path, tmp_path: Path, body: str) -> subprocess.CompletedProcess:
    script = tmp_path / "check.sh"
    script.write_text(f'source "{root / "scripts" / "ota_markers.sh"}"\n{body}\n', encoding="utf-8")
    return subprocess.run(["bash", str(script)], capture_output=True, text=True, timeout=60)


def log(tmp_path: Path, text: str, name: str = "phase.log") -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_a_complete_update_passes(root, tmp_path):
    path = log(tmp_path, GOOD_UPDATE)
    result = run(root, tmp_path, f'ota_ordered "{path}" "{CHECK}" "{DOWNLOADED}" "{SWITCH}"')
    assert result.returncode == 0, result.stderr


def test_crlf_lines_still_match_anchored_markers(root, tmp_path):
    # QEMU's UART ends every line with CRLF; `$` must match the marker, not the CR.
    path = log(tmp_path, GOOD_UPDATE.replace("\n", "\r\n"))
    result = run(
        root,
        tmp_path,
        f'ota_ordered "{path}" "{CHECK}$" "{DOWNLOADED}$" "{SWITCH}$"\n'
        f'ota_count_is "{path}" "{VALID}$" 1\n'
        f'ota_forbid "{path}" "{REJECTED}$"',
    )
    assert result.returncode == 0, result.stderr


def test_a_missing_marker_fails(root, tmp_path):
    path = log(tmp_path, "\n".join([CHECK, SWITCH, ""]))
    result = run(root, tmp_path, f'ota_ordered "{path}" "{CHECK}" "{DOWNLOADED}" "{SWITCH}"')
    assert result.returncode != 0
    assert "not found" in result.stderr


def test_a_wrong_order_fails(root, tmp_path):
    path = log(tmp_path, "\n".join([SWITCH, DOWNLOADED, CHECK, ""]))
    result = run(root, tmp_path, f'ota_ordered "{path}" "{CHECK}" "{DOWNLOADED}" "{SWITCH}"')
    assert result.returncode != 0


def test_an_empty_log_fails_ordered_count_and_first(root, tmp_path):
    path = log(tmp_path, "")
    result = run(
        root,
        tmp_path,
        f'ota_ordered "{path}" "{PASS}" || exit 1\n'
        f'ota_count_is "{path}" "{PASS}" 1 || exit 2\n'
        f'[ "$(ota_first "{path}" "{PASS}")" = 0 ] || exit 3',
    )
    assert result.returncode == 1, result.stderr


def test_a_marker_that_must_not_appear_fails_forbid(root, tmp_path):
    path = log(tmp_path, STAYED)
    assert run(root, tmp_path, f'ota_forbid "{path}" "{REJECTED}"').returncode == 1
    assert run(root, tmp_path, f'ota_forbid "{path}" "{SWITCH}"').returncode == 0


def test_has_after_finds_only_what_follows_the_anchor(root, tmp_path):
    path = log(tmp_path, "\n".join(["rst:0x1 (POWERON)", PASS, ROTATED_ON, ROLLBACK, ""]))
    # The first reset is before the marker; the second one, after it.
    assert run(root, tmp_path, f'ota_has_after "{path}" "{PASS}" "^{ROTATED_ON}"').returncode == 0
    before = log(tmp_path, "\n".join([PASS, ROTATED_ON, ""]), "before.log")
    assert run(root, tmp_path, f'ota_has_after "{before}" "{ROLLBACK}" "{ROTATED_ON}"').returncode
    missing = log(tmp_path, "\n".join([PASS, ""]), "missing.log")
    assert run(root, tmp_path, f'ota_has_after "{missing}" "{PASS}" "{ROTATED_ON}"').returncode != 0


def test_negative_verdicts_need_a_log(root, tmp_path):
    # An empty or missing log could hide anything: a "forbid" or a count of 0
    # on it would pass for the wrong reason.
    empty = log(tmp_path, "")
    missing = tmp_path / "missing.log"
    for path in (empty, missing):
        assert run(root, tmp_path, f'ota_forbid "{path}" "NE_OTA SWITCH"').returncode == 1
        assert run(root, tmp_path, f'ota_count_is "{path}" "NE_OTA SWITCH" 0').returncode == 1
    assert run(root, tmp_path, f'ota_forbid "{empty}" "NE_OTA SWITCH"').returncode == 1
    real = log(tmp_path, "NE_OTA CHECK url=x\n")
    assert run(root, tmp_path, f'ota_forbid "{real}" "NE_OTA SWITCH"').returncode == 0
    assert run(root, tmp_path, f'ota_count_is "{real}" "NE_OTA SWITCH" 0').returncode == 0


def test_a_wrong_count_fails(root, tmp_path):
    path = log(tmp_path, "\n".join([PASS, PASS, ""]))
    assert run(root, tmp_path, f'ota_count_is "{path}" "{PASS}" 2').returncode == 0
    assert run(root, tmp_path, f'ota_count_is "{path}" "{PASS}" 1').returncode == 1


def test_a_reboot_after_a_refusal_fails_nothing_after(root, tmp_path):
    rebooted = log(tmp_path, "\n".join([REJECTED, PASS, ""]), "rebooted.log")
    result = run(root, tmp_path, f'ota_nothing_after "{rebooted}" "{REJECTED}" "{PASS}"')
    assert result.returncode == 1
    assert "after" in result.stderr
    stayed = log(tmp_path, STAYED, "stayed.log")
    assert (
        run(root, tmp_path, f'ota_nothing_after "{stayed}" "{REJECTED}" "{PASS}"').returncode == 0
    )


def test_the_rollback_story_is_read_in_order(root, tmp_path):
    path = log(
        tmp_path,
        "\n".join(
            [CHECK, DOWNLOADED, SWITCH, "Guru Meditation Error: Core  0 panic'ed", ROLLBACK, ""]
        ),
    )
    assert (
        run(
            root,
            tmp_path,
            f'ota_ordered "{path}" "{SWITCH}" "Guru Meditation" "{ROLLBACK}"',
        ).returncode
        == 0
    )
    # The refusal path must not read as a rollback path: the failed image never
    # reaches VALID, and a rollback without the switch before it is not ours.
    fail_selftest = log(tmp_path, "\n".join([SWITCH, FAIL, INVALID, ROLLBACK, ""]), "fail.log")
    assert (
        run(
            root,
            tmp_path,
            f'ota_ordered "{fail_selftest}" "{SWITCH}" "{FAIL}" "{INVALID}" "{ROLLBACK}"',
        ).returncode
        == 0
    )
    assert (
        run(
            root, tmp_path, f'ota_forbid "{fail_selftest}" "NE_OTA VALID partition=ota_1"'
        ).returncode
        == 0
    )
