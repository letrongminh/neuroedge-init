"""
The brain in the image: `neuroedge build --target esp32s3 --brain neuroclaw` (Q-79, Q-83, Profile B).

One ESP-IDF project holds the box (`ne_*`), the bridge (`components/ne_brain_bridge/`) and
NeuroClaw-ESP, pinned (docs/spec/deployment_profiles.md DP-B-01, DP-B-09, DP-NF-02):

* `targets/esp32s3/brain/neuroclaw.lock` names the NeuroClaw repository, a version, the commit
  and the SHA-256 of the component's file tree (`tree_sha256`: every file's SHA-256 and path,
  sorted). The tree is what is checked, not an archive: the same files give the same hash
  however they were fetched. A mismatch fails the build and names the lock file.
* `--brain-source` is a NeuroClaw checkout (or the component directory itself); without it the
  build fetches the pinned commit from the repository into a cache, then checks it the same way.
* The partition table gains a LittleFS `ws` for the brain's workspace, taken from the end of
  `storage`, so no other offset moves (`ne_config`, `nvs_keys` stay where the box keeps them).

Host-only files (`test/`) are not copied. `main/brain.c` starts the brain on the bridge
(`neuroclaw_start` with its `nc_gate`); `components/ne_hal` and the LittleFS dependency of
`main/idf_component.yml` come with it.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import tarfile
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from ..errors import NeuroEdgeError

BRAINS = ("neuroclaw",)
LOCK = "brain/neuroclaw.lock"  # relative to targets/esp32s3/
IN_REPOSITORY = "esp32/components/neuroclaw"
COMPONENT = "components/neuroclaw"
BRIDGE = "components/ne_brain_bridge"
HAL = "components/ne_hal"  # the token door the bridge drives pins through (DP-B-08)
MAIN_DEPENDENCIES = "main/idf_component.yml"
# NeuroClaw-ESP keeps its workspace on LittleFS (`ws`); the version its examples pin.
LITTLEFS = "joltwallet/littlefs"
LITTLEFS_VERSION = "==1.22.3"
PIN = f"{COMPONENT}/NEUROEDGE_PIN"
# What the image may grow to (Q-3) and what the brain's workspace needs (DP-B-09, DP-B-13).
IMAGE_BUDGET = 0x380000
WORKSPACE_MIN = 0x100000
FLASH_SIZE = 0x1000000  # ESP32-S3 N16R8
# What the build reads from the firmware sources for the brain, besides firmware.SOURCES: the
# installed wheel carries exactly these (hatch_build.py BRAIN_SOURCES, test_packaging.py).
SOURCES = (
    LOCK,
    f"{BRIDGE}/CMakeLists.txt",
    f"{BRIDGE}/include/*.h",
    f"{BRIDGE}/src/*.c",
    f"{HAL}/CMakeLists.txt",
    f"{HAL}/include/*.h",
    f"{HAL}/src/*.c",
)
# The files of the two components a project holds, as `firmware.OWNED` patterns.
OWNED = (
    f"{COMPONENT}/CMakeLists.txt",
    f"{COMPONENT}/Kconfig",
    f"{COMPONENT}/include/*.h",
    f"{COMPONENT}/src/*.c",
    PIN,
    f"{BRIDGE}/CMakeLists.txt",
    f"{BRIDGE}/include/*.h",
    f"{BRIDGE}/src/*.c",
    f"{HAL}/CMakeLists.txt",
    f"{HAL}/include/*.h",
    f"{HAL}/src/*.c",
    MAIN_DEPENDENCIES,
)


@dataclass(frozen=True)
class Lock:
    path: Path
    repository: str
    version: str
    commit: str
    tree_sha256: str


def load_lock(firmware_root: Path) -> Lock:
    path = firmware_root / LOCK
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return Lock(
            path,
            str(data["repository"]),
            str(data["version"]),
            str(data["commit"]),
            str(data["tree_sha256"]),
        )
    except (OSError, ValueError, KeyError) as error:
        raise NeuroEdgeError(
            where=str(path),
            why=f"the NeuroClaw pin cannot be read: {error}",
            how="restore it from the repository; it names the repository, version, commit and "
            "tree_sha256",
        ) from error


def tree_sha256(directory: Path) -> str:
    """SHA-256 over `<file sha256>  <path>` lines of every file under `directory`, sorted by path."""
    lines = []
    for path in sorted(p for p in directory.rglob("*") if p.is_file()):
        relative = path.relative_to(directory).as_posix()
        if "\n" in relative or "\r" in relative:
            raise NeuroEdgeError(
                where=str(path),
                why="a file name holds a line break: the tree hash would be ambiguous",
                how="NeuroClaw-ESP has no such file; fetch the pinned commit again",
            )
        lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {relative}\n")
    return hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()


def _component(source: Path) -> Path:
    """The component directory inside a NeuroClaw checkout, or `source` if it is one."""
    inside = source / IN_REPOSITORY
    if inside.is_dir():
        return inside
    if (source / "include" / "neuroclaw.h").is_file():
        return source
    raise NeuroEdgeError(
        where=f"--brain-source {source}",
        why=f"neither a NeuroClaw checkout (no {IN_REPOSITORY}/) nor its ESP-IDF component",
        how="pass the NeuroClaw repository checked out at the pinned commit, or leave "
        "--brain-source out to fetch it",
    )


def fetch(lock: Lock, cache: Path | None = None) -> Path:
    """The pinned commit's component, downloaded once into `cache` (checked by `brain_files`)."""
    cache = cache or Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "neuroedge"
    target = cache / f"neuroclaw-{lock.commit}"
    if (target / "include" / "neuroclaw.h").is_file():
        return target
    owner_repo = lock.repository.removeprefix("https://github.com/").removesuffix(".git")
    url = f"https://codeload.github.com/{owner_repo}/tar.gz/{lock.commit}"
    try:
        with urllib.request.urlopen(url, timeout=60) as response:  # noqa: S310 - https, pinned
            data = response.read()
    except OSError as error:
        raise NeuroEdgeError(
            where=f"{lock.path} ({url})",
            why=f"cannot fetch NeuroClaw {lock.version}: {error}",
            how="check the network, or pass a checkout with --brain-source",
        ) from error
    cache.mkdir(parents=True, exist_ok=True)
    # Extract beside the cache entry and move it in only once its tree matches the pin: an
    # interrupted or tampered download never becomes the cached copy.
    staging = Path(tempfile.mkdtemp(prefix=f".{target.name}.", dir=cache))
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
            for member in archive.getmembers():
                parts = PurePosixPath(member.name).parts
                if len(parts) < 5 or parts[1:4] != tuple(IN_REPOSITORY.split("/")):
                    continue
                relative = PurePosixPath(*parts[4:])
                if not member.isfile() or ".." in relative.parts:
                    continue
                path = staging / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                extracted = archive.extractfile(member)
                if extracted is not None:
                    path.write_bytes(extracted.read())
        found = tree_sha256(staging)
        if found != lock.tree_sha256:
            raise NeuroEdgeError(
                where=f"{lock.path} ({url})",
                why=f"the fetched NeuroClaw-ESP has tree_sha256 {found}, the pin says "
                f"{lock.tree_sha256}",
                how="fetch again; if it persists, the pin or the repository changed (DP-NF-02)",
            )
        shutil.rmtree(target, ignore_errors=True)  # a partial copy without neuroclaw.h
        os.replace(staging, target)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return target


