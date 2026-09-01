"""Persistencia do dominio de agenda."""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.mod_agenda.access import calendar_view_clause
from app.mod_agenda.schemas import (
    AgendaItemInput,
    AttendanceInput,
    CalendarInput,
    CalendarMemberInput,
    CalendarUpdate,
    CatalogCreate,
    CatalogUpdate,
    DemandFromEventInput,
    EventInput,
    EventUpdate,
    InvitationInput,
    LeadershipInput,
    ParticipantInput,
)


class AgendaRepository:
    CATALOG_TABLES = {"tipo_evento", "status_evento"}

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_calendars(
        self, tenant_id: int, user_id: int, *, administrator: bool = False
    ) -> list[dict[str, Any]]:
        access = (
            "TRUE"
            if administrator
            else calendar_view_clause()
        )
        result = await self.session.execute(
            text(
                "SELECT a.id, a.tenant_id, a.nome, a.descricao, a.natureza_candidato, "
                "a.frente_comunidade, a.tipo_agenda, a.visibilidade, a.cor, a.padrao, "
                "a.ativo, a.criado_em, a.atualizado_em, "
                "COALESCE((SELECT array_remove(ARRAY["
                "CASE WHEN au.pode_visualizar THEN 'visualizar' END, "
                "CASE WHEN au.pode_criar THEN 'criar' END, "
                "CASE WHEN au.pode_editar THEN 'editar' END, "
                "CASE WHEN au.pode_alterar_classificacao THEN 'alterar_classificacao' END, "
                "CASE WHEN au.pode_excluir THEN 'excluir' END, "
                "CASE WHEN au.pode_administrar_usuarios THEN 'administrar_usuarios' END, "
                "CASE WHEN au.pode_administrar_agenda THEN 'administrar_agenda' END], NULL) "
                "FROM agenda.agenda_usuario au WHERE au.agenda_id = a.id "
                "AND au.usuario_id = :user_id), ARRAY[]::text[]) AS permissoes, "
                "CASE WHEN gi.id IS NULL THEN NULL ELSE jsonb_build_object("
                "'id', gi.id, 'google_calendar_id', gi.google_calendar_id, "
                "'google_calendar_nome', gi.google_calendar_nome, 'direcao', gi.direcao, "
                "'status', gi.status, 'ultima_sincronizacao_em', gi.ultima_sincronizacao_em, "
                "'ultimo_erro', gi.ultimo_erro) END AS google_integracao "
                "FROM agenda.agenda a LEFT JOIN agenda.google_integracao_agenda gi "
                "ON gi.agenda_id = a.id WHERE a.tenant_id = :tenant_id "
                f"AND a.excluido_em IS NULL AND {access} ORDER BY a.padrao DESC, a.nome"
            ),
            {"tenant_id": tenant_id, "user_id": user_id},
        )
        return [dict(row) for row in result.mappings()]

    async def get_calendar(self, tenant_id: int, calendar_id: int) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(
                "SELECT * FROM agenda.agenda WHERE tenant_id = :tenant_id AND id = :id "
                "AND excluido_em IS NULL"
            ),
            {"tenant_id": tenant_id, "id": calendar_id},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def default_calendar_id(self, tenant_id: int) -> int | None:
        value = await self.session.scalar(
            text(
                "SELECT id FROM agenda.agenda WHERE tenant_id = :tenant_id "
                "AND padrao AND excluido_em IS NULL LIMIT 1"
            ),
            {"tenant_id": tenant_id},
        )
        return int(value) if value else None

    async def calendar_permissions(
        self, tenant_id: int, calendar_id: int, user_id: int
    ) -> set[str]:
        result = await self.session.execute(
            text(
                "SELECT pode_visualizar, pode_criar, pode_editar, pode_alterar_classificacao, "
                "pode_excluir, pode_administrar_usuarios, pode_administrar_agenda "
                "FROM agenda.agenda_usuario WHERE tenant_id = :tenant_id "
                "AND agenda_id = :calendar_id AND usuario_id = :user_id"
            ),
            {"tenant_id": tenant_id, "calendar_id": calendar_id, "user_id": user_id},
        )
        row = result.mappings().first()
        if not row:
            return set()
        return {field.removeprefix("pode_") for field, enabled in row.items() if enabled}

    async def create_calendar(self, tenant_id: int, user_id: int, payload: CalendarInput) -> int:
        result = await self.session.execute(
            text(
                "INSERT INTO agenda.agenda (tenant_id, nome, descricao, natureza_candidato, "
                "frente_comunidade, tipo_agenda, visibilidade, cor, criado_por) VALUES "
                "(:tenant_id, :nome, :descricao, :natureza_candidato, :frente_comunidade, "
                ":tipo_agenda, :visibilidade, :cor, :user_id) RETURNING id"
            ),
            {"tenant_id": tenant_id, "user_id": user_id, **payload.model_dump()},
        )
        return int(result.scalar_one())

    async def update_calendar(
        self, tenant_id: int, calendar_id: int, payload: CalendarUpdate
    ) -> bool:
        values = payload.model_dump(exclude_unset=True)
        if not values:
            return True
        assignments = ", ".join(f"{field} = :{field}" for field in values)
        result = await self.session.execute(
            text(
                f"UPDATE agenda.agenda SET {assignments} WHERE tenant_id = :tenant_id "
                "AND id = :id AND excluido_em IS NULL"
            ),
            {"tenant_id": tenant_id, "id": calendar_id, **values},
        )
        return bool(result.rowcount)  # type: ignore[attr-defined]

    async def delete_calendar(self, tenant_id: int, calendar_id: int) -> bool:
        result = await self.session.execute(
            text(
                "UPDATE agenda.agenda SET excluido_em = now(), ativo = FALSE "
                "WHERE tenant_id = :tenant_id AND id = :id AND NOT padrao "
                "AND excluido_em IS NULL AND NOT EXISTS (SELECT 1 FROM agenda.evento e "
                "WHERE e.agenda_id = agenda.agenda.id AND e.excluido_em IS NULL)"
            ),
            {"tenant_id": tenant_id, "id": calendar_id},
        )
        return bool(result.rowcount)  # type: ignore[attr-defined]

    async def calendar_members(self, tenant_id: int, calendar_id: int) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text(
                "SELECT au.usuario_id, u.nome, u.email, au.pode_visualizar, au.pode_criar, "
                "au.pode_editar, au.pode_alterar_classificacao, au.pode_excluir, "
                "au.pode_administrar_usuarios, au.pode_administrar_agenda "
                "FROM agenda.agenda_usuario au JOIN auth.usuario u ON u.id = au.usuario_id "
                "WHERE au.tenant_id = :tenant_id AND au.agenda_id = :calendar_id ORDER BY u.nome"
            ),
            {"tenant_id": tenant_id, "calendar_id": calendar_id},
        )
        return [dict(row) for row in result.mappings()]

    async def upsert_calendar_member(
        self, tenant_id: int, calendar_id: int, user_id: int, payload: CalendarMemberInput
    ) -> None:
        await self.session.execute(
            text(
                "INSERT INTO agenda.agenda_usuario (agenda_id, usuario_id, tenant_id, "
                "pode_visualizar, pode_criar, pode_editar, pode_alterar_classificacao, "
                "pode_excluir, pode_administrar_usuarios, pode_administrar_agenda, criado_por) "
                "VALUES (:calendar_id, :usuario_id, :tenant_id, :pode_visualizar, :pode_criar, "
                ":pode_editar, :pode_alterar_classificacao, :pode_excluir, "
                ":pode_administrar_usuarios, :pode_administrar_agenda, :user_id) "
                "ON CONFLICT (agenda_id, usuario_id) DO UPDATE SET "
                "pode_visualizar = EXCLUDED.pode_visualizar, pode_criar = EXCLUDED.pode_criar, "
                "pode_editar = EXCLUDED.pode_editar, "
                "pode_alterar_classificacao = EXCLUDED.pode_alterar_classificacao, "
                "pode_excluir = EXCLUDED.pode_excluir, "
                "pode_administrar_usuarios = EXCLUDED.pode_administrar_usuarios, "
                "pode_administrar_agenda = EXCLUDED.pode_administrar_agenda"
            ),
            {
                "tenant_id": tenant_id,
                "calendar_id": calendar_id,
                "user_id": user_id,
                **payload.model_dump(),
            },
        )

    async def delete_calendar_member(
        self, tenant_id: int, calendar_id: int, member_user_id: int
    ) -> None:
        await self.session.execute(
            text(
                "DELETE FROM agenda.agenda_usuario WHERE tenant_id = :tenant_id "
                "AND agenda_id = :calendar_id AND usuario_id = :user_id"
            ),
            {"tenant_id": tenant_id, "calendar_id": calendar_id, "user_id": member_user_id},
        )

    async def create_oauth_state(
        self,
        tenant_id: int,
        user_id: int,
        state_hash: str,
        verifier_encrypted: str,
        expires_at: datetime,
    ) -> None:
        await self.session.execute(
            text(
                "DELETE FROM agenda.google_oauth_estado WHERE expira_em < now() "
                "OR consumido_em IS NOT NULL"
            )
        )
        await self.session.execute(
            text(
                "INSERT INTO agenda.google_oauth_estado "
                "(tenant_id, usuario_id, estado_hash, code_verifier_criptografado, expira_em) "
                "VALUES (:tenant_id, :user_id, :state_hash, :verifier, :expires_at)"
            ),
            {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "state_hash": state_hash,
                "verifier": verifier_encrypted,
                "expires_at": expires_at,
            },
        )

    async def consume_oauth_state(self, state_hash: str) -> dict[str, Any] | None:
        result = await self.session.execute(
            text("SELECT * FROM agenda.fn_consumir_google_oauth_estado(:state_hash)"),
            {"state_hash": state_hash},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def upsert_google_account(
        self,
        tenant_id: int,
        user_id: int,
        subject: str,
        email: str | None,
        refresh_token_encrypted: str,
        access_token_encrypted: str,
        access_token_expires_at: datetime,
        scopes: str,
    ) -> None:
        await self.session.execute(
            text(
                "INSERT INTO agenda.google_conta_usuario (tenant_id, usuario_id, google_subject, "
                "email, refresh_token_criptografado, access_token_criptografado, "
                "access_token_expira_em, escopos) VALUES (:tenant_id, :user_id, :subject, :email, "
                ":refresh_token, :access_token, :expires_at, :scopes) "
                "ON CONFLICT (tenant_id, usuario_id) DO UPDATE SET "
                "google_subject = EXCLUDED.google_subject, email = EXCLUDED.email, "
                "refresh_token_criptografado = EXCLUDED.refresh_token_criptografado, "
                "access_token_criptografado = EXCLUDED.access_token_criptografado, "
                "access_token_expira_em = EXCLUDED.access_token_expira_em, "
                "escopos = EXCLUDED.escopos, status = 'ativa', ultimo_erro = NULL"
            ),
            {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "subject": subject,
                "email": email,
                "refresh_token": refresh_token_encrypted,
                "access_token": access_token_encrypted,
                "expires_at": access_token_expires_at,
                "scopes": scopes,
            },
        )

    async def google_subject_user(self, tenant_id: int, subject: str) -> int | None:
        value = await self.session.scalar(
            text(
                "SELECT usuario_id FROM agenda.google_conta_usuario "
                "WHERE tenant_id = :tenant_id AND google_subject = :subject"
            ),
            {"tenant_id": tenant_id, "subject": subject},
        )
        return int(value) if value else None

    async def google_account(self, tenant_id: int, user_id: int) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(
                "SELECT * FROM agenda.google_conta_usuario WHERE tenant_id = :tenant_id "
                "AND usuario_id = :user_id AND status = 'ativa'"
            ),
            {"tenant_id": tenant_id, "user_id": user_id},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def update_google_access_token(
        self, account_id: int, encrypted_token: str, expires_at: datetime
    ) -> None:
        await self.session.execute(
            text(
                "UPDATE agenda.google_conta_usuario SET access_token_criptografado = :token, "
                "access_token_expira_em = :expires_at, status = 'ativa', ultimo_erro = NULL "
                "WHERE id = :id"
            ),
            {"id": account_id, "token": encrypted_token, "expires_at": expires_at},
        )

    async def link_google_calendar(
        self,
        tenant_id: int,
        calendar_id: int,
        account_id: int,
        user_id: int,
        google_calendar_id: str,
        google_calendar_name: str,
        direction: str,
    ) -> dict[str, Any]:
        result = await self.session.execute(
            text(
                "INSERT INTO agenda.google_integracao_agenda (tenant_id, agenda_id, "
                "google_conta_id, google_calendar_id, google_calendar_nome, direcao, criado_por) "
                "VALUES (:tenant_id, :calendar_id, :account_id, :google_calendar_id, "
                ":google_calendar_name, :direction, :user_id) "
                "ON CONFLICT (agenda_id) DO UPDATE SET google_conta_id = EXCLUDED.google_conta_id, "
                "google_calendar_id = EXCLUDED.google_calendar_id, "
                "google_calendar_nome = EXCLUDED.google_calendar_nome, direcao = EXCLUDED.direcao, "
                "sync_token = NULL, status = 'ativa', ultimo_erro = NULL "
                "RETURNING id, agenda_id, google_calendar_id, google_calendar_nome, direcao, "
                "status, ultima_sincronizacao_em, ultimo_erro"
            ),
            {
                "tenant_id": tenant_id,
                "calendar_id": calendar_id,
                "account_id": account_id,
                "user_id": user_id,
                "google_calendar_id": google_calendar_id,
                "google_calendar_name": google_calendar_name,
                "direction": direction,
            },
        )
        return dict(result.mappings().one())

    async def google_integration(self, tenant_id: int, calendar_id: int) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(
                "SELECT gi.*, a.visibilidade AS agenda_visibilidade, gc.usuario_id, "
                "gc.refresh_token_criptografado, "
                "gc.access_token_criptografado, gc.access_token_expira_em, u.pessoa_id "
                "FROM agenda.google_integracao_agenda gi "
                "JOIN agenda.agenda a ON a.id = gi.agenda_id "
                "JOIN agenda.google_conta_usuario gc ON gc.id = gi.google_conta_id "
                "JOIN auth.usuario u ON u.id = gc.usuario_id "
                "WHERE gi.tenant_id = :tenant_id AND gi.agenda_id = :calendar_id "
                "AND gi.status <> 'pausada'"
            ),
            {"tenant_id": tenant_id, "calendar_id": calendar_id},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def unlink_google_calendar(self, tenant_id: int, calendar_id: int) -> None:
        await self.session.execute(
            text(
                "DELETE FROM agenda.google_integracao_agenda WHERE tenant_id = :tenant_id "
                "AND agenda_id = :calendar_id"
            ),
            {"tenant_id": tenant_id, "calendar_id": calendar_id},
        )

    async def events_for_google_sync(
        self, tenant_id: int, calendar_id: int
    ) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text(
                "SELECT e.*, se.codigo AS status_evento_codigo, gv.google_event_id, "
                "gv.google_etag, gv.google_atualizado_em, gv.sistema_atualizado_em, "
                "gv.status AS google_link_status "
                "FROM agenda.evento e LEFT JOIN agenda.status_evento se "
                "ON se.id = e.status_evento_id "
                "LEFT JOIN agenda.google_integracao_agenda gi ON gi.agenda_id = e.agenda_id "
                "LEFT JOIN agenda.google_evento_vinculo gv ON gv.integracao_id = gi.id "
                "AND gv.evento_id = e.id WHERE e.tenant_id = :tenant_id "
                "AND e.agenda_id = :calendar_id AND (e.excluido_em IS NULL OR "
                "(gv.id IS NOT NULL AND gv.status <> 'excluido')) ORDER BY e.id"
            ),
            {"tenant_id": tenant_id, "calendar_id": calendar_id},
        )
        return [dict(row) for row in result.mappings()]

    async def upsert_google_event_link(
        self,
        tenant_id: int,
        integration_id: int,
        event_id: int,
        google_event_id: str,
        etag: str | None,
        google_updated_at: datetime | None,
        system_updated_at: datetime | None,
    ) -> None:
        await self.session.execute(
            text(
                "INSERT INTO agenda.google_evento_vinculo (tenant_id, integracao_id, evento_id, "
                "google_event_id, google_etag, google_atualizado_em, sistema_atualizado_em) "
                "VALUES (:tenant_id, :integration_id, :event_id, :google_event_id, :etag, "
                ":google_updated_at, :system_updated_at) ON CONFLICT (integracao_id, evento_id) "
                "DO UPDATE SET google_event_id = EXCLUDED.google_event_id, "
                "google_etag = EXCLUDED.google_etag, "
                "google_atualizado_em = EXCLUDED.google_atualizado_em, "
                "sistema_atualizado_em = EXCLUDED.sistema_atualizado_em, "
                "status = 'sincronizado', ultimo_erro = NULL"
            ),
            {
                "tenant_id": tenant_id,
                "integration_id": integration_id,
                "event_id": event_id,
                "google_event_id": google_event_id,
                "etag": etag,
                "google_updated_at": google_updated_at,
                "system_updated_at": system_updated_at,
            },
        )

    async def google_event_link(
        self, integration_id: int, google_event_id: str
    ) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(
                "SELECT * FROM agenda.google_evento_vinculo WHERE integracao_id = :integration_id "
                "AND google_event_id = :google_event_id"
            ),
            {"integration_id": integration_id, "google_event_id": google_event_id},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def mark_google_event_deleted(self, integration_id: int, event_id: int) -> None:
        await self.session.execute(
            text(
                "UPDATE agenda.google_evento_vinculo SET status = 'excluido', "
                "atualizado_em = now() WHERE integracao_id = :integration_id "
                "AND evento_id = :event_id"
            ),
            {"integration_id": integration_id, "event_id": event_id},
        )

    async def import_google_event(
        self,
        tenant_id: int,
        calendar_id: int,
        responsible_person_id: int,
        title: str,
        description: str | None,
        start: datetime,
        end: datetime | None,
        location: str | None,
    ) -> int:
        result = await self.session.execute(
            text(
                "INSERT INTO agenda.evento (tenant_id, agenda_id, contexto, titulo, descricao, "
                "data_inicio, data_fim, local_nome, responsavel_pessoa_id, status_evento_id) "
                "VALUES (:tenant_id, :calendar_id, 'campanha', :title, :description, :start, :end, "
                ":location, :responsible_person_id, (SELECT id FROM agenda.status_evento "
                "WHERE codigo = 'planejado' AND (tenant_id IS NULL OR tenant_id = :tenant_id) "
                "ORDER BY tenant_id DESC NULLS LAST LIMIT 1)) RETURNING id"
            ),
            {
                "tenant_id": tenant_id,
                "calendar_id": calendar_id,
                "responsible_person_id": responsible_person_id,
                "title": title,
                "description": description,
                "start": start,
                "end": end,
                "location": location,
            },
        )
        return int(result.scalar_one())

    async def update_imported_event(
        self,
        tenant_id: int,
        event_id: int,
        title: str,
        description: str | None,
        start: datetime,
        end: datetime | None,
        location: str | None,
        cancelled: bool,
    ) -> None:
        await self.session.execute(
            text(
                "UPDATE agenda.evento SET titulo = :title, descricao = :description, "
                "data_inicio = :start, data_fim = :end, local_nome = :location, "
                "status_evento_id = CASE WHEN :cancelled THEN (SELECT id FROM agenda.status_evento "
                "WHERE codigo = 'cancelado' AND (tenant_id IS NULL OR tenant_id = :tenant_id) "
                "ORDER BY tenant_id DESC NULLS LAST LIMIT 1) ELSE status_evento_id END "
                "WHERE tenant_id = :tenant_id AND id = :event_id"
            ),
            {
                "tenant_id": tenant_id,
                "event_id": event_id,
                "title": title,
                "description": description,
                "start": start,
                "end": end,
                "location": location,
                "cancelled": cancelled,
            },
        )

    async def cancel_imported_event(self, tenant_id: int, event_id: int) -> None:
        await self.session.execute(
            text(
                "UPDATE agenda.evento SET status_evento_id = (SELECT id "
                "FROM agenda.status_evento WHERE codigo = 'cancelado' "
                "AND (tenant_id IS NULL OR tenant_id = :tenant_id) "
                "ORDER BY tenant_id DESC NULLS LAST LIMIT 1), "
                "motivo_cancelamento = 'Excluido no Google Agenda', cancelado_em = now() "
                "WHERE tenant_id = :tenant_id AND id = :event_id"
            ),
            {"tenant_id": tenant_id, "event_id": event_id},
        )

    async def finish_google_sync(
        self, integration_id: int, sync_token: str | None, error: str | None = None
    ) -> None:
        await self.session.execute(
            text(
                "UPDATE agenda.google_integracao_agenda "
                "SET sync_token = COALESCE(:sync_token, sync_token), "
                "ultima_sincronizacao_em = now(), status = CASE WHEN :error IS NULL THEN 'ativa' "
                "ELSE 'erro' END, ultimo_erro = :error WHERE id = :id"
            ),
            {"id": integration_id, "sync_token": sync_token, "error": error},
        )

    async def list_catalog(
        self, table: str, tenant_id: int, include_inactive: bool
    ) -> list[dict[str, Any]]:
        self._ensure_catalog(table)
        inactive = "" if include_inactive else "AND ativo"
        result = await self.session.execute(
            text(
                f"SELECT id, tenant_id, codigo, nome, descricao, ativo, "
                f"criado_em, atualizado_em FROM agenda.{table} "
                "WHERE (tenant_id IS NULL OR tenant_id = :tenant_id) "
                f"{inactive} ORDER BY tenant_id NULLS FIRST, nome"
            ),
            {"tenant_id": tenant_id},
        )
        return [dict(row) for row in result.mappings()]

    async def get_catalog(self, table: str, tenant_id: int, item_id: int) -> dict[str, Any] | None:
        self._ensure_catalog(table)
        result = await self.session.execute(
            text(
                f"SELECT id, tenant_id, codigo, nome, descricao, ativo, "
                f"criado_em, atualizado_em FROM agenda.{table} "
                "WHERE id = :id AND (tenant_id IS NULL OR tenant_id = :tenant_id)"
            ),
            {"id": item_id, "tenant_id": tenant_id},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def create_catalog(
        self, table: str, tenant_id: int, payload: CatalogCreate
    ) -> dict[str, Any]:
        self._ensure_catalog(table)
        result = await self.session.execute(
            text(
                f"INSERT INTO agenda.{table} "
                "(tenant_id, codigo, nome, descricao) "
                "VALUES (:tenant_id, :codigo, :nome, :descricao) "
                "RETURNING id, tenant_id, codigo, nome, descricao, ativo, "
                "criado_em, atualizado_em"
            ),
            {"tenant_id": tenant_id, **payload.model_dump()},
        )
        return dict(result.mappings().one())

    async def update_catalog(
        self,
        table: str,
        tenant_id: int,
        item_id: int,
        payload: CatalogUpdate,
    ) -> dict[str, Any] | None:
        self._ensure_catalog(table)
        values = payload.model_dump(exclude_unset=True)
        if not values:
            return await self.get_catalog(table, tenant_id, item_id)
        assignments = ", ".join(f"{field} = :{field}" for field in values)
        result = await self.session.execute(
            text(
                f"UPDATE agenda.{table} SET {assignments} "
                "WHERE id = :id AND tenant_id = :tenant_id "
                "RETURNING id, tenant_id, codigo, nome, descricao, ativo, "
                "criado_em, atualizado_em"
            ),
            {"id": item_id, "tenant_id": tenant_id, **values},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def list_events(
        self,
        tenant_id: int,
        *,
        start: datetime | None,
        end: datetime | None,
        territory_id: int | None,
        leader_id: int | None,
        event_type_id: int | None,
        status_id: int | None,
        calendar_id: int | None,
        candidate_nature: str | None,
        community_front: str | None,
        calendar_type: str | None,
        visibility: str | None,
        user_id: int,
        calendar_administrator: bool,
    ) -> list[dict[str, Any]]:
        clauses = ["e.tenant_id = :tenant_id", "e.excluido_em IS NULL", "a.ativo"]
        values: dict[str, Any] = {"tenant_id": tenant_id}
        if start:
            clauses.append("e.data_inicio >= :start")
            values["start"] = start
        if end:
            clauses.append("e.data_inicio < :end")
            values["end"] = end
        if territory_id:
            clauses.append("e.territorio_id = :territory_id")
            values["territory_id"] = territory_id
        if leader_id:
            clauses.append(
                "EXISTS (SELECT 1 FROM agenda.evento_lideranca el "
                "WHERE el.evento_id = e.id AND el.tenant_id = e.tenant_id "
                "AND el.lideranca_id = :leader_id)"
            )
            values["leader_id"] = leader_id
        if event_type_id:
            clauses.append("e.tipo_evento_id = :event_type_id")
            values["event_type_id"] = event_type_id
        if status_id:
            clauses.append("e.status_evento_id = :status_id")
            values["status_id"] = status_id
        if calendar_id:
            clauses.append("e.agenda_id = :calendar_id")
            values["calendar_id"] = calendar_id
        for column, parameter, value in (
            ("natureza_candidato", "candidate_nature", candidate_nature),
            ("frente_comunidade", "community_front", community_front),
            ("tipo_agenda", "calendar_type", calendar_type),
            ("visibilidade", "visibility", visibility),
        ):
            if value:
                clauses.append(f"a.{column} = :{parameter}")
                values[parameter] = value
        if not calendar_administrator:
            clauses.append(calendar_view_clause())
            values["user_id"] = user_id
        result = await self.session.execute(
            text(
                self._event_select() + " WHERE " + " AND ".join(clauses) + " ORDER BY e.data_inicio"
            ),
            values,
        )
        return [dict(row) for row in result.mappings()]

    async def get_event(self, tenant_id: int, event_id: int) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(
                self._event_select() + " WHERE e.tenant_id = :tenant_id AND e.id = :id "
                "AND e.excluido_em IS NULL"
            ),
            {"tenant_id": tenant_id, "id": event_id},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def get_event_by_uuid(self, tenant_id: int, event_uuid: UUID) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(
                self._event_select() + " WHERE e.tenant_id = :tenant_id "
                "AND e.uuid_publico = :event_uuid AND e.excluido_em IS NULL"
            ),
            {"tenant_id": tenant_id, "event_uuid": event_uuid},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    @staticmethod
    def _event_select() -> str:
        return (
            "SELECT e.id, e.uuid_publico, e.tenant_id, e.contexto, e.campanha_eleicao_id, "
            "e.agenda_id, a.nome AS agenda_nome, a.cor AS agenda_cor, "
            "a.natureza_candidato, a.frente_comunidade, a.tipo_agenda, a.visibilidade, "
            "e.tipo_evento_id, te.nome AS tipo_evento_nome, "
            "e.status_evento_id, se.codigo AS status_evento_codigo, "
            "se.nome AS status_evento_nome, e.titulo, e.descricao, e.data_inicio, "
            "e.data_fim, e.local_nome, e.endereco_id, e.codigo_municipio_ibge, e.bairro_id, "
            "e.zona_eleitoral_id, e.territorio_id, t.nome AS territorio_nome, "
            "e.latitude, e.longitude, e.responsavel_pessoa_id, "
            "p.nome_completo AS responsavel_nome, e.motivo_cancelamento, "
            "e.cancelado_em, e.criado_em, e.atualizado_em FROM agenda.evento e "
            "JOIN agenda.agenda a ON a.id = e.agenda_id "
            "LEFT JOIN agenda.tipo_evento te ON te.id = e.tipo_evento_id "
            "LEFT JOIN agenda.status_evento se ON se.id = e.status_evento_id "
            "LEFT JOIN territorio.territorio t ON t.id = e.territorio_id "
            "JOIN cadastro.pessoa p ON p.id = e.responsavel_pessoa_id "
        )

    async def get_public_event(self, public_id: UUID) -> dict[str, Any] | None:
        result = await self.session.execute(
            text("SELECT * FROM agenda.fn_evento_publico(:public_id)"),
            {"public_id": public_id},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def set_tenant_context(self, tenant_id: int) -> None:
        await self.session.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": str(tenant_id)},
        )

    async def lock_public_attendance_identity(
        self, tenant_id: int, normalized_name: str, phone_digits: str
    ) -> None:
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:identity_key, 0))"),
            {"identity_key": f"presenca:{tenant_id}:{normalized_name}:{phone_digits}"},
        )

    async def find_public_attendance_person(
        self,
        tenant_id: int,
        name: str,
        phone_digits: str,
        email: str | None,
        birth_date: date | None,
    ) -> int | None:
        result = await self.session.execute(
            text(
                "SELECT p.id FROM cadastro.pessoa p "
                "WHERE p.tenant_id = :tenant_id AND p.ativo "
                "AND p.excluido_em IS NULL "
                "AND unaccent(lower(regexp_replace(btrim(p.nome_completo), "
                "'\\s+', ' ', 'g'))) = unaccent(lower(:name)) "
                "AND EXISTS (SELECT 1 FROM cadastro.pessoa_contato pc "
                "WHERE pc.tenant_id = p.tenant_id AND pc.pessoa_id = p.id "
                "AND pc.tipo_contato IN ('telefone', 'celular', 'whatsapp') "
                "AND regexp_replace(pc.valor, '\\D', '', 'g') "
                "IN (:phone, '55' || :phone)) "
                "ORDER BY "
                "CASE WHEN CAST(:email AS TEXT) IS NOT NULL AND EXISTS ("
                "SELECT 1 FROM cadastro.pessoa_contato pe WHERE pe.pessoa_id = p.id "
                "AND pe.tenant_id = p.tenant_id AND pe.tipo_contato = 'email' "
                "AND lower(pe.valor) = CAST(:email AS TEXT)) THEN 1 ELSE 0 END DESC, "
                "CASE WHEN CAST(:birth_date AS DATE) IS NOT NULL "
                "AND p.data_nascimento = CAST(:birth_date AS DATE) "
                "THEN 1 ELSE 0 END DESC, p.id LIMIT 1"
            ),
            {
                "tenant_id": tenant_id,
                "name": name,
                "phone": phone_digits,
                "email": email,
                "birth_date": birth_date,
            },
        )
        value = result.scalar_one_or_none()
        return int(value) if value is not None else None

    async def create_public_attendance_person(
        self,
        tenant_id: int,
        name: str,
        phone_digits: str,
        email: str | None,
        birth_date: date | None,
    ) -> int:
        person_id = int(
            await self.session.scalar(
                text(
                    "INSERT INTO cadastro.pessoa "
                    "(tenant_id, nome_completo, data_nascimento, origem_cadastro) "
                    "VALUES (:tenant_id, :name, :birth_date, 'formulario') "
                    "RETURNING id"
                ),
                {"tenant_id": tenant_id, "name": name, "birth_date": birth_date},
            )
        )
        await self.session.execute(
            text(
                "INSERT INTO cadastro.pessoa_contato "
                "(tenant_id, pessoa_id, tipo_contato, valor, principal) "
                "VALUES (:tenant_id, :person_id, 'whatsapp', :phone, TRUE)"
            ),
            {"tenant_id": tenant_id, "person_id": person_id, "phone": phone_digits},
        )
        if email:
            await self.session.execute(
                text(
                    "INSERT INTO cadastro.pessoa_contato "
                    "(tenant_id, pessoa_id, tipo_contato, valor, principal) "
                    "VALUES (:tenant_id, :person_id, 'email', :email, FALSE)"
                ),
                {"tenant_id": tenant_id, "person_id": person_id, "email": email},
            )
        return person_id

    async def complement_public_attendance_person(
        self,
        tenant_id: int,
        person_id: int,
        email: str | None,
        birth_date: date | None,
    ) -> None:
        if birth_date is not None:
            await self.session.execute(
                text(
                    "UPDATE cadastro.pessoa SET data_nascimento = :birth_date, "
                    "atualizado_em = now() WHERE tenant_id = :tenant_id AND id = :person_id "
                    "AND data_nascimento IS NULL"
                ),
                {
                    "tenant_id": tenant_id,
                    "person_id": person_id,
                    "birth_date": birth_date,
                },
            )
        if email:
            await self.session.execute(
                text(
                    "INSERT INTO cadastro.pessoa_contato "
                    "(tenant_id, pessoa_id, tipo_contato, valor, principal) "
                    "SELECT :tenant_id, :person_id, 'email', :email, FALSE "
                    "WHERE NOT EXISTS (SELECT 1 FROM cadastro.pessoa_contato "
                    "WHERE tenant_id = :tenant_id AND pessoa_id = :person_id "
                    "AND tipo_contato = 'email')"
                ),
                {"tenant_id": tenant_id, "person_id": person_id, "email": email},
            )

    async def public_participation(
        self, tenant_id: int, event_id: int, person_id: int
    ) -> bool | None:
        value = await self.session.scalar(
            text(
                "SELECT presente FROM agenda.evento_participante "
                "WHERE tenant_id = :tenant_id AND evento_id = :event_id "
                "AND pessoa_id = :person_id"
            ),
            {"tenant_id": tenant_id, "event_id": event_id, "person_id": person_id},
        )
        return bool(value) if value is not None else None

    async def upsert_public_participation(
        self, tenant_id: int, event_id: int, person_id: int, *, confirmed: bool
    ) -> None:
        if confirmed:
            conflict_action = "DO UPDATE SET presente = TRUE"
            present_value = "TRUE"
        else:
            conflict_action = "DO UPDATE SET presente = NULL"
            present_value = "NULL"
        await self.session.execute(
            text(
                "INSERT INTO agenda.evento_participante "
                "(tenant_id, evento_id, pessoa_id, papel, presente, observacao) "
                "VALUES (:tenant_id, :event_id, :person_id, 'participante', "
                f"{present_value}, 'Cadastro pelo formulario publico') "
                "ON CONFLICT (evento_id, pessoa_id) "
                f"{conflict_action}"
            ),
            {"tenant_id": tenant_id, "event_id": event_id, "person_id": person_id},
        )

    async def create_event(self, tenant_id: int, user_id: int, payload: EventInput) -> int:
        values = payload.model_dump()
        result = await self.session.execute(
            text(
                "INSERT INTO agenda.evento "
                "(tenant_id, agenda_id, contexto, campanha_eleicao_id, tipo_evento_id, "
                "status_evento_id, titulo, descricao, "
                "data_inicio, data_fim, local_nome, endereco_id, codigo_municipio_ibge, "
                "bairro_id, zona_eleitoral_id, territorio_id, latitude, longitude, "
                "responsavel_pessoa_id, criado_por) VALUES "
                "(:tenant_id, :agenda_id, :contexto, :campanha_eleicao_id, :tipo_evento_id, "
                "COALESCE(:status_evento_id, "
                "(SELECT id FROM agenda.status_evento WHERE codigo = 'planejado' "
                "AND (tenant_id IS NULL OR tenant_id = :tenant_id) "
                "ORDER BY tenant_id DESC NULLS LAST LIMIT 1)), :titulo, :descricao, "
                ":data_inicio, :data_fim, :local_nome, :endereco_id, :codigo_municipio_ibge, "
                ":bairro_id, :zona_eleitoral_id, :territorio_id, :latitude, :longitude, "
                ":responsavel_pessoa_id, :user_id) RETURNING id"
            ),
            {"tenant_id": tenant_id, "user_id": user_id, **values},
        )
        return int(result.scalar_one())

    async def update_event(self, tenant_id: int, event_id: int, payload: EventUpdate) -> bool:
        values = payload.model_dump(exclude_unset=True)
        if not values:
            return True
        assignments = ", ".join(f"{field} = :{field}" for field in values)
        result = await self.session.execute(
            text(
                f"UPDATE agenda.evento SET {assignments} "
                "WHERE tenant_id = :tenant_id AND id = :id AND excluido_em IS NULL"
            ),
            {"tenant_id": tenant_id, "id": event_id, **values},
        )
        return bool(result.rowcount)  # type: ignore[attr-defined]

    async def cancel_event(self, tenant_id: int, event_id: int, user_id: int, reason: str) -> bool:
        result = await self.session.execute(
            text(
                "UPDATE agenda.evento SET status_evento_id = ("
                "SELECT id FROM agenda.status_evento WHERE codigo = 'cancelado' "
                "AND (tenant_id IS NULL OR tenant_id = :tenant_id) "
                "ORDER BY tenant_id DESC NULLS LAST LIMIT 1), "
                "motivo_cancelamento = :reason, cancelado_por = :user_id, "
                "cancelado_em = now() WHERE tenant_id = :tenant_id AND id = :id "
                "AND excluido_em IS NULL"
            ),
            {
                "tenant_id": tenant_id,
                "id": event_id,
                "user_id": user_id,
                "reason": reason,
            },
        )
        return bool(result.rowcount)  # type: ignore[attr-defined]

    async def delete_event(self, tenant_id: int, event_id: int) -> bool:
        result = await self.session.execute(
            text(
                "UPDATE agenda.evento SET excluido_em = now() WHERE tenant_id = :tenant_id "
                "AND id = :id AND excluido_em IS NULL"
            ),
            {"tenant_id": tenant_id, "id": event_id},
        )
        return bool(result.rowcount)  # type: ignore[attr-defined]

    async def participants(self, tenant_id: int, event_id: int) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text(
                "SELECT ep.id, ep.pessoa_id, p.nome_completo AS nome, ep.papel, "
                "ep.presente, ep.observacao FROM agenda.evento_participante ep "
                "JOIN cadastro.pessoa p ON p.id = ep.pessoa_id "
                "WHERE ep.tenant_id = :tenant_id AND ep.evento_id = :event_id "
                "ORDER BY p.nome_completo"
            ),
            {"tenant_id": tenant_id, "event_id": event_id},
        )
        return [dict(row) for row in result.mappings()]

    async def upsert_participant(
        self, tenant_id: int, event_id: int, payload: ParticipantInput
    ) -> dict[str, Any]:
        await self.session.execute(
            text(
                "INSERT INTO agenda.evento_participante "
                "(tenant_id, evento_id, pessoa_id, papel, presente, observacao) "
                "VALUES (:tenant_id, :event_id, :pessoa_id, :papel, :presente, :observacao) "
                "ON CONFLICT (evento_id, pessoa_id) DO UPDATE SET "
                "papel = EXCLUDED.papel, presente = EXCLUDED.presente, "
                "observacao = EXCLUDED.observacao"
            ),
            {"tenant_id": tenant_id, "event_id": event_id, **payload.model_dump()},
        )
        items = await self.participants(tenant_id, event_id)
        return next(item for item in items if item["pessoa_id"] == payload.pessoa_id)

    async def delete_participant(self, tenant_id: int, event_id: int, person_id: int) -> None:
        await self.session.execute(
            text(
                "DELETE FROM agenda.evento_participante "
                "WHERE tenant_id = :tenant_id AND evento_id = :event_id "
                "AND pessoa_id = :person_id"
            ),
            {"tenant_id": tenant_id, "event_id": event_id, "person_id": person_id},
        )

    async def leaderships(self, tenant_id: int, event_id: int) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text(
                "SELECT el.lideranca_id, el.papel, l.pessoa_id, "
                "p.nome_completo AS nome, l.tipo_lideranca "
                "FROM agenda.evento_lideranca el "
                "JOIN cadastro.lideranca l ON l.id = el.lideranca_id "
                "JOIN cadastro.pessoa p ON p.id = l.pessoa_id "
                "WHERE el.tenant_id = :tenant_id AND el.evento_id = :event_id "
                "ORDER BY p.nome_completo"
            ),
            {"tenant_id": tenant_id, "event_id": event_id},
        )
        return [dict(row) for row in result.mappings()]

    async def upsert_leadership(
        self, tenant_id: int, event_id: int, payload: LeadershipInput
    ) -> dict[str, Any]:
        await self.session.execute(
            text(
                "INSERT INTO agenda.evento_lideranca "
                "(tenant_id, evento_id, lideranca_id, papel) "
                "VALUES (:tenant_id, :event_id, :lideranca_id, :papel) "
                "ON CONFLICT (evento_id, lideranca_id) DO UPDATE "
                "SET papel = EXCLUDED.papel"
            ),
            {"tenant_id": tenant_id, "event_id": event_id, **payload.model_dump()},
        )
        items = await self.leaderships(tenant_id, event_id)
        return next(item for item in items if item["lideranca_id"] == payload.lideranca_id)

    async def delete_leadership(self, tenant_id: int, event_id: int, leadership_id: int) -> None:
        await self.session.execute(
            text(
                "DELETE FROM agenda.evento_lideranca "
                "WHERE tenant_id = :tenant_id AND evento_id = :event_id "
                "AND lideranca_id = :leadership_id"
            ),
            {
                "tenant_id": tenant_id,
                "event_id": event_id,
                "leadership_id": leadership_id,
            },
        )

    async def invitations(self, tenant_id: int, event_id: int) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text(
                "SELECT c.id, c.direcao, c.origem, c.pessoa_indicou_id, "
                "p.nome_completo AS pessoa_indicou_nome, c.arquivo_id, "
                "a.nome_original AS arquivo_nome, c.status, c.descricao, c.criado_em "
                "FROM agenda.convite c "
                "LEFT JOIN cadastro.pessoa p ON p.id = c.pessoa_indicou_id "
                "LEFT JOIN arquivo.arquivo a ON a.id = c.arquivo_id "
                "WHERE c.tenant_id = :tenant_id AND c.evento_id = :event_id "
                "ORDER BY c.criado_em DESC"
            ),
            {"tenant_id": tenant_id, "event_id": event_id},
        )
        return [dict(row) for row in result.mappings()]

    async def create_invitation(
        self, tenant_id: int, event_id: int, payload: InvitationInput
    ) -> dict[str, Any]:
        invitation_id = int(
            await self.session.scalar(
                text(
                    "INSERT INTO agenda.convite "
                    "(tenant_id, evento_id, direcao, origem, pessoa_indicou_id, "
                    "arquivo_id, status, descricao) VALUES "
                    "(:tenant_id, :event_id, :direcao, :origem, :pessoa_indicou_id, "
                    ":arquivo_id, :status, :descricao) RETURNING id"
                ),
                {"tenant_id": tenant_id, "event_id": event_id, **payload.model_dump()},
            )
        )
        return next(
            item
            for item in await self.invitations(tenant_id, event_id)
            if item["id"] == invitation_id
        )

    async def agenda_items(self, tenant_id: int, event_id: int) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text(
                "SELECT id, titulo, descricao, encaminhamento, ordem, criado_em "
                "FROM agenda.pauta_evento WHERE tenant_id = :tenant_id "
                "AND evento_id = :event_id ORDER BY ordem NULLS LAST, id"
            ),
            {"tenant_id": tenant_id, "event_id": event_id},
        )
        return [dict(row) for row in result.mappings()]

    async def create_agenda_item(
        self, tenant_id: int, event_id: int, payload: AgendaItemInput
    ) -> dict[str, Any]:
        result = await self.session.execute(
            text(
                "INSERT INTO agenda.pauta_evento "
                "(tenant_id, evento_id, titulo, descricao, encaminhamento, ordem) "
                "VALUES (:tenant_id, :event_id, :titulo, :descricao, "
                ":encaminhamento, :ordem) "
                "RETURNING id, titulo, descricao, encaminhamento, ordem, criado_em"
            ),
            {"tenant_id": tenant_id, "event_id": event_id, **payload.model_dump()},
        )
        return dict(result.mappings().one())

    async def attendance(self, tenant_id: int, event_id: int) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(
                "SELECT id, presenca_parlamentar, presenca_representante, "
                "nome_representante, numero_lideres_presentes, numero_convidados, "
                "numero_estimado_presentes, observacao, registrado_por, registrado_em "
                "FROM agenda.presenca_evento WHERE tenant_id = :tenant_id "
                "AND evento_id = :event_id"
            ),
            {"tenant_id": tenant_id, "event_id": event_id},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def upsert_attendance(
        self,
        tenant_id: int,
        event_id: int,
        user_id: int,
        payload: AttendanceInput,
    ) -> dict[str, Any]:
        values = payload.model_dump()
        await self.session.execute(
            text(
                "INSERT INTO agenda.presenca_evento "
                "(tenant_id, evento_id, presenca_parlamentar, presenca_representante, "
                "nome_representante, numero_lideres_presentes, numero_convidados, "
                "numero_estimado_presentes, observacao, registrado_por) VALUES "
                "(:tenant_id, :event_id, :presenca_parlamentar, "
                ":presenca_representante, :nome_representante, "
                ":numero_lideres_presentes, :numero_convidados, "
                ":numero_estimado_presentes, :observacao, :user_id) "
                "ON CONFLICT (evento_id) DO UPDATE SET "
                "presenca_parlamentar = EXCLUDED.presenca_parlamentar, "
                "presenca_representante = EXCLUDED.presenca_representante, "
                "nome_representante = EXCLUDED.nome_representante, "
                "numero_lideres_presentes = EXCLUDED.numero_lideres_presentes, "
                "numero_convidados = EXCLUDED.numero_convidados, "
                "numero_estimado_presentes = EXCLUDED.numero_estimado_presentes, "
                "observacao = EXCLUDED.observacao, registrado_por = EXCLUDED.registrado_por, "
                "registrado_em = now()"
            ),
            {
                "tenant_id": tenant_id,
                "event_id": event_id,
                "user_id": user_id,
                **values,
            },
        )
        item = await self.attendance(tenant_id, event_id)
        assert item is not None
        return item

    async def demands(self, tenant_id: int, event_id: int) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text(
                "SELECT d.id, d.evento_id, d.titulo, d.descricao, "
                "d.pessoa_solicitante_id, d.territorio_id, sd.codigo AS status, "
                "pd.nome AS prioridade, d.criado_em FROM demanda.demanda d "
                "JOIN demanda.status_demanda sd ON sd.id = d.status_demanda_id "
                "LEFT JOIN demanda.prioridade_demanda pd "
                "ON pd.id = d.prioridade_demanda_id "
                "WHERE d.tenant_id = :tenant_id AND d.evento_id = :event_id "
                "AND d.excluido_em IS NULL ORDER BY d.criado_em DESC"
            ),
            {"tenant_id": tenant_id, "event_id": event_id},
        )
        return [dict(row) for row in result.mappings()]

    async def create_demand(
        self,
        tenant_id: int,
        event_id: int,
        user_id: int,
        event_territory_id: int | None,
        payload: DemandFromEventInput,
    ) -> dict[str, Any]:
        demand_id = int(
            await self.session.scalar(
                text(
                    "INSERT INTO demanda.demanda "
                    "(tenant_id, categoria_demanda_id, prioridade_demanda_id, "
                    "status_demanda_id, origem_demanda_id, titulo, descricao, "
                    "pessoa_solicitante_id, evento_id, territorio_id, prazo, criado_por) "
                    "VALUES (:tenant_id, :categoria_demanda_id, :prioridade_demanda_id, "
                    "(SELECT id FROM demanda.status_demanda WHERE codigo = 'pendente'), "
                    "(SELECT id FROM demanda.origem_demanda WHERE codigo = 'evento'), "
                    ":titulo, :descricao, :pessoa_solicitante_id, :event_id, "
                    "COALESCE(CAST(:territorio_id AS bigint), "
                    "CAST(:event_territory_id AS bigint)), :prazo, :user_id) "
                    "RETURNING id"
                ),
                {
                    "tenant_id": tenant_id,
                    "event_id": event_id,
                    "user_id": user_id,
                    "event_territory_id": event_territory_id,
                    **payload.model_dump(),
                },
            )
        )
        return next(
            item for item in await self.demands(tenant_id, event_id) if item["id"] == demand_id
        )

    async def reminders(self, tenant_id: int, event_id: int) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text(
                "SELECT id, evento_id, tipo, mensagem, agendado_para, status "
                "FROM agenda.lembrete_evento WHERE tenant_id = :tenant_id "
                "AND evento_id = :event_id ORDER BY agendado_para"
            ),
            {"tenant_id": tenant_id, "event_id": event_id},
        )
        return [dict(row) for row in result.mappings()]

    async def insights(
        self,
        tenant_id: int,
        event_id: int | None = None,
        *,
        user_id: int | None = None,
        calendar_administrator: bool = False,
    ) -> list[dict[str, Any]]:
        clause = "AND (evento_id = :event_id OR evento_id IS NULL)" if event_id else ""
        calendar_access = ""
        values: dict[str, Any] = {"tenant_id": tenant_id, "event_id": event_id}
        if event_id is None and not calendar_administrator:
            calendar_access = f"AND (ie.evento_id IS NULL OR {calendar_view_clause()}) "
            values["user_id"] = user_id
        result = await self.session.execute(
            text(
                "SELECT ie.id, ie.evento_id, ie.tipo, ie.tema, ie.frequencia, ie.score, "
                "ie.detalhes, ie.gerado_em FROM agenda.insight_evento ie "
                "LEFT JOIN agenda.evento e ON e.id = ie.evento_id "
                "LEFT JOIN agenda.agenda a ON a.id = e.agenda_id "
                "WHERE ie.tenant_id = :tenant_id "
                f"{clause} {calendar_access}ORDER BY ie.frequencia DESC, ie.score DESC, ie.tema"
            ),
            values,
        )
        return [dict(row) for row in result.mappings()]

    async def summary(
        self,
        tenant_id: int,
        start: datetime,
        end: datetime,
        user_id: int,
        calendar_administrator: bool,
    ) -> dict[str, Any]:
        values: dict[str, Any] = {
            "tenant_id": tenant_id,
            "start": start,
            "end": end,
            "user_id": user_id,
        }
        calendar_access = (
            ""
            if calendar_administrator
            else f"AND {calendar_view_clause()} "
        )
        base = (
            "FROM agenda.evento e JOIN agenda.agenda a ON a.id = e.agenda_id "
            "LEFT JOIN agenda.status_evento se ON se.id = e.status_evento_id "
            "LEFT JOIN agenda.tipo_evento te ON te.id = e.tipo_evento_id "
            "WHERE e.tenant_id = :tenant_id AND e.excluido_em IS NULL "
            "AND e.data_inicio >= :start AND e.data_inicio < :end "
            f"{calendar_access}"
        )
        total = int(await self.session.scalar(text("SELECT count(*) " + base), values) or 0)

        async def grouped(expression: str, key: str) -> list[dict[str, Any]]:
            result = await self.session.execute(
                text(
                    f"SELECT {expression}::text AS chave, count(*)::int AS total "
                    + base
                    + f" GROUP BY {expression} ORDER BY {expression}"
                ),
                values,
            )
            return [
                {"chave": str(row[key] or "sem_classificacao"), "total": int(row["total"])}
                for row in result.mappings()
            ]

        return {
            "total": total,
            "por_dia": await grouped("e.data_inicio::date", "chave"),
            "por_status": await grouped("se.codigo", "chave"),
            "por_tipo": await grouped("te.codigo", "chave"),
        }

    async def reference_exists(self, table: str, tenant_id: int, item_id: int) -> bool:
        allowed = {
            "pessoa": ("cadastro.pessoa", "tenant_id = :tenant_id AND ativo"),
            "lideranca": ("cadastro.lideranca", "tenant_id = :tenant_id AND ativo"),
            "territorio": ("territorio.territorio", "tenant_id = :tenant_id AND ativo"),
            "arquivo": ("arquivo.arquivo", "tenant_id = :tenant_id AND excluido_em IS NULL"),
            "endereco": ("cadastro.endereco", "tenant_id = :tenant_id"),
            "categoria_demanda": (
                "demanda.categoria_demanda",
                "(tenant_id IS NULL OR tenant_id = :tenant_id)",
            ),
            "prioridade_demanda": ("demanda.prioridade_demanda", "TRUE"),
            "usuario": ("auth.usuario", "tenant_id = :tenant_id AND status = 'ativo'"),
        }
        sql_table, clause = allowed[table]
        return bool(
            await self.session.scalar(
                text(f"SELECT EXISTS (SELECT 1 FROM {sql_table} WHERE id = :id AND {clause})"),
                {"id": item_id, "tenant_id": tenant_id},
            )
        )

    async def commit(self) -> None:
        await self.session.commit()

    @classmethod
    def _ensure_catalog(cls, table: str) -> None:
        if table not in cls.CATALOG_TABLES:
            raise ValueError("Catalogo de agenda invalido.")
