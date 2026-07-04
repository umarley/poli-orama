from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.access import (
    RequestActor,
    TerritorialAccess,
    get_db_session,
    get_territorial_access,
    require_permission,
)
from app.mod_metas.repository import MetaRepository
from app.mod_metas.schemas import (
    GoalCreate,
    GoalDetailResponse,
    GoalPeriodCreate,
    GoalPeriodResponse,
    GoalPeriodUpdate,
    GoalResponse,
    GoalSummaryResponse,
    GoalTrackingCreate,
    GoalTrackingResponse,
    GoalTypeCreate,
    GoalTypeResponse,
    GoalTypeUpdate,
    GoalUpdate,
    LeadershipRankingResponse,
    MetaStatus,
    TargetOption,
    TargetType,
)
from app.mod_metas.service import MetaService

router = APIRouter(prefix="/metas", tags=["Metas"])


def get_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MetaService:
    return MetaService(MetaRepository(session))


@router.get("/tipos", response_model=list[GoalTypeResponse])
async def list_types(
    actor: Annotated[RequestActor, Depends(require_permission("metas", "visualizar"))],
    service: Annotated[MetaService, Depends(get_service)],
    incluir_inativos: bool = False,
) -> list[dict[str, Any]]:
    return await service.repository.list_types(actor.tenant_id, incluir_inativos)


