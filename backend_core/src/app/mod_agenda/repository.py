"""Persistencia do dominio de agenda."""

from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.mod_agenda.schemas import (
    AgendaItemInput,
    AttendanceInput,
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

    async def get_catalog(
        self, table: str, tenant_id: int, item_id: int
    ) -> dict[str, Any] | None:
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
        accessible_ids: set[int] | None,
    ) -> list[dict[str, Any]]:
        clauses = ["e.tenant_id = :tenant_id", "e.excluido_em IS NULL"]
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
        if accessible_ids is not None:
            if not accessible_ids:
                return []
            clauses.append("e.territorio_id = ANY(:accessible_ids)")
            values["accessible_ids"] = list(accessible_ids)
        result = await self.session.execute(
            text(
                self._event_select()
                + " WHERE "
                + " AND ".join(clauses)
                + " ORDER BY e.data_inicio"
            ),
            values,
        )
        return [dict(row) for row in result.mappings()]

    async def get_event(self, tenant_id: int, event_id: int) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(
                self._event_select()
                + " WHERE e.tenant_id = :tenant_id AND e.id = :id "
                "AND e.excluido_em IS NULL"
            ),
            {"tenant_id": tenant_id, "id": event_id},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    @staticmethod
    def _event_select() -> str:
        return (
            "SELECT e.id, e.tenant_id, e.contexto, e.campanha_eleicao_id, "
            "e.tipo_evento_id, te.nome AS tipo_evento_nome, "
            "e.status_evento_id, se.codigo AS status_evento_codigo, "
            "se.nome AS status_evento_nome, e.titulo, e.descricao, e.data_inicio, "
            "e.data_fim, e.local_nome, e.endereco_id, e.codigo_municipio_ibge, e.bairro_id, "
            "e.zona_eleitoral_id, e.territorio_id, t.nome AS territorio_nome, "
            "e.latitude, e.longitude, e.responsavel_pessoa_id, "
            "p.nome_completo AS responsavel_nome, e.motivo_cancelamento, "
            "e.cancelado_em, e.criado_em, e.atualizado_em FROM agenda.evento e "
            "LEFT JOIN agenda.tipo_evento te ON te.id = e.tipo_evento_id "
            "LEFT JOIN agenda.status_evento se ON se.id = e.status_evento_id "
            "LEFT JOIN territorio.territorio t ON t.id = e.territorio_id "
            "JOIN cadastro.pessoa p ON p.id = e.responsavel_pessoa_id "
        )

    async def create_event(
        self, tenant_id: int, user_id: int, payload: EventInput
    ) -> int:
        values = payload.model_dump()
        result = await self.session.execute(
            text(
                "INSERT INTO agenda.evento "
                "(tenant_id, contexto, campanha_eleicao_id, tipo_evento_id, "
                "status_evento_id, titulo, descricao, "
                "data_inicio, data_fim, local_nome, endereco_id, codigo_municipio_ibge, "
                "bairro_id, zona_eleitoral_id, territorio_id, latitude, longitude, "
                "responsavel_pessoa_id, criado_por) VALUES "
                "(:tenant_id, :contexto, :campanha_eleicao_id, :tipo_evento_id, "
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

    async def update_event(
        self, tenant_id: int, event_id: int, payload: EventUpdate
    ) -> bool:
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

    async def cancel_event(
        self, tenant_id: int, event_id: int, user_id: int, reason: str
    ) -> bool:
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

    async def delete_participant(
        self, tenant_id: int, event_id: int, person_id: int
    ) -> None:
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

    async def delete_leadership(
        self, tenant_id: int, event_id: int, leadership_id: int
    ) -> None:
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
        self, tenant_id: int, event_id: int | None = None
    ) -> list[dict[str, Any]]:
        clause = "AND (evento_id = :event_id OR evento_id IS NULL)" if event_id else ""
        result = await self.session.execute(
            text(
                "SELECT id, evento_id, tipo, tema, frequencia, score, detalhes, gerado_em "
                "FROM agenda.insight_evento WHERE tenant_id = :tenant_id "
                f"{clause} ORDER BY frequencia DESC, score DESC, tema"
            ),
            {"tenant_id": tenant_id, "event_id": event_id},
        )
        return [dict(row) for row in result.mappings()]

    async def summary(
        self,
        tenant_id: int,
        start: datetime,
        end: datetime,
        accessible_ids: set[int] | None,
    ) -> dict[str, Any]:
        access = ""
        values: dict[str, Any] = {
            "tenant_id": tenant_id,
            "start": start,
            "end": end,
        }
        if accessible_ids is not None:
            if not accessible_ids:
                return {"total": 0, "por_dia": [], "por_status": [], "por_tipo": []}
            access = "AND e.territorio_id = ANY(:accessible_ids)"
            values["accessible_ids"] = list(accessible_ids)
        base = (
            "FROM agenda.evento e "
            "LEFT JOIN agenda.status_evento se ON se.id = e.status_evento_id "
            "LEFT JOIN agenda.tipo_evento te ON te.id = e.tipo_evento_id "
            "WHERE e.tenant_id = :tenant_id AND e.excluido_em IS NULL "
            "AND e.data_inicio >= :start AND e.data_inicio < :end "
            f"{access}"
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
