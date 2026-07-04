from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.access import (
    RequestActor,
    TerritorialAccess,
    get_db_session,
    get_territorial_access,
    require_permission,
)
from app.core.errors import BusinessRuleError, ResourceNotFoundError
from app.mod_demandas.repository import DemandRepository
from app.mod_demandas.schemas import (
    AttendanceIn,
    CatalogIn,
    CatalogKey,
    CatalogOut,
    CatalogPatch,
    ClassificationIn,
    ClassificationOut,
    DemandDetail,
    DemandIn,
    DemandOut,
    DemandPatch,
    ResponsibleIn,
    StatusChange,
    Summary,
)
from app.mod_demandas.service import DemandService

router = APIRouter(prefix="/demandas", tags=["Demandas"])


def svc(s: Annotated[AsyncSession, Depends(get_db_session)]):
    return DemandService(DemandRepository(s))


@router.get("/catalogos/{key}", response_model=list[CatalogOut])
async def cats(
    key: CatalogKey,
    a: Annotated[RequestActor, Depends(require_permission("demandas", "visualizar"))],
    s: Annotated[DemandService, Depends(svc)],
    incluir_inativos: bool = False,
):
    return await s.r.catalogs(key, a.tenant_id, incluir_inativos)


@router.post("/catalogos/{key}", response_model=CatalogOut)
async def cat_create(
    key: CatalogKey,
    p: CatalogIn,
    a: Annotated[RequestActor, Depends(require_permission("demandas", "administrar"))],
    s: Annotated[DemandService, Depends(svc)],
):
    allowed = {"codigo", "nome", "descricao"}
    allowed |= {"ordem", "final"} if key == "status" else set()
    allowed |= {"peso"} if key == "prioridades" else set()
    invalid = p.model_fields_set - allowed
    if invalid:
        raise BusinessRuleError(
            f"Campos incompativeis com o catalogo {key}: {', '.join(sorted(invalid))}."
        )
    z = await s.r.create_catalog(key, a.tenant_id, p)
    await s.r.commit()
    return z


@router.patch("/catalogos/{key}/{i}", response_model=CatalogOut)
async def cat_patch(
    key: CatalogKey,
    p: CatalogPatch,
    a: Annotated[RequestActor, Depends(require_permission("demandas", "administrar"))],
    s: Annotated[DemandService, Depends(svc)],
    i: int = Path(ge=1),
):
    allowed = {"nome", "descricao", "ativo"}
    allowed |= {"ordem", "final"} if key == "status" else set()
    allowed |= {"peso"} if key == "prioridades" else set()
    invalid = p.model_fields_set - allowed
    if invalid:
        raise BusinessRuleError(
            f"Campos incompativeis com o catalogo {key}: {', '.join(sorted(invalid))}."
        )
    z = await s.r.patch_catalog(key, a.tenant_id, i, p)
    await s.r.commit()
    return z


@router.delete("/catalogos/{key}/{i}", status_code=204)
async def cat_delete(
    key: CatalogKey,
    a: Annotated[RequestActor, Depends(require_permission("demandas", "administrar"))],
    s: Annotated[DemandService, Depends(svc)],
    i: int = Path(ge=1),
):
    if not await s.r.delete_catalog(key, a.tenant_id, i):
        raise ResourceNotFoundError("Catalogo", i)
    await s.r.commit()


def filters(
    status=None,
    categoria=None,
    responsavel=None,
    territorio=None,
    origem=None,
    lider=None,
    inicio=None,
    fim=None,
):
    return locals()


@router.get("", response_model=list[DemandOut])
async def listing(
    a: Annotated[RequestActor, Depends(require_permission("demandas", "visualizar"))],
    x: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    s: Annotated[DemandService, Depends(svc)],
    status: int | None = None,
    categoria: int | None = None,
    responsavel: int | None = None,
    territorio: int | None = None,
    origem: int | None = None,
    lider: int | None = None,
    inicio: datetime | None = None,
    fim: datetime | None = None,
):
    return await s.r.list(
        a.tenant_id,
        filters(status, categoria, responsavel, territorio, origem, lider, inicio, fim),
        await s.ids(a, x),
    )


