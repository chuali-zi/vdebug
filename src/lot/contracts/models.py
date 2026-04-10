from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

SessionStatus = Literal["active", "finished", "error"]
Severity = Literal["info", "warn", "error"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4()}"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ErrorPayload(StrictModel):
    error_code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    explain: str | None = None
    observations: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


class Capabilities(StrictModel):
    modes: list[str]
    buses: list[str]
    device_types: list[str]
    scenario_version: str = "v1alpha1"
    api_version: str = "v1"


class SessionRecord(StrictModel):
    session_id: str = Field(default_factory=lambda: new_id("sess"))
    board_profile: str
    mode: str = "device_sim"
    seed: int = 0
    created_at: datetime = Field(default_factory=utc_now)
    status: SessionStatus = "active"


class BoardProfile(StrictModel):
    source_path: str
    version: str = "v1alpha1"
    board: str = "TODO_BOARD"
    buses: dict[str, Any] = Field(default_factory=dict)
    gpio: dict[str, Any] = Field(default_factory=dict)
    power: dict[str, Any] | None = None
    constraints: dict[str, Any] | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class SimEvent(StrictModel):
    event_id: str = Field(default_factory=lambda: new_id("evt"))
    session_id: str
    t_virtual_ns: int
    source: str
    type: str
    severity: Severity
    payload: dict[str, Any] = Field(default_factory=dict)


class DiagnosticFact(StrictModel):
    fact_id: str = Field(default_factory=lambda: new_id("fact"))
    session_id: str
    kind: str
    params: dict[str, Any] = Field(default_factory=dict)
    source_events: list[str] = Field(default_factory=list)


class Explanation(StrictModel):
    hypothesis: str
    confidence: float = 0.0
    observations: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    uncertainty_note: str | None = None


class DiagnosisBatch(StrictModel):
    facts: list[DiagnosticFact] = Field(default_factory=list)
    explanations: list[Explanation] = Field(default_factory=list)


class StepResult(StrictModel):
    now_ns: int
    events: list[SimEvent] = Field(default_factory=list)
    state_delta: dict[str, Any] = Field(default_factory=dict)


class IoResult(StrictModel):
    result: dict[str, Any] = Field(default_factory=dict)
    events: list[SimEvent] = Field(default_factory=list)
    state_delta: dict[str, Any] = Field(default_factory=dict)


class StateSnapshot(StrictModel):
    session: SessionRecord
    board: BoardProfile
    now_ns: int
    pending_events: int = 0
    state: dict[str, Any] = Field(default_factory=dict)
    recent_events: list[SimEvent] = Field(default_factory=list)
    facts: list[DiagnosticFact] = Field(default_factory=list)
    explanations: list[Explanation] = Field(default_factory=list)


class ScenarioAction(StrictModel):
    at_ms: int
    action: str
    params: dict[str, Any] = Field(default_factory=dict)


class ScenarioAssertion(StrictModel):
    kind: str
    params: dict[str, Any] = Field(default_factory=dict)


class ScenarioPlan(StrictModel):
    source: str
    source_text: str | None = None
    version: str = "v1alpha1"
    setup: dict[str, Any] = Field(default_factory=dict)
    stimulus: list[ScenarioAction] = Field(default_factory=list)
    assertions: list[ScenarioAssertion] = Field(default_factory=list)


class ScenarioResult(StrictModel):
    status: Literal["pass", "fail", "todo"] = "todo"
    summary: str
    assertions: list[dict[str, Any]] = Field(default_factory=list)
    snapshot: StateSnapshot | None = None
