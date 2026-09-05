from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.access import get_db_session, require_saas_admin
from app.auth.api_key_service import ApiKeyService
from app.auth.repository import AuthRepository
from app.auth.schemas import ApiKeyCreate, ApiKeyCreatedResponse, ApiKeyResponse
from app.core.pagination import ListParams, Page, list_params

router = APIRouter(tags=["Integracao"])


def get_api_key_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiKeyService:
    return ApiKeyService(AuthRepository(session))


@router.get(
    "/admin/api-keys",
    response_model=Page[ApiKeyResponse],
    summary="Lista chaves de integracao",
)
async def list_api_keys(
    params: Annotated[ListParams, Depends(list_params)],
    service: Annotated[ApiKeyService, Depends(get_api_key_service)],
    _: Annotated[int, Depends(require_saas_admin)],
    tenant_id: int | None = Query(default=None, ge=1),
) -> Page[ApiKeyResponse]:
    return await service.list(params, tenant_id)


@router.post(
    "/admin/api-keys",
    response_model=ApiKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cria chave de integracao para um tenant",
)
async def create_api_key(
    payload: ApiKeyCreate,
    request: Request,
    service: Annotated[ApiKeyService, Depends(get_api_key_service)],
    actor_id: Annotated[int, Depends(require_saas_admin)],
) -> ApiKeyCreatedResponse:
    return await service.create(
        payload,
        actor_id,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


@router.post(
    "/admin/api-keys/{api_key_id}/revogar",
    response_model=ApiKeyResponse,
    summary="Revoga chave de integracao",
)
async def revoke_api_key(
    request: Request,
    service: Annotated[ApiKeyService, Depends(get_api_key_service)],
    actor_id: Annotated[int, Depends(require_saas_admin)],
    api_key_id: int = Path(ge=1),
) -> ApiKeyResponse:
    return await service.revoke(
        api_key_id,
        actor_id,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


def _client_ip(request: Request) -> str | None:
    if request.client is None:
        return None
    return request.client.host.split("%", 1)[0]
