from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExplanationRule:
    fact_kind: str
    hypothesis_template: str
    base_confidence: float
    next_actions: tuple[str, ...]


_RULES: dict[str, ExplanationRule] = {
    "bus_stuck_low": ExplanationRule(
        fact_kind="bus_stuck_low",
        hypothesis_template="i2c bus_stuck_low detected on {bus}; the SDA line is likely being held low.",
        base_confidence=0.96,
        next_actions=(
            "Check the bus pull-up network and confirm the target device is not holding SDA low.",
            "Power-cycle or reset the device on the affected bus and retry the transaction.",
        ),
    ),
    "repeated_nack": ExplanationRule(
        fact_kind="repeated_nack",
        hypothesis_template="i2c repeated_nack detected on {bus} for address {addr}.",
        base_confidence=0.72,
        next_actions=(
            "Verify the target address and confirm the peripheral is powered and enabled.",
            "Check bus timing, reset sequencing, and whether the target requires register pointer setup before reads.",
        ),
    ),
    "gpio_direction_conflict": ExplanationRule(
        fact_kind="gpio_direction_conflict",
        hypothesis_template="gpio_direction_conflict detected on {pin}; software is driving a pin that is not configured as output.",
        base_confidence=0.94,
        next_actions=(
            "Update the board profile or firmware setup so the pin direction matches the intended write operation.",
            "Inspect pin mux and initialization order before the GPIO write is attempted.",
        ),
    ),
    "uart_baud_mismatch": ExplanationRule(
        fact_kind="uart_baud_mismatch",
        hypothesis_template="uart_baud_mismatch detected on {bus}; the configured and observed baud rates diverge.",
        base_confidence=0.93,
        next_actions=(
            "Align the UART baud configuration on both ends of the link.",
            "Inspect clock source selection and divider settings for the affected UART peripheral.",
        ),
    ),
}


def builtin_rule_names() -> list[str]:
    """Stable built-in rule names exposed by the diagnosis module."""

    return sorted(_RULES)


def get_rule(fact_kind: str) -> ExplanationRule | None:
    return _RULES.get(fact_kind)
