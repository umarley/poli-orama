"""Endpoints de agenda, eventos, presenca, demandas e exportacao."""

import html
import json
from datetime import datetime
from typing import Annotated, Any
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Response, status
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.access import (
    RequestActor,
    TerritorialAccess,
    get_db_session,
    get_territorial_access,
    require_permission,
)
from app.core.database import get_session
from app.mod_agenda.google_calendar import GoogleCalendarService
from app.mod_agenda.repository import AgendaRepository
from app.mod_agenda.schemas import (
    AgendaItemInput,
    AgendaItemResponse,
    AgendaSummary,
    AttendanceInput,
    AttendanceResponse,
    CalendarInput,
    CalendarMemberInput,
    CalendarMemberResponse,
    CalendarResponse,
    CalendarUpdate,
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
    GoogleCalendarItem,
    GoogleCalendarLinkInput,
    GoogleCalendarLinkResponse,
    GoogleOAuthStartResponse,
    GoogleSyncResponse,
    InsightResponse,
    InvitationInput,
    InvitationResponse,
    LeadershipInput,
    LeadershipResponse,
    ParticipantInput,
    ParticipantResponse,
    PublicAttendanceInput,
    PublicAttendanceResponse,
    PublicEventResponse,
)
from app.mod_agenda.service import AgendaService

router = APIRouter(prefix="/agenda", tags=["Agenda"])


def get_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AgendaService:
    return AgendaService(AgendaRepository(session))


def get_public_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AgendaService:
    return AgendaService(AgendaRepository(session))


def get_google_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GoogleCalendarService:
    return GoogleCalendarService(AgendaRepository(session))


def get_public_google_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> GoogleCalendarService:
    return GoogleCalendarService(AgendaRepository(session))


@router.get("/agendas", response_model=list[CalendarResponse])
async def list_calendars(
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "visualizar"))],
    service: Annotated[AgendaService, Depends(get_service)],
) -> list[CalendarResponse]:
    return await service.list_calendars(actor)


@router.post("/agendas", response_model=CalendarResponse, status_code=status.HTTP_201_CREATED)
async def create_calendar(
    payload: CalendarInput,
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "administrar"))],
    service: Annotated[AgendaService, Depends(get_service)],
) -> CalendarResponse:
    return await service.create_calendar(actor, payload)


@router.patch("/agendas/{calendar_id}", response_model=CalendarResponse)
async def update_calendar(
    payload: CalendarUpdate,
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "visualizar"))],
    service: Annotated[AgendaService, Depends(get_service)],
    calendar_id: int = Path(ge=1),
) -> CalendarResponse:
    return await service.update_calendar(actor, calendar_id, payload)


@router.delete("/agendas/{calendar_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_calendar(
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "visualizar"))],
    service: Annotated[AgendaService, Depends(get_service)],
    calendar_id: int = Path(ge=1),
) -> Response:
    await service.delete_calendar(actor, calendar_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/agendas/{calendar_id}/usuarios", response_model=list[CalendarMemberResponse])
async def list_calendar_members(
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "visualizar"))],
    service: Annotated[AgendaService, Depends(get_service)],
    calendar_id: int = Path(ge=1),
) -> list[dict[str, Any]]:
    return await service.calendar_members(actor, calendar_id)


@router.put("/agendas/{calendar_id}/usuarios", response_model=list[CalendarMemberResponse])
async def save_calendar_member(
    payload: CalendarMemberInput,
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "visualizar"))],
    service: Annotated[AgendaService, Depends(get_service)],
    calendar_id: int = Path(ge=1),
) -> list[dict[str, Any]]:
    return await service.save_calendar_member(actor, calendar_id, payload)


@router.delete("/agendas/{calendar_id}/usuarios/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_calendar_member(
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "visualizar"))],
    service: Annotated[AgendaService, Depends(get_service)],
    calendar_id: int = Path(ge=1),
    user_id: int = Path(ge=1),
) -> Response:
    await service.remove_calendar_member(actor, calendar_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/google/oauth/iniciar", response_model=GoogleOAuthStartResponse)
async def start_google_oauth(
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "integrar_google"))],
    service: Annotated[GoogleCalendarService, Depends(get_google_service)],
) -> GoogleOAuthStartResponse:
    return await service.start_oauth(actor)


