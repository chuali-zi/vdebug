from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from lot.contracts.errors import DomainError
from lot.contracts.models import BoardProfile, SimEvent
from lot.devices.base import DevicePlugin
from lot.devices.gpio import GPIODevicePlugin
from lot.devices.i2c import I2CDevicePlugin
from lot.devices.uart import UARTDevicePlugin


@dataclass(slots=True)
class DeviceRegistry:
    """Registry owned by the devices module."""

    plugins: list[type[DevicePlugin]] = field(default_factory=list)

    def register(self, plugin: type[DevicePlugin]) -> None:
        self.plugins.append(plugin)

    def supported_buses(self) -> list[str]:
        return sorted({plugin.descriptor.bus for plugin in self.plugins})

    def registered_types(self) -> list[str]:
        return sorted({plugin.descriptor.device_type for plugin in self.plugins})

    def plugin_for_bus(self, bus: str) -> type[DevicePlugin]:
        for plugin in self.plugins:
            if plugin.descriptor.bus == bus:
                return plugin
        raise DomainError(
            error_code="DEVICE_BUS_NOT_SUPPORTED",
            message=f"Unsupported device bus: {bus}",
            explain="The devices runtime only supports GPIO, UART, and I2C in the MVP.",
            details={"supported_buses": self.supported_buses()},
        )


