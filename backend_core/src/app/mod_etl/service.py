"""Orquestracao de uploads, aprovacao e jobs de importacao."""

import csv
import hashlib
import io
import logging
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

import anyio
from celery import Celery
from fastapi.encoders import jsonable_encoder

from app.audit.service import AuditService
from app.auth.access import RequestActor
from app.core.config import Settings
from app.core.errors import BusinessRuleError, ResourceNotFoundError
from app.mod_etl.repository import EtlRepository
from app.mod_etl.schemas import (
    ColumnMappingUpdate,
    ImportResponse,
    ImportSummary,
    JobResponse,
    SourceCreate,
    SourceUpdate,
)

logger = logging.getLogger(__name__)
ALLOWED_EXTENSIONS = {".csv", ".xlsx"}


class EtlService:
    def __init__(self, repository: EtlRepository, settings: Settings) -> None:
        self.repository = repository
        self.settings = settings

    async def create_source(
        self, actor: RequestActor, payload: SourceCreate
    ) -> dict[str, Any]:
        item = await self.repository.create_source(actor.tenant_id, payload)
        await self._audit(actor, "criar", "fonte_dado", item["id"], None, item)
        await self.repository.commit()
        return item

    async def update_source(
        self, actor: RequestActor, source_id: int, payload: SourceUpdate
    ) -> dict[str, Any]:
        current = await self.repository.get_source(actor.tenant_id, source_id)
        if current is None:
            raise ResourceNotFoundError("Fonte de dado", source_id)
        if current["tenant_id"] is None:
            raise BusinessRuleError("Fontes globais nao podem ser alteradas.")
        updated = await self.repository.update_source(
            actor.tenant_id, source_id, payload
        )
        assert updated is not None
        await self._audit(actor, "editar", "fonte_dado", source_id, current, updated)
        await self.repository.commit()
        return updated

    async def create_import(
        self,
        actor: RequestActor,
        *,
        source_id: int,
        description: str | None,
        parameters: dict[str, Any],
        mapping: dict[str, str],
        filename: str,
        content_type: str | None,
        content: bytes,
    ) -> tuple[ImportResponse, JobResponse]:
        source = await self.repository.get_source(actor.tenant_id, source_id)
        if source is None or not source["ativo"]:
            raise ResourceNotFoundError("Fonte de dado", source_id)
        extension = Path(filename).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise BusinessRuleError(
                "Formato nao suportado. Envie CSV ou XLSX.",
                code="unsupported_import_format",
            )
        max_size = self.settings.import_max_file_mb * 1024 * 1024
        if not content or len(content) > max_size:
            raise BusinessRuleError(
                f"O arquivo deve possuir no maximo {self.settings.import_max_file_mb} MB.",
                code="invalid_import_file_size",
            )
        safe_original = re.sub(r"[^A-Za-z0-9._-]", "_", Path(filename).name)
        stored_name = f"{uuid4().hex}{extension}"
        destination = await anyio.to_thread.run_sync(
            self._write_file,
            self.settings.import_storage_path,
            actor.tenant_id,
            stored_name,
            content,
        )
        try:
            import_id = await self.repository.create_import(
                tenant_id=actor.tenant_id,
                user_id=actor.user_id,
                source_id=source_id,
                description=description,
                parameters=parameters,
                mapping=mapping,
                file_data={
                    "original_name": safe_original,
                    "stored_name": stored_name,
                    "mime_type": content_type,
                    "extension": extension.removeprefix("."),
                    "size": len(content),
                    "sha256": hashlib.sha256(content).hexdigest(),
                    "path": str(destination),
                },
            )
            job_id = await self.repository.create_job(
                actor.tenant_id, import_id, "validar"
            )
            await self._audit(
                actor,
                "criar",
                "importacao",
                import_id,
                None,
                {
                    "fonte_dado_id": source_id,
                    "nome_arquivo": safe_original,
                    "parametros": parameters,
                    "mapeamento": mapping,
                },
            )
            await self.repository.commit()
        except Exception:
            await anyio.to_thread.run_sync(self._delete_file, destination)
            raise
        self._dispatch(
            "jobs.etl.process_import",
            {"job_id": job_id, "tenant_id": actor.tenant_id, "import_id": import_id},
        )
        item = await self.repository.get_import(actor.tenant_id, import_id)
        assert item is not None
        return (
            ImportResponse.model_validate(item),
            JobResponse(job_id=job_id, importacao_id=import_id),
        )

    async def update_mapping(
        self,
        actor: RequestActor,
        import_id: int,
        payload: ColumnMappingUpdate,
    ) -> JobResponse | None:
        current = await self._require_import(actor.tenant_id, import_id)
        if not await self.repository.update_mapping(
            actor.tenant_id,
            import_id,
            payload.mapeamento,
            payload.parametros,
        ):
            raise BusinessRuleError("Importacao nao aceita remapeamento neste status.")
        await self._audit(
            actor,
            "editar",
            "importacao",
            import_id,
            current,
            {"mapeamento_colunas": payload.mapeamento},
        )
        job: JobResponse | None = None
        if payload.reprocessar:
            job_id = await self.repository.create_job(
                actor.tenant_id, import_id, "validar"
            )
            job = JobResponse(job_id=job_id, importacao_id=import_id)
        await self.repository.commit()
        if job:
            self._dispatch(
                "jobs.etl.process_import",
                {
                    "job_id": job.job_id,
                    "tenant_id": actor.tenant_id,
                    "import_id": import_id,
                },
            )
        return job

    async def approve(self, actor: RequestActor, import_id: int) -> JobResponse:
        current = await self._require_import(actor.tenant_id, import_id)
        if not await self.repository.approve(
            actor.tenant_id, import_id, actor.user_id
        ):
            raise BusinessRuleError(
                "A importacao deve estar validada e possuir linhas validas."
            )
        job_id = await self.repository.create_job(
            actor.tenant_id, import_id, "carregar"
        )
        await self._audit(
            actor,
            "editar",
            "importacao",
            import_id,
            current,
            {"status": "processando", "aprovado_por": actor.user_id},
        )
        await self.repository.commit()
        self._dispatch(
            "jobs.etl.load_import",
            {"job_id": job_id, "tenant_id": actor.tenant_id, "import_id": import_id},
        )
        return JobResponse(job_id=job_id, importacao_id=import_id)

    async def cancel(self, actor: RequestActor, import_id: int) -> None:
        current = await self._require_import(actor.tenant_id, import_id)
        if not await self.repository.cancel(actor.tenant_id, import_id):
            raise BusinessRuleError("Importacao nao pode ser cancelada neste status.")
        await self._audit(
            actor,
            "editar",
            "importacao",
            import_id,
            current,
            {"status": "cancelada"},
        )
        await self.repository.commit()

    async def summary(
        self, tenant_id: int, import_id: int
    ) -> ImportSummary:
        summary = await self.repository.summary(tenant_id, import_id)
        if summary is None:
            raise ResourceNotFoundError("Importacao", import_id)
        return ImportSummary.model_validate(summary)

    async def error_report(self, tenant_id: int, import_id: int) -> bytes:
        await self._require_import(tenant_id, import_id)
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(["linha", "etapa", "campo", "severidade", "motivo"])
        for error in await self.repository.errors(tenant_id, import_id):
            writer.writerow(
                [
                    error["numero_linha"],
                    error["etapa"],
                    error["campo"],
                    error["severidade"],
                    error["mensagem"],
                ]
            )
        return output.getvalue().encode("utf-8-sig")

    async def _require_import(
        self, tenant_id: int, import_id: int
    ) -> dict[str, Any]:
        item = await self.repository.get_import(tenant_id, import_id)
        if item is None:
            raise ResourceNotFoundError("Importacao", import_id)
        return item

    def _dispatch(self, task: str, kwargs: dict[str, Any]) -> None:
        try:
            Celery(broker=self.settings.celery_broker_url).send_task(
                task, kwargs=kwargs
            )
        except Exception:
            logger.exception("Falha ao despachar job %s; registro permanece enfileirado.", task)

    @staticmethod
    def _write_file(
        storage_path: str,
        tenant_id: int,
        stored_name: str,
        content: bytes,
    ) -> Path:
        tenant_dir = Path(storage_path).resolve() / str(tenant_id)
        tenant_dir.mkdir(parents=True, exist_ok=True)
        destination = (tenant_dir / stored_name).resolve()
        if tenant_dir not in destination.parents:
            raise BusinessRuleError("Caminho de armazenamento invalido.")
        destination.write_bytes(content)
        return destination

    @staticmethod
    def _delete_file(path: Path) -> None:
        path.unlink(missing_ok=True)

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
            schema_name="etl",
            table_name=table,
            record_id=record_id,
            before=jsonable_encoder(before) if before else None,
            after=jsonable_encoder(after) if after else None,
        )
