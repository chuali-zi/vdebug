from __future__ import annotations

from dataclasses import dataclass

from lot.contracts.models import ScenarioResult
from lot.contracts.protocols import (
    ArtifactsServiceProtocol,
    BoardServiceProtocol,
    CapabilitiesProviderProtocol,
    DiagnosisServiceProtocol,
    EngineServiceProtocol,
    ScenarioServiceProtocol,
    SessionServiceProtocol,
)


@dataclass(slots=True)
class ApiFacade:
    """Thin orchestration layer that freezes module seams for future work."""

    capabilities: CapabilitiesProviderProtocol
    session_service: SessionServiceProtocol
    board_service: BoardServiceProtocol
    engine_service: EngineServiceProtocol
    diagnosis_service: DiagnosisServiceProtocol
    scenario_service: ScenarioServiceProtocol
    artifacts_service: ArtifactsServiceProtocol

    def get_capabilities(self) -> dict:
        return self.capabilities.get_capabilities().model_dump()

    def create_session(self, payload: dict) -> dict:
        board_profile = self.board_service.load_profile(payload["board_profile"])
        session = self.session_service.create_session(
            board_profile=board_profile,
            seed=payload.get("seed", 0),
            mode=payload.get("mode", "device_sim"),
        )
        runtime = self.session_service.get_runtime(session.session_id)
        snapshot = self.artifacts_service.build_state_view(session, runtime)
        return {"session": session.model_dump(), "state": snapshot.model_dump()}

    def step_session(self, session_id: str, payload: dict) -> dict:
        runtime = self.session_service.get_runtime(session_id)
        step_result = self.engine_service.step(runtime, payload["delta_ms"])
        diagnosis = self.diagnosis_service.analyze(runtime, step_result.events)
        self.artifacts_service.append_runtime_data(
            runtime,
            step_events=step_result.events,
            diagnosis=diagnosis,
        )
        self.session_service.save_runtime(runtime)
        snapshot = self.artifacts_service.build_state_view(
            self.session_service.get_session(session_id),
            runtime,
        )
        return {
            "step": step_result.model_dump(),
            "diagnosis": diagnosis.model_dump(),
            "state": snapshot.model_dump(),
        }

    def execute_io(self, session_id: str, bus_action: str, payload: dict) -> dict:
        runtime = self.session_service.get_runtime(session_id)
        io_result = self.engine_service.execute_io(runtime, bus_action, payload.get("params", {}))
        diagnosis = self.diagnosis_service.analyze(runtime, io_result.events)
        self.artifacts_service.append_runtime_data(
            runtime,
            step_events=io_result.events,
            diagnosis=diagnosis,
        )
        self.session_service.save_runtime(runtime)
        snapshot = self.artifacts_service.build_state_view(
            self.session_service.get_session(session_id),
            runtime,
        )
        return {
            "io": io_result.model_dump(),
            "diagnosis": diagnosis.model_dump(),
            "state": snapshot.model_dump(),
        }

    def get_state(self, session_id: str) -> dict:
        session = self.session_service.get_session(session_id)
        runtime = self.session_service.get_runtime(session_id)
        snapshot = self.artifacts_service.build_state_view(session, runtime)
        return snapshot.model_dump()

    def run_scenario(self, session_id: str, payload: dict) -> dict:
        session = self.session_service.get_session(session_id)
        runtime = self.session_service.get_runtime(session_id)
        plan = self.scenario_service.load_plan(
            scenario_path=payload.get("scenario_path"),
            scenario_text=payload.get("scenario_text"),
        )
        result: ScenarioResult = self.scenario_service.run_plan(runtime, plan, session=session)
        self.session_service.save_runtime(runtime)
        bundle = self.artifacts_service.export_bundle(
            session,
            runtime,
        )
        return {
            "plan": plan.model_dump(),
            "result": result.model_dump(),
            "bundle": bundle,
        }
