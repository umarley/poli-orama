"""Regras de negocio, escopo territorial e auditoria da agenda."""

import csv
import io
import unicodedata
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy import text

from app.audit.service import AuditService
from app.auth.access import RequestActor, TerritorialAccess
from app.core.errors import AuthorizationError, BusinessRuleError, ResourceNotFoundError
from app.mod_agenda.repository import AgendaRepository
from app.mod_agenda.schemas import (
    AgendaItemInput,
    AgendaSummary,
    AttendanceInput,
    CalendarInput,
    CalendarMemberInput,
    CalendarResponse,
    CalendarUpdate,
    CatalogCreate,
    CatalogUpdate,
    DemandFromEventInput,
    EventDetailResponse,
    EventInput,
    EventResponse,
    EventUpdate,
    InvitationInput,
    LeadershipInput,
    ParticipantInput,
    PublicAttendanceInput,
    PublicAttendanceResponse,
    PublicEventResponse,
)
from app.mod_territorio.repository import TerritorioRepository


class AgendaService:
    def __init__(self, repository: AgendaRepository) -> None:
        self.repository = repository
        self.territories = TerritorioRepository(repository.session)

    async def accessible_ids(
        self, actor: RequestActor, access: TerritorialAccess
    ) -> set[int] | None:
        return await self.territories.accessible_ids(actor.tenant_id, access)

    async def public_event(self, public_id: UUID) -> PublicEventResponse:
        event = await self.repository.get_public_event(public_id)
        if event is None:
            raise ResourceNotFoundError("Evento", public_id)
        return PublicEventResponse(
            uuid_publico=cast(UUID, event["uuid_publico"]),
            titulo=cast(str, event["titulo"]),
            data_inicio=cast(datetime, event["data_inicio"]),
            data_fim=cast(datetime | None, event["data_fim"]),
            local_nome=cast(str | None, event["local_nome"]),
            confirmacao_aberta=self._attendance_window_open(event),
        )

    async def confirm_public_attendance(
        self, public_id: UUID, payload: PublicAttendanceInput
    ) -> PublicAttendanceResponse:
        event = await self.repository.get_public_event(public_id)
        if event is None:
            raise ResourceNotFoundError("Evento", public_id)

        tenant_id = int(event["tenant_id"])
        await self.repository.set_tenant_context(tenant_id)
        phone_digits = self._normalize_phone(payload.celular)
        normalized_name = self._identity_name(payload.nome_completo)
        await self.repository.lock_public_attendance_identity(
            tenant_id, normalized_name, phone_digits
        )
        person_id = await self.repository.find_public_attendance_person(
            tenant_id,
            payload.nome_completo,
            phone_digits,
            payload.email,
            payload.data_nascimento,
        )
        if person_id is None:
            person_id = await self.repository.create_public_attendance_person(
                tenant_id,
                payload.nome_completo,
                phone_digits,
                payload.email,
                payload.data_nascimento,
            )
        else:
            await self.repository.complement_public_attendance_person(
                tenant_id,
                person_id,
                payload.email,
                payload.data_nascimento,
            )

        participation = await self.repository.public_participation(
            tenant_id, int(event["id"]), person_id
        )
        if participation is True:
            await self.repository.commit()
            return PublicAttendanceResponse(
                status="ja_confirmada",
                message="Sua presenca ja se encontra registrada neste evento.",
            )

        confirmation_open = self._attendance_window_open(event)
        await self.repository.upsert_public_participation(
            tenant_id,
            int(event["id"]),
            person_id,
            confirmed=confirmation_open,
        )
        await self.repository.commit()
        if confirmation_open:
            return PublicAttendanceResponse(
                status="confirmada",
                message="Presenca registrada com sucesso.",
            )
        return PublicAttendanceResponse(
            status="fora_do_periodo",
            message=(
                "Seus dados foram gravados com sucesso, mas a presenca nao pode ser "
                "confirmada porque o periodo permitido para este evento esta encerrado."
            ),
        )

    @staticmethod
    def _attendance_window_open(event: dict[str, Any], now: datetime | None = None) -> bool:
        current = now or datetime.now(UTC)
        start = cast(datetime, event["data_inicio"])
        end = cast(datetime | None, event["data_fim"]) or start
        return start - timedelta(minutes=15) <= current <= end + timedelta(hours=1)

    @staticmethod
    def _normalize_phone(value: str) -> str:
        digits = "".join(character for character in value if character.isdigit())
        if digits.startswith("55") and len(digits) in {12, 13}:
            digits = digits[2:]
        if len(digits) not in {10, 11}:
            raise BusinessRuleError(
                "Informe um celular com DDD e 10 ou 11 digitos.",
                code="invalid_phone",
            )
        return digits

    @staticmethod
    def _identity_name(value: str) -> str:
        normalized = unicodedata.normalize("NFKD", " ".join(value.lower().split()))
        return "".join(
            character for character in normalized if not unicodedata.combining(character)
        )

    async def create_catalog(
        self, actor: RequestActor, table: str, payload: CatalogCreate
    ) -> dict[str, Any]:
        item = await self.repository.create_catalog(table, actor.tenant_id, payload)
        await self._audit(actor, "criar", table, item["id"], None, item)
        await self.repository.commit()
        return item

    async def list_calendars(self, actor: RequestActor) -> list[CalendarResponse]:
        administrator = "agenda.administrar" in actor.permissions
        items = await self.repository.list_calendars(
            actor.tenant_id, actor.user_id, administrator=administrator
        )
        if administrator:
            for item in items:
                item["permissoes"] = [
                    "visualizar",
                    "criar",
                    "editar",
                    "alterar_classificacao",
                    "excluir",
                    "administrar_usuarios",
                    "administrar_agenda",
                ]
        else:
            for item in items:
                if item["visibilidade"] == "publica":
                    inherited = {
                        code.removeprefix("agenda.")
                        for code in actor.permissions
                        if code.startswith("agenda.")
                    }
                    item["permissoes"] = sorted(set(item["permissoes"]) | inherited)
        return [CalendarResponse.model_validate(item) for item in items]

    async def create_calendar(
        self, actor: RequestActor, payload: CalendarInput
    ) -> CalendarResponse:
        calendar_id = await self.repository.create_calendar(actor.tenant_id, actor.user_id, payload)
        await self.repository.upsert_calendar_member(
            actor.tenant_id,
            calendar_id,
            actor.user_id,
            CalendarMemberInput(
                usuario_id=actor.user_id,
                pode_visualizar=True,
                pode_criar=True,
                pode_editar=True,
                pode_alterar_classificacao=True,
                pode_excluir=True,
                pode_administrar_usuarios=True,
                pode_administrar_agenda=True,
            ),
        )
        item = await self.repository.get_calendar(actor.tenant_id, calendar_id)
        assert item is not None
        await self._audit(actor, "criar", "agenda", calendar_id, None, item)
        response = next(item for item in await self.list_calendars(actor) if item.id == calendar_id)
        await self.repository.commit()
        return response

    async def update_calendar(
        self, actor: RequestActor, calendar_id: int, payload: CalendarUpdate
    ) -> CalendarResponse:
        current = await self.ensure_calendar(actor, calendar_id, "administrar_agenda")
        classification_fields = {
            "natureza_candidato",
            "frente_comunidade",
            "tipo_agenda",
            "visibilidade",
            "cor",
        }
        if classification_fields & payload.model_fields_set:
            await self.ensure_calendar(actor, calendar_id, "alterar_classificacao")
        await self.repository.update_calendar(actor.tenant_id, calendar_id, payload)
        updated = await self.repository.get_calendar(actor.tenant_id, calendar_id)
        assert updated is not None
        await self._audit(actor, "editar", "agenda", calendar_id, current, updated)
        response = next(item for item in await self.list_calendars(actor) if item.id == calendar_id)
        await self.repository.commit()
        return response

    async def delete_calendar(self, actor: RequestActor, calendar_id: int) -> None:
        current = await self.ensure_calendar(actor, calendar_id, "excluir")
        if current["padrao"]:
            raise BusinessRuleError("A agenda padrao nao pode ser excluida.")
        if not await self.repository.delete_calendar(actor.tenant_id, calendar_id):
            raise BusinessRuleError(
                "Remova ou transfira os compromissos antes de excluir a agenda."
            )
        await self._audit(actor, "excluir", "agenda", calendar_id, current, None)
        await self.repository.commit()

    async def calendar_members(self, actor: RequestActor, calendar_id: int) -> list[dict[str, Any]]:
        await self.ensure_calendar(actor, calendar_id, "administrar_usuarios")
        return await self.repository.calendar_members(actor.tenant_id, calendar_id)

    async def save_calendar_member(
        self, actor: RequestActor, calendar_id: int, payload: CalendarMemberInput
    ) -> list[dict[str, Any]]:
        await self.ensure_calendar(actor, calendar_id, "administrar_usuarios")
        await self._require_reference(actor, "usuario", payload.usuario_id)
        await self.repository.upsert_calendar_member(
            actor.tenant_id, calendar_id, actor.user_id, payload
        )
        await self._audit(
            actor, "editar", "agenda_usuario", calendar_id, None, payload.model_dump()
        )
        members = await self.repository.calendar_members(actor.tenant_id, calendar_id)
        await self.repository.commit()
        return members

    async def remove_calendar_member(
        self, actor: RequestActor, calendar_id: int, user_id: int
    ) -> None:
        await self.ensure_calendar(actor, calendar_id, "administrar_usuarios")
        await self.repository.delete_calendar_member(actor.tenant_id, calendar_id, user_id)
        await self.repository.commit()

    async def ensure_calendar(
        self, actor: RequestActor, calendar_id: int, action: str = "visualizar"
    ) -> dict[str, Any]:
        item = await self.repository.get_calendar(actor.tenant_id, calendar_id)
        if item is None:
            raise ResourceNotFoundError("Agenda", calendar_id)
        if "agenda.administrar" in actor.permissions:
            return item
        permissions = await self.repository.calendar_permissions(
            actor.tenant_id, calendar_id, actor.user_id
        )
        if "administrar_agenda" in permissions or action in permissions:
            return item
        if item["visibilidade"] == "publica":
            if action == "visualizar" or f"agenda.{action}" in actor.permissions:
                return item
        raise AuthorizationError("Usuario nao possui permissao nesta agenda.")

    async def update_catalog(
        self,
        actor: RequestActor,
        table: str,
        item_id: int,
        payload: CatalogUpdate,
    ) -> dict[str, Any]:
        current = await self.repository.get_catalog(table, actor.tenant_id, item_id)
        if current is None:
            raise ResourceNotFoundError("Catalogo de agenda", item_id)
        if current["tenant_id"] is None:
            raise BusinessRuleError("Registros globais nao podem ser alterados.")
        item = await self.repository.update_catalog(table, actor.tenant_id, item_id, payload)
        assert item is not None
        await self._audit(actor, "editar", table, item_id, current, item)
        await self.repository.commit()
        return item

    async def list_events(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        **filters: Any,
    ) -> list[dict[str, Any]]:
        return await self.repository.list_events(
            actor.tenant_id,
            user_id=actor.user_id,
            calendar_administrator="agenda.administrar" in actor.permissions,
            **filters,
        )

    async def create_event(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        payload: EventInput,
    ) -> EventResponse:
        calendar_id = payload.agenda_id or await self.repository.default_calendar_id(
            actor.tenant_id
        )
        if calendar_id is None:
            raise BusinessRuleError("Cadastre uma agenda antes de criar compromissos.")
        await self.ensure_calendar(actor, calendar_id, "criar")
        payload = payload.model_copy(update={"agenda_id": calendar_id})
        await self._validate_event_references(actor, access, payload, administer=True)
        event_id = await self.repository.create_event(actor.tenant_id, actor.user_id, payload)
        item = await self.repository.get_event(actor.tenant_id, event_id)
        assert item is not None
        await self._audit(actor, "criar", "evento", event_id, None, item)
        await self.repository.commit()
        return EventResponse.model_validate(item)

    async def update_event(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        event_id: int,
        payload: EventUpdate,
    ) -> EventResponse:
        current = await self.ensure_event(actor, access, event_id, administer=True)
        if payload.agenda_id is not None and payload.agenda_id != current["agenda_id"]:
            await self.ensure_calendar(actor, payload.agenda_id, "criar")
        schedule_fields = {"data_inicio", "data_fim"}
        if schedule_fields & payload.model_fields_set and not {
            "gestor",
            "gestor_saas",
        }.intersection(actor.profiles):
            raise AuthorizationError(
                "Apenas usuarios com perfil gestor podem alterar a data e o horario do evento."
            )
        await self._validate_event_references(actor, access, payload, administer=True)
        start = payload.data_inicio or current["data_inicio"]
        end = payload.data_fim if "data_fim" in payload.model_fields_set else current["data_fim"]
        if end is not None and end < start:
            raise BusinessRuleError("A data final deve ser posterior ao inicio.")
        await self.repository.update_event(actor.tenant_id, event_id, payload)
        item = await self.repository.get_event(actor.tenant_id, event_id)
        assert item is not None
        await self._audit(actor, "editar", "evento", event_id, current, item)
        await self.repository.commit()
        return EventResponse.model_validate(item)

    async def cancel_event(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        event_id: int,
        reason: str,
    ) -> EventResponse:
        if len(reason.strip()) < 3:
            raise BusinessRuleError("Informe o motivo do cancelamento.")
        current = await self.ensure_event(actor, access, event_id, administer=True)
        if current["status_evento_codigo"] == "cancelado":
            raise BusinessRuleError("Evento ja esta cancelado.")
        await self.repository.cancel_event(actor.tenant_id, event_id, actor.user_id, reason.strip())
        item = await self.repository.get_event(actor.tenant_id, event_id)
        assert item is not None
        await self._audit(actor, "editar", "evento", event_id, current, item)
        await self.repository.commit()
        return EventResponse.model_validate(item)

    async def delete_event(
        self, actor: RequestActor, access: TerritorialAccess, event_id: int
    ) -> None:
        current = await self.ensure_event(actor, access, event_id)
        await self.ensure_calendar(actor, int(current["agenda_id"]), "excluir")
        await self.repository.delete_event(actor.tenant_id, event_id)
        await self._audit(actor, "excluir", "evento", event_id, current, None)
        await self.repository.commit()

    async def detail(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        event_id: int,
    ) -> EventDetailResponse:
        item = await self.ensure_event(actor, access, event_id)
        return EventDetailResponse.model_validate(
            {
                **item,
                "participantes": await self.repository.participants(actor.tenant_id, event_id),
                "liderancas": await self.repository.leaderships(actor.tenant_id, event_id),
                "convites": await self.repository.invitations(actor.tenant_id, event_id),
                "pautas": await self.repository.agenda_items(actor.tenant_id, event_id),
                "presenca": await self.repository.attendance(actor.tenant_id, event_id),
                "demandas": await self.repository.demands(actor.tenant_id, event_id),
                "lembretes": await self.repository.reminders(actor.tenant_id, event_id),
                "insights": await self.repository.insights(actor.tenant_id, event_id),
            }
        )

    async def detail_by_uuid(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        event_uuid: UUID,
    ) -> EventDetailResponse:
        item = await self.repository.get_event_by_uuid(actor.tenant_id, event_uuid)
        if item is None:
            raise ResourceNotFoundError("Evento", event_uuid)
        return await self.detail(actor, access, int(item["id"]))

    async def add_participant(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        event_id: int,
        payload: ParticipantInput,
    ) -> dict[str, Any]:
        await self.ensure_event(actor, access, event_id, administer=True)
        await self._require_reference(actor, "pessoa", payload.pessoa_id)
        item = await self.repository.upsert_participant(actor.tenant_id, event_id, payload)
        await self._audit(actor, "editar", "evento_participante", item["id"], None, item)
        await self.repository.commit()
        return item

    async def remove_participant(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        event_id: int,
        person_id: int,
    ) -> None:
        await self.ensure_event(actor, access, event_id, administer=True)
        await self.repository.delete_participant(actor.tenant_id, event_id, person_id)
        await self._audit(
            actor,
            "excluir",
            "evento_participante",
            person_id,
            {"evento_id": event_id, "pessoa_id": person_id},
            None,
        )
        await self.repository.commit()

    async def add_leadership(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        event_id: int,
        payload: LeadershipInput,
    ) -> dict[str, Any]:
        await self.ensure_event(actor, access, event_id, administer=True)
        await self._require_reference(actor, "lideranca", payload.lideranca_id)
        item = await self.repository.upsert_leadership(actor.tenant_id, event_id, payload)
        await self._audit(
            actor,
            "editar",
            "evento_lideranca",
            payload.lideranca_id,
            None,
            item,
        )
        await self.repository.commit()
        return item

    async def remove_leadership(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        event_id: int,
        leadership_id: int,
    ) -> None:
        await self.ensure_event(actor, access, event_id, administer=True)
        await self.repository.delete_leadership(actor.tenant_id, event_id, leadership_id)
        await self._audit(
            actor,
            "excluir",
            "evento_lideranca",
            leadership_id,
            {"evento_id": event_id, "lideranca_id": leadership_id},
            None,
        )
        await self.repository.commit()

    async def create_invitation(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        event_id: int,
        payload: InvitationInput,
    ) -> dict[str, Any]:
        await self.ensure_event(actor, access, event_id, administer=True)
        if payload.pessoa_indicou_id:
            await self._require_reference(actor, "pessoa", payload.pessoa_indicou_id)
        if payload.arquivo_id:
            await self._require_reference(actor, "arquivo", payload.arquivo_id)
        item = await self.repository.create_invitation(actor.tenant_id, event_id, payload)
        await self._audit(actor, "criar", "convite", item["id"], None, item)
        await self.repository.commit()
        return item

    async def create_agenda_item(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        event_id: int,
        payload: AgendaItemInput,
    ) -> dict[str, Any]:
        await self.ensure_event(actor, access, event_id, administer=True)
        item = await self.repository.create_agenda_item(actor.tenant_id, event_id, payload)
        await self._audit(actor, "criar", "pauta_evento", item["id"], None, item)
        await self.repository.commit()
        return item

    async def record_attendance(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        event_id: int,
        payload: AttendanceInput,
    ) -> dict[str, Any]:
        await self.ensure_event(actor, access, event_id, administer=True)
        before = await self.repository.attendance(actor.tenant_id, event_id)
        item = await self.repository.upsert_attendance(
            actor.tenant_id, event_id, actor.user_id, payload
        )
        await self.repository.session.execute(
            text(
                "UPDATE agenda.evento SET presenca_parlamentar = :parlamentar, "
                "presenca_representante = :representante, numero_presentes = :numero "
                "WHERE tenant_id = :tenant_id AND id = :event_id"
            ),
            {
                "parlamentar": payload.presenca_parlamentar,
                "representante": payload.presenca_representante,
                "numero": payload.numero_estimado_presentes,
                "tenant_id": actor.tenant_id,
                "event_id": event_id,
            },
        )
        await self._audit(actor, "editar", "presenca_evento", item["id"], before, item)
        await self.repository.commit()
        return item

    async def create_demand(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        event_id: int,
        payload: DemandFromEventInput,
    ) -> dict[str, Any]:
        event = await self.ensure_event(actor, access, event_id, administer=True)
        if payload.pessoa_solicitante_id:
            await self._require_reference(actor, "pessoa", payload.pessoa_solicitante_id)
        if payload.categoria_demanda_id:
            await self._require_reference(actor, "categoria_demanda", payload.categoria_demanda_id)
        if payload.prioridade_demanda_id:
            await self._require_reference(
                actor, "prioridade_demanda", payload.prioridade_demanda_id
            )
        if payload.territorio_id:
            await self._ensure_territory(actor, access, payload.territorio_id, administer=True)
        item = await self.repository.create_demand(
            actor.tenant_id,
            event_id,
            actor.user_id,
            event["territorio_id"],
            payload,
        )
        await AuditService(self.repository.session).record(
            action="criar",
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            schema_name="demanda",
            table_name="demanda",
            record_id=item["id"],
            after=jsonable_encoder(item),
        )
        await self.repository.commit()
        return item

    async def summary(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        start: datetime,
        end: datetime,
    ) -> AgendaSummary:
        if end <= start:
            raise BusinessRuleError("Periodo final deve ser posterior ao inicial.")
        return AgendaSummary.model_validate(
            await self.repository.summary(
                actor.tenant_id,
                start,
                end,
                actor.user_id,
                "agenda.administrar" in actor.permissions,
            )
        )

    async def list_insights(self, actor: RequestActor) -> list[dict[str, Any]]:
        return await self.repository.insights(
            actor.tenant_id,
            user_id=actor.user_id,
            calendar_administrator="agenda.administrar" in actor.permissions,
        )

    async def export_csv(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        **filters: Any,
    ) -> bytes:
        events = await self.list_events(actor, access, **filters)
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(
            [
                "id",
                "data_inicio",
                "data_fim",
                "titulo",
                "agenda",
                "natureza_candidato",
                "frente_comunidade",
                "tipo_agenda",
                "visibilidade",
                "tipo",
                "status",
                "local",
                "territorio",
                "responsavel",
            ]
        )
        for event in events:
            writer.writerow(
                [
                    event["id"],
                    event["data_inicio"].isoformat(),
                    event["data_fim"].isoformat() if event["data_fim"] else "",
                    event["titulo"],
                    event["agenda_nome"],
                    event["natureza_candidato"],
                    event["frente_comunidade"],
                    event["tipo_agenda"],
                    event["visibilidade"],
                    event["tipo_evento_nome"] or "",
                    event["status_evento_nome"] or "",
                    event["local_nome"] or "",
                    event["territorio_nome"] or "",
                    event["responsavel_nome"],
                ]
            )
        await self._audit(
            actor,
            "exportar",
            "evento",
            0,
            None,
            {"quantidade": len(events), "filtros": jsonable_encoder(filters)},
        )
        await self.repository.commit()
        return output.getvalue().encode("utf-8-sig")

    async def ensure_event(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        event_id: int,
        *,
        administer: bool = False,
    ) -> dict[str, Any]:
        item = await self.repository.get_event(actor.tenant_id, event_id)
        if item is None:
            raise ResourceNotFoundError("Evento", event_id)
        await self.ensure_calendar(
            actor, int(item["agenda_id"]), "editar" if administer else "visualizar"
        )
        territory_id = item["territorio_id"]
        if administer:
            ids = await self.accessible_ids(actor, access)
            if ids is not None and territory_id not in ids:
                raise AuthorizationError("Evento fora do escopo territorial permitido.")
            if territory_id is not None:
                await self._ensure_territory(actor, access, territory_id, administer=True)
        return item

    async def _validate_event_references(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        payload: EventInput | EventUpdate,
        *,
        administer: bool,
    ) -> None:
        responsible = payload.responsavel_pessoa_id
        if responsible:
            await self._require_reference(actor, "pessoa", responsible)
        territory_id = payload.territorio_id
        if territory_id:
            await self._ensure_territory(actor, access, territory_id, administer=administer)
        elif not access.unrestricted and isinstance(payload, EventInput):
            raise AuthorizationError(
                "Usuarios com escopo territorial devem informar um territorio."
            )
        if payload.endereco_id:
            await self._require_reference(actor, "endereco", payload.endereco_id)
        for table, item_id in (
            ("tipo_evento", payload.tipo_evento_id),
            ("status_evento", payload.status_evento_id),
        ):
            if (
                item_id
                and await self.repository.get_catalog(table, actor.tenant_id, item_id) is None
            ):
                raise ResourceNotFoundError(table.replace("_", " ").title(), item_id)

    async def _ensure_territory(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        territory_id: int,
        *,
        administer: bool,
    ) -> None:
        territory = await self.territories.get_territory(actor.tenant_id, territory_id)
        if territory is None:
            raise ResourceNotFoundError("Territorio", territory_id)
        ids = await self.territories.accessible_ids(actor.tenant_id, access)
        if ids is not None and territory_id not in ids:
            raise AuthorizationError("Territorio fora do escopo permitido.")
        if administer and not access.unrestricted:
            admin_access = TerritorialAccess(
                unrestricted=False,
                scopes=frozenset(scope for scope in access.scopes if scope[2]),
            )
            admin_ids = await self.territories.accessible_ids(actor.tenant_id, admin_access)
            if admin_ids is not None and territory_id not in admin_ids:
                raise AuthorizationError("Administracao territorial nao permitida.")

    async def _require_reference(self, actor: RequestActor, table: str, item_id: int) -> None:
        if not await self.repository.reference_exists(table, actor.tenant_id, item_id):
            raise ResourceNotFoundError(table.replace("_", " ").title(), item_id)

    async def _audit(
        self,
        actor: RequestActor,
        action: str,
        table: str,
        record_id: int,
        before: dict[str, Any] | None,
        after: dict[str, Any] | None,
    ) -> None:
        await AuditService(self.repository.session).record(
            action=action,
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            schema_name="agenda",
            table_name=table,
            record_id=record_id,
            before=jsonable_encoder(before) if before else None,
            after=jsonable_encoder(after) if after else None,
        )
