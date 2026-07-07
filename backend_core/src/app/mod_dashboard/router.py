from datetime import date, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.access import (
    RequestActor,
    TerritorialAccess,
    get_db_session,
    get_territorial_access,
    require_permission,
)
from app.mod_dashboard.repository import DashboardRepository
from app.mod_dashboard.schemas import (
    Birthdays,
    CommemorativeDate,
    DashboardConfiguration,
    DashboardConfigurationUpdate,
    DashboardFilters,
    DashboardOverview,
    ExportRequest,
    ReportDefinition,
    ReportExecution,
)
from app.mod_dashboard.service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def service(session: Annotated[AsyncSession, Depends(get_db_session)]) -> DashboardService:
    return DashboardService(DashboardRepository(session))


def filters(
    data_inicio: Annotated[date | None, Query()] = None,
    data_fim: Annotated[date | None, Query()] = None,
    territorio_id: Annotated[int | None, Query(ge=1)] = None,
    lideranca_id: Annotated[int | None, Query(ge=1)] = None,
) -> DashboardFilters:
    end = data_fim or date.today()
    return DashboardFilters(
        data_inicio=data_inicio or end - timedelta(days=29),
        data_fim=end,
        territorio_id=territorio_id,
        lideranca_id=lideranca_id,
    )


Viewer = Annotated[RequestActor, Depends(require_permission("dashboard", "visualizar"))]
Access = Annotated[TerritorialAccess, Depends(get_territorial_access)]
Service = Annotated[DashboardService, Depends(service)]
Filter = Annotated[DashboardFilters, Depends(filters)]


@router.get("/visao-geral", response_model=DashboardOverview)
async def overview(actor: Viewer, access: Access, svc: Service, query: Filter):
    return await svc.overview(actor, access, query)


@router.get("/aniversariantes", response_model=Birthdays)
async def birthdays(actor: Viewer, access: Access, svc: Service, query: Filter):
    return await svc.birthdays(actor, access, query)


@router.get("/datas-comemorativas", response_model=list[CommemorativeDate])
async def commemorative_dates(actor: Viewer, access: Access, svc: Service, query: Filter):
    return await svc.commemorative_dates(actor, access, query)


@router.get("/relatorios/{report_type}")
async def report(
    report_type: Literal["metas", "demandas", "agenda", "cadastros", "lideres"],
    actor: Viewer,
    access: Access,
    svc: Service,
    query: Filter,
):
    return await svc.report(report_type, actor, access, query)


@router.post("/exportacoes")
async def export(
    payload: ExportRequest,
    actor: Annotated[RequestActor, Depends(require_permission("dashboard", "exportar"))],
    access: Access,
    svc: Service,
):
    content, media_type, filename = await svc.export(payload, actor, access)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/configuracao", response_model=DashboardConfiguration)
async def configuration(actor: Viewer, svc: Service):
    return await svc.configuration(actor)


@router.put("/configuracao", response_model=DashboardConfiguration)
async def save_configuration(
    payload: DashboardConfigurationUpdate,
    actor: Annotated[RequestActor, Depends(require_permission("configuracoes", "administrar"))],
    svc: Service,
):
    value = await svc.repository.save_configuration(actor.tenant_id, actor.user_id, payload)
    await svc.repository.commit()
    return value


@router.get("/relatorios", response_model=list[ReportDefinition])
async def report_definitions(actor: Viewer, svc: Service):
    return await svc.repository.report_definitions(actor.tenant_id)


@router.get("/relatorios-execucoes", response_model=list[ReportExecution])
async def report_executions(actor: Viewer, svc: Service):
    return await svc.repository.report_executions(actor.tenant_id)
