from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from lot.contracts.errors import DomainError
from lot.contracts.models import BoardProfile, SessionRecord, SessionStatus
from lot.session.models import RuntimeContext

_SUPPORTED_MODE = "device_sim"
_TERMINAL_STATUSES: set[SessionStatus] = {"finished", "error"}
_ALLOWED_TRANSITIONS: dict[SessionStatus, set[SessionStatus]] = {
    "active": {"active", "finished", "error"},
    "finished": {"finished"},
    "error": {"error"},
}


@dataclass(slots=True)
class _SessionRepository:
    """Persists session metadata and terminal snapshots as JSON."""

    root_dir: Path

    def _session_dir(self, session_id: str) -> Path:
        session_dir = self.root_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir

    def save_session(self, session: SessionRecord) -> None:
        target = self._session_dir(session.session_id) / "session.json"
        target.write_text(
            json.dumps(session.model_dump(mode="json"), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def save_final_snapshot(self, session: SessionRecord, runtime: RuntimeContext) -> None:
        target = self._session_dir(session.session_id) / "final_snapshot.json"
        target.write_text(
            json.dumps(
                {
                    "session": session.model_dump(mode="json"),
                    "runtime": runtime.model_dump(mode="json"),
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )


@dataclass(slots=True)
class SessionServiceStub:
    """Owns session metadata, runtime registration, and lifecycle state."""

    storage_dir: Path | None = None
    _sessions: dict[str, SessionRecord] = field(default_factory=dict)
    _runtimes: dict[str, RuntimeContext] = field(default_factory=dict)
    _repository: _SessionRepository = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._repository = _SessionRepository(
            root_dir=self.storage_dir or Path.cwd() / "runtime_sessions"
        )

    def create_session(self, board_profile: BoardProfile, seed: int, mode: str) -> SessionRecord:
        self._validate_mode(mode)
        self._validate_seed(seed)

        session = SessionRecord(
            board_profile=board_profile.source_path,
            seed=seed,
            mode=mode,
        )
        runtime = RuntimeContext.from_board_profile(
            session_id=session.session_id,
            board_profile=board_profile,
        )
        self._sessions[session.session_id] = session
        self._runtimes[session.session_id] = runtime
        self._repository.save_session(session)
        return session

    def get_session(self, session_id: str) -> SessionRecord:
        session = self._sessions.get(session_id)
        if session is None:
            raise DomainError(
                error_code="SESSION_NOT_FOUND",
                message=f"Session not found: {session_id}",
                explain="The requested session_id is unknown to the session module.",
            )
        return session

    def get_runtime(self, session_id: str) -> RuntimeContext:
        runtime = self._runtimes.get(session_id)
        if runtime is None:
            raise DomainError(
                error_code="RUNTIME_NOT_FOUND",
                message=f"Runtime not found: {session_id}",
                explain="Session exists without runtime, or runtime bootstrap is incomplete.",
            )
        return runtime

    def require_runtime(self, session_id: str) -> RuntimeContext:
        return self.get_runtime(session_id)

    def save_runtime(self, runtime: RuntimeContext) -> None:
        session = self.get_session(runtime.session_id)
        self._runtimes[runtime.session_id] = runtime

        if runtime.last_error is not None and session.status == "active":
            session = self._set_status_record(session, "error")

        if session.status in _TERMINAL_STATUSES:
            self._repository.save_final_snapshot(session, runtime)

    def set_status(self, session_id: str, status: SessionStatus) -> None:
        session = self.get_session(session_id)
        self._set_status_record(session, status)

    def close(self, session_id: str) -> None:
        session = self.get_session(session_id)
        updated = self._set_status_record(session, "finished")
        runtime = self._runtimes.get(session_id)
        if runtime is not None:
            self._repository.save_final_snapshot(updated, runtime)

    def get(self, session_id: str) -> dict:
        return self.get_session(session_id).model_dump(mode="json")

    def _set_status_record(self, session: SessionRecord, status: SessionStatus) -> SessionRecord:
        self._validate_status(status)
        allowed = _ALLOWED_TRANSITIONS[session.status]
        if status not in allowed:
            raise DomainError(
                error_code="INVALID_SESSION_STATUS_TRANSITION",
                message=f"Cannot change session {session.session_id} from {session.status} to {status}.",
                explain="Session status transitions must be explicit and follow the MVP lifecycle.",
                observations=[
                    f"Current status: {session.status}",
                    f"Requested status: {status}",
                ],
                next_actions=[
                    "Only transition active sessions to finished or error.",
                    "Create a new session for a new execution.",
                ],
            )

        if session.status == status:
            self._repository.save_session(session)
            return session

        updated = session.model_copy(update={"status": status})
        self._sessions[session.session_id] = updated
        self._repository.save_session(updated)

        runtime = self._runtimes.get(session.session_id)
        if runtime is not None and status in _TERMINAL_STATUSES:
            self._repository.save_final_snapshot(updated, runtime)

        return updated

    def _validate_mode(self, mode: str) -> None:
        if mode != _SUPPORTED_MODE:
            raise DomainError(
                error_code="MODE_NOT_SUPPORTED",
                message=f"Unsupported mode: {mode}",
                explain="MVP only supports Mode A / device_sim.",
                next_actions=["Retry with mode=device_sim."],
            )

    def _validate_seed(self, seed: int) -> None:
        if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
            raise DomainError(
                error_code="INVALID_SESSION_SEED",
                message=f"Invalid session seed: {seed!r}",
                explain="Session seed must be a non-negative integer.",
                next_actions=["Retry with a non-negative integer seed."],
            )

    def _validate_status(self, status: SessionStatus) -> None:
        if status not in _ALLOWED_TRANSITIONS:
            raise DomainError(
                error_code="INVALID_SESSION_STATUS",
                message=f"Unsupported session status: {status}",
                explain="Session status must stay within the MVP lifecycle states.",
                next_actions=["Use one of: active, finished, error."],
            )
