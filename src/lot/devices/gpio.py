from __future__ import annotations

from typing import Any

from lot.contracts.errors import DomainError
from lot.devices.base import DeviceCommandResult, DeviceDescriptor, DevicePlugin


class GPIODevicePlugin(DevicePlugin):
    descriptor = DeviceDescriptor(
        device_type="gpio_pin",
        bus="gpio",
        supported_actions=["get", "set", "read", "write"],
        fault_kinds=["gpio_direction_conflict"],
        notes=["Represents a single GPIO pin with direction and pull semantics."],
    )

    def default_state(self) -> dict[str, Any]:
        pull = str(self.config.get("pull", "none")).lower()
        value = True if pull == "up" else False
        return {
            "direction": str(self.config.get("direction", "input")).lower(),
            "pull": pull,
            "value": value,
            "fault_direction_conflict": False,
        }

    def handle(self, action: str, params: dict[str, Any], now_ns: int) -> DeviceCommandResult:
        if action in {"get", "read"}:
            return DeviceCommandResult(
                result={
                    "pin": self.instance_id,
                    "value": self.state["value"],
                    "direction": self.state["direction"],
                    "pull": self.state["pull"],
                },
                events=[
                    self._event(
                        "GPIO_READ",
                        payload={"pin": self.instance_id, "value": self.state["value"]},
                    )
                ],
            )

        if action not in {"set", "write"}:
            return super().handle(action, params, now_ns)

        value = self._parse_bool(params.get("value"))
        if value is None:
            raise DomainError(
                error_code="INVALID_GPIO_VALUE",
                message=f"GPIO value for {self.instance_id} must be true/false.",
                explain="GPIO writes in the MVP only accept boolean values.",
                details={"pin": self.instance_id, "value": params.get("value")},
            )

        direction = self.state["direction"]
        if direction not in {"output", "inout"} or self.state["fault_direction_conflict"]:
            return DeviceCommandResult(
                result={
                    "accepted": False,
                    "pin": self.instance_id,
                    "value": value,
                    "reason": "direction_conflict",
                },
                events=[
                    self._event(
                        "GPIO_DIRECTION_CONFLICT",
                        severity="warn",
                        payload={
                            "pin": self.instance_id,
                            "direction": direction,
                            "requested_value": value,
                        },
                    )
                ],
            )

        self.state["value"] = value
        return DeviceCommandResult(
            result={"accepted": True, "pin": self.instance_id, "value": value},
            events=[
                self._event(
                    "GPIO_WRITE",
                    payload={"pin": self.instance_id, "value": value},
                )
            ],
        )

    def inject_fault(
        self,
        fault_kind: str,
        payload: dict[str, Any],
        now_ns: int,
    ) -> DeviceCommandResult:
        if fault_kind != "gpio_direction_conflict":
            return super().inject_fault(fault_kind, payload, now_ns)

        enabled = payload.get("enabled", True)
        parsed = self._parse_bool(enabled)
        if parsed is None:
            raise DomainError(
                error_code="INVALID_FAULT_PAYLOAD",
                message="gpio_direction_conflict requires an optional boolean enabled flag.",
                details={"fault_kind": fault_kind, "enabled": enabled},
            )

        self.state["fault_direction_conflict"] = parsed
        return DeviceCommandResult(
            result={
                "fault_kind": fault_kind,
                "pin": self.instance_id,
                "enabled": parsed,
            },
            events=[
                self._event(
                    "GPIO_FAULT_INJECTED",
                    severity="warn",
                    payload={
                        "pin": self.instance_id,
                        "fault_kind": fault_kind,
                        "enabled": parsed,
                    },
                )
            ],
        )

    def _parse_bool(self, value: Any) -> bool | None:
        if isinstance(value, bool):
            return value
        if isinstance(value, int) and value in {0, 1}:
            return bool(value)
        return None
