from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from shutil import copy2

from lot.artifacts.store import ArtifactSessionPaths, ArtifactStoreConfig
from lot.contracts.models import DiagnosisBatch, SessionRecord, StateSnapshot
from lot.session.models import RuntimeContext

_EVENT_WINDOW = 200
_FACT_WINDOW = 200
_EXPLANATION_WINDOW = 100


@dataclass(slots=True)
class ArtifactsServiceStub:
    """Owns state views and exported artifact paths."""

    config: ArtifactStoreConfig

    def append_runtime_data(self, runtime: RuntimeContext, *, step_events: list, diagnosis: DiagnosisBatch) -> None:
        runtime.recent_events.extend(step_events)
        runtime.recent_facts.extend(diagnosis.facts)
        runtime.recent_explanations.extend(diagnosis.explanations)

        self._trim_recent_windows(runtime)

        paths = self.config.session_paths(runtime.session_id)
        self.config.append_ndjson(
            paths.event_stream,
            [event.model_dump(mode="json") for event in step_events],
        )
        self.config.append_ndjson(
            paths.diagnostic_facts,
            [fact.model_dump(mode="json") for fact in diagnosis.facts],
        )

        explanations = self.config.read_json(paths.explanations, default=[])
        if not isinstance(explanations, list):
            explanations = []
        explanations.extend(
            explanation.model_dump(mode="json")
            for explanation in diagnosis.explanations
        )
        self.config.write_json(paths.explanations, explanations)

        self.config.write_json(paths.state_snapshot, self._runtime_state_payload(runtime))
        self.config.write_json(paths.manifest, self._manifest_payload(runtime, paths))

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
        paths = self.config.session_paths(session.session_id)

        self.config.write_json(paths.session_meta, session.model_dump(mode="json"))
        self.config.write_json(paths.board_profile, runtime.board_profile.model_dump(mode="json"))
        self.config.write_json(
            paths.state_snapshot,
            self.build_state_view(session, runtime).model_dump(mode="json"),
        )

        self.config.ensure_text_file(paths.event_stream)
        self.config.ensure_text_file(paths.diagnostic_facts)

        explanations = self.config.read_json(paths.explanations, default=[])
        if not isinstance(explanations, list):
            explanations = []
        if not explanations and runtime.recent_explanations:
            explanations = [
                explanation.model_dump(mode="json")
                for explanation in runtime.recent_explanations
            ]
        self.config.write_json(paths.explanations, explanations)

        warnings: list[str] = []
        board_source = Path(session.board_profile)
        if not self.config.copy_file(board_source, paths.board_profile_source):
            warnings.append(
                f"board profile source unavailable via path: {session.board_profile}"
            )

        if not paths.scenario_source.exists():
            warnings.append(
                "scenario source unavailable: current public seam does not store it on "
                "RuntimeContext or pass it into export_bundle"
            )

        manifest = self._manifest_payload(runtime, paths, session=session, warnings=warnings)
        self.config.write_json(paths.manifest, manifest)

        included_files: list[str] = []
        for source in paths.canonical_files():
            if not source.exists():
                continue
            target = paths.bundle_dir / source.name
            copy2(source, target)
            included_files.append(str(target))

        runtime.exported_artifacts = {
            "session_dir": str(paths.session_dir),
            "bundle_path": str(paths.bundle_dir),
            "manifest": str(paths.bundle_dir / paths.manifest.name),
            "included_files": json.dumps(included_files, ensure_ascii=False),
        }
        return runtime.exported_artifacts

    def _trim_recent_windows(self, runtime: RuntimeContext) -> None:
        runtime.recent_events = runtime.recent_events[-_EVENT_WINDOW:]
        runtime.recent_facts = runtime.recent_facts[-_FACT_WINDOW:]
        runtime.recent_explanations = runtime.recent_explanations[-_EXPLANATION_WINDOW:]

    def _runtime_state_payload(self, runtime: RuntimeContext) -> dict[str, object]:
        return {
            "session_id": runtime.session_id,
            "board": runtime.board_profile.model_dump(mode="json"),
            "now_ns": runtime.now_ns,
            "pending_events": len(runtime.scheduler_items),
            "state": runtime.device_state,
            "recent_events": [
                event.model_dump(mode="json")
                for event in runtime.recent_events[-20:]
            ],
            "facts": [
                fact.model_dump(mode="json")
                for fact in runtime.recent_facts[-20:]
            ],
            "explanations": [
                explanation.model_dump(mode="json")
                for explanation in runtime.recent_explanations[-10:]
            ],
        }

    def _manifest_payload(
        self,
        runtime: RuntimeContext,
        paths: ArtifactSessionPaths,
        *,
        session: SessionRecord | None = None,
        warnings: list[str] | None = None,
    ) -> dict[str, object]:
        included = [
            str(path)
            for path in paths.canonical_files()
            if path.exists()
        ]
        manifest: dict[str, object] = {
            "session_id": runtime.session_id,
            "session_status": session.status if session is not None else "active",
            "now_ns": runtime.now_ns,
            "pending_events": len(runtime.scheduler_items),
            "board_profile": runtime.board_profile.source_path,
            "artifact_root": str(paths.session_dir),
            "bundle_path": str(paths.bundle_dir),
            "included_files": included,
            "counts": {
                "recent_events": len(runtime.recent_events),
                "recent_facts": len(runtime.recent_facts),
                "recent_explanations": len(runtime.recent_explanations),
            },
        }
        if warnings:
            manifest["warnings"] = warnings
        return manifest
