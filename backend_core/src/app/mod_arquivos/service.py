"""Regras de negocio para upload, acesso e auditoria de anexos."""

import hashlib
import logging
from pathlib import Path
from typing import Any

from celery import Celery
from fastapi.encoders import jsonable_encoder

from app.audit.service import AuditService
from app.auth.access import RequestActor
from app.core.config import Settings
from app.core.errors import AuthorizationError, BusinessRuleError, ResourceNotFoundError
from app.mod_arquivos.repository import FileRepository
from app.mod_arquivos.schemas import (
    AttachmentResponse,
    AttachmentTypeCreate,
    AttachmentTypeUpdate,
    EntityType,
    ExtractedDocumentResponse,
)
from app.mod_arquivos.storage import StorageAdapter, get_storage, sanitize_filename

logger = logging.getLogger(__name__)
ENTITY_MODULE = {
    "pessoa": "cadastro",
    "evento": "agenda",
    "demanda": "demandas",
    "interacao": "comunicacao",
    "importacao": "etl",
    "comunidade": "cadastro",
    "lideranca": "cadastro",
    "convite": "agenda",
}
IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
PREVIEW_EXTENSIONS = IMAGE_EXTENSIONS | {"pdf"}


class FileService:
    def __init__(
        self,
        repository: FileRepository,
        settings: Settings,
        storage: StorageAdapter | None = None,
    ) -> None:
        self.repository = repository
        self.settings = settings
        self.storage = storage or get_storage(settings)

    async def list_types(
        self, actor: RequestActor, include_inactive: bool = False
    ) -> list[dict[str, Any]]:
        self._require_any(
            actor,
            "arquivo.visualizar",
            "cadastro.visualizar",
            "agenda.visualizar",
            "demandas.visualizar",
            "etl.visualizar",
            "comunicacao.visualizar",
        )
        return await self.repository.list_types(actor.tenant_id, include_inactive)

    async def create_type(
        self, actor: RequestActor, payload: AttachmentTypeCreate
    ) -> dict[str, Any]:
        self._require(actor, "arquivo.administrar")
        item = await self.repository.create_type(actor.tenant_id, payload)
        await self._audit(actor, "criar", "tipo_anexo", item["id"], None, item)
        await self.repository.commit()
        return item

    async def update_type(
        self, actor: RequestActor, type_id: int, payload: AttachmentTypeUpdate
    ) -> dict[str, Any]:
        self._require(actor, "arquivo.administrar")
        before = await self.repository.get_type(actor.tenant_id, type_id)
        if before is None or before["tenant_id"] is None:
            raise ResourceNotFoundError("Tipo de anexo do tenant", type_id)
        item = await self.repository.update_type(actor.tenant_id, type_id, payload)
        assert item is not None
        await self._audit(actor, "editar", "tipo_anexo", type_id, before, item)
        await self.repository.commit()
        return item

    async def upload(
        self,
        actor: RequestActor,
        *,
        entity_type: EntityType,
        entity_id: int,
        type_id: int,
        description: str | None,
        filename: str,
        content_type: str | None,
        content: bytes,
        photo_only: bool = False,
    ) -> AttachmentResponse:
        self._require_entity(actor, entity_type, write=True)
        await self._require_entity_exists(actor.tenant_id, entity_type, entity_id)
        attachment_type = await self.repository.get_type(actor.tenant_id, type_id)
        if attachment_type is None or not attachment_type["ativo"]:
            raise ResourceNotFoundError("Tipo de anexo", type_id)
        if photo_only and attachment_type["codigo"] != "foto":
            raise BusinessRuleError("O tipo informado deve ser foto.", code="invalid_photo_type")

        clean_name, extension = self.validate_file(
            filename, content_type, content, photo_only=photo_only
        )
        stored = await self.storage.save(
            tenant_id=actor.tenant_id,
            filename=clean_name,
            extension=extension,
            content=content,
        )
        digest = hashlib.sha256(content).hexdigest()
        try:
            if photo_only:
                for previous in await self.repository.list_attachments(
                    actor.tenant_id, "pessoa", entity_id
                ):
                    if previous["tipo"] and previous["tipo"]["codigo"] == "foto":
                        await self.repository.deactivate_attachment(actor.tenant_id, previous["id"])
            attachment_id = await self.repository.create_attachment(
                tenant_id=actor.tenant_id,
                user_id=actor.user_id,
                entity_type=entity_type,
                entity_id=entity_id,
                type_id=type_id,
                description=description,
                original_name=clean_name,
                mime_type=content_type,
                extension=extension,
                size=len(content),
                sha256=digest,
                stored=stored,
            )
            await self._audit(
                actor,
                "upload_sensivel" if attachment_type["codigo"] == "documento_pessoal" else "criar",
                "anexo",
                attachment_id,
                None,
                {
                    "entidade_tipo": entity_type,
                    "entidade_id": entity_id,
                    "tipo_anexo_id": type_id,
                    "nome_original": clean_name,
                    "tamanho_bytes": len(content),
                    "hash_sha256": digest,
                },
            )
            await self.repository.commit()
        except Exception:
            await self.storage.delete(bucket=stored.bucket, key=stored.key)
            raise

        if extension in PREVIEW_EXTENSIONS:
            self._dispatch_extraction(attachment_id, actor.tenant_id)
        item = await self.repository.get_attachment(actor.tenant_id, attachment_id)
        assert item is not None
        return self._response(item)

    async def list_attachments(
        self, actor: RequestActor, entity_type: EntityType, entity_id: int
    ) -> list[AttachmentResponse]:
        self._require_entity(actor, entity_type, write=False)
        await self._require_entity_exists(actor.tenant_id, entity_type, entity_id)
        return [
            self._response(item)
            for item in await self.repository.list_attachments(
                actor.tenant_id, entity_type, entity_id
            )
        ]

    async def download(
        self, actor: RequestActor, attachment_id: int
    ) -> tuple[bytes, dict[str, Any]]:
        item = await self._require_attachment(actor, attachment_id, write=False)
        content = await get_storage(self.settings, item["arquivo"]["provedor_storage"]).read(
            bucket=item["bucket"], key=item["caminho"]
        )
        return content, item

    async def remove(self, actor: RequestActor, attachment_id: int) -> None:
        item = await self._require_attachment(actor, attachment_id, write=True)
        if not await self.repository.deactivate_attachment(actor.tenant_id, attachment_id):
            raise ResourceNotFoundError("Anexo", attachment_id)
        await self._audit(actor, "excluir", "anexo", attachment_id, item, {"excluido": True})
        await self.repository.commit()

    async def remove_photo(self, actor: RequestActor, person_id: int) -> None:
        self._require_entity(actor, "pessoa", write=True)
        items = await self.repository.list_attachments(actor.tenant_id, "pessoa", person_id)
        current = next(
            (item for item in items if item["tipo"] and item["tipo"]["codigo"] == "foto"),
            None,
        )
        if current is None:
            raise ResourceNotFoundError("Foto da pessoa", person_id)
        await self.remove(actor, current["id"])

    async def search(
        self, actor: RequestActor, query: str, limit: int
    ) -> list[ExtractedDocumentResponse]:
        results = await self.repository.search_documents(actor.tenant_id, query, limit)
        allowed = [
            item
            for item in results
            if f"{ENTITY_MODULE[item['entidade_tipo']]}.visualizar" in actor.permissions
        ]
        return [
            ExtractedDocumentResponse(
                **item,
                download_url=f"/api/v1/arquivos/anexos/{item['anexo_id']}/download",
            )
            for item in allowed
        ]

    def validate_file(
        self,
        filename: str,
        content_type: str | None,
        content: bytes,
        *,
        photo_only: bool = False,
    ) -> tuple[str, str]:
        clean_name = sanitize_filename(filename)
        extension = Path(clean_name).suffix.lower().removeprefix(".")
        allowed = (
            IMAGE_EXTENSIONS
            if photo_only
            else {
                value.strip().lower().removeprefix(".")
                for value in self.settings.storage_allowed_extensions.split(",")
                if value.strip()
            }
        )
        if not extension or extension not in allowed:
            formats = ", ".join(sorted(allowed))
            raise BusinessRuleError(
                f"Extensao nao permitida. Formatos aceitos: {formats}.",
                code="unsupported_file_extension",
            )
        maximum = (
            (self.settings.photo_max_file_mb if photo_only else self.settings.storage_max_file_mb)
            * 1024
            * 1024
        )
        if not content:
            raise BusinessRuleError("O arquivo esta vazio.", code="empty_file")
        if len(content) > maximum:
            raise BusinessRuleError(
                f"O arquivo deve possuir no maximo {maximum // 1024 // 1024} MB.",
                code="file_too_large",
            )
        self._validate_signature(extension, content_type, content)
        return clean_name, extension

    @staticmethod
    def _validate_signature(extension: str, content_type: str | None, content: bytes) -> None:
        signatures = {
            "pdf": content.startswith(b"%PDF-"),
            "png": content.startswith(b"\x89PNG\r\n\x1a\n"),
            "jpg": content.startswith(b"\xff\xd8\xff"),
            "jpeg": content.startswith(b"\xff\xd8\xff"),
            "webp": content.startswith(b"RIFF") and content[8:12] == b"WEBP",
            "xlsx": content.startswith(b"PK\x03\x04"),
        }
        if extension in signatures and not signatures[extension]:
            raise BusinessRuleError(
                "O conteudo do arquivo nao corresponde a extensao informada.",
                code="invalid_file_signature",
            )
        if content_type and content_type.lower() in {
            "application/x-msdownload",
            "application/x-executable",
        }:
            raise BusinessRuleError("Tipo de arquivo executavel nao permitido.", code="unsafe_file")

    async def _require_attachment(
        self, actor: RequestActor, attachment_id: int, *, write: bool
    ) -> dict[str, Any]:
        item = await self.repository.get_attachment(actor.tenant_id, attachment_id)
        if item is None or item["excluido_em"] is not None:
            raise ResourceNotFoundError("Anexo", attachment_id)
        self._require_entity(actor, item["entidade_tipo"], write=write)
        await self._require_entity_exists(
            actor.tenant_id, item["entidade_tipo"], item["entidade_id"]
        )
        return item

    async def _require_entity_exists(
        self, tenant_id: int, entity_type: EntityType, entity_id: int
    ) -> None:
        if not await self.repository.entity_exists(tenant_id, entity_type, entity_id):
            raise ResourceNotFoundError(entity_type.capitalize(), entity_id)

    @staticmethod
    def _require_entity(actor: RequestActor, entity_type: EntityType, *, write: bool) -> None:
        module = ENTITY_MODULE[entity_type]
        actions = ("editar", "criar") if write else ("visualizar",)
        if not any(f"{module}.{action}" in actor.permissions for action in actions):
            raise AuthorizationError(f"Permissao obrigatoria para acessar anexos de {entity_type}.")

    @staticmethod
    def _require(actor: RequestActor, permission: str) -> None:
        if permission not in actor.permissions:
            raise AuthorizationError(f"Permissao obrigatoria: {permission}.")

    @staticmethod
    def _require_any(actor: RequestActor, *permissions: str) -> None:
        if not set(permissions) & actor.permissions:
            raise AuthorizationError()

    @staticmethod
    def _response(item: dict[str, Any]) -> AttachmentResponse:
        item = dict(item)
        item.pop("bucket", None)
        item.pop("caminho", None)
        item.pop("excluido_em", None)
        attachment_id = item["id"]
        item["download_url"] = f"/api/v1/arquivos/anexos/{attachment_id}/download"
        item["preview_url"] = (
            f"/api/v1/arquivos/anexos/{attachment_id}/preview"
            if item["arquivo"]["extensao"] in PREVIEW_EXTENSIONS
            else None
        )
        return AttachmentResponse.model_validate(item)

    def _dispatch_extraction(self, attachment_id: int, tenant_id: int) -> None:
        try:
            Celery(broker=self.settings.celery_broker_url).send_task(
                "jobs.arquivos.extract",
                kwargs={"attachment_id": attachment_id, "tenant_id": tenant_id},
            )
        except Exception:
            logger.exception("Falha ao despachar extracao do anexo %s.", attachment_id)

    async def _audit(
        self,
        actor: RequestActor,
        action: str,
        table: str,
        record_id: int,
        before: dict[str, Any] | None,
        after: dict[str, Any] | None,
    ) -> None:
        await AuditService(self.repository.session).record(
            action=action,
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            schema_name="arquivo",
            table_name=table,
            record_id=record_id,
            before=jsonable_encoder(before) if before else None,
            after=jsonable_encoder(after) if after else None,
        )
