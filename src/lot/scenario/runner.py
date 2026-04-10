from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lot.contracts.errors import DomainError
from lot.contracts.models import (
    DiagnosticFact,
    Explanation,
    ScenarioAction,
    ScenarioAssertion,
    ScenarioPlan,
    ScenarioResult,
    SessionRecord,
    SimEvent,
)
from lot.contracts.protocols import ArtifactsServiceProtocol, DiagnosisServiceProtocol, EngineServiceProtocol
from lot.scenario.models import ScenarioAssertionResult
from lot.session.models import RuntimeContext

_MS_TO_NS = 1_000_000
_MISSING = object()


@dataclass(slots=True)
class ScenarioExecutionContext:
    runtime: RuntimeContext
    engine: EngineServiceProtocol
    diagnosis: DiagnosisServiceProtocol
    artifacts: ArtifactsServiceProtocol
    start_ns: int
    events: list[SimEvent]
    facts: list[DiagnosticFact]
    explanations: list[Explanation]
    explanation_timeline: list[tuple[int, list[Explanation]]]
    state_timeline: list[tuple[int, dict[str, Any]]]


def run_plan(
    runtime: RuntimeContext,
    plan: ScenarioPlan,
    *,
    engine: EngineServiceProtocol,
    diagnosis: DiagnosisServiceProtocol,
    artifacts: ArtifactsServiceProtocol,
    session: SessionRecord | None = None,
) -> ScenarioResult:
    context = ScenarioExecutionContext(
        runtime=runtime,
        engine=engine,
        diagnosis=diagnosis,
        artifacts=artifacts,
        start_ns=runtime.now_ns,
        events=[],
        facts=[],
        explanations=[],
        explanation_timeline=[],
        state_timeline=[(runtime.now_ns, deepcopy(runtime.device_state))],
    )

    _validate_setup(runtime, plan)

    for action in plan.stimulus:
        _advance_to_action_time(context, action.at_ms)
        _execute_action(context, action)

    _advance_to_assertion_horizon(context, plan.assertions)
    assertion_results = [_evaluate_assertion(context, assertion) for assertion in plan.assertions]
    passed = all(item.status == "pass" for item in assertion_results)

    return ScenarioResult(
        status="pass" if passed else "fail",
        summary=_build_summary(passed, assertion_results, context),
        assertions=[item.model_dump() for item in assertion_results],
        snapshot=artifacts.build_state_view(session, runtime) if session is not None else None,
    )


def _validate_setup(runtime: RuntimeContext, plan: ScenarioPlan) -> None:
    board_profile = plan.setup.get("board_profile")
    if isinstance(board_profile, str) and board_profile.strip():
        runtime_source = str(Path(runtime.board_profile.source_path).resolve())
        requested_source = str(Path(board_profile.strip()).resolve())
        if runtime_source != requested_source:
            raise DomainError(
                error_code="SCENARIO_SETUP_MISMATCH",
                message="Scenario board_profile does not match the active session board profile.",
                explain="Scenario setup can describe the expected board, but it cannot replace the session runtime board in MVP.",
                details={
                    "scenario_board_profile": requested_source,
                    "runtime_board_profile": runtime_source,
                },
            )

    seed = plan.setup.get("seed")
    if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int) or seed < 0):
        raise DomainError(
            error_code="SCENARIO_SETUP_INVALID",
            message="Scenario setup seed must be a non-negative integer.",
            explain="The scenario seed is metadata in MVP and must still be structurally valid.",
            details={"seed": seed},
        )


