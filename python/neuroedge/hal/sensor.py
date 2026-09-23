"""
`sensor.read(name)` — read a sensor from inside an `@action` body.

    @action(name="report_temperature", requires="sensor.read:temperature", gate="report")
    def report_temperature() -> None:
        celsius = sensor.read("temperature")

Reading moves nothing, so it needs no verdict token — but it uses the HAL of the
`c.do()` that is running the action, so the same action code reads the scripted
value on `sim`, sysfs on `linux` and the I2C driver on `esp32s3`. Every read is
recorded as `sensor_read`, which replay feeds back (docs/spec/simulation_coverage.md).
"""

from __future__ import annotations

from typing import Any

from ..errors import ActionContractViolation
from .digital import _active, _caller


def read(name: str) -> Any:
    active = _active.get()
    where = _caller()
    if active is None:
        raise ActionContractViolation(
            where=f"{where} -> sensor.read({name!r})",
            why="no HAL is active; sensors are read inside an @action run by c.do()",
            how="read the sensor in an @action body, or call hal.sensor_read() in a test",
        )
    return active.hal.sensor_read(name, called_from=f"{where} ({active.action})")
