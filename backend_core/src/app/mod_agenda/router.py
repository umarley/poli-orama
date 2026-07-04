"""Endpoints de agenda, eventos, presenca, demandas e exportacao."""

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.access import (
    RequestActor,
    TerritorialAccess,
    get_db_session,
    get_territorial_access,
    require_permission,
)
from app.mod_agenda.repository import AgendaRepository
from app.mod_agenda.schemas import (
    AgendaItemInput,
    AgendaItemResponse,
    AgendaSummary,
    AttendanceInput,
    AttendanceResponse,
    CatalogCreate,
    CatalogResponse,
    CatalogUpdate,
    DemandFromEventInput,
    DemandResponse,
    EventCancel,
    EventDetailResponse,
    EventInput,
    EventResponse,
    EventUpdate,
    InsightResponse,
    InvitationInput,
    InvitationResponse,
    LeadershipInput,
    LeadershipResponse,
    ParticipantInput,
    ParticipantResponse,
)
from app.mod_agenda.service import AgendaService

router = APIRouter(prefix="/agenda", tags=["Agenda"])


def get_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AgendaService:
    return AgendaService(AgendaRepository(session))


@router.get("/tipos", response_model=list[CatalogResponse])
async def list_event_types(
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "visualizar"))],
    service: Annotated[AgendaService, Depends(get_service)],
    incluir_inativos: bool = False,
) -> list[dict[str, Any]]:
    return await service.repository.list_catalog(
        "tipo_evento", actor.tenant_id, incluir_inativos
    )


@router.post(
    "/tipos", response_model=CatalogResponse, status_code=status.HTTP_201_CREATED
)
async def create_event_type(
    payload: CatalogCreate,
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "administrar"))],
    service: Annotated[AgendaService, Depends(get_service)],
) -> dict[str, Any]:
    return await service.create_catalog(actor, "tipo_evento", payload)


@router.patch("/tipos/{item_id}", response_model=CatalogResponse)
async def update_event_type(
    payload: CatalogUpdate,
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "administrar"))],
    service: Annotated[AgendaService, Depends(get_service)],
    item_id: int = Path(ge=1),
) -> dict[str, Any]:
    return await service.update_catalog(actor, "tipo_evento", item_id, payload)


@router.delete("/tipos/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_event_type(
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "administrar"))],
    service: Annotated[AgendaService, Depends(get_service)],
    item_id: int = Path(ge=1),
) -> Response:
    await service.update_catalog(
        actor, "tipo_evento", item_id, CatalogUpdate(ativo=False)
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/status", response_model=list[CatalogResponse])
async def list_event_statuses(
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "visualizar"))],
    service: Annotated[AgendaService, Depends(get_service)],
    incluir_inativos: bool = False,
) -> list[dict[str, Any]]:
    return await service.repository.list_catalog(
        "status_evento", actor.tenant_id, incluir_inativos
    )


@router.post(
    "/status", response_model=CatalogResponse, status_code=status.HTTP_201_CREATED
)
async def create_event_status(
    payload: CatalogCreate,
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "administrar"))],
    service: Annotated[AgendaService, Depends(get_service)],
) -> dict[str, Any]:
    return await service.create_catalog(actor, "status_evento", payload)


@router.patch("/status/{item_id}", response_model=CatalogResponse)
async def update_event_status(
    payload: CatalogUpdate,
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "administrar"))],
    service: Annotated[AgendaService, Depends(get_service)],
    item_id: int = Path(ge=1),
) -> dict[str, Any]:
    return await service.update_catalog(actor, "status_evento", item_id, payload)