def brain_files(firmware_root: Path, source: Path | None = None) -> dict[str, bytes]:
    """
    NeuroClaw-ESP and the bridge, keyed by their path in the project, and the pin: checked
    against the lock first (DP-B-01). The partition table is `brain_partitions`.
    """
    lock = load_lock(firmware_root)
    component = _component(source) if source is not None else fetch(lock)
    found = tree_sha256(component)
    if found != lock.tree_sha256:
        raise NeuroEdgeError(
            where=str(lock.path),
            why=f"NeuroClaw-ESP at {component} has tree_sha256 {found}, the pin says "
            f"{lock.tree_sha256} ({lock.version}, commit {lock.commit[:12]})",
            how="use the pinned commit; to upgrade, change the pin in one commit with a passing "
            "contract run (DP-NF-02)",
        )
    files: dict[str, bytes] = {}
    for path in sorted(p for p in component.rglob("*") if p.is_file()):
        relative = path.relative_to(component).as_posix()
        if relative.split("/", 1)[0] == "test":
            continue  # host-only
        files[f"{COMPONENT}/{relative}"] = path.read_bytes()
    for part in (BRIDGE, HAL):
        root = firmware_root / part
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            relative = path.relative_to(root).as_posix()
            if relative.split("/", 1)[0] != "test":
                files[f"{part}/{relative}"] = path.read_bytes()
    files[MAIN_DEPENDENCIES] = (
        "# Written by `neuroedge build --brain neuroclaw`: NeuroClaw-ESP's workspace (DP-B-09).\n"
        f'dependencies:\n  {LITTLEFS}: "{LITTLEFS_VERSION}"\n'
    ).encode()
    files[PIN] = (
        f"neuroclaw {lock.version}\ncommit {lock.commit}\ntree_sha256 {lock.tree_sha256}\n"
        f"from {lock.repository}\n"
    ).encode()
    return files


