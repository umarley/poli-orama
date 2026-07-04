"""Acesso a dados do dominio de metas."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repository import BaseRepository
from app.mod_metas.rules import alert_severity
from app.mod_metas.schemas import (
    GoalCreate,
    GoalPeriodCreate,
    GoalPeriodUpdate,
    GoalTargetInput,
    GoalTrackingCreate,
    GoalTypeCreate,
    GoalTypeUpdate,
    GoalUpdate,
    TargetType,
)


class MetaRepository(BaseRepository[object]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_types(
        self, tenant_id: int, include_inactive: bool = False
    ) -> list[dict[str, Any]]:
        active = "" if include_inactive else "AND ativo"
        result = await self.session.execute(
            text(
                "SELECT id, tenant_id, codigo, nome, descricao, ativo "
                "FROM meta.tipo_meta_voto "
                "WHERE (tenant_id IS NULL OR tenant_id = :tenant_id) "
                f"{active} ORDER BY tenant_id NULLS FIRST, nome"
            ),
            {"tenant_id": tenant_id},
        )
        return [dict(row) for row in result.mappings()]

    async def get_type(self, tenant_id: int, type_id: int) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(
                "SELECT id, tenant_id, codigo, nome, descricao, ativo "
                "FROM meta.tipo_meta_voto WHERE id = :id "
                "AND (tenant_id IS NULL OR tenant_id = :tenant_id)"
            ),
            {"id": type_id, "tenant_id": tenant_id},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def create_type(
        self, tenant_id: int, payload: GoalTypeCreate
    ) -> dict[str, Any]:
        result = await self.session.execute(
            text(
                "INSERT INTO meta.tipo_meta_voto "
                "(tenant_id, codigo, nome, descricao) "
                "VALUES (:tenant_id, :codigo, :nome, :descricao) "
                "RETURNING id, tenant_id, codigo, nome, descricao, ativo"
            ),
            {"tenant_id": tenant_id, **payload.model_dump()},
        )
        return dict(result.mappings().one())

    async def update_type(
        self, tenant_id: int, type_id: int, payload: GoalTypeUpdate
    ) -> dict[str, Any] | None:
        values = payload.model_dump(exclude_unset=True)
        if not values:
            return await self.get_type(tenant_id, type_id)
        assignments = ", ".join(f"{key} = :{key}" for key in values)
        result = await self.session.execute(
            text(
                f"UPDATE meta.tipo_meta_voto SET {assignments} "
                "WHERE id = :id AND tenant_id = :tenant_id "
                "RETURNING id, tenant_id, codigo, nome, descricao, ativo"
            ),
            {"id": type_id, "tenant_id": tenant_id, **values},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def list_periods(
        self, tenant_id: int, include_inactive: bool = False
    ) -> list[dict[str, Any]]:
        active = "" if include_inactive else "AND ativo"
        result = await self.session.execute(
            text(
                "SELECT id, tenant_id, nome, data_inicio, data_fim, ciclo, eleicao_id,"
                " ativo, criado_em, atualizado_em FROM meta.periodo_meta "
                f"WHERE tenant_id = :tenant_id {active} "
                "ORDER BY data_inicio DESC, nome"
            ),
            {"tenant_id": tenant_id},
        )
        return [dict(row) for row in result.mappings()]

    async def get_period(self, tenant_id: int, period_id: int) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(
                "SELECT id, tenant_id, nome, data_inicio, data_fim, ciclo, eleicao_id,"
                " ativo, criado_em, atualizado_em FROM meta.periodo_meta "
                "WHERE tenant_id = :tenant_id AND id = :id"
            ),
            {"tenant_id": tenant_id, "id": period_id},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def election_exists(self, tenant_id: int, election_id: int) -> bool:
        return bool(
            await self.session.scalar(
                text(
                    "SELECT EXISTS(SELECT 1 FROM eleicao.eleicao "
                    "WHERE id = :id AND (tenant_id IS NULL OR tenant_id = :tenant_id))"
                ),
                {"id": election_id, "tenant_id": tenant_id},
            )
        )

    async def coordinator_exists(self, tenant_id: int, leader_id: int) -> bool:
        return bool(
            await self.session.scalar(
                text(
                    "SELECT EXISTS(SELECT 1 FROM cadastro.lideranca "
                    "WHERE id = :id AND tenant_id = :tenant_id AND ativo "
                    "AND tipo_lideranca IN "
                    "('coordenador_geral', 'coordenador_territorial'))"
                ),
                {"id": leader_id, "tenant_id": tenant_id},
            )
        )

    async def create_period(
        self, tenant_id: int, payload: GoalPeriodCreate
    ) -> dict[str, Any]:
        result = await self.session.execute(
            text(
                "INSERT INTO meta.periodo_meta "
                "(tenant_id, nome, data_inicio, data_fim, ciclo, eleicao_id) "
                "VALUES (:tenant_id, :nome, :data_inicio, :data_fim, :ciclo, :eleicao_id) "
                "RETURNING id, tenant_id, nome, data_inicio, data_fim, ciclo, eleicao_id,"
                " ativo, criado_em, atualizado_em"
            ),
            {"tenant_id": tenant_id, **payload.model_dump()},
        )
        return dict(result.mappings().one())

    async def update_period(
        self, tenant_id: int, period_id: int, payload: GoalPeriodUpdate
    ) -> dict[str, Any] | None:
        values = payload.model_dump(exclude_unset=True)
        if values:
            assignments = ", ".join(f"{key} = :{key}" for key in values)
            await self.session.execute(
                text(
                    f"UPDATE meta.periodo_meta SET {assignments} "
                    "WHERE id = :id AND tenant_id = :tenant_id"
                ),
                {"id": period_id, "tenant_id": tenant_id, **values},
            )
        return await self.get_period(tenant_id, period_id)

    def _goal_scope_clause(self, accessible_ids: set[int] | None) -> str:
        if accessible_ids is None:
            return ""
        return """
            AND (
                m.territorio_id = ANY(:accessible_ids)
                OR EXISTS (
                    SELECT 1 FROM meta.meta_voto_alvo scope_target
                    WHERE scope_target.meta_voto_id = m.id
                      AND scope_target.tipo_alvo = 'territorio'
                      AND scope_target.alvo_id = ANY(:accessible_ids)
                )
                OR EXISTS (
                    SELECT 1
                    FROM meta.meta_voto_alvo scope_target
                    JOIN territorio.lideranca_territorio lt
                      ON scope_target.tipo_alvo = 'lideranca'
                     AND lt.lideranca_id = scope_target.alvo_id
                     AND lt.tenant_id = m.tenant_id
                    WHERE scope_target.meta_voto_id = m.id
                      AND lt.territorio_id = ANY(:accessible_ids)
                )
                OR EXISTS (
                    SELECT 1
                    FROM auth.usuario scope_user
                    JOIN cadastro.lideranca own_leader
                      ON own_leader.pessoa_id = scope_user.pessoa_id
                     AND own_leader.tenant_id = m.tenant_id
                    LEFT JOIN meta.meta_voto_alvo own_target
                      ON own_target.meta_voto_id = m.id
                     AND own_target.tipo_alvo = 'lideranca'
                    WHERE scope_user.id = :user_id
                      AND scope_user.tenant_id = m.tenant_id
                      AND (m.lideranca_id = own_leader.id
                           OR own_target.alvo_id = own_leader.id)
                )
            )
        """

    async def list_goals(
        self,
        tenant_id: int,
        user_id: int,
        *,
        territory_id: int | None,
        leader_id: int | None,
        period_id: int | None,
        status: str | None,
        accessible_ids: set[int] | None,
    ) -> list[dict[str, Any]]:
        if accessible_ids is not None and not accessible_ids:
            accessible_ids = {-1}
        clauses = ["m.tenant_id = :tenant_id"]
        values: dict[str, Any] = {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "accessible_ids": sorted(accessible_ids or {-1}),
        }
        if territory_id:
            clauses.append(
                "(m.territorio_id = :territory_id OR EXISTS ("
                "SELECT 1 FROM meta.meta_voto_alvo fta WHERE fta.meta_voto_id = m.id "
                "AND fta.tipo_alvo = 'territorio' AND fta.alvo_id = :territory_id))"
            )
            values["territory_id"] = territory_id
        if leader_id:
            clauses.append(
                "(m.lideranca_id = :leader_id OR EXISTS ("
                "SELECT 1 FROM meta.meta_voto_alvo fla WHERE fla.meta_voto_id = m.id "
                "AND fla.tipo_alvo = 'lideranca' AND fla.alvo_id = :leader_id))"
            )
            values["leader_id"] = leader_id
        if period_id:
            clauses.append("m.periodo_meta_id = :period_id")
            values["period_id"] = period_id
        if status:
            clauses.append("m.status = :status")
            values["status"] = status
        result = await self.session.execute(
            text(
                "SELECT m.id, m.tenant_id, m.tipo_meta_voto_id, tm.codigo AS tipo_codigo,"
                " tm.nome AS tipo_nome, m.periodo_meta_id, pm.nome AS periodo_nome,"
                " m.titulo, m.quantidade_meta, m.coordenador_id, m.territorio_id,"
                " m.lideranca_id, m.status, m.criado_por, m.score_risco,"
                " m.fatores_risco, m.criado_em, m.atualizado_em"
                " FROM meta.meta_voto m"
                " JOIN meta.tipo_meta_voto tm ON tm.id = m.tipo_meta_voto_id"
                " JOIN meta.periodo_meta pm ON pm.id = m.periodo_meta_id"
                f" WHERE {' AND '.join(clauses)}"
                f" {self._goal_scope_clause(accessible_ids)}"
                " ORDER BY m.atualizado_em DESC, m.id DESC"
            ),
            values,
        )
        return [dict(row) for row in result.mappings()]

    async def get_goal(
        self, tenant_id: int, goal_id: int
    ) -> dict[str, Any] | None:
        result = await self.session.execute(
            text(
                "SELECT m.id, m.tenant_id, m.tipo_meta_voto_id, tm.codigo AS tipo_codigo,"
                " tm.nome AS tipo_nome, m.periodo_meta_id, pm.nome AS periodo_nome,"
                " m.titulo, m.quantidade_meta, m.coordenador_id, m.territorio_id,"
                " m.lideranca_id, m.status, m.criado_por, m.score_risco,"
                " m.fatores_risco, m.criado_em, m.atualizado_em"
                " FROM meta.meta_voto m"
                " JOIN meta.tipo_meta_voto tm ON tm.id = m.tipo_meta_voto_id"
                " JOIN meta.periodo_meta pm ON pm.id = m.periodo_meta_id"
                " WHERE m.tenant_id = :tenant_id AND m.id = :id"
            ),
            {"tenant_id": tenant_id, "id": goal_id},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def create_goal(
        self, tenant_id: int, user_id: int, payload: GoalCreate
    ) -> int:
        goal_id = int(
            await self.session.scalar(
                text(
                    "INSERT INTO meta.meta_voto "
                    "(tenant_id, tipo_meta_voto_id, periodo_meta_id, titulo,"
                    " quantidade_meta, coordenador_id, criado_por) "
                    "VALUES (:tenant_id, :tipo_meta_voto_id, :periodo_meta_id, :titulo,"
                    " :quantidade_meta, :coordenador_id, :user_id) RETURNING id"
                ),
                {
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    **payload.model_dump(exclude={"alvos"}),
                },
            )
        )
        await self.replace_targets(tenant_id, goal_id, payload.alvos)
        await self.sync_primary_targets(tenant_id, goal_id)
        return goal_id

    async def update_goal(
        self, tenant_id: int, goal_id: int, payload: GoalUpdate
    ) -> None:
        values = payload.model_dump(exclude_unset=True, exclude={"alvos"})
        if values:
            assignments = ", ".join(f"{key} = :{key}" for key in values)
            await self.session.execute(
                text(
                    f"UPDATE meta.meta_voto SET {assignments} "
                    "WHERE id = :id AND tenant_id = :tenant_id"
                ),
                {"id": goal_id, "tenant_id": tenant_id, **values},
            )
        if payload.alvos is not None:
            await self.replace_targets(tenant_id, goal_id, payload.alvos)
            await self.sync_primary_targets(tenant_id, goal_id)

    async def replace_targets(
        self, tenant_id: int, goal_id: int, targets: list[GoalTargetInput]
    ) -> None:
        await self.session.execute(
            text(
                "DELETE FROM meta.meta_voto_alvo "
                "WHERE tenant_id = :tenant_id AND meta_voto_id = :goal_id"
            ),
            {"tenant_id": tenant_id, "goal_id": goal_id},
        )
        for target in targets:
            await self.session.execute(
                text(
                    "INSERT INTO meta.meta_voto_alvo "
                    "(tenant_id, meta_voto_id, tipo_alvo, alvo_id, quantidade_atribuida) "
                    "VALUES (:tenant_id, :goal_id, :tipo_alvo, :alvo_id,"
                    " :quantidade_atribuida)"
                ),
                {"tenant_id": tenant_id, "goal_id": goal_id, **target.model_dump()},
            )

    async def sync_primary_targets(self, tenant_id: int, goal_id: int) -> None:
        await self.session.execute(
            text(
                "UPDATE meta.meta_voto m SET "
                " lideranca_id = (SELECT alvo_id FROM meta.meta_voto_alvo "
                "   WHERE meta_voto_id = m.id AND tipo_alvo = 'lideranca' LIMIT 1),"
                " territorio_id = (SELECT alvo_id FROM meta.meta_voto_alvo "
                "   WHERE meta_voto_id = m.id AND tipo_alvo = 'territorio' LIMIT 1),"
                " comunidade_id = (SELECT alvo_id FROM meta.meta_voto_alvo "
                "   WHERE meta_voto_id = m.id AND tipo_alvo = 'comunidade' LIMIT 1),"
                " nucleo_familiar_id = (SELECT alvo_id FROM meta.meta_voto_alvo "
                "   WHERE meta_voto_id = m.id AND tipo_alvo = 'nucleo_familiar' LIMIT 1)"
                " WHERE m.id = :goal_id AND m.tenant_id = :tenant_id"
            ),
            {"tenant_id": tenant_id, "goal_id": goal_id},
        )

    async def list_targets(
        self, tenant_id: int, goal_id: int
    ) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text(
                "SELECT id, tenant_id, meta_voto_id, tipo_alvo, alvo_id,"
                " quantidade_atribuida, criado_em FROM meta.meta_voto_alvo "
                "WHERE tenant_id = :tenant_id AND meta_voto_id = :goal_id "
                "ORDER BY id"
            ),
            {"tenant_id": tenant_id, "goal_id": goal_id},
        )
        targets = [dict(row) for row in result.mappings()]
        for target in targets:
            target["nome_alvo"] = await self.target_name(
                tenant_id, target["tipo_alvo"], target["alvo_id"]
            )
        return targets

    async def target_name(
        self, tenant_id: int, target_type: str, target_id: int
    ) -> str | None:
        queries = {
            "lideranca": (
                "SELECT COALESCE(l.apelido_campanha, p.nome_completo) "
                "FROM cadastro.lideranca l JOIN cadastro.pessoa p ON p.id = l.pessoa_id "
                "WHERE l.id = :id AND l.tenant_id = :tenant_id"
            ),
            "territorio": (
                "SELECT nome FROM territorio.territorio "
                "WHERE id = :id AND tenant_id = :tenant_id"
            ),
            "equipe": (
                "SELECT nome FROM cadastro.equipe "
                "WHERE id = :id AND tenant_id = :tenant_id"
            ),
            "comunidade": (
                "SELECT nome FROM cadastro.comunidade "
                "WHERE id = :id AND tenant_id = :tenant_id"
            ),
            "nucleo_familiar": (
                "SELECT COALESCE(nome, 'Nucleo ' || id::text) "
                "FROM cadastro.nucleo_familiar "
                "WHERE id = :id AND tenant_id = :tenant_id"
            ),
            "pessoa": (
                "SELECT nome_completo FROM cadastro.pessoa "
                "WHERE id = :id AND tenant_id = :tenant_id"
            ),
        }
        query = queries.get(target_type)
        if not query:
            return None
        value = await self.session.scalar(
            text(query), {"id": target_id, "tenant_id": tenant_id}
        )
        return str(value) if value is not None else None

    async def target_exists(
        self, tenant_id: int, target_type: TargetType, target_id: int
    ) -> bool:
        return await self.target_name(tenant_id, target_type, target_id) is not None

    async def target_is_accessible(
        self,
        tenant_id: int,
        target_type: TargetType,
        target_id: int,
        accessible_ids: set[int] | None,
    ) -> bool:
        if accessible_ids is None:
            return True
        if not accessible_ids:
            return False
        if target_type == "territorio":
            return target_id in accessible_ids
        queries = {
            "lideranca": (
                "SELECT EXISTS(SELECT 1 FROM territorio.lideranca_territorio "
                "WHERE tenant_id = :tenant_id AND lideranca_id = :target_id "
                "AND territorio_id = ANY(:accessible_ids))"
            ),
            "pessoa": (
                "SELECT EXISTS(SELECT 1 FROM territorio.pessoa_territorio "
                "WHERE tenant_id = :tenant_id AND pessoa_id = :target_id "
                "AND territorio_id = ANY(:accessible_ids))"
            ),
            "equipe": (
                "SELECT EXISTS(SELECT 1 FROM cadastro.equipe_pessoa ep "
                "JOIN territorio.pessoa_territorio pt ON pt.pessoa_id = ep.pessoa_id "
                "AND pt.tenant_id = ep.tenant_id "
                "WHERE ep.tenant_id = :tenant_id AND ep.equipe_id = :target_id "
                "AND pt.territorio_id = ANY(:accessible_ids))"
            ),
            "comunidade": (
                "SELECT EXISTS(SELECT 1 FROM cadastro.pessoa_comunidade pc "
                "JOIN territorio.pessoa_territorio pt ON pt.pessoa_id = pc.pessoa_id "
                "AND pt.tenant_id = pc.tenant_id "
                "WHERE pc.tenant_id = :tenant_id AND pc.comunidade_id = :target_id "
                "AND pt.territorio_id = ANY(:accessible_ids))"
            ),
            "nucleo_familiar": (
                "SELECT EXISTS(SELECT 1 FROM cadastro.pessoa_nucleo_familiar pn "
                "JOIN territorio.pessoa_territorio pt ON pt.pessoa_id = pn.pessoa_id "
                "AND pt.tenant_id = pn.tenant_id "
                "WHERE pn.tenant_id = :tenant_id AND pn.nucleo_familiar_id = :target_id "
                "AND pt.territorio_id = ANY(:accessible_ids))"
            ),
        }
        return bool(
            await self.session.scalar(
                text(queries[target_type]),
                {
                    "tenant_id": tenant_id,
                    "target_id": target_id,
                    "accessible_ids": sorted(accessible_ids),
                },
            )
        )

    async def visible_leader_ids(
        self,
        tenant_id: int,
        user_id: int,
        accessible_ids: set[int] | None,
    ) -> set[int] | None:
        if accessible_ids is None:
            return None
        result = await self.session.scalars(
            text(
                "SELECT DISTINCT l.id FROM cadastro.lideranca l "
                "LEFT JOIN territorio.lideranca_territorio lt "
                "ON lt.lideranca_id = l.id AND lt.tenant_id = l.tenant_id "
                "LEFT JOIN auth.usuario u ON u.pessoa_id = l.pessoa_id "
                "AND u.tenant_id = l.tenant_id AND u.id = :user_id "
                "WHERE l.tenant_id = :tenant_id AND l.ativo "
                "AND (lt.territorio_id = ANY(:accessible_ids) OR u.id IS NOT NULL)"
            ),
            {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "accessible_ids": sorted(accessible_ids or {-1}),
            },
        )
        return {int(value) for value in result}

    async def target_person_ids(
        self, tenant_id: int, target_type: str, target_id: int
    ) -> set[int]:
        queries = {
            "lideranca": (
                "SELECT pessoa_subordinada_id FROM cadastro.hierarquia_lideranca "
                "WHERE tenant_id = :tenant_id AND lideranca_superior_id = :id AND ativo"
            ),
            "territorio": (
                "WITH RECURSIVE tree AS (SELECT CAST(:id AS bigint) AS id UNION ALL "
                "SELECT h.territorio_filho_id FROM territorio.territorio_hierarquia h "
                "JOIN tree t ON t.id = h.territorio_pai_id "
                "WHERE h.tenant_id = :tenant_id) "
                "SELECT DISTINCT pt.pessoa_id FROM territorio.pessoa_territorio pt "
                "WHERE pt.tenant_id = :tenant_id AND pt.territorio_id IN (SELECT id FROM tree)"
            ),
            "equipe": (
                "SELECT pessoa_id FROM cadastro.equipe_pessoa "
                "WHERE tenant_id = :tenant_id AND equipe_id = :id"
            ),
            "comunidade": (
                "SELECT pessoa_id FROM cadastro.pessoa_comunidade "
                "WHERE tenant_id = :tenant_id AND comunidade_id = :id"
            ),
            "nucleo_familiar": (
                "SELECT pessoa_id FROM cadastro.pessoa_nucleo_familiar "
                "WHERE tenant_id = :tenant_id AND nucleo_familiar_id = :id"
            ),
            "pessoa": (
                "SELECT id FROM cadastro.pessoa "
                "WHERE tenant_id = :tenant_id AND id = :id AND ativo"
            ),
        }
        result = await self.session.scalars(
            text(queries[target_type]), {"tenant_id": tenant_id, "id": target_id}
        )
        return {int(identifier) for identifier in result}

    async def global_person_ids(self, tenant_id: int) -> set[int]:
        result = await self.session.scalars(
            text(
                "SELECT id FROM cadastro.pessoa WHERE tenant_id = :tenant_id "
                "AND ativo AND excluido_em IS NULL"
            ),
            {"tenant_id": tenant_id},
        )
        return {int(identifier) for identifier in result}

    async def average_person_engagement(
        self, tenant_id: int, person_ids: set[int]
    ) -> Decimal:
        if not person_ids:
            return Decimal("0")
        result = await self.session.execute(
            text(
                "SELECT COALESCE(avg(nivel_engajamento), 0)::numeric "
                "FROM cadastro.pessoa "
                "WHERE tenant_id = :tenant_id AND id = ANY(:person_ids)"
            ),
            {"tenant_id": tenant_id, "person_ids": list(person_ids)},
        )
        return Decimal(str(result.scalar_one()))

    async def list_tracking(
        self, tenant_id: int, goal_id: int
    ) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text(
                "SELECT id, tenant_id, meta_voto_id, data_referencia,"
                " quantidade_projetada, quantidade_confirmada,"
                " COALESCE(quantidade_eleitores_vinculados, 0)"
                " AS quantidade_eleitores_vinculados,"
                " COALESCE(percentual_atingido, 0) AS percentual_atingido,"
                " situacao_risco, observacao, criado_por, criado_em"
                " FROM meta.acompanhamento_meta "
                "WHERE tenant_id = :tenant_id AND meta_voto_id = :goal_id "
                "ORDER BY data_referencia DESC, id DESC"
            ),
            {"tenant_id": tenant_id, "goal_id": goal_id},
        )
        return [dict(row) for row in result.mappings()]

    async def upsert_tracking(
        self,
        tenant_id: int,
        user_id: int,
        goal_id: int,
        payload: GoalTrackingCreate,
        *,
        base_count: int,
        percentage: Decimal,
        risk_status: str,
    ) -> dict[str, Any]:
        result = await self.session.execute(
            text(
                "INSERT INTO meta.acompanhamento_meta "
                "(tenant_id, meta_voto_id, data_referencia, quantidade_projetada,"
                " quantidade_confirmada, quantidade_eleitores_vinculados,"
                " percentual_atingido, situacao_risco, observacao, criado_por) "
                "VALUES (:tenant_id, :goal_id, :data_referencia, :quantidade_projetada,"
                " :quantidade_confirmada, :base_count, :percentage, :risk_status,"
                " :observacao, :user_id) "
                "ON CONFLICT (meta_voto_id, data_referencia) DO UPDATE SET "
                " quantidade_projetada = EXCLUDED.quantidade_projetada,"
                " quantidade_confirmada = EXCLUDED.quantidade_confirmada,"
                " quantidade_eleitores_vinculados = EXCLUDED.quantidade_eleitores_vinculados,"
                " percentual_atingido = EXCLUDED.percentual_atingido,"
                " situacao_risco = EXCLUDED.situacao_risco,"
                " observacao = EXCLUDED.observacao, criado_por = EXCLUDED.criado_por "
                "RETURNING id, tenant_id, meta_voto_id, data_referencia,"
                " quantidade_projetada, quantidade_confirmada,"
                " quantidade_eleitores_vinculados, percentual_atingido,"
                " situacao_risco, observacao, criado_por, criado_em"
            ),
            {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "goal_id": goal_id,
                "base_count": base_count,
                "percentage": percentage,
                "risk_status": risk_status,
                **payload.model_dump(),
            },
        )
        return dict(result.mappings().one())

    async def list_alerts(
        self, tenant_id: int, goal_id: int
    ) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text(
                "SELECT id, tenant_id, meta_voto_id, tipo_alerta,"
                " percentual_referencia, mensagem, severidade, resolvido,"
                " gerado_em, resolvido_em FROM meta.alerta_meta "
                "WHERE tenant_id = :tenant_id AND meta_voto_id = :goal_id "
                "ORDER BY resolvido, gerado_em DESC"
            ),
            {"tenant_id": tenant_id, "goal_id": goal_id},
        )
        return [dict(row) for row in result.mappings()]

    async def sync_risk_alert(
        self,
        tenant_id: int,
        goal_id: int,
        percentage: Decimal,
        threshold: Decimal,
        risk_status: str,
    ) -> dict[str, Any] | None:
        existing_result = await self.session.execute(
            text(
                "SELECT id, percentual_referencia, mensagem, severidade, resolvido "
                "FROM meta.alerta_meta WHERE tenant_id = :tenant_id "
                "AND meta_voto_id = :goal_id "
                "AND tipo_alerta = 'meta_abaixo_esperado' AND NOT resolvido"
            ),
            {"tenant_id": tenant_id, "goal_id": goal_id},
        )
        existing_row = existing_result.mappings().first()
        existing = dict(existing_row) if existing_row else None
        if percentage < threshold:
            severity = alert_severity(risk_status)
            result = await self.session.execute(
                text(
                    "INSERT INTO meta.alerta_meta "
                    "(tenant_id, meta_voto_id, tipo_alerta, percentual_referencia,"
                    " mensagem, severidade) "
                    "VALUES (:tenant_id, :goal_id, 'meta_abaixo_esperado', :percentage,"
                    " :message, :severity) "
                    "ON CONFLICT (meta_voto_id, tipo_alerta) WHERE resolvido = FALSE "
                    "DO UPDATE SET percentual_referencia = EXCLUDED.percentual_referencia,"
                    " mensagem = EXCLUDED.mensagem, severidade = EXCLUDED.severidade,"
                    " atualizado_em = now() "
                    "RETURNING id, percentual_referencia, mensagem, severidade, resolvido"
                ),
                {
                    "tenant_id": tenant_id,
                    "goal_id": goal_id,
                    "percentage": percentage,
                    "message": (
                        f"Meta em {percentage:.2f}%, abaixo do limiar de {threshold:.2f}%."
                    ),
                    "severity": severity,
                },
            )
            current = dict(result.mappings().one())
            if existing == current:
                return None
            return {
                "action": "editar" if existing else "criar",
                "id": current["id"],
                "before": existing,
                "after": current,
            }
        if existing:
            result = await self.session.execute(
                text(
                    "UPDATE meta.alerta_meta SET resolvido = TRUE, resolvido_em = now() "
                    "WHERE tenant_id = :tenant_id AND meta_voto_id = :goal_id "
                    "AND tipo_alerta = 'meta_abaixo_esperado' AND NOT resolvido "
                    "RETURNING id, percentual_referencia, mensagem, severidade, resolvido"
                ),
                {"tenant_id": tenant_id, "goal_id": goal_id},
            )
            current = dict(result.mappings().one())
            return {
                "action": "editar",
                "id": current["id"],
                "before": existing,
                "after": current,
            }
        return None

    async def risk_threshold(self, tenant_id: int) -> Decimal:
        value = await self.session.scalar(
            text(
                "SELECT COALESCE(percentual_alerta_meta, 70) "
                "FROM public.tenant_configuracao WHERE tenant_id = :tenant_id"
            ),
            {"tenant_id": tenant_id},
        )
        return Decimal(str(value if value is not None else 70))

    async def update_predictive_risk(
        self,
        tenant_id: int,
        goal_id: int,
        score: Decimal,
        factors: dict[str, Any],
        status: str,
    ) -> None:
        await self.session.execute(
            text(
                "UPDATE meta.meta_voto SET score_risco = :score,"
                " fatores_risco = CAST(:factors AS jsonb), risco_calculado_em = now(),"
                " status = CASE WHEN status = 'ativa' AND :at_risk THEN 'em_risco' "
                "WHEN status = 'em_risco' AND NOT :at_risk THEN 'ativa' ELSE status END "
                "WHERE tenant_id = :tenant_id AND id = :goal_id"
            ),
            {
                "tenant_id": tenant_id,
                "goal_id": goal_id,
                "score": score,
                "factors": json.dumps(factors, default=str),
                "at_risk": status != "normal",
            },
        )

    async def target_options(
        self,
        tenant_id: int,
        target_type: TargetType,
        query: str | None,
        accessible_ids: set[int] | None,
    ) -> list[dict[str, Any]]:
        if accessible_ids is not None and not accessible_ids:
            return []
        term = f"%{query or ''}%"
        queries = {
            "lideranca": (
                "SELECT l.id, COALESCE(l.apelido_campanha, p.nome_completo) AS nome "
                "FROM cadastro.lideranca l JOIN cadastro.pessoa p ON p.id = l.pessoa_id "
                "WHERE l.tenant_id = :tenant_id AND l.ativo "
                "AND COALESCE(l.apelido_campanha, p.nome_completo) ILIKE :term"
            ),
            "territorio": (
                "SELECT id, nome FROM territorio.territorio "
                "WHERE tenant_id = :tenant_id AND ativo AND nome ILIKE :term"
            ),
            "equipe": (
                "SELECT id, nome FROM cadastro.equipe "
                "WHERE tenant_id = :tenant_id AND ativo AND nome ILIKE :term"
            ),
            "comunidade": (
                "SELECT id, nome FROM cadastro.comunidade "
                "WHERE tenant_id = :tenant_id AND nome ILIKE :term"
            ),
            "nucleo_familiar": (
                "SELECT id, COALESCE(nome, 'Nucleo ' || id::text) AS nome "
                "FROM cadastro.nucleo_familiar "
                "WHERE tenant_id = :tenant_id "
                "AND COALESCE(nome, 'Nucleo ' || id::text) ILIKE :term"
            ),
            "pessoa": (
                "SELECT id, nome_completo AS nome FROM cadastro.pessoa "
                "WHERE tenant_id = :tenant_id AND ativo AND excluido_em IS NULL "
                "AND nome_completo ILIKE :term"
            ),
        }
        scope_clauses = {
            "lideranca": (
                " AND EXISTS (SELECT 1 FROM territorio.lideranca_territorio lt "
                "WHERE lt.tenant_id = l.tenant_id AND lt.lideranca_id = l.id "
                "AND lt.territorio_id = ANY(:accessible_ids))"
            ),
            "territorio": " AND id = ANY(:accessible_ids)",
            "equipe": (
                " AND EXISTS (SELECT 1 FROM cadastro.equipe_pessoa ep "
                "JOIN territorio.pessoa_territorio pt ON pt.pessoa_id = ep.pessoa_id "
                "AND pt.tenant_id = ep.tenant_id WHERE ep.tenant_id = :tenant_id "
                "AND ep.equipe_id = cadastro.equipe.id "
                "AND pt.territorio_id = ANY(:accessible_ids))"
            ),
            "comunidade": (
                " AND EXISTS (SELECT 1 FROM cadastro.pessoa_comunidade pc "
                "JOIN territorio.pessoa_territorio pt ON pt.pessoa_id = pc.pessoa_id "
                "AND pt.tenant_id = pc.tenant_id WHERE pc.tenant_id = :tenant_id "
                "AND pc.comunidade_id = cadastro.comunidade.id "
                "AND pt.territorio_id = ANY(:accessible_ids))"
            ),
            "nucleo_familiar": (
                " AND EXISTS (SELECT 1 FROM cadastro.pessoa_nucleo_familiar pn "
                "JOIN territorio.pessoa_territorio pt ON pt.pessoa_id = pn.pessoa_id "
                "AND pt.tenant_id = pn.tenant_id WHERE pn.tenant_id = :tenant_id "
                "AND pn.nucleo_familiar_id = cadastro.nucleo_familiar.id "
                "AND pt.territorio_id = ANY(:accessible_ids))"
            ),
            "pessoa": (
                " AND EXISTS (SELECT 1 FROM territorio.pessoa_territorio pt "
                "WHERE pt.tenant_id = cadastro.pessoa.tenant_id "
                "AND pt.pessoa_id = cadastro.pessoa.id "
                "AND pt.territorio_id = ANY(:accessible_ids))"
            ),
        }
        sql = queries[target_type]
        values: dict[str, Any] = {"tenant_id": tenant_id, "term": term}
        if accessible_ids is not None:
            sql += scope_clauses[target_type]
            values["accessible_ids"] = sorted(accessible_ids)
        result = await self.session.execute(
            text(sql + " ORDER BY nome LIMIT 100"),
            values,
        )
        return [
            {"id": int(row["id"]), "nome": str(row["nome"]), "tipo": target_type}
            for row in result.mappings()
        ]

    async def replace_ranking(
        self, tenant_id: int, ranking_date: date, rows: list[dict[str, Any]]
    ) -> None:
        await self.session.execute(
            text(
                "DELETE FROM meta.ranking_lideranca "
                "WHERE tenant_id = :tenant_id AND data_referencia = :ranking_date"
            ),
            {"tenant_id": tenant_id, "ranking_date": ranking_date},
        )
        for row in rows:
            await self.session.execute(
                text(
                    "INSERT INTO meta.ranking_lideranca "
                    "(tenant_id, lideranca_id, data_referencia, posicao,"
                    " total_cadastros, total_confirmacoes, total_eventos,"
                    " total_demandas, percentual_meta, pontuacao) "
                    "VALUES (:tenant_id, :lideranca_id, :ranking_date, :posicao,"
                    " :total_cadastros, :total_confirmacoes, :total_eventos,"
                    " :total_demandas, :percentual_meta, :pontuacao)"
                ),
                {"tenant_id": tenant_id, "ranking_date": ranking_date, **row},
            )

    async def ranking_metrics(self, tenant_id: int) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text(
                "SELECT l.id AS lideranca_id,"
                " COALESCE(l.apelido_campanha, p.nome_completo) AS nome_lideranca,"
                " count(DISTINCT hl.pessoa_subordinada_id)::int AS total_cadastros,"
                " COALESCE(avg(subordinate.nivel_engajamento), 0)::numeric AS engajamento,"
                " count(DISTINCT el.evento_id)::int AS total_eventos,"
                " count(DISTINCT d.id)::int AS total_demandas"
                " FROM cadastro.lideranca l"
                " JOIN cadastro.pessoa p ON p.id = l.pessoa_id"
                " LEFT JOIN cadastro.hierarquia_lideranca hl"
                " ON hl.lideranca_superior_id = l.id AND hl.tenant_id = l.tenant_id AND hl.ativo"
                " LEFT JOIN cadastro.pessoa subordinate"
                " ON subordinate.id = hl.pessoa_subordinada_id"
                " LEFT JOIN agenda.evento_lideranca el"
                " ON el.lideranca_id = l.id AND el.tenant_id = l.tenant_id"
                " LEFT JOIN demanda.demanda d"
                " ON d.lideranca_indicacao_id = l.id AND d.tenant_id = l.tenant_id"
                " WHERE l.tenant_id = :tenant_id AND l.ativo"
                " GROUP BY l.id, p.nome_completo ORDER BY l.id"
            ),
            {"tenant_id": tenant_id},
        )
        return [dict(row) for row in result.mappings()]

    async def list_ranking(
        self, tenant_id: int, ranking_date: date | None = None
    ) -> list[dict[str, Any]]:
        result = await self.session.execute(
            text(
                "SELECT r.id, r.lideranca_id,"
                " COALESCE(l.apelido_campanha, p.nome_completo) AS nome_lideranca,"
                " r.data_referencia, r.posicao, r.total_cadastros,"
                " r.total_confirmacoes, r.total_eventos, r.total_demandas,"
                " COALESCE(r.percentual_meta, 0) AS percentual_meta,"
                " COALESCE(r.pontuacao, 0) AS pontuacao"
                " FROM meta.ranking_lideranca r"
                " JOIN cadastro.lideranca l ON l.id = r.lideranca_id"
                " JOIN cadastro.pessoa p ON p.id = l.pessoa_id"
                " WHERE r.tenant_id = :tenant_id AND r.data_referencia = COALESCE("
                " :ranking_date, (SELECT max(data_referencia)"
                " FROM meta.ranking_lideranca WHERE tenant_id = :tenant_id))"
                " ORDER BY r.posicao"
            ),
            {"tenant_id": tenant_id, "ranking_date": ranking_date},
        )
        return [dict(row) for row in result.mappings()]

    async def cancel_goal(self, tenant_id: int, goal_id: int) -> bool:
        result = await self.session.execute(
            text(
                "UPDATE meta.meta_voto SET status = 'cancelada' "
                "WHERE tenant_id = :tenant_id AND id = :id AND status <> 'cancelada'"
            ),
            {"tenant_id": tenant_id, "id": goal_id},
        )
        return bool(cast(CursorResult[Any], result).rowcount)

    async def commit(self) -> None:
        await self.session.commit()
