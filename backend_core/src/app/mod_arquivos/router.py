"""Endpoints controlados de arquivos e anexos."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, Path, Query, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.access import RequestActor, get_current_user, get_db_session, require_permission
from app.core.config import get_settings
from app.core.errors import BusinessRuleError
from app.mod_arquivos.repository import FileRepository
from app.mod_arquivos.schemas import (
    AttachmentResponse,
    AttachmentTypeCreate,
    AttachmentTypeResponse,
    AttachmentTypeUpdate,
    EntityType,
    ExtractedDocumentResponse,
)
from app.mod_arquivos.service import FileService

router = APIRouter(prefix="/arquivos", tags=["Arquivos e anexos"])


def get_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> FileService:
    return FileService(FileRepository(session), get_settings())


@router.get("/tipos", response_model=list[AttachmentTypeResponse])
async def list_types(
    actor: Annotated[RequestActor, Depends(get_current_user)],
    service: Annotated[FileService, Depends(get_service)],
    incluir_inativos: bool = False,
) -> list[dict[str, Any]]:
    return await service.list_types(actor, incluir_inativos)


@router.post("/tipos", response_model=AttachmentTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_type(
    payload: AttachmentTypeCreate,
    actor: Annotated[RequestActor, Depends(require_permission("arquivo", "administrar"))],
    service: Annotated[FileService, Depends(get_service)],
) -> dict[str, Any]:
    return await service.create_type(actor, payload)


@router.patch("/tipos/{type_id}", response_model=AttachmentTypeResponse)
async def update_type(
    payload: AttachmentTypeUpdate,
    actor: Annotated[RequestActor, Depends(require_permission("arquivo", "administrar"))],
    service: Annotated[FileService, Depends(get_service)],
    type_id: int = Path(ge=1),
) -> dict[str, Any]:
    return await service.update_type(actor, type_id, payload)


@router.delete("/tipos/{type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_type(
    actor: Annotated[RequestActor, Depends(require_permission("arquivo", "administrar"))],
    service: Annotated[FileService, Depends(get_service)],
    type_id: int = Path(ge=1),
) -> Response:
    await service.update_type(actor, type_id, AttachmentTypeUpdate(ativo=False))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/anexos", response_model=AttachmentResponse, status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    actor: Annotated[RequestActor, Depends(get_current_user)],
    service: Annotated[FileService, Depends(get_service)],
    arquivo: Annotated[UploadFile, File()],
    entidade_tipo: Annotated[EntityType, Form()],
    entidade_id: Annotated[int, Form(ge=1)],
    tipo_anexo_id: Annotated[int, Form(ge=1)],
    descricao: Annotated[str | None, Form(max_length=255)] = None,
) -> AttachmentResponse:
    limit = get_settings().storage_max_file_mb * 1024 * 1024
    content = await arquivo.read(limit + 1)
    return await service.upload(
        actor,
        entity_type=entidade_tipo,
        entity_id=entidade_id,
        type_id=tipo_anexo_id,
        description=descricao,
        filename=arquivo.filename or "arquivo",
        content_type=arquivo.content_type,
        content=content,
    )


@router.post(
    "/pessoas/{person_id}/foto",
    response_model=AttachmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_person_photo(
    actor: Annotated[RequestActor, Depends(require_permission("cadastro", "editar"))],
    service: Annotated[FileService, Depends(get_service)],
    arquivo: Annotated[UploadFile, File()],
    person_id: int = Path(ge=1),
) -> AttachmentResponse:
    types = await service.repository.list_types(actor.tenant_id)
    photo_type = next((item for item in types if item["codigo"] == "foto"), None)
    if photo_type is None:
        raise BusinessRuleError("Tipo de anexo 'foto' nao configurado.")
    limit = get_settings().photo_max_file_mb * 1024 * 1024
    content = await arquivo.read(limit + 1)
    return await service.upload(
        actor,
        entity_type="pessoa",
        entity_id=person_id,
        type_id=photo_type["id"],
        description="Foto de perfil",
        filename=arquivo.filename or "foto",
        content_type=arquivo.content_type,
        content=content,
        photo_only=True,
    )


@router.delete("/pessoas/{person_id}/foto", status_code=status.HTTP_204_NO_CONTENT)
async def remove_person_photo(
    actor: Annotated[RequestActor, Depends(require_permission("cadastro", "editar"))],
    service: Annotated[FileService, Depends(get_service)],
    person_id: int = Path(ge=1),
) -> Response:
    await service.remove_photo(actor, person_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/entidades/{entity_type}/{entity_id}/anexos",
    response_model=list[AttachmentResponse],
)
async def list_attachments(
    actor: Annotated[RequestActor, Depends(get_current_user)],
    service: Annotated[FileService, Depends(get_service)],
    entity_type: EntityType,
    entity_id: int = Path(ge=1),
) -> list[AttachmentResponse]:
    return await service.list_attachments(actor, entity_type, entity_id)


def _content_disposition(filename: str, inline: bool) -> str:
    safe = filename.replace('"', "_").replace("\r", "").replace("\n", "")
    return f'{"inline" if inline else "attachment"}; filename="{safe}"'


async def _file_response(
    actor: RequestActor, service: FileService, attachment_id: int, *, inline: bool
) -> StreamingResponse:
    content, item = await service.download(actor, attachment_id)
    return StreamingResponse(
        iter([content]),
        media_type=item["arquivo"]["mime_type"] or "application/octet-stream",
        headers={
            "Content-Disposition": _content_disposition(item["arquivo"]["nome_original"], inline),
            "Content-Length": str(len(content)),
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; sandbox",
            "Cache-Control": "private, no-store",
        },
    )


@router.get("/anexos/{attachment_id}/download")
async def download_attachment(
    actor: Annotated[RequestActor, Depends(get_current_user)],
    service: Annotated[FileService, Depends(get_service)],
    attachment_id: int = Path(ge=1),
) -> StreamingResponse:
    return await _file_response(actor, service, attachment_id, inline=False)


@router.get("/anexos/{attachment_id}/preview")
async def preview_attachment(
    actor: Annotated[RequestActor, Depends(get_current_user)],
    service: Annotated[FileService, Depends(get_service)],
    attachment_id: int = Path(ge=1),
) -> StreamingResponse:
    return await _file_response(actor, service, attachment_id, inline=True)


@router.delete("/anexos/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_attachment(
    actor: Annotated[RequestActor, Depends(get_current_user)],
    service: Annotated[FileService, Depends(get_service)],
    attachment_id: int = Path(ge=1),
) -> Response:
    await service.remove(actor, attachment_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/documentos/busca", response_model=list[ExtractedDocumentResponse])
async def search_documents(
    actor: Annotated[RequestActor, Depends(get_current_user)],
    service: Annotated[FileService, Depends(get_service)],
    q: str = Query(min_length=2, max_length=100),
    limite: int = Query(default=30, ge=1, le=100),
) -> list[ExtractedDocumentResponse]:
    return await service.search(actor, q, limite)
