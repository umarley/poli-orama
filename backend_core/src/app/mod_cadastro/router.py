from datetime import date
from ipaddress import ip_address
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.access import (
    RequestActor,
    TerritorialAccess,
    get_db_session,
    get_territorial_access,
    require_permission,
)
from app.core.pagination import ListParams, Page, list_params
from app.mod_cadastro.repository import CadastroRepository
from app.mod_cadastro.service import CadastroService
from app.schemas.cadastro import (
    EleitorCreate,
    EleitorResponse,
    LiderancaCreate,
    LiderancaResponse,
    PessoaContatoCreate,
    PessoaContatoResponse,
    PessoaContatoUpdate,
    PessoaDocumentoCreate,
    PessoaDocumentoResponse,
    PessoaDocumentoUpdate,
    PessoaEnderecoCreate,
    PessoaEnderecoResponse,
    PessoaEnderecoUpdate,
    PessoaUpdate,
)
from app.schemas.cadastro_operacional import (
    BuscaRapidaItem,
    ComplementoPoliticoInput,
    ComplementoPoliticoResponse,
    ComunidadeInput,
    ComunidadeResponse,
    EstadoCivilResponse,
    HierarquiaInput,
    HierarquiaResponse,
    IndicacaoGraphResponse,
    IndicacaoInput,
    IndicacaoResponse,
    LiderancaOperacionalResponse,
    NucleoFamiliarInput,
    NucleoFamiliarResponse,
    PessoaCadastroCreate,
    PessoaDetalheResponse,
    PessoaFiltros,
    PessoaListItem,
    PessoaMergePreview,
    PessoaMergeRequest,
    PessoaMergeResponse,
    PessoaRedeSocialInput,
    PessoaRedeSocialResponse,
    PessoaTipoResponse,
    RelacionamentoInput,
    RelacionamentoResponse,
    SuspeitaDuplicidadeResolve,
    SuspeitaDuplicidadeResponse,
    TagInput,
    TagResponse,
    TagUpdate,
    ValidacaoInput,
    ValidacaoResolve,
    ValidacaoResponse,
    VinculoComunidadeInput,
    VinculoNucleoInput,
    VinculoNucleoResponse,
    VinculoTagInput,
)

router = APIRouter(prefix="/cadastro", tags=["Cadastro"])


class TypeIdsInput(BaseModel):
    tipo_ids: list[int] = Field(max_length=20)


def get_cadastro_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CadastroService:
    return CadastroService(CadastroRepository(session))


@router.get(
    "/indicacoes/grafo",
    response_model=IndicacaoGraphResponse,
    summary="Retorna a rede filtravel de indicacoes",
)
async def indication_graph(
    actor: Annotated[RequestActor, Depends(require_permission("cadastro", "visualizar"))],
    service: Annotated[CadastroService, Depends(get_cadastro_service)],
    pessoa_id: int | None = Query(default=None, ge=1),
    origem: str | None = Query(default=None, max_length=60),
    data_inicial: date | None = None,
    data_final: date | None = None,
    profundidade: int = Query(default=3, ge=1, le=6),
    limite: int = Query(default=300, ge=1, le=500),
) -> IndicacaoGraphResponse:
    return await service.indication_graph(
        actor,
        person_id=pessoa_id,
        origin=origem,
        date_from=data_inicial,
        date_to=data_final,
        depth=profundidade,
        limit=limite,
    )


@router.get(
    "/pessoas/busca-rapida",
    response_model=list[BuscaRapidaItem],
    summary="Busca pessoas por nome, documento ou telefone",
)
async def quick_search(
    actor: Annotated[RequestActor, Depends(require_permission("cadastro", "visualizar"))],
    territorial_access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[CadastroService, Depends(get_cadastro_service)],
    query: str = Query(min_length=2, max_length=180),
    limit: int = Query(default=10, ge=1, le=50),
) -> list[BuscaRapidaItem]:
    return await service.quick_search(actor, query, limit, territorial_access)


@router.get(
    "/pessoas/tipos",
    response_model=list[PessoaTipoResponse],
    summary="Lista tipos de pessoa",
)
async def list_person_types(
    _: Annotated[RequestActor, Depends(require_permission("cadastro", "visualizar"))],
    service: Annotated[CadastroService, Depends(get_cadastro_service)],
) -> list[PessoaTipoResponse]:
    return await service.list_types()


@router.get(
    "/estados-civis",
    response_model=list[EstadoCivilResponse],
    summary="Lista estados civis",
)
async def list_marital_statuses(
    _: Annotated[RequestActor, Depends(require_permission("cadastro", "visualizar"))],
    service: Annotated[CadastroService, Depends(get_cadastro_service)],
) -> list[EstadoCivilResponse]:
    return await service.list_marital_statuses()


