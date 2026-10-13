from __future__ import annotations

import csv
import hashlib
import io
import json
from collections.abc import Awaitable, Callable
from datetime import date
from typing import Any

from fastapi.encoders import jsonable_encoder
from openpyxl import Workbook

from app.audit.service import AuditService
from app.auth.access import RequestActor, TerritorialAccess
from app.core.cache import AsyncCache
from app.core.errors import BusinessRuleError
from app.mod_gestao_eleitoral.repository import GestaoEleitoralRepository, TerritorialScope
from app.mod_gestao_eleitoral.schemas import (
    CandidateOption,
    DistributionItem,
    ElectionOption,
    ElectoralZoneCandidateVotes,
    ElectoralZoneResult,
    IndicatorSummary,
    MapExportRequest,
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
    def __init__(
        self, repository: GestaoEleitoralRepository, cache: AsyncCache | None = None
    ) -> None:
        self.repository = repository
        self.cache = cache

    async def _cache_key(
        self,
        endpoint: str,
        actor: RequestActor,
        filters: ResultadoFilters,
        scope: TerritorialScope,
        **options: Any,
    ) -> str:
        generation = await self.repository.rollup_generation_fingerprint(filters)
        payload = {
            "endpoint": endpoint,
            "tenant": actor.tenant_id,
            "filters": {
                key: sorted(value) if isinstance(value, list) else value
                for key, value in filters.model_dump().items()
            },
            "scope": {
                "unrestricted": scope.unrestricted,
                "ufs": sorted(scope.ufs),
                "municipios": sorted(scope.municipios_ibge),
                "zonas": sorted(scope.zonas_ids),
                "secoes": sorted(scope.secoes_ids),
            },
            "generation": generation,
            "options": options,
        }
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return f"gestao-eleitoral:{endpoint}:{digest}"

    async def _cached(
        self,
        endpoint: str,
        actor: RequestActor,
        filters: ResultadoFilters,
        scope: TerritorialScope,
        producer: Callable[[], Awaitable[Any]],
        **options: Any,
    ) -> Any:
        if self.cache is None:
            return await producer()
        producer_failed = False

        async def tracked_producer() -> Any:
            nonlocal producer_failed
            try:
                return await producer()
            except Exception:
                producer_failed = True
                raise

        try:
            key = await self._cache_key(endpoint, actor, filters, scope, **options)
            return await self.cache.get_or_set(key, tracked_producer)
        except Exception:
            if producer_failed:
                raise
            return await producer()

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
        filters = ResultadoFilters()

        async def load() -> list[dict[str, Any]]:
            rows = await self.repository.list_elections(scope)
            return [
                ElectionOption(
                    aa_eleicao=row.get("aa_eleicao"),
                    cd_eleicao=row.get("cd_eleicao"),
                    nr_turno=row.get("nr_turno"),
                    ds_eleicao=row.get("ds_eleicao"),
                    nm_tipo_eleicao=row.get("nm_tipo_eleicao"),
                    dt_eleicao=row.get("dt_eleicao"),
                    chave=(
                        f"{row.get('aa_eleicao') or ''}:{row.get('cd_eleicao') or ''}:"
                        f"{row.get('nr_turno') or ''}"
                    ),
                ).model_dump(mode="json")
                for row in rows
            ]

        data = await self._cached("filtros-eleicoes", actor, filters, scope, load)
        return [ElectionOption.model_validate(item) for item in data]

    async def search_candidates(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        filters: ResultadoFilters,
        query: str,
    ) -> list[CandidateOption]:
        scope = await self.territorial_scope(actor, access)

        async def load() -> list[dict[str, Any]]:
            rows = await self.repository.search_candidates(filters, scope, query, 40)
            return [
                CandidateOption(
                    nm_votavel=str(row["nm_votavel"]),
                    nr_votavel=row.get("nr_votavel"),
                    ds_cargo=row.get("ds_cargo"),
                ).model_dump(mode="json")
                for row in rows
                if row.get("nm_votavel")
            ]

        data = await self._cached(
            "filtros-candidatos", actor, filters, scope, load, query=query.strip().casefold()
        )
        return [CandidateOption.model_validate(item) for item in data]

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
        async def load() -> list[dict[str, Any]]:
            return await loaders[kind](filters, scope)

        rows = await self._cached(f"filtros-{kind}", actor, filters, scope, load)
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
        indicator_summary = await self._indicator_summary(actor, filters, scope)
        ranking_items = (
            await self._ranking_items(actor, filters, scope, limit=80) if filters.cargos else []
        )
        comparison_items = await self._comparison_items(actor, filters, scope)
        by_candidate = len(filters.votaveis) > 1
        distributions = [
            await self._distribution(
                actor,
                filters,
                scope,
                dimension,
                page=1,
                page_size=12,
                by_candidate=by_candidate,
            )
            for dimension in ("municipio", "zona", "local", "secao")
        ]
        return PanelResponse(
            indicadores=indicator_summary,
            ranking=ranking_items,
            comparativo=comparison_items,
            por_municipio=distributions[0].items,
            por_zona=distributions[1].items,
            por_local=distributions[2].items,
            por_secao=distributions[3].items,
        )

    async def indicators(
        self, actor: RequestActor, access: TerritorialAccess, filters: ResultadoFilters
    ) -> IndicatorSummary:
        scope = await self.territorial_scope(actor, access)
        return await self._indicator_summary(actor, filters, scope)

    async def _indicator_summary(
        self, actor: RequestActor, filters: ResultadoFilters, scope: TerritorialScope
    ) -> IndicatorSummary:
        async def load() -> dict[str, Any]:
            row = await self.repository.indicators(filters, scope)
            return IndicatorSummary(
                total_votos=int(row.get("total_votos") or 0),
                candidatos=int(row.get("candidatos") or 0),
                municipios=int(row.get("municipios") or 0),
                zonas=int(row.get("zonas") or 0),
                locais=int(row.get("locais") or 0),
                secoes=int(row.get("secoes") or 0),
            ).model_dump(mode="json")

        data = await self._cached("indicadores", actor, filters, scope, load)
        return IndicatorSummary.model_validate(data)

    async def ranking(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        filters: ResultadoFilters,
        *,
        limit: int = 80,
    ) -> list[RankingItem]:
        scope = await self.territorial_scope(actor, access)
        return await self._ranking_items(actor, filters, scope, limit=limit)

    async def _ranking_items(
        self,
        actor: RequestActor,
        filters: ResultadoFilters,
        scope: TerritorialScope,
        *,
        limit: int,
    ) -> list[RankingItem]:
        async def load() -> list[dict[str, Any]]:
            rows = await self.repository.ranking(filters, scope, limit=limit)
            indicators = await self.repository.indicators(filters, scope)
            total = int(indicators.get("total_votos") or 0)
            return [item.model_dump(mode="json") for item in with_ranking_gaps(rows, total)]

        data = await self._cached("ranking", actor, filters, scope, load, limit=limit)
        return [RankingItem.model_validate(item) for item in data]

    async def comparison(
        self, actor: RequestActor, access: TerritorialAccess, filters: ResultadoFilters
    ) -> list[RankingItem]:
        scope = await self.territorial_scope(actor, access)
        return await self._comparison_items(actor, filters, scope)

    async def _comparison_items(
        self, actor: RequestActor, filters: ResultadoFilters, scope: TerritorialScope
    ) -> list[RankingItem]:
        async def load() -> list[dict[str, Any]]:
            rows = await self.repository.comparison(filters, scope)
            indicators = await self.repository.indicators(filters, scope)
            total = int(indicators.get("total_votos") or 0)
            return [item.model_dump(mode="json") for item in with_ranking_gaps(rows, total)]

        data = await self._cached("comparativo", actor, filters, scope, load)
        return [RankingItem.model_validate(item) for item in data]

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
            candidates = [str(name) for name in (row.get("candidatos") or []) if name]
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
                    percentual=(round((votes * 100 / series_total), 2) if series_total else 0.0),
                    candidato=candidate,
                    candidatos=candidates,
                )
            )
        return MapResponse(
            modo="zona" if mode == "zona" else "secao",
            pontos=points,
            truncado=any(int(row.get("ordem") or 0) >= limit for row in rows),
        )

    async def export_map(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        payload: MapExportRequest,
    ) -> tuple[bytes, str, str]:
        scope = await self.territorial_scope(actor, access)
        rows = await self.repository.export_map_rows(payload.filtros, scope, payload.modo)
        columns = list(rows[0]) if rows else self._map_export_columns(payload.modo)
        if payload.formato == "xlsx":
            content = self._xlsx(columns, rows)
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            content = self._csv(columns, rows)
            media_type = "text/csv; charset=utf-8"
        await AuditService(self.repository.session).record_export(
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            entity="gestao_eleitoral_mapa",
            filters=jsonable_encoder(
                {"modo": payload.modo, **payload.filtros.model_dump(exclude_none=True)}
            ),
            record_count=len(rows),
            file_format=payload.formato,
            purpose="Exportação da análise eleitoral no mapa",
        )
        await self.repository.commit()
        filename = f"analise-eleitoral-mapa-{date.today().isoformat()}.{payload.formato}"
        return content, media_type, filename

    @staticmethod
    def _map_export_columns(mode: str) -> list[str]:
        columns = [
            "Eleição",
            "Ano",
            "Turno",
            "Cargo",
            "Candidato",
            "Número do candidato",
            "UF",
            "Município",
            "Zona eleitoral",
        ]
        if mode != "zona":
            columns.extend(["Local de votação", "Seção eleitoral"])
        return [*columns, "Quantidade de votos", "Latitude", "Longitude"]

    @staticmethod
    def _csv(columns: list[str], rows: list[dict[str, Any]]) -> bytes:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue().encode("utf-8-sig")

    @staticmethod
    def _xlsx(columns: list[str], rows: list[dict[str, Any]]) -> bytes:
        workbook = Workbook(write_only=True)
        sheet = workbook.create_sheet("Análise eleitoral")
        sheet.append(columns)
        for row in rows:
            sheet.append([row.get(column) for column in columns])
        output = io.BytesIO()
        workbook.save(output)
        return output.getvalue()

    async def electoral_zone_meshes(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        filters: ResultadoFilters,
        *,
        south: float,
        west: float,
        north: float,
        east: float,
        limit: int,
    ) -> list[dict[str, Any]]:
        if south >= north or west >= east:
            raise BusinessRuleError("Os limites geograficos informados sao invalidos.")
        scope = await self.territorial_scope(actor, access)
        return await self.repository.electoral_zone_meshes(
            filters,
            scope,
            south=south,
            west=west,
            north=north,
            east=east,
            limit=limit,
        )

    async def electoral_zone_results(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        filters: ResultadoFilters,
    ) -> list[ElectoralZoneResult]:
        scope = await self.territorial_scope(actor, access)
        rows = await self.repository.electoral_zone_results(filters, scope)
        grouped: dict[int, dict[str, Any]] = {}
        for row in rows:
            zone_id = int(row["id"])
            item = grouped.setdefault(
                zone_id,
                {
                    "id": zone_id,
                    "numero_zona": int(row["numero_zona"]),
                    "municipio": row.get("municipio"),
                    "quantidade_locais": int(row.get("quantidade_locais") or 0),
                    "quantidade_secoes": int(row.get("quantidade_secoes") or 0),
                    "total_votos": 0,
                    "candidatos": [],
                },
            )
            votes = int(row.get("votos") or 0)
            item["total_votos"] += votes
            item["candidatos"].append(
                ElectoralZoneCandidateVotes(candidato=str(row["candidato"]), votos=votes)
            )
        return [ElectoralZoneResult.model_validate(item) for item in grouped.values()]

    async def paginated_distribution(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        filters: ResultadoFilters,
        dimension: str,
        page: int,
        page_size: int,
        *,
        by_candidate: bool = False,
    ) -> PaginatedDistribution:
        scope = await self.territorial_scope(actor, access)
        return await self._distribution(
            actor,
            filters,
            scope,
            dimension,
            page=page,
            page_size=page_size,
            by_candidate=by_candidate,
        )

    async def _distribution(
        self,
        actor: RequestActor,
        filters: ResultadoFilters,
        scope: TerritorialScope,
        dimension: str,
        *,
        page: int,
        page_size: int,
        by_candidate: bool,
    ) -> PaginatedDistribution:
        async def load() -> dict[str, Any]:
            result = await self.repository.distribution(
                filters,
                scope,
                dimension,
                page=page,
                page_size=page_size,
                by_candidate=by_candidate,
            )
            # Tuple de dois itens e aceito para repositorios de terceiros/testes
            # anteriores ao total de votos passar a vir na mesma consulta.
            if len(result) == 3:
                rows, total, total_votes = result
            else:
                rows, total = result
                total_votes = sum(int(row.get("votos") or 0) for row in rows)
            return PaginatedDistribution(
                items=as_distribution(rows, total_votes),
                total=total,
                page=page,
                page_size=page_size,
            ).model_dump(mode="json")

        data = await self._cached(
            f"distribuicao-{dimension}",
            actor,
            filters,
            scope,
            load,
            page=page,
            page_size=page_size,
            by_candidate=by_candidate,
        )
        return PaginatedDistribution.model_validate(data)
