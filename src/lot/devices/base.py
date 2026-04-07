from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class DeviceDescriptor:
    """Static registration metadata for a device plugin."""

    device_type: str
    bus: str
    notes: list[str] = field(default_factory=list)


class DevicePlugin:
    """Base class for future concrete device and bus plugins.

    The MVP scaffold keeps device semantics behind this abstraction so later
    agents can implement GPIO/UART/I2C behavior without coupling engine code to
    any specific device type.
    """

    descriptor: DeviceDescriptor

    def bootstrap(self) -> None:
        # TODO(devices): allocate plugin-local runtime state.
        return None
