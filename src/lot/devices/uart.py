from __future__ import annotations

from lot.devices.base import DeviceDescriptor, DevicePlugin


class UARTDevicePlugin(DevicePlugin):
    descriptor = DeviceDescriptor(
        device_type="TODO_UART_DEVICE",
        bus="uart",
        notes=["Replace with concrete UART framing, baud, and error semantics."],
    )
