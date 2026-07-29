from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.access import (
    RequestActor,
    get_current_user,
    get_db_session,
    require_any_profile,
    require_saas_admin,
)
from app.core.config import get_settings
from app.mod_eleicoes.repository import ElectionRepository
from app.mod_eleicoes.schemas import (
    CampaignClosureCreate,
    CampaignClosureResponse,
    CampaignCreate,
    CampaignResponse,
    CampaignUpdate,
    ContestedOfficeResponse,
    ElectionCreate,
    ElectionResponse,
    ElectionType,
    ElectionUpdate,
)
from app.mod_eleicoes.service import ElectionService

router = APIRouter(prefix="/eleicoes", tags=["Eleicoes"])
campaign_manager = require_any_profile(
    "gestor", "gestor_saas", "coordenador_territorial"
)


def get_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ElectionService:
    return ElectionService(ElectionRepository(session), get_settings())


@router.get("", response_model=list[ElectionResponse])
async def list_elections(
    _: Annotated[RequestActor, Depends(get_current_user)],
    service: Annotated[ElectionService, Depends(get_service)],
    incluir_inativas: bool = False,
) -> list[dict[str, Any]]:
    return await service.repository.list(incluir_inativas)


@router.post("", response_model=ElectionResponse, status_code=status.HTTP_201_CREATED)
async def create_election(
    payload: ElectionCreate,
    _: Annotated[int, Depends(require_saas_admin)],
    actor: Annotated[RequestActor, Depends(get_current_user)],
    service: Annotated[ElectionService, Depends(get_service)],
) -> dict[str, Any]:
    return await service.create(actor, payload)


@router.patch("/{election_id}", response_model=ElectionResponse)
async def update_election(
    payload: ElectionUpdate,
    _: Annotated[int, Depends(require_saas_admin)],
    service: Annotated[ElectionService, Depends(get_service)],
    election_id: int = Path(ge=1),
) -> dict[str, Any]:
    return await service.update(election_id, payload)


@router.get("/cargos", response_model=list[ContestedOfficeResponse])
async def list_contested_offices(
    service: Annotated[ElectionService, Depends(get_service)],
    _: Annotated[RequestActor, Depends(get_current_user)],
    tipo: Annotated[ElectionType, Query()],
) -> list[ContestedOfficeResponse]:
    return await service.list_contested_offices(tipo)


@router.get("/campanhas/atual", response_model=CampaignResponse | None)
async def get_current_campaign(
    actor: Annotated[RequestActor, Depends(get_current_user)],
    service: Annotated[ElectionService, Depends(get_service)],
) -> CampaignResponse | None:
    return await service.current_campaign(actor)


@router.get("/campanhas", response_model=list[CampaignResponse])
async def list_campaigns(
    actor: Annotated[RequestActor, Depends(campaign_manager)],
    service: Annotated[ElectionService, Depends(get_service)],
) -> list[CampaignResponse]:
    return await service.list_campaigns(actor)


@router.post(
    "/campanhas", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED
)
async def create_campaign(
    payload: CampaignCreate,
    actor: Annotated[RequestActor, Depends(campaign_manager)],
    service: Annotated[ElectionService, Depends(get_service)],
) -> CampaignResponse:
    return await service.create_campaign(actor, payload)


@router.patch("/campanhas/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    payload: CampaignUpdate,
    actor: Annotated[RequestActor, Depends(campaign_manager)],
    service: Annotated[ElectionService, Depends(get_service)],
    campaign_id: int = Path(ge=1),
) -> CampaignResponse:
    return await service.update_campaign(actor, campaign_id, payload)


@router.post("/campanhas/{campaign_id}/ativar", response_model=CampaignResponse)
async def activate_campaign(
    actor: Annotated[RequestActor, Depends(campaign_manager)],
    service: Annotated[ElectionService, Depends(get_service)],
    campaign_id: int = Path(ge=1),
) -> CampaignResponse:
    return await service.activate_campaign(actor, campaign_id)


@router.get(
    "/campanha-ativa/encerramento",
    response_model=CampaignClosureResponse | None,
)
async def get_active_campaign_closure(
    actor: Annotated[RequestActor, Depends(campaign_manager)],
    service: Annotated[ElectionService, Depends(get_service)],
) -> CampaignClosureResponse | None:
    return await service.active_closure(actor)


@router.post(
    "/campanha-ativa/encerramento",
    response_model=CampaignClosureResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_active_campaign_closure(
    payload: CampaignClosureCreate,
    actor: Annotated[RequestActor, Depends(campaign_manager)],
    service: Annotated[ElectionService, Depends(get_service)],
) -> CampaignClosureResponse:
    return await service.request_closure(actor, payload)


@router.post(
    "/campanha-ativa/encerramento/reprocessar",
    response_model=CampaignClosureResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def retry_active_campaign_closure(
    actor: Annotated[RequestActor, Depends(campaign_manager)],
    service: Annotated[ElectionService, Depends(get_service)],
) -> CampaignClosureResponse:
    return await service.retry_closure(actor)
