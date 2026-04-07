from __future__ import annotations

from pathlib import Path
from typing import Protocol

from lot.contracts.models import (
    BoardProfile,
    Capabilities,
    DiagnosisBatch,
    IoResult,
    ScenarioPlan,
    ScenarioResult,
    SessionRecord,
    StateSnapshot,
    StepResult,
)
from lot.session.models import RuntimeContext


class SessionServiceProtocol(Protocol):
    def create_session(self, board_profile: BoardProfile, seed: int, mode: str) -> SessionRecord: ...

    def get_session(self, session_id: str) -> SessionRecord: ...

    def get_runtime(self, session_id: str) -> RuntimeContext: ...

    def save_runtime(self, runtime: RuntimeContext) -> None: ...


class BoardServiceProtocol(Protocol):
    def load_profile(self, profile_ref: str | Path) -> BoardProfile: ...


class EngineServiceProtocol(Protocol):
    def step(self, runtime: RuntimeContext, delta_ms: int) -> StepResult: ...

    def execute_io(self, runtime: RuntimeContext, bus_action: str, payload: dict[str, object]) -> IoResult: ...


class DiagnosisServiceProtocol(Protocol):
    def analyze(self, runtime: RuntimeContext, events: list) -> DiagnosisBatch: ...


class ScenarioServiceProtocol(Protocol):
    def load_plan(self, *, scenario_path: str | None, scenario_text: str | None) -> ScenarioPlan: ...

    def run_plan(self, runtime: RuntimeContext, plan: ScenarioPlan) -> ScenarioResult: ...


class ArtifactsServiceProtocol(Protocol):
    def append_runtime_data(self, runtime: RuntimeContext, *, step_events: list, diagnosis: DiagnosisBatch) -> None: ...

    def build_state_view(self, session: SessionRecord, runtime: RuntimeContext) -> StateSnapshot: ...

    def export_bundle(self, session: SessionRecord, runtime: RuntimeContext) -> dict[str, str]: ...


class CapabilitiesProviderProtocol(Protocol):
    def get_capabilities(self) -> Capabilities: ...
