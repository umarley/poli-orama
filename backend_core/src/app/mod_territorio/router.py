from decimal import Decimal
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
from app.core.errors import ResourceNotFoundError
from app.mod_territorio.repository import MAP_MESH_TYPES, TerritorioRepository
from app.mod_territorio.schemas import (
    BairroCreate,
    BairroResponse,
    EstadoResponse,
    GeocodificacaoInput,
    GeocodificacaoResponse,
    HierarchyOrganizationApply,
    HierarchyOrganizationPreview,
    HierarchyOrganizationResult,
    LiderancaTerritorioInput,
    LiderancaTerritorioResponse,
    LocalVotacaoResponse,
    MapMarker,
    MapMunicipalityShape,
    MapPerson,
    MapTerritoryShape,
    MunicipioResponse,
    PessoaTerritorioDetalhe,
    PessoaTerritorioInput,
    PessoaTerritorioResponse,
    SecaoEleitoralResponse,
    TerritorioCreate,
    TerritorioDetalheResponse,
    TerritorioResponse,
    TerritorioTreeNode,
    TerritorioUpdate,
    TipoTerritorioCreate,
    TipoTerritorioResponse,
    TipoTerritorioUpdate,
    ZonaEleitoralResponse,
)
from app.mod_territorio.service import TerritorioService

router = APIRouter(tags=["Territorio"])


def get_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TerritorioService:
    return TerritorioService(TerritorioRepository(session))


@router.get("/global/estados", response_model=list[EstadoResponse])
async def list_states(
    _: Annotated[RequestActor, Depends(require_permission("territorio", "visualizar"))],
    service: Annotated[TerritorioService, Depends(get_service)],
) -> list[dict[str, Any]]:
    return await service.repository.global_list("estado")


