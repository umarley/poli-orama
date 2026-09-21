from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.auth.access import RequestActor, TerritorialAccess
from app.core.errors import BusinessRuleError
from app.mod_agenda.schemas import EventInput, PublicAttendanceInput
from app.mod_agenda.service import AgendaService


def authenticated_actor() -> RequestActor:
    return RequestActor(
        tenant_id=7,
        user_id=9,
        session_id=3,
        profiles=("usuario",),
        permissions=frozenset({"agenda.visualizar"}),
        token="token",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("active_campaign_id", [44, None])
async def test_event_creation_always_uses_the_active_campaign(
    active_campaign_id: int | None,
) -> None:
    repository = SimpleNamespace(
        session=AsyncMock(),
        active_campaign_id=AsyncMock(return_value=active_campaign_id),
        create_event=AsyncMock(return_value=30),
        get_event=AsyncMock(return_value={"id": 30}),
        commit=AsyncMock(),
    )
    service = AgendaService(repository)  # type: ignore[arg-type]
    service.ensure_calendar = AsyncMock()  # type: ignore[method-assign]
    service._validate_event_references = AsyncMock()  # type: ignore[method-assign]
    service._audit = AsyncMock()  # type: ignore[method-assign]
    payload = EventInput(
        agenda_id=12,
        campanha_eleicao_id=999,
        titulo="Compromisso",
        data_inicio=datetime(2026, 9, 22, 13, 0, tzinfo=UTC),
        responsavel_pessoa_id=20,
    )

    with patch("app.mod_agenda.service.EventResponse.model_validate", return_value="event"):
        result = await service.create_event(
            authenticated_actor(),
            TerritorialAccess(unrestricted=True, scopes=frozenset()),
            payload,
        )

    saved_payload = repository.create_event.await_args.args[2]
    assert saved_payload.agenda_id == 12
    assert saved_payload.campanha_eleicao_id == active_campaign_id
    assert result == "event"
    repository.active_campaign_id.assert_awaited_once_with(7)
    repository.commit.assert_awaited_once()


class PublicAttendanceRepositoryStub:
    def __init__(self, event: dict[str, object], *, person_id: int | None = None) -> None:
        self.session = SimpleNamespace()
        self.event = event
        self.person_id = person_id
        self.existing_presence: bool | None = None
        self.created = False
        self.complemented = False
        self.confirmed: bool | None = None
        self.committed = False

    async def get_public_event(self, public_id: object):
        return self.event

    async def set_tenant_context(self, tenant_id: int) -> None:
        assert tenant_id == 7

    async def lock_public_attendance_identity(self, *args: object) -> None:
        return None

    async def find_public_attendance_person(self, *args: object):
        return self.person_id

    async def create_public_attendance_person(self, *args: object) -> int:
        self.created = True
        return 91

    async def complement_public_attendance_person(self, *args: object) -> None:
        self.complemented = True

    async def public_participation(self, *args: object):
        return self.existing_presence

    async def upsert_public_participation(
        self, tenant_id: int, event_id: int, person_id: int, *, confirmed: bool
    ) -> None:
        assert (tenant_id, event_id, person_id) == (7, 30, self.person_id or 91)
        self.confirmed = confirmed

    async def commit(self) -> None:
        self.committed = True


def event_during_window() -> dict[str, object]:
    now = datetime.now(UTC)
    return {
        "id": 30,
        "uuid_publico": uuid4(),
        "tenant_id": 7,
        "titulo": "Encontro comunitario",
        "data_inicio": now - timedelta(minutes=5),
        "data_fim": now + timedelta(hours=1),
        "local_nome": "Centro comunitario",
    }


def payload() -> PublicAttendanceInput:
    return PublicAttendanceInput(
        nome_completo="Maria da Silva",
        celular="(62) 99999-1234",
        email="maria@example.com",
        data_nascimento="1990-05-20",
    )


@pytest.mark.asyncio
async def test_exposes_public_event_without_internal_identifiers() -> None:
    repository = PublicAttendanceRepositoryStub(event_during_window())
    service = AgendaService(repository)  # type: ignore[arg-type]

    response = await service.public_event(uuid4())

    assert response.titulo == "Encontro comunitario"
    assert response.confirmacao_aberta
    assert "id" not in response.model_dump()
    assert "tenant_id" not in response.model_dump()


@pytest.mark.asyncio
async def test_creates_person_and_confirms_attendance_inside_window() -> None:
    repository = PublicAttendanceRepositoryStub(event_during_window())
    service = AgendaService(repository)  # type: ignore[arg-type]

    response = await service.confirm_public_attendance(uuid4(), payload())

    assert response.status == "confirmada"
    assert repository.created
    assert repository.confirmed is True
    assert repository.committed


@pytest.mark.asyncio
async def test_complements_existing_person_without_duplicate_participation() -> None:
    repository = PublicAttendanceRepositoryStub(event_during_window(), person_id=44)
    repository.existing_presence = True
    service = AgendaService(repository)  # type: ignore[arg-type]

    response = await service.confirm_public_attendance(uuid4(), payload())

    assert response.status == "ja_confirmada"
    assert repository.complemented
    assert repository.confirmed is None
    assert repository.committed


@pytest.mark.asyncio
async def test_saves_person_but_does_not_confirm_outside_window() -> None:
    event = event_during_window()
    event["data_inicio"] = datetime.now(UTC) - timedelta(hours=4)
    event["data_fim"] = datetime.now(UTC) - timedelta(hours=3)
    repository = PublicAttendanceRepositoryStub(event)
    service = AgendaService(repository)  # type: ignore[arg-type]

    response = await service.confirm_public_attendance(uuid4(), payload())

    assert response.status == "fora_do_periodo"
    assert repository.created
    assert repository.confirmed is False


@pytest.mark.asyncio
async def test_rejects_invalid_phone_without_creating_person() -> None:
    repository = PublicAttendanceRepositoryStub(event_during_window())
    service = AgendaService(repository)  # type: ignore[arg-type]

    with pytest.raises(BusinessRuleError) as error:
        await service.confirm_public_attendance(
            uuid4(),
            PublicAttendanceInput(nome_completo="Maria da Silva", celular="sem-telefone"),
        )

    assert error.value.code == "invalid_phone"
    assert not repository.created
