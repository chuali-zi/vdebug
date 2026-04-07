from __future__ import annotations

from lot.api.models import ErrorEnvelope
from lot.contracts.errors import DomainError
from lot.contracts.models import ErrorPayload


def map_domain_error(request_id: str, error: DomainError) -> ErrorEnvelope:
    return ErrorEnvelope(
        request_id=request_id,
        error=ErrorPayload(
            error_code=error.error_code,
            message=error.message,
            details=error.details,
            explain=error.explain,
            observations=error.observations,
            next_actions=error.next_actions,
        ),
    )