@router.get("/google/oauth/callback", response_class=HTMLResponse)
async def google_oauth_callback(
    service: Annotated[GoogleCalendarService, Depends(get_public_google_service)],
    state: str,
    code: str | None = None,
    error: str | None = None,
) -> HTMLResponse:
    success = False
    message = error or "Autorizacao cancelada."
    if code and not error:
        try:
            await service.finish_oauth(state, code)
            success = True
            message = "Conta Google conectada com sucesso."
        except Exception as exc:  # a janela OAuth deve sempre devolver feedback ao frontend
            message = str(exc)
    payload = (
        json.dumps({"type": "google-calendar-oauth", "success": success, "message": message})
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )
    frontend = urlsplit(service.settings.google_calendar_frontend_url)
    target_origin = f"{frontend.scheme}://{frontend.netloc}"
    return HTMLResponse(
        "<!doctype html><meta charset='utf-8'><title>Google Agenda</title>"
        f"<script>window.opener?.postMessage({payload}, {json.dumps(target_origin)});"
        "window.close();</script>"
        f"<p>{html.escape(message)}</p>"
    )


@router.get("/google/calendarios", response_model=list[GoogleCalendarItem])
async def list_google_calendars(
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "integrar_google"))],
    service: Annotated[GoogleCalendarService, Depends(get_google_service)],
) -> list[GoogleCalendarItem]:
    return await service.calendars(actor)


@router.put("/agendas/{calendar_id}/google", response_model=GoogleCalendarLinkResponse)
async def link_google_calendar(
    payload: GoogleCalendarLinkInput,
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "integrar_google"))],
    agenda_service: Annotated[AgendaService, Depends(get_service)],
    google_service: Annotated[GoogleCalendarService, Depends(get_google_service)],
    calendar_id: int = Path(ge=1),
) -> GoogleCalendarLinkResponse:
    await agenda_service.ensure_calendar(actor, calendar_id, "administrar_agenda")
    return await google_service.link(actor, calendar_id, payload)


@router.delete("/agendas/{calendar_id}/google", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_google_calendar(
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "integrar_google"))],
    agenda_service: Annotated[AgendaService, Depends(get_service)],
    google_service: Annotated[GoogleCalendarService, Depends(get_google_service)],
    calendar_id: int = Path(ge=1),
) -> Response:
    await agenda_service.ensure_calendar(actor, calendar_id, "administrar_agenda")
    await google_service.unlink(actor, calendar_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/agendas/{calendar_id}/google/sincronizar", response_model=GoogleSyncResponse)
async def sync_google_calendar(
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "integrar_google"))],
    agenda_service: Annotated[AgendaService, Depends(get_service)],
    google_service: Annotated[GoogleCalendarService, Depends(get_google_service)],
    calendar_id: int = Path(ge=1),
) -> GoogleSyncResponse:
    await agenda_service.ensure_calendar(actor, calendar_id, "editar")
    return await google_service.sync(actor, calendar_id)


@router.get(
    "/publico/eventos/{public_id}/presenca",
    response_model=PublicEventResponse,
    summary="Exibe os dados publicos para confirmacao de presenca",
)
async def get_public_attendance_event(
    service: Annotated[AgendaService, Depends(get_public_service)],
    public_id: Annotated[UUID, Path()],
) -> PublicEventResponse:
    return await service.public_event(public_id)


@router.post(
    "/publico/eventos/{public_id}/presenca",
    response_model=PublicAttendanceResponse,
    summary="Registra a presenca informada pelo proprio participante",
)
async def confirm_public_attendance(
    payload: PublicAttendanceInput,
    service: Annotated[AgendaService, Depends(get_public_service)],
    public_id: Annotated[UUID, Path()],
) -> PublicAttendanceResponse:
    return await service.confirm_public_attendance(public_id, payload)


@router.get("/tipos", response_model=list[CatalogResponse])
async def list_event_types(
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "visualizar"))],
    service: Annotated[AgendaService, Depends(get_service)],
    incluir_inativos: bool = False,
) -> list[dict[str, Any]]:
    return await service.repository.list_catalog("tipo_evento", actor.tenant_id, incluir_inativos)


