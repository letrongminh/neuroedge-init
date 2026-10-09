"""A driver built for an SDK this core does not have."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from neuroedge_ref_actuators import RefActuator

sdk_requires = (2, 0)


def make(config: Mapping[str, Any]) -> RefActuator:
    return RefActuator("L1", config)
