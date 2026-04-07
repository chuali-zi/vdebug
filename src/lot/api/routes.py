from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, status

from lot.api.error_mapper import map_domain_error
from lot.api.facade import ApiFacade
from lot.api.models import (
    CreateSessionRequest,
    ErrorEnvelope,
    ExecuteIoRequest,
    RunScenarioRequest,
    StepSessionRequest,
    SuccessEnvelope,
)
from lot.contracts.errors import DomainError


def _request_id() -> str:
    return f"req-{uuid4()}"


def build_api_router(facade: ApiFacade) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["mvp"])

    @router.get(
        "/capabilities",
        response_model=SuccessEnvelope,
        responses={400: {"model": ErrorEnvelope}, 500: {"model": ErrorEnvelope}},
    )
    def get_capabilities() -> SuccessEnvelope | ErrorEnvelope:
        request_id = _request_id()
        try:
            return SuccessEnvelope(request_id=request_id, data=facade.get_capabilities())
        except DomainError as error:
            return map_domain_error(request_id, error)

    @router.post(
        "/sessions",
        response_model=SuccessEnvelope,
        status_code=status.HTTP_201_CREATED,
        responses={400: {"model": ErrorEnvelope}, 500: {"model": ErrorEnvelope}},
    )
    def create_session(payload: CreateSessionRequest) -> SuccessEnvelope | ErrorEnvelope:
        request_id = _request_id()
        try:
            return SuccessEnvelope(request_id=request_id, data=facade.create_session(payload.model_dump()))
        except DomainError as error:
            return map_domain_error(request_id, error)

    @router.post(
        "/sessions/{session_id}/step",
        response_model=SuccessEnvelope,
        responses={400: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}},
    )
    def step_session(session_id: str, payload: StepSessionRequest) -> SuccessEnvelope | ErrorEnvelope:
        request_id = _request_id()
        try:
            return SuccessEnvelope(
                request_id=request_id,
                data=facade.step_session(session_id, payload.model_dump()),
            )
        except DomainError as error:
            return map_domain_error(request_id, error)

    @router.post(
        "/sessions/{session_id}/io/{bus_action}",
        response_model=SuccessEnvelope,
        responses={400: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}},
    )
    def execute_io(
        session_id: str,
        bus_action: str,
        payload: ExecuteIoRequest,
    ) -> SuccessEnvelope | ErrorEnvelope:
        request_id = _request_id()
        try:
            return SuccessEnvelope(
                request_id=request_id,
                data=facade.execute_io(session_id, bus_action, payload.model_dump()),
            )
        except DomainError as error:
            return map_domain_error(request_id, error)

    @router.get(
        "/sessions/{session_id}/state",
        response_model=SuccessEnvelope,
        responses={404: {"model": ErrorEnvelope}},
    )
    def get_state(session_id: str) -> SuccessEnvelope | ErrorEnvelope:
        request_id = _request_id()
        try:
            return SuccessEnvelope(request_id=request_id, data=facade.get_state(session_id))
        except DomainError as error:
            return map_domain_error(request_id, error)

    @router.post(
        "/sessions/{session_id}/scenario:run",
        response_model=SuccessEnvelope,
        responses={400: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}},
    )
    def run_scenario(session_id: str, payload: RunScenarioRequest) -> SuccessEnvelope | ErrorEnvelope:
        request_id = _request_id()
        try:
            return SuccessEnvelope(
                request_id=request_id,
                data=facade.run_scenario(session_id, payload.model_dump()),
            )
        except DomainError as error:
            return map_domain_error(request_id, error)

    return router
