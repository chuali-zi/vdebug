from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class VirtualClock:
    """Canonical time owner for Mode A."""

    now_ns: int = 0

    def advance_ms(self, delta_ms: int) -> int:
        self.now_ns += delta_ms * 1_000_000
        return self.now_ns
