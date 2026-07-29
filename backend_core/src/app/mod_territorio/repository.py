"""Acesso a dados do dominio de territorio."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.access import TerritorialAccess
from app.core.repository import BaseRepository
from app.mod_territorio.schemas import (
    BairroCreate,
    GeocodificacaoInput,
    LiderancaTerritorioInput,
    PessoaTerritorioInput,
    TerritorioCreate,
    TerritorioUpdate,
    TipoTerritorioCreate,
    TipoTerritorioUpdate,
)


class TerritorioRepository(BaseRepository[object]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def global_list(
        self,
        table: str,
        where: str = "",
        values: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        allowed = {
            "estado",
            "municipio",
            "bairro",
            "zona_eleitoral",
            "local_votacao",
            "secao_eleitoral",
        }
        if table not in allowed:
            raise ValueError("Tabela global nao permitida.")
        columns = {
            "estado": "codigo_ibge, uf, nome, regiao",
            "municipio": (
                "codigo_ibge, codigo_uf_ibge, codigo_tse, nome, latitude, longitude"
            ),
            "bairro": "id, codigo_municipio_ibge, nome, origem",
            "zona_eleitoral": (
                "id, codigo_uf_ibge, codigo_municipio_ibge, numero_zona, descricao"
            ),
            "local_votacao": (
                "id, codigo_municipio_ibge, zona_eleitoral_id, bairro_id, codigo_local, nome,"
                " logradouro, numero, complemento, cep, latitude, longitude, situacao"
            ),
            "secao_eleitoral": (
                "id, zona_eleitoral_id, local_votacao_id, numero_secao, agregada_em"
            ),
        }
        query = f"SELECT {columns[table]} FROM global.{table}"
        if where:
            query += f" WHERE {where}"
        named_tables = {"estado", "municipio", "bairro", "local_votacao"}
        query += " ORDER BY nome" if table in named_tables else " ORDER BY id"
        result = await self.session.execute(text(query), values or {})
        return [dict(row) for row in result.mappings()]

    async def create_neighborhood(self, payload: BairroCreate) -> dict[str, Any]:
        existing = await self.session.execute(
            text(
                "SELECT id, codigo_municipio_ibge, nome, origem"
                " FROM global.bairro"
                " WHERE codigo_municipio_ibge = :codigo_municipio_ibge"
                " AND unaccent(lower(btrim(nome))) = unaccent(lower(btrim(:nome)))"
                " ORDER BY CASE WHEN origem = 'oficial' THEN 0 ELSE 1 END, id"
                " LIMIT 1"
            ),
            payload.model_dump(),
        )
        row = existing.mappings().one_or_none()
        if row is not None:
            return dict(row)
        result = await self.session.execute(
            text(
                "INSERT INTO global.bairro (codigo_municipio_ibge, nome, origem)"
                " VALUES (:codigo_municipio_ibge, btrim(:nome), 'usuario')"
                " ON CONFLICT (codigo_municipio_ibge, nome) DO UPDATE"
                " SET nome = EXCLUDED.nome"
                " RETURNING id, codigo_municipio_ibge, nome, origem"
            ),
            payload.model_dump(),
        )
        return dict(result.mappings().one())

    async def list_types(
        self, tenant_id: int, include_inactive: bool = False
    ) -> list[dict[str, Any]]:
        inactive = "" if include_inactive else "AND ativo"
        result = await self.session.execute(
            text(
                "SELECT id, tenant_id, codigo, nome, descricao, ativo "
                "FROM territorio.tipo_territorio "
                "WHERE (tenant_id IS NULL OR tenant_id = :tenant_id) "
                f"{inactive} ORDER BY tenant_id NULLS FIRST, nome"
            ),
            {"tenant_id": tenant_id},
        )
        return [dict(row) for row in result.mappings()]

    async def get_type(self, tenant_id: int, type_id: int) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(
                "SELECT id, tenant_id, codigo, nome, descricao, ativo "
                "FROM territorio.tipo_territorio WHERE id = :id "
                "AND (tenant_id IS NULL OR tenant_id = :tenant_id)"
            ),
            {"id": type_id, "tenant_id": tenant_id},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def create_type(
        self, tenant_id: int, payload: TipoTerritorioCreate
    ) -> dict[str, Any]:
        result = await self.session.execute(
            text(
                "INSERT INTO territorio.tipo_territorio "
                "(tenant_id, codigo, nome, descricao) "
                "VALUES (:tenant_id, :codigo, :nome, :descricao) "
                "RETURNING id, tenant_id, codigo, nome, descricao, ativo"
            ),
            {"tenant_id": tenant_id, **payload.model_dump()},
        )
        return dict(result.mappings().one())

    async def update_type(
        self, tenant_id: int, type_id: int, payload: TipoTerritorioUpdate
    ) -> dict[str, Any] | None:
        values = payload.model_dump(exclude_unset=True)
        if not values:
            return await self.get_type(tenant_id, type_id)
        assignments = ", ".join(f"{key} = :{key}" for key in values)
        result = await self.session.execute(
            text(
                f"UPDATE territorio.tipo_territorio SET {assignments} "
                "WHERE id = :id AND tenant_id = :tenant_id "
                "RETURNING id, tenant_id, codigo, nome, descricao, ativo"
            ),
            {"id": type_id, "tenant_id": tenant_id, **values},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def accessible_ids(
        self, tenant_id: int, access: TerritorialAccess
    ) -> set[int] | None:
        if access.unrestricted:
            return None
        ids: set[int] = set()
        for scope_type, scope_id, _ in access.scopes:
            if scope_type == "global":
                return None
            if scope_id is None:
                continue
            if scope_type == "territorio":
                rows = await self.session.scalars(
                    text(
                        "WITH RECURSIVE arvore AS ("
                        " SELECT CAST(:scope_id AS bigint) AS id"
                        " UNION ALL"
                        " SELECT h.territorio_filho_id FROM territorio.territorio_hierarquia h"
                        " JOIN arvore a ON a.id = h.territorio_pai_id"
                        " WHERE h.tenant_id = :tenant_id"
                        ") SELECT id FROM arvore"
                    ),
                    {"scope_id": scope_id, "tenant_id": tenant_id},
                )
                ids.update(int(value) for value in rows)
                continue
            column = {
                "estado": "codigo_uf_ibge",
                "municipio": "codigo_municipio_ibge",
                "bairro": "bairro_id",
                "zona_eleitoral": "zona_eleitoral_id",
                "secao_eleitoral": "secao_eleitoral_id",
            }.get(scope_type)
            if column:
                rows = await self.session.scalars(
                    text(
                        f"SELECT id FROM territorio.territorio "
                        f"WHERE tenant_id = :tenant_id AND {column} = :scope_id"
                    ),
                    {"tenant_id": tenant_id, "scope_id": scope_id},
                )
                ids.update(int(value) for value in rows)
        return ids

    async def list_territories(
        self,
        tenant_id: int,
        *,
        include_inactive: bool,
        type_id: int | None,
        query: str | None,
        accessible_ids: set[int] | None,
    ) -> list[dict[str, Any]]:
        clauses = ["t.tenant_id = :tenant_id"]
        values: dict[str, Any] = {"tenant_id": tenant_id}
        if not include_inactive:
            clauses.append("t.ativo")
        if type_id:
            clauses.append("t.tipo_territorio_id = :type_id")
            values["type_id"] = type_id
        if query:
            clauses.append("t.nome ILIKE :query")
            values["query"] = f"%{query}%"
        if accessible_ids is not None:
            if not accessible_ids:
                return []
            clauses.append("t.id = ANY(:accessible_ids)")
            values["accessible_ids"] = sorted(accessible_ids)
        result = await self.session.execute(
            text(
                "SELECT t.id, t.tenant_id, t.tipo_territorio_id, tt.codigo AS tipo_codigo,"
                " tt.nome AS tipo_nome, t.nome, t.nome, t.codigo_uf_ibge, t.codigo_municipio_ibge, t.bairro_id,"
                " t.zona_eleitoral_id, t.secao_eleitoral_id, h.territorio_pai_id,"
                " t.ativo, t.criado_em, t.atualizado_em"
                " FROM territorio.territorio t"
                " JOIN territorio.tipo_territorio tt ON tt.id = t.tipo_territorio_id"
                " LEFT JOIN territorio.territorio_hierarquia h"
                " ON h.territorio_filho_id = t.id AND h.tenant_id = t.tenant_id"
                f" WHERE {' AND '.join(clauses)} ORDER BY t.nome"
            ),
            values,
        )
        return [dict(row) for row in result.mappings()]

    async def get_territory(self, tenant_id: int, territory_id: int) -> dict[str, Any] | None:
        rows = await self.list_territories(
            tenant_id,
            include_inactive=True,
            type_id=None,
            query=None,
            accessible_ids={territory_id},
        )
        return rows[0] if rows else None

    async def reference_exists(self, table: str, identifier: int) -> bool:
        identifier_columns = {
            "estado": "codigo_ibge",
            "municipio": "codigo_ibge",
            "bairro": "id",
            "zona_eleitoral": "id",
            "secao_eleitoral": "id",
        }
        identifier_column = identifier_columns.get(table)
        if identifier_column is None:
            return False
        return bool(
            await self.session.scalar(
                text(
                    f"SELECT EXISTS(SELECT 1 FROM global.{table} "
                    f"WHERE {identifier_column} = :id)"
                ),
                {"id": identifier},
            )
        )

    async def create_territory(
        self, tenant_id: int, payload: TerritorioCreate
    ) -> dict[str, Any]:
        values = payload.model_dump(exclude={"territorio_pai_id"})
        territory_id = int(
            await self.session.scalar(
                text(
                    "INSERT INTO territorio.territorio "
                    "(tenant_id, tipo_territorio_id, nome, codigo_uf_ibge, codigo_municipio_ibge, bairro_id,"
                    " zona_eleitoral_id, secao_eleitoral_id) "
                    "VALUES (:tenant_id, :tipo_territorio_id, :nome, :codigo_uf_ibge, :codigo_municipio_ibge,"
                    " :bairro_id, :zona_eleitoral_id, :secao_eleitoral_id) RETURNING id"
                ),
                {"tenant_id": tenant_id, **values},
            )
        )
        if payload.territorio_pai_id:
            await self.set_parent(tenant_id, territory_id, payload.territorio_pai_id)
        result = await self.get_territory(tenant_id, territory_id)
        assert result is not None
        return result

    async def update_territory(
        self, tenant_id: int, territory_id: int, payload: TerritorioUpdate
    ) -> dict[str, Any] | None:
        values = payload.model_dump(exclude_unset=True, exclude={"territorio_pai_id"})
        if values:
            assignments = ", ".join(f"{key} = :{key}" for key in values)
            await self.session.execute(
                text(
                    f"UPDATE territorio.territorio SET {assignments} "
                    "WHERE id = :id AND tenant_id = :tenant_id"
                ),
                {"id": territory_id, "tenant_id": tenant_id, **values},
            )
        if "territorio_pai_id" in payload.model_fields_set:
            await self.set_parent(tenant_id, territory_id, payload.territorio_pai_id)
        return await self.get_territory(tenant_id, territory_id)

    async def set_parent(self, tenant_id: int, child_id: int, parent_id: int | None) -> None:
        await self.session.execute(
            text(
                "DELETE FROM territorio.territorio_hierarquia "
                "WHERE tenant_id = :tenant_id AND territorio_filho_id = :child_id"
            ),
            {"tenant_id": tenant_id, "child_id": child_id},
        )
        if parent_id is not None:
            await self.session.execute(
                text(
                    "INSERT INTO territorio.territorio_hierarquia "
                    "(tenant_id, territorio_pai_id, territorio_filho_id) "
                    "VALUES (:tenant_id, :parent_id, :child_id)"
                ),
                {"tenant_id": tenant_id, "parent_id": parent_id, "child_id": child_id},
            )

    async def would_create_cycle(self, tenant_id: int, child_id: int, parent_id: int) -> bool:
        return bool(
            await self.session.scalar(
                text(
                    "WITH RECURSIVE descendentes AS ("
                    " SELECT territorio_filho_id AS id"
                    " FROM territorio.territorio_hierarquia"
                    " WHERE tenant_id = :tenant_id AND territorio_pai_id = :child_id"
                    " UNION ALL"
                    " SELECT h.territorio_filho_id"
                    " FROM territorio.territorio_hierarquia h"
                    " JOIN descendentes d ON d.id = h.territorio_pai_id"
                    " WHERE h.tenant_id = :tenant_id"
                    ") SELECT :parent_id = :child_id OR EXISTS("
                    " SELECT 1 FROM descendentes WHERE id = :parent_id)"
                ),
                {"tenant_id": tenant_id, "child_id": child_id, "parent_id": parent_id},
            )
        )

    async def entity_exists(self, table: str, tenant_id: int, identifier: int) -> bool:
        allowed = {"pessoa": "cadastro.pessoa", "lideranca": "cadastro.lideranca"}
        qualified = allowed.get(table)
        if not qualified:
            return False
        return bool(
            await self.session.scalar(
                text(
                    f"SELECT EXISTS(SELECT 1 FROM {qualified} "
                    "WHERE id = :id AND tenant_id = :tenant_id)"
                ),
                {"id": identifier, "tenant_id": tenant_id},
            )
        )

    async def link_person(
        self, tenant_id: int, territory_id: int, payload: PessoaTerritorioInput
    ) -> dict[str, Any]:
        result = await self.session.execute(
            text(
                "INSERT INTO territorio.pessoa_territorio "
                "(tenant_id, pessoa_id, territorio_id, vinculo) "
                "VALUES (:tenant_id, :pessoa_id, :territorio_id, :vinculo) "
                "ON CONFLICT (pessoa_id, territorio_id, vinculo) DO UPDATE "
                "SET vinculo = EXCLUDED.vinculo "
                "RETURNING id, tenant_id, pessoa_id, territorio_id, vinculo"
            ),
            {"tenant_id": tenant_id, "territorio_id": territory_id, **payload.model_dump()},
        )
        return dict(result.mappings().one())

    async def list_person_links(
        self,
        tenant_id: int,
        person_id: int,
        accessible_ids: set[int] | None,
    ) -> list[dict[str, Any]]:
        values: dict[str, Any] = {"tenant_id": tenant_id, "person_id": person_id}
        territory_filter = ""
        if accessible_ids is not None:
            if not accessible_ids:
                return []
            territory_filter = "AND pt.territorio_id = ANY(:territory_ids)"
            values["territory_ids"] = sorted(accessible_ids)
        result = await self.session.execute(
            text(
                "SELECT pt.id, pt.tenant_id, pt.pessoa_id, pt.territorio_id, pt.vinculo,"
                " t.nome AS territorio_nome, tt.nome AS tipo_nome,"
                " t.ativo AS territorio_ativo"
                " FROM territorio.pessoa_territorio pt"
                " JOIN territorio.territorio t ON t.id = pt.territorio_id"
                " AND t.tenant_id = pt.tenant_id"
                " JOIN territorio.tipo_territorio tt ON tt.id = t.tipo_territorio_id"
                " WHERE pt.tenant_id = :tenant_id AND pt.pessoa_id = :person_id "
                f" {territory_filter}"
                " ORDER BY t.nome, pt.vinculo, pt.id"
            ),
            values,
        )
        return [dict(row) for row in result.mappings()]

    async def unlink_person(self, tenant_id: int, link_id: int) -> bool:
        result = await self.session.execute(
            text(
                "DELETE FROM territorio.pessoa_territorio "
                "WHERE id = :id AND tenant_id = :tenant_id"
            ),
            {"id": link_id, "tenant_id": tenant_id},
        )
        return bool(cast(CursorResult[Any], result).rowcount)

    async def person_link(self, tenant_id: int, link_id: int) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(
                "SELECT id, pessoa_id, territorio_id, vinculo"
                " FROM territorio.pessoa_territorio"
                " WHERE id = :id AND tenant_id = :tenant_id"
            ),
            {"id": link_id, "tenant_id": tenant_id},
        )
        row = result.mappings().one_or_none()
        return dict(row) if row else None

    async def link_leadership(
        self, tenant_id: int, territory_id: int, payload: LiderancaTerritorioInput
    ) -> dict[str, Any]:
        result = await self.session.execute(
            text(
                "INSERT INTO territorio.lideranca_territorio "
                "(tenant_id, lideranca_id, territorio_id, responsabilidade) "
                "VALUES (:tenant_id, :lideranca_id, :territorio_id, :responsabilidade) "
                "ON CONFLICT (lideranca_id, territorio_id) DO UPDATE "
                "SET responsabilidade = EXCLUDED.responsabilidade "
                "RETURNING id, tenant_id, lideranca_id, territorio_id, responsabilidade"
            ),
            {"tenant_id": tenant_id, "territorio_id": territory_id, **payload.model_dump()},
        )
        return dict(result.mappings().one())

    async def unlink_leadership(self, tenant_id: int, link_id: int) -> bool:
        result = await self.session.execute(
            text(
                "DELETE FROM territorio.lideranca_territorio "
                "WHERE id = :id AND tenant_id = :tenant_id"
            ),
            {"id": link_id, "tenant_id": tenant_id},
        )
        return bool(cast(CursorResult[Any], result).rowcount)

    async def create_geocoding(
        self, tenant_id: int, payload: GeocodificacaoInput
    ) -> dict[str, Any]:
        result = await self.session.execute(
            text(
                "INSERT INTO territorio.geocodificacao "
                "(tenant_id, entidade_tipo, entidade_id, endereco_texto, latitude, longitude,"
                " precisao, provedor, status, processado_em) "
                "VALUES (:tenant_id, :entidade_tipo, :entidade_id, :endereco_texto,"
                " :latitude, :longitude, :precisao, :provedor, :status,"
                " CASE WHEN :status <> 'pendente' THEN now() ELSE NULL END) "
                "RETURNING id, tenant_id, entidade_tipo, entidade_id, endereco_texto,"
                " latitude, longitude, precisao, provedor, status, processado_em, criado_em"
            ),
            {"tenant_id": tenant_id, **payload.model_dump()},
        )
        return dict(result.mappings().one())

    async def map_markers(
        self, tenant_id: int, territory_ids: Iterable[int] | None
    ) -> list[dict[str, Any]]:
        values: dict[str, Any] = {"tenant_id": tenant_id}
        territory_filter = ""
        if territory_ids is not None:
            ids = sorted(set(territory_ids))
            if not ids:
                return []
            territory_filter = "AND pt.territorio_id = ANY(:territory_ids)"
            values["territory_ids"] = ids
        result = await self.session.execute(
            text(
                "SELECT round(e.latitude, 3) AS latitude,"
                " round(e.longitude, 3) AS longitude,"
                " count(DISTINCT pe.pessoa_id)::int AS quantidade,"
                " 'pessoa'::text AS tipo"
                " FROM cadastro.endereco e"
                " JOIN cadastro.pessoa_endereco pe ON pe.endereco_id = e.id"
                " JOIN territorio.pessoa_territorio pt ON pt.pessoa_id = pe.pessoa_id"
                " AND pt.tenant_id = pe.tenant_id"
                " WHERE e.tenant_id = :tenant_id AND e.latitude IS NOT NULL"
                f" AND e.longitude IS NOT NULL {territory_filter}"
                " GROUP BY round(e.latitude, 3), round(e.longitude, 3)"
                " ORDER BY quantidade DESC LIMIT 2000"
            ),
            values,
        )
        return [dict(row) for row in result.mappings()]

    async def map_people(
        self,
        tenant_id: int,
        latitude: Any,
        longitude: Any,
        territory_ids: Iterable[int] | None,
    ) -> list[dict[str, Any]]:
        values: dict[str, Any] = {
            "tenant_id": tenant_id,
            "latitude": latitude,
            "longitude": longitude,
        }
        territory_filter = ""
        if territory_ids is not None:
            ids = sorted(set(territory_ids))
            if not ids:
                return []
            territory_filter = "AND pt.territorio_id = ANY(:territory_ids)"
            values["territory_ids"] = ids
        result = await self.session.execute(
            text(
                "SELECT DISTINCT ON (p.id) p.id, p.nome_completo, p.apelido,"
                " contact.valor AS telefone, t.nome AS territorio"
                " FROM cadastro.endereco e"
                " JOIN cadastro.pessoa_endereco pe ON pe.endereco_id = e.id"
                " JOIN cadastro.pessoa p ON p.id = pe.pessoa_id"
                " AND p.tenant_id = pe.tenant_id"
                " JOIN territorio.pessoa_territorio pt ON pt.pessoa_id = p.id"
                " AND pt.tenant_id = p.tenant_id"
                " LEFT JOIN territorio.territorio t ON t.id = pt.territorio_id"
                " LEFT JOIN LATERAL ("
                "  SELECT pc.valor FROM cadastro.pessoa_contato pc"
                "  WHERE pc.tenant_id = p.tenant_id AND pc.pessoa_id = p.id"
                "  AND pc.tipo_contato IN ('whatsapp','celular','telefone')"
                "  ORDER BY pc.principal DESC, pc.id LIMIT 1"
                " ) contact ON true"
                " WHERE e.tenant_id = :tenant_id AND p.ativo"
                " AND p.excluido_em IS NULL"
                " AND round(e.latitude, 3) = :latitude"
                " AND round(e.longitude, 3) = :longitude"
                f" {territory_filter}"
                " ORDER BY p.id, pt.id"
            ),
            values,
        )
        return [dict(row) for row in result.mappings()]

    async def commit(self) -> None:
        await self.session.commit()
