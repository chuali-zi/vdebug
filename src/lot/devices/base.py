from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from lot.contracts.errors import DomainError


@dataclass(slots=True)
class DeviceDescriptor:
    """Static registration metadata for a device plugin."""

    device_type: str
    bus: str
    supported_actions: list[str] = field(default_factory=list)
    fault_kinds: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DeviceEvent:
    """Internal device event before it is normalized into a SimEvent."""

    source_suffix: str
    type: str
    severity: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DeviceCommandResult:
    """Stable plugin result shape owned by the devices module."""

    result: dict[str, Any] = field(default_factory=dict)
    events: list[DeviceEvent] = field(default_factory=list)
    state_delta: dict[str, Any] = field(default_factory=dict)


class DevicePlugin:
    """Base class shared by GPIO/UART/I2C runtime plugins."""

    descriptor: DeviceDescriptor

    def __init__(
        self,
        instance_id: str,
        config: dict[str, Any],
        initial_state: dict[str, Any] | None = None,
    ) -> None:
        self.instance_id = instance_id
        self.config = dict(config)
        self.state = self.default_state()
        if initial_state:
            self.state.update(initial_state)

    def default_state(self) -> dict[str, Any]:
        return {}

    def handle(self, action: str, params: dict[str, Any], now_ns: int) -> DeviceCommandResult:
        raise DomainError(
            error_code="DEVICE_ACTION_NOT_SUPPORTED",
            message=f"Action {action!r} is not supported for {self.instance_id}.",
            explain="The requested bus action is outside the MVP device plugin contract.",
            details={
                "instance_id": self.instance_id,
                "supported_actions": self.descriptor.supported_actions,
            },
        )

    def inject_fault(
        self,
        fault_kind: str,
        payload: dict[str, Any],
        now_ns: int,
    ) -> DeviceCommandResult:
        raise DomainError(
            error_code="DEVICE_FAULT_NOT_SUPPORTED",
            message=f"Fault {fault_kind!r} is not supported for {self.instance_id}.",
            explain="The requested fault kind is outside the MVP device plugin contract.",
            details={
                "instance_id": self.instance_id,
                "fault_kinds": self.descriptor.fault_kinds,
            },
        )

    def snapshot(self) -> dict[str, Any]:
        return dict(self.state)

    def _event(
        self,
        event_type: str,
        *,
        severity: str = "info",
        payload: dict[str, Any] | None = None,
    ) -> DeviceEvent:
        return DeviceEvent(
            source_suffix=f"{self.descriptor.bus}.{self.instance_id}",
            type=event_type,
            severity=severity,
            payload=payload or {},
        )
