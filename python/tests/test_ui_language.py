"""
The device UI language rule (TSK-S4-10, FR-HAL-01) — docs/spec/ui.md §Ngôn ngữ.

`[agent] language` wins; else `[stt] language`; else `vi`. The shape and the
conflict (both set, different) are checked at manifest load, so **every** target
refuses them; only the `--target esp32s3` build checks that the UI has strings
and glyphs for the code. The generated `ne_agent` component carries the resolved
code as `NE_AGENT_LANGUAGE` so the device shows one language, the one its gates'
messages are written for.

The C side of the same fact is pinned in `test_ui_assets.py`; the golden render
itself is CI's job (`scripts/run_ui_golden.sh`).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from neuroedge.engine.compiler import AgentManifest, build, load_agent_manifest
from neuroedge.engine.firmware import UI_LANGUAGES, firmware_problems, render_component, ui_language
from neuroedge.errors import AgentManifestError, NeuroEdgeError

BASE = """
[agent]
name    = "language-test"
version = "0.1.0"

[requires]
"digital.out" = { pins = ["lamp"] }
"""


def write_agent(
    tmp_path: Path,
    *,
    raw_agent_language: str | None = None,
    stt_language: str | None = None,
    raw_stt_language: str | None = None,
) -> Path:
    """A minimal agent.toml; a `raw_*` value goes in verbatim (malformed cases)."""
    lines = ["[agent]", 'name    = "language-test"', 'version = "0.1.0"']
    if raw_agent_language is not None:
        lines.append(f"language = {raw_agent_language}")
    lines += ["", "[requires]", '"digital.out" = { pins = ["lamp"] }']
    if stt_language is not None or raw_stt_language is not None:
        lines += ["", "[stt]"]
        if raw_stt_language is not None:
            lines.append(f"language = {raw_stt_language}")
        if stt_language is not None:
            lines.append(f'language = "{stt_language}"')
    path = tmp_path / "agent.toml"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def agent(tmp_path: Path, **kwargs) -> AgentManifest:
    return load_agent_manifest(write_agent(tmp_path, **kwargs))


def parts(error: BaseException) -> tuple[str, str, str]:
    assert isinstance(error, NeuroEdgeError), error
    assert error.where and error.why and error.how, error.render()
    return error.where, error.why, error.how


def test_no_language_anywhere_defaults_to_vietnamese(tmp_path: Path) -> None:
    assert ui_language(agent(tmp_path)) == "vi"


def test_stt_language_is_taken_when_agent_language_is_absent(tmp_path: Path) -> None:
    assert ui_language(agent(tmp_path, stt_language="en")) == "en"


def test_agent_language_wins_when_both_agree(tmp_path: Path) -> None:
    manifest = agent(tmp_path, raw_agent_language='"en"', stt_language="en")
    assert ui_language(manifest) == "en"


def test_agent_language_alone_is_used(tmp_path: Path) -> None:
    assert ui_language(agent(tmp_path, raw_agent_language='"vi"')) == "vi"


def test_disagreeing_languages_are_refused_at_manifest_load(tmp_path: Path) -> None:
    path = write_agent(tmp_path, raw_agent_language='"vi"', stt_language="en")
    with pytest.raises(AgentManifestError) as info:
        load_agent_manifest(path)
    where, why, how = parts(info.value)
    assert where.endswith("-> [agent] language")
    assert "'vi'" in why and "'en'" in why
    assert "[stt] language" in how


@pytest.mark.parametrize("target", ["sim", "linux"])
def test_the_conflict_is_refused_on_every_target(tmp_path: Path, target: str) -> None:
    # build() loads the manifest before it looks at the board or the target, so a
    # conflict stops every target, not only the one with a screen.
    path = write_agent(tmp_path, raw_agent_language='"vi"', stt_language="en")
    with pytest.raises(AgentManifestError):
        build(path, target=target, board_id="sim-default" if target == "sim" else "linux-rpi5")


@pytest.mark.parametrize(
    ("kwargs", "where"),
    [
        ({"raw_agent_language": '"fr"'}, "[agent] language"),
        ({"stt_language": "ja"}, "[stt] language"),
    ],
)
def test_unsupported_language_is_refused_where_a_ui_exists(
    tmp_path: Path, kwargs: dict[str, str], where: str
) -> None:
    manifest = agent(tmp_path, **kwargs)
    with pytest.raises(AgentManifestError) as info:
        ui_language(manifest)
    reported, why, how = parts(info.value)
    assert where in reported
    assert "no strings or glyphs" in why
    assert str(list(UI_LANGUAGES)) in why
    assert "docs/spec/ui.md" in how


@pytest.mark.parametrize("raw", ['"VI"', '"vietnamese"', '"vie"', "3", "true"])
def test_malformed_agent_language_is_refused_at_load(tmp_path: Path, raw: str) -> None:
    path = write_agent(tmp_path, raw_agent_language=raw)
    with pytest.raises(AgentManifestError) as info:
        load_agent_manifest(path)
    where, why, how = parts(info.value)
    assert where.endswith("-> [agent] language")
    assert "ISO-639-1" in why and "two lowercase letters" in why
    assert 'language = "vi"' in how


def test_a_malformed_stt_language_is_ignored_by_the_rule(tmp_path: Path) -> None:
    # The manifest itself is check_speech()'s to refuse; the rule must not crash on it
    # and must not read `3` as a language code.
    manifest = load_agent_manifest(write_agent(tmp_path, raw_stt_language="3"))
    assert ui_language(manifest) == "vi"


def test_problems_collect_the_language_error(tmp_path: Path) -> None:
    manifest = agent(tmp_path, raw_agent_language='"fr"')
    problems = firmware_problems(manifest, {})
    assert [type(problem) for problem in problems] == [AgentManifestError]
    assert "no strings or glyphs" in problems[0].why


def test_generated_component_carries_the_resolved_language(tmp_path: Path) -> None:
    for kwargs, expected in (
        ({}, "vi"),
        ({"raw_agent_language": '"en"'}, "en"),
        ({"stt_language": "en"}, "en"),
    ):
        manifest = agent(tmp_path, **kwargs)
        header = render_component(manifest, "esp32s3-box-3", {}, [])["include/ne_agent.h"]
        assert f'#define NE_AGENT_LANGUAGE "{expected}"' in header


def test_the_same_agent_renders_the_same_language_bytes(tmp_path: Path) -> None:
    manifest = agent(tmp_path, raw_agent_language='"en"')
    first = render_component(manifest, "esp32s3-box-3", {}, [])
    second = render_component(manifest, "esp32s3-box-3", {}, [])
    assert first == second


def test_the_loader_resolves_agent_then_stt_then_nothing(tmp_path: Path) -> None:
    assert agent(tmp_path, raw_agent_language='"en"').language == "en"
    assert agent(tmp_path, stt_language="en").language == "en"
    assert agent(tmp_path).language is None
