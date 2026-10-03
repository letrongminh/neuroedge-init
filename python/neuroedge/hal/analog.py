"""
`analog.in(channel)` — one ADC channel, in the unit and range the board declares (TSK-I2a-04).

A channel is `{name, unit, min, max}` in `[capabilities.analog_in]` (RFC-0007 §3c). A
reading is a finite number in that unit inside `[min, max]`; anything else — a missing
device, a file that holds garbage, a value outside the range, a driver reporting another
unit — is a read failure, `PerceptionUnavailableError` (NE5001), never a value clamped
to the range or a default. The gate that needed the reading then BLOCKs
`criterion_unavailable` (RFC-0009 §3c). The same checks run on `sim` and on `linux`, so
the two targets refuse the same readings.

Every read — fact reads carry `use="fact"` — is recorded as `analog_in`:
`{channel, value, unit, use}`, or `{channel, error, use}` when it failed.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from ..errors import PerceptionUnavailableError


def analog_data(
    channel: str,
    value: Any = None,
    unit: str | None = None,
    use: str | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    """`analog_in` / `analog_set` event data, the same on every target (`reading_data`'s shape)."""
    if error is not None:
        failed: dict[str, Any] = {"channel": channel, "error": error}
        if use is not None:
            failed["use"] = use
        return failed
    data: dict[str, Any] = {"channel": channel, "value": value}
    if isinstance(value, float) and not math.isfinite(value):
        # JSON has no NaN or inf (`reading_data`): written as text, flagged.
        data["value"], data["non_finite"] = repr(value), True
    if unit is not None:
        data["unit"] = unit
    if use is not None:
        data["use"] = use
    return data


def unavailable(where: str, why: str, how: str) -> PerceptionUnavailableError:
    return PerceptionUnavailableError(where=where, why=why, how=how)


def check_reading(declared: Mapping[str, Any], value: Any, unit: str | None, where: str) -> float:
    """
    `value`, if it is a finite number in the channel's unit and `[min, max]`; else the
    refusal. Never clamps: a reading at the edge of the range is valid, one past it is
    a fault (a shorted or open input), not the nearest valid value.
    """
    name, low, high = declared["name"], declared["min"], declared["max"]
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        raise unavailable(
            where,
            f"{value!r} is not a finite number, so channel {name!r} has no reading",
            "check the ADC and its wiring; an analog input never reads as a default",
        )
    if unit is not None and unit != declared["unit"]:
        raise unavailable(
            where,
            f"the source reports {name!r} in {unit!r}, and the board declares {declared['unit']!r}",
            "map the channel to the source that measures it, or fix the declared unit",
        )
    if not low <= value <= high:
        raise unavailable(
            where,
            f"{value} {declared['unit']} is outside the range [{low}, {high}] of channel {name!r}",
            "an out-of-range reading is a fault (a shorted or open input), not a value to clamp",
        )
    return float(value)
