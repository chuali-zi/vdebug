from __future__ import annotations

from typing import Any

from pydantic import Field

from lot.contracts.models import StrictModel


class ScenarioAssertionResult(StrictModel):
    kind: str
    status: str
    details: dict[str, Any] = Field(default_factory=dict)
