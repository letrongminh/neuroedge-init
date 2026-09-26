"""
The C side of the device UI, pinned to the Python facts (TSK-S4-10).

The UI is C (`targets/esp32s3/ui/`), but three of its facts live in Python or
in both places and must not drift apart:

* the shipped languages: `firmware.UI_LANGUAGES` and the string tables;
* the reason codes: `firmware.REASONS` and the `ne_ui_reason_t` enum/table;
* the screen matrix: every `ne_ui_show_*` screen and every case in the golden
  runner, with one golden per case in both languages, 320x240.

Plus the licence record (CONTRIBUTING.md §4): the generated fonts and the OFL
text are there, the generator script pins its sources by SHA-256, and NOTICE
names them. The golden render itself is CI's (`scripts/run_ui_golden.sh`).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from neuroedge.engine.firmware import REASONS, UI_LANGUAGES

ROOT = Path(__file__).parent.parent.parent
UI = ROOT / "targets" / "esp32s3" / "ui"
HEADER = UI / "include" / "ne_ui.h"
STRINGS = UI / "src" / "ne_ui_strings.c"
MAIN = UI / "host" / "main.c"
RANGES = UI / "fonts" / "ranges.txt"


def read(path: Path) -> str:
    assert path.is_file(), f"{path} is missing"
    return path.read_text(encoding="utf-8")


def golden_cases() -> list[str]:
    """The case names of the runner's matrix, in order."""
    body = read(MAIN).split("static const ui_case CASES[] = {", 1)[1].split("};", 1)[0]
    return re.findall(r'\{"([a-z0-9_]+)",\s*case_', body)


def show_functions() -> set[str]:
    return set(re.findall(r"\bvoid (ne_ui_show_[a-z_]+)\(", read(HEADER)))


def called_show_functions() -> set[str]:
    return set(re.findall(r"\b(ne_ui_show_[a-z_]+)\(", read(MAIN)))


def ui_reason_values() -> dict[str, int]:
    found = {
        name: int(value)
        for name, value in re.findall(r"NE_UI_REASON_([A-Z_]+) = (\d+),", read(HEADER))
    }
    for sentinel in ("NONE", "COUNT"):
        found.pop(sentinel, None)
    return found


def string_literals(source: str) -> list[str]:
    return re.findall(r'"((?:[^"\\]|\\.)*)"', source)


def glyph_ranges() -> list[tuple[int, int]]:
    ranges = []
    for line in read(RANGES).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        for token in line.rstrip(",").split(","):
            low, _, high = token.strip().partition("-")
            ranges.append((int(low, 16), int(high or low, 16)))
    return ranges


def font_codepoints(path: Path) -> set[int]:
    """
    Every code point the generated font can draw, read from its `cmaps` the way
    LVGL reads them: a contiguous map covers `range_start … range_start +
    range_length - 1`; a sparse map lists offsets from `range_start`.
    """
    source = read(path)
    covered: set[int] = set()
    maps = re.search(
        r"static const lv_font_fmt_txt_cmap_t cmaps\[\] =\s*\{(.*?)\n\};", source, re.S
    )
    assert maps, f"{path} has no cmaps: is it a generated LVGL font?"
    for entry in re.finditer(
        r"\.range_start = (\d+), \.range_length = (\d+),.*?\.unicode_list = (\w+),",
        maps.group(1),
        re.S,
    ):
        start, length, unicode_list = int(entry.group(1)), int(entry.group(2)), entry.group(3)
        if unicode_list == "NULL":
            covered.update(range(start, start + length))
            continue
        table = re.search(rf"static const \w+ {unicode_list}\[\] = \{{(.*?)\}};", source, re.S)
        assert table, f"{path}: {unicode_list} is not in the file"
        # lv_font_conv writes these as hex (0x1c80), as LVGL's relative code points.
        covered.update(
            start + int(value, 0) for value in re.findall(r"0x[0-9a-fA-F]+|\d+", table.group(1))
        )
    return covered


def table_characters() -> set[str]:
    """Every non-ASCII character the Vietnamese and English tables draw."""
    characters = set()
    for literal in string_literals(read(STRINGS)):
        for char in literal.replace("\\n", "").replace('\\"', '"'):
            if ord(char) >= 0x80:
                characters.add(char)
    return characters


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", f"{path} is not a PNG"
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


# --- shipped languages ------------------------------------------------------------------------


def test_the_string_tables_ship_exactly_the_python_languages() -> None:
    codes = [m.group(1).lower() for m in re.finditer(r"NE_UI_LANG_([A-Z]{2})\b", read(STRINGS))]
    assert sorted(set(codes)) == sorted(UI_LANGUAGES)
    for language in UI_LANGUAGES:
        assert f'.code = "{language}"' in read(STRINGS)


def test_every_string_table_character_is_in_every_generated_fonts_cmap() -> None:
    # The real question is what the fonts can draw, not what ranges.txt asked
    # lv_font_conv for: a character the generated cmap lacks renders as a box.
    wanted = table_characters()
    for font in sorted((UI / "fonts").glob("ne_font_*.c")):
        covered = font_codepoints(font)
        missing = sorted(
            {f"U+{ord(char):04X} {char!r}" for char in wanted if ord(char) not in covered}
        )
        assert missing == [], f"{font.name} has no glyph for {missing}"


def test_the_range_file_is_what_the_generator_passes() -> None:
    # ranges.txt is the generator's input; a range that survives generation must
    # be visible to the test that checks coverage.
    script = read(ROOT / "scripts" / "gen_ui_fonts.sh")
    assert '--range "$RANGES"' in script
    assert "grep -v '^[[:space:]]*#' \"$FONTS/ranges.txt\"" in script
    assert glyph_ranges(), "fonts/ranges.txt is empty"


