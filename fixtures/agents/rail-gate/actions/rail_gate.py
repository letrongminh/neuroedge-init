"""Hai action của agent rail-gate. Chỉ `c.do()` chạy chúng, sau gate của mỗi action."""

from neuroedge import action, digital
from neuroedge.hal import display, i2c

# ina219: thanh ghi 0x02 là điện áp bus; bit 15..3 đếm theo bước 4 mV, ba bit thấp là cờ.
BUS_VOLTAGE = 0x02


@action(name="rail_open_gate", requires="digital.out:gate_relay", gate="rail_open_gate")
def rail_open_gate() -> None:
    """Pulse the gate motor relay, with the gate at its closed stop and the rail healthy."""
    digital.out("gate_relay").pulse(seconds=20)


@action(
    name="rail_report",
    requires=["i2c:i2c1/ina219", "display"],
    gate="rail_report",
)
def rail_report() -> None:
    """Show the battery rail voltage the power monitor measures (an I2C read, never a gate fact)."""
    raw = i2c.read("i2c1", "ina219", register=BUS_VOLTAGE, width=2)
    display.show(f"Nguồn: {(raw >> 3) * 4} mV")
