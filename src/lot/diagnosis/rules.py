from __future__ import annotations


def builtin_rule_names() -> list[str]:
    """List of rule hooks reserved for future diagnosis work."""

    return [
        "gpio.direction_conflict",
        "uart.baud_mismatch",
        "i2c.bus_stuck_low",
    ]
