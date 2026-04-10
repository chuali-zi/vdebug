from __future__ import annotations

from dataclasses import dataclass

from lot.contracts.models import ScenarioPlan, ScenarioResult, SessionRecord
from lot.contracts.protocols import ArtifactsServiceProtocol, DiagnosisServiceProtocol, EngineServiceProtocol
from lot.scenario.parser import load_plan_from_source
from lot.scenario.runner import run_plan
from lot.session.models import RuntimeContext


@dataclass(slots=True)
class ScenarioServiceStub:
    """Scenario parsing and execution boundary."""

    engine_service: EngineServiceProtocol
    diagnosis_service: DiagnosisServiceProtocol
    artifacts_service: ArtifactsServiceProtocol

    def load_plan(self, *, scenario_path: str | None, scenario_text: str | None) -> ScenarioPlan:
        return load_plan_from_source(scenario_path=scenario_path, scenario_text=scenario_text)

    def run_plan(
        self,
        runtime: RuntimeContext,
        plan: ScenarioPlan,
        session: SessionRecord | None = None,
    ) -> ScenarioResult:
        runtime.scenario_source = plan.source
        runtime.scenario_source_text = plan.source_text
        return run_plan(
            runtime,
            plan,
            engine=self.engine_service,
            diagnosis=self.diagnosis_service,
            artifacts=self.artifacts_service,
            session=session,
        )
