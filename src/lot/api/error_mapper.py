from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from lot.api.models import ErrorEnvelope
from lot.contracts.errors import DomainError
from lot.contracts.models import ErrorPayload

_REQUEST_ID_KEY = "request_id"

_ERROR_STATUS_BY_CODE = {
    "BOARD_PROFILE_NOT_FOUND": status.HTTP_400_BAD_REQUEST,
    "INVALID_REQUEST": status.HTTP_400_BAD_REQUEST,
    "MODE_NOT_SUPPORTED": status.HTTP_400_BAD_REQUEST,
    "SCENARIO_SOURCE_REQUIRED": status.HTTP_400_BAD_REQUEST,
    "RUNTIME_NOT_FOUND": status.HTTP_404_NOT_FOUND,
    "SESSION_NOT_FOUND": status.HTTP_404_NOT_FOUND,
    "TODO_NOT_IMPLEMENTED": status.HTTP_501_NOT_IMPLEMENTED,
}


def new_request_id() -> str:
    return f"req-{uuid4()}"


def request_id_from_request(request: Request) -> str:
    request_id = getattr(request.state, _REQUEST_ID_KEY, None)
    if request_id is None:
        request_id = new_request_id()
        setattr(request.state, _REQUEST_ID_KEY, request_id)
    return request_id


def map_domain_error(error: DomainError) -> tuple[int, ErrorEnvelope]:
    status_code = _ERROR_STATUS_BY_CODE.get(error.error_code, status.HTTP_400_BAD_REQUEST)
    envelope = ErrorEnvelope(
        request_id="",
        error=ErrorPayload(
            error_code=error.error_code,
            message=error.message,
            details=error.details,
            explain=error.explain,
            observations=error.observations,
            next_actions=error.next_actions,
        ),
    )
    return status_code, envelope


def build_error_response(request: Request, *, status_code: int, error: ErrorPayload) -> JSONResponse:
    envelope = ErrorEnvelope(request_id=request_id_from_request(request), error=error)
    return JSONResponse(status_code=status_code, content=envelope.model_dump(mode="json"))


def install_api_error_handlers(app: FastAPI) -> None:
    @app.middleware("http")
    async def attach_request_id(request: Request, call_next):
        request_id_from_request(request)
        response = await call_next(request)
        response.headers.setdefault("x-request-id", request_id_from_request(request))
        return response

    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, error: DomainError) -> JSONResponse:
        status_code, envelope = map_domain_error(error)
        envelope.request_id = request_id_from_request(request)
        return JSONResponse(status_code=status_code, content=envelope.model_dump(mode="json"))

    @app.exception_handler(RequestValidationError)
    @app.exception_handler(ValidationError)
    async def handle_validation_error(request: Request, error: Exception) -> JSONResponse:
        details = {"errors": jsonable_encoder(error.errors())} if hasattr(error, "errors") else {}
        return build_error_response(
            request,
            status_code=status.HTTP_400_BAD_REQUEST,
            error=ErrorPayload(
                error_code="INVALID_REQUEST",
                message="Request validation failed.",
                details=details,
                explain="The request did not match the public API schema.",
                next_actions=[
                    "Check required fields and field types.",
                    "Retry with a payload that matches the documented schema.",
                ],
            ),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, _: Exception) -> JSONResponse:
        return build_error_response(
            request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error=ErrorPayload(
                error_code="INTERNAL_SERVER_ERROR",
                message="Unexpected internal error.",
                explain="The platform failed before it could complete the request.",
                next_actions=["Retry the request.", "Inspect server logs for the root cause."],
            ),
        )