@router.post("/tipos", response_model=GoalTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_type(
    payload: GoalTypeCreate,
    actor: Annotated[
        RequestActor, Depends(require_permission("configuracoes", "administrar"))
    ],
    service: Annotated[MetaService, Depends(get_service)],
) -> dict[str, Any]:
    return await service.create_type(actor, payload)


@router.patch("/tipos/{type_id}", response_model=GoalTypeResponse)
async def update_type(
    payload: GoalTypeUpdate,
    actor: Annotated[
        RequestActor, Depends(require_permission("configuracoes", "administrar"))
    ],
    service: Annotated[MetaService, Depends(get_service)],
    type_id: int = Path(ge=1),
) -> dict[str, Any]:
    return await service.update_type(actor, type_id, payload)


@router.delete("/tipos/{type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_type(
    actor: Annotated[
        RequestActor, Depends(require_permission("configuracoes", "administrar"))
    ],
    service: Annotated[MetaService, Depends(get_service)],
    type_id: int = Path(ge=1),
) -> Response:
    await service.update_type(actor, type_id, GoalTypeUpdate(ativo=False))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/periodos", response_model=list[GoalPeriodResponse])
async def list_periods(
    actor: Annotated[RequestActor, Depends(require_permission("metas", "visualizar"))],
    service: Annotated[MetaService, Depends(get_service)],
    incluir_inativos: bool = False,
) -> list[dict[str, Any]]:
    return await service.repository.list_periods(actor.tenant_id, incluir_inativos)


@router.post(
    "/periodos", response_model=GoalPeriodResponse, status_code=status.HTTP_201_CREATED
)
async def create_period(
    payload: GoalPeriodCreate,
    actor: Annotated[RequestActor, Depends(require_permission("metas", "criar"))],
    service: Annotated[MetaService, Depends(get_service)],
) -> dict[str, Any]:
    return await service.create_period(actor, payload)


@router.patch("/periodos/{period_id}", response_model=GoalPeriodResponse)
async def update_period(
    payload: GoalPeriodUpdate,
    actor: Annotated[RequestActor, Depends(require_permission("metas", "editar"))],
    service: Annotated[MetaService, Depends(get_service)],
    period_id: int = Path(ge=1),
) -> dict[str, Any]:
    return await service.update_period(actor, period_id, payload)


@router.delete("/periodos/{period_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_period(
    actor: Annotated[RequestActor, Depends(require_permission("metas", "editar"))],
    service: Annotated[MetaService, Depends(get_service)],
    period_id: int = Path(ge=1),
) -> Response:
    await service.update_period(actor, period_id, GoalPeriodUpdate(ativo=False))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/alvos/opcoes", response_model=list[TargetOption])
async def target_options(
    actor: Annotated[RequestActor, Depends(require_permission("metas", "visualizar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[MetaService, Depends(get_service)],
    tipo: TargetType,
    query: str | None = Query(default=None, max_length=150),
) -> list[TargetOption]:
    return await service.target_options(actor, access, tipo, query)


@router.get("/resumo", response_model=GoalSummaryResponse)
async def summary(
    actor: Annotated[RequestActor, Depends(require_permission("metas", "visualizar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[MetaService, Depends(get_service)],
    territorio_id: int | None = Query(default=None, ge=1),
    lideranca_id: int | None = Query(default=None, ge=1),
    periodo_id: int | None = Query(default=None, ge=1),
    status_meta: Annotated[MetaStatus | None, Query(alias="status")] = None,
) -> GoalSummaryResponse:
    return await service.summary(
        actor,
        access,
        territory_id=territorio_id,
        leader_id=lideranca_id,
        period_id=periodo_id,
        status=status_meta,
    )


@router.get("/ranking", response_model=list[LeadershipRankingResponse])
async def ranking(
    actor: Annotated[RequestActor, Depends(require_permission("metas", "visualizar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[MetaService, Depends(get_service)],
    data_referencia: date | None = None,
) -> list[LeadershipRankingResponse]:
    return await service.list_ranking(actor, access, data_referencia)


@router.post("/ranking/recalcular", response_model=list[LeadershipRankingResponse])
async def recalculate_ranking(
    actor: Annotated[RequestActor, Depends(require_permission("metas", "aprovar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[MetaService, Depends(get_service)],
    data_referencia: date | None = None,
) -> list[LeadershipRankingResponse]:
    return await service.recalculate_ranking(actor, access, data_referencia)


@router.get("", response_model=list[GoalResponse])
async def list_goals(
    actor: Annotated[RequestActor, Depends(require_permission("metas", "visualizar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[MetaService, Depends(get_service)],
    territorio_id: int | None = Query(default=None, ge=1),
    lideranca_id: int | None = Query(default=None, ge=1),
    periodo_id: int | None = Query(default=None, ge=1),
    status_meta: Annotated[MetaStatus | None, Query(alias="status")] = None,
) -> list[GoalResponse]:
    return await service.list_goals(
        actor,
        access,
        territory_id=territorio_id,
        leader_id=lideranca_id,
        period_id=periodo_id,
        status=status_meta,
    )


@router.post("", response_model=GoalDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_goal(
    payload: GoalCreate,
    actor: Annotated[RequestActor, Depends(require_permission("metas", "criar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[MetaService, Depends(get_service)],
) -> GoalDetailResponse:
    return await service.create_goal(actor, access, payload)


@router.get("/{goal_id}", response_model=GoalDetailResponse)
async def get_goal(
    actor: Annotated[RequestActor, Depends(require_permission("metas", "visualizar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[MetaService, Depends(get_service)],
    goal_id: int = Path(ge=1),
) -> GoalDetailResponse:
    return await service.get_goal(actor, access, goal_id)


@router.patch("/{goal_id}", response_model=GoalDetailResponse)
async def update_goal(
    payload: GoalUpdate,
    actor: Annotated[RequestActor, Depends(require_permission("metas", "editar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[MetaService, Depends(get_service)],
    goal_id: int = Path(ge=1),
) -> GoalDetailResponse:
    return await service.update_goal(actor, access, goal_id, payload)


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_goal(
    actor: Annotated[RequestActor, Depends(require_permission("metas", "editar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[MetaService, Depends(get_service)],
    goal_id: int = Path(ge=1),
) -> Response:
    await service.cancel_goal(actor, access, goal_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{goal_id}/acompanhamentos",
    response_model=GoalTrackingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_tracking(
    payload: GoalTrackingCreate,
    actor: Annotated[RequestActor, Depends(require_permission("metas", "editar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[MetaService, Depends(get_service)],
    goal_id: int = Path(ge=1),
) -> GoalTrackingResponse:
    return await service.create_tracking(actor, access, goal_id, payload)
