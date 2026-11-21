from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def error_body(
    code: str, message: str, details: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details}}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code_message = {
            400: ("bad_request", "The request could not be processed."),
            404: ("not_found", "The requested resource was not found."),
            409: ("conflict", "The task is not in a state that allows this action."),
            413: ("request_too_large", "The request body is too large."),
            429: ("rate_limited", "Too many tasks were submitted. Try again shortly."),
            503: ("service_unavailable", "A required service is temporarily unavailable."),
        }.get(exc.status_code, ("request_error", "The request could not be processed."))
        if isinstance(exc.detail, dict):
            body = error_body(
                exc.detail.get("code", code_message[0]), exc.detail.get("message", code_message[1])
            )
        else:
            body = error_body(*code_message)
        return JSONResponse(body, status_code=exc.status_code, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"loc": list(item["loc"]), "msg": item["msg"], "type": item["type"]}
            for item in exc.errors()
        ]
        return JSONResponse(
            error_body("validation_error", "The request contains invalid fields.", details), 422
        )

    @app.exception_handler(Exception)
    async def unexpected_error(_: Request, __: Exception) -> JSONResponse:
        return JSONResponse(
            error_body("internal_error", "The server could not complete this request."), 500
        )
