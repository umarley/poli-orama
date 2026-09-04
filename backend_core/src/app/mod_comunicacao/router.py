from datetime import datetime
from ipaddress import ip_address
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, Path, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.access import (
    RequestActor,
    TerritorialAccess,
    get_db_session,
    get_territorial_access,
    require_any_profile,
    require_permission,
)
from app.mod_comunicacao.atendimento_repository import AtendimentoRepository
from app.mod_comunicacao.atendimento_schemas import (
    AttendanceClose,
    AttendanceDocumentInput,
    AttendanceIndicators,
    AttendanceInteractionInput,
    AttendanceInvalidate,
    AttendancePersonUpdate,
    AttendanceQueue,
    AttendanceResponse,
    AttendanceResult,
    AttendanceUpdate,
    CommunicationChannel,
    IndicatorFilters,
    RejectionReason,
)
from app.mod_comunicacao.atendimento_service import AtendimentoService
from app.mod_comunicacao.repository import ComunicacaoRepository
from app.mod_comunicacao.schemas import (
    CatalogInput,
    CatalogResponse,
    CatalogUpdate,
    InteracaoInput,
    InteracaoResponse,
)
from app.mod_comunicacao.service import ComunicacaoService
from app.schemas.cadastro import PessoaContatoCreate, PessoaContatoUpdate

router = APIRouter(prefix="/comunicacao", tags=["Comunicacao"])

CatalogName = Literal["tipos-interacao", "canais"]
ModuleViewer = Annotated[RequestActor, Depends(require_any_profile("telefonista", "gestor"))]
Operator = Annotated[RequestActor, Depends(require_any_profile("telefonista"))]
Reporter = Annotated[RequestActor, Depends(require_any_profile("gestor"))]
CampaignHeader = Annotated[str | None, Header(alias="X-Campaign-ID")]


def get_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ComunicacaoService:
    return ComunicacaoService(ComunicacaoRepository(session))


def get_attendance_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AtendimentoService:
    return AtendimentoService(AtendimentoRepository(session))


@router.get("/atendimento/motivos-rejeicao", response_model=list[RejectionReason])
async def list_rejection_reasons(
    actor: ModuleViewer,
    service: Annotated[AtendimentoService, Depends(get_attendance_service)],
) -> list[RejectionReason]:
    return await service.list_rejection_reasons(actor)


@router.get("/atendimento/canais", response_model=list[CommunicationChannel])
async def list_attendance_channels(
    actor: ModuleViewer,
    service: Annotated[AtendimentoService, Depends(get_attendance_service)],
) -> list[CommunicationChannel]:
    return await service.list_channels(actor)


@router.get("/atendimento/atual", response_model=AttendanceResponse | None)
async def current_attendance(
    actor: Operator,
    service: Annotated[AtendimentoService, Depends(get_attendance_service)],
) -> AttendanceResponse | None:
    return await service.current(actor)


@router.get("/atendimento/abertos", response_model=AttendanceQueue)
async def open_attendances(
    actor: Operator,
    service: Annotated[AtendimentoService, Depends(get_attendance_service)],
) -> AttendanceQueue:
    return await service.open_queue(actor)