def _advance_to_action_time(context: ScenarioExecutionContext, at_ms: int) -> None:
    target_ns = context.start_ns + (at_ms * _MS_TO_NS)
    if target_ns < context.runtime.now_ns:
        raise DomainError(
            error_code="SCENARIO_TIMELINE_INVALID",
            message="Scenario action targets time before the current runtime clock.",
            explain="Scenario actions are scheduled relative to the scenario start and must not move time backwards.",
            details={"target_ns": target_ns, "runtime_now_ns": context.runtime.now_ns},
        )

    delta_ns = target_ns - context.runtime.now_ns
    if delta_ns <= 0:
        return

    step_result = context.engine.step(context.runtime, delta_ns // _MS_TO_NS)
    _record_batch(context, step_result.events)


def _advance_to_assertion_horizon(
    context: ScenarioExecutionContext,
    assertions: list[ScenarioAssertion],
) -> None:
    max_window_ms = max((_validated_within_ms(assertion.params) or 0 for assertion in assertions), default=0)
    horizon_ns = context.start_ns + (max_window_ms * _MS_TO_NS)
    if horizon_ns <= context.runtime.now_ns:
        return

    step_result = context.engine.step(context.runtime, (horizon_ns - context.runtime.now_ns) // _MS_TO_NS)
    _record_batch(context, step_result.events)


def _execute_action(context: ScenarioExecutionContext, action: ScenarioAction) -> None:
    bus_action, payload = _translate_action(action.action, action.params)
    io_result = context.engine.execute_io(context.runtime, bus_action, payload)
    _record_batch(context, io_result.events)


def _translate_action(action: str, params: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    normalized = action.strip().replace(":", ".").lower()
    if normalized == "fault.inject":
        fault_kind = params.get("fault_kind", params.get("kind"))
        if not isinstance(fault_kind, str) or not fault_kind.strip():
            raise DomainError(
                error_code="SCENARIO_ACTION_INVALID",
                message="fault.inject requires params.kind or params.fault_kind.",
                explain="Fault injection crosses the public engine boundary as fault:inject plus a concrete fault kind.",
                details={"action": action, "params": params},
            )
        payload = dict(params)
        payload["fault_kind"] = fault_kind.strip()
        return "fault:inject", payload

    supported = {
        "gpio.set",
        "gpio.write",
        "gpio.get",
        "gpio.read",
        "uart.send",
        "uart.write",
        "uart.receive",
        "uart.read",
        "i2c.transact",
    }
    if normalized not in supported:
        supported_actions = sorted([*supported, "fault.inject"])
        raise DomainError(
            error_code="SCENARIO_ACTION_NOT_SUPPORTED",
            message=f"Unsupported scenario action: {action}",
            explain="MVP scenario execution only supports GPIO, UART, I2C, and fault injection actions.",
            details={"action": action, "supported_actions": supported_actions},
        )
    return normalized.replace(".", ":"), dict(params)


def _record_batch(context: ScenarioExecutionContext, events: list[SimEvent]) -> None:
    diagnosis = context.diagnosis.analyze(context.runtime, events)
    context.artifacts.append_runtime_data(
        context.runtime,
        step_events=events,
        diagnosis=diagnosis,
    )
    context.events.extend(events)
    context.facts.extend(diagnosis.facts)
    context.explanations.extend(diagnosis.explanations)
    context.explanation_timeline.append((context.runtime.now_ns, list(diagnosis.explanations)))
    context.state_timeline.append((context.runtime.now_ns, deepcopy(context.runtime.device_state)))


def _evaluate_assertion(
    context: ScenarioExecutionContext,
    assertion: ScenarioAssertion,
) -> ScenarioAssertionResult:
    if assertion.kind == "expect_event":
        return _evaluate_event_assertion(context, assertion.params)
    if assertion.kind == "expect_diagnosis":
        return _evaluate_diagnosis_assertion(context, assertion.params)
    if assertion.kind == "expect_state":
        return _evaluate_state_assertion(context, assertion.params)
    return ScenarioAssertionResult(
        kind=assertion.kind,
        status="fail",
        details={"reason": "unsupported_assertion_kind", "params": assertion.params},
    )


def _evaluate_event_assertion(
    context: ScenarioExecutionContext,
    params: dict[str, Any],
) -> ScenarioAssertionResult:
    deadline_ns = _deadline_ns(context.start_ns, params)
    matched_events: list[SimEvent] = []
    for event in context.events:
        if event.t_virtual_ns > deadline_ns:
            continue
        if not _matches_expected_fields(event.model_dump(), params, ignored_keys={"within_ms", "payload_contains"}):
            continue
        payload_contains = params.get("payload_contains")
        if payload_contains is not None and not _contains_value(event.payload, payload_contains):
            continue
        matched_events.append(event)

    if matched_events:
        return ScenarioAssertionResult(
            kind="expect_event",
            status="pass",
            details={
                "matched_event_ids": [event.event_id for event in matched_events],
                "within_ms": params.get("within_ms"),
                "expected": params,
            },
        )

    return ScenarioAssertionResult(
        kind="expect_event",
        status="fail",
        details={
            "reason": "event_not_found",
            "within_ms": params.get("within_ms"),
            "expected": params,
            "observed_event_types": [event.type for event in context.events],
        },
    )


def _evaluate_diagnosis_assertion(
    context: ScenarioExecutionContext,
    params: dict[str, Any],
) -> ScenarioAssertionResult:
    deadline_ns = _deadline_ns(context.start_ns, params)
    visible_events = [event for event in context.events if event.t_virtual_ns <= deadline_ns]
    visible_event_ids = {event.event_id for event in visible_events}
    visible_facts = [
        fact
        for fact in context.facts
        if not fact.source_events or all(event_id in visible_event_ids for event_id in fact.source_events)
    ]
    visible_explanations = [
        explanation
        for timestamp_ns, batch in context.explanation_timeline
        if timestamp_ns <= deadline_ns
        for explanation in batch
    ]
    haystack = "\n".join(
        [
            *[str(fact.model_dump()) for fact in visible_facts],
            *[str(explanation.model_dump()) for explanation in visible_explanations],
        ]
    ).lower()

    needle = params.get("hypothesis_contains", params.get("contains"))
    if isinstance(needle, str) and needle.strip():
        matched = needle.strip().lower() in haystack
        return ScenarioAssertionResult(
            kind="expect_diagnosis",
            status="pass" if matched else "fail",
            details={
                "within_ms": params.get("within_ms"),
                "contains": needle,
                "visible_fact_ids": [fact.fact_id for fact in visible_facts],
                "visible_explanation_count": len(visible_explanations),
            },
        )

    matched = any(_matches_expected_fields(fact.model_dump(), params, ignored_keys={"within_ms"}) for fact in visible_facts)
    return ScenarioAssertionResult(
        kind="expect_diagnosis",
        status="pass" if matched else "fail",
        details={
            "within_ms": params.get("within_ms"),
            "expected": params,
            "visible_fact_ids": [fact.fact_id for fact in visible_facts],
        },
    )


def _evaluate_state_assertion(
    context: ScenarioExecutionContext,
    params: dict[str, Any],
) -> ScenarioAssertionResult:
    deadline_ns = _deadline_ns(context.start_ns, params)
    snapshot = _state_at_or_before(context.state_timeline, deadline_ns)
    path = params.get("path")
    value: Any = snapshot
    path_parts: list[str] = []
    if isinstance(path, str) and path.strip():
        path_parts = [part for part in path.strip().split(".") if part]
        value = _read_path(snapshot, path_parts)

    exists = params.get("exists")
    if exists is not None:
        present = value is not _MISSING
        matched = bool(exists) == present
        return ScenarioAssertionResult(
            kind="expect_state",
            status="pass" if matched else "fail",
            details={
                "path": path_parts,
                "exists": exists,
                "actual_present": present,
            },
        )

    if value is _MISSING:
        return ScenarioAssertionResult(
            kind="expect_state",
            status="fail",
            details={"reason": "state_path_not_found", "path": path_parts},
        )

    if "equals" in params:
        matched = value == params["equals"]
        return ScenarioAssertionResult(
            kind="expect_state",
            status="pass" if matched else "fail",
            details={
                "path": path_parts,
                "expected": params["equals"],
                "actual": value,
            },
        )

    if "contains" in params:
        matched = _contains_value(value, params["contains"])
        return ScenarioAssertionResult(
            kind="expect_state",
            status="pass" if matched else "fail",
            details={
                "path": path_parts,
                "contains": params["contains"],
                "actual": value,
            },
        )

    matched = _matches_expected_fields(value, params, ignored_keys={"within_ms", "path"})
    return ScenarioAssertionResult(
        kind="expect_state",
        status="pass" if matched else "fail",
        details={
            "path": path_parts,
            "expected": {key: value for key, value in params.items() if key not in {"within_ms", "path"}},
            "actual": value,
        },
    )


def _build_summary(
    passed: bool,
    assertion_results: list[ScenarioAssertionResult],
    context: ScenarioExecutionContext,
) -> str:
    failed = [item.kind for item in assertion_results if item.status != "pass"]
    summary = (
        f"Scenario {'passed' if passed else 'failed'} with {len(assertion_results)} assertion(s), "
        f"{len(context.events)} event(s), {len(context.facts)} fact(s), and "
        f"{len(context.explanations)} explanation(s)."
    )
    if failed:
        summary += f" Failed assertions: {', '.join(failed)}."
    return summary


def _deadline_ns(start_ns: int, params: dict[str, Any]) -> int:
    within_ms = _validated_within_ms(params)
    if within_ms is None:
        return 2**63 - 1
    return start_ns + (within_ms * _MS_TO_NS)


def _validated_within_ms(params: dict[str, Any]) -> int | None:
    within_ms = params.get("within_ms")
    if within_ms is None:
        return None
    if isinstance(within_ms, bool) or not isinstance(within_ms, int) or within_ms < 0:
        raise DomainError(
            error_code="SCENARIO_ASSERTION_INVALID",
            message="Assertion within_ms must be a non-negative integer.",
            explain="Assertion time windows are expressed in integer milliseconds from scenario start.",
            details={"within_ms": within_ms},
        )
    return within_ms


def _matches_expected_fields(
    actual: Any,
    expected: dict[str, Any],
    *,
    ignored_keys: set[str],
) -> bool:
    if not isinstance(actual, dict):
        return actual == expected
    for key, expected_value in expected.items():
        if key in ignored_keys:
            continue
        if actual.get(key) != expected_value:
            return False
    return True


def _contains_value(actual: Any, expected_fragment: Any) -> bool:
    if isinstance(expected_fragment, str):
        return expected_fragment.lower() in str(actual).lower()
    if isinstance(actual, list):
        return expected_fragment in actual
    if isinstance(actual, dict):
        return expected_fragment in actual.keys() or expected_fragment in actual.values()
    return actual == expected_fragment


def _state_at_or_before(
    timeline: list[tuple[int, dict[str, Any]]],
    deadline_ns: int,
) -> dict[str, Any]:
    selected = timeline[0][1]
    for timestamp_ns, state in timeline:
        if timestamp_ns <= deadline_ns:
            selected = state
        else:
            break
    return deepcopy(selected)


def _read_path(data: Any, path_parts: list[str]) -> Any:
    value = data
    for part in path_parts:
        if isinstance(value, dict):
            if part not in value:
                return _MISSING
            value = value[part]
            continue
        if isinstance(value, list) and part.isdigit():
            index = int(part)
            if index >= len(value):
                return _MISSING
            value = value[index]
            continue
        return _MISSING
    return value
