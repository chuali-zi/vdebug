from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ArtifactStoreConfig:
    root_dir: Path

    def ensure_root(self) -> Path:
        self.root_dir.mkdir(parents=True, exist_ok=True)
        return self.root_dir
