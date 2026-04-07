from __future__ import annotations

from typing import Any

from pydantic import Field

from lot.contracts.models import BoardProfile, DiagnosticFact, Explanation, SimEvent, StrictModel


class RuntimeContext(StrictModel):
    """Single execution container in MVP.

    The frozen cross-module shape is:
    - ``board_topology`` for structural board data
    - ``engine_state`` for time/scheduler state
    - ``device_registry`` for device-facing runtime state

    Compatibility properties keep the existing scaffold modules working while
    the rest of the MVP is still being filled in.
    """

    session_id: str
    board_profile: BoardProfile
    board_topology: dict[str, Any] = Field(default_factory=dict)
    engine_state: dict[str, Any] = Field(default_factory=dict)
    device_registry: dict[str, Any] = Field(default_factory=dict)
    last_error: dict[str, Any] | None = None
    recent_events: list[SimEvent] = Field(default_factory=list)
    recent_facts: list[DiagnosticFact] = Field(default_factory=list)
    recent_explanations: list[Explanation] = Field(default_factory=list)
    exported_artifacts: dict[str, str] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        if not self.board_topology:
            self.board_topology = dict(self.board_profile.raw)

        self.engine_state.setdefault("now_ns", 0)
        self.engine_state.setdefault("scheduler_items", [])
        self.device_registry.setdefault("devices", {})
        self.device_registry.setdefault("state", {})

    @classmethod
    def from_board_profile(cls, *, session_id: str, board_profile: BoardProfile) -> "RuntimeContext":
        return cls(
            session_id=session_id,
            board_profile=board_profile,
            board_topology=dict(board_profile.raw),
            engine_state={
                "now_ns": 0,
                "scheduler_items": [],
            },
            device_registry={
                "devices": {},
                "state": {},
            },
        )

    @property
    def now_ns(self) -> int:
        return int(self.engine_state.setdefault("now_ns", 0))

    @now_ns.setter
    def now_ns(self, value: int) -> None:
        self.engine_state["now_ns"] = int(value)

    @property
    def scheduler_items(self) -> list[dict[str, Any]]:
        return self.engine_state.setdefault("scheduler_items", [])

    @scheduler_items.setter
    def scheduler_items(self, value: list[dict[str, Any]]) -> None:
        self.engine_state["scheduler_items"] = value

    @property
    def device_state(self) -> dict[str, Any]:
        return self.device_registry.setdefault("state", {})

    @device_state.setter
    def device_state(self, value: dict[str, Any]) -> None:
        self.device_registry["state"] = value
