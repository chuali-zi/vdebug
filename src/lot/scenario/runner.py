from __future__ import annotations

from lot.contracts.models import ScenarioPlan, ScenarioResult
from lot.session.models import RuntimeContext


def run_plan_placeholder(runtime: RuntimeContext, plan: ScenarioPlan) -> ScenarioResult:
    """Placeholder runner that reserves scenario ownership.

    TODO(scenario):
    - translate stimulus into engine commands
    - execute assertions against events and diagnosis output
    - keep scenario control on public service boundaries only
    """

    return ScenarioResult(
        status="todo",
        summary=(
            "Scenario parsing is wired, but execution is still a scaffold. "
            "Future agents should implement timeline dispatch and assertion evaluation here."
        ),
        assertions=[
            {
                "kind": assertion.kind,
                "status": "todo",
                "details": {"params": assertion.params},
            }
            for assertion in plan.assertions
        ],
        snapshot=None,
    )
