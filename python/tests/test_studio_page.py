"""
Tests for `neuroedge studio` page slice S3 (TSK-I1-04, Q-51).

Contract & hard rules from docs/spec/studio.md:
- No external assets: no <script src>, <link href>, url(, @import, images only /api/...
- studio.js contains no innerHTML, insertAdjacentHTML, outerHTML, document.write
- Every fetch() argument starts with a quote and /
- I18N.vi and I18N.en have the exact same keys
- Every data-i18n / t("key") used in studio.js exists in I18N
- The boot JSON has agent, target, board, voice
"""

from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

import pytest

from neuroedge.sim import SimSession
from neuroedge.studio import StudioServer

ROOT = Path(__file__).resolve().parents[2]
VILLA = ROOT / "fixtures" / "agents" / "villa-concierge" / "agent.toml"
ASSETS_DIR = ROOT / "python" / "neuroedge" / "studio" / "assets"


@pytest.fixture
def studio():
    session = SimSession.load(VILLA)
    server = StudioServer(session, agent_path=VILLA).start()
    yield server
    server.stop()
    session.close()


def get(server: StudioServer, path: str) -> tuple[int, str | None, bytes]:
    with urllib.request.urlopen(server.url.rstrip("/") + path, timeout=5) as reply:
        return reply.status, reply.headers.get("Content-Type"), reply.read()


def parse_i18n_dict() -> dict[str, dict[str, str]]:
    i18n_js = (ASSETS_DIR / "i18n.js").read_text(encoding="utf-8")
    match = re.search(r"const\s+I18N\s*=\s*(\{.*?\});", i18n_js, re.DOTALL)
    assert match is not None, "Could not find I18N object in i18n.js"
    return json.loads(match.group(1))


def test_the_page_loads_and_has_no_external_resources(studio: StudioServer):
    status, content_type, body = get(studio, "/")
    page = body.decode("utf-8")

    assert status == 200
    assert content_type is not None and content_type.startswith("text/html")
    assert 'id="ne-boot"' in page
    assert 'id="studio"' in page
    assert "NeuroEdge Studio" in page

    # No external scripts or styles
    assert not re.search(r"<script[^>]+src=", page, re.IGNORECASE)
    assert not re.search(r"<link[^>]+href=", page, re.IGNORECASE)

    # Any img src must be local same-origin /api/...
    img_srcs = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', page, re.IGNORECASE)
    for src in img_srcs:
        assert src.startswith("/api/"), f"Image src {src!r} is not /api/..."

    # No external url( or @import in CSS or JS
    assert "@import" not in page
    assert "url(" not in page


def test_studio_js_contains_no_html_injection_methods():
    studio_js = (ASSETS_DIR / "studio.js").read_text(encoding="utf-8")
    forbidden = ["innerHTML", "insertAdjacentHTML", "outerHTML", "document.write"]
    for method in forbidden:
        assert method not in studio_js, f"studio.js must not contain {method}"


def test_every_fetch_argument_starts_with_quote_and_slash():
    studio_js = (ASSETS_DIR / "studio.js").read_text(encoding="utf-8")

    # Match all fetch calls: fetch( <arg> ... )
    fetch_calls = re.findall(r"fetch\(\s*([^,\)]+)", studio_js)
    assert len(fetch_calls) > 0, "No fetch() calls found in studio.js"

    for arg in fetch_calls:
        trimmed = arg.strip()
        assert trimmed.startswith(("'", '"', "`")), (
            f"fetch argument {trimmed!r} must start with a quote"
        )
        assert len(trimmed) > 1 and trimmed[1] == "/", (
            f"fetch argument {trimmed!r} must start with quote and /"
        )


def test_i18n_keys_match_in_vi_and_en():
    i18n = parse_i18n_dict()
    assert "vi" in i18n and "en" in i18n
    vi_keys = set(i18n["vi"].keys())
    en_keys = set(i18n["en"].keys())

    assert len(vi_keys) >= 50, f"Expected at least 50 keys, got {len(vi_keys)}"
    assert vi_keys == en_keys, (
        f"Key mismatch. VI-only: {vi_keys - en_keys}, EN-only: {en_keys - vi_keys}"
    )


def test_every_data_i18n_and_t_key_in_studio_js_exists_in_i18n_dictionary():
    studio_js = (ASSETS_DIR / "studio.js").read_text(encoding="utf-8")
    i18n = parse_i18n_dict()
    vi_keys = set(i18n["vi"].keys())

    # Extract all t("...") and t('...')
    t_keys = set(re.findall(r't\(\s*["\']([a-zA-Z0-9_]+)["\']\s*\)', studio_js))

    # Extract all data-i18n references
    attr_keys = set(re.findall(r'["\']data-i18n["\']\s*:\s*["\']([a-zA-Z0-9_]+)["\']', studio_js))
    literal_attr_keys = set(re.findall(r'data-i18n\s*=\s*["\']([a-zA-Z0-9_]+)["\']', studio_js))

    all_used_keys = t_keys | attr_keys | literal_attr_keys
    assert len(all_used_keys) > 0, "No i18n keys found in studio.js"

    missing = all_used_keys - vi_keys
    assert not missing, f"Keys used in studio.js missing from I18N: {sorted(missing)}"


def test_the_boot_json_has_agent_target_board_voice(studio: StudioServer):
    _, _, body = get(studio, "/")
    page = body.decode("utf-8")

    match = re.search(r'<script type="application/json" id="ne-boot">(.*?)</script>', page)
    assert match is not None, "ne-boot script element not found"

    boot = json.loads(match.group(1))
    required_keys = {"agent", "target", "board", "voice"}
    assert required_keys.issubset(boot.keys()), f"boot JSON missing keys from {required_keys}"
    assert isinstance(boot["agent"], str) and boot["agent"]
    assert boot["target"] == "sim"
    assert boot["board"] == "sim-default"
    assert isinstance(boot["voice"], bool)


def test_assets_budget_under_120kb():
    css_size = (ASSETS_DIR / "studio.css").stat().st_size
    i18n_size = (ASSETS_DIR / "i18n.js").stat().st_size
    js_size = (ASSETS_DIR / "studio.js").stat().st_size
    total_size = css_size + i18n_size + js_size

    # Hard rule 6: target under ~120 KB total
    assert total_size < 120 * 1024, f"Total assets size {total_size} bytes exceeds 120 KB"
