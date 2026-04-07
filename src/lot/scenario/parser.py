from __future__ import annotations

from pathlib import Path

import yaml

from lot.contracts.errors import DomainError
from lot.contracts.models import ScenarioAction, ScenarioAssertion, ScenarioPlan


def load_plan_from_source(*, scenario_path: str | None, scenario_text: str | None) -> ScenarioPlan:
    if not scenario_path and not scenario_text:
        raise DomainError(
            error_code="SCENARIO_SOURCE_REQUIRED",
            message="scenario_path or scenario_text is required",
            explain="The scenario module needs a YAML source to build a ScenarioPlan.",
        )

    if scenario_path:
        source = scenario_path
        raw = yaml.safe_load(Path(scenario_path).read_text(encoding="utf-8")) or {}
    else:
        source = "inline://scenario"
        raw = yaml.safe_load(scenario_text or "") or {}

    # TODO(scenario): validate the three-block DSL and normalize action/assertion schemas.
    return ScenarioPlan(
        source=source,
        version=str(raw.get("version", "v1alpha1")),
        setup=raw.get("setup", {}),
        stimulus=[
            ScenarioAction(**item)
            for item in raw.get("stimulus", [])
        ],
        assertions=[
            ScenarioAssertion(**item)
            for item in raw.get("assertions", [])
        ],
    )
