from __future__ import annotations

from lot.contracts.models import DiagnosticFact, Explanation


def explain_facts(facts: list[DiagnosticFact]) -> list[Explanation]:
    """Build evidence-bound explanations from diagnostic facts.

    TODO(diagnosis):
    - rank hypotheses by fact patterns and board context
    - emit stable observations and next_actions
    - preserve the event -> fact -> explanation chain
    """

    if not facts:
        return []

    return [
        Explanation(
            hypothesis="TODO: derive hypothesis from diagnostic facts",
            confidence=0.1,
            observations=[fact.fact_id for fact in facts],
            next_actions=["Implement rule-based explanation generation in diagnosis/explainer.py."],
            uncertainty_note="Scaffold placeholder only.",
        )
    ]
