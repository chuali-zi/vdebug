from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from lot.artifacts.service import ArtifactsServiceStub
from lot.artifacts.store import ArtifactStoreConfig
from lot.contracts.models import ScenarioPlan, ScenarioResult
from lot.devices.registry import build_default_device_registry
from lot.diagnosis.service import DiagnosisServiceStub
from lot.engine.service import EngineServiceStub
from lot.scenario.parser import load_plan_from_source
from lot.scenario.runner import run_plan
from lot.session.models import RuntimeContext


@dataclass(slots=True)
class ScenarioServiceStub:
    """Scenario parsing and execution boundary."""

    engine_service: EngineServiceStub = field(
        default_factory=lambda: EngineServiceStub(device_registry=build_default_device_registry())
    )
    diagnosis_service: DiagnosisServiceStub = field(default_factory=DiagnosisServiceStub)
    artifacts_service: ArtifactsServiceStub = field(
        default_factory=lambda: ArtifactsServiceStub(
            config=ArtifactStoreConfig(root_dir=Path.cwd() / "runtime_artifacts")
        )
    )

    def load_plan(self, *, scenario_path: str | None, scenario_text: str | None) -> ScenarioPlan:
        return load_plan_from_source(scenario_path=scenario_path, scenario_text=scenario_text)

    def run_plan(self, runtime: RuntimeContext, plan: ScenarioPlan) -> ScenarioResult:
        return run_plan(
            runtime,
            plan,
            engine=self.engine_service,
            diagnosis=self.diagnosis_service,
            artifacts=self.artifacts_service,
        )
