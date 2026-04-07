from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class DomainError(Exception):
    """Stable error shape for module boundaries."""

    error_code: str
    message: str
    explain: str | None = None
    observations: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    details: dict[str, object] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"{self.error_code}: {self.message}"


class TodoBoundaryError(DomainError):
    """Raised by scaffold-only paths that still need real implementation."""

    def __init__(self, message: str, *, details: dict[str, object] | None = None) -> None:
        super().__init__(
            error_code="TODO_NOT_IMPLEMENTED",
            message=message,
            explain="This call crossed into a scaffold boundary that still needs a concrete implementation.",
            next_actions=[
                "Replace the stub service owned by this module.",
                "Keep the public contract unchanged while filling the implementation.",
            ],
            details=details or {},
        )
