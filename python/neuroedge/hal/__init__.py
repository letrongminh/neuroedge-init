"""
Hardware Abstraction Layer (HAL) - L1.
5 Immutable Primitives: audio.in, audio.out, digital.out, sensor.read, display.
"""
from typing import Dict, Any, List

class PinAssertion:
    def __init__(self, pin_name: str, pulsed: bool = False, duration_ms: int = 0):
        self.pin_name = pin_name
        self.pulsed = pulsed
        self.duration_ms = duration_ms

    def never_pulsed(self) -> bool:
        return not self.pulsed

    def pulsed_once(self, duration_ms: int = 0) -> bool:
        if duration_ms > 0:
            return self.pulsed and self.duration_ms == duration_ms
        return self.pulsed

class HardwareAbstractionLayer:
    """
    Standard interface across sim, linux, and esp32s3.
    """
    def __init__(self, target: str = "sim"):
        self.target = target
        self.pins: Dict[str, PinAssertion] = {}

    def digital_out(self, pin: str, operation: str, duration_ms: int = 0, signature: str = "") -> None:
        if not signature:
            raise PermissionError("ActionContractViolation: Actuator command lacks valid gate signature")
        self.pins[pin] = PinAssertion(pin, pulsed=(operation == "pulse"), duration_ms=duration_ms)
