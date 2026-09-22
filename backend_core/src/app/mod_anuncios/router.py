"""Endpoints administrativos e do aplicativo de campo para Anuncios."""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    Path,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.access import RequestActor, get_current_user, get_db_session
from app.core.config import get_settings
from app.core.errors import BusinessRuleError
from app.core.pagination import ListParams, Page, list_params
from app.mod_anuncios.repository import AnunciosRepository
from app.mod_anuncios.schemas import (
    DashboardResponse,
    InstallationInput,
    MaterialCreate,
    MaterialResponse,
    MaterialUpdate,
    OperationResponse,
    PlanningCreate,
    PlanningDetail,
    PlanningResponse,
    PlanningUpdate,
    RouteCreate,
    RouteDetail,
    RouteResponse,
    RouteUpdate,
    TeamInput,
    TeamResponse,
    TeamUpdate,
    WithdrawalInput,
)
from app.mod_anuncios.service import AnunciosService
from app.mod_arquivos.repository import FileRepository
from app.mod_arquivos.service import FileService

router = APIRouter(prefix="/anuncios", tags=["Anuncios"])


def get_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AnunciosService:
    return AnunciosService(
        AnunciosRepository(session),
        FileService(FileRepository(session), get_settings()),
    )


@router.get("/materiais", response_model=Page[MaterialResponse])
async def list_materials(
    actor: Annotated[RequestActor, Depends(get_current_user)],
    service: Annotated[AnunciosService, Depends(get_service)],
    params: Annotated[ListParams, Depends(list_params)],
    incluir_inativos: bool = False,
    para_planejamento: bool = False,
) -> Page[MaterialResponse]:
    return await service.list_materials(
        actor,
        params,
        include_inactive=incluir_inativos,
        active_only_for_planning=para_planejamento,
    )


@router.post("/materiais", response_model=MaterialResponse, status_code=status.HTTP_201_CREATED)
async def create_material(
    payload: MaterialCreate,
    actor: Annotated[RequestActor, Depends(get_current_user)],
    service: Annotated[AnunciosService, Depends(get_service)],
) -> MaterialResponse:
    return await service.create_material(actor, payload)


@router.patch("/materiais/{material_id}", response_model=MaterialResponse)
async def update_material(
    payload: MaterialUpdate,
    actor: Annotated[RequestActor, Depends(get_current_user)],
    service: Annotated[AnunciosService, Depends(get_service)],
    material_id: int = Path(ge=1),
) -> MaterialResponse:
    return await service.update_material(actor, material_id, payload)


