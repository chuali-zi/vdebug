from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from lot.contracts.errors import DomainError
from lot.contracts.models import BoardProfile


@dataclass(slots=True)
class BoardServiceStub:
    """Loads and normalizes board profile documents."""

    root_dir: Path

    def load_profile(self, profile_ref: str | Path) -> BoardProfile:
        candidate = Path(profile_ref)
        if not candidate.is_absolute():
            candidate = self.root_dir / candidate

        if not candidate.exists():
            raise DomainError(
                error_code="BOARD_PROFILE_NOT_FOUND",
                message=f"Board profile not found: {candidate}",
                explain="The requested board profile file could not be resolved from the repository root.",
            )

        raw = yaml.safe_load(candidate.read_text(encoding="utf-8")) or {}

        # TODO(board): replace permissive loading with schema validation and richer normalization.
        return BoardProfile(
            source_path=str(candidate),
            version=str(raw.get("version", "v1alpha1")),
            board=str(raw.get("board", "TODO_BOARD")),
            buses=raw.get("buses", {}),
            gpio=raw.get("gpio", {}),
            raw=raw,
        )
