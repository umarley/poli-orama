from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session
from app.core.pagination import ListParams, Page, list_params
from app.tenants.access import RequestActor, require_actor, require_saas_admin, require_tenant_admin
from app.tenants.repository import CommercialRepository, TenantRepository
from app.tenants.schemas import (
    PlanUsageResponse,
    TenantConfiguracaoResponse,
    TenantConfiguracaoUpdate,
    TenantCreate,
    TenantResponse,
    TenantUpdate,
)
from app.tenants.service import CommercialService, TenantManagementService

router = APIRouter(tags=["Tenants"])


def get_tenant_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TenantManagementService:
    return TenantManagementService(TenantRepository(session))


def get_commercial_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CommercialService:
    return CommercialService(CommercialRepository(session), get_settings())


@router.get("/tenants", response_model=Page[TenantResponse], summary="Lista tenants")
async def list_tenants(
    params: Annotated[ListParams, Depends(list_params)],
    service: Annotated[TenantManagementService, Depends(get_tenant_service)],
    _: Annotated[int, Depends(require_saas_admin)],
    tenant_status: str | None = Query(default=None, alias="status", max_length=20),
    plano_id: int | None = Query(default=None, ge=1),
) -> Page[TenantResponse]:
    return await service.list(params, tenant_status, plano_id)


@router.post(
    "/tenants",
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cria tenant com configuracao padrao",
)
async def create_tenant(
    payload: TenantCreate,
    service: Annotated[TenantManagementService, Depends(get_tenant_service)],
    actor_id: Annotated[int, Depends(require_saas_admin)],
) -> TenantResponse:
    return await service.create(payload, actor_id)


@router.get("/tenants/{tenant_id}", response_model=TenantResponse, summary="Busca tenant por ID")
async def get_tenant(
    service: Annotated[TenantManagementService, Depends(get_tenant_service)],
    _: Annotated[int, Depends(require_saas_admin)],
    tenant_id: int = Path(ge=1),
) -> TenantResponse:
    return await service.get_by_id(tenant_id)


@router.patch(
    "/tenants/{tenant_id}", response_model=TenantResponse, summary="Atualiza dados do tenant"
)
async def update_tenant(
    payload: TenantUpdate,
    service: Annotated[TenantManagementService, Depends(get_tenant_service)],
    actor_id: Annotated[int, Depends(require_saas_admin)],
    tenant_id: int = Path(ge=1),
) -> TenantResponse:
    return await service.update(tenant_id, payload, actor_id)


@router.post(
    "/tenants/{tenant_id}/ativar",
    response_model=TenantResponse,
    summary="Ativa tenant manualmente",
)
async def activate_tenant(
    service: Annotated[TenantManagementService, Depends(get_tenant_service)],
    actor_id: Annotated[int, Depends(require_saas_admin)],
    tenant_id: int = Path(ge=1),
) -> TenantResponse:
    return await service.activate(tenant_id, actor_id)


@router.post(
    "/tenants/suspender-inadimplentes",
    summary="Suspende tenants marcados como inadimplentes",
)
async def suspend_overdue_tenants(
    commercial: Annotated[CommercialService, Depends(get_commercial_service)],
    _: Annotated[int, Depends(require_saas_admin)],
) -> dict[str, int]:
    count = await commercial.repository.suspend_overdue()
    return {"tenants_suspensos": count}


@router.get("/me/tenant", response_model=TenantResponse, summary="Retorna o tenant atual")
async def get_current_tenant(
    actor: Annotated[RequestActor, Depends(require_actor)],
    service: Annotated[TenantManagementService, Depends(get_tenant_service)],
) -> TenantResponse:
    return await service.get_by_id(actor.tenant_id)


@router.get(
    "/me/tenant/configuracao",
    response_model=TenantConfiguracaoResponse,
    summary="Retorna a configuracao do tenant atual",
)
async def get_current_tenant_configuration(
    actor: Annotated[RequestActor, Depends(require_actor)],
    service: Annotated[TenantManagementService, Depends(get_tenant_service)],
) -> TenantConfiguracaoResponse:
    return await service.get_configuration(actor.tenant_id)


@router.patch(
    "/me/tenant/configuracao",
    response_model=TenantConfiguracaoResponse,
    summary="Atualiza a configuracao do tenant atual",
)
async def update_current_tenant_configuration(
    payload: TenantConfiguracaoUpdate,
    actor: Annotated[RequestActor, Depends(require_tenant_admin)],
    service: Annotated[TenantManagementService, Depends(get_tenant_service)],
) -> TenantConfiguracaoResponse:
    return await service.update_configuration(actor.tenant_id, payload)


@router.get(
    "/me/tenant/assinatura",
    response_model=PlanUsageResponse,
    summary="Retorna assinatura, limites e uso atual",
)
async def get_current_subscription(
    actor: Annotated[RequestActor, Depends(require_actor)],
    tenant_service: Annotated[TenantManagementService, Depends(get_tenant_service)],
    commercial: Annotated[CommercialService, Depends(get_commercial_service)],
) -> PlanUsageResponse:
    tenant = await tenant_service.repository.get_by_id(actor.tenant_id)
    assert tenant is not None
    return await commercial.usage(tenant)
