"""
Is the brain kept apart from the box? `neuroedge doctor` (Q-83, DP-A-03, TSK-I2d-24).

In Profile A on one machine the brain (NeuroClaw) runs under an OS user of its own. The box's
promises hold only if that user cannot reach what the box guards (docs/spec/deployment_profiles.md
DP-A-03, threat model §2k):

* no device group — `gpio`, `i2c`, `spi`, `dialout`, `video`, `audio`, `plugdev`, `input`;
* no access to `/dev/gpiochip*`, `/dev/i2c-*`, `/dev/spidev*` by owner, group or other bits;
* no read of the box's key directory, nor of any file or directory under it;
* `/proc` mounted with `hidepid=2` (or `invisible`), the brain's user not in its `gid=` group
  (that group sees every process): otherwise the brain reads the box's command line and
  environment. The last mount of `/proc` is the one in force.

Each check reads the system through `System`, so the tests give it a fake one. A check it cannot
make (not Linux, no such user) is a problem too: fail closed.
"""

from __future__ import annotations

import contextlib
import os
import stat
from dataclasses import dataclass, field
from pathlib import Path

DEVICE_GROUPS = ("gpio", "i2c", "spi", "dialout", "video", "audio", "plugdev", "input")
DEVICE_GLOBS = ("gpiochip*", "i2c-*", "spidev*")


@dataclass
class Account:
    name: str
    uid: int
    gid: int
    groups: dict[str, int] = field(default_factory=dict)  # every group the user is in: name -> gid


@dataclass
class System:
    """What the checks read; `System.live()` reads this machine."""

    account: Account | None
    proc_mounts: str
    dev: Path = Path("/dev")

    @classmethod
    def live(cls, user: str) -> System:
        import grp
        import pwd

        try:
            entry = pwd.getpwnam(user)
        except KeyError:
            account = None
        else:
            groups = {g.gr_name: g.gr_gid for g in grp.getgrall() if user in g.gr_mem}
            with contextlib.suppress(KeyError):
                groups[grp.getgrgid(entry.pw_gid).gr_name] = entry.pw_gid
            account = Account(user, entry.pw_uid, entry.pw_gid, groups)
        try:
            mounts = Path("/proc/mounts").read_text(encoding="utf-8")
        except OSError:
            mounts = ""
        return cls(account, mounts)


def _can(account: Account, info: os.stat_result, read: int, other: int, group: int) -> bool:
    """Whether `account` has the access bits `read` (owner), `group`, `other` on a file."""
    if account.uid == 0:
        return True
    if info.st_uid == account.uid:
        return bool(info.st_mode & read)
    if info.st_gid in account.groups.values():
        return bool(info.st_mode & group)
    return bool(info.st_mode & other)


def _reads(account: Account, path: Path) -> bool:
    info = path.stat()
    return _can(account, info, stat.S_IRUSR, stat.S_IROTH, stat.S_IRGRP)


def _enters(account: Account, path: Path) -> bool:
    info = path.stat()
    return _can(account, info, stat.S_IXUSR, stat.S_IXOTH, stat.S_IXGRP)


def _opens_device(account: Account, path: Path) -> bool:
    info = path.stat()
    readable = _can(account, info, stat.S_IRUSR, stat.S_IROTH, stat.S_IRGRP)
    writable = _can(account, info, stat.S_IWUSR, stat.S_IWOTH, stat.S_IWGRP)
    return readable or writable


def _proc_options(mounts: str) -> list[str] | None:
    """The options of the last `proc` mount on `/proc` (the one in force), or None."""
    found = None
    for line in mounts.splitlines():
        fields = line.split()
        if len(fields) >= 4 and fields[1] == "/proc" and fields[2] == "proc":
            found = fields[3].split(",")
    return found


def problems(system: System, keys: Path) -> list[str]:
    """Every way the brain's user reaches what the box guards; empty when it is kept apart."""
    account = system.account
    if account is None:
        return ["no such user: create the brain's own user (`useradd --system neuroclaw`)"]
    found: list[str] = []
    if account.uid == 0:
        found.append(f"{account.name} is root")
    for name in DEVICE_GROUPS:
        if name in account.groups:
            found.append(f"{account.name} is in group {name}: it can drive devices")
    for pattern in DEVICE_GLOBS:
        for device in sorted(system.dev.glob(pattern)):
            try:
                if _opens_device(account, device):
                    found.append(f"{account.name} can open {device}")
            except OSError:
                continue
    if keys.is_dir():
        if _reads(account, keys):
            found.append(f"{account.name} can read the key directory {keys}")
        # Only what the brain can get to: every directory from `keys` down must let it in
        # (the public certificates are 0644 by design, behind a 0700 directory).
        for path in sorted(keys.rglob("*")):
            try:
                parents = [keys, *list(path.relative_to(keys).parents)[-2::-1]]
                reachable = all(_enters(account, keys / d) for d in parents)
                if reachable and (path.is_file() or path.is_dir()) and _reads(account, path):
                    found.append(f"{account.name} can read {path}")
            except OSError:
                continue
    else:
        found.append(f"no key directory at {keys}")
    options = _proc_options(system.proc_mounts) or []
    if not any(o in ("hidepid=2", "hidepid=invisible") for o in options):
        found.append(
            "/proc is not mounted with hidepid=2: the brain can read the box's command line and "
            "environment (mount -o remount,hidepid=2 /proc, and in /etc/fstab)"
        )
    for option in options:
        if option.startswith("gid=") and option[4:].isdigit():
            gid = int(option[4:])
            if gid == account.gid or gid in account.groups.values():
                found.append(
                    f"{account.name} is in /proc's exempt group (gid={gid}): it sees every "
                    "process despite hidepid"
                )
    return found
