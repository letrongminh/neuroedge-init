"""
TSK-I2f-14, Q-83 — one image of box and brain: `neuroedge build --target esp32s3 --brain neuroclaw`.

`engine/brain.py` puts NeuroClaw-ESP, checked against `targets/esp32s3/brain/neuroclaw.lock`, and
the bridge into the project, and cuts the brain's workspace from `storage`
(docs/spec/deployment_profiles.md DP-B-01, DP-B-09). The real component lives in the NeuroClaw
repository; these tests stand a component of their own in for it, pinned the same way, so the
check itself is what is tested, offline.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from neuroedge.engine import brain
from neuroedge.engine.compiler import build
from neuroedge.engine.firmware import PROJECT_DIR, firmware_root, owned
from neuroedge.errors import BuildFailed, NeuroEdgeError

ROOT = Path(__file__).resolve().parents[2]
DEMO = ROOT / "fixtures" / "agents" / "chat-den-cua" / "agent.toml"


@pytest.fixture
def stand_in(tmp_path, monkeypatch) -> Path:
    """A NeuroClaw checkout of a few files, and a pin that names it."""
    component = tmp_path / "neuroclaw" / brain.IN_REPOSITORY
    for name, text in {
        "CMakeLists.txt": 'idf_component_register(SRCS "src/nc_brain.c" INCLUDE_DIRS "include")\n',
        "Kconfig": 'menu "NeuroClaw"\nendmenu\n',
        "include/neuroclaw.h": "/* the brain */\n",
        "src/nc_brain.c": "/* the loop */\n",
        "test/test_core_host.c": "/* host only */\n",
    }.items():
        (component / name).parent.mkdir(parents=True, exist_ok=True)
        (component / name).write_text(text)
    lock = tmp_path / "neuroclaw.lock"
    pinned = brain.Lock(
        lock,
        "https://github.com/letrongminh/neuroclaw",
        "esp32-test",
        "0" * 40,
        brain.tree_sha256(component),
    )
    monkeypatch.setattr(brain, "load_lock", lambda _root: pinned)
    return tmp_path / "neuroclaw"


def test_the_committed_pin_names_a_commit_and_a_tree():
    """DP-NF-02: the box fetches NeuroClaw by version and SHA-256, nowhere else."""
    data = json.loads((firmware_root() / brain.LOCK).read_text())
    assert data["repository"].startswith("https://github.com/")
    assert re.fullmatch(r"[0-9a-f]{40}", data["commit"])
    assert re.fullmatch(r"[0-9a-f]{64}", data["tree_sha256"])
    assert data["version"]
    assert brain.load_lock(firmware_root()).tree_sha256 == data["tree_sha256"]


def test_build_with_the_brain_writes_one_project_with_its_pin(stand_in, tmp_path):
    """TC-B-01-1: NeuroClaw-ESP, the bridge and the pin in the project; host-only files out."""
    out = tmp_path / "out"
    build(
        DEMO,
        target="esp32s3",
        board_id="esp32s3-box-3",
        out_dir=out,
        brain="neuroclaw",
        brain_source=stand_in,
    )
    project = out / PROJECT_DIR
    assert (project / "components/neuroclaw/include/neuroclaw.h").is_file()
    assert not (project / "components/neuroclaw/test").exists()
    assert (project / "components/ne_brain_bridge/src/ne_brain_bridge.c").is_file()
    assert not (project / "components/ne_brain_bridge/test").exists()
    pin = (project / brain.PIN).read_text()
    assert (
        "neuroclaw esp32-test" in pin and brain.tree_sha256(stand_in / brain.IN_REPOSITORY) in pin
    )
    listed = (project / ".neuroedge-build").read_text().splitlines()
    assert brain.PIN in listed and all(owned(name) for name in listed[2:])
    assert "ws," in (project / "partitions.csv").read_text()


def test_a_tampered_brain_fails_the_build_naming_the_pin(stand_in, tmp_path):
    """TC-B-01-1: one byte changed in NeuroClaw-ESP -> a build error that names the lock file."""
    source = stand_in / brain.IN_REPOSITORY / "src" / "nc_brain.c"
    source.write_text(source.read_text() + "/* changed */\n")
    out = tmp_path / "out"
    with pytest.raises(BuildFailed) as failed:
        build(
            DEMO,
            target="esp32s3",
            board_id="esp32s3-box-3",
            out_dir=out,
            brain="neuroclaw",
            brain_source=stand_in,
        )
    text = str(failed.value) + " ".join(f"{p.where} {p.why}" for p in failed.value.problems)
    assert "neuroclaw.lock" in text and "tree_sha256" in text
    assert not (out / PROJECT_DIR).exists()  # nothing written


def test_a_brain_is_for_the_one_chip_only(stand_in, tmp_path):
    with pytest.raises(BuildFailed) as failed:
        build(DEMO, target="sim", board_id="sim-default", out_dir=tmp_path, brain="neuroclaw")
    assert any("--brain" in p.where for p in failed.value.problems)


def test_without_the_brain_the_project_is_the_box_alone(tmp_path):
    build(DEMO, target="esp32s3", board_id="esp32s3-box-3", out_dir=tmp_path)
    project = tmp_path / PROJECT_DIR
    assert not (project / "components/neuroclaw").exists()
    assert not (project / "components/ne_brain_bridge").exists()
    assert "ws," not in (project / "partitions.csv").read_text()


# --- the partition table (DP-B-09) ---------------------------------------------------------


def test_the_brains_partition_table_holds_box_brain_and_signed_ota():
    """TC-B-09-1: aligned, no overlap, OTA slots >= the image, ws >= 1 MB, nvs_keys encrypted."""
    base = (firmware_root() / "partitions.csv").read_text()
    table = brain.brain_partitions(base)
    assert brain.partition_problems(table) == []
    rows = {r[0]: r for r in brain._rows(table)}
    old = {r[0]: r for r in brain._rows(base)}
    for name in ("factory", "ota_0", "ota_1", "ne_config", "nvs_keys", "nvs", "otadata"):
        assert rows[name][3] == old[name][3], f"{name} moved"  # the box's offsets stay
    assert int(rows["ws"][4], 16) >= brain.WORKSPACE_MIN


@pytest.mark.parametrize(
    "change, problem",
    [
        (
            (
                "ota_1,    app,  ota_1,   0x710000,0x380000,",
                "ota_1,    app,  ota_1,   0x718000,0x380000,",
            ),
            "not aligned",
        ),
        (
            (
                "ota_0,    app,  ota_0,   0x390000,0x380000,",
                "ota_0,    app,  ota_0,   0x390000,0x300000,",
            ),
            "image budget",
        ),
        (("0xf96000,0x1000, encrypted", "0xf96000,0x1000,"), "nvs_keys must be encrypted"),
        (("ws,       data, littlefs", "ws,       data, spiffs"), "littlefs"),
        (("ne_config, data, nvs,    0xf90000", "ne_config, data, nvs,    0xf8f000"), "overlaps"),
    ],
)
def test_a_table_that_breaks_a_rule_is_named(change, problem):
    table = brain.brain_partitions((firmware_root() / "partitions.csv").read_text())
    assert change[0] in table
    assert any(problem in p for p in brain.partition_problems(table.replace(*change)))


def _served(monkeypatch, checkout: Path) -> None:
    """`urlopen` answers with a codeload-style archive of `checkout`."""
    import io
    import tarfile

    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode="w:gz") as archive:
        archive.add(checkout, arcname="neuroclaw-0000")
    payload = data.getvalue()

    class Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    monkeypatch.setattr(brain.urllib.request, "urlopen", lambda *_a, **_k: Response(payload))


def test_a_fetched_brain_enters_the_cache_only_when_it_matches_the_pin(
    stand_in, tmp_path, monkeypatch
):
    """DP-B-01: a tampered download fails and leaves nothing cached; the pinned one is kept."""
    lock = brain.load_lock(tmp_path)
    cache = tmp_path / "cache"
    (stand_in / brain.IN_REPOSITORY / "src" / "nc_brain.c").write_text("/* changed */\n")
    _served(monkeypatch, stand_in)
    with pytest.raises(NeuroEdgeError, match="tree_sha256"):
        brain.fetch(lock, cache)
    assert not any(cache.iterdir())
    (stand_in / brain.IN_REPOSITORY / "src" / "nc_brain.c").write_text("/* the loop */\n")
    _served(monkeypatch, stand_in)
    fetched = brain.fetch(lock, cache)
    assert brain.tree_sha256(fetched) == lock.tree_sha256
    assert [p.name for p in cache.iterdir()] == [fetched.name]
