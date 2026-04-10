from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lot.bootstrap import build_container
from lot.contracts.models import BoardProfile, DiagnosisBatch, DiagnosticFact, IoResult, ScenarioAction, ScenarioAssertion, ScenarioPlan, SimEvent, StepResult
from lot.scenario.runner import run_plan
from lot.session.models import RuntimeContext
from tests.support import repo_temp_dir

_MS_TO_NS = 1_000_000


class EngineStub:
    def __init__(self) -> None:
        self.event_ids: list[str] = []

    def step(self, runtime: RuntimeContext, delta_ms: int) -> StepResult:
        runtime.now_ns += delta_ms * _MS_TO_NS
        return StepResult(now_ns=runtime.now_ns, events=[])

    def execute_io(self, runtime: RuntimeContext, bus_action: str, payload: dict[str, object]) -> IoResult:
        event_id = f"evt-{len(self.event_ids) + 1}"
        self.event_ids.append(event_id)
        event = SimEvent(
            event_id=event_id,
            session_id=runtime.session_id,
            t_virtual_ns=runtime.now_ns,
            source=bus_action,
            type="I2C_NACK",
            severity="warn",
            payload={"bus": "i2c0", "addr_7bit": 80},
        )
        return IoResult(result={}, events=[event], state_delta={})


class DiagnosisStub:
    def __init__(self, engine: EngineStub) -> None:
        self.engine = engine

    def analyze(self, runtime: RuntimeContext, events: list[SimEvent]) -> DiagnosisBatch:
        if not events or len(self.engine.event_ids) < 2:
            return DiagnosisBatch()
        return DiagnosisBatch(
            facts=[
                DiagnosticFact(
                    session_id=runtime.session_id,
                    kind="repeated_nack",
                    params={"count": len(self.engine.event_ids)},
                    source_events=list(self.engine.event_ids),
                )
            ]
        )


class ArtifactsStub:
    def append_runtime_data(self, runtime: RuntimeContext, *, step_events: list[SimEvent], diagnosis: DiagnosisBatch) -> None:
        runtime.recent_events.extend(step_events)
        runtime.recent_facts.extend(diagnosis.facts)
        runtime.recent_explanations.extend(diagnosis.explanations)

    def build_state_view(self, session, runtime: RuntimeContext):
        return None


class ScenarioRegressionTests(unittest.TestCase):
    def test_expect_diagnosis_waits_for_all_source_events(self) -> None:
        runtime = RuntimeContext.from_board_profile(
            session_id="sess-scenario",
            board_profile=BoardProfile(source_path="profiles/example_stm32f4.yaml", raw={}),
        )
        engine = EngineStub()
        diagnosis = DiagnosisStub(engine)
        plan = ScenarioPlan(
            source="inline://scenario",
            stimulus=[
                ScenarioAction(at_ms=0, action="i2c.transact", params={}),
                ScenarioAction(at_ms=20, action="i2c.transact", params={}),
            ],
            assertions=[
                ScenarioAssertion(
                    kind="expect_diagnosis",
                    params={"kind": "repeated_nack", "within_ms": 10},
                )
            ],
        )

        result = run_plan(
            runtime,
            plan,
            engine=engine,
            diagnosis=diagnosis,
            artifacts=ArtifactsStub(),
        )

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.assertions[0]["status"], "fail")
        self.assertEqual(result.assertions[0]["details"]["visible_fact_ids"], [])

    def test_build_container_shares_scenario_services(self) -> None:
        with repo_temp_dir("container") as tmpdir:
            container = build_container(base_dir=tmpdir)

        self.assertIs(container.scenario_service.engine_service, container.engine_service)
        self.assertIs(container.scenario_service.diagnosis_service, container.diagnosis_service)
        self.assertIs(container.scenario_service.artifacts_service, container.artifacts_service)

    def test_build_container_uses_base_dir_for_session_storage(self) -> None:
        with repo_temp_dir("container") as tmpdir:
            container = build_container(base_dir=tmpdir)
            session = container.session_service.create_session(
                board_profile=container.board_service.load_profile("profiles/example_stm32f4.yaml"),
                seed=0,
                mode="device_sim",
            )
            session_file = tmpdir / "runtime_sessions" / session.session_id / "session.json"
            self.assertTrue(session_file.exists())

    def test_example_scenario_exports_source_and_snapshot(self) -> None:
        with repo_temp_dir("scenario-run") as tmpdir:
            container = build_container(base_dir=tmpdir)
            payload = container.api_facade.create_session(
                {"board_profile": "profiles/example_stm32f4.yaml", "seed": 42, "mode": "device_sim"}
            )
            session_id = payload["session"]["session_id"]

            result = container.api_facade.run_scenario(
                session_id,
                {"scenario_path": "scenarios/example_i2c_stuck.yaml"},
            )

            scenario_source = Path(result["bundle"]["bundle_path"]) / "scenario.source.yaml"
            self.assertEqual(result["result"]["status"], "pass")
            self.assertIsNotNone(result["result"]["snapshot"])
            self.assertTrue(scenario_source.exists())
            self.assertIn("fault.inject", scenario_source.read_text(encoding="utf-8"))
            self.assertIsInstance(result["bundle"]["included_files"], list)
            self.assertIn(str(scenario_source), result["bundle"]["included_files"])


if __name__ == "__main__":
    unittest.main()