# --- reason codes -----------------------------------------------------------------------------


def test_the_reason_enum_matches_the_walkers_reasons() -> None:
    expected = {name.upper(): value for name, value in REASONS.items() if name is not None}
    assert ui_reason_values() == expected


def test_every_reason_has_a_localized_label_in_every_language() -> None:
    entries: dict[str, list[str]] = {}
    for name, label in re.findall(
        r"\[NE_UI_REASON_([A-Z_]+)\]\s*=\s*(\"(?:[^\"\\]|\\.)*\")", read(STRINGS)
    ):
        entries.setdefault(name, []).append(label)
    expected = {name.upper() for name in REASONS if name is not None} | {"NONE"}
    assert set(entries) == expected
    for name, labels in entries.items():
        assert len(labels) == len(UI_LANGUAGES), f"{name} has {len(labels)} labels"
        if name == "NONE":
            assert all(label == '""' for label in labels)
        else:
            assert all(label != '""' for label in labels), f"{name} has an empty label"


# --- the screen matrix and its goldens --------------------------------------------------------


def test_the_runner_covers_every_screen_function() -> None:
    assert show_functions() == called_show_functions()
    assert len(show_functions()) >= 9, (
        "the full screen set is idle, boot, voice, confirm, verdict, degraded, sensor, OTA, fatal"
    )


@pytest.mark.parametrize("language", UI_LANGUAGES)
def test_goldens_are_exactly_the_case_matrix(language: str) -> None:
    folder = UI / "golden" / language
    assert folder.is_dir(), f"{folder} is missing: run scripts/run_ui_golden.sh --update"
    found = sorted(path.stem for path in folder.glob("*.png"))
    assert found == sorted(golden_cases())
    for name in golden_cases():
        assert png_size(folder / f"{name}.png") == (320, 240)


def test_the_two_languages_render_the_same_cases() -> None:
    vietnamese = {path.name for path in (UI / "golden" / "vi").glob("*.png")}
    english = {path.name for path in (UI / "golden" / "en").glob("*.png")}
    assert vietnamese == english
    assert len(vietnamese) == len(golden_cases())


# --- licences and pins (CONTRIBUTING.md §4) ----------------------------------------------------


def font_source_shas() -> list[str]:
    """The two font pins of the generator, in file order (the OFL pin is third)."""
    script = read(ROOT / "scripts" / "gen_ui_fonts.sh")
    return [
        match.group(1)
        for match in re.finditer(r"(?:REGULAR|SEMIBOLD)_SHA=\"([0-9a-f]{64})\"", script)
    ]


def test_the_generator_pins_its_sources() -> None:
    script = read(ROOT / "scripts" / "gen_ui_fonts.sh")
    assert "lv_font_conv@1.5.3" in script
    assert len(font_source_shas()) == 2
    assert re.search(r"OFL_SHA=\"[0-9a-f]{64}\"", script)
    assert (
        script.count('_URL="https://raw.githubusercontent.com/google/fonts/main/ofl/bevietnampro/')
        == 3
    )


def test_every_font_carries_its_attribution_and_source_sha() -> None:
    shas = font_source_shas()
    fonts = sorted((UI / "fonts").glob("ne_font_*.c"))
    assert [font.name for font in fonts] == ["ne_font_12.c", "ne_font_16.c", "ne_font_22.c"]
    for font in fonts:
        source = read(font)
        assert "scripts/gen_ui_fonts.sh" in source
        assert "SIL Open Font License 1.1" in source
        assert "LICENSES/OFL-1.1.txt" in source
        assert "Modified Version" in source and "Reserved Font Name" in source
        assert any(sha in source for sha in shas), font


def test_notice_records_the_same_source_pins_as_the_generator() -> None:
    notice = read(ROOT / "NOTICE")
    for sha in font_source_shas():
        assert sha in notice, "NOTICE does not record the font pin the generator verifies"


def test_the_compressed_fonts_are_enabled_or_the_build_stops() -> None:
    # LVGL draws blank glyphs and only warns when compressed fonts are disabled;
    # the UI header turns that into a build error, and the harness enables it.
    fonts_header = read(UI / "fonts" / "ne_fonts.h")
    assert "LV_USE_FONT_COMPRESSED" in fonts_header and "#error" in fonts_header
    assert "#define LV_USE_FONT_COMPRESSED 1" in read(UI / "host" / "lv_conf.h")


def test_the_ofl_text_ships_and_notice_names_the_font_and_lvgl() -> None:
    assert (
        (ROOT / "LICENSES" / "OFL-1.1.txt")
        .read_text(encoding="utf-8")
        .startswith("Copyright 2021 The Be Vietnam Pro Project Authors")
    )
    notice = read(ROOT / "NOTICE")
    assert "Be Vietnam Pro" in notice
    assert "OFL-1.1" in notice
    assert "LVGL" in notice
    licensing = read(ROOT / "LICENSING.md")
    assert "OFL-1.1" in licensing


def test_the_host_harness_pins_lvgl_by_url_and_sha256() -> None:
    cmake = read(UI / "host" / "CMakeLists.txt")
    assert "v9.6.0" in cmake
    assert (
        "URL_HASH SHA256=b20ee3acc1bba13c62d854f9ebd62e4c51e0b443b1e0225892e86442defa84df" in cmake
    )
    assert "lv_test_display" in read(MAIN)
    assert "lv_test_screenshot_compare" in read(MAIN)


def test_the_run_script_is_the_ci_entry_point() -> None:
    workflow = read(ROOT / ".github" / "workflows" / "ci-sim-linux.yml")
    assert "scripts/run_ui_golden.sh" in workflow
