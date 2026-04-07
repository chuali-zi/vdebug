from __future__ import annotations

from dataclasses import dataclass

from lot.contracts.models import ScenarioPlan, ScenarioResult
from lot.scenario.parser import load_plan_from_source
from lot.scenario.runner import run_plan_placeholder
from lot.session.models import RuntimeContext


@dataclass(slots=True)
class ScenarioServiceStub:
    """Scenario parsing and execution boundary."""

    def load_plan(self, *, scenario_path: str | None, scenario_text: str | None) -> ScenarioPlan:
        return load_plan_from_source(scenario_path=scenario_path, scenario_text=scenario_text)

    def run_plan(self, runtime: RuntimeContext, plan: ScenarioPlan) -> ScenarioResult:
        return run_plan_placeholder(runtime, plan)
