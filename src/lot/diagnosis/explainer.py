from __future__ import annotations

from lot.contracts.models import DiagnosticFact, Explanation
from lot.diagnosis.rules import get_rule


def explain_facts(facts: list[DiagnosticFact]) -> list[Explanation]:
    """Build evidence-bound explanations from diagnostic facts.

    Each explanation is generated from a stable fact kind so the event -> fact
    -> explanation chain stays inspectable by downstream modules.
    """

    if not facts:
        return []

    explanations: list[Explanation] = []
    for fact in facts:
        rule = get_rule(fact.kind)
        if rule is None:
            continue

        explanations.append(
            Explanation(
                hypothesis=rule.hypothesis_template.format(**_format_params(fact)),
                confidence=_confidence(rule.base_confidence, fact),
                observations=[_observation_for_fact(fact)],
                next_actions=list(rule.next_actions),
                uncertainty_note=_uncertainty_note(fact),
            )
        )

    explanations.sort(key=lambda item: item.confidence, reverse=True)
    return explanations


def _format_params(fact: DiagnosticFact) -> dict[str, object]:
    params = dict(fact.params)
    params.setdefault("bus", "unknown")
    params.setdefault("pin", "unknown")
    params.setdefault("addr", "unknown")
    return params


def _confidence(base_confidence: float, fact: DiagnosticFact) -> float:
    if fact.kind == "repeated_nack":
        count = fact.params.get("count", 0)
        if isinstance(count, int):
            return min(0.92, base_confidence + (min(count, 5) - 2) * 0.08)
    if fact.kind == "uart_baud_mismatch":
        expected = fact.params.get("expected")
        observed = fact.params.get("observed")
        if isinstance(expected, int) and isinstance(observed, int) and expected != observed:
            return min(0.98, base_confidence + 0.02)
    if fact.kind == "gpio_direction_conflict":
        actual = fact.params.get("actual")
        if isinstance(actual, str) and actual != "unknown":
            return min(0.98, base_confidence + 0.02)
    return base_confidence


def _uncertainty_note(fact: DiagnosticFact) -> str | None:
    if fact.kind == "repeated_nack":
        count = fact.params.get("count")
        if isinstance(count, int) and count < 3:
            return "Only a short NACK streak is observed so addressing, sequencing, or power issues are all still plausible."
    if fact.kind == "gpio_direction_conflict" and fact.params.get("actual") == "unknown":
        return "Pin direction could not be confirmed from the public runtime state."
    if fact.kind == "uart_baud_mismatch":
        expected = fact.params.get("expected")
        observed = fact.params.get("observed")
        if expected is None or observed is None:
            return "Baud mismatch was inferred from the command result because the exact baud pair was not available."
    return None


def _observation_for_fact(fact: DiagnosticFact) -> str:
    if fact.kind == "bus_stuck_low":
        return f"{fact.fact_id}: bus_stuck_low bus={fact.params.get('bus')} line={fact.params.get('line')}"
    if fact.kind == "repeated_nack":
        return (
            f"{fact.fact_id}: repeated_nack bus={fact.params.get('bus')} "
            f"addr={fact.params.get('addr')} count={fact.params.get('count')}"
        )
    if fact.kind == "gpio_direction_conflict":
        return (
            f"{fact.fact_id}: gpio_direction_conflict pin={fact.params.get('pin')} "
            f"expected={fact.params.get('expected')} actual={fact.params.get('actual')}"
        )
    if fact.kind == "uart_baud_mismatch":
        return (
            f"{fact.fact_id}: uart_baud_mismatch bus={fact.params.get('bus')} "
            f"expected={fact.params.get('expected')} observed={fact.params.get('observed')}"
        )
    return fact.fact_id
