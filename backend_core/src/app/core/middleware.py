import logging
import time
from uuid import UUID, uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.logging import bind_request_id, reset_request_id

logger = logging.getLogger("app.requests")


def _request_id_from_header(value: str | None) -> str:
    if not value:
        return str(uuid4())
    try:
        return str(UUID(value))
    except ValueError:
        return str(uuid4())


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = _request_id_from_header(request.headers.get("X-Request-ID"))
        request.state.request_id = request_id
        token = bind_request_id(request_id)
        started_at = time.perf_counter()
        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - started_at) * 1000
            logger.info(
                "%s %s status=%s duration_ms=%.2f",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
            )
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            reset_request_id(token)
