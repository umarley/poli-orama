from __future__ import annotations

from typing import Any

from app.auth.access import RequestActor, TerritorialAccess
from app.mod_gestao_eleitoral.repository import GestaoEleitoralRepository, TerritorialScope
from app.mod_gestao_eleitoral.schemas import (
    CandidateOption,
    DistributionItem,
    ElectionOption,
    IndicatorSummary,
    MapPoint,
    MapResponse,
    NamedOption,
    NumericOption,
    PaginatedDistribution,
    PanelResponse,
    RankingItem,
    ResultadoFilters,
)


def with_ranking_gaps(rows: list[dict[str, Any]], total_votes: int) -> list[RankingItem]:
    ranked: list[RankingItem] = []
    previous_votes: int | None = None
    denominator = total_votes or sum(int(row.get("votos") or 0) for row in rows)
    for index, row in enumerate(rows, start=1):
        votes = int(row.get("votos") or 0)
        ranked.append(
            RankingItem(
                posicao=index,
                nm_votavel=str(row["nm_votavel"]),
                nr_votavel=row.get("nr_votavel"),
                partido=row.get("partido"),
                votos=votes,
                percentual=round((votes * 100 / denominator), 2) if denominator else 0.0,
                diferenca_votos=None if previous_votes is None else previous_votes - votes,
            )
        )
        previous_votes = votes
    return ranked


def as_distribution(rows: list[dict[str, Any]], total_votes: int) -> list[DistributionItem]:
    denominator = total_votes or sum(int(row.get("votos") or 0) for row in rows)
    items: list[DistributionItem] = []
    for row in rows:
        votes = int(row.get("votos") or 0)
        valor = row.get("valor")
        rotulo = str(row.get("rotulo") or valor or "—")
        candidato = str(row.get("candidato") or "").strip() or None
        chave = str(valor) if valor is not None else rotulo
        if candidato:
            chave = f"{chave}:{candidato}"
        items.append(
            DistributionItem(
                chave=chave,
                rotulo=rotulo,
                municipio=row.get("municipio"),
                zona=row.get("zona"),
                local_votacao=row.get("local_votacao"),
                secao=row.get("secao"),
                candidato=candidato,
                votos=votes,
                percentual=round((votes * 100 / denominator), 2) if denominator else 0.0,
            )
        )
    return items


