"""Acesso a dados do dominio de territorio."""

from __future__ import annotations

from collections.abc import Iterable
import json
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

AREA_MAPA_TERRITORY_TYPES = frozenset(
    {"microrregiao", "comunidade", "area_personalizada"}
)
MESH_TERRITORY_TYPES = AREA_MAPA_TERRITORY_TYPES | {"bairro"}
MAP_MESH_TYPES = frozenset(
    {"municipio", "bairro", "microrregiao", "comunidade", "area_personalizada"}
)

_GEOJSON_TO_MULTIPOLYGON = (
    "ST_Multi(ST_CollectionExtract("
    "ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326)), 3)"
    ")::geography"
)

_MAP_CONTEXT_TYPES = frozenset({"estado", "municipio", "bairro"}) | AREA_MAPA_TERRITORY_TYPES


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
                "codigo_ibge, codigo_uf_ibge, codigo_tse, nome, latitude, longitude, habitantes"
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

    async def list_electoral_zones(
        self,
        *,
        estado_id: int | None = None,
        codigo_municipio_ibge: int | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        values: dict[str, object] = {}
        if estado_id:
            clauses.append("ze.codigo_uf_ibge = :estado_id")
            values["estado_id"] = estado_id
        if codigo_municipio_ibge:
            clauses.append(
                """
                (
                    ze.codigo_municipio_ibge = :codigo_municipio_ibge
                    OR EXISTS (
                        SELECT 1
                          FROM global.local_votacao lv
                         WHERE lv.zona_eleitoral_id = ze.id
                           AND lv.codigo_municipio_ibge = :codigo_municipio_ibge
                           AND lv.situacao = 'ativo'
                    )
                )
                """
            )
            values["codigo_municipio_ibge"] = codigo_municipio_ibge
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        result = await self.session.execute(
            text(
                f"""
                SELECT ze.id, ze.codigo_uf_ibge, ze.codigo_municipio_ibge,
                       ze.numero_zona, ze.descricao
                  FROM global.zona_eleitoral ze
                {where}
                 ORDER BY ze.numero_zona, ze.id
                """
            ),
            values,
        )
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
                " tt.nome AS tipo_nome, t.nome, t.nome, t.codigo_uf_ibge,"
                " t.codigo_municipio_ibge, t.bairro_id,"
                " t.zona_eleitoral_id, t.secao_eleitoral_id, h.territorio_pai_id, t.cor,"
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
        if not rows:
            return None
        return await self.attach_territory_mesh(tenant_id, rows[0])

    async def attach_territory_mesh(
        self, tenant_id: int, territory: dict[str, Any]
    ) -> dict[str, Any]:
        enriched = dict(territory)
        enriched["malha_geom"] = await self.get_territory_mesh(
            tenant_id,
            territory["id"],
            territory["tipo_codigo"],
            territory.get("bairro_id"),
        )
        return enriched

    async def get_territory_mesh(
        self,
        tenant_id: int,
        territory_id: int,
        tipo_codigo: str,
        bairro_id: int | None,
    ) -> dict[str, Any] | None:
        if tipo_codigo in AREA_MAPA_TERRITORY_TYPES:
            result = await self.session.execute(
                text(
                    "SELECT ST_AsGeoJSON(am.geom::geometry, 6)::json AS geometry"
                    " FROM territorio.area_mapa am"
                    " WHERE am.tenant_id = :tenant_id"
                    " AND am.territorio_id = :territory_id"
                ),
                {"tenant_id": tenant_id, "territory_id": territory_id},
            )
            row = result.mappings().one_or_none()
            geometry = row["geometry"] if row else None
            return geometry if isinstance(geometry, dict) else None

        if tipo_codigo == "bairro" and bairro_id:
            result = await self.session.execute(
                text(
                    "SELECT ST_AsGeoJSON(b.limite_geom::geometry, 6)::json AS geometry"
                    " FROM global.bairro b"
                    " WHERE b.id = :bairro_id AND b.limite_geom IS NOT NULL"
                ),
                {"bairro_id": bairro_id},
            )
            row = result.mappings().one_or_none()
            geometry = row["geometry"] if row else None
            return geometry if isinstance(geometry, dict) else None

        return None

    async def save_territory_mesh(
        self,
        tenant_id: int,
        territory_id: int,
        tipo_codigo: str,
        nome: str,
        cor: str,
        bairro_id: int | None,
        malha_geom: dict[str, Any] | None,
    ) -> None:
        if tipo_codigo in AREA_MAPA_TERRITORY_TYPES:
            if malha_geom is None:
                await self.delete_area_mapa_by_territory(tenant_id, territory_id)
                return
            await self.upsert_area_mapa(
                tenant_id,
                territory_id,
                nome,
                cor,
                json.dumps(malha_geom, ensure_ascii=False, separators=(",", ":")),
            )
            return

        if tipo_codigo == "bairro":
            if not bairro_id:
                return
            geojson = (
                json.dumps(malha_geom, ensure_ascii=False, separators=(",", ":"))
                if malha_geom is not None
                else None
            )
            await self.update_bairro_limite_geom(bairro_id, geojson)

    async def delete_area_mapa_by_territory(
        self, tenant_id: int, territory_id: int
    ) -> None:
        await self.session.execute(
            text(
                "DELETE FROM territorio.area_mapa"
                " WHERE tenant_id = :tenant_id AND territorio_id = :territory_id"
            ),
            {"tenant_id": tenant_id, "territory_id": territory_id},
        )

    async def upsert_area_mapa(
        self,
        tenant_id: int,
        territory_id: int,
        nome: str,
        cor: str,
        geojson: str,
    ) -> None:
        existing_id = await self.session.scalar(
            text(
                "SELECT id FROM territorio.area_mapa"
                " WHERE tenant_id = :tenant_id AND territorio_id = :territory_id"
            ),
            {"tenant_id": tenant_id, "territory_id": territory_id},
        )
        if existing_id:
            await self.session.execute(
                text(
                    f"UPDATE territorio.area_mapa"
                    f" SET nome = :nome, cor = :cor, geom = {_GEOJSON_TO_MULTIPOLYGON}"
                    f" WHERE id = :id AND tenant_id = :tenant_id"
                ),
                {
                    "id": existing_id,
                    "tenant_id": tenant_id,
                    "nome": nome,
                    "cor": cor,
                    "geojson": geojson,
                },
            )
            return

        await self.session.execute(
            text(
                f"INSERT INTO territorio.area_mapa"
                f" (tenant_id, territorio_id, nome, geom, cor)"
                f" VALUES (:tenant_id, :territory_id, :nome, {_GEOJSON_TO_MULTIPOLYGON}, :cor)"
            ),
            {
                "tenant_id": tenant_id,
                "territory_id": territory_id,
                "nome": nome,
                "cor": cor,
                "geojson": geojson,
            },
        )

    async def update_bairro_limite_geom(
        self, bairro_id: int, geojson: str | None
    ) -> None:
        if geojson is None:
            await self.session.execute(
                text("UPDATE global.bairro SET limite_geom = NULL WHERE id = :bairro_id"),
                {"bairro_id": bairro_id},
            )
            return

        await self.session.execute(
            text(
                f"UPDATE global.bairro SET limite_geom = {_GEOJSON_TO_MULTIPOLYGON}"
                f" WHERE id = :bairro_id"
            ),
            {"bairro_id": bairro_id, "geojson": geojson},
        )

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
        values = payload.model_dump(exclude={"territorio_pai_id", "malha_geom"})
        territory_id = int(
            await self.session.scalar(
                text(
                    "INSERT INTO territorio.territorio "
                    "(tenant_id, tipo_territorio_id, nome, codigo_uf_ibge,"
                    " codigo_municipio_ibge, bairro_id,"
                    " zona_eleitoral_id, secao_eleitoral_id, cor) "
                    "VALUES (:tenant_id, :tipo_territorio_id, :nome, :codigo_uf_ibge,"
                    " :codigo_municipio_ibge,"
                    " :bairro_id, :zona_eleitoral_id, :secao_eleitoral_id, :cor) RETURNING id"
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
        values = payload.model_dump(
            exclude_unset=True,
            exclude={"territorio_pai_id", "malha_geom"},
        )
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

    async def get_territory_map_context(
        self, tenant_id: int, territory_id: int
    ) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(
                "SELECT t.id, tt.codigo AS tipo_codigo,"
                " t.codigo_municipio_ibge, t.codigo_uf_ibge"
                " FROM territorio.territorio t"
                " JOIN territorio.tipo_territorio tt ON tt.id = t.tipo_territorio_id"
                " WHERE t.id = :territory_id AND t.tenant_id = :tenant_id AND t.ativo"
            ),
            {"tenant_id": tenant_id, "territory_id": territory_id},
        )
        row = result.mappings().one_or_none()
        return dict(row) if row else None

    def _build_accessible_filter(
        self, accessible_ids: Iterable[int] | None, values: dict[str, Any]
    ) -> str:
        if accessible_ids is None:
            return ""
        ids = sorted(set(accessible_ids))
        if not ids:
            return " AND FALSE"
        values["accessible_ids"] = ids
        return " AND t.id = ANY(:accessible_ids)"

    def _build_map_scope_filter(
        self,
        context: dict[str, Any] | None,
        layer_tipo: str,
        values: dict[str, Any],
    ) -> str:
        if context is None:
            return ""

        ctx_tipo = context["tipo_codigo"]
        territory_id = context["id"]
        municipio_ibge = context.get("codigo_municipio_ibge")
        uf_ibge = context.get("codigo_uf_ibge")

        if ctx_tipo == layer_tipo:
            values["scope_territory_id"] = territory_id
            return " AND t.id = :scope_territory_id"

        if ctx_tipo == "estado" and uf_ibge:
            values["scope_uf_ibge"] = uf_ibge
            if layer_tipo == "municipio":
                return " AND t.codigo_uf_ibge = :scope_uf_ibge"
            return (
                " AND t.codigo_municipio_ibge IN ("
                "  SELECT m_scope.codigo_ibge FROM global.municipio m_scope"
                "  WHERE m_scope.codigo_uf_ibge = :scope_uf_ibge"
                " )"
            )

        if municipio_ibge and ctx_tipo in _MAP_CONTEXT_TYPES:
            values["scope_municipio_ibge"] = municipio_ibge
            if layer_tipo == "municipio":
                return (
                    " AND t.codigo_municipio_ibge = :scope_municipio_ibge"
                    " AND tt.codigo = 'municipio'"
                )
            return " AND t.codigo_municipio_ibge = :scope_municipio_ibge"

        values["scope_territory_id"] = territory_id
        return " AND t.id = :scope_territory_id"

    async def map_municipality_shapes(
        self,
        tenant_id: int,
        accessible_ids: Iterable[int] | None,
        context_territory_id: int | None = None,
    ) -> list[dict[str, Any]]:
        values: dict[str, Any] = {"tenant_id": tenant_id}
        context = (
            await self.get_territory_map_context(tenant_id, context_territory_id)
            if context_territory_id
            else None
        )
        scope_filter = self._build_map_scope_filter(context, "municipio", values)
        access_filter = self._build_accessible_filter(accessible_ids, values)
        result = await self.session.execute(
            text(
                "SELECT t.id AS territorio_id, t.codigo_municipio_ibge, t.nome, t.cor,"
                " COALESCE(eleitorado.quantidade_eleitores, 0)::int AS quantidade_eleitores,"
                " COALESCE(people.quantidade, 0)::int AS quantidade_pessoas,"
                " ST_AsGeoJSON(m.limite_geom::geometry, 6)::json AS geometry"
                " FROM territorio.territorio t"
                " JOIN territorio.tipo_territorio tt ON tt.id = t.tipo_territorio_id"
                " JOIN global.municipio m ON m.codigo_ibge = t.codigo_municipio_ibge"
                " LEFT JOIN LATERAL ("
                "  SELECT pem.quantidade_eleitores"
                "  FROM tse.perfil_eleitorado_municipio pem"
                "  WHERE pem.codigo_municipio_ibge = t.codigo_municipio_ibge"
                "  ORDER BY pem.ano DESC"
                "  LIMIT 1"
                " ) eleitorado ON true"
                " LEFT JOIN LATERAL ("
                "  SELECT count(DISTINCT p.id)::int AS quantidade"
                "  FROM territorio.pessoa_territorio pt"
                "  JOIN cadastro.pessoa p ON p.id = pt.pessoa_id"
                "  AND p.tenant_id = pt.tenant_id"
                "  WHERE pt.territorio_id = t.id AND pt.tenant_id = t.tenant_id"
                "  AND p.ativo AND p.excluido_em IS NULL"
                " ) people ON true"
                " WHERE t.tenant_id = :tenant_id AND t.ativo"
                " AND tt.codigo = 'municipio' AND m.limite_geom IS NOT NULL"
                f"{scope_filter}{access_filter}"
                " ORDER BY t.nome, t.id"
            ),
            values,
        )
        return [dict(row) for row in result.mappings()]

    async def map_territory_shapes(
        self,
        tenant_id: int,
        tipo_codigo: str,
        accessible_ids: Iterable[int] | None,
        context_territory_id: int | None = None,
    ) -> list[dict[str, Any]]:
        if tipo_codigo == "municipio":
            rows = await self.map_municipality_shapes(
                tenant_id, accessible_ids, context_territory_id
            )
            return [{**row, "tipo_codigo": "municipio"} for row in rows]

        if tipo_codigo not in AREA_MAPA_TERRITORY_TYPES and tipo_codigo != "bairro":
            return []

        values: dict[str, Any] = {"tenant_id": tenant_id, "tipo_codigo": tipo_codigo}
        context = (
            await self.get_territory_map_context(tenant_id, context_territory_id)
            if context_territory_id
            else None
        )
        scope_filter = self._build_map_scope_filter(context, tipo_codigo, values)
        access_filter = self._build_accessible_filter(accessible_ids, values)

        if tipo_codigo == "bairro":
            geometry_source = "b.limite_geom"
            join_clause = " JOIN global.bairro b ON b.id = t.bairro_id"
            geom_filter = " AND b.limite_geom IS NOT NULL"
        else:
            geometry_source = "am.geom"
            join_clause = (
                " JOIN territorio.area_mapa am"
                " ON am.territorio_id = t.id AND am.tenant_id = t.tenant_id"
            )
            geom_filter = " AND am.geom IS NOT NULL"

        result = await self.session.execute(
            text(
                f"SELECT t.id AS territorio_id, tt.codigo AS tipo_codigo,"
                f" t.codigo_municipio_ibge, t.nome, t.cor,"
                f" 0::int AS quantidade_eleitores,"
                f" COALESCE(people.quantidade, 0)::int AS quantidade_pessoas,"
                f" ST_AsGeoJSON({geometry_source}::geometry, 6)::json AS geometry"
                f" FROM territorio.territorio t"
                f" JOIN territorio.tipo_territorio tt ON tt.id = t.tipo_territorio_id"
                f"{join_clause}"
                f" LEFT JOIN LATERAL ("
                f"  SELECT count(DISTINCT p.id)::int AS quantidade"
                f"  FROM territorio.pessoa_territorio pt"
                f"  JOIN cadastro.pessoa p ON p.id = pt.pessoa_id"
                f"  AND p.tenant_id = pt.tenant_id"
                f"  WHERE pt.territorio_id = t.id AND pt.tenant_id = t.tenant_id"
                f"  AND p.ativo AND p.excluido_em IS NULL"
                f" ) people ON true"
                f" WHERE t.tenant_id = :tenant_id AND t.ativo"
                f" AND tt.codigo = :tipo_codigo{geom_filter}"
                f"{scope_filter}{access_filter}"
                f" ORDER BY t.nome, t.id"
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

    async def territory_detail(
        self, tenant_id: int, territory_id: int
    ) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(
                "SELECT t.id AS territorio_id, t.nome AS territorio_nome, t.cor,"
                " t.codigo_municipio_ibge, t.codigo_uf_ibge,"
                " tt.codigo AS tipo_codigo, tt.nome AS tipo_nome,"
                " e.uf, e.nome AS estado_nome,"
                " m.nome AS municipio_nome,"
                " CASE"
                "  WHEN tt.codigo = 'estado' THEN ("
                "   SELECT COALESCE(SUM(m2.habitantes), 0)::int"
                "   FROM global.municipio m2"
                "   WHERE m2.codigo_uf_ibge = t.codigo_uf_ibge"
                "  )"
                "  ELSE m.habitantes"
                " END AS habitantes,"
                " CASE"
                "  WHEN tt.codigo = 'estado' THEN ("
                "   SELECT COALESCE(SUM(pem.quantidade_eleitores), 0)::int"
                "   FROM tse.perfil_eleitorado_municipio pem"
                "   WHERE pem.codigo_uf_ibge = t.codigo_uf_ibge"
                "   AND pem.ano = ("
                "    SELECT MAX(ano) FROM tse.perfil_eleitorado_municipio"
                "    WHERE codigo_uf_ibge = t.codigo_uf_ibge"
                "   )"
                "  )"
                "  ELSE COALESCE(eleitorado.quantidade_eleitores, 0)::int"
                " END AS quantidade_eleitores,"
                " CASE"
                "  WHEN tt.codigo = 'estado' THEN ("
                "   SELECT count(DISTINCT p.id)::int"
                "   FROM territorio.territorio_hierarquia th"
                "   JOIN territorio.pessoa_territorio pt"
                "    ON pt.territorio_id = th.territorio_filho_id"
                "   AND pt.tenant_id = th.tenant_id"
                "   JOIN cadastro.pessoa p ON p.id = pt.pessoa_id"
                "   AND p.tenant_id = pt.tenant_id"
                "   WHERE th.territorio_pai_id = t.id"
                "   AND th.tenant_id = t.tenant_id"
                "   AND p.ativo AND p.excluido_em IS NULL"
                "  )"
                "  ELSE COALESCE(people.quantidade, 0)::int"
                " END AS quantidade_pessoas,"
                " CASE"
                "  WHEN tt.codigo = 'estado' AND e.limite_geom IS NOT NULL"
                "  THEN ST_AsGeoJSON(e.limite_geom::geometry, 6)::json"
                "  WHEN tt.codigo = 'municipio' AND m.limite_geom IS NOT NULL"
                "  THEN ST_AsGeoJSON(m.limite_geom::geometry, 6)::json"
                "  WHEN tt.codigo IN ('microrregiao', 'comunidade', 'area_personalizada')"
                "   AND am.geom IS NOT NULL"
                "  THEN ST_AsGeoJSON(am.geom::geometry, 6)::json"
                "  WHEN tt.codigo = 'bairro' AND b.limite_geom IS NOT NULL"
                "  THEN ST_AsGeoJSON(b.limite_geom::geometry, 6)::json"
                "  ELSE NULL"
                " END AS geometry"
                " FROM territorio.territorio t"
                " JOIN territorio.tipo_territorio tt ON tt.id = t.tipo_territorio_id"
                " LEFT JOIN global.estado e ON e.codigo_ibge = t.codigo_uf_ibge"
                " LEFT JOIN global.municipio m ON m.codigo_ibge = t.codigo_municipio_ibge"
                " LEFT JOIN global.bairro b ON b.id = t.bairro_id"
                " LEFT JOIN territorio.area_mapa am"
                "  ON am.territorio_id = t.id AND am.tenant_id = t.tenant_id"
                " LEFT JOIN LATERAL ("
                "  SELECT pem.quantidade_eleitores"
                "  FROM tse.perfil_eleitorado_municipio pem"
                "  WHERE pem.codigo_municipio_ibge = t.codigo_municipio_ibge"
                "  ORDER BY pem.ano DESC"
                "  LIMIT 1"
                " ) eleitorado ON true"
                " LEFT JOIN LATERAL ("
                "  SELECT count(DISTINCT p.id)::int AS quantidade"
                "  FROM territorio.pessoa_territorio pt"
                "  JOIN cadastro.pessoa p ON p.id = pt.pessoa_id"
                "  AND p.tenant_id = pt.tenant_id"
                "  WHERE pt.territorio_id = t.id AND pt.tenant_id = t.tenant_id"
                "  AND p.ativo AND p.excluido_em IS NULL"
                " ) people ON true"
                " WHERE t.id = :territory_id AND t.tenant_id = :tenant_id AND t.ativo"
            ),
            {"tenant_id": tenant_id, "territory_id": territory_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            return None
        detail = dict(row)
        if detail.get("tipo_codigo") == "municipio":
            detail["pessoas"] = await self.territory_linked_people(tenant_id, territory_id)
        else:
            detail["pessoas"] = []
        return detail

    async def territory_linked_people(
        self, tenant_id: int, territory_id: int
    ) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text(
                "SELECT DISTINCT ON (p.id) p.id, p.nome_completo,"
                " phone.valor AS telefone, email.valor AS email,"
                " COALESCE(roles.papeis, 'Sem papel') AS papel"
                " FROM territorio.pessoa_territorio pt_link"
                " JOIN cadastro.pessoa p ON p.id = pt_link.pessoa_id"
                " AND p.tenant_id = pt_link.tenant_id"
                " LEFT JOIN LATERAL ("
                "  SELECT pc.valor FROM cadastro.pessoa_contato pc"
                "  WHERE pc.pessoa_id = p.id AND pc.tenant_id = p.tenant_id"
                "  AND pc.tipo_contato IN ('whatsapp', 'celular', 'telefone')"
                "  ORDER BY CASE pc.tipo_contato"
                "   WHEN 'whatsapp' THEN 0 WHEN 'celular' THEN 1 ELSE 2 END,"
                "   pc.principal DESC, pc.id LIMIT 1"
                " ) phone ON true"
                " LEFT JOIN LATERAL ("
                "  SELECT pc.valor FROM cadastro.pessoa_contato pc"
                "  WHERE pc.pessoa_id = p.id AND pc.tenant_id = p.tenant_id"
                "  AND pc.tipo_contato = 'email'"
                "  ORDER BY pc.principal DESC, pc.id LIMIT 1"
                " ) email ON true"
                " LEFT JOIN LATERAL ("
                "  SELECT string_agg(DISTINCT pt_tipo.nome, ', '"
                "   ORDER BY pt_tipo.nome) AS papeis"
                "  FROM cadastro.pessoa_pessoa_tipo ppt"
                "  JOIN cadastro.pessoa_tipo pt_tipo ON pt_tipo.id = ppt.pessoa_tipo_id"
                "  WHERE ppt.pessoa_id = p.id AND ppt.tenant_id = p.tenant_id"
                " ) roles ON true"
                " WHERE pt_link.territorio_id = :territory_id"
                " AND pt_link.tenant_id = :tenant_id"
                " AND p.ativo AND p.excluido_em IS NULL"
                " ORDER BY p.id, p.nome_completo"
            ),
            {"tenant_id": tenant_id, "territory_id": territory_id},
        )
        return [dict(row) for row in result.mappings()]

    async def commit(self) -> None:
        await self.session.commit()
