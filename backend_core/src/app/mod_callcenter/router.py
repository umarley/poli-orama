from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.access import RequestActor, get_db_session, require_permission
from app.mod_callcenter.repository import CallCenterRepository
from app.mod_callcenter.schemas import (
    CallQueueItem,
    ConfirmedVoteReportItem,
    ContactCreate,
    ContactResponse,
    VoterStatus,
)
from app.mod_callcenter.service import CallCenterService

router = APIRouter(prefix="/call-center", tags=["Call Center"])


def get_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CallCenterService:
    return CallCenterService(CallCenterRepository(session))


@router.get("/fila", response_model=list[CallQueueItem])
async def list_queue(
    actor: Annotated[RequestActor, Depends(require_permission("comunicacao", "visualizar"))],
    service: Annotated[CallCenterService, Depends(get_service)],
    campanha_eleicao_id: int = Query(ge=1),
    lideranca_id: int | None = Query(default=None, ge=1),
    situacao: VoterStatus | None = None,
    limite: int = Query(default=100, ge=1, le=500),
) -> list[dict[str, Any]]:
    await service.ensure_campaign(actor, campanha_eleicao_id)
    return await service.repository.list_queue(
        actor.tenant_id,
        campanha_eleicao_id,
        leader_id=lideranca_id,
        status=situacao,
        limit=limite,
    )


@router.post(
    "/atendimentos",
    response_model=ContactResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_contact(
    payload: ContactCreate,
    actor: Annotated[RequestActor, Depends(require_permission("comunicacao", "criar"))],
    service: Annotated[CallCenterService, Depends(get_service)],
) -> ContactResponse:
    return await service.create_contact(actor, payload)


@router.get(
    "/relatorios/votos-confirmados",
    response_model=list[ConfirmedVoteReportItem],
)
async def confirmed_votes_report(
    actor: Annotated[RequestActor, Depends(require_permission("comunicacao", "visualizar"))],
    service: Annotated[CallCenterService, Depends(get_service)],
    campanha_eleicao_id: int = Query(ge=1),
    lideranca_id: int | None = Query(default=None, ge=1),
) -> list[dict[str, Any]]:
    await service.ensure_campaign(actor, campanha_eleicao_id)
    return await service.repository.confirmed_report(
        actor.tenant_id, campanha_eleicao_id, lideranca_id
    )
