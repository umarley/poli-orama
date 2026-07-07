from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.mod_comunicacao.schemas import CatalogInput, CatalogUpdate, InteracaoInput


class ComunicacaoRepository:
    CATALOGS = {
        "tipos-interacao": "tipo_interacao",
        "canais": "canal_comunicacao",
    }

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_catalog(
        self, catalog: str, tenant_id: int, include_inactive: bool = False
    ) -> list[dict[str, Any]]:
        table = self._table(catalog)
        inactive = "" if include_inactive else "AND ativo"
        result = await self.session.execute(
            text(
                f"SELECT id, tenant_id, codigo, nome, descricao, ativo, criado_em, atualizado_em "
                f"FROM comunicacao.{table} "
                "WHERE tenant_id IS NULL OR tenant_id = :tenant_id "
                f"{inactive} ORDER BY tenant_id NULLS FIRST, nome"
            ),
            {"tenant_id": tenant_id},
        )
        return [dict(row) for row in result.mappings()]

    async def get_catalog(
        self, catalog: str, tenant_id: int, item_id: int
    ) -> dict[str, Any] | None:
        table = self._table(catalog)
        row = (
            await self.session.execute(
                text(
                    "SELECT id, tenant_id, codigo, nome, descricao, ativo, "
                    "criado_em, atualizado_em "
                    f"FROM comunicacao.{table} "
                    "WHERE id = :id AND (tenant_id IS NULL OR tenant_id = :tenant_id)"
                ),
                {"id": item_id, "tenant_id": tenant_id},
            )
        ).mappings().first()
        return dict(row) if row else None

    async def create_catalog(
        self, catalog: str, tenant_id: int, payload: CatalogInput
    ) -> dict[str, Any]:
        table = self._table(catalog)
        row = (
            await self.session.execute(
                text(
                    f"INSERT INTO comunicacao.{table} "
                    "(tenant_id, codigo, nome, descricao) "
                    "VALUES (:tenant_id, :codigo, :nome, :descricao) "
                    "ON CONFLICT (tenant_id, codigo) DO UPDATE SET "
                    "nome = EXCLUDED.nome, descricao = EXCLUDED.descricao, "
                    "ativo = true, atualizado_em = now() "
                    "RETURNING id, tenant_id, codigo, nome, descricao, ativo, "
                    "criado_em, atualizado_em"
                ),
                {"tenant_id": tenant_id, **payload.model_dump()},
            )
        ).mappings().one()
        return dict(row)

    async def update_catalog(
        self, catalog: str, tenant_id: int, item_id: int, payload: CatalogUpdate
    ) -> dict[str, Any] | None:
        table = self._table(catalog)
        values = payload.model_dump(exclude_unset=True)
        if not values:
            return await self.get_catalog(catalog, tenant_id, item_id)
        assignments = ", ".join(f"{field} = :{field}" for field in values)
        row = (
            await self.session.execute(
                text(
                    f"UPDATE comunicacao.{table} SET {assignments}, atualizado_em = now() "
                    "WHERE id = :id AND tenant_id = :tenant_id "
                    "RETURNING id, tenant_id, codigo, nome, descricao, ativo, "
                    "criado_em, atualizado_em"
                ),
                {"id": item_id, "tenant_id": tenant_id, **values},
            )
        ).mappings().first()
        return dict(row) if row else None

    async def person_in_scope(
        self, tenant_id: int, person_id: int, accessible_ids: set[int] | None
    ) -> bool:
        if accessible_ids is not None and not accessible_ids:
            return False
        access_clause = (
            ""
            if accessible_ids is None
            else "AND EXISTS (SELECT 1 FROM territorio.pessoa_territorio pt "
            "WHERE pt.tenant_id = p.tenant_id AND pt.pessoa_id = p.id "
            "AND pt.territorio_id = ANY(:accessible_ids))"
        )
        return bool(
            await self.session.scalar(
                text(
                    "SELECT EXISTS (SELECT 1 FROM cadastro.pessoa p "
                    "WHERE p.tenant_id = :tenant_id AND p.id = :person_id "
                    "AND p.ativo AND p.excluido_em IS NULL "
                    f"{access_clause})"
                ),
                {
                    "tenant_id": tenant_id,
                    "person_id": person_id,
                    "accessible_ids": (
                        sorted(accessible_ids) if accessible_ids is not None else None
                    ),
                },
            )
        )

    async def catalog_item_exists(self, catalog: str, tenant_id: int, item_id: int) -> bool:
        table = self._table(catalog)
        return bool(
            await self.session.scalar(
                text(
                    f"SELECT EXISTS (SELECT 1 FROM comunicacao.{table} "
                    "WHERE id = :id AND ativo AND (tenant_id IS NULL OR tenant_id = :tenant_id))"
                ),
                {"id": item_id, "tenant_id": tenant_id},
            )
        )

    async def create_interaction(
        self, tenant_id: int, user_id: int, person_id: int, payload: InteracaoInput
    ) -> dict[str, Any]:
        values = payload.model_dump()
        row = (
            await self.session.execute(
                text(
                    "INSERT INTO comunicacao.interacao "
                    "(tenant_id, pessoa_id, tipo_interacao_id, canal_comunicacao_id, "
                    "lideranca_id, demanda_id, evento_id, direcao, assunto, conteudo, "
                    "resultado, data_interacao, registrado_por) VALUES "
                    "(:tenant_id, :person_id, :tipo_interacao_id, :canal_comunicacao_id, "
                    ":lideranca_id, :demanda_id, :evento_id, :direcao, :assunto, :conteudo, "
                    ":resultado, COALESCE(:data_interacao, now()), :user_id) RETURNING id"
                ),
                {"tenant_id": tenant_id, "user_id": user_id, "person_id": person_id, **values},
            )
        ).scalar_one()
        item = await self.get_interaction(tenant_id, int(row))
        assert item is not None
        return item

    async def get_interaction(self, tenant_id: int, interaction_id: int) -> dict[str, Any] | None:
        row = (
            await self.session.execute(
                text(
                    self._interaction_select()
                    + " WHERE i.tenant_id = :tenant_id AND i.id = :id"
                ),
                {"tenant_id": tenant_id, "id": interaction_id},
            )
        ).mappings().first()
        return dict(row) if row else None

    async def list_person_interactions(
        self, tenant_id: int, person_id: int, limit: int
    ) -> list[dict[str, Any]]:
        rows = (
            await self.session.execute(
                text(
                    self._interaction_select()
                    + " WHERE i.tenant_id = :tenant_id AND i.pessoa_id = :person_id "
                    "ORDER BY i.data_interacao DESC, i.id DESC LIMIT :limit"
                ),
                {"tenant_id": tenant_id, "person_id": person_id, "limit": limit},
            )
        ).mappings()
        return [dict(row) for row in rows]

    async def commit(self) -> None:
        await self.session.commit()

    @staticmethod
    def _interaction_select() -> str:
        return (
            "SELECT i.id, i.tenant_id, i.pessoa_id, p.nome_completo AS pessoa_nome, "
            "i.tipo_interacao_id, ti.nome AS tipo_interacao_nome, "
            "i.canal_comunicacao_id, cc.nome AS canal_comunicacao_nome, "
            "i.lideranca_id, i.demanda_id, i.evento_id, i.direcao, i.assunto, "
            "i.conteudo, i.resultado, i.data_interacao, i.registrado_por, "
            "u.nome AS registrado_por_nome, i.criado_em "
            "FROM comunicacao.interacao i "
            "JOIN cadastro.pessoa p ON p.id = i.pessoa_id AND p.tenant_id = i.tenant_id "
            "LEFT JOIN comunicacao.tipo_interacao ti ON ti.id = i.tipo_interacao_id "
            "LEFT JOIN comunicacao.canal_comunicacao cc ON cc.id = i.canal_comunicacao_id "
            "LEFT JOIN auth.usuario u ON u.id = i.registrado_por "
        )

    @classmethod
    def _table(cls, catalog: str) -> str:
        if catalog not in cls.CATALOGS:
            raise ValueError("Catalogo de comunicacao invalido.")
        return cls.CATALOGS[catalog]
