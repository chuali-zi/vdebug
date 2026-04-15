---
name: lot-dev-workflow
description: Understand and modify the LOT MVP codebase with stable module boundaries and contract-first checks. Use when working on LOT, FastAPI routes under /v1, session/board/engine/devices/diagnosis/scenario/artifacts modules, board profiles, scenario DSL, or unittest regression updates.
---

# LOT Development Workflow

## Purpose

Use this skill when implementing or reviewing changes in the LOT MVP (`lot` package) to keep API contracts, runtime behavior, and tests aligned.

## Project Snapshot

- Runtime stack: Python 3.11+, FastAPI, Pydantic v2, PyYAML, uvicorn
- Package root: `src/lot`
- API prefix: `/v1`
- Test framework: `unittest` (`tests/test_*.py`)
- Current architecture emphasis: `device_sim` mode, stable MVP boundaries

## Module Map

- `src/lot/api`: HTTP routes, request/response envelopes, API orchestration
- `src/lot/session`: session lifecycle and runtime context
- `src/lot/board`: board profile loading and validation
- `src/lot/engine`: virtual clock, scheduling, I/O execution
- `src/lot/devices`: GPIO/UART/I2C device plugins and registry
- `src/lot/diagnosis`: events -> facts -> explanations
- `src/lot/scenario`: DSL parser/runner and assertions
- `src/lot/artifacts`: state snapshots and repro bundle export
- `src/lot/contracts`: cross-module data models, errors, protocols

## Default Workflow

1. Confirm target behavior and impacted module boundary first.
2. Make the smallest local change that preserves contracts.
3. Validate API envelope and error code stability if endpoint behavior changes.
4. Run regression tests relevant to touched modules, then run full suite.
5. Report what changed, why, and what verification passed.

## Contract Rules

- Keep success envelope shape stable:
  - `{"ok": true, "request_id": "...", "data": ...}`
- Keep failure envelope shape stable:
  - `{"ok": false, "request_id": "...", "error": {"error_code": "...", ...}}`
- Preserve domain error specificity; do not collapse all failures into generic errors.
- Treat path and payload validation as explicit contract behavior.

## Command Shortcuts

Run from repository root:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

Start API locally:

```bash
python -m uvicorn --app-dir src lot.main:app --reload --host 0.0.0.0 --port 8000
```

## Change Patterns

### API endpoint update

- Touch likely files: `src/lot/api/models.py`, `src/lot/api/routes.py`, `src/lot/api/facade.py`
- Re-check status mapping and envelope consistency in API tests (`tests/test_api.py`)

### Engine/device behavior update

- Touch likely files under `src/lot/engine` and `src/lot/devices`
- Verify no runtime state pollution after failed I/O paths
- Re-run device and engine tests first, then full suite

### Scenario DSL update

- Touch likely files: `src/lot/scenario/parser.py`, `src/lot/scenario/runner.py`, `src/lot/scenario/service.py`
- Ensure invalid DSL returns domain-specific errors (for example `SCENARIO_DSL_INVALID`)

## Response Style For This Project

When presenting results:

- Start with changed files and behavior impact.
- Include concrete verification commands executed.
- Call out contract-sensitive risks (API shape, error codes, state mutation).
- Keep recommendations incremental and MVP-safe.
