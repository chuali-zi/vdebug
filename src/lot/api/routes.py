from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Request, status

from lot.api.error_mapper import request_id_from_request
from lot.api.facade import ApiFacade
from lot.api.models import (
    CreateSessionRequest,
    ErrorEnvelope,
    ExecuteIoRequest,
    RunScenarioRequest,
    StepSessionRequest,
    SuccessEnvelope,
)

BusSegment = Annotated[str, Path(pattern=r"^[a-z0-9_]+$")]
ActionSegment = Annotated[str, Path(pattern=r"^[a-z0-9_]+$")]
SessionIdSegment = Annotated[str, Path(min_length=1)]


def build_api_router(facade: ApiFacade) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["mvp"])

    @router.get(
        "/capabilities",
        response_model=SuccessEnvelope,
        responses={400: {"model": ErrorEnvelope}, 500: {"model": ErrorEnvelope}},
    )
    def get_capabilities(request: Request) -> SuccessEnvelope:
        return SuccessEnvelope(
            request_id=request_id_from_request(request),
            data=facade.get_capabilities(),
        )

    @router.post(
        "/sessions",
        response_model=SuccessEnvelope,
        status_code=status.HTTP_201_CREATED,
        responses={400: {"model": ErrorEnvelope}, 500: {"model": ErrorEnvelope}},
    )
    def create_session(request: Request, payload: CreateSessionRequest) -> SuccessEnvelope:
        return SuccessEnvelope(
            request_id=request_id_from_request(request),
            data=facade.create_session(payload.model_dump()),
        )

    @router.post(
        "/sessions/{session_id}/step",
        response_model=SuccessEnvelope,
        responses={400: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}, 500: {"model": ErrorEnvelope}},
    )
    def step_session(
        request: Request,
        session_id: SessionIdSegment,
        payload: StepSessionRequest,
    ) -> SuccessEnvelope:
        return SuccessEnvelope(
            request_id=request_id_from_request(request),
            data=facade.step_session(session_id, payload.model_dump()),
        )

    @router.post(
        "/sessions/{session_id}/io/{bus}:{action}",
        response_model=SuccessEnvelope,
        responses={400: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}, 500: {"model": ErrorEnvelope}},
    )
    def execute_io(
        request: Request,
        session_id: SessionIdSegment,
        bus: BusSegment,
        action: ActionSegment,
        payload: ExecuteIoRequest,
    ) -> SuccessEnvelope:
        return SuccessEnvelope(
            request_id=request_id_from_request(request),
            data=facade.execute_io(session_id, f"{bus}:{action}", payload.model_dump()),
        )

    @router.get(
        "/sessions/{session_id}/state",
        response_model=SuccessEnvelope,
        responses={404: {"model": ErrorEnvelope}, 500: {"model": ErrorEnvelope}},
    )
    def get_state(request: Request, session_id: SessionIdSegment) -> SuccessEnvelope:
        return SuccessEnvelope(
            request_id=request_id_from_request(request),
            data=facade.get_state(session_id),
        )

    @router.post(
        "/sessions/{session_id}/scenario:run",
        response_model=SuccessEnvelope,
        responses={400: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}, 500: {"model": ErrorEnvelope}},
    )
    def run_scenario(
        request: Request,
        session_id: SessionIdSegment,
        payload: RunScenarioRequest,
    ) -> SuccessEnvelope:
        return SuccessEnvelope(
            request_id=request_id_from_request(request),
            data=facade.run_scenario(session_id, payload.model_dump()),
        )

    return router
