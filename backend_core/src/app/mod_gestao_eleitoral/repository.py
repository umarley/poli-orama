from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.mod_gestao_eleitoral.schemas import ResultadoFilters

BASE_FROM = """
FROM tse.resultados_eleicoes re
LEFT JOIN global.municipio m ON m.codigo_tse = re.cd_municipio
LEFT JOIN global.zona_eleitoral ze
  ON ze.codigo_municipio_ibge = m.codigo_ibge
 AND ze.numero_zona = re.nr_zona
LEFT JOIN global.secao_eleitoral se
  ON se.zona_eleitoral_id = ze.id
 AND se.numero_secao = re.nr_secao
LEFT JOIN global.local_votacao lv ON lv.id = se.local_votacao_id
"""

CANDIDATE_ONLY = (
    "re.nm_votavel IS NOT NULL "
    "AND upper(btrim(re.nm_votavel)) NOT IN ("
    "'BRANCO', 'NULO', 'VOTO BRANCO', 'VOTO NULO', 'VOTOS BRANCOS', 'VOTOS NULOS'"
    ") "
    "AND COALESCE(re.nr_votavel, 0) NOT IN (95, 96, 97)"
)


@dataclass(slots=True)
class TerritorialScope:
    unrestricted: bool = False
    ufs: list[str] = field(default_factory=list)
    municipios_ibge: list[int] = field(default_factory=list)
    zonas_ids: list[int] = field(default_factory=list)
    secoes_ids: list[int] = field(default_factory=list)

    @property
    def blocks_all(self) -> bool:
        return not self.unrestricted and not (
            self.ufs or self.municipios_ibge or self.zonas_ids or self.secoes_ids
        )


class GestaoEleitoralRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _all(self, query: str, values: dict[str, Any]) -> list[dict[str, Any]]:
        rows = (await self.session.execute(text(query), values)).mappings()
        return [dict(row) for row in rows]

    async def _one(self, query: str, values: dict[str, Any]) -> dict[str, Any]:
        row = (await self.session.execute(text(query), values)).mappings().one()
        return dict(row)

    def _filters(
        self,
        filters: ResultadoFilters,
        scope: TerritorialScope,
        *,
        include_candidates: bool = True,
        extra: dict[str, Any] | None = None,
    ) -> tuple[str, dict[str, Any]]:
        clauses: list[str] = []
        values: dict[str, Any] = dict(extra or {})
        election_clauses: list[str] = []
        for index, chave in enumerate(filters.eleicao_chaves):
            parts = str(chave).split(":")
            if len(parts) != 3:
                continue
            year, code, turn = parts
            conds: list[str] = []
            if year:
                name = f"eleicao_aa_{index}"
                conds.append(f"re.aa_eleicao = :{name}")
                values[name] = int(year)
            if code:
                name = f"eleicao_cd_{index}"
                conds.append(f"re.cd_eleicao = :{name}")
                values[name] = int(code)
            if turn:
                name = f"eleicao_turno_{index}"
                conds.append(f"re.nr_turno = :{name}")
                values[name] = int(turn)
            if conds:
                election_clauses.append(f"({' AND '.join(conds)})")
        if election_clauses:
            clauses.append(f"({' OR '.join(election_clauses)})")
        list_filters: tuple[tuple[str, str, list[Any]], ...] = (
            ("sg_uf", "re.sg_uf = ANY(:sg_uf)", filters.ufs),
            ("cd_municipio", "re.cd_municipio = ANY(:cd_municipio)", list(filters.cd_municipio)),
            ("ds_cargo", "re.ds_cargo = ANY(:ds_cargo)", filters.cargos),
            ("nr_zona", "re.nr_zona = ANY(:nr_zona)", list(filters.nr_zona)),
            (
                "nr_local_votacao",
                "re.nr_local_votacao = ANY(:nr_local_votacao)",
                list(filters.nr_local_votacao),
            ),
            ("nr_secao", "re.nr_secao = ANY(:nr_secao)", list(filters.nr_secao)),
        )
        for name, clause, value in list_filters:
            if not value:
                continue
            clauses.append(clause)
            values[name] = value
        if include_candidates and filters.votaveis:
            clauses.append("re.nm_votavel = ANY(:nm_votaveis)")
            values["nm_votaveis"] = filters.votaveis
        if not scope.unrestricted:
            if scope.blocks_all:
                clauses.append("FALSE")
            else:
                parts: list[str] = []
                if scope.ufs:
                    parts.append("re.sg_uf = ANY(:scope_ufs)")
                    values["scope_ufs"] = scope.ufs
                if scope.municipios_ibge:
                    parts.append("m.codigo_ibge = ANY(:scope_municipios)")
                    values["scope_municipios"] = scope.municipios_ibge
                if scope.zonas_ids:
                    parts.append("ze.id = ANY(:scope_zonas)")
                    values["scope_zonas"] = scope.zonas_ids
                if scope.secoes_ids:
                    parts.append("se.id = ANY(:scope_secoes)")
                    values["scope_secoes"] = scope.secoes_ids
                clauses.append(f"({' OR '.join(parts)})" if parts else "FALSE")
        return (" AND ".join(clauses) if clauses else "TRUE"), values

    def _from_clause(self, scope: TerritorialScope, *, geo: bool) -> str:
        needs_geo = geo or bool(scope.municipios_ibge or scope.zonas_ids or scope.secoes_ids)
        return BASE_FROM if needs_geo else "FROM tse.resultados_eleicoes re"

    async def resolve_scope_references(
        self,
        estado_ids: list[int],
        bairro_ids: list[int],
        territorio_ids: list[int],
        tenant_id: int,
    ) -> tuple[list[str], list[int]]:
        ufs: list[str] = []
        municipios: list[int] = []
        if estado_ids:
            rows = await self._all(
                "SELECT uf FROM global.estado WHERE codigo_ibge = ANY(CAST(:ids AS INTEGER[]))",
                {"ids": estado_ids},
            )
            ufs = [str(row["uf"]) for row in rows if row.get("uf")]
        if bairro_ids:
            rows = await self._all(
                "SELECT DISTINCT codigo_municipio_ibge AS codigo "
                "FROM global.bairro WHERE id = ANY(CAST(:ids AS INTEGER[]))",
                {"ids": bairro_ids},
            )
            municipios.extend(int(row["codigo"]) for row in rows if row.get("codigo"))
        if territorio_ids:
            rows = await self._all(
                "SELECT DISTINCT codigo_municipio_ibge AS codigo "
                "FROM territorio.territorio "
                "WHERE tenant_id = :tenant_id AND id = ANY(CAST(:ids AS BIGINT[])) "
                "AND codigo_municipio_ibge IS NOT NULL",
                {"ids": territorio_ids, "tenant_id": tenant_id},
            )
            municipios.extend(int(row["codigo"]) for row in rows if row.get("codigo"))
        return ufs, sorted(set(municipios))

    async def list_elections(self, scope: TerritorialScope) -> list[dict[str, Any]]:
        where, values = self._filters(
            ResultadoFilters(), scope, include_candidates=False
        )
        return await self._all(
            f"""
            SELECT DISTINCT ON (re.aa_eleicao, re.cd_eleicao, re.nr_turno)
                   re.aa_eleicao, re.cd_eleicao, re.nr_turno, re.ds_eleicao,
                   re.nm_tipo_eleicao, to_char(re.dt_eleicao, 'YYYY-MM-DD') AS dt_eleicao
            {self._from_clause(scope, geo=False)}
            WHERE {where}
            ORDER BY re.aa_eleicao DESC NULLS LAST, re.cd_eleicao, re.nr_turno
            """,
            values,
        )

    async def search_candidates(
        self, filters: ResultadoFilters, scope: TerritorialScope, query: str, limit: int
    ) -> list[dict[str, Any]]:
        where, values = self._filters(
            filters,
            scope,
            include_candidates=False,
            extra={"q": f"%{query.strip()}%", "limit": limit},
        )
        return await self._all(
            f"""
            SELECT re.nm_votavel, MIN(re.nr_votavel) AS nr_votavel, MIN(re.ds_cargo) AS ds_cargo
            {self._from_clause(scope, geo=False)}
            WHERE {where}
              AND re.nm_votavel ILIKE :q
            GROUP BY re.nm_votavel
            ORDER BY re.nm_votavel
            LIMIT :limit
            """,
            values,
        )

    async def list_states(
        self, filters: ResultadoFilters, scope: TerritorialScope
    ) -> list[dict[str, Any]]:
        where, values = self._filters(filters, scope)
        return await self._all(
            f"""
            SELECT re.sg_uf AS valor,
                   COALESCE(MAX(e.nome), re.sg_uf) AS rotulo
            {self._from_clause(scope, geo=False)}
            LEFT JOIN global.estado e ON e.uf = re.sg_uf
            WHERE {where}
              AND re.sg_uf IS NOT NULL
            GROUP BY re.sg_uf
            ORDER BY re.sg_uf
            """,
            values,
        )

    async def list_municipalities(
        self, filters: ResultadoFilters, scope: TerritorialScope
    ) -> list[dict[str, Any]]:
        where, values = self._filters(filters, scope)
        return await self._all(
            f"""
            SELECT re.cd_municipio AS valor,
                   COALESCE(MAX(m.nome), MAX(re.nm_municipio), re.cd_municipio::text) AS rotulo
            {BASE_FROM}
            WHERE {where}
              AND re.cd_municipio IS NOT NULL
            GROUP BY re.cd_municipio
            ORDER BY 2
            LIMIT 500
            """,
            values,
        )

    async def list_offices(
        self, filters: ResultadoFilters, scope: TerritorialScope
    ) -> list[dict[str, Any]]:
        where, values = self._filters(filters, scope)
        return await self._all(
            f"""
            SELECT re.ds_cargo AS valor, re.ds_cargo AS rotulo
            {BASE_FROM}
            WHERE {where}
              AND re.ds_cargo IS NOT NULL
            GROUP BY re.ds_cargo
            ORDER BY re.ds_cargo
            """,
            values,
        )

    async def list_zones(
        self, filters: ResultadoFilters, scope: TerritorialScope
    ) -> list[dict[str, Any]]:
        where, values = self._filters(filters, scope)
        return await self._all(
            f"""
            SELECT re.nr_zona AS valor,
                   CONCAT('Zona ', re.nr_zona) AS rotulo
            {BASE_FROM}
            WHERE {where}
              AND re.nr_zona IS NOT NULL
            GROUP BY re.nr_zona
            ORDER BY re.nr_zona
            LIMIT 200
            """,
            values,
        )

    async def list_polling_places(
        self, filters: ResultadoFilters, scope: TerritorialScope
    ) -> list[dict[str, Any]]:
        where, values = self._filters(filters, scope)
        return await self._all(
            f"""
            SELECT re.nr_local_votacao AS valor,
                   COALESCE(MAX(lv.nome), MAX(re.nm_local_votacao),
                            CONCAT('Local ', re.nr_local_votacao)) AS rotulo
            {BASE_FROM}
            WHERE {where}
              AND re.nr_local_votacao IS NOT NULL
            GROUP BY re.nr_local_votacao
            ORDER BY 2
            LIMIT 300
            """,
            values,
        )

    async def list_sections(
        self, filters: ResultadoFilters, scope: TerritorialScope
    ) -> list[dict[str, Any]]:
        where, values = self._filters(filters, scope)
        return await self._all(
            f"""
            SELECT re.nr_secao AS valor,
                   CONCAT('Seção ', re.nr_secao) AS rotulo
            {BASE_FROM}
            WHERE {where}
              AND re.nr_secao IS NOT NULL
            GROUP BY re.nr_secao
            ORDER BY re.nr_secao
            LIMIT 400
            """,
            values,
        )

    async def indicators(
        self, filters: ResultadoFilters, scope: TerritorialScope
    ) -> dict[str, Any]:
        where, values = self._filters(filters, scope)
        return await self._one(
            f"""
            SELECT
              COALESCE(SUM(re.qt_votos), 0)::bigint AS total_votos,
              COUNT(DISTINCT re.nm_votavel) FILTER (
                WHERE {CANDIDATE_ONLY}
              )::int AS candidatos,
              COUNT(DISTINCT re.cd_municipio)::int AS municipios,
              COUNT(DISTINCT (re.sg_uf, re.nr_zona))::int AS zonas,
              COUNT(DISTINCT (re.cd_municipio, re.nr_zona, re.nr_local_votacao))::int AS locais,
              COUNT(DISTINCT (re.cd_municipio, re.nr_zona, re.nr_secao))::int AS secoes
            {BASE_FROM}
            WHERE {where}
            """,
            values,
        )

    async def ranking(
        self, filters: ResultadoFilters, scope: TerritorialScope, *, limit: int = 80
    ) -> list[dict[str, Any]]:
        where, values = self._filters(filters, scope)
        values["limit"] = limit
        return await self._all(
            f"""
            SELECT re.nm_votavel,
                   MIN(re.nr_votavel) AS nr_votavel,
                   SUM(re.qt_votos)::bigint AS votos
            {self._from_clause(scope, geo=False)}
            WHERE {where}
              AND {CANDIDATE_ONLY}
            GROUP BY re.nm_votavel
            ORDER BY votos DESC, re.nm_votavel
            LIMIT CAST(:limit AS INTEGER)
            """,
            values,
        )

    async def comparison(
        self, filters: ResultadoFilters, scope: TerritorialScope
    ) -> list[dict[str, Any]]:
        if not filters.votaveis:
            return []
        where, values = self._filters(filters, scope)
        return await self._all(
            f"""
            SELECT re.nm_votavel,
                   MIN(re.nr_votavel) AS nr_votavel,
                   SUM(re.qt_votos)::bigint AS votos
            {BASE_FROM}
            WHERE {where}
            GROUP BY re.nm_votavel
            ORDER BY votos DESC, re.nm_votavel
            """,
            values,
        )

    async def distribution(
        self,
        filters: ResultadoFilters,
        scope: TerritorialScope,
        dimension: str,
        *,
        page: int,
        page_size: int,
        by_candidate: bool = False,
    ) -> tuple[list[dict[str, Any]], int]:
        expressions = {
            "municipio": (
                "COALESCE(MAX(m.nome), MAX(re.nm_municipio), re.cd_municipio::text)",
                "re.cd_municipio",
                "MAX(m.nome) AS municipio, NULL::int AS zona,"
                " NULL::text AS local_votacao, NULL::int AS secao",
            ),
            "zona": (
                "CONCAT('Zona ', re.nr_zona)",
                "re.nr_zona",
                "MAX(COALESCE(m.nome, re.nm_municipio)) AS municipio, re.nr_zona AS zona, "
                "NULL::text AS local_votacao, NULL::int AS secao",
            ),
            "local": (
                "COALESCE(MAX(lv.nome), MAX(re.nm_local_votacao),"
                " CONCAT('Local ', re.nr_local_votacao))",
                "re.nr_local_votacao",
                "MAX(COALESCE(m.nome, re.nm_municipio)) AS municipio, re.nr_zona AS zona, "
                "COALESCE(MAX(lv.nome), MAX(re.nm_local_votacao))"
                " AS local_votacao, NULL::int AS secao",
            ),
            "secao": (
                "CONCAT('Zona ', re.nr_zona, ' · Seção ', re.nr_secao)",
                "re.nr_secao",
                "MAX(COALESCE(m.nome, re.nm_municipio)) AS municipio, re.nr_zona AS zona, "
                "COALESCE(MAX(lv.nome), MAX(re.nm_local_votacao))"
                " AS local_votacao, re.nr_secao AS secao",
            ),
        }
        label_expr, group_expr, extra = expressions[dimension]
        where, values = self._filters(filters, scope)
        values["limit"] = page_size
        values["offset"] = (page - 1) * page_size
        group_by = {
            "municipio": "re.cd_municipio",
            "zona": "re.nr_zona",
            "local": "re.nr_zona, re.nr_local_votacao",
            "secao": "re.nr_zona, re.nr_local_votacao, re.nr_secao",
        }[dimension]
        if by_candidate:
            rows = await self._all(
                f"""
                WITH agregados AS (
                  SELECT {group_expr} AS valor,
                         {label_expr} AS rotulo,
                         {extra},
                         re.nm_votavel AS candidato,
                         SUM(re.qt_votos)::bigint AS votos,
                         SUM(SUM(re.qt_votos)) OVER (
                           PARTITION BY {group_by}
                         )::bigint AS votos_local
                  {BASE_FROM}
                  WHERE {where}
                  GROUP BY {group_by}, re.nm_votavel
                ),
                ranqueados AS (
                  SELECT valor, rotulo, municipio, zona, local_votacao, secao,
                         candidato, votos, votos_local,
                         DENSE_RANK() OVER (
                           ORDER BY votos_local DESC, rotulo, valor
                         ) AS ordem_local
                  FROM agregados
                  WHERE valor IS NOT NULL
                    AND candidato IS NOT NULL
                ),
                com_total AS (
                  SELECT valor, rotulo, municipio, zona, local_votacao, secao,
                         candidato, votos, ordem_local,
                         MAX(ordem_local) OVER ()::int AS total
                  FROM ranqueados
                )
                SELECT valor, rotulo, municipio, zona, local_votacao, secao,
                       candidato, votos, total
                FROM com_total
                WHERE ordem_local > CAST(:offset AS INTEGER)
                  AND ordem_local <= CAST(:offset AS INTEGER) + CAST(:limit AS INTEGER)
                ORDER BY ordem_local, votos DESC, candidato
                """,
                values,
            )
        else:
            rows = await self._all(
                f"""
                WITH agregados AS (
                  SELECT {group_expr} AS valor,
                         {label_expr} AS rotulo,
                         {extra},
                         NULL::text AS candidato,
                         SUM(re.qt_votos)::bigint AS votos
                  {BASE_FROM}
                  WHERE {where}
                  GROUP BY {group_by}
                )
                SELECT valor, rotulo, municipio, zona, local_votacao, secao,
                       candidato, votos, COUNT(*) OVER()::int AS total
                FROM agregados
                WHERE valor IS NOT NULL
                ORDER BY votos DESC, rotulo
                LIMIT CAST(:limit AS INTEGER) OFFSET CAST(:offset AS INTEGER)
                """,
                values,
            )
        total = int(rows[0]["total"]) if rows else 0
        return rows, total

    async def map_points(
        self,
        filters: ResultadoFilters,
        scope: TerritorialScope,
        mode: str,
        *,
        limit: int = 1500,
    ) -> list[dict[str, Any]]:
        where, values = self._filters(filters, scope)
        values["limit"] = limit
        split_by_candidate = bool(filters.votaveis)
        if split_by_candidate:
            candidate_select = "re.nm_votavel AS candidato"
            candidate_agg = "ARRAY[re.nm_votavel] AS candidatos"
            partition = "re.nm_votavel"
            candidate_group = ", re.nm_votavel"
        else:
            candidate_select = "NULL::text AS candidato"
            candidate_agg = (
                "ARRAY_REMOVE(ARRAY_AGG(DISTINCT re.nm_votavel), NULL) AS candidatos"
            )
            partition = "1"
            candidate_group = ""
        if mode == "zona":
            location_select = """
                       re.nr_zona AS zona,
                       NULL::int AS secao,
                       NULL::text AS local_votacao,"""
            group_by = f"re.nr_zona, re.cd_municipio{candidate_group}"
        else:
            location_select = """
                       re.nr_zona AS zona,
                       re.nr_secao AS secao,
                       COALESCE(MAX(lv.nome), MAX(re.nm_local_votacao)) AS local_votacao,"""
            group_by = (
                f"re.cd_municipio, re.nr_zona, re.nr_secao, re.nr_local_votacao"
                f"{candidate_group}"
            )
        return await self._all(
            f"""
            WITH agregados AS (
              SELECT {location_select}
                     COALESCE(MAX(m.nome), MAX(re.nm_municipio)) AS municipio,
                     AVG(COALESCE(lv.latitude, m.latitude)) AS latitude,
                     AVG(COALESCE(lv.longitude, m.longitude)) AS longitude,
                     SUM(re.qt_votos)::bigint AS votos,
                     {candidate_select},
                     {candidate_agg},
                     ROW_NUMBER() OVER (
                       PARTITION BY {partition}
                       ORDER BY SUM(re.qt_votos) DESC
                     ) AS ordem
              {BASE_FROM}
              WHERE {where}
                AND COALESCE(lv.latitude, m.latitude) IS NOT NULL
                AND COALESCE(lv.longitude, m.longitude) IS NOT NULL
              GROUP BY {group_by}
              HAVING SUM(re.qt_votos) > 0
            )
            SELECT zona, secao, local_votacao, municipio, latitude, longitude,
                   votos, candidato, candidatos, ordem
            FROM agregados
            WHERE ordem <= CAST(:limit AS INTEGER)
            ORDER BY votos DESC
            """,
            values,
        )
