"""
TSK-S6-01/02 — one version rule for the build and the device.

`neuroedge build` refuses an agent version that is not MAJOR.MINOR.PATCH
(`_RELEASE` in python/neuroedge/engine/firmware.py), and the firmware's OTA
code parses the same string to refuse downgrades; a version accepted on one
side and refused on the other is either a build that cannot update or a
downgrade that sneaks through. Here the C parser
(`targets/esp32s3/components/ne_ota/src/ne_ota_policy.c`) is compiled on this
host and driven over one shared case list, and every answer must equal the
Python rule's.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from neuroedge.engine.firmware import _RELEASE

from .test_c_walker import STRICT, cc

# Values both sides must accept, values both must refuse. Kept one list so a
# change to either rule that is not mirrored breaks this test.
CASES = (
    "0.0.0",
    "0.1.0",
    "1.2.3",
    "10.20.30",
    "999999999.0.0",
    "0.999999999.999999999",
    "",
    "1",
    "0.1",
    "0.1.0.0",
    "01.002.0003",
    "1.02.3",
    "1.2.03",
    "00.1.2",
    "1..2",
    ".1.2",
    "1.2.",
    "1.2.3.",
    "1.2.x",
    "v1.2.3",
    "1.2.-3",
    "1.2. 3",
    "1.2.3 ",
    " 1.2.3",
    "4294967296.0.0",  # over the u32 the firmware stores
    "99999999999999999999.0.0",
    "bình thường",
)


def test_the_python_and_c_version_rules_agree_on_every_case(root, tmp_path):
    component = root / "targets" / "esp32s3" / "components" / "ne_ota"
    runner = tmp_path / "test_ota_version_host"
    compiled = subprocess.run(
        [
            cc(),
            *STRICT[:-1],  # the driver itself is not held to -Wconversion
            "-O1",
            "-g",
            "-I",
            str(component / "include"),
            str(component / "src" / "ne_ota_policy.c"),
            str(component / "test" / "test_ota_version_host.c"),
            "-o",
            str(runner),
        ],
        capture_output=True,
        text=True,
    )
    assert compiled.returncode == 0, compiled.stderr
    result = subprocess.run([str(runner), *CASES], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    c_answers = [line == "1" for line in result.stdout.split()]
    assert len(c_answers) == len(CASES), result.stdout
    python_answers = [_RELEASE.fullmatch(case) is not None for case in CASES]
    assert c_answers == python_answers, [
        (case, py, c) for case, py, c in zip(CASES, python_answers, c_answers, strict=True) if py != c
    ]
    # The corpus proves both directions: it has accepted and refused versions.
    assert any(python_answers) and not all(python_answers)
