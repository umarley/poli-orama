from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.pagination import ListParams, Page, list_params
from app.tenants.repository import TenantRepository
from app.tenants.schemas import TenantResponse
from app.tenants.service import TenantService

router = APIRouter(prefix="/tenants", tags=["Tenants"])


def get_tenant_service(session: Annotated[AsyncSession, Depends(get_session)]) -> TenantService:
    return TenantService(TenantRepository(session))


@router.get("", response_model=Page[TenantResponse], summary="Lista tenants")
async def list_tenants(
    params: Annotated[ListParams, Depends(list_params)],
    service: Annotated[TenantService, Depends(get_tenant_service)],
    status: str | None = Query(default=None, max_length=20),
) -> Page[TenantResponse]:
    return await service.list(params, status)


@router.get("/{tenant_id}", response_model=TenantResponse, summary="Busca tenant por ID")
async def get_tenant(
    service: Annotated[TenantService, Depends(get_tenant_service)],
    tenant_id: int = Path(ge=1),
) -> TenantResponse:
    return await service.get_by_id(tenant_id)
