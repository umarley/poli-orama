from datetime import date
from unittest.mock import AsyncMock, Mock

import pytest

from app.auth.access import RequestActor, TerritorialAccess
from app.core.errors import AuthorizationError
from app.mod_dashboard.schemas import DashboardFilters, ExportRequest
from app.mod_dashboard.service import DashboardService


def actor(*permissions: str) -> RequestActor:
    return RequestActor(
        tenant_id=10,
        user_id=20,
        session_id=30,
        profiles=("coordenador_territorial",),
        permissions=frozenset(permissions),
        token="test",
    )


def filters(territory_id: int | None = None) -> DashboardFilters:
    return DashboardFilters(
        data_inicio=date(2026, 6, 1),
        data_fim=date(2026, 6, 30),
        territorio_id=territory_id,
    )


@pytest.mark.asyncio
async def test_dashboard_rejects_territory_outside_coordinator_scope() -> None:
    repository = Mock()
    repository.session = Mock()
    service = DashboardService(repository)
    service.territories.accessible_ids = AsyncMock(return_value={100, 101})  # type: ignore[method-assign]

    with pytest.raises(AuthorizationError):
        await service.territory_ids(
            actor("dashboard.visualizar"),
            TerritorialAccess(
                unrestricted=False, scopes=frozenset({("territorio", 100, False)})
            ),
            filters(999),
        )


@pytest.mark.asyncio
async def test_dashboard_export_is_audited_with_filters_and_purpose() -> None:
    repository = Mock()
    repository.session = Mock()
    repository.goals_by_leader = AsyncMock(
        return_value=[
            {
                "lideranca_id": 1,
                "lider": "Lider A",
                "meta": 100,
                "atual": 80,
                "percentual": 80.0,
                "risco": "normal",
            }
        ]
    )
    repository.add_export_log = AsyncMock()
    repository.commit = AsyncMock()
    service = DashboardService(repository)
    service.territories.accessible_ids = AsyncMock(return_value=None)  # type: ignore[method-assign]
    payload = ExportRequest(
        relatorio="metas",
        formato="csv",
        finalidade="Reuniao da coordenacao",
        filtros=filters(),
    )

    content, media_type, filename = await service.export(
        payload,
        actor("dashboard.visualizar", "dashboard.exportar"),
        TerritorialAccess(unrestricted=True, scopes=frozenset()),
    )

    assert content.startswith(b"\xef\xbb\xbf")
    assert media_type.startswith("text/csv")
    assert filename == "relatorio-metas.csv"
    repository.add_export_log.assert_awaited_once()
    logged = repository.add_export_log.await_args.args
    assert logged[0:3] == (10, 20, "metas")
    assert logged[4:] == (1, "csv", "Reuniao da coordenacao")
    repository.commit.assert_awaited_once()