@dataclass(slots=True)
class DeviceRuntime:
    """Serializable devices runtime bound to one session runtime container."""

    registry: DeviceRegistry
    session_id: str
    storage: dict[str, Any]

    def __post_init__(self) -> None:
        self.storage.setdefault("devices", {})
        self.storage.setdefault("state", {})

    def register_from_board(self, board_profile: BoardProfile | dict[str, Any]) -> None:
        if isinstance(board_profile, BoardProfile):
            gpio_items = board_profile.gpio
            bus_items = board_profile.buses
        else:
            gpio_items = dict(board_profile.get("gpio", {}))
            bus_items = dict(board_profile.get("buses", {}))

        devices: dict[str, dict[str, Any]] = {}
        next_state: dict[str, dict[str, Any]] = {}

        for pin_name, pin_config in sorted(gpio_items.items()):
            plugin_cls = self.registry.plugin_for_bus("gpio")
            config = {"pin": pin_name, **dict(pin_config)}
            devices[pin_name] = self._device_entry(pin_name, plugin_cls, config)
            next_state[pin_name] = plugin_cls(
                pin_name,
                config,
                self.storage["state"].get(pin_name),
            ).snapshot()

        for bus_name, bus_config in sorted(bus_items.items()):
            bus_kind = str(bus_config.get("kind", "")).lower()
            plugin_cls = self.registry.plugin_for_bus(bus_kind)
            config = {"bus": bus_name, **dict(bus_config)}
            devices[bus_name] = self._device_entry(bus_name, plugin_cls, config)
            next_state[bus_name] = plugin_cls(
                bus_name,
                config,
                self.storage["state"].get(bus_name),
            ).snapshot()

        self.storage["devices"] = devices
        self.storage["state"] = next_state

    def execute(self, action: str, payload: dict[str, Any], now_ns: int) -> dict[str, Any]:
        bus, verb = self._split_action(action)
        instance_id, plugin = self._resolve_plugin(bus, payload)
        outcome = plugin.handle(verb, payload, now_ns)
        return self._commit(instance_id, plugin, outcome, now_ns)

    def inject_fault(
        self,
        fault_kind: str,
        payload: dict[str, Any],
        now_ns: int,
    ) -> dict[str, Any]:
        bus = self._bus_from_fault_kind(fault_kind)
        instance_id, plugin = self._resolve_plugin(bus, payload)
        outcome = plugin.inject_fault(fault_kind, payload, now_ns)
        return self._commit(instance_id, plugin, outcome, now_ns)

    def snapshot(self) -> dict[str, Any]:
        return {
            "devices": dict(self.storage["devices"]),
            "state": dict(self.storage["state"]),
        }

    def _resolve_plugin(self, bus: str, payload: dict[str, Any]) -> tuple[str, DevicePlugin]:
        if bus == "gpio":
            instance_id = payload.get("pin")
            field_name = "pin"
        elif bus == "uart":
            instance_id = payload.get("bus", payload.get("port"))
            field_name = "bus"
        else:
            instance_id = payload.get("bus")
            field_name = "bus"

        if not isinstance(instance_id, str) or not instance_id.strip():
            raise DomainError(
                error_code="DEVICE_TARGET_REQUIRED",
                message=f"Payload for {bus} must include {field_name}.",
                explain="The devices runtime needs a concrete pin or bus instance to route the action.",
                details={"bus": bus, "payload": payload},
            )

        normalized_id = instance_id.strip()
        device_entry = self.storage["devices"].get(normalized_id)
        if device_entry is None:
            device_entry = self._auto_register_device(bus, normalized_id)
        if device_entry["bus"] != bus:
            raise DomainError(
                error_code="DEVICE_TARGET_NOT_FOUND",
                message=f"Unknown {bus} target: {normalized_id}",
                explain="The requested device target is not registered from the current board profile.",
                details={"target": normalized_id, "bus": bus},
            )

        plugin_cls = self.registry.plugin_for_bus(bus)
        plugin = plugin_cls(
            normalized_id,
            device_entry["config"],
            self.storage["state"].get(normalized_id),
        )
        return normalized_id, plugin

    def _commit(
        self,
        instance_id: str,
        plugin: DevicePlugin,
        outcome: Any,
        now_ns: int,
    ) -> dict[str, Any]:
        snapshot = plugin.snapshot()
        self.storage["state"][instance_id] = snapshot
        events = [
            SimEvent(
                session_id=self.session_id,
                t_virtual_ns=now_ns,
                source=f"devices.{event.source_suffix}",
                type=event.type,
                severity=event.severity,
                payload=event.payload,
            )
            for event in outcome.events
        ]
        return {
            "result": outcome.result,
            "events": events,
            "state_delta": {instance_id: snapshot},
        }

    def _device_entry(
        self,
        instance_id: str,
        plugin_cls: type[DevicePlugin],
        config: dict[str, Any],
    ) -> dict[str, Any]:
        descriptor = plugin_cls.descriptor
        return {
            "instance_id": instance_id,
            "bus": descriptor.bus,
            "device_type": descriptor.device_type,
            "supported_actions": list(descriptor.supported_actions),
            "fault_kinds": list(descriptor.fault_kinds),
            "config": config,
        }

    def _split_action(self, action: str) -> tuple[str, str]:
        if ":" not in action:
            raise DomainError(
                error_code="INVALID_BUS_ACTION",
                message=f"Invalid device action: {action!r}",
                explain="Actions must use the stable '<bus>:<action>' format.",
            )
        bus, verb = action.split(":", 1)
        if not bus or not verb:
            raise DomainError(
                error_code="INVALID_BUS_ACTION",
                message=f"Invalid device action: {action!r}",
                explain="Actions must use the stable '<bus>:<action>' format.",
            )
        return bus, verb

    def _bus_from_fault_kind(self, fault_kind: str) -> str:
        if fault_kind.startswith("gpio_"):
            return "gpio"
        if fault_kind.startswith("uart_"):
            return "uart"
        if fault_kind.startswith("i2c_") or fault_kind == "repeated_nack":
            return "i2c"
        raise DomainError(
            error_code="DEVICE_FAULT_NOT_SUPPORTED",
            message=f"Unsupported fault kind: {fault_kind}",
            explain="The devices runtime only supports the MVP fault injection set.",
        )

    def _auto_register_device(self, bus: str, instance_id: str) -> dict[str, Any]:
        plugin_cls = self.registry.plugin_for_bus(bus)
        if bus == "gpio":
            config = {"pin": instance_id, "direction": "inout", "pull": "none"}
        elif bus == "uart":
            config = {"bus": instance_id, "baud": 115200}
        elif bus == "i2c":
            config = {"bus": instance_id, "pullup_ohm": None, "devices": []}
        else:
            raise DomainError(
                error_code="DEVICE_BUS_NOT_SUPPORTED",
                message=f"Unsupported device bus: {bus}",
                details={"instance_id": instance_id},
            )

        entry = self._device_entry(instance_id, plugin_cls, config)
        self.storage["devices"][instance_id] = entry
        self.storage["state"][instance_id] = plugin_cls(instance_id, config).snapshot()
        return entry


def build_default_device_registry() -> DeviceRegistry:
    registry = DeviceRegistry()
    registry.register(GPIODevicePlugin)
    registry.register(UARTDevicePlugin)
    registry.register(I2CDevicePlugin)
    return registry
