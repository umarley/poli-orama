from ipaddress import ip_address
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.access import (
    RequestActor,
    TerritorialAccess,
    get_db_session,
    get_territorial_access,
    require_permission,
)
from app.mod_comunicacao.repository import ComunicacaoRepository
from app.mod_comunicacao.schemas import (
    CatalogInput,
    CatalogResponse,
    CatalogUpdate,
    InteracaoInput,
    InteracaoResponse,
)
from app.mod_comunicacao.service import ComunicacaoService

router = APIRouter(prefix="/comunicacao", tags=["Comunicacao"])

CatalogName = Literal["tipos-interacao", "canais"]


def get_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ComunicacaoService:
    return ComunicacaoService(ComunicacaoRepository(session))


@router.get("/{catalog}", response_model=list[CatalogResponse])
async def list_catalog(
    catalog: CatalogName,
    actor: Annotated[RequestActor, Depends(require_permission("comunicacao", "visualizar"))],
    service: Annotated[ComunicacaoService, Depends(get_service)],
    incluir_inativos: bool = False,
) -> list[dict]:
    return await service.list_catalog(actor, catalog, incluir_inativos)


@router.post("/{catalog}", response_model=CatalogResponse, status_code=status.HTTP_201_CREATED)
async def create_catalog(
    catalog: CatalogName,
    payload: CatalogInput,
    actor: Annotated[RequestActor, Depends(require_permission("comunicacao", "criar"))],
    service: Annotated[ComunicacaoService, Depends(get_service)],
) -> dict:
    return await service.create_catalog(actor, catalog, payload)


@router.patch("/{catalog}/{item_id}", response_model=CatalogResponse)
async def update_catalog(
    catalog: CatalogName,
    payload: CatalogUpdate,
    actor: Annotated[RequestActor, Depends(require_permission("comunicacao", "editar"))],
    service: Annotated[ComunicacaoService, Depends(get_service)],
    item_id: int = Path(ge=1),
) -> dict:
    return await service.update_catalog(actor, catalog, item_id, payload)


@router.delete("/{catalog}/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_catalog(
    catalog: CatalogName,
    actor: Annotated[RequestActor, Depends(require_permission("comunicacao", "excluir"))],
    service: Annotated[ComunicacaoService, Depends(get_service)],
    item_id: int = Path(ge=1),
) -> Response:
    await service.update_catalog(actor, catalog, item_id, CatalogUpdate(ativo=False))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/pessoas/{person_id}/interacoes",
    response_model=list[InteracaoResponse],
)
async def list_person_interactions(
    actor: Annotated[RequestActor, Depends(require_permission("comunicacao", "visualizar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[ComunicacaoService, Depends(get_service)],
    person_id: int = Path(ge=1),
    limite: int = Query(default=50, ge=1, le=200),
) -> list[dict]:
    return await service.list_person_interactions(actor, access, person_id, limite)


@router.post(
    "/pessoas/{person_id}/interacoes",
    response_model=InteracaoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_person_interaction(
    payload: InteracaoInput,
    request: Request,
    actor: Annotated[RequestActor, Depends(require_permission("comunicacao", "criar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[ComunicacaoService, Depends(get_service)],
    person_id: int = Path(ge=1),
) -> dict:
    return await service.create_person_interaction(
        actor,
        access,
        person_id,
        payload,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


def _client_ip(request: Request) -> str | None:
    if request.client is None:
        return None
    try:
        return str(ip_address(request.client.host))
    except ValueError:
        return None
