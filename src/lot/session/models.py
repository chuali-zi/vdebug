from __future__ import annotations

from typing import Any

from pydantic import Field

from lot.contracts.models import BoardProfile, DiagnosticFact, Explanation, SimEvent, StrictModel


class RuntimeContext(StrictModel):
    """Single execution container in MVP."""

    session_id: str
    board_profile: BoardProfile
    now_ns: int = 0
    scheduler_items: list[dict[str, Any]] = Field(default_factory=list)
    device_state: dict[str, Any] = Field(default_factory=dict)
    recent_events: list[SimEvent] = Field(default_factory=list)
    recent_facts: list[DiagnosticFact] = Field(default_factory=list)
    recent_explanations: list[Explanation] = Field(default_factory=list)
    exported_artifacts: dict[str, str] = Field(default_factory=dict)
