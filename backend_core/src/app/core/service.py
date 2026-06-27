from typing import Literal

from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.core.database import check_database_connection
from app.core.errors import DatabaseUnavailableError
from app.core.schemas import HealthResponse, InternalHealthResponse


class HealthService:
    def status(self) -> HealthResponse:
        settings = get_settings()
        return HealthResponse(
            status="ok",
            app=settings.app_name,
            version=settings.app_version,
            environment=settings.environment,
        )

    async def internal_status(self, *, check_database: bool) -> InternalHealthResponse:
        settings = get_settings()
        database_status: Literal["ok", "not_checked"] = "not_checked"
        if check_database:
            try:
                await check_database_connection()
            except SQLAlchemyError as exc:
                raise DatabaseUnavailableError from exc
            database_status = "ok"
        return InternalHealthResponse(
            status="ok",
            app=settings.app_name,
            version=settings.app_version,
            environment=settings.environment,
            database=database_status,
        )
