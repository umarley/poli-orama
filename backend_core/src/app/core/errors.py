import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppError(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


class BusinessRuleError(AppError):
    def __init__(
        self, message: str, *, code: str = "business_rule_error", details: Any = None
    ) -> None:
        super().__init__(
            status_code=422,
            code=code,
            message=message,
            details=details,
        )


class ResourceNotFoundError(AppError):
    def __init__(self, resource: str, identifier: Any) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            code="resource_not_found",
            message=f"{resource} nao encontrado.",
            details={"identifier": identifier},
        )


class DatabaseUnavailableError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="database_unavailable",
            message="Banco de dados indisponivel.",
            details=None,
        )


def _error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: Any,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    response = JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(
            {
                "code": code,
                "message": message,
                "details": details,
                "request_id": request_id,
            }
        ),
    )
    if request_id:
        response.headers["X-Request-ID"] = request_id
    return response


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return _error_response(
            request,
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            details=exc.details,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return _error_response(
            request,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="validation_error",
            message="Dados da requisicao invalidos.",
            details=exc.errors(),
        )

    @app.exception_handler(HTTPException)
    async def handle_http_error(request: Request, exc: HTTPException) -> JSONResponse:
        message = exc.detail if isinstance(exc.detail, str) else "Erro HTTP."
        details = None if isinstance(exc.detail, str) else exc.detail
        return _error_response(
            request,
            status_code=exc.status_code,
            code="http_error",
            message=message,
            details=details,
        )

    @app.exception_handler(Exception)
    async def handle_internal_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Erro interno nao tratado", exc_info=exc)
        return _error_response(
            request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="internal_error",
            message="Erro interno do servidor.",
            details=None,
        )
