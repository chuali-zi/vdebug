from __future__ import annotations

from dataclasses import dataclass

from lot.contracts.errors import DomainError

NS_PER_MS = 1_000_000


@dataclass(slots=True)
class VirtualClock:
    """Canonical time owner for Mode A."""

    now_ns: int = 0

    def preview_advance_ms(self, delta_ms: int) -> int:
        self._validate_delta_ms(delta_ms)
        return self.now_ns + (delta_ms * NS_PER_MS)

    def advance_ms(self, delta_ms: int) -> int:
        self.now_ns = self.preview_advance_ms(delta_ms)
        return self.now_ns

    def advance_to(self, target_ns: int) -> int:
        if isinstance(target_ns, bool) or not isinstance(target_ns, int) or target_ns < self.now_ns:
            raise DomainError(
                error_code="INVALID_TARGET_TIME",
                message=f"Invalid target_ns for virtual clock: {target_ns!r}",
                explain="Virtual time must advance monotonically in nanoseconds.",
                next_actions=["Retry with an integer target_ns greater than or equal to now_ns."],
            )
        self.now_ns = target_ns
        return self.now_ns

    def _validate_delta_ms(self, delta_ms: int) -> None:
        if isinstance(delta_ms, bool) or not isinstance(delta_ms, int) or delta_ms < 0:
            raise DomainError(
                error_code="INVALID_STEP_DELTA",
                message=f"Invalid delta_ms for virtual clock: {delta_ms!r}",
                explain="Step delta must be a non-negative integer expressed in milliseconds.",
                next_actions=["Retry with a non-negative integer delta_ms."],
            )
