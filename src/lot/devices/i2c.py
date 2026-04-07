from __future__ import annotations

from lot.devices.base import DeviceDescriptor, DevicePlugin


class I2CDevicePlugin(DevicePlugin):
    descriptor = DeviceDescriptor(
        device_type="TODO_I2C_DEVICE",
        bus="i2c",
        notes=["Replace with concrete address, transaction, NACK, and pull-up semantics."],
    )
