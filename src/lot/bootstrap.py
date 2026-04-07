from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lot.api.facade import ApiFacade
from lot.api.models import CapabilitiesProvider
from lot.artifacts.service import ArtifactsServiceStub
from lot.artifacts.store import ArtifactStoreConfig
from lot.board.service import BoardServiceStub
from lot.devices.registry import build_default_device_registry
from lot.diagnosis.service import DiagnosisServiceStub
from lot.engine.service import EngineServiceStub
from lot.scenario.service import ScenarioServiceStub
from lot.session.service import SessionServiceStub


@dataclass(slots=True)
class AppContainer:
    """Single place where module ownership is wired together."""

    api_facade: ApiFacade
    session_service: SessionServiceStub
    board_service: BoardServiceStub
    engine_service: EngineServiceStub
    diagnosis_service: DiagnosisServiceStub
    scenario_service: ScenarioServiceStub
    artifacts_service: ArtifactsServiceStub


def build_container(base_dir: Path | None = None) -> AppContainer:
    root = base_dir or Path.cwd()
    device_registry = build_default_device_registry()
    board_service = BoardServiceStub(root_dir=root)
    session_service = SessionServiceStub()
    engine_service = EngineServiceStub(device_registry=device_registry)
    diagnosis_service = DiagnosisServiceStub()
    artifacts_service = ArtifactsServiceStub(
        config=ArtifactStoreConfig(root_dir=root / "runtime_artifacts")
    )
    scenario_service = ScenarioServiceStub()
    capabilities = CapabilitiesProvider.from_registry(device_registry)

    api_facade = ApiFacade(
        capabilities=capabilities,
        session_service=session_service,
        board_service=board_service,
        engine_service=engine_service,
        diagnosis_service=diagnosis_service,
        scenario_service=scenario_service,
        artifacts_service=artifacts_service,
    )

    return AppContainer(
        api_facade=api_facade,
        session_service=session_service,
        board_service=board_service,
        engine_service=engine_service,
        diagnosis_service=diagnosis_service,
        scenario_service=scenario_service,
        artifacts_service=artifacts_service,
    )
