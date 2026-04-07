from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(order=True, slots=True)
class ScheduledEvent:
    due_ns: int
    priority: int
    seq: int
    kind: str
    payload: dict[str, Any] = field(default_factory=dict, compare=False)


@dataclass(slots=True)
class SchedulerQueue:
    """Placeholder queue abstraction for the engine."""

    items: list[ScheduledEvent] = field(default_factory=list)

    def count(self) -> int:
        return len(self.items)

    def to_public_state(self) -> list[dict[str, Any]]:
        return [
            {
                "due_ns": item.due_ns,
                "priority": item.priority,
                "seq": item.seq,
                "kind": item.kind,
            }
            for item in self.items
        ]