@router.get("/global/municipios", response_model=list[MunicipioResponse])
async def list_cities(
    _: Annotated[RequestActor, Depends(require_permission("territorio", "visualizar"))],
    service: Annotated[TerritorioService, Depends(get_service)],
    estado_id: int | None = Query(default=None, ge=1),
    nome: str | None = Query(default=None, min_length=1, max_length=120),
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    values: dict[str, object] = {}
    if estado_id:
        clauses.append("codigo_uf_ibge = :estado_id")
        values["estado_id"] = estado_id
    if nome:
        clauses.append("nome ILIKE :nome")
        values["nome"] = f"%{nome}%"
    return await service.repository.global_list("municipio", " AND ".join(clauses), values)


@router.get("/global/bairros", response_model=list[BairroResponse])
async def list_neighborhoods(
    _: Annotated[RequestActor, Depends(require_permission("territorio", "visualizar"))],
    service: Annotated[TerritorioService, Depends(get_service)],
    codigo_municipio_ibge: int = Query(ge=1),
    nome: str | None = Query(default=None, min_length=1, max_length=150),
) -> list[dict[str, Any]]:
    where = "codigo_municipio_ibge = :codigo_municipio_ibge"
    values: dict[str, object] = {"codigo_municipio_ibge": codigo_municipio_ibge}
    if nome:
        where += " AND nome ILIKE :nome"
        values["nome"] = f"%{nome}%"
    return await service.repository.global_list("bairro", where, values)


@router.post(
    "/global/bairros",
    response_model=BairroResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_neighborhood(
    payload: BairroCreate,
    _: Annotated[RequestActor, Depends(require_permission("territorio", "criar"))],
    service: Annotated[TerritorioService, Depends(get_service)],
) -> dict[str, Any]:
    return await service.create_neighborhood(payload)


@router.get("/global/zonas-eleitorais", response_model=list[ZonaEleitoralResponse])
async def list_electoral_zones(
    _: Annotated[RequestActor, Depends(require_permission("territorio", "visualizar"))],
    service: Annotated[TerritorioService, Depends(get_service)],
    estado_id: int | None = Query(default=None, ge=1),
    codigo_municipio_ibge: int | None = Query(default=None, ge=1),
) -> list[dict[str, Any]]:
    return await service.repository.list_electoral_zones(
        estado_id=estado_id,
        codigo_municipio_ibge=codigo_municipio_ibge,
    )


@router.get("/global/locais-votacao", response_model=list[LocalVotacaoResponse])
async def list_polling_places(
    _: Annotated[RequestActor, Depends(require_permission("territorio", "visualizar"))],
    service: Annotated[TerritorioService, Depends(get_service)],
    codigo_municipio_ibge: int | None = Query(default=None, ge=1),
    bairro_id: int | None = Query(default=None, ge=1),
    zona_eleitoral_id: int | None = Query(default=None, ge=1),
    nome: str | None = Query(default=None, min_length=1, max_length=180),
) -> list[dict[str, Any]]:
    clauses = ["situacao = 'ativo'"]
    values: dict[str, object] = {}
    for column, value in {
        "codigo_municipio_ibge": codigo_municipio_ibge,
        "bairro_id": bairro_id,
        "zona_eleitoral_id": zona_eleitoral_id,
    }.items():
        if value:
            clauses.append(f"{column} = :{column}")
            values[column] = value
    if nome:
        clauses.append("nome ILIKE :nome")
        values["nome"] = f"%{nome}%"
    return await service.repository.global_list("local_votacao", " AND ".join(clauses), values)


@router.get("/global/secoes-eleitorais", response_model=list[SecaoEleitoralResponse])
async def list_electoral_sections(
    _: Annotated[RequestActor, Depends(require_permission("territorio", "visualizar"))],
    service: Annotated[TerritorioService, Depends(get_service)],
    zona_eleitoral_id: int = Query(ge=1),
    local_votacao_id: int | None = Query(default=None, ge=1),
) -> list[dict[str, Any]]:
    where = "zona_eleitoral_id = :zona_eleitoral_id"
    values: dict[str, object] = {"zona_eleitoral_id": zona_eleitoral_id}
    if local_votacao_id:
        where += " AND local_votacao_id = :local_votacao_id"
        values["local_votacao_id"] = local_votacao_id
    return await service.repository.global_list("secao_eleitoral", where, values)


@router.get("/territorios/tipos", response_model=list[TipoTerritorioResponse])
async def list_types(
    actor: Annotated[RequestActor, Depends(require_permission("territorio", "visualizar"))],
    service: Annotated[TerritorioService, Depends(get_service)],
    incluir_inativos: bool = False,
) -> list[dict[str, Any]]:
    return await service.repository.list_types(actor.tenant_id, incluir_inativos)


@router.post(
    "/territorios/tipos",
    response_model=TipoTerritorioResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_type(
    payload: TipoTerritorioCreate,
    actor: Annotated[RequestActor, Depends(require_permission("territorio", "criar"))],
    service: Annotated[TerritorioService, Depends(get_service)],
) -> dict[str, Any]:
    return await service.create_type(actor, payload)


@router.patch("/territorios/tipos/{type_id}", response_model=TipoTerritorioResponse)
async def update_type(
    payload: TipoTerritorioUpdate,
    actor: Annotated[RequestActor, Depends(require_permission("territorio", "editar"))],
    service: Annotated[TerritorioService, Depends(get_service)],
    type_id: int = Path(ge=1),
) -> dict[str, Any]:
    return await service.update_type(actor, type_id, payload)


@router.get("/territorios/arvore", response_model=list[TerritorioTreeNode])
async def territory_tree(
    actor: Annotated[RequestActor, Depends(require_permission("territorio", "visualizar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[TerritorioService, Depends(get_service)],
) -> list[TerritorioTreeNode]:
    return await service.tree(actor, access)


@router.get(
    "/territorios/hierarquia/organizacao",
    response_model=HierarchyOrganizationPreview,
)
async def preview_hierarchy_organization(
    actor: Annotated[RequestActor, Depends(require_permission("territorio", "visualizar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[TerritorioService, Depends(get_service)],
) -> HierarchyOrganizationPreview:
    return await service.hierarchy_organization_preview(actor, access)


@router.post(
    "/territorios/hierarquia/organizacao",
    response_model=HierarchyOrganizationResult,
)
async def organize_hierarchy(
    payload: HierarchyOrganizationApply,
    actor: Annotated[RequestActor, Depends(require_permission("territorio", "editar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[TerritorioService, Depends(get_service)],
) -> HierarchyOrganizationResult:
    return await service.organize_hierarchy(actor, access, payload)


@router.get("/territorios/mapa/marcadores", response_model=list[MapMarker])
async def map_markers(
    actor: Annotated[RequestActor, Depends(require_permission("territorio", "visualizar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[TerritorioService, Depends(get_service)],
    territorio_id: int | None = Query(default=None, ge=1),
) -> list[dict[str, Any]]:
    ids = await service.accessible_ids(actor, access)
    if territorio_id:
        await service.ensure_access(actor, access, territorio_id, administer=False)
        ids = {territorio_id}
    return await service.repository.map_markers(actor.tenant_id, ids)


@router.get(
    "/territorios/mapa/municipios",
    response_model=list[MapMunicipalityShape],
)
async def map_municipality_shapes(
    actor: Annotated[RequestActor, Depends(require_permission("territorio", "visualizar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[TerritorioService, Depends(get_service)],
    territorio_id: int | None = Query(default=None, ge=1),
) -> list[dict[str, Any]]:
    ids = await service.accessible_ids(actor, access)
    if territorio_id:
        await service.ensure_access(actor, access, territorio_id, administer=False)
    return await service.repository.map_municipality_shapes(actor.tenant_id, ids, territorio_id)


@router.get(
    "/territorios/mapa/malhas",
    response_model=list[MapTerritoryShape],
)
async def map_territory_shapes(
    actor: Annotated[RequestActor, Depends(require_permission("territorio", "visualizar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[TerritorioService, Depends(get_service)],
    tipo: Annotated[str, Query(min_length=1, max_length=40)],
    territorio_id: int | None = Query(default=None, ge=1),
) -> list[dict[str, Any]]:
    if tipo not in MAP_MESH_TYPES:
        raise ResourceNotFoundError("Tipo de malha", tipo)
    ids = await service.accessible_ids(actor, access)
    if territorio_id:
        await service.ensure_access(actor, access, territorio_id, administer=False)
    return await service.repository.map_territory_shapes(actor.tenant_id, tipo, ids, territorio_id)


@router.get("/territorios/mapa/pessoas", response_model=list[MapPerson])
async def map_people(
    actor: Annotated[RequestActor, Depends(require_permission("territorio", "visualizar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[TerritorioService, Depends(get_service)],
    latitude: Annotated[Decimal, Query(ge=-90, le=90, decimal_places=3)],
    longitude: Annotated[Decimal, Query(ge=-180, le=180, decimal_places=3)],
    territorio_id: int | None = Query(default=None, ge=1),
) -> list[dict[str, Any]]:
    ids = await service.accessible_ids(actor, access)
    if territorio_id:
        await service.ensure_access(actor, access, territorio_id, administer=False)
        ids = {territorio_id}
    return await service.repository.map_people(actor.tenant_id, latitude, longitude, ids)


@router.get("/territorios", response_model=list[TerritorioResponse])
async def list_territories(
    actor: Annotated[RequestActor, Depends(require_permission("territorio", "visualizar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[TerritorioService, Depends(get_service)],
    incluir_inativos: bool = False,
    tipo_territorio_id: int | None = Query(default=None, ge=1),
    query: str | None = Query(default=None, max_length=150),
) -> list[dict[str, Any]]:
    return await service.list_territories(
        actor,
        access,
        include_inactive=incluir_inativos,
        type_id=tipo_territorio_id,
        query=query,
    )


@router.post(
    "/territorios",
    response_model=TerritorioResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_territory(
    payload: TerritorioCreate,
    actor: Annotated[RequestActor, Depends(require_permission("territorio", "criar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[TerritorioService, Depends(get_service)],
) -> dict[str, Any]:
    return await service.create_territory(actor, access, payload)


@router.get("/territorios/{territory_id}/detalhes", response_model=TerritorioDetalheResponse)
async def get_territory_detail(
    actor: Annotated[RequestActor, Depends(require_permission("territorio", "visualizar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[TerritorioService, Depends(get_service)],
    territory_id: int = Path(ge=1),
) -> dict[str, Any]:
    return await service.get_territory_detail(actor, access, territory_id)


@router.get("/territorios/{territory_id}", response_model=TerritorioResponse)
async def get_territory(
    actor: Annotated[RequestActor, Depends(require_permission("territorio", "visualizar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[TerritorioService, Depends(get_service)],
    territory_id: int = Path(ge=1),
) -> dict[str, Any]:
    return await service.ensure_access(actor, access, territory_id, administer=False)


@router.patch("/territorios/{territory_id}", response_model=TerritorioResponse)
async def update_territory(
    payload: TerritorioUpdate,
    actor: Annotated[RequestActor, Depends(require_permission("territorio", "editar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[TerritorioService, Depends(get_service)],
    territory_id: int = Path(ge=1),
) -> dict[str, Any]:
    return await service.update_territory(actor, access, territory_id, payload)


@router.delete("/territorios/{territory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_territory(
    actor: Annotated[RequestActor, Depends(require_permission("territorio", "excluir"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[TerritorioService, Depends(get_service)],
    territory_id: int = Path(ge=1),
) -> Response:
    await service.update_territory(actor, access, territory_id, TerritorioUpdate(ativo=False))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/territorios/{territory_id}/pessoas",
    response_model=PessoaTerritorioResponse,
    status_code=status.HTTP_201_CREATED,
)
async def link_person(
    payload: PessoaTerritorioInput,
    actor: Annotated[RequestActor, Depends(require_permission("territorio", "editar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[TerritorioService, Depends(get_service)],
    territory_id: int = Path(ge=1),
) -> dict[str, Any]:
    return await service.link_person(actor, access, territory_id, payload)


@router.get(
    "/territorios/pessoas/{person_id}",
    response_model=list[PessoaTerritorioDetalhe],
)
async def list_person_links(
    actor: Annotated[RequestActor, Depends(require_permission("territorio", "visualizar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[TerritorioService, Depends(get_service)],
    person_id: int = Path(ge=1),
) -> list[dict[str, Any]]:
    return await service.list_person_links(actor, access, person_id)


@router.delete("/territorios/pessoas-vinculos/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_person(
    actor: Annotated[RequestActor, Depends(require_permission("territorio", "editar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[TerritorioService, Depends(get_service)],
    link_id: int = Path(ge=1),
) -> Response:
    await service.unlink_person(actor, access, link_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/territorios/{territory_id}/liderancas",
    response_model=LiderancaTerritorioResponse,
    status_code=status.HTTP_201_CREATED,
)
async def link_leadership(
    payload: LiderancaTerritorioInput,
    actor: Annotated[RequestActor, Depends(require_permission("territorio", "editar"))],
    access: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    service: Annotated[TerritorioService, Depends(get_service)],
    territory_id: int = Path(ge=1),
) -> dict[str, Any]:
    return await service.link_leadership(actor, access, territory_id, payload)


@router.delete("/territorios/liderancas-vinculos/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_leadership(
    actor: Annotated[RequestActor, Depends(require_permission("territorio", "editar"))],
    service: Annotated[TerritorioService, Depends(get_service)],
    link_id: int = Path(ge=1),
) -> Response:
    if not await service.repository.unlink_leadership(actor.tenant_id, link_id):
        raise ResourceNotFoundError("Vinculo territorial da lideranca", link_id)
    await service.repository.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/territorios/geocodificacoes",
    response_model=GeocodificacaoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_geocoding(
    payload: GeocodificacaoInput,
    actor: Annotated[RequestActor, Depends(require_permission("territorio", "editar"))],
    service: Annotated[TerritorioService, Depends(get_service)],
) -> dict[str, Any]:
    return await service.create_geocoding(actor, payload)