@router.post("/tipos", response_model=CatalogResponse, status_code=status.HTTP_201_CREATED)
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
    await service.update_catalog(actor, "tipo_evento", item_id, CatalogUpdate(ativo=False))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/status", response_model=list[CatalogResponse])
async def list_event_statuses(
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "visualizar"))],
    service: Annotated[AgendaService, Depends(get_service)],
    incluir_inativos: bool = False,
) -> list[dict[str, Any]]:
    return await service.repository.list_catalog("status_evento", actor.tenant_id, incluir_inativos)


@router.post("/status", response_model=CatalogResponse, status_code=status.HTTP_201_CREATED)
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
    await service.update_catalog(actor, "status_evento", item_id, CatalogUpdate(ativo=False))
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
    agenda_id: int | None = Query(default=None, ge=1),
    natureza_candidato: str | None = Query(default=None, pattern="^(rede|recurso|rua)$"),
    frente_comunidade: str | None = Query(
        default=None,
        pattern="^(juventude|sindicalista|cultura|engenharia|saude|educacao|dobradas)$",
    ),
    tipo_agenda: str | None = Query(
        default=None, pattern="^(fixa_campanha|agenda_aberta|agenda_candidato)$"
    ),
    visibilidade: str | None = Query(default=None, pattern="^(publica|restrita)$"),
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
        calendar_id=agenda_id,
        candidate_nature=natureza_candidato,
        community_front=frente_comunidade,
        calendar_type=tipo_agenda,
        visibility=visibilidade,
    )


@router.post("/eventos", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    payload: EventInput,
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "visualizar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[AgendaService, Depends(get_service)],
) -> EventResponse:
    return await service.create_event(actor, access, payload)


@router.get("/eventos/{event_identifier}", response_model=EventDetailResponse)
async def event_detail(
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "visualizar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[AgendaService, Depends(get_service)],
    event_identifier: Annotated[
        str,
        Path(
            pattern=(
                r"^(?:[1-9][0-9]*|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-"
                r"[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})$"
            )
        ),
    ],
) -> EventDetailResponse:
    if event_identifier.isdecimal():
        return await service.detail(actor, access, int(event_identifier))
    return await service.detail_by_uuid(actor, access, UUID(event_identifier))


@router.patch("/eventos/{event_id}", response_model=EventResponse)
async def update_event(
    payload: EventUpdate,
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "visualizar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[AgendaService, Depends(get_service)],
    event_id: int = Path(ge=1),
) -> EventResponse:
    return await service.update_event(actor, access, event_id, payload)


@router.post("/eventos/{event_id}/cancelar", response_model=EventResponse)
async def cancel_event(
    payload: EventCancel,
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "visualizar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[AgendaService, Depends(get_service)],
    event_id: int = Path(ge=1),
) -> EventResponse:
    return await service.cancel_event(actor, access, event_id, payload.motivo)


@router.delete("/eventos/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "visualizar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[AgendaService, Depends(get_service)],
    event_id: int = Path(ge=1),
) -> Response:
    await service.delete_event(actor, access, event_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/eventos/{event_id}/participantes",
    response_model=ParticipantResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_participant(
    payload: ParticipantInput,
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "visualizar"))],
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
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "visualizar"))],
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
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "visualizar"))],
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
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "visualizar"))],
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
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "visualizar"))],
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
    actor: Annotated[RequestActor, Depends(require_permission("agenda", "visualizar"))],
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
    return await service.list_insights(actor)


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
    agenda_id: int | None = Query(default=None, ge=1),
    natureza_candidato: str | None = Query(default=None, pattern="^(rede|recurso|rua)$"),
    frente_comunidade: str | None = Query(
        default=None,
        pattern="^(juventude|sindicalista|cultura|engenharia|saude|educacao|dobradas)$",
    ),
    tipo_agenda: str | None = Query(
        default=None, pattern="^(fixa_campanha|agenda_aberta|agenda_candidato)$"
    ),
    visibilidade: str | None = Query(default=None, pattern="^(publica|restrita)$"),
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
        calendar_id=agenda_id,
        candidate_nature=natureza_candidato,
        community_front=frente_comunidade,
        calendar_type=tipo_agenda,
        visibility=visibilidade,
    )
    return StreamingResponse(
        iter([content]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="agenda.csv"'},
    )
