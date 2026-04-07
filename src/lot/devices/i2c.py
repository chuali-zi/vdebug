from __future__ import annotations

from typing import Any

from lot.contracts.errors import DomainError
from lot.devices.base import DeviceCommandResult, DeviceDescriptor, DevicePlugin


class I2CDevicePlugin(DevicePlugin):
    descriptor = DeviceDescriptor(
        device_type="i2c_bus",
        bus="i2c",
        supported_actions=["transact"],
        fault_kinds=["i2c_sda_stuck_low", "repeated_nack"],
        notes=["Represents a simplified I2C bus with addressable devices and fault injection."],
    )

    def default_state(self) -> dict[str, Any]:
        devices: dict[str, dict[str, Any]] = {}
        for item in self.config.get("devices", []):
            addr = int(item["addr_7bit"])
            devices[self._device_key(addr)] = {
                "type": item["type"],
                "addr_7bit": addr,
                "last_write": [],
                "read_count": 0,
            }

        return {
            "pullup_ohm": self.config.get("pullup_ohm"),
            "fault_sda_stuck_low": False,
            "fault_repeated_nack_remaining": 0,
            "transaction_count": 0,
            "devices": devices,
        }

    def handle(self, action: str, params: dict[str, Any], now_ns: int) -> DeviceCommandResult:
        if action != "transact":
            return super().handle(action, params, now_ns)

        addr = self._parse_address(params.get("addr_7bit"))
        write = self._coerce_bytes(params.get("write", []), field_name="write")
        read_len = self._parse_read_len(params.get("read_len", 0))

        if self.state["fault_sda_stuck_low"]:
            return DeviceCommandResult(
                result={
                    "accepted": False,
                    "bus": self.instance_id,
                    "addr_7bit": addr,
                    "reason": "bus_stuck_low",
                },
                events=[
                    self._event(
                        "I2C_BUS_STUCK_LOW",
                        severity="warn",
                        payload={"bus": self.instance_id, "addr_7bit": addr},
                    )
                ],
            )

        device_key = self._device_key(addr)
        if self.state["fault_repeated_nack_remaining"] > 0 or device_key not in self.state["devices"]:
            if self.state["fault_repeated_nack_remaining"] > 0:
                self.state["fault_repeated_nack_remaining"] -= 1
            return DeviceCommandResult(
                result={
                    "accepted": False,
                    "bus": self.instance_id,
                    "addr_7bit": addr,
                    "acknowledged": False,
                },
                events=[
                    self._event(
                        "I2C_NACK",
                        severity="warn",
                        payload={"bus": self.instance_id, "addr_7bit": addr},
                    )
                ],
            )

        self.state["transaction_count"] += 1
        device_state = self.state["devices"][device_key]
        device_state["last_write"] = list(write)
        read_data = [((addr + index + len(write)) & 0xFF) for index in range(read_len)]
        device_state["read_count"] += len(read_data)

        return DeviceCommandResult(
            result={
                "accepted": True,
                "bus": self.instance_id,
                "addr_7bit": addr,
                "acknowledged": True,
                "read": read_data,
            },
            events=[
                self._event(
                    "I2C_TRANSACTION",
                    payload={
                        "bus": self.instance_id,
                        "addr_7bit": addr,
                        "write": write,
                        "read": read_data,
                    },
                )
            ],
        )

    def inject_fault(
        self,
        fault_kind: str,
        payload: dict[str, Any],
        now_ns: int,
    ) -> DeviceCommandResult:
        if fault_kind == "i2c_sda_stuck_low":
            enabled = bool(payload.get("enabled", True))
            self.state["fault_sda_stuck_low"] = enabled
            return DeviceCommandResult(
                result={
                    "fault_kind": fault_kind,
                    "bus": self.instance_id,
                    "enabled": enabled,
                },
                events=[
                    self._event(
                        "I2C_FAULT_INJECTED",
                        severity="warn",
                        payload={
                            "bus": self.instance_id,
                            "fault_kind": fault_kind,
                            "enabled": enabled,
                        },
                    )
                ],
            )

        if fault_kind == "repeated_nack":
            count = payload.get("count", 1)
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise DomainError(
                    error_code="INVALID_FAULT_PAYLOAD",
                    message="repeated_nack requires a non-negative integer count.",
                    details={"fault_kind": fault_kind, "count": count},
                )
            self.state["fault_repeated_nack_remaining"] = count
            return DeviceCommandResult(
                result={
                    "fault_kind": fault_kind,
                    "bus": self.instance_id,
                    "remaining": count,
                },
                events=[
                    self._event(
                        "I2C_FAULT_INJECTED",
                        severity="warn",
                        payload={
                            "bus": self.instance_id,
                            "fault_kind": fault_kind,
                            "remaining": count,
                        },
                    )
                ],
            )

        return super().inject_fault(fault_kind, payload, now_ns)

    def _parse_address(self, value: Any) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 0x7F:
            raise DomainError(
                error_code="INVALID_I2C_ADDRESS",
                message="I2C addr_7bit must be an integer in range 0..127.",
                details={"bus": self.instance_id, "addr_7bit": value},
            )
        return value

    def _parse_read_len(self, value: Any) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise DomainError(
                error_code="INVALID_I2C_READ_LENGTH",
                message="I2C read_len must be a non-negative integer.",
                details={"bus": self.instance_id, "read_len": value},
            )
        return value

    def _coerce_bytes(self, value: Any, *, field_name: str) -> list[int]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise DomainError(
                error_code="INVALID_I2C_PAYLOAD",
                message=f"I2C {field_name} must be a list of bytes.",
                details={"bus": self.instance_id, field_name: value},
            )

        output: list[int] = []
        for index, item in enumerate(value):
            if isinstance(item, bool) or not isinstance(item, int) or not 0 <= item <= 0xFF:
                raise DomainError(
                    error_code="INVALID_I2C_PAYLOAD",
                    message=f"I2C {field_name} must contain integers in range 0..255.",
                    details={"bus": self.instance_id, "index": index, "value": item},
                )
            output.append(item)
        return output

    def _device_key(self, addr_7bit: int) -> str:
        return f"0x{addr_7bit:02x}"
