"""
A `SimHAL` driving remote actuators of the reference plugin (RFC-0018), on a hand clock — the
wiring `SimSession` and `Guard` use (`remote_setup` → `build_hal`), with nothing else around it.

`Rig.on()` / `Rig.off()` go through `hal.digital_out` with an `authorize` the test controls;
`Rig.conversation()` puts a real token ledger in front, for the tests about tokens.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from neuroedge.engine import EventLog
from neuroedge.hal.board import load_board_by_id
from neuroedge.plugins.actuators import remote_setup
from neuroedge.sim.hal_build import build_hal

from .hand_clock import HandClock

ENVELOPE = {
    "window_s": 3600,
    "max_on_ms_per_window": 1_800_000,
    "min_interval_ms": 1000,
    "max_continuous_ms": 10_000,
}


def declaration(
    plugin: str = "ref_l1",
    *,
    safe_off: str | None = None,
    reversible: bool | None = None,
    config: Mapping[str, Any] | None = None,
    envelope: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    level = safe_off or plugin.removeprefix("ref_").upper()
    table: dict[str, Any] = {
        "plugin": plugin,
        "safe_off": level,
        "envelope": dict(envelope or ENVELOPE),
    }
    if reversible is None:
        reversible = level in ("L0", "L1")
    table["reversible"] = reversible
    if config:
        table["config"] = dict(config)
    return table


class Allow:
    """An `authorize` that lets every command through and remembers who asked, in order."""

    def __init__(self, log: list[str] | None = None) -> None:
        self.calls: list[str] = []
        self.log = log

    def __call__(self, signature: Any, pin: str, called_from: str) -> None:
        self.calls.append(pin)
        if self.log is not None:
            self.log.append("authorize")


class Rig:
    """
    `target="linux"`: a `LinuxHAL` on the in-memory gpiod, `target_options` its options. The
    plugin's real transport is replaced by its double *by the test* (a linux deployment talks to
    the device); the HAL does not move the double's clock there, `advance()` does.
    """

    def __init__(
        self,
        actuators: Mapping[str, Mapping[str, Any]],
        *,
        target: str = "sim",
        target_options: Mapping[str, Any] | None = None,
        clock: HandClock | None = None,
        enable: tuple[str, ...] = ("neuroedge-ref-actuators",),
    ) -> None:
        self.target = target
        self.clock = clock or HandClock()
        self.events = EventLog(self.clock, target=target)
        self.board = load_board_by_id("sim-default" if target == "sim" else "linux-rpi5")
        document = {"plugins": {"enable": list(enable)}, "actuators": dict(actuators)}
        self.setup = remote_setup(
            document,
            where="rig",
            target=target,
            board=self.board,
            requires={"digital.out": {"pins": list(actuators)}},
        )
        self.setup.raise_problems("rig")
        self.doubles: dict[str, Any] = {}
        if target == "linux":
            self.doubles = {n: b.driver.probe() for n, b in self.setup.checked.bound.items()}
        self.hal = build_hal(
            target,
            self.board,
            self.events,
            dict(target_options or {}),
            remote=self.setup.checked.bound,
        )
        self.allow = Allow()
        self.hal.authorize = self.allow

    def double(self, name: str) -> Any:
        return self.doubles.get(name) or self.hal._remote[name].double

    def remote(self, name: str) -> Any:
        return self.hal._remote[name]

    def state(self, name: str) -> str:
        return self.hal.remote_state(name)

    def on(self, name: str, *, signature: Any = "token") -> Any:
        return self.hal.digital_out(name, "on", 0, signature=signature, called_from="test")

    def pulse(self, name: str, ms: int, *, signature: Any = "token") -> Any:
        return self.hal.digital_out(name, "pulse", ms, signature=signature, called_from="test")

    def off(self, name: str) -> Any:
        return self.hal.digital_out(name, "off", 0, called_from="test")

    def advance(self, ms: float) -> None:
        """Time passes and the HAL's timers run, as `run_due()` does on `sim`."""
        step = 50.0
        left = float(ms)
        while left > 0:
            moved = min(step, left)
            self.clock.advance(moved)
            left -= step
            for double in self.doubles.values():
                double.advance(int(moved))
            if self.target == "sim":
                self.hal.run_due()
            else:
                self.hal.settle_remote()

    def of_type(self, kind: str) -> list[dict[str, Any]]:
        return self.events.of_type(kind)

    def kinds(self, prefix: str = "remote_") -> list[str]:
        return [e["type"] for e in self.events.to_trace()["events"] if e["type"].startswith(prefix)]


def write_agent(
    root: Path,
    actuators: str,
    *,
    pins: tuple[str, ...] = ("garden_valve",),
    enable: tuple[str, ...] = ("neuroedge-ref-actuators",),
    body: str = 'digital.out("garden_valve").pulse(seconds=seconds)',
    extra_imports: str = "",
) -> Path:
    """
    An agent project on `sim-default` with one gated action that drives a remote actuator. The
    action is named after the folder (`water_<folder>`), so two agents of one test never share an
    @action name; "water the garden" calls it.
    """
    action = "water_" + "".join(c if c.isalnum() else "_" for c in root.name).lower()
    root.mkdir(parents=True, exist_ok=True)
    (root / "actions").mkdir(exist_ok=True)
    plugins = ", ".join(f'"{name}"' for name in enable)
    pin_list = ", ".join(f'"{pin}"' for pin in pins)
    (root / "agent.toml").write_text(
        f"""[agent]
name    = "remote-valve"
version = "0.1.0"

[requires]
"digital.out" = {{ pins = [{pin_list}] }}

[gates]
valve = "neuroedge://gates/home/light@1.0.0"

[targets]
supported = ["sim", "linux"]

[plugins]
enable = [{plugins}]

{actuators}

[sim.facts]
device_fault_free = true
quiet_hours_ok    = true
""",
        encoding="utf-8",
    )
    (root / "actions" / "valve.py").write_text(
        f'''"""The one action of the test agent: a gated command to a remote actuator."""
{extra_imports}
from neuroedge import action, digital


@action(name="{action}", requires="digital.out:{pins[0]}", gate="valve")
def water(seconds: int = 2) -> None:
    """Water the garden for a few seconds."""
    {body}
''',
        encoding="utf-8",
    )
    (root / "commands.toml").write_text(
        f"""[grammar]
version   = 1
threshold = 0.80

[[command]]
intent   = "water"
patterns = ["water the garden"]
tool     = "{action}"
""",
        encoding="utf-8",
    )
    return root / "agent.toml"


ACTUATOR_TOML = """[actuators.garden_valve]
plugin   = "{plugin}"
safe_off = "{safe_off}"
{reversible}
[actuators.garden_valve.envelope]
window_s             = 3600
max_on_ms_per_window = 1800000
min_interval_ms      = 1000
max_continuous_ms    = {max_continuous_ms}
"""


def actuator_toml(
    plugin: str = "ref_l2",
    safe_off: str = "L2",
    reversible: bool | None = None,
    max_continuous_ms: int = 10_000,
) -> str:
    return ACTUATOR_TOML.format(
        plugin=plugin,
        safe_off=safe_off,
        reversible="" if reversible is None else f"reversible = {str(reversible).lower()}",
        max_continuous_ms=max_continuous_ms,
    )