@router.post(
    "/atendimento/iniciar",
    response_model=AttendanceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_attendance(
    actor: Operator,
    service: Annotated[AtendimentoService, Depends(get_attendance_service)],
    campaign: CampaignHeader = None,
) -> AttendanceResponse:
    return await service.start(actor, campaign)


@router.get("/atendimento/{attendance_id}", response_model=AttendanceResponse)
async def get_attendance(
    actor: ModuleViewer,
    service: Annotated[AtendimentoService, Depends(get_attendance_service)],
    attendance_id: int = Path(ge=1),
) -> AttendanceResponse:
    return await service.get(actor, attendance_id)


@router.patch("/atendimento/{attendance_id}", response_model=AttendanceResponse)
async def update_attendance(
    payload: AttendanceUpdate,
    actor: Operator,
    service: Annotated[AtendimentoService, Depends(get_attendance_service)],
    attendance_id: int = Path(ge=1),
) -> AttendanceResponse:
    return await service.update(actor, attendance_id, payload)


@router.patch("/atendimento/{attendance_id}/pessoa", response_model=AttendanceResponse)
async def update_attendance_person(
    payload: AttendancePersonUpdate,
    actor: Operator,
    service: Annotated[AtendimentoService, Depends(get_attendance_service)],
    attendance_id: int = Path(ge=1),
) -> AttendanceResponse:
    return await service.update_person(actor, attendance_id, payload)


@router.post("/atendimento/{attendance_id}/documentos", response_model=AttendanceResponse)
async def add_attendance_document(
    payload: AttendanceDocumentInput,
    actor: Operator,
    service: Annotated[AtendimentoService, Depends(get_attendance_service)],
    attendance_id: int = Path(ge=1),
) -> AttendanceResponse:
    return await service.add_document(actor, attendance_id, payload)


@router.post("/atendimento/{attendance_id}/interacoes", response_model=AttendanceResponse)
async def add_attendance_interaction(
    payload: AttendanceInteractionInput,
    actor: Operator,
    service: Annotated[AtendimentoService, Depends(get_attendance_service)],
    attendance_id: int = Path(ge=1),
) -> AttendanceResponse:
    return await service.add_interaction(actor, attendance_id, payload)


@router.post(
    "/atendimento/{attendance_id}/contatos",
    response_model=AttendanceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_attendance_contact(
    payload: PessoaContatoCreate,
    actor: Operator,
    service: Annotated[AtendimentoService, Depends(get_attendance_service)],
    attendance_id: int = Path(ge=1),
) -> AttendanceResponse:
    return await service.add_contact(actor, attendance_id, payload)


@router.patch(
    "/atendimento/{attendance_id}/contatos/{contact_id}",
    response_model=AttendanceResponse,
)
async def update_attendance_contact(
    payload: PessoaContatoUpdate,
    actor: Operator,
    service: Annotated[AtendimentoService, Depends(get_attendance_service)],
    attendance_id: int = Path(ge=1),
    contact_id: int = Path(ge=1),
) -> AttendanceResponse:
    return await service.update_contact(actor, attendance_id, contact_id, payload)


@router.delete(
    "/atendimento/{attendance_id}/contatos/{contact_id}",
    response_model=AttendanceResponse,
)
async def delete_attendance_contact(
    actor: Operator,
    service: Annotated[AtendimentoService, Depends(get_attendance_service)],
    attendance_id: int = Path(ge=1),
    contact_id: int = Path(ge=1),
) -> AttendanceResponse:
    return await service.delete_contact(actor, attendance_id, contact_id)


@router.post("/atendimento/{attendance_id}/encerrar", response_model=AttendanceResponse)
async def close_attendance(
    payload: AttendanceClose,
    actor: Operator,
    service: Annotated[AtendimentoService, Depends(get_attendance_service)],
    attendance_id: int = Path(ge=1),
) -> AttendanceResponse:
    return await service.close(actor, attendance_id, payload)


@router.post("/atendimento/{attendance_id}/invalidar", response_model=AttendanceResponse)
async def invalidate_attendance(
    payload: AttendanceInvalidate,
    actor: Operator,
    service: Annotated[AtendimentoService, Depends(get_attendance_service)],
    attendance_id: int = Path(ge=1),
) -> AttendanceResponse:
    return await service.invalidate(actor, attendance_id, payload)


@router.get("/indicadores", response_model=AttendanceIndicators)
async def attendance_indicators(
    actor: Reporter,
    service: Annotated[AtendimentoService, Depends(get_attendance_service)],
    campaign: CampaignHeader = None,
    inicio: datetime | None = None,
    fim: datetime | None = None,
    atendente_usuario_id: int | None = Query(default=None, ge=1),
    canal: int | None = Query(default=None, ge=1),
    situacao: Literal[
        "em_atendimento", "concluido", "sem_resposta", "numero_invalido", "interrompido"
    ]
    | None = None,
    resultado: AttendanceResult | None = None,
) -> AttendanceIndicators:
    return await service.indicators(
        actor,
        campaign,
        IndicatorFilters(
            inicio=inicio,
            fim=fim,
            atendente_usuario_id=atendente_usuario_id,
            canal=canal,
            situacao=situacao,
            resultado=resultado,
        ),
    )


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
