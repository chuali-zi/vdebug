from __future__ import annotations

from dataclasses import dataclass

from lot.contracts.models import DiagnosisBatch, SimEvent
from lot.diagnosis.explainer import explain_facts
from lot.diagnosis.facts import extract_facts
from lot.session.models import RuntimeContext


@dataclass(slots=True)
class DiagnosisServiceStub:
    """Owns the event -> fact -> explanation pipeline."""

    def analyze(self, runtime: RuntimeContext, events: list[SimEvent]) -> DiagnosisBatch:
        facts = extract_facts(runtime.session_id, events)
        explanations = explain_facts(facts)
        return DiagnosisBatch(facts=facts, explanations=explanations)
