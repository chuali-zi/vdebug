from __future__ import annotations

from typing import Any

from lot.contracts.models import DiagnosticFact, SimEvent
from lot.session.models import RuntimeContext


def extract_facts(
    session_id: str,
    events: list[SimEvent],
    runtime: RuntimeContext | None = None,
) -> list[DiagnosticFact]:
    """Convert normalized events into diagnostic facts.

    Facts are derived from public event payloads plus stable runtime context
    such as board profile metadata and the recent event window.
    """

    facts: list[DiagnosticFact] = []

    for event in events:
        if _is_i2c_bus_stuck_low(event):
            bus = _coerce_str(
                _nested(event.payload, "params", "bus"),
                _nested(event.payload, "result", "bus"),
                event.payload.get("bus"),
            ) or "i2c"
            facts.append(
                DiagnosticFact(
                    session_id=session_id,
                    kind="bus_stuck_low",
                    params={
                        "bus_type": "i2c",
                        "bus": bus,
                        "line": "sda",
                        "line_pin": _board_bus_pin(runtime, bus, "sda"),
                    },
                    source_events=[event.event_id],
                )
            )

        if _is_gpio_direction_conflict(event):
            pin = _coerce_str(
                _nested(event.payload, "params", "pin"),
                event.payload.get("pin"),
                _nested(event.payload, "result", "pin"),
            ) or "unknown"
            actual = _gpio_direction(runtime, pin)
            facts.append(
                DiagnosticFact(
                    session_id=session_id,
                    kind="gpio_direction_conflict",
                    params={
                        "bus_type": "gpio",
                        "pin": pin,
                        "expected": "output",
                        "actual": actual,
                    },
                    source_events=[event.event_id],
                )
            )

        if _is_uart_baud_mismatch(event):
            bus = _coerce_str(
                _nested(event.payload, "params", "bus"),
                _nested(event.payload, "params", "port"),
                _nested(event.payload, "result", "bus"),
                event.payload.get("bus"),
            ) or "uart0"
            expected, observed = _uart_baud_pair(runtime, bus)
            facts.append(
                DiagnosticFact(
                    session_id=session_id,
                    kind="uart_baud_mismatch",
                    params={
                        "bus_type": "uart",
                        "bus": bus,
                        "expected": expected,
                        "observed": observed,
                    },
                    source_events=[event.event_id],
                )
            )

    facts.extend(_extract_repeated_nack_facts(session_id, events, runtime))
    return facts


def _extract_repeated_nack_facts(
    session_id: str,
    events: list[SimEvent],
    runtime: RuntimeContext | None,
) -> list[DiagnosticFact]:
    current_keys: set[tuple[str, int]] = set()
    for event in events:
        key = _i2c_nack_key(event)
        if key is not None:
            current_keys.add(key)

    if not current_keys:
        return []

    recent_events = list(runtime.recent_events) if runtime is not None else []
    combined_events = recent_events + list(events)
    window = combined_events[-8:]
    facts: list[DiagnosticFact] = []

    for bus, addr_7bit in sorted(current_keys):
        matching_events = [event for event in window if _i2c_nack_key(event) == (bus, addr_7bit)]
        if len(matching_events) < 2:
            continue
        facts.append(
            DiagnosticFact(
                session_id=session_id,
                kind="repeated_nack",
                params={
                    "bus_type": "i2c",
                    "bus": bus,
                    "addr": f"0x{addr_7bit:02x}",
                    "addr_7bit": addr_7bit,
                    "count": len(matching_events),
                },
                source_events=[event.event_id for event in matching_events],
            )
        )

    return facts


def _i2c_nack_key(event: SimEvent) -> tuple[str, int] | None:
    if event.type == "I2C_NACK":
        bus = _coerce_str(event.payload.get("bus")) or "i2c"
        addr = _coerce_int(event.payload.get("addr_7bit"))
        if addr is None:
            return None
        return bus, addr

    if not event.type.endswith("I2C_TRANSACT"):
        return None

    result = _nested(event.payload, "result")
    if not isinstance(result, dict):
        return None

    accepted = result.get("accepted")
    acknowledged = result.get("acknowledged")
    if accepted is not False or acknowledged is not False:
        return None

    bus = _coerce_str(
        _nested(event.payload, "params", "bus"),
        result.get("bus"),
        event.payload.get("bus"),
    ) or "i2c"
    addr = _coerce_int(
        _nested(event.payload, "params", "addr_7bit"),
        result.get("addr_7bit"),
    )
    if addr is None:
        return None
    return bus, addr


def _is_i2c_bus_stuck_low(event: SimEvent) -> bool:
    if event.type == "I2C_BUS_STUCK_LOW":
        return True
    if not event.type.endswith("I2C_TRANSACT"):
        return False
    result = _nested(event.payload, "result")
    return isinstance(result, dict) and result.get("reason") == "bus_stuck_low"


def _is_gpio_direction_conflict(event: SimEvent) -> bool:
    if event.type == "GPIO_DIRECTION_CONFLICT":
        return True
    result = _nested(event.payload, "result")
    return isinstance(result, dict) and result.get("reason") == "direction_conflict"


def _is_uart_baud_mismatch(event: SimEvent) -> bool:
    if event.type == "UART_BAUD_MISMATCH":
        return True
    result = _nested(event.payload, "result")
    return isinstance(result, dict) and result.get("reason") == "baud_mismatch"


def _gpio_direction(runtime: RuntimeContext | None, pin: str) -> str:
    if runtime is None:
        return "unknown"
    state = runtime.device_state.get(pin)
    if isinstance(state, dict):
        direction = _coerce_str(state.get("direction"))
        if direction:
            return direction
    config = runtime.board_profile.gpio.get(pin)
    if isinstance(config, dict):
        direction = _coerce_str(config.get("direction"))
        if direction:
            return direction
    return "unknown"


def _uart_baud_pair(runtime: RuntimeContext | None, bus: str) -> tuple[int | None, int | None]:
    if runtime is None:
        return None, None
    state = runtime.device_state.get(bus)
    if isinstance(state, dict):
        expected = _coerce_int(state.get("configured_baud"))
        observed = _coerce_int(state.get("actual_baud"))
        if expected is not None or observed is not None:
            return expected, observed

    config = runtime.board_profile.buses.get(bus)
    if isinstance(config, dict):
        baud = _coerce_int(config.get("baud"))
        return baud, baud
    return None, None


def _board_bus_pin(runtime: RuntimeContext | None, bus: str, line: str) -> str | None:
    if runtime is None:
        return None
    bus_config = runtime.board_profile.buses.get(bus)
    if not isinstance(bus_config, dict):
        return None
    pins = bus_config.get("pins")
    if not isinstance(pins, dict):
        return None
    return _coerce_str(pins.get(line))


def _nested(mapping: dict[str, Any], *path: str) -> Any:
    current: Any = mapping
    for part in path:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _coerce_str(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _coerce_int(*values: Any) -> int | None:
    for value in values:
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            return value
    return None
