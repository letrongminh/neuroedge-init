"""
Q-83 Profile B — `scripts/check_brain_image.py`, the inspection of the image of box and brain
(TC-B-02-1, and the static half of TC-B-11-1). CI runs it on the real image; here it reads
`nm` output and a project of its own, so the check itself is what is tested.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from neuroedge.engine.firmware import firmware_root


@pytest.fixture(scope="module")
def check(root):
    spec = importlib.util.spec_from_file_location(
        "check_brain_image", root / "scripts" / "check_brain_image.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    yield module
    sys.modules.pop(spec.name, None)


NM = """\
42000000 T app_main
42001000 T neuroclaw_start
42002000 T ne_bridge_call
42002400 T ne_bridge_answer
42003000 T esp_tls_conn_new_sync
42004000 T mbedtls_ssl_handshake_client_step
         U esp_wifi_start
"""


def project(tmp_path: Path, brain_source: str = "/* the loop */\n") -> Path:
    root = tmp_path / "project"
    (root / "components" / "neuroclaw" / "src").mkdir(parents=True)
    (root / "components" / "neuroclaw" / "src" / "nc_brain.c").write_text(brain_source)
    (root / "main").mkdir()
    (root / "main" / "brain.c").write_bytes((firmware_root() / "main" / "brain.c").read_bytes())
    return root


def run(check, capsys, tmp_path, nm: str, root: Path) -> tuple[int, str]:
    symbols = tmp_path / "nm.txt"
    symbols.write_text(nm)
    code = check.main(["--symbols", str(symbols), "--project", str(root)])
    out = capsys.readouterr()
    return code, out.out + out.err


def test_the_image_holds_both_ends_of_nc_gate_and_no_server(check, capsys, tmp_path):
    """TC-B-02-1: client TLS is fine; an HTTP or TLS server, or an MCP server, is not."""
    code, out = run(check, capsys, tmp_path, NM, project(tmp_path))
    assert code == 0, out
    for server in ("httpd_start", "mbedtls_ssl_handshake_server_step", "nc_mcp_server_run"):
        code, out = run(
            check, capsys, tmp_path, NM + f"42005000 T {server}\n", project(tmp_path / server)
        )
        assert code == 1 and f"{server}: a server on the chip" in out


def test_an_image_without_the_brain_or_the_bridge_is_not_this_image(check, capsys, tmp_path):
    alone = "\n".join(line for line in NM.splitlines() if "neuroclaw_start" not in line)
    code, out = run(check, capsys, tmp_path, alone, project(tmp_path))
    assert code == 1 and "neuroclaw_start: not linked" in out
    code, out = run(check, capsys, tmp_path, "", project(tmp_path / "empty"))
    assert code == 1 and "no symbols" in out


def test_only_the_image_starts_wifi(check, capsys, tmp_path):
    """TC-B-11-1, static half: main/brain.c starts it once; NeuroClaw-ESP never does."""
    rogue = project(tmp_path, "void f(void) { esp_wifi_init(&cfg); }\n")
    code, out = run(check, capsys, tmp_path, NM, rogue)
    assert code == 1 and "nc_brain.c:1: the brain sets Wi-Fi up itself" in out
    code, out = run(check, capsys, tmp_path, NM, tmp_path / "nowhere")
    assert code == 1 and "not a --brain project" in out