@router.delete("/materiais/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_material(
    actor: Annotated[RequestActor, Depends(get_current_user)],
    service: Annotated[AnunciosService, Depends(get_service)],
    material_id: int = Path(ge=1),
) -> Response:
    await service.deactivate_material(actor, material_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/equipes", response_model=Page[TeamResponse])
async def list_teams(
    actor: Annotated[RequestActor, Depends(get_current_user)],
    service: Annotated[AnunciosService, Depends(get_service)],
    params: Annotated[ListParams, Depends(list_params)],
    incluir_inativos: bool = False,
) -> Page[TeamResponse]:
    return await service.list_teams(actor, params, include_inactive=incluir_inativos)


@router.post("/equipes", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    payload: TeamInput,
    actor: Annotated[RequestActor, Depends(get_current_user)],
    service: Annotated[AnunciosService, Depends(get_service)],
) -> TeamResponse:
    return await service.create_team(actor, payload)


@router.patch("/equipes/{team_id}", response_model=TeamResponse)
async def update_team(
    payload: TeamUpdate,
    actor: Annotated[RequestActor, Depends(get_current_user)],
    service: Annotated[AnunciosService, Depends(get_service)],
    team_id: int = Path(ge=1),
) -> TeamResponse:
    return await service.update_team(actor, team_id, payload)


@router.delete("/equipes/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_team(
    actor: Annotated[RequestActor, Depends(get_current_user)],
    service: Annotated[AnunciosService, Depends(get_service)],
    team_id: int = Path(ge=1),
) -> Response:
    await service.update_team(actor, team_id, TeamUpdate(ativo=False))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/rotas", response_model=Page[RouteResponse])
async def list_routes(
    actor: Annotated[RequestActor, Depends(get_current_user)],
    service: Annotated[AnunciosService, Depends(get_service)],
    params: Annotated[ListParams, Depends(list_params)],
    territorio_id: int | None = Query(default=None, ge=1),
    material_id: int | None = Query(default=None, ge=1),
    incluir_inativas: bool = False,
) -> Page[RouteResponse]:
    return await service.list_routes(
        actor,
        params,
        territory_id=territorio_id,
        material_id=material_id,
        include_inactive=incluir_inativas,
    )


@router.post("/rotas", response_model=RouteDetail, status_code=status.HTTP_201_CREATED)
async def create_route(
    payload: RouteCreate,
    actor: Annotated[RequestActor, Depends(get_current_user)],
    service: Annotated[AnunciosService, Depends(get_service)],
) -> RouteDetail:
    return await service.create_route(actor, payload)


@router.get("/rotas/{route_uuid}", response_model=RouteDetail)
async def get_route(
    actor: Annotated[RequestActor, Depends(get_current_user)],
    service: Annotated[AnunciosService, Depends(get_service)],
    route_uuid: UUID,
) -> RouteDetail:
    return await service.get_admin_route(actor, route_uuid)


@router.patch("/rotas/{route_uuid}", response_model=RouteDetail)
async def update_route(
    payload: RouteUpdate,
    actor: Annotated[RequestActor, Depends(get_current_user)],
    service: Annotated[AnunciosService, Depends(get_service)],
    route_uuid: UUID,
) -> RouteDetail:
    return await service.update_route(actor, route_uuid, payload)


@router.delete("/rotas/{route_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_route(
    actor: Annotated[RequestActor, Depends(get_current_user)],
    service: Annotated[AnunciosService, Depends(get_service)],
    route_uuid: UUID,
) -> Response:
    await service.update_route(actor, route_uuid, RouteUpdate(ativo=False))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/planejamentos", response_model=Page[PlanningResponse])
async def list_plannings(
    actor: Annotated[RequestActor, Depends(get_current_user)],
    service: Annotated[AnunciosService, Depends(get_service)],
    params: Annotated[ListParams, Depends(list_params)],
    data_inicio: date | None = None,
    data_fim: date | None = None,
    status_planejamento: str | None = Query(default=None, alias="status"),
    equipe_id: int | None = Query(default=None, ge=1),
    usuario_id: int | None = Query(default=None, ge=1),
    territorio_id: int | None = Query(default=None, ge=1),
    material_id: int | None = Query(default=None, ge=1),
    rota_id: int | None = Query(default=None, ge=1),
) -> Page[PlanningResponse]:
    return await service.list_plannings(
        actor,
        params,
        start=data_inicio,
        end=data_fim,
        status=status_planejamento,
        team_id=equipe_id,
        user_id=usuario_id,
        territory_id=territorio_id,
        material_id=material_id,
        route_id=rota_id,
    )


@router.post("/planejamentos", response_model=PlanningDetail, status_code=status.HTTP_201_CREATED)
async def create_planning(
    payload: PlanningCreate,
    actor: Annotated[RequestActor, Depends(get_current_user)],
    service: Annotated[AnunciosService, Depends(get_service)],
) -> PlanningDetail:
    return await service.create_planning(actor, payload)


@router.get("/planejamentos/{planning_uuid}", response_model=PlanningDetail)
async def get_planning(
    actor: Annotated[RequestActor, Depends(get_current_user)],
    service: Annotated[AnunciosService, Depends(get_service)],
    planning_uuid: UUID,
) -> PlanningDetail:
    return await service.get_admin_planning(actor, planning_uuid)


@router.patch("/planejamentos/{planning_uuid}", response_model=PlanningDetail)
async def update_planning(
    payload: PlanningUpdate,
    actor: Annotated[RequestActor, Depends(get_current_user)],
    service: Annotated[AnunciosService, Depends(get_service)],
    planning_uuid: UUID,
) -> PlanningDetail:
    return await service.update_planning(actor, planning_uuid, payload)


@router.get("/dashboard", response_model=DashboardResponse)
async def dashboard(
    actor: Annotated[RequestActor, Depends(get_current_user)],
    service: Annotated[AnunciosService, Depends(get_service)],
    data_inicio: date | None = None,
    data_fim: date | None = None,
    equipe_id: int | None = Query(default=None, ge=1),
    usuario_id: int | None = Query(default=None, ge=1),
    material_id: int | None = Query(default=None, ge=1),
    rota_id: int | None = Query(default=None, ge=1),
    territorio_id: int | None = Query(default=None, ge=1),
    status_rota: str | None = Query(default=None, alias="status"),
) -> DashboardResponse:
    return await service.dashboard(
        actor,
        start=data_inicio or date.today(),
        end=data_fim or date.today(),
        team_id=equipe_id,
        user_id=usuario_id,
        material_id=material_id,
        route_id=rota_id,
        territory_id=territorio_id,
        status=status_rota,
    )


@router.get("/app/rotas", response_model=Page[PlanningResponse])
async def app_routes(
    actor: Annotated[RequestActor, Depends(get_current_user)],
    service: Annotated[AnunciosService, Depends(get_service)],
    params: Annotated[ListParams, Depends(list_params)],
) -> Page[PlanningResponse]:
    return await service.app_routes(actor, params)


@router.get("/app/rotas/{route_uuid}", response_model=PlanningDetail)
async def app_route(
    actor: Annotated[RequestActor, Depends(get_current_user)],
    service: Annotated[AnunciosService, Depends(get_service)],
    route_uuid: UUID,
) -> PlanningDetail:
    return await service.app_route(actor, route_uuid)


async def _read_photo(
    photo: UploadFile | None, *, required: bool
) -> tuple[str, str | None, bytes] | None:
    if photo is None:
        if required:
            raise BusinessRuleError("Uma fotografia do local e obrigatoria.", code="photo_required")
        return None
    limit = get_settings().photo_max_file_mb * 1024 * 1024
    content = await photo.read(limit + 1)
    return photo.filename or "foto.jpg", photo.content_type, content


def _validate_idempotency_header(payload_key: str, header_key: str | None) -> None:
    if header_key is not None and header_key != payload_key:
        raise BusinessRuleError(
            "A chave Idempotency-Key difere da chave enviada no formulario.",
            code="idempotency_key_mismatch",
        )


@router.post(
    "/app/pontos/{point_uuid}/instalar",
    response_model=OperationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def install_point(
    actor: Annotated[RequestActor, Depends(get_current_user)],
    service: Annotated[AnunciosService, Depends(get_service)],
    dados: Annotated[str, Form()],
    foto: Annotated[UploadFile, File()],
    point_uuid: UUID,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> OperationResponse:
    payload = InstallationInput.model_validate_json(dados)
    _validate_idempotency_header(payload.chave_idempotencia, idempotency_key)
    photo = await _read_photo(foto, required=True)
    assert photo is not None
    return await service.install(actor, point_uuid, payload, photo=photo)


@router.post(
    "/app/pontos/{point_uuid}/retirar",
    response_model=OperationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def withdraw_point(
    actor: Annotated[RequestActor, Depends(get_current_user)],
    service: Annotated[AnunciosService, Depends(get_service)],
    dados: Annotated[str, Form()],
    point_uuid: UUID,
    foto: Annotated[UploadFile | None, File()] = None,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> OperationResponse:
    payload = WithdrawalInput.model_validate_json(dados)
    _validate_idempotency_header(payload.chave_idempotencia, idempotency_key)
    photo = await _read_photo(foto, required=False)
    return await service.withdraw(actor, point_uuid, payload, photo=photo)
