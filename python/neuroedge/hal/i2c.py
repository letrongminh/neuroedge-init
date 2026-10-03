"""
`i2c.read(bus, device, register)` — read a device on the board's I2C bus from inside an
`@action` body (RFC-0007 §3b).

    @action(name="report_current", requires="i2c:i2c1/ina219", gate="report")
    def report_current() -> None:
        raw = i2c.read("i2c1", "ina219", register=0x04, width=2)

There is no function that writes data: `read` is the whole API. The device is named as the
board declares it (`i2c1`, `ina219`), so an address outside the board's allow-list cannot
even be written down. `register` must be one the board lists in `readable_registers`; with
no register the call is a receive-byte, which any allow-listed device answers. A 16-bit
register is read with `width=2` and returned in wire order (first byte on the bus high).

Reading moves nothing, so it needs no verdict token — but it uses the HAL of the `c.do()`
that is running the action: the allow-list and the real bus on `linux`, the scripted value
on `sim`. A read that fails raises `PerceptionUnavailableError` (NE5001). Every read is
recorded as `i2c_read`, which replay feeds back (docs/spec/simulation_coverage.md).
"""

from __future__ import annotations

from ..errors import ActionContractViolation
from .digital import _active, _caller


def read(bus: str, device: str, register: int | None = None, *, width: int = 1) -> int:
    active = _active.get()
    where = _caller()
    if active is None:
        raise ActionContractViolation(
            where=f"{where} -> i2c.read({bus!r}, {device!r})",
            why="no HAL is active; I2C is read inside an @action run by c.do()",
            how="read the device in an @action body, or call hal.i2c_read() in a test",
        )
    return active.hal.i2c_read(
        bus, device, register, width=width, called_from=f"{where} ({active.action})"
    )
