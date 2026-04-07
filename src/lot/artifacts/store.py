from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(slots=True)
class ArtifactStoreConfig:
    root_dir: Path

    def ensure_root(self) -> Path:
        self.root_dir.mkdir(parents=True, exist_ok=True)
        return self.root_dir

    def session_paths(self, session_id: str) -> "ArtifactSessionPaths":
        session_dir = self.ensure_root() / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        bundle_dir = session_dir / "repro_bundle"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        return ArtifactSessionPaths(
            session_dir=session_dir,
            bundle_dir=bundle_dir,
            session_meta=session_dir / "session_meta.json",
            board_profile=session_dir / "board_profile.json",
            board_profile_source=session_dir / "board_profile.source.yaml",
            scenario_source=session_dir / "scenario.source.yaml",
            event_stream=session_dir / "event_stream.ndjson",
            diagnostic_facts=session_dir / "diagnostic_facts.ndjson",
            explanations=session_dir / "explanations.json",
            state_snapshot=session_dir / "state_snapshot.json",
            manifest=session_dir / "manifest.json",
        )

    def write_json(self, target: Path, payload: Any) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def read_json(self, target: Path, default: Any) -> Any:
        if not target.exists():
            return default
        return json.loads(target.read_text(encoding="utf-8"))

    def append_ndjson(self, target: Path, records: Iterable[dict[str, Any]]) -> None:
        rows = list(records)
        if not rows:
            return

        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8", newline="\n") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False))
                handle.write("\n")

    def ensure_text_file(self, target: Path, content: str = "") -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_text(content, encoding="utf-8")

    def copy_file(self, source: Path, target: Path) -> bool:
        if not source.exists() or not source.is_file():
            return False
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        return True


@dataclass(frozen=True, slots=True)
class ArtifactSessionPaths:
    session_dir: Path
    bundle_dir: Path
    session_meta: Path
    board_profile: Path
    board_profile_source: Path
    scenario_source: Path
    event_stream: Path
    diagnostic_facts: Path
    explanations: Path
    state_snapshot: Path
    manifest: Path

    def canonical_files(self) -> list[Path]:
        return [
            self.session_meta,
            self.board_profile,
            self.board_profile_source,
            self.scenario_source,
            self.event_stream,
            self.diagnostic_facts,
            self.explanations,
            self.state_snapshot,
            self.manifest,
        ]
