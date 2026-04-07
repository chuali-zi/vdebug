from __future__ import annotations

from dataclasses import dataclass, field

from lot.contracts.errors import DomainError
from lot.contracts.models import BoardProfile, SessionRecord
from lot.session.models import RuntimeContext


@dataclass(slots=True)
class SessionServiceStub:
    """Owns session metadata and runtime registration."""

    _sessions: dict[str, SessionRecord] = field(default_factory=dict)
    _runtimes: dict[str, RuntimeContext] = field(default_factory=dict)

    def create_session(self, board_profile: BoardProfile, seed: int, mode: str) -> SessionRecord:
        if mode != "device_sim":
            raise DomainError(
                error_code="MODE_NOT_SUPPORTED",
                message=f"Unsupported mode: {mode}",
                explain="MVP only supports Mode A / device_sim.",
                next_actions=["Retry with mode=device_sim."],
            )

        session = SessionRecord(
            board_profile=board_profile.source_path,
            seed=seed,
            mode=mode,
        )
        runtime = RuntimeContext(
            session_id=session.session_id,
            board_profile=board_profile,
        )
        self._sessions[session.session_id] = session
        self._runtimes[session.session_id] = runtime
        return session

    def get_session(self, session_id: str) -> SessionRecord:
        if session_id not in self._sessions:
            raise DomainError(
                error_code="SESSION_NOT_FOUND",
                message=f"Session not found: {session_id}",
                explain="The requested session_id is unknown to the session module.",
            )
        return self._sessions[session_id]

    def get_runtime(self, session_id: str) -> RuntimeContext:
        if session_id not in self._runtimes:
            raise DomainError(
                error_code="RUNTIME_NOT_FOUND",
                message=f"Runtime not found: {session_id}",
                explain="Session exists without runtime, or runtime bootstrap is incomplete.",
            )
        return self._runtimes[session_id]

    def save_runtime(self, runtime: RuntimeContext) -> None:
        # TODO(session): add lifecycle transitions, status updates, and optional persistence.
        self._runtimes[runtime.session_id] = runtime
