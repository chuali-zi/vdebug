from __future__ import annotations

from typing import Any

from lot.contracts.errors import DomainError
from lot.devices.base import DeviceCommandResult, DeviceDescriptor, DevicePlugin


class UARTDevicePlugin(DevicePlugin):
    descriptor = DeviceDescriptor(
        device_type="uart_bus",
        bus="uart",
        supported_actions=["write", "read", "send", "receive"],
        fault_kinds=["uart_baud_mismatch"],
        notes=["Represents a UART bus with tx/rx buffers and baud mismatch faults."],
    )

    def default_state(self) -> dict[str, Any]:
        configured_baud = int(self.config.get("baud", 115200))
        return {
            "configured_baud": configured_baud,
            "actual_baud": configured_baud,
            "fault_baud_mismatch": False,
            "tx_buffer": [],
            "rx_buffer": [],
        }

    def handle(self, action: str, params: dict[str, Any], now_ns: int) -> DeviceCommandResult:
        if action in {"write", "send"}:
            data = self._coerce_bytes(params.get("data", []))
            if self.state["fault_baud_mismatch"]:
                return DeviceCommandResult(
                    result={
                        "accepted": False,
                        "bus": self.instance_id,
                        "written": 0,
                        "reason": "baud_mismatch",
                    },
                    events=[
                        self._event(
                            "UART_BAUD_MISMATCH",
                            severity="warn",
                            payload={
                                "bus": self.instance_id,
                                "configured_baud": self.state["configured_baud"],
                                "actual_baud": self.state["actual_baud"],
                            },
                        )
                    ],
                )

            self.state["tx_buffer"].extend(data)
            return DeviceCommandResult(
                result={"accepted": True, "bus": self.instance_id, "written": len(data)},
                events=[
                    self._event(
                        "UART_WRITE",
                        payload={"bus": self.instance_id, "bytes": data},
                    )
                ],
            )

        if action in {"read", "receive"}:
            size = self._parse_size(params.get("size"))
            data = self.state["rx_buffer"][:size]
            self.state["rx_buffer"] = self.state["rx_buffer"][size:]
            return DeviceCommandResult(
                result={"bus": self.instance_id, "data": data, "read": len(data)},
                events=[
                    self._event(
                        "UART_READ",
                        payload={"bus": self.instance_id, "bytes": data},
                    )
                ],
            )

        return super().handle(action, params, now_ns)

    def inject_fault(
        self,
        fault_kind: str,
        payload: dict[str, Any],
        now_ns: int,
    ) -> DeviceCommandResult:
        if fault_kind != "uart_baud_mismatch":
            return super().inject_fault(fault_kind, payload, now_ns)

        enabled = bool(payload.get("enabled", True))
        configured_baud = self.state["configured_baud"]
        actual_baud = int(payload.get("actual_baud", max(1, configured_baud // 2)))
        self.state["fault_baud_mismatch"] = enabled
        self.state["actual_baud"] = actual_baud if enabled else configured_baud

        return DeviceCommandResult(
            result={
                "fault_kind": fault_kind,
                "bus": self.instance_id,
                "enabled": enabled,
                "actual_baud": self.state["actual_baud"],
            },
            events=[
                self._event(
                    "UART_FAULT_INJECTED",
                    severity="warn",
                    payload={
                        "bus": self.instance_id,
                        "fault_kind": fault_kind,
                        "enabled": enabled,
                        "actual_baud": self.state["actual_baud"],
                    },
                )
            ],
        )

    def _parse_size(self, value: Any) -> int:
        if value is None:
            return len(self.state["rx_buffer"])
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise DomainError(
                error_code="INVALID_UART_READ_SIZE",
                message="UART read size must be a non-negative integer.",
                details={"bus": self.instance_id, "size": value},
            )
        return value

    def _coerce_bytes(self, value: Any) -> list[int]:
        if isinstance(value, (bytes, bytearray)):
            return list(value)
        if isinstance(value, str):
            return list(value.encode("utf-8"))
        if isinstance(value, list):
            output: list[int] = []
            for index, item in enumerate(value):
                if isinstance(item, bool) or not isinstance(item, int) or not 0 <= item <= 0xFF:
                    raise DomainError(
                        error_code="INVALID_UART_PAYLOAD",
                        message="UART data must contain integers in range 0..255.",
                        details={"bus": self.instance_id, "index": index, "value": item},
                    )
                output.append(item)
            return output
        raise DomainError(
            error_code="INVALID_UART_PAYLOAD",
            message="UART data must be bytes, string, or list[int].",
            details={"bus": self.instance_id, "value": value},
        )