class GestaoEleitoralService:
    def __init__(self, repository: GestaoEleitoralRepository) -> None:
        self.repository = repository

    async def territorial_scope(
        self, actor: RequestActor, access: TerritorialAccess
    ) -> TerritorialScope:
        if access.unrestricted:
            return TerritorialScope(unrestricted=True)
        estado_ids: list[int] = []
        municipios: list[int] = []
        zonas: list[int] = []
        secoes: list[int] = []
        bairro_ids: list[int] = []
        territorio_ids: list[int] = []
        for scope_type, scope_id, _ in access.scopes:
            if scope_type == "global":
                return TerritorialScope(unrestricted=True)
            if scope_id is None:
                continue
            if scope_type == "estado":
                estado_ids.append(int(scope_id))
            elif scope_type == "municipio":
                municipios.append(int(scope_id))
            elif scope_type == "zona_eleitoral":
                zonas.append(int(scope_id))
            elif scope_type == "secao_eleitoral":
                secoes.append(int(scope_id))
            elif scope_type == "bairro":
                bairro_ids.append(int(scope_id))
            elif scope_type == "territorio":
                territorio_ids.append(int(scope_id))
        extra_ufs, extra_municipios = await self.repository.resolve_scope_references(
            estado_ids, bairro_ids, territorio_ids, actor.tenant_id
        )
        return TerritorialScope(
            unrestricted=False,
            ufs=extra_ufs,
            municipios_ibge=sorted(set(municipios + extra_municipios)),
            zonas_ids=zonas,
            secoes_ids=secoes,
        )

    async def list_elections(
        self, actor: RequestActor, access: TerritorialAccess
    ) -> list[ElectionOption]:
        scope = await self.territorial_scope(actor, access)
        rows = await self.repository.list_elections(scope)
        options: list[ElectionOption] = []
        for row in rows:
            year = row.get("aa_eleicao")
            code = row.get("cd_eleicao")
            turn = row.get("nr_turno")
            options.append(
                ElectionOption(
                    aa_eleicao=year,
                    cd_eleicao=code,
                    nr_turno=turn,
                    ds_eleicao=row.get("ds_eleicao"),
                    nm_tipo_eleicao=row.get("nm_tipo_eleicao"),
                    dt_eleicao=row.get("dt_eleicao"),
                    chave=f"{year or ''}:{code or ''}:{turn or ''}",
                )
            )
        return options

    async def search_candidates(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        filters: ResultadoFilters,
        query: str,
    ) -> list[CandidateOption]:
        scope = await self.territorial_scope(actor, access)
        rows = await self.repository.search_candidates(filters, scope, query, 40)
        return [
            CandidateOption(
                nm_votavel=str(row["nm_votavel"]),
                nr_votavel=row.get("nr_votavel"),
                ds_cargo=row.get("ds_cargo"),
            )
            for row in rows
            if row.get("nm_votavel")
        ]

    async def list_named_options(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        filters: ResultadoFilters,
        kind: str,
    ) -> list[NamedOption] | list[NumericOption]:
        scope = await self.territorial_scope(actor, access)
        loaders = {
            "estados": self.repository.list_states,
            "municipios": self.repository.list_municipalities,
            "cargos": self.repository.list_offices,
            "zonas": self.repository.list_zones,
            "locais": self.repository.list_polling_places,
            "secoes": self.repository.list_sections,
        }
        rows = await loaders[kind](filters, scope)
        if kind in {"estados", "cargos"}:
            return [
                NamedOption(valor=str(row["valor"]), rotulo=str(row["rotulo"]))
                for row in rows
                if row.get("valor") is not None
            ]
        return [
            NumericOption(valor=int(row["valor"]), rotulo=str(row["rotulo"]))
            for row in rows
            if row.get("valor") is not None
        ]

    async def panel(
        self, actor: RequestActor, access: TerritorialAccess, filters: ResultadoFilters
    ) -> PanelResponse:
        scope = await self.territorial_scope(actor, access)
        indicators = await self.repository.indicators(filters, scope)
        total_votes = int(indicators.get("total_votos") or 0)
        ranking_rows = (
            await self.repository.ranking(filters, scope) if filters.cargos else []
        )
        comparison_rows = await self.repository.comparison(filters, scope)
        by_candidate = len(filters.votaveis) > 1
        municipio_rows, _ = await self.repository.distribution(
            filters, scope, "municipio", page=1, page_size=12, by_candidate=by_candidate
        )
        zona_rows, _ = await self.repository.distribution(
            filters, scope, "zona", page=1, page_size=12, by_candidate=by_candidate
        )
        local_rows, _ = await self.repository.distribution(
            filters, scope, "local", page=1, page_size=12, by_candidate=by_candidate
        )
        secao_rows, _ = await self.repository.distribution(
            filters, scope, "secao", page=1, page_size=12, by_candidate=by_candidate
        )
        ranking_total = sum(int(row.get("votos") or 0) for row in ranking_rows) or total_votes
        return PanelResponse(
            indicadores=IndicatorSummary(
                total_votos=total_votes,
                candidatos=int(indicators.get("candidatos") or 0),
                municipios=int(indicators.get("municipios") or 0),
                zonas=int(indicators.get("zonas") or 0),
                locais=int(indicators.get("locais") or 0),
                secoes=int(indicators.get("secoes") or 0),
            ),
            ranking=with_ranking_gaps(ranking_rows, ranking_total),
            comparativo=with_ranking_gaps(comparison_rows, total_votes),
            por_municipio=as_distribution(municipio_rows, total_votes),
            por_zona=as_distribution(zona_rows, total_votes),
            por_local=as_distribution(local_rows, total_votes),
            por_secao=as_distribution(secao_rows, total_votes),
        )

    async def map_points(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        filters: ResultadoFilters,
        mode: str,
    ) -> MapResponse:
        scope = await self.territorial_scope(actor, access)
        limit = 1500
        rows = await self.repository.map_points(filters, scope, mode, limit=limit)
        totals: dict[str, int] = {}
        for row in rows:
            key = str(row.get("candidato") or "")
            totals[key] = totals.get(key, 0) + int(row.get("votos") or 0)
        points: list[MapPoint] = []
        for row in rows:
            latitude = row.get("latitude")
            longitude = row.get("longitude")
            if latitude is None or longitude is None:
                continue
            votes = int(row.get("votos") or 0)
            candidate = str(row.get("candidato") or "").strip() or None
            candidates = [
                str(name) for name in (row.get("candidatos") or []) if name
            ]
            if candidate and candidate not in candidates:
                candidates = [candidate, *candidates]
            series_total = totals.get(candidate or "", 0)
            points.append(
                MapPoint(
                    latitude=float(latitude),
                    longitude=float(longitude),
                    zona=row.get("zona"),
                    secao=row.get("secao"),
                    local_votacao=row.get("local_votacao"),
                    municipio=row.get("municipio"),
                    votos=votes,
                    percentual=(
                        round((votes * 100 / series_total), 2) if series_total else 0.0
                    ),
                    candidato=candidate,
                    candidatos=candidates,
                )
            )
        return MapResponse(
            modo="zona" if mode == "zona" else "secao",
            pontos=points,
            truncado=any(int(row.get("ordem") or 0) >= limit for row in rows),
        )

    async def paginated_distribution(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        filters: ResultadoFilters,
        dimension: str,
        page: int,
        page_size: int,
    ) -> PaginatedDistribution:
        scope = await self.territorial_scope(actor, access)
        rows, total = await self.repository.distribution(
            filters, scope, dimension, page=page, page_size=page_size
        )
        indicators = await self.repository.indicators(filters, scope)
        total_votes = int(indicators.get("total_votos") or 0)
        return PaginatedDistribution(
            items=as_distribution(rows, total_votes),
            total=total,
            page=page,
            page_size=page_size,
        )
