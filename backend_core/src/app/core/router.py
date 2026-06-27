from fastapi import APIRouter, Query

from app.core.schemas import HealthResponse, InternalHealthResponse
from app.core.service import HealthService

router = APIRouter(tags=["Infraestrutura"])
service = HealthService()


@router.get("/health", response_model=HealthResponse, summary="Verifica disponibilidade da API")
async def health() -> HealthResponse:
    return service.status()


@router.get(
    "/internal/health",
    response_model=InternalHealthResponse,
    summary="Verifica API e, opcionalmente, banco de dados",
)
async def internal_health(
    check_database: bool = Query(default=False),
) -> InternalHealthResponse:
    return await service.internal_status(check_database=check_database)