@router.get(
    "/pessoas",
    response_model=Page[PessoaListItem],
    summary="Lista pessoas com paginacao e filtros",
)
async def list_people(
    params: Annotated[ListParams, Depends(list_params)],
    actor: Annotated[RequestActor, Depends(require_permission("cadastro", "visualizar"))],
    territorial_access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[CadastroService, Depends(get_cadastro_service)],
    nome: str | None = Query(default=None, max_length=180),
    cpf: str | None = Query(default=None, max_length=14),
    telefone: str | None = Query(default=None, max_length=20),
    tipo_id: int | None = Query(default=None, ge=1),
    lideranca_id: int | None = Query(default=None, ge=1),
    territorio_id: int | None = Query(default=None, ge=1),
    tag_id: int | None = Query(default=None, ge=1),
    incluir_inativos: bool = False,
) -> Page[PessoaListItem]:
    filters = PessoaFiltros(
        nome=nome,
        cpf=cpf,
        telefone=telefone,
        tipo_id=tipo_id,
        lideranca_id=lideranca_id,
        territorio_id=territorio_id,
        tag_id=tag_id,
        incluir_inativos=incluir_inativos,
    )
    return await service.list_people(actor, params, filters, territorial_access)


@router.post(
    "/pessoas",
    response_model=PessoaDetalheResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cria cadastro completo de pessoa",
)
async def create_person(
    payload: PessoaCadastroCreate,
    request: Request,
    actor: Annotated[RequestActor, Depends(require_permission("cadastro", "criar"))],
    service: Annotated[CadastroService, Depends(get_cadastro_service)],
) -> PessoaDetalheResponse:
    return await service.create_person(
        actor,
        payload,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


@router.get(
    "/pessoas/{person_id}",
    response_model=PessoaDetalheResponse,
    summary="Retorna detalhe consolidado da pessoa",
)
async def get_person(
    actor: Annotated[RequestActor, Depends(require_permission("cadastro", "visualizar"))],
    territorial_access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[CadastroService, Depends(get_cadastro_service)],
    person_id: int = Path(ge=1),
) -> PessoaDetalheResponse:
    await service.ensure_person_territorial_access(actor, person_id, territorial_access)
    return await service.get_person(actor, person_id)


@router.patch(
    "/pessoas/{person_id}",
    response_model=PessoaDetalheResponse,
    summary="Atualiza parcialmente uma pessoa",
)
async def update_person(
    payload: PessoaUpdate,
    request: Request,
    actor: Annotated[RequestActor, Depends(require_permission("cadastro", "editar"))],
    service: Annotated[CadastroService, Depends(get_cadastro_service)],
    person_id: int = Path(ge=1),
) -> PessoaDetalheResponse:
    return await service.update_person(
        actor,
        person_id,
        payload,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


@router.delete(
    "/pessoas/{person_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Inativa uma pessoa sem apagar o historico",
)
async def deactivate_person(
    request: Request,
    actor: Annotated[RequestActor, Depends(require_permission("cadastro", "excluir"))],
    service: Annotated[CadastroService, Depends(get_cadastro_service)],
    person_id: int = Path(ge=1),
) -> Response:
    await service.deactivate_person(
        actor,
        person_id,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/pessoas/{person_id}/documentos",
    response_model=PessoaDocumentoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_document(
    payload: PessoaDocumentoCreate,
    actor: Annotated[RequestActor, Depends(require_permission("cadastro", "editar"))],
    service: Annotated[CadastroService, Depends(get_cadastro_service)],
    person_id: int = Path(ge=1),
) -> PessoaDocumentoResponse:
    return await service.add_document(actor, person_id, payload)


@router.patch(
    "/pessoas/{person_id}/documentos/{document_id}",
    response_model=PessoaDocumentoResponse,
)
async def update_document(
    payload: PessoaDocumentoUpdate,
    actor: Annotated[RequestActor, Depends(require_permission("cadastro", "editar"))],
    service: Annotated[CadastroService, Depends(get_cadastro_service)],
    person_id: int = Path(ge=1),
    document_id: int = Path(ge=1),
) -> PessoaDocumentoResponse:
    return await service.update_document(actor, person_id, document_id, payload)


@router.post(
    "/pessoas/{person_id}/contatos",
    response_model=PessoaContatoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_contact(
    payload: PessoaContatoCreate,
    actor: Annotated[RequestActor, Depends(require_permission("cadastro", "editar"))],
    service: Annotated[CadastroService, Depends(get_cadastro_service)],
    person_id: int = Path(ge=1),
) -> PessoaContatoResponse:
    return await service.add_contact(actor, person_id, payload)


@router.patch(
    "/pessoas/{person_id}/contatos/{contact_id}",
    response_model=PessoaContatoResponse,
)
async def update_contact(
    payload: PessoaContatoUpdate,
    actor: Annotated[RequestActor, Depends(require_permission("cadastro", "editar"))],
    service: Annotated[CadastroService, Depends(get_cadastro_service)],
    person_id: int = Path(ge=1),
    contact_id: int = Path(ge=1),
) -> PessoaContatoResponse:
    return await service.update_contact(actor, person_id, contact_id, payload)


@router.post(
    "/pessoas/{person_id}/redes-sociais",
    response_model=PessoaRedeSocialResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_social(
    payload: PessoaRedeSocialInput,
    actor: Annotated[RequestActor, Depends(require_permission("cadastro", "editar"))],
    service: Annotated[CadastroService, Depends(get_cadastro_service)],
    person_id: int = Path(ge=1),
) -> PessoaRedeSocialResponse:
    return await service.add_social(actor, person_id, payload)


@router.post(
    "/pessoas/{person_id}/enderecos",
    response_model=PessoaEnderecoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_address(
    payload: PessoaEnderecoCreate,
    actor: Annotated[RequestActor, Depends(require_permission("cadastro", "editar"))],
    service: Annotated[CadastroService, Depends(get_cadastro_service)],
    person_id: int = Path(ge=1),
) -> PessoaEnderecoResponse:
    return await service.add_address(actor, person_id, payload)


@router.patch(
    "/pessoas/{person_id}/enderecos/{address_id}",
    response_model=PessoaEnderecoResponse,
)
async def update_address(
    payload: PessoaEnderecoUpdate,
    actor: Annotated[RequestActor, Depends(require_permission("cadastro", "editar"))],
    service: Annotated[CadastroService, Depends(get_cadastro_service)],
    person_id: int = Path(ge=1),
    address_id: int = Path(ge=1),
) -> PessoaEnderecoResponse:
    return await service.update_address(actor, person_id, address_id, payload)


@router.put(
    "/pessoas/{person_id}/eleitor",
    response_model=EleitorResponse,
)
async def set_voter(
    payload: EleitorCreate,
    actor: Annotated[RequestActor, Depends(require_permission("cadastro", "editar"))],
    service: Annotated[CadastroService, Depends(get_cadastro_service)],
    person_id: int = Path(ge=1),
) -> EleitorResponse:
    return await service.set_voter(actor, person_id, payload)


@router.put(
    "/pessoas/{person_id}/tipos",
    response_model=list[PessoaTipoResponse],
)
async def replace_person_types(
    payload: TypeIdsInput,
    actor: Annotated[RequestActor, Depends(require_permission("cadastro", "editar"))],
    service: Annotated[CadastroService, Depends(get_cadastro_service)],
    person_id: int = Path(ge=1),
) -> list[PessoaTipoResponse]:
    return await service.replace_types(actor, person_id, payload.tipo_ids)


@router.put(
    "/pessoas/{person_id}/lideranca",
    response_model=LiderancaResponse,
)
async def set_leadership(
    payload: LiderancaCreate,
    actor: Annotated[RequestActor, Depends(require_permission("cadastro", "editar"))],
    service: Annotated[CadastroService, Depends(get_cadastro_service)],
    person_id: int = Path(ge=1),
) -> LiderancaResponse:
    return await service.set_leadership(actor, person_id, payload)


@router.get("/liderancas", response_model=list[LiderancaOperacionalResponse])
async def list_leaderships(
    actor: Annotated[RequestActor, Depends(require_permission("cadastro", "visualizar"))],
    service: Annotated[CadastroService, Depends(get_cadastro_service)],
) -> list[LiderancaOperacionalResponse]:
    return await service.list_leaderships(actor)


@router.get("/hierarquia", response_model=list[HierarquiaResponse])
async def list_hierarchy(
    actor: Annotated[RequestActor, Depends(require_permission("cadastro", "visualizar"))],
    service: Annotated[CadastroService, Depends(get_cadastro_service)],
) -> list[HierarquiaResponse]:
    return await service.list_hierarchy(actor)


@router.post(
    "/hierarquia",
    response_model=HierarquiaResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_hierarchy(
    payload: HierarquiaInput,
    actor: Annotated[RequestActor, Depends(require_permission("cadastro", "editar"))],
    service: Annotated[CadastroService, Depends(get_cadastro_service)],
) -> HierarquiaResponse:
    return await service.add_hierarchy(actor, payload)


@router.post(
    "/pessoas/{person_id}/indicacoes",
    response_model=IndicacaoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_indication(
    payload: IndicacaoInput,
    actor: Annotated[RequestActor, Depends(require_permission("cadastro", "editar"))],
    service: Annotated[CadastroService, Depends(get_cadastro_service)],
    person_id: int = Path(ge=1),
) -> IndicacaoResponse:
    return await service.add_indication(actor, person_id, payload)


@router.post(
    "/pessoas/{person_id}/relacionamentos",
    response_model=RelacionamentoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_relationship(
    payload: RelacionamentoInput,
    actor: Annotated[RequestActor, Depends(require_permission("cadastro", "editar"))],
    service: Annotated[CadastroService, Depends(get_cadastro_service)],
    person_id: int = Path(ge=1),
) -> RelacionamentoResponse:
    return await service.add_relationship(actor, person_id, payload)


@router.put(
    "/pessoas/{person_id}/complemento-politico",
    response_model=ComplementoPoliticoResponse,
)
async def set_political_complement(
    payload: ComplementoPoliticoInput,
    actor: Annotated[RequestActor, Depends(require_permission("cadastro", "editar"))],
    service: Annotated[CadastroService, Depends(get_cadastro_service)],
    person_id: int = Path(ge=1),
) -> ComplementoPoliticoResponse:
    return await service.set_political(actor, person_id, payload)


@router.post(
    "/pessoas/{person_id}/validacoes",
    response_model=ValidacaoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_validation(
    payload: ValidacaoInput,
    actor: Annotated[RequestActor, Depends(require_permission("cadastro", "editar"))],
    service: Annotated[CadastroService, Depends(get_cadastro_service)],
    person_id: int = Path(ge=1),
) -> ValidacaoResponse:
    return await service.create_validation(actor, person_id, payload)


@router.patch(
    "/validacoes/{validation_id}",
    response_model=ValidacaoResponse,
)
async def resolve_validation(
    payload: ValidacaoResolve,
    actor: Annotated[RequestActor, Depends(require_permission("cadastro", "editar"))],
    service: Annotated[CadastroService, Depends(get_cadastro_service)],
    validation_id: int = Path(ge=1),
) -> ValidacaoResponse:
    return await service.resolve_validation(actor, validation_id, payload)


@router.get(
    "/validacoes",
    response_model=list[ValidacaoResponse],
)
async def list_validations(
    actor: Annotated[RequestActor, Depends(require_permission("cadastro", "visualizar"))],
    service: Annotated[CadastroService, Depends(get_cadastro_service)],
    validation_status: str | None = Query(
        default=None,
        alias="status",
        pattern=r"^(pendente|aprovado|rejeitado|em_revisao)$",
    ),
) -> list[ValidacaoResponse]:
    return await service.list_validations(actor, validation_status)


@router.get(
    "/nucleos-familiares",
    response_model=list[NucleoFamiliarResponse],
)
async def list_nuclei(
    actor: Annotated[RequestActor, Depends(require_permission("cadastro", "visualizar"))],
    service: Annotated[CadastroService, Depends(get_cadastro_service)],
) -> list[NucleoFamiliarResponse]:
    return await service.list_nuclei(actor)


@router.post(
    "/nucleos-familiares",
    response_model=NucleoFamiliarResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_nucleus(
    payload: NucleoFamiliarInput,
    actor: Annotated[RequestActor, Depends(require_permission("cadastro", "criar"))],
    service: Annotated[CadastroService, Depends(get_cadastro_service)],
) -> NucleoFamiliarResponse:
    return await service.create_nucleus(actor, payload)


@router.post(
    "/nucleos-familiares/{nucleus_id}/pessoas",
    response_model=VinculoNucleoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_nucleus_member(
    payload: VinculoNucleoInput,
    actor: Annotated[RequestActor, Depends(require_permission("cadastro", "editar"))],
    service: Annotated[CadastroService, Depends(get_cadastro_service)],
    nucleus_id: int = Path(ge=1),
) -> VinculoNucleoResponse:
    return await service.add_nucleus_member(actor, nucleus_id, payload)


@router.get(
    "/comunidades",
    response_model=list[ComunidadeResponse],
)
async def list_communities(
    actor: Annotated[RequestActor, Depends(require_permission("cadastro", "visualizar"))],
    service: Annotated[CadastroService, Depends(get_cadastro_service)],
) -> list[ComunidadeResponse]:
    return await service.list_communities(actor)


@router.post(
    "/comunidades",
    response_model=ComunidadeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_community(
    payload: ComunidadeInput,
    actor: Annotated[RequestActor, Depends(require_permission("cadastro", "criar"))],
    service: Annotated[CadastroService, Depends(get_cadastro_service)],
) -> ComunidadeResponse:
    return await service.create_community(actor, payload)


@router.post(
    "/comunidades/{community_id}/pessoas",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def add_community_member(
    payload: VinculoComunidadeInput,
    actor: Annotated[RequestActor, Depends(require_permission("cadastro", "editar"))],
    service: Annotated[CadastroService, Depends(get_cadastro_service)],
    community_id: int = Path(ge=1),
) -> Response:
    await service.add_community_member(actor, community_id, payload)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/tags",
    response_model=list[TagResponse],
)
async def list_tags(
    actor: Annotated[RequestActor, Depends(require_permission("cadastro", "visualizar"))],
    service: Annotated[CadastroService, Depends(get_cadastro_service)],
) -> list[TagResponse]:
    return await service.list_tags(actor)


@router.post(
    "/tags",
    response_model=TagResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_tag(
    payload: TagInput,
    actor: Annotated[RequestActor, Depends(require_permission("cadastro", "criar"))],
    service: Annotated[CadastroService, Depends(get_cadastro_service)],
) -> TagResponse:
    return await service.create_tag(actor, payload)


@router.patch(
    "/tags/{tag_id}",
    response_model=TagResponse,
)
async def update_tag(
    payload: TagUpdate,
    actor: Annotated[RequestActor, Depends(require_permission("cadastro", "editar"))],
    service: Annotated[CadastroService, Depends(get_cadastro_service)],
    tag_id: int = Path(ge=1),
) -> TagResponse:
    return await service.update_tag(actor, tag_id, payload)


@router.post(
    "/tags/{tag_id}/pessoas",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def add_person_tag(
    payload: VinculoTagInput,
    actor: Annotated[RequestActor, Depends(require_permission("cadastro", "editar"))],
    service: Annotated[CadastroService, Depends(get_cadastro_service)],
    tag_id: int = Path(ge=1),
) -> Response:
    await service.add_person_tag(actor, tag_id, payload.pessoa_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/duplicidades",
    response_model=list[SuspeitaDuplicidadeResponse],
)
async def list_duplicates(
    actor: Annotated[RequestActor, Depends(require_permission("cadastro", "visualizar"))],
    service: Annotated[CadastroService, Depends(get_cadastro_service)],
    duplicate_status: str | None = Query(
        default=None,
        alias="status",
        pattern=r"^(pendente|confirmada|descartada|mesclada)$",
    ),
) -> list[SuspeitaDuplicidadeResponse]:
    return await service.list_duplicates(actor, duplicate_status)


@router.get(
    "/duplicidades/{duplicate_id}/merge-preview",
    response_model=PessoaMergePreview,
    summary="Compara os cadastros antes da mesclagem",
)
async def preview_duplicate_merge(
    actor: Annotated[RequestActor, Depends(require_permission("cadastro", "visualizar"))],
    service: Annotated[CadastroService, Depends(get_cadastro_service)],
    duplicate_id: int = Path(ge=1),
) -> PessoaMergePreview:
    return await service.merge_preview(actor, duplicate_id)


@router.post(
    "/duplicidades/{duplicate_id}/merge",
    response_model=PessoaMergeResponse,
    summary="Mescla dois cadastros duplicados de forma auditavel",
)
async def merge_duplicate(
    payload: PessoaMergeRequest,
    request: Request,
    actor: Annotated[RequestActor, Depends(require_permission("cadastro", "editar"))],
    service: Annotated[CadastroService, Depends(get_cadastro_service)],
    duplicate_id: int = Path(ge=1),
) -> PessoaMergeResponse:
    return await service.merge_duplicate(
        actor,
        duplicate_id,
        payload,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


@router.patch(
    "/duplicidades/{duplicate_id}",
    response_model=SuspeitaDuplicidadeResponse,
)
async def resolve_duplicate(
    payload: SuspeitaDuplicidadeResolve,
    actor: Annotated[RequestActor, Depends(require_permission("cadastro", "editar"))],
    service: Annotated[CadastroService, Depends(get_cadastro_service)],
    duplicate_id: int = Path(ge=1),
) -> SuspeitaDuplicidadeResponse:
    return await service.resolve_duplicate(actor, duplicate_id, payload)


def _client_ip(request: Request) -> str | None:
    if request.client is None:
        return None
    try:
        return str(ip_address(request.client.host))
    except ValueError:
        return None
