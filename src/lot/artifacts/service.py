from __future__ import annotations

from dataclasses import dataclass

from lot.artifacts.store import ArtifactStoreConfig
from lot.contracts.models import DiagnosisBatch, SessionRecord, StateSnapshot
from lot.session.models import RuntimeContext


@dataclass(slots=True)
class ArtifactsServiceStub:
    """Owns state views and exported artifact paths."""

    config: ArtifactStoreConfig

    def append_runtime_data(self, runtime: RuntimeContext, *, step_events: list, diagnosis: DiagnosisBatch) -> None:
        runtime.recent_events.extend(step_events)
        runtime.recent_facts.extend(diagnosis.facts)
        runtime.recent_explanations.extend(diagnosis.explanations)

        # TODO(artifacts): rotate windows, write NDJSON traces, and preserve reproducibility metadata.

    def build_state_view(self, session: SessionRecord, runtime: RuntimeContext) -> StateSnapshot:
        return StateSnapshot(
            session=session,
            board=runtime.board_profile,
            now_ns=runtime.now_ns,
            pending_events=len(runtime.scheduler_items),
            state=runtime.device_state,
            recent_events=runtime.recent_events[-20:],
            facts=runtime.recent_facts[-20:],
            explanations=runtime.recent_explanations[-10:],
        )

    def export_bundle(self, session: SessionRecord, runtime: RuntimeContext) -> dict[str, str]:
        root = self.config.ensure_root() / session.session_id
        root.mkdir(parents=True, exist_ok=True)

        # TODO(artifacts): export board profile, scenario source, event log, facts, and explanation bundle.
        runtime.exported_artifacts = {
            "session_dir": str(root),
            "manifest": str(root / "TODO_manifest.json"),
        }
        return runtime.exported_artifacts
