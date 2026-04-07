from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field, model_validator

from lot.contracts.models import Capabilities, ErrorPayload, StrictModel
from lot.devices.registry import DeviceRegistry


class CreateSessionRequest(StrictModel):
    board_profile: Annotated[str, Field(min_length=1)]
    seed: Annotated[int, Field(ge=0)] = 0
    mode: Annotated[str, Field(min_length=1)] = "device_sim"


class StepSessionRequest(StrictModel):
    delta_ms: int = Field(..., gt=0)


class ExecuteIoRequest(StrictModel):
    params: dict[str, Any] = Field(default_factory=dict)


class RunScenarioRequest(StrictModel):
    scenario_path: str | None = None
    scenario_text: str | None = None

    @model_validator(mode="after")
    def validate_source(self) -> "RunScenarioRequest":
        has_path = bool(self.scenario_path)
        has_text = bool(self.scenario_text)
        if has_path == has_text:
            raise ValueError("Provide exactly one of scenario_path or scenario_text.")
        return self


class ApiCommand(StrictModel):
    request_id: str
    session_id: str | None = None
    kind: str
    params: dict[str, Any] = Field(default_factory=dict)


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