# --- the partition table (DP-B-09) ---------------------------------------------------------


def _rows(text: str) -> list[list[str]]:
    return [
        [cell.strip() for cell in line.split(",")]
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def brain_partitions(base: str) -> str:
    """The box's table for one image of box and brain: two OTA slots and no `factory`
    (ESP-IDF builds anti-rollback, DP-B-17, only so), `storage` grown into the slot that
    frees, and `ws` (LittleFS, WORKSPACE_MIN) cut from its end. nvs, otadata, ne_config and
    nvs_keys keep their offsets."""
    rows = {row[0]: row for row in _rows(base)}
    try:
        slots = [int(rows[name][3], 16) for name in ("factory", "ota_0", "ota_1")]
        storage_end = int(rows["storage"][3], 16) + int(rows["storage"][4], 16)
    except (KeyError, IndexError, ValueError) as error:
        raise NeuroEdgeError(
            where="targets/esp32s3/partitions.csv",
            why=f"no factory, ota_0, ota_1 and storage rows to lay the brain out from ({error})",
            how="keep the box's table: factory, ota_0, ota_1, then storage",
        ) from error
    storage_start = slots[2]  # ota_1's old place; the factory slot went to ota_0
    if storage_end - storage_start < 2 * WORKSPACE_MIN:
        raise NeuroEdgeError(
            where="targets/esp32s3/partitions.csv (storage)",
            why="storage is too small to give the brain its workspace",
            how=f"keep storage at least {2 * WORKSPACE_MIN:#x} bytes",
        )
    moved = {"ota_0": slots[0], "ota_1": slots[1]}
    out = []
    for line in base.splitlines():
        cells = [cell.strip() for cell in line.split(",")]
        if not cells or len(cells) < 5:
            out.append(line)
        elif cells[0] == "factory":
            out.append("# No factory slot: anti-rollback (DP-B-17) boots only ota_0 / ota_1.")
        elif cells[0] in moved:
            name = cells[0]
            out.append(f"{name},    app,  {name},   {moved[name]:#x},{cells[4]},")
        elif cells[0] == "storage":
            size = storage_end - storage_start - WORKSPACE_MIN
            out.append(f"storage,  data, spiffs,  {storage_start:#x},{size:#x},")
            out.append(
                "# The brain's workspace (NeuroClaw-ESP: memory, notes, sessions, cron), "
                "Profile B, DP-B-09"
            )
            out.append(
                f"ws,       data, littlefs,{storage_end - WORKSPACE_MIN:#x},{WORKSPACE_MIN:#x},"
            )
        else:
            out.append(line)
    return "\n".join(out) + "\n"


def partition_problems(text: str) -> list[str]:
    """What is wrong with a table for one image of box and brain (empty when nothing is)."""
    problems: list[str] = []
    rows = _rows(text)
    by_name = {row[0]: row for row in rows}
    spans = []
    for row in rows:
        name, kind, subtype, offset, size = row[:5]
        start, length = int(offset, 16), int(size, 16)
        align = 0x10000 if kind == "app" else 0x1000
        if start % align:
            problems.append(f"{name} at {offset} is not aligned to {align:#x}")
        spans.append((start, start + length, name))
        if kind == "app" and length < IMAGE_BUDGET:
            problems.append(f"{name} ({size}) is smaller than the image budget {IMAGE_BUDGET:#x}")
    spans.sort()
    for (_, end, name), (start, _, after) in zip(spans, spans[1:], strict=False):
        if start < end:
            problems.append(f"{after} overlaps {name}")
    if spans and spans[-1][1] > FLASH_SIZE:
        problems.append(f"{spans[-1][2]} ends past the {FLASH_SIZE:#x} bytes of flash")
    for name in ("ota_0", "ota_1", "ne_config", "nvs_keys", "ws"):
        if name not in by_name:
            problems.append(f"no {name} partition")
    if "factory" in by_name:
        problems.append("a factory partition: anti-rollback (DP-B-17) builds only without one")
    ws = by_name.get("ws")
    if ws is not None and (ws[2] != "littlefs" or int(ws[4], 16) < WORKSPACE_MIN):
        problems.append(f"ws must be littlefs of at least {WORKSPACE_MIN:#x} bytes")
    keys = by_name.get("nvs_keys")
    if keys is not None and "encrypted" not in keys[5:]:
        problems.append("nvs_keys must be encrypted")
    return problems
