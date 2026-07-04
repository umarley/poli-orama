"""Persistencia da API de importacao."""

import json
from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.mod_etl.schemas import SourceCreate, SourceUpdate


class EtlRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_sources(
        self, tenant_id: int, include_inactive: bool = False
    ) -> list[dict[str, Any]]:
        active = "" if include_inactive else "AND ativo"
        result = await self.session.execute(
            text(
                "SELECT id, tenant_id, codigo, nome, tipo, descricao, ativo, "
                "criado_em, atualizado_em FROM etl.fonte_dado "
                "WHERE (tenant_id IS NULL OR tenant_id = :tenant_id) "
                f"{active} ORDER BY tenant_id NULLS FIRST, nome"
            ),
            {"tenant_id": tenant_id},
        )
        return [dict(row) for row in result.mappings()]

    async def get_source(self, tenant_id: int, source_id: int) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(
                "SELECT id, tenant_id, codigo, nome, tipo, descricao, ativo, "
                "criado_em, atualizado_em FROM etl.fonte_dado "
                "WHERE id = :id AND (tenant_id IS NULL OR tenant_id = :tenant_id)"
            ),
            {"id": source_id, "tenant_id": tenant_id},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def create_source(
        self, tenant_id: int, payload: SourceCreate
    ) -> dict[str, Any]:
        result = await self.session.execute(
            text(
                "INSERT INTO etl.fonte_dado "
                "(tenant_id, codigo, nome, tipo, descricao) "
                "VALUES (:tenant_id, :codigo, :nome, :tipo, :descricao) "
                "RETURNING id, tenant_id, codigo, nome, tipo, descricao, ativo, "
                "criado_em, atualizado_em"
            ),
            {"tenant_id": tenant_id, **payload.model_dump()},
        )
        return dict(result.mappings().one())

    async def update_source(
        self, tenant_id: int, source_id: int, payload: SourceUpdate
    ) -> dict[str, Any] | None:
        values = payload.model_dump(exclude_unset=True)
        if values:
            assignments = ", ".join(f"{key} = :{key}" for key in values)
            await self.session.execute(
                text(
                    f"UPDATE etl.fonte_dado SET {assignments} "
                    "WHERE id = :id AND tenant_id = :tenant_id"
                ),
                {"id": source_id, "tenant_id": tenant_id, **values},
            )
        return await self.get_source(tenant_id, source_id)

    async def list_imports(self, tenant_id: int) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text(self._import_select() + " ORDER BY i.criado_em DESC, i.id DESC"),
            {"tenant_id": tenant_id},
        )
        return [self._import_dict(row) for row in result.mappings()]

    async def get_import(self, tenant_id: int, import_id: int) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(self._import_select() + " AND i.id = :id"),
            {"tenant_id": tenant_id, "id": import_id},
        )
        row = result.mappings().first()
        return self._import_dict(row) if row else None

    @staticmethod
    def _import_select() -> str:
        return (
            "SELECT i.id, i.tenant_id, i.fonte_dado_id, f.nome AS fonte_nome, "
            "i.descricao, i.tipo_destino, i.status, i.parametros, "
            "i.mapeamento_colunas, COALESCE(i.total_linhas, 0) AS total_linhas, "
            "COALESCE(i.linhas_validas, 0) AS linhas_validas, "
            "COALESCE(i.linhas_erro, 0) AS linhas_erro, i.linhas_duplicadas, "
            "i.linhas_pendentes, i.linhas_carregadas, i.iniciado_em, "
            "i.concluido_em, i.criado_por, i.aprovado_por, i.criado_em, "
            "i.atualizado_em, ia.id AS importacao_arquivo_id, ia.arquivo_id, "
            "ia.nome_arquivo FROM etl.importacao i "
            "JOIN etl.fonte_dado f ON f.id = i.fonte_dado_id "
            "LEFT JOIN LATERAL (SELECT * FROM etl.importacao_arquivo x "
            "WHERE x.importacao_id = i.id ORDER BY x.id LIMIT 1) ia ON TRUE "
            "WHERE i.tenant_id = :tenant_id"
        )

    @staticmethod
    def _import_dict(row: Any) -> dict[str, Any]:
        item = dict(row)
        file_id = item.pop("importacao_arquivo_id")
        arquivo_id = item.pop("arquivo_id")
        file_name = item.pop("nome_arquivo")
        item["arquivo"] = (
            {"id": file_id, "arquivo_id": arquivo_id, "nome_arquivo": file_name}
            if file_id
            else None
        )
        return item

    async def create_import(
        self,
        *,
        tenant_id: int,
        user_id: int,
        source_id: int,
        description: str | None,
        parameters: dict[str, Any],
        mapping: dict[str, str],
        file_data: dict[str, Any],
    ) -> int:
        import_id = int(
            await self.session.scalar(
                text(
                    "INSERT INTO etl.importacao "
                    "(tenant_id, fonte_dado_id, descricao, tipo_destino, criado_por, "
                    "parametros, mapeamento_colunas) VALUES "
                    "(:tenant_id, :source_id, :description, 'pessoa', :user_id, "
                    "CAST(:parameters AS jsonb), CAST(:mapping AS jsonb)) RETURNING id"
                ),
                {
                    "tenant_id": tenant_id,
                    "source_id": source_id,
                    "description": description,
                    "user_id": user_id,
                    "parameters": json.dumps(parameters),
                    "mapping": json.dumps(mapping),
                },
            )
        )
        arquivo_id = int(
            await self.session.scalar(
                text(
                    "INSERT INTO arquivo.arquivo "
                    "(tenant_id, nome_original, nome_armazenado, mime_type, extensao, "
                    "tamanho_bytes, hash_sha256, provedor_storage, bucket, caminho, criado_por) "
                    "VALUES (:tenant_id, :original_name, :stored_name, :mime_type, "
                    ":extension, :size, :sha256, 'local', 'importacoes', :path, :user_id) "
                    "RETURNING id"
                ),
                {"tenant_id": tenant_id, "user_id": user_id, **file_data},
            )
        )
        await self.session.execute(
            text(
                "INSERT INTO etl.importacao_arquivo "
                "(tenant_id, importacao_id, arquivo_id, nome_arquivo) "
                "VALUES (:tenant_id, :import_id, :file_id, :file_name)"
            ),
            {
                "tenant_id": tenant_id,
                "import_id": import_id,
                "file_id": arquivo_id,
                "file_name": file_data["original_name"],
            },
        )
        return import_id

    async def update_mapping(
        self,
        tenant_id: int,
        import_id: int,
        mapping: dict[str, str],
        parameters: dict[str, Any],
    ) -> bool:
        result = await self.session.execute(
            text(
                "UPDATE etl.importacao SET mapeamento_colunas = CAST(:mapping AS jsonb), "
                "parametros = parametros || CAST(:parameters AS jsonb), status = 'pendente' "
                "WHERE tenant_id = :tenant_id AND id = :id "
                "AND status IN ('pendente', 'parcial', 'falha')"
            ),
            {
                "tenant_id": tenant_id,
                "id": import_id,
                "mapping": json.dumps(mapping),
                "parameters": json.dumps(parameters),
            },
        )
        return bool(cast(CursorResult[Any], result).rowcount)

    async def create_job(
        self, tenant_id: int, import_id: int, operation: str
    ) -> int:
        job_id = int(
            await self.session.scalar(
                text(
                    "INSERT INTO etl.job_processamento "
                    "(tenant_id, tipo, referencia, parametros) "
                    "VALUES (:tenant_id, 'importacao', :reference, CAST(:params AS jsonb)) "
                    "RETURNING id"
                ),
                {
                    "tenant_id": tenant_id,
                    "reference": f"importacao:{import_id}:{operation}",
                    "params": json.dumps(
                        {"importacao_id": import_id, "operacao": operation}
                    ),
                },
            )
        )
        await self.session.execute(
            text(
                "INSERT INTO etl.log_processamento "
                "(job_processamento_id, nivel, mensagem, contexto) "
                "VALUES (:job_id, 'info', 'Job de importacao enfileirado.', "
                "CAST(:context AS jsonb))"
            ),
            {
                "job_id": job_id,
                "context": json.dumps(
                    {"importacao_id": import_id, "operacao": operation}
                ),
            },
        )
        return job_id

    async def approve(
        self, tenant_id: int, import_id: int, user_id: int
    ) -> bool:
        result = await self.session.execute(
            text(
                "UPDATE etl.importacao SET aprovado_por = :user_id, aprovado_em = now(), "
                "status = 'processando' WHERE tenant_id = :tenant_id AND id = :id "
                "AND status = 'parcial' AND COALESCE(linhas_validas, 0) > 0"
            ),
            {"tenant_id": tenant_id, "id": import_id, "user_id": user_id},
        )
        return bool(cast(CursorResult[Any], result).rowcount)

    async def cancel(self, tenant_id: int, import_id: int) -> bool:
        result = await self.session.execute(
            text(
                "UPDATE etl.importacao SET status = 'cancelada', concluido_em = now() "
                "WHERE tenant_id = :tenant_id AND id = :id "
                "AND status IN ('pendente', 'parcial', 'falha')"
            ),
            {"tenant_id": tenant_id, "id": import_id},
        )
        return bool(cast(CursorResult[Any], result).rowcount)

    async def summary(self, tenant_id: int, import_id: int) -> dict[str, Any] | None:
        item = await self.get_import(tenant_id, import_id)
        if item is None:
            return None
        warnings = int(
            await self.session.scalar(
                text(
                    "SELECT count(*) FROM etl.erro_importacao "
                    "WHERE tenant_id = :tenant_id AND importacao_id = :id "
                    "AND severidade = 'aviso'"
                ),
                {"tenant_id": tenant_id, "id": import_id},
            )
            or 0
        )
        return {
            "importacao_id": import_id,
            "status": item["status"],
            "total": item["total_linhas"],
            "validas": item["linhas_validas"],
            "invalidas": item["linhas_erro"],
            "duplicadas": item["linhas_duplicadas"],
            "pendentes": item["linhas_pendentes"],
            "carregadas": item["linhas_carregadas"],
            "avisos": warnings,
        }

    async def errors(
        self, tenant_id: int, import_id: int
    ) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text(
                "SELECT e.id, l.numero_linha, e.etapa, e.campo, e.valor, "
                "e.mensagem, e.severidade, e.criado_em "
                "FROM etl.erro_importacao e LEFT JOIN etl.importacao_linha l "
                "ON l.id = e.importacao_linha_id "
                "WHERE e.tenant_id = :tenant_id AND e.importacao_id = :id "
                "ORDER BY l.numero_linha NULLS LAST, e.id"
            ),
            {"tenant_id": tenant_id, "id": import_id},
        )
        return [dict(row) for row in result.mappings()]

    async def duplicates(
        self, tenant_id: int, import_id: int
    ) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text(
                "SELECT d.id, d.staging_pessoa_id, d.pessoa_candidata_id, "
                "r.criterio, d.score, d.decisao, d.detalhes "
                "FROM etl.resultado_deduplicacao d "
                "LEFT JOIN etl.regra_deduplicacao r ON r.id = d.regra_deduplicacao_id "
                "WHERE d.tenant_id = :tenant_id AND d.importacao_id = :id "
                "ORDER BY d.score DESC, d.id"
            ),
            {"tenant_id": tenant_id, "id": import_id},
        )
        return [dict(row) for row in result.mappings()]

    async def commit(self) -> None:
        await self.session.commit()
