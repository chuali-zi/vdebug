from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import Any

from lot.contracts.errors import DomainError


@dataclass(order=True, slots=True)
class ScheduledEvent:
    due_ns: int
    priority: int
    seq: int
    kind: str
    payload: dict[str, Any] = field(default_factory=dict, compare=False)


@dataclass(slots=True)
class SchedulerQueue:
    """Deterministic scheduler abstraction for the engine."""

    items: list[ScheduledEvent] = field(default_factory=list)

    @classmethod
    def from_runtime_state(cls, runtime_items: list[dict[str, Any]]) -> "SchedulerQueue":
        queue = cls()
        for item in runtime_items:
            queue.push(
                ScheduledEvent(
                    due_ns=int(item["due_ns"]),
                    priority=int(item["priority"]),
                    seq=int(item["seq"]),
                    kind=str(item["kind"]),
                    payload=dict(item.get("payload", {})),
                )
            )
        return queue

    def count(self) -> int:
        return len(self.items)

    def next_seq(self) -> int:
        if not self.items:
            return 1
        return max(item.seq for item in self.items) + 1

    def enqueue(self, *, due_ns: int, kind: str, payload: dict[str, Any], priority: int = 100) -> ScheduledEvent:
        self._validate_queue_input(due_ns=due_ns, kind=kind, priority=priority, payload=payload)
        scheduled = ScheduledEvent(
            due_ns=due_ns,
            priority=priority,
            seq=self.next_seq(),
            kind=kind,
            payload=dict(payload),
        )
        self.push(scheduled)
        return scheduled

    def push(self, item: ScheduledEvent) -> None:
        heapq.heappush(self.items, item)

    def drain_due(self, target_ns: int) -> list[ScheduledEvent]:
        if isinstance(target_ns, bool) or not isinstance(target_ns, int):
            raise DomainError(
                error_code="INVALID_TARGET_TIME",
                message=f"Invalid scheduler target_ns: {target_ns!r}",
                explain="Scheduler comparisons must use integer virtual nanoseconds.",
                next_actions=["Retry with an integer target_ns."],
            )

        due_items: list[ScheduledEvent] = []
        while self.items and self.items[0].due_ns <= target_ns:
            due_items.append(heapq.heappop(self.items))
        return due_items

    def to_runtime_state(self) -> list[dict[str, Any]]:
        ordered_items = sorted(self.items)
        return [
            {
                "due_ns": item.due_ns,
                "priority": item.priority,
                "seq": item.seq,
                "kind": item.kind,
                "payload": dict(item.payload),
            }
            for item in ordered_items
        ]

    def to_public_state(self) -> list[dict[str, Any]]:
        ordered_items = sorted(self.items)
        return [
            {
                "due_ns": item.due_ns,
                "priority": item.priority,
                "seq": item.seq,
                "kind": item.kind,
            }
            for item in ordered_items
        ]

    def _validate_queue_input(
        self,
        *,
        due_ns: int,
        kind: str,
        priority: int,
        payload: dict[str, Any],
    ) -> None:
        if isinstance(due_ns, bool) or not isinstance(due_ns, int) or due_ns < 0:
            raise DomainError(
                error_code="INVALID_SCHEDULE_TIME",
                message=f"Invalid due_ns for scheduled event: {due_ns!r}",
                explain="Scheduled events must use a non-negative integer nanosecond due time.",
                next_actions=["Retry with a non-negative integer due_ns."],
            )
        if isinstance(priority, bool) or not isinstance(priority, int):
            raise DomainError(
                error_code="INVALID_SCHEDULE_PRIORITY",
                message=f"Invalid priority for scheduled event: {priority!r}",
                explain="Scheduler priority must be an integer so ordering stays deterministic.",
                next_actions=["Retry with an integer priority."],
            )
        if not isinstance(kind, str) or not kind:
            raise DomainError(
                error_code="INVALID_SCHEDULE_KIND",
                message=f"Invalid kind for scheduled event: {kind!r}",
                explain="Each scheduled event must declare a stable non-empty kind.",
                next_actions=["Retry with a non-empty string kind."],
            )
        if not isinstance(payload, dict):
            raise DomainError(
                error_code="INVALID_SCHEDULE_PAYLOAD",
                message="Scheduled event payload must be a dictionary.",
                explain="Scheduler payloads must stay serializable across module boundaries.",
                next_actions=["Retry with a JSON-like object payload."],
            )
