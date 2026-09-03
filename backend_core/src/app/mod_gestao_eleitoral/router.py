from typing import Annotated, Literal, TypeVar

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.access import (
    RequestActor,
    TerritorialAccess,
    get_db_session,
    get_territorial_access,
    require_any_profile,
)
from app.mod_gestao_eleitoral.repository import GestaoEleitoralRepository
from app.mod_gestao_eleitoral.schemas import (
    CandidateOption,
    ElectionOption,
    MapResponse,
    NamedOption,
    NumericOption,
    PaginatedDistribution,
    PanelResponse,
    ResultadoFilters,
)
from app.mod_gestao_eleitoral.service import GestaoEleitoralService

router = APIRouter(prefix="/gestao-eleitoral", tags=["Gestao eleitoral"])

Viewer = Annotated[
    RequestActor,
    Depends(require_any_profile("gestor", "gestor_saas", "coordenador_territorial")),
]
Access = Annotated[TerritorialAccess, Depends(get_territorial_access)]


def get_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GestaoEleitoralService:
    return GestaoEleitoralService(GestaoEleitoralRepository(session))


T = TypeVar("T")


def as_list(value: list[T] | T | None) -> list[T]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def filters(
    eleicao_chaves: Annotated[list[str] | None, Query()] = None,
    nm_votaveis: Annotated[list[str] | None, Query()] = None,
    sg_uf: Annotated[list[str] | None, Query()] = None,
    cd_municipio: Annotated[list[int] | None, Query()] = None,
    ds_cargo: Annotated[list[str] | None, Query()] = None,
    nr_zona: Annotated[list[int] | None, Query()] = None,
    nr_local_votacao: Annotated[list[int] | None, Query()] = None,
    nr_secao: Annotated[list[int] | None, Query()] = None,
) -> ResultadoFilters:
    return ResultadoFilters(
        eleicao_chaves=as_list(eleicao_chaves),
        nm_votaveis=as_list(nm_votaveis),
        sg_uf=[item.upper() for item in as_list(sg_uf) if item],
        cd_municipio=as_list(cd_municipio),
        ds_cargo=as_list(ds_cargo),
        nr_zona=as_list(nr_zona),
        nr_local_votacao=as_list(nr_local_votacao),
        nr_secao=as_list(nr_secao),
    )


Service = Annotated[GestaoEleitoralService, Depends(get_service)]
Filter = Annotated[ResultadoFilters, Depends(filters)]


@router.get("/filtros/eleicoes", response_model=list[ElectionOption])
async def list_elections(actor: Viewer, access: Access, service: Service) -> list[ElectionOption]:
    return await service.list_elections(actor, access)


@router.get("/filtros/candidatos", response_model=list[CandidateOption])
async def search_candidates(
    actor: Viewer,
    access: Access,
    service: Service,
    query: Filter,
    q: Annotated[str, Query(min_length=2, max_length=120)],
) -> list[CandidateOption]:
    return await service.search_candidates(actor, access, query, q)


@router.get("/filtros/estados", response_model=list[NamedOption])
async def list_states(
    actor: Viewer, access: Access, service: Service, query: Filter
) -> list[NamedOption] | list[NumericOption]:
    return await service.list_named_options(actor, access, query, "estados")


@router.get("/filtros/municipios", response_model=list[NumericOption])
async def list_municipalities(
    actor: Viewer, access: Access, service: Service, query: Filter
) -> list[NamedOption] | list[NumericOption]:
    return await service.list_named_options(actor, access, query, "municipios")


@router.get("/filtros/cargos", response_model=list[NamedOption])
async def list_offices(
    actor: Viewer, access: Access, service: Service, query: Filter
) -> list[NamedOption] | list[NumericOption]:
    return await service.list_named_options(actor, access, query, "cargos")


@router.get("/filtros/zonas", response_model=list[NumericOption])
async def list_zones(
    actor: Viewer, access: Access, service: Service, query: Filter
) -> list[NamedOption] | list[NumericOption]:
    return await service.list_named_options(actor, access, query, "zonas")


@router.get("/filtros/locais", response_model=list[NumericOption])
async def list_polling_places(
    actor: Viewer, access: Access, service: Service, query: Filter
) -> list[NamedOption] | list[NumericOption]:
    return await service.list_named_options(actor, access, query, "locais")


@router.get("/filtros/secoes", response_model=list[NumericOption])
async def list_sections(
    actor: Viewer, access: Access, service: Service, query: Filter
) -> list[NamedOption] | list[NumericOption]:
    return await service.list_named_options(actor, access, query, "secoes")


@router.get("/painel", response_model=PanelResponse)
async def panel(actor: Viewer, access: Access, service: Service, query: Filter) -> PanelResponse:
    return await service.panel(actor, access, query)


@router.get("/mapa", response_model=MapResponse)
async def map_points(
    actor: Viewer,
    access: Access,
    service: Service,
    query: Filter,
    modo: Annotated[Literal["secao", "zona"], Query()] = "secao",
) -> MapResponse:
    return await service.map_points(actor, access, query, modo)


@router.get("/distribuicao/{dimensao}", response_model=PaginatedDistribution)
async def distribution(
    dimensao: Literal["municipio", "zona", "local", "secao"],
    actor: Viewer,
    access: Access,
    service: Service,
    query: Filter,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=5, le=100)] = 20,
) -> PaginatedDistribution:
    return await service.paginated_distribution(actor, access, query, dimensao, page, page_size)
