"""The assistant's two physical actions. Only `c.do()` runs them, after their gate."""

from neuroedge import action
from neuroedge.hal import digital


@action(name="light_on", requires="digital.out:porch_light", gate="light_on")
def light_on() -> None:
    digital.out("porch_light").on()


@action(name="light_off", requires="digital.out:porch_light", gate="light_off")
def light_off() -> None:
    digital.out("porch_light").off()
