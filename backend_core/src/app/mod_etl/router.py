"""Endpoints de fontes, importacoes, validacao e aprovacao."""

import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, Path, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.access import RequestActor, get_db_session, require_permission
from app.core.config import get_settings
from app.core.errors import BusinessRuleError
from app.mod_etl.repository import EtlRepository
from app.mod_etl.schemas import (
    ColumnMappingUpdate,
    DuplicateResponse,
    ImportErrorResponse,
    ImportResponse,
    ImportSummary,
    JobResponse,
    SourceCreate,
    SourceResponse,
    SourceUpdate,
)
from app.mod_etl.service import EtlService

router = APIRouter(prefix="/etl", tags=["Importacao e ETL"])


def get_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> EtlService:
    return EtlService(EtlRepository(session), get_settings())


@router.get("/fontes", response_model=list[SourceResponse])
async def list_sources(
    actor: Annotated[RequestActor, Depends(require_permission("etl", "visualizar"))],
    service: Annotated[EtlService, Depends(get_service)],
    incluir_inativas: bool = False,
) -> list[dict[str, Any]]:
    return await service.repository.list_sources(actor.tenant_id, incluir_inativas)


@router.post(
    "/fontes", response_model=SourceResponse, status_code=status.HTTP_201_CREATED
)
async def create_source(
    payload: SourceCreate,
    actor: Annotated[RequestActor, Depends(require_permission("etl", "criar"))],
    service: Annotated[EtlService, Depends(get_service)],
) -> dict[str, Any]:
    return await service.create_source(actor, payload)


@router.patch("/fontes/{source_id}", response_model=SourceResponse)
async def update_source(
    payload: SourceUpdate,
    actor: Annotated[RequestActor, Depends(require_permission("etl", "editar"))],
    service: Annotated[EtlService, Depends(get_service)],
    source_id: int = Path(ge=1),
) -> dict[str, Any]:
    return await service.update_source(actor, source_id, payload)


@router.delete("/fontes/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_source(
    actor: Annotated[RequestActor, Depends(require_permission("etl", "editar"))],
    service: Annotated[EtlService, Depends(get_service)],
    source_id: int = Path(ge=1),
) -> Response:
    await service.update_source(actor, source_id, SourceUpdate(ativo=False))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/importacoes", response_model=list[ImportResponse])
async def list_imports(
    actor: Annotated[RequestActor, Depends(require_permission("etl", "visualizar"))],
    service: Annotated[EtlService, Depends(get_service)],
) -> list[dict[str, Any]]:
    return await service.repository.list_imports(actor.tenant_id)


@router.post(
    "/importacoes",
    response_model=ImportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_import(
    actor: Annotated[RequestActor, Depends(require_permission("etl", "criar"))],
    service: Annotated[EtlService, Depends(get_service)],
    arquivo: Annotated[UploadFile, File()],
    fonte_dado_id: Annotated[int, Form(ge=1)],
    descricao: Annotated[str | None, Form(max_length=180)] = None,
    parametros: Annotated[str, Form()] = "{}",
    mapeamento: Annotated[str, Form()] = "{}",
) -> ImportResponse:
    try:
        parsed_parameters = json.loads(parametros)
        parsed_mapping = json.loads(mapeamento)
        if not isinstance(parsed_parameters, dict) or not isinstance(parsed_mapping, dict):
            raise ValueError
    except (json.JSONDecodeError, ValueError) as exc:
        raise BusinessRuleError("Parametros e mapeamento devem ser objetos JSON.") from exc
    limit = get_settings().import_max_file_mb * 1024 * 1024
    content = await arquivo.read(limit + 1)
    item, _ = await service.create_import(
        actor,
        source_id=fonte_dado_id,
        description=descricao,
        parameters=parsed_parameters,
        mapping={str(key): str(value) for key, value in parsed_mapping.items()},
        filename=arquivo.filename or "importacao",
        content_type=arquivo.content_type,
        content=content,
    )
    return item


@router.get("/importacoes/{import_id}", response_model=ImportResponse)
async def get_import(
    actor: Annotated[RequestActor, Depends(require_permission("etl", "visualizar"))],
    service: Annotated[EtlService, Depends(get_service)],
    import_id: int = Path(ge=1),
) -> ImportResponse:
    return ImportResponse.model_validate(
        await service._require_import(actor.tenant_id, import_id)
    )


@router.put(
    "/importacoes/{import_id}/mapeamento", response_model=JobResponse | None
)
async def update_mapping(
    payload: ColumnMappingUpdate,
    actor: Annotated[RequestActor, Depends(require_permission("etl", "editar"))],
    service: Annotated[EtlService, Depends(get_service)],
    import_id: int = Path(ge=1),
) -> JobResponse | None:
    return await service.update_mapping(actor, import_id, payload)


@router.get("/importacoes/{import_id}/resumo", response_model=ImportSummary)
async def import_summary(
    actor: Annotated[RequestActor, Depends(require_permission("etl", "visualizar"))],
    service: Annotated[EtlService, Depends(get_service)],
    import_id: int = Path(ge=1),
) -> ImportSummary:
    return await service.summary(actor.tenant_id, import_id)


@router.get(
    "/importacoes/{import_id}/erros", response_model=list[ImportErrorResponse]
)
async def list_errors(
    actor: Annotated[RequestActor, Depends(require_permission("etl", "visualizar"))],
    service: Annotated[EtlService, Depends(get_service)],
    import_id: int = Path(ge=1),
) -> list[dict[str, Any]]:
    await service._require_import(actor.tenant_id, import_id)
    return await service.repository.errors(actor.tenant_id, import_id)


@router.get(
    "/importacoes/{import_id}/duplicidades",
    response_model=list[DuplicateResponse],
)
async def list_duplicates(
    actor: Annotated[RequestActor, Depends(require_permission("etl", "visualizar"))],
    service: Annotated[EtlService, Depends(get_service)],
    import_id: int = Path(ge=1),
) -> list[dict[str, Any]]:
    await service._require_import(actor.tenant_id, import_id)
    return await service.repository.duplicates(actor.tenant_id, import_id)


@router.post("/importacoes/{import_id}/aprovar", response_model=JobResponse)
async def approve_import(
    actor: Annotated[RequestActor, Depends(require_permission("etl", "aprovar"))],
    service: Annotated[EtlService, Depends(get_service)],
    import_id: int = Path(ge=1),
) -> JobResponse:
    return await service.approve(actor, import_id)


@router.delete(
    "/importacoes/{import_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def cancel_import(
    actor: Annotated[RequestActor, Depends(require_permission("etl", "editar"))],
    service: Annotated[EtlService, Depends(get_service)],
    import_id: int = Path(ge=1),
) -> Response:
    await service.cancel(actor, import_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/importacoes/{import_id}/relatorio-erros.csv")
async def download_errors(
    actor: Annotated[RequestActor, Depends(require_permission("etl", "exportar"))],
    service: Annotated[EtlService, Depends(get_service)],
    import_id: int = Path(ge=1),
) -> StreamingResponse:
    content = await service.error_report(actor.tenant_id, import_id)
    return StreamingResponse(
        iter([content]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="importacao-{import_id}-erros.csv"'
            )
        },
    )
