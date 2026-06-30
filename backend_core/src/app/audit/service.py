from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models import AuditLog, ExportLog


class AuditService:
    """Registra auditoria na mesma transacao da operacao de negocio."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record(
        self,
        *,
        action: str,
        tenant_id: int | None,
        user_id: int | None,
        schema_name: str | None = None,
        table_name: str | None = None,
        record_id: int | None = None,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        log = AuditLog(
            tenant_id=tenant_id,
            usuario_id=user_id,
            acao=action,
            schema_nome=schema_name,
            tabela=table_name,
            registro_id=record_id,
            dados_anteriores=before,
            dados_novos=after,
            ip_origem=ip_address,
            user_agent=user_agent,
            criado_em=datetime.now(UTC),
        )
        self.session.add(log)
        await self.session.flush()
        return log

    async def record_export(
        self,
        *,
        tenant_id: int,
        user_id: int,
        entity: str,
        filters: dict[str, Any],
        record_count: int,
        file_format: str,
        purpose: str,
        file_id: int | None = None,
        ip_address: str | None = None,
    ) -> ExportLog:
        export = ExportLog(
            tenant_id=tenant_id,
            usuario_id=user_id,
            entidade=entity,
            filtros=filters,
            volume_registros=record_count,
            formato=file_format,
            finalidade=purpose,
            arquivo_id=file_id,
            ip_origem=ip_address,
            criado_em=datetime.now(UTC),
        )
        self.session.add(export)
        await self.record(
            action="exportar",
            tenant_id=tenant_id,
            user_id=user_id,
            schema_name="auditoria",
            table_name="log_exportacao",
            after={
                "entidade": entity,
                "filtros": filters,
                "volume_registros": record_count,
                "formato": file_format,
                "finalidade": purpose,
            },
            ip_address=ip_address,
        )
        await self.session.flush()
        return export
