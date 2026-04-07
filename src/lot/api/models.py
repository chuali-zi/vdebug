from __future__ import annotations

from typing import Any

from pydantic import Field

from lot.contracts.models import Capabilities, ErrorPayload, StrictModel
from lot.devices.registry import DeviceRegistry


class CreateSessionRequest(StrictModel):
    board_profile: str
    seed: int = 0
    mode: str = "device_sim"


class StepSessionRequest(StrictModel):
    delta_ms: int = Field(..., gt=0)


class ExecuteIoRequest(StrictModel):
    params: dict[str, Any] = Field(default_factory=dict)


class RunScenarioRequest(StrictModel):
    scenario_path: str | None = None
    scenario_text: str | None = None


class SuccessEnvelope(StrictModel):
    ok: bool = True
    request_id: str
    data: dict[str, Any]


class ErrorEnvelope(StrictModel):
    ok: bool = False
    request_id: str
    error: ErrorPayload


class CapabilitiesProvider:
    """Static capability provider owned by the API module in the MVP."""

    def __init__(self, capabilities: Capabilities) -> None:
        self._capabilities = capabilities

    @classmethod
    def from_registry(cls, registry: DeviceRegistry) -> "CapabilitiesProvider":
        return cls(
            Capabilities(
                modes=["device_sim"],
                buses=registry.supported_buses(),
                device_types=registry.registered_types(),
            )
        )

    def get_capabilities(self) -> Capabilities:
        return self._capabilities
