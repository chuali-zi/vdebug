from __future__ import annotations

from lot.contracts.models import DiagnosticFact, SimEvent


def extract_facts(session_id: str, events: list[SimEvent]) -> list[DiagnosticFact]:
    """Convert normalized events into diagnostic facts.

    TODO(diagnosis):
    - classify meaningful evidence patterns
    - keep facts traceable back to event_ids
    - avoid direct dependency on device-private runtime structures
    """

    return [
        DiagnosticFact(
            session_id=session_id,
            kind="event_observed",
            params={"event_type": event.type},
            source_events=[event.event_id],
        )
        for event in events
    ]
