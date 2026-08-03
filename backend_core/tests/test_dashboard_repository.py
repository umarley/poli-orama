from datetime import date
from unittest.mock import AsyncMock, Mock

import pytest

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
