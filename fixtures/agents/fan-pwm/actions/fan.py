"""
The fan-pwm sample's two physical actions. Only `c.do()` runs them, after their gate.

`fan_run` takes all three PWM parameters and gives none a default: the gate limits each one
(`arguments`) before it looks at anything else, and a call that leaves one out is REJECTED.
"""

from neuroedge import action, digital


@action(name="fan_run", requires="digital.out:fan", gate="fan_run")
def fan_run(duty: float, frequency_hz: int, duration_ms: int) -> None:
    """Run the fan at a duty (0..1) and frequency for a time."""
    digital.out("fan").pwm(frequency_hz=frequency_hz, duty=duty, ms=duration_ms)


@action(name="fan_stop", requires="digital.out:fan", gate="fan_stop")
def fan_stop() -> None:
    """Stop the fan."""
    digital.out("fan").off()