@router.delete("/status/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_event_status(
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "administrar"))],
    service: Annotated[AgendaService, Depends(get_service)],
    item_id: int = Path(ge=1),
) -> Response:
    await service.update_catalog(
        actor, "status_evento", item_id, CatalogUpdate(ativo=False)
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/eventos", response_model=list[EventResponse])
async def list_events(
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "visualizar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[AgendaService, Depends(get_service)],
    data_inicio: datetime | None = None,
    data_fim: datetime | None = None,
    territorio_id: int | None = Query(default=None, ge=1),
    lideranca_id: int | None = Query(default=None, ge=1),
    tipo_evento_id: int | None = Query(default=None, ge=1),
    status_evento_id: int | None = Query(default=None, ge=1),
) -> list[dict[str, Any]]:
    return await service.list_events(
        actor,
        access,
        start=data_inicio,
        end=data_fim,
        territory_id=territorio_id,
        leader_id=lideranca_id,
        event_type_id=tipo_evento_id,
        status_id=status_evento_id,
    )


@router.post(
    "/eventos", response_model=EventResponse, status_code=status.HTTP_201_CREATED
)
async def create_event(
    payload: EventInput,
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "criar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[AgendaService, Depends(get_service)],
) -> EventResponse:
    return await service.create_event(actor, access, payload)


@router.get("/eventos/{event_id}", response_model=EventDetailResponse)
async def event_detail(
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "visualizar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[AgendaService, Depends(get_service)],
    event_id: int = Path(ge=1),
) -> EventDetailResponse:
    return await service.detail(actor, access, event_id)


@router.patch("/eventos/{event_id}", response_model=EventResponse)
async def update_event(
    payload: EventUpdate,
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "editar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[AgendaService, Depends(get_service)],
    event_id: int = Path(ge=1),
) -> EventResponse:
    return await service.update_event(actor, access, event_id, payload)


@router.post("/eventos/{event_id}/cancelar", response_model=EventResponse)
async def cancel_event(
    payload: EventCancel,
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "editar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[AgendaService, Depends(get_service)],
    event_id: int = Path(ge=1),
) -> EventResponse:
    return await service.cancel_event(actor, access, event_id, payload.motivo)


@router.post(
    "/eventos/{event_id}/participantes",
    response_model=ParticipantResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_participant(
    payload: ParticipantInput,
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "editar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[AgendaService, Depends(get_service)],
    event_id: int = Path(ge=1),
) -> dict[str, Any]:
    return await service.add_participant(actor, access, event_id, payload)


@router.delete(
    "/eventos/{event_id}/participantes/{person_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_participant(
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "editar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[AgendaService, Depends(get_service)],
    event_id: int = Path(ge=1),
    person_id: int = Path(ge=1),
) -> Response:
    await service.remove_participant(actor, access, event_id, person_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/eventos/{event_id}/liderancas",
    response_model=LeadershipResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_leadership(
    payload: LeadershipInput,
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "editar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[AgendaService, Depends(get_service)],
    event_id: int = Path(ge=1),
) -> dict[str, Any]:
    return await service.add_leadership(actor, access, event_id, payload)


@router.delete(
    "/eventos/{event_id}/liderancas/{leadership_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_leadership(
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "editar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[AgendaService, Depends(get_service)],
    event_id: int = Path(ge=1),
    leadership_id: int = Path(ge=1),
) -> Response:
    await service.remove_leadership(actor, access, event_id, leadership_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/eventos/{event_id}/convites",
    response_model=InvitationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_invitation(
    payload: InvitationInput,
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "editar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[AgendaService, Depends(get_service)],
    event_id: int = Path(ge=1),
) -> dict[str, Any]:
    return await service.create_invitation(actor, access, event_id, payload)


@router.post(
    "/eventos/{event_id}/pautas",
    response_model=AgendaItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_agenda_item(
    payload: AgendaItemInput,
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "editar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[AgendaService, Depends(get_service)],
    event_id: int = Path(ge=1),
) -> dict[str, Any]:
    return await service.create_agenda_item(actor, access, event_id, payload)


@router.put("/eventos/{event_id}/presenca", response_model=AttendanceResponse)
async def record_attendance(
    payload: AttendanceInput,
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "editar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[AgendaService, Depends(get_service)],
    event_id: int = Path(ge=1),
) -> dict[str, Any]:
    return await service.record_attendance(actor, access, event_id, payload)


@router.post(
    "/eventos/{event_id}/demandas",
    response_model=DemandResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_demand(
    payload: DemandFromEventInput,
    actor: Annotated[RequestActor, Depends(require_permission("demandas", "criar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[AgendaService, Depends(get_service)],
    event_id: int = Path(ge=1),
) -> dict[str, Any]:
    return await service.create_demand(actor, access, event_id, payload)


@router.get("/resumo", response_model=AgendaSummary)
async def agenda_summary(
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "visualizar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[AgendaService, Depends(get_service)],
    data_inicio: datetime,
    data_fim: datetime,
) -> AgendaSummary:
    return await service.summary(actor, access, data_inicio, data_fim)


@router.get("/insights", response_model=list[InsightResponse])
async def agenda_insights(
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "visualizar"))],
    service: Annotated[AgendaService, Depends(get_service)],
) -> list[dict[str, Any]]:
    return await service.repository.insights(actor.tenant_id)


@router.get("/exportar.csv")
async def export_agenda(
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "exportar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[AgendaService, Depends(get_service)],
    data_inicio: datetime | None = None,
    data_fim: datetime | None = None,
    territorio_id: int | None = Query(default=None, ge=1),
    lideranca_id: int | None = Query(default=None, ge=1),
    tipo_evento_id: int | None = Query(default=None, ge=1),
    status_evento_id: int | None = Query(default=None, ge=1),
) -> StreamingResponse:
    content = await service.export_csv(
        actor,
        access,
        start=data_inicio,
        end=data_fim,
        territory_id=territorio_id,
        leader_id=lideranca_id,
        event_type_id=tipo_evento_id,
        status_id=status_evento_id,
    )
    return StreamingResponse(
        iter([content]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="agenda.csv"'},
    )