@router.post("", response_model=DemandOut)
async def create(
    p: DemandIn,
    a: Annotated[RequestActor, Depends(require_permission("demandas", "criar"))],
    x: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    s: Annotated[DemandService, Depends(svc)],
):
    return await s.create(a, x, p)


@router.get("/resumo", response_model=Summary)
async def summary(
    a: Annotated[RequestActor, Depends(require_permission("demandas", "visualizar"))],
    x: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    s: Annotated[DemandService, Depends(svc)],
):
    return await s.summary(a, x, {})


@router.get("/responsaveis")
async def resp(
    a: Annotated[RequestActor, Depends(require_permission("demandas", "visualizar"))],
    s: Annotated[DemandService, Depends(svc)],
):
    return await s.r.responsibles(a.tenant_id)


@router.post("/responsaveis")
async def resp_create(
    p: ResponsibleIn,
    a: Annotated[RequestActor, Depends(require_permission("demandas", "editar"))],
    s: Annotated[DemandService, Depends(svc)],
):
    z = await s.r.responsible(a.tenant_id, p)
    await s.r.commit()
    return z


@router.get("/exportar.csv")
async def export(
    a: Annotated[RequestActor, Depends(require_permission("demandas", "exportar"))],
    x: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    s: Annotated[DemandService, Depends(svc)],
    finalidade: str = Query(min_length=3, max_length=200),
    status: int | None = None,
    categoria: int | None = None,
    responsavel: int | None = None,
    territorio: int | None = None,
    origem: int | None = None,
    lider: int | None = None,
    inicio: datetime | None = None,
    fim: datetime | None = None,
):
    return StreamingResponse(
        iter(
            [
                await s.export(
                    a,
                    x,
                    filters(
                        status,
                        categoria,
                        responsavel,
                        territorio,
                        origem,
                        lider,
                        inicio,
                        fim,
                    ),
                    finalidade,
                )
            ]
        ),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="demandas.csv"'},
    )


@router.post("/classificar", response_model=ClassificationOut)
async def classify(
    p: ClassificationIn,
    a: Annotated[RequestActor, Depends(require_permission("demandas", "criar"))],
    s: Annotated[DemandService, Depends(svc)],
):
    return await s.classify(a.tenant_id, p.descricao)


@router.get("/{i}", response_model=DemandDetail)
async def detail(
    a: Annotated[RequestActor, Depends(require_permission("demandas", "visualizar"))],
    x: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    s: Annotated[DemandService, Depends(svc)],
    i: int = Path(ge=1),
):
    return await s.detail(a, x, i)


@router.patch("/{i}", response_model=DemandOut)
async def update(
    p: DemandPatch,
    a: Annotated[RequestActor, Depends(require_permission("demandas", "editar"))],
    x: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    s: Annotated[DemandService, Depends(svc)],
    i: int = Path(ge=1),
):
    return await s.update(a, x, i, p)


@router.post("/{i}/status", response_model=DemandOut)
async def status_change(
    p: StatusChange,
    a: Annotated[RequestActor, Depends(require_permission("demandas", "editar"))],
    x: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    s: Annotated[DemandService, Depends(svc)],
    i: int = Path(ge=1),
):
    return await s.update(a, x, i, DemandPatch(**p.model_dump()))


@router.post("/{i}/atendimentos")
async def attend(
    p: AttendanceIn,
    a: Annotated[RequestActor, Depends(require_permission("demandas", "editar"))],
    x: Annotated[TerritorialAccess, Depends(get_territorial_access)],
    s: Annotated[DemandService, Depends(svc)],
    i: int = Path(ge=1),
):
    return await s.attendance(a, x, i, p)
