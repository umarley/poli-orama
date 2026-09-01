"""Persistencia de arquivos e anexos."""

from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.mod_arquivos.schemas import AttachmentTypeCreate, AttachmentTypeUpdate, EntityType
from app.mod_arquivos.storage import StoredObject

ENTITY_TABLES: dict[str, tuple[str, str]] = {
    "pessoa": ("cadastro.pessoa", "excluido_em IS NULL"),
    "evento": ("agenda.evento", "excluido_em IS NULL"),
    "demanda": ("demanda.demanda", "excluido_em IS NULL"),
    "interacao": ("comunicacao.interacao", "TRUE"),
    "importacao": ("etl.importacao", "TRUE"),
    "comunidade": ("cadastro.comunidade", "ativo"),
    "lideranca": ("cadastro.lideranca", "ativo"),
    "convite": ("agenda.convite", "TRUE"),
    "tenant": ("public.tenant", "excluido_em IS NULL"),
    "contrato": ("contrato.contrato", "excluido_em IS NULL"),
}


class FileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_types(
        self, tenant_id: int, include_inactive: bool = False
    ) -> list[dict[str, Any]]:
        active = "" if include_inactive else "AND ativo"
        result = await self.session.execute(
            text(
                "SELECT id,tenant_id,codigo,nome,descricao,ativo FROM arquivo.tipo_anexo "
                "WHERE (tenant_id IS NULL OR tenant_id=:tenant_id) "
                f"{active} ORDER BY tenant_id NULLS FIRST,nome"
            ),
            {"tenant_id": tenant_id},
        )
        return [dict(row) for row in result.mappings()]

    async def get_type(self, tenant_id: int, type_id: int) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(
                "SELECT id,tenant_id,codigo,nome,descricao,ativo FROM arquivo.tipo_anexo "
                "WHERE id=:id AND (tenant_id IS NULL OR tenant_id=:tenant_id)"
            ),
            {"id": type_id, "tenant_id": tenant_id},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def create_type(self, tenant_id: int, payload: AttachmentTypeCreate) -> dict[str, Any]:
        result = await self.session.execute(
            text(
                "INSERT INTO arquivo.tipo_anexo(tenant_id,codigo,nome,descricao) "
                "VALUES(:tenant_id,:codigo,:nome,:descricao) "
                "RETURNING id,tenant_id,codigo,nome,descricao,ativo"
            ),
            {"tenant_id": tenant_id, **payload.model_dump()},
        )
        return dict(result.mappings().one())

    async def update_type(
        self, tenant_id: int, type_id: int, payload: AttachmentTypeUpdate
    ) -> dict[str, Any] | None:
        values = payload.model_dump(exclude_unset=True)
        if not values:
            return await self.get_type(tenant_id, type_id)
        assignments = ", ".join(f"{field}=:{field}" for field in values)
        result = await self.session.execute(
            text(
                f"UPDATE arquivo.tipo_anexo SET {assignments},atualizado_em=now() "
                "WHERE id=:id AND tenant_id=:tenant_id "
                "RETURNING id,tenant_id,codigo,nome,descricao,ativo"
            ),
            {"id": type_id, "tenant_id": tenant_id, **values},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def entity_exists(self, tenant_id: int, entity_type: EntityType, entity_id: int) -> bool:
        if entity_type == "tenant":
            if entity_id != tenant_id:
                return False
            return bool(
                await self.session.scalar(
                    text(
                        "SELECT EXISTS(SELECT 1 FROM public.tenant "
                        "WHERE id=:tenant_id AND excluido_em IS NULL)"
                    ),
                    {"tenant_id": tenant_id},
                )
            )
        table, predicate = ENTITY_TABLES[entity_type]
        return bool(
            await self.session.scalar(
                text(
                    f"SELECT EXISTS(SELECT 1 FROM {table} "
                    f"WHERE id=:id AND tenant_id=:tenant_id AND {predicate})"
                ),
                {"id": entity_id, "tenant_id": tenant_id},
            )
        )

    async def create_attachment(
        self,
        *,
        tenant_id: int,
        user_id: int,
        entity_type: EntityType,
        entity_id: int,
        type_id: int,
        description: str | None,
        original_name: str,
        mime_type: str | None,
        extension: str,
        size: int,
        sha256: str,
        stored: StoredObject,
    ) -> int:
        file_id = int(
            await self.session.scalar(
                text(
                    "INSERT INTO arquivo.arquivo "
                    "(tenant_id,nome_original,nome_armazenado,mime_type,extensao,"
                    "tamanho_bytes,hash_sha256,provedor_storage,bucket,caminho,criado_por) "
                    "VALUES(:tenant_id,:original_name,:stored_name,:mime_type,:extension,"
                    ":size,:sha256,:provider,:bucket,:key,:user_id) RETURNING id"
                ),
                {
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "original_name": original_name,
                    "mime_type": mime_type,
                    "extension": extension,
                    "size": size,
                    "sha256": sha256,
                    "provider": stored.provider,
                    "bucket": stored.bucket,
                    "key": stored.key,
                    "stored_name": stored.stored_name,
                },
            )
        )
        attachment_id = int(
            await self.session.scalar(
                text(
                    "INSERT INTO arquivo.anexo "
                    "(tenant_id,arquivo_id,tipo_anexo_id,entidade_tipo,entidade_id,"
                    "descricao,criado_por) VALUES "
                    "(:tenant_id,:file_id,:type_id,:entity_type,:entity_id,:description,:user_id) "
                    "RETURNING id"
                ),
                {
                    "tenant_id": tenant_id,
                    "file_id": file_id,
                    "type_id": type_id,
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "description": description,
                    "user_id": user_id,
                },
            )
        )
        if entity_type == "pessoa":
            type_code = await self.session.scalar(
                text("SELECT codigo FROM arquivo.tipo_anexo WHERE id=:id"), {"id": type_id}
            )
            if type_code == "foto":
                await self.session.execute(
                    text(
                        "UPDATE cadastro.pessoa SET foto_arquivo_id=:file_id "
                        "WHERE id=:entity_id AND tenant_id=:tenant_id"
                    ),
                    {"file_id": file_id, "entity_id": entity_id, "tenant_id": tenant_id},
                )
        return attachment_id

    async def get_attachment(self, tenant_id: int, attachment_id: int) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(self._attachment_select() + " WHERE an.tenant_id=:tenant_id AND an.id=:id"),
            {"tenant_id": tenant_id, "id": attachment_id},
        )
        row = result.mappings().first()
        return self._attachment_dict(row) if row else None

    async def list_attachments(
        self, tenant_id: int, entity_type: EntityType, entity_id: int
    ) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text(
                self._attachment_select()
                + " WHERE an.tenant_id=:tenant_id AND an.entidade_tipo=:entity_type "
                "AND an.entidade_id=:entity_id AND an.excluido_em IS NULL "
                "AND ar.excluido_em IS NULL ORDER BY an.criado_em DESC"
            ),
            {"tenant_id": tenant_id, "entity_type": entity_type, "entity_id": entity_id},
        )
        return [self._attachment_dict(row) for row in result.mappings()]

    async def deactivate_attachment(self, tenant_id: int, attachment_id: int) -> bool:
        attachment = await self.get_attachment(tenant_id, attachment_id)
        if attachment is None or attachment["excluido_em"] is not None:
            return False
        result = await self.session.execute(
            text(
                "UPDATE arquivo.anexo SET excluido_em=now() "
                "WHERE tenant_id=:tenant_id AND id=:id AND excluido_em IS NULL"
            ),
            {"tenant_id": tenant_id, "id": attachment_id},
        )
        if (
            attachment["entidade_tipo"] == "pessoa"
            and attachment["tipo"]
            and attachment["tipo"]["codigo"] == "foto"
        ):
            await self.session.execute(
                text(
                    "UPDATE cadastro.pessoa SET foto_arquivo_id=NULL "
                    "WHERE tenant_id=:tenant_id AND id=:entity_id "
                    "AND foto_arquivo_id=:file_id"
                ),
                {
                    "tenant_id": tenant_id,
                    "entity_id": attachment["entidade_id"],
                    "file_id": attachment["arquivo"]["id"],
                },
            )
        return bool(cast(CursorResult[Any], result).rowcount)

    async def search_documents(
        self, tenant_id: int, query: str, limit: int
    ) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text(
                "SELECT de.arquivo_id,ar.nome_original,an.entidade_tipo,an.entidade_id,"
                "de.texto_extraido,de.metodo_extracao,de.processado_em,an.id AS anexo_id "
                "FROM arquivo.documento_extraido de "
                "JOIN arquivo.arquivo ar ON ar.id=de.arquivo_id "
                "JOIN arquivo.anexo an ON an.arquivo_id=ar.id "
                "WHERE de.tenant_id=:tenant_id AND ar.excluido_em IS NULL "
                "AND an.excluido_em IS NULL "
                "AND to_tsvector('portuguese',COALESCE(de.texto_extraido,'')) "
                "@@ websearch_to_tsquery('portuguese',:query) "
                "ORDER BY de.processado_em DESC LIMIT :limit"
            ),
            {"tenant_id": tenant_id, "query": query, "limit": limit},
        )
        return [dict(row) for row in result.mappings()]

    async def commit(self) -> None:
        await self.session.commit()

    @staticmethod
    def _attachment_select() -> str:
        return (
            "SELECT an.id,an.entidade_tipo,an.entidade_id,an.descricao,an.criado_em,"
            "an.excluido_em,ar.id AS arquivo_id,ar.uuid_publico,ar.nome_original,"
            "ar.mime_type,ar.extensao,ar.tamanho_bytes,ar.hash_sha256,"
            "ar.provedor_storage,ar.bucket,ar.caminho,ar.criado_em AS arquivo_criado_em,"
            "ta.id AS tipo_id,ta.tenant_id AS tipo_tenant_id,ta.codigo AS tipo_codigo,"
            "ta.nome AS tipo_nome,ta.descricao AS tipo_descricao,ta.ativo AS tipo_ativo "
            "FROM arquivo.anexo an JOIN arquivo.arquivo ar ON ar.id=an.arquivo_id "
            "LEFT JOIN arquivo.tipo_anexo ta ON ta.id=an.tipo_anexo_id"
        )

    @staticmethod
    def _attachment_dict(row: Any) -> dict[str, Any]:
        item = dict(row)
        item["arquivo"] = {
            "id": item.pop("arquivo_id"),
            "uuid_publico": item.pop("uuid_publico"),
            "nome_original": item.pop("nome_original"),
            "mime_type": item.pop("mime_type"),
            "extensao": item.pop("extensao"),
            "tamanho_bytes": item.pop("tamanho_bytes"),
            "hash_sha256": item.pop("hash_sha256"),
            "provedor_storage": item.pop("provedor_storage"),
            "criado_em": item.pop("arquivo_criado_em"),
        }
        item["tipo"] = (
            {
                "id": item.pop("tipo_id"),
                "tenant_id": item.pop("tipo_tenant_id"),
                "codigo": item.pop("tipo_codigo"),
                "nome": item.pop("tipo_nome"),
                "descricao": item.pop("tipo_descricao"),
                "ativo": item.pop("tipo_ativo"),
            }
            if item["tipo_id"] is not None
            else None
        )
        if item["tipo"] is None:
            for key in (
                "tipo_id",
                "tipo_tenant_id",
                "tipo_codigo",
                "tipo_nome",
                "tipo_descricao",
                "tipo_ativo",
            ):
                item.pop(key, None)
        return item
