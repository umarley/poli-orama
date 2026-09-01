from datetime import date
from unittest.mock import AsyncMock, Mock

import pytest

from app.mod_agenda.access import calendar_view_clause
from app.mod_dashboard.repository import DashboardRepository
from app.mod_dashboard.schemas import DashboardFilters


@pytest.mark.asyncio
async def test_commemorative_dates_casts_date_parameters_in_raw_sql() -> None:
    result = Mock()
    result.mappings.return_value = []
    session = Mock()
    session.execute = AsyncMock(return_value=result)
    repository = DashboardRepository(session)
    filters = DashboardFilters(
        data_inicio=date(2026, 7, 2),
        data_fim=date(2026, 7, 31),
    )

    await repository.commemorative_dates(filters, None, date(2026, 7, 31))

    statement, values = session.execute.await_args.args
    query = str(statement)
    assert "EXTRACT(YEAR FROM CAST(:today AS DATE))" in query
    assert "data_base<CAST(:today AS DATE)" in query
    assert "BETWEEN CAST(:today AS DATE) AND CAST(:end AS DATE)" in query
    assert values["today"] == date(2026, 7, 31)
    assert values["end"] == date(2026, 8, 30)


@pytest.mark.asyncio
async def test_event_dashboard_uses_the_central_calendar_visibility_rule() -> None:
    mappings = Mock()
    mappings.one.return_value = {"total_periodo": 0}
    result = Mock()
    result.mappings.return_value = mappings
    session = Mock()
    session.execute = AsyncMock(return_value=result)
    repository = DashboardRepository(session)

    await repository.eventos(
        tenant_id=7,
        filters=DashboardFilters(data_inicio=date(2026, 7, 1), data_fim=date(2026, 7, 31)),
        territory_ids=None,
        user_id=9,
        calendar_administrator=False,
    )

    statement, values = session.execute.await_args.args
    query = str(statement)
    assert calendar_view_clause() in query
    assert "criado_por" not in query
    assert values["user_id"] == 9
