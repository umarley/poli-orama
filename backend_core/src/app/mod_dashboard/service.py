import csv
import io
from datetime import UTC, date, datetime
from threading import Lock
from time import monotonic
from typing import Any

from fastapi.encoders import jsonable_encoder
from openpyxl import Workbook

from app.auth.access import RequestActor, TerritorialAccess
from app.core.errors import AuthorizationError
from app.mod_dashboard.repository import DashboardRepository
from app.mod_dashboard.schemas import DashboardFilters, ExportRequest
from app.mod_territorio.repository import TerritorioRepository


class DashboardCache:
    _values: dict[tuple[Any, ...], tuple[float, dict[str, Any]]] = {}
    _lock = Lock()
    ttl_seconds = 30

    @classmethod
    def get(cls, key: tuple[Any, ...]) -> dict[str, Any] | None:
        with cls._lock:
            item = cls._values.get(key)
            if item is None:
                return None
            created, value = item
            if monotonic() - created > cls.ttl_seconds:
                cls._values.pop(key, None)
                return None
            return value

    @classmethod
    def set(cls, key: tuple[Any, ...], value: dict[str, Any]) -> None:
        with cls._lock:
            cls._values[key] = (monotonic(), value)
            if len(cls._values) > 500:
                oldest = min(cls._values, key=lambda current: cls._values[current][0])
                cls._values.pop(oldest, None)


class DashboardService:
    default_widgets = [
        "cadastros",
        "liderancas",
        "metas",
        "demandas",
        "eventos",
        "aniversariantes",
        "datas_comemorativas",
    ]

    def __init__(self, repository: DashboardRepository):
        self.repository = repository
        self.territories = TerritorioRepository(repository.session)

    async def territory_ids(
        self, actor: RequestActor, access: TerritorialAccess, filters: DashboardFilters
    ) -> set[int] | None:
        accessible = await self.territories.accessible_ids(actor.tenant_id, access)
        if filters.territorio_id is None:
            return accessible
        if accessible is not None and filters.territorio_id not in accessible:
            raise AuthorizationError("Territorio fora do escopo permitido.")
        return {filters.territorio_id}

    async def overview(
        self, actor: RequestActor, access: TerritorialAccess, filters: DashboardFilters
    ) -> dict[str, Any]:
        territory_ids = await self.territory_ids(actor, access, filters)
        key = (
            actor.tenant_id,
            actor.user_id,
            filters.data_inicio,
            filters.data_fim,
            filters.territorio_id,
            filters.lideranca_id,
            tuple(sorted(territory_ids)) if territory_ids is not None else None,
        )
        cached = DashboardCache.get(key)
        if cached is not None:
            return cached
        agenda_territory_ids = (
            {filters.territorio_id} if filters.territorio_id is not None else None
        )
        value = {
            "filtros": filters.model_dump(),
            "cadastros": await self.repository.cadastros(
                actor.tenant_id, filters, territory_ids
            ),
            "liderancas": await self.repository.liderancas(
                actor.tenant_id, filters, territory_ids
            ),
            "metas": await self.repository.metas(actor.tenant_id, filters, territory_ids),
            "demandas": await self.repository.demandas(
                actor.tenant_id, filters, territory_ids
            ),
            "eventos": await self.repository.eventos(
                actor.tenant_id,
                filters,
                agenda_territory_ids,
                actor.user_id,
                "agenda.administrar" in actor.permissions,
            ),
            "gerado_em": datetime.now(UTC),
        }
        DashboardCache.set(key, value)
        return value

    async def birthdays(
        self, actor: RequestActor, access: TerritorialAccess, filters: DashboardFilters
    ) -> dict[str, Any]:
        rows = await self.repository.birthdays(
            actor.tenant_id, filters, await self.territory_ids(actor, access, filters)
        )
        if "cadastro.visualizar" not in actor.permissions:
            for row in rows:
                parts = row["nome"].split()
                row["nome"] = " ".join([parts[0], *(f"{part[0]}." for part in parts[1:])])
        today = date.today()
        return {
            "hoje": [
                row
                for row in rows
                if row["data_nascimento"].month == today.month
                and row["data_nascimento"].day == today.day
            ],
            "mes": [row for row in rows if row["data_nascimento"].month == today.month],
        }

    async def commemorative_dates(
        self, actor: RequestActor, access: TerritorialAccess, filters: DashboardFilters
    ) -> list[dict[str, Any]]:
        return await self.repository.commemorative_dates(
            filters, await self.territory_ids(actor, access, filters), date.today()
        )

    async def report(
        self,
        report_type: str,
        actor: RequestActor,
        access: TerritorialAccess,
        filters: DashboardFilters,
    ) -> list[dict[str, Any]]:
        territory_ids = await self.territory_ids(actor, access, filters)
        methods = {
            "metas": self.repository.goals_by_leader,
            "demandas": self.repository.demands_report,
            "agenda": self.repository.agenda_report,
            "cadastros": self.repository.registrations_evolution,
            "lideres": self.repository.leader_ranking,
        }
        if report_type == "agenda":
            agenda_territory_ids = (
                {filters.territorio_id} if filters.territorio_id is not None else None
            )
            return await self.repository.agenda_report(
                actor.tenant_id,
                filters,
                agenda_territory_ids,
                actor.user_id,
                "agenda.administrar" in actor.permissions,
            )
        return await methods[report_type](actor.tenant_id, filters, territory_ids)

    async def export(
        self, payload: ExportRequest, actor: RequestActor, access: TerritorialAccess
    ) -> tuple[bytes, str, str]:
        rows = await self.report(payload.relatorio, actor, access, payload.filtros)
        columns = list(rows[0]) if rows else self._empty_columns(payload.relatorio)
        if payload.formato == "xlsx":
            content = self._xlsx(columns, rows)
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            content = self._csv(columns, rows)
            media_type = "text/csv; charset=utf-8"
        await self.repository.add_export_log(
            actor.tenant_id,
            actor.user_id,
            payload.relatorio,
            jsonable_encoder(payload.filtros.model_dump()),
            len(rows),
            payload.formato,
            payload.finalidade,
        )
        await self.repository.commit()
        return content, media_type, f"relatorio-{payload.relatorio}.{payload.formato}"

    @staticmethod
    def _empty_columns(report_type: str) -> list[str]:
        return {
            "metas": ["lideranca_id", "lider", "meta", "atual", "percentual", "risco"],
            "demandas": ["status", "categoria", "responsavel", "prazo", "total", "vencidas"],
            "agenda": [
                "evento_id",
                "titulo",
                "data_inicio",
                "data_fim",
                "status",
                "territorio",
                "responsavel",
                "convites",
                "pautas",
            ],
            "cadastros": ["data", "origem", "total"],
            "lideres": [
                "posicao",
                "lideranca_id",
                "lider",
                "liderados",
                "meta",
                "atual",
                "percentual",
            ],
        }[report_type]

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
        sheet = workbook.create_sheet("Relatorio")
        sheet.append(columns)
        for row in rows:
            sheet.append([row.get(column) for column in columns])
        output = io.BytesIO()
        workbook.save(output)
        return output.getvalue()

    async def configuration(self, actor: RequestActor) -> dict[str, Any]:
        value = await self.repository.configuration(actor.tenant_id, actor.profiles)
        if value:
            return value
        return {
            "id": None,
            "nome": "Dashboard principal",
            "perfil": actor.role,
            "filtros_padrao": {"periodo_dias": 30},
            "widgets": self.default_widgets,
        }
