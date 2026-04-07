from __future__ import annotations

from lot.devices.base import DeviceDescriptor, DevicePlugin


class GPIODevicePlugin(DevicePlugin):
    descriptor = DeviceDescriptor(
        device_type="TODO_GPIO_DEVICE",
        bus="gpio",
        notes=["Replace with concrete GPIO semantics and validation rules."],
    )
