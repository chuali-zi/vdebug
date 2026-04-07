from __future__ import annotations

from dataclasses import dataclass, field

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


def build_default_device_registry() -> DeviceRegistry:
    registry = DeviceRegistry()
    registry.register(GPIODevicePlugin)
    registry.register(UARTDevicePlugin)
    registry.register(I2CDevicePlugin)
    return registry
