from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from lot.contracts.errors import DomainError
from lot.contracts.models import ScenarioAction, ScenarioAssertion, ScenarioPlan


def load_plan_from_source(*, scenario_path: str | None, scenario_text: str | None) -> ScenarioPlan:
    has_path = bool(scenario_path)
    has_text = bool(scenario_text)
    if has_path == has_text:
        raise DomainError(
            error_code="SCENARIO_SOURCE_INVALID",
            message="Provide exactly one of scenario_path or scenario_text.",
            explain="Scenario parsing needs a single YAML source so the plan source stays unambiguous.",
            details={"has_path": has_path, "has_text": has_text},
        )

    source, raw = _load_raw_payload(
        scenario_path=scenario_path,
        scenario_text=scenario_text,
    )
    if not isinstance(raw, dict):
        raise _dsl_error(
            "Scenario root must be a mapping.",
            path=["$"],
            details={"received_type": type(raw).__name__},
        )

    version = raw.get("version", "v1alpha1")
    if not isinstance(version, str) or not version.strip():
        raise _dsl_error(
            "Scenario version must be a non-empty string.",
            path=["version"],
            details={"value": version},
        )

    setup = raw.get("setup", {})
    if setup is None:
        setup = {}
    if not isinstance(setup, dict):
        raise _dsl_error(
            "Scenario setup must be a mapping.",
            path=["setup"],
            details={"received_type": type(setup).__name__},
        )

    stimulus_raw = raw.get("stimulus", [])
    if stimulus_raw is None:
        stimulus_raw = []
    if not isinstance(stimulus_raw, list):
        raise _dsl_error(
            "Scenario stimulus must be a list.",
            path=["stimulus"],
            details={"received_type": type(stimulus_raw).__name__},
        )

    assertions_raw = raw.get("assertions", [])
    if assertions_raw is None:
        assertions_raw = []
    if not isinstance(assertions_raw, list):
        raise _dsl_error(
            "Scenario assertions must be a list.",
            path=["assertions"],
            details={"received_type": type(assertions_raw).__name__},
        )

    return ScenarioPlan(
        source=source,
        version=version.strip(),
        setup=setup,
        stimulus=sorted(
            [_normalize_action(item, index) for index, item in enumerate(stimulus_raw)],
            key=lambda action: action.at_ms,
        ),
        assertions=[_normalize_assertion(item, index) for index, item in enumerate(assertions_raw)],
    )


def _load_raw_payload(*, scenario_path: str | None, scenario_text: str | None) -> tuple[str, Any]:
    source = "inline://scenario"
    try:
        if scenario_path:
            source = scenario_path
            text = Path(scenario_path).read_text(encoding="utf-8")
        else:
            text = scenario_text or ""
        return source, yaml.safe_load(text) or {}
    except OSError as exc:
        raise DomainError(
            error_code="SCENARIO_SOURCE_READ_ERROR",
            message=f"Failed to read scenario source: {source}",
            explain="The scenario module could not open the requested YAML source.",
            details={"source": source, "reason": str(exc)},
        ) from exc
    except yaml.YAMLError as exc:
        raise DomainError(
            error_code="SCENARIO_PARSE_ERROR",
            message="Scenario YAML is invalid.",
            explain="Fix the YAML syntax before retrying the scenario run.",
            details={"source": source, "reason": str(exc)},
        ) from exc


def _normalize_action(raw: Any, index: int) -> ScenarioAction:
    path = ["stimulus", index]
    if not isinstance(raw, dict):
        raise _dsl_error(
            "Stimulus item must be a mapping.",
            path=path,
            details={"received_type": type(raw).__name__},
        )

    at_ms = raw.get("at_ms")
    if isinstance(at_ms, bool) or not isinstance(at_ms, int) or at_ms < 0:
        raise _dsl_error(
            "Stimulus at_ms must be a non-negative integer.",
            path=[*path, "at_ms"],
            details={"value": at_ms},
        )

    action = raw.get("action")
    if not isinstance(action, str) or not action.strip():
        raise _dsl_error(
            "Stimulus action must be a non-empty string.",
            path=[*path, "action"],
            details={"value": action},
        )

    params = raw.get("params", {})
    if params is None:
        params = {}
    if not isinstance(params, dict):
        raise _dsl_error(
            "Stimulus params must be a mapping.",
            path=[*path, "params"],
            details={"received_type": type(params).__name__},
        )

    return ScenarioAction(
        at_ms=at_ms,
        action=action.strip().replace(":", "."),
        params=dict(params),
    )


def _normalize_assertion(raw: Any, index: int) -> ScenarioAssertion:
    path = ["assertions", index]
    if not isinstance(raw, dict):
        raise _dsl_error(
            "Assertion item must be a mapping.",
            path=path,
            details={"received_type": type(raw).__name__},
        )

    if "kind" in raw:
        kind = raw.get("kind")
        params = raw.get("params", {})
    else:
        supported_kinds = [key for key in ("expect_event", "expect_diagnosis", "expect_state") if key in raw]
        if len(supported_kinds) != 1:
            raise _dsl_error(
                "Assertion must declare exactly one supported expectation.",
                path=path,
                details={"supported_keys": supported_kinds, "raw_keys": sorted(raw.keys())},
            )
        kind = supported_kinds[0]
        params = raw.get(kind, {})

    if not isinstance(kind, str) or kind not in {"expect_event", "expect_diagnosis", "expect_state"}:
        raise _dsl_error(
            "Unsupported assertion kind.",
            path=[*path, "kind"],
            details={"kind": kind},
        )

    if params is None:
        params = {}
    if not isinstance(params, dict):
        raise _dsl_error(
            "Assertion params must be a mapping.",
            path=[*path, "params"],
            details={"received_type": type(params).__name__},
        )

    normalized_params = dict(params)
    if "within_ms" in raw:
        within_ms = raw.get("within_ms")
        if isinstance(within_ms, bool) or not isinstance(within_ms, int) or within_ms < 0:
            raise _dsl_error(
                "Assertion within_ms must be a non-negative integer.",
                path=[*path, "within_ms"],
                details={"value": within_ms},
            )
        normalized_params["within_ms"] = within_ms

    return ScenarioAssertion(kind=kind, params=normalized_params)


def _dsl_error(message: str, *, path: list[object], details: dict[str, object]) -> DomainError:
    return DomainError(
        error_code="SCENARIO_DSL_INVALID",
        message=message,
        explain="Scenario DSL must follow the stable setup/stimulus/assertions structure.",
        details={"path": path, **details},
    )
