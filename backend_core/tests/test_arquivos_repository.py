from unittest.mock import AsyncMock, Mock

import pytest

from app.mod_arquivos.repository import FileRepository


@pytest.mark.asyncio
async def test_anuncio_execution_access_uses_planning_assignment() -> None:
    session = Mock()
    session.scalar = AsyncMock(return_value=True)
    repository = FileRepository(session)

    allowed = await repository.can_access_anuncio_execution(
        tenant_id=7,
        execution_id=41,
        user_id=13,
        person_id=29,
        administrative=False,
    )

    statement, values = session.scalar.await_args.args
    query = str(statement)
    assert allowed is True
    assert "JOIN anuncio.rota_comunicacao_planejamento pl" in query
    assert "pl.id=ex.planejamento_id AND pl.tenant_id=ex.tenant_id" in query
    assert "pl.usuario_responsavel_id=:user_id" in query
    assert "ep.equipe_id=pl.equipe_id" in query
    assert "rota_comunicacao r" not in query
    assert values == {
        "tenant_id": 7,
        "execution_id": 41,
        "administrative": False,
        "user_id": 13,
        "person_id": 29,
    }


@pytest.mark.asyncio
async def test_anuncio_execution_access_uses_impossible_person_without_linked_person() -> None:
    session = Mock()
    session.scalar = AsyncMock(return_value=False)
    repository = FileRepository(session)

    allowed = await repository.can_access_anuncio_execution(
        tenant_id=7,
        execution_id=41,
        user_id=13,
        person_id=None,
        administrative=False,
    )

    _, values = session.scalar.await_args.args
    assert allowed is False
    assert values["person_id"] == -1
