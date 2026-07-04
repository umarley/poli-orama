"""Regras de negocio do dominio de metas."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from fastapi.encoders import jsonable_encoder

from app.audit.service import AuditService
from app.auth.access import RequestActor, TerritorialAccess
from app.core.errors import AuthorizationError, BusinessRuleError, ResourceNotFoundError
from app.mod_metas.repository import MetaRepository
from app.mod_metas.rules import (
    ACTIVE_GOAL_STATUSES,
    ranking_score,
)
from app.mod_metas.rules import (
    percentage as calculate_percentage,
)
from app.mod_metas.rules import (
    predictive_risk_score as calculate_predictive_risk_score,
)
from app.mod_metas.rules import (
    risk_status as calculate_risk_status,
)
from app.mod_metas.schemas import (
    GoalCreate,
    GoalDetailResponse,
    GoalPeriodCreate,
    GoalPeriodUpdate,
    GoalResponse,
    GoalSummaryResponse,
    GoalTargetInput,
    GoalTrackingCreate,
    GoalTrackingResponse,
    GoalTypeCreate,
    GoalTypeUpdate,
    GoalUpdate,
    LeadershipRankingResponse,
    RiskStatus,
    TargetOption,
    TargetType,
)
from app.mod_territorio.repository import TerritorioRepository


class MetaService:
    def __init__(self, repository: MetaRepository) -> None:
        self.repository = repository

    async def accessible_territories(
        self, actor: RequestActor, access: TerritorialAccess
    ) -> set[int] | None:
        return await TerritorioRepository(self.repository.session).accessible_ids(
            actor.tenant_id, access
        )

    async def create_type(
        self, actor: RequestActor, payload: GoalTypeCreate
    ) -> dict[str, Any]:
        item = await self.repository.create_type(actor.tenant_id, payload)
        await self._audit(actor, "criar", "tipo_meta_voto", item["id"], None, item)
        await self.repository.commit()
        return item

    async def update_type(
        self, actor: RequestActor, type_id: int, payload: GoalTypeUpdate
    ) -> dict[str, Any]:
        current = await self.repository.get_type(actor.tenant_id, type_id)
        if current is None:
            raise ResourceNotFoundError("Tipo de meta", type_id)
        if current["tenant_id"] is None:
            raise BusinessRuleError("Tipos globais de meta nao podem ser alterados.")
        updated = await self.repository.update_type(actor.tenant_id, type_id, payload)
        assert updated is not None
        await self._audit(actor, "editar", "tipo_meta_voto", type_id, current, updated)
        await self.repository.commit()
        return updated

    async def create_period(
        self, actor: RequestActor, payload: GoalPeriodCreate
    ) -> dict[str, Any]:
        if payload.eleicao_id and not await self.repository.election_exists(
            actor.tenant_id, payload.eleicao_id
        ):
            raise ResourceNotFoundError("Eleicao", payload.eleicao_id)
        item = await self.repository.create_period(actor.tenant_id, payload)
        await self._audit(actor, "criar", "periodo_meta", item["id"], None, item)
        await self.repository.commit()
        return item

    async def update_period(
        self, actor: RequestActor, period_id: int, payload: GoalPeriodUpdate
    ) -> dict[str, Any]:
        current = await self.repository.get_period(actor.tenant_id, period_id)
        if current is None:
            raise ResourceNotFoundError("Periodo de meta", period_id)
        start = payload.data_inicio or current["data_inicio"]
        end = payload.data_fim or current["data_fim"]
        if end < start:
            raise BusinessRuleError("A data final deve ser igual ou posterior a inicial.")
        if payload.eleicao_id and not await self.repository.election_exists(
            actor.tenant_id, payload.eleicao_id
        ):
            raise ResourceNotFoundError("Eleicao", payload.eleicao_id)
        updated = await self.repository.update_period(actor.tenant_id, period_id, payload)
        assert updated is not None
        await self._audit(actor, "editar", "periodo_meta", period_id, current, updated)
        await self.repository.commit()
        return updated

    async def validate_goal(
        self,
        actor: RequestActor,
        *,
        type_id: int,
        period_id: int,
        targets: list[GoalTargetInput],
        accessible_ids: set[int] | None,
        coordinator_id: int | None,
    ) -> dict[str, Any]:
        goal_type = await self.repository.get_type(actor.tenant_id, type_id)
        if goal_type is None or not goal_type["ativo"]:
            raise ResourceNotFoundError("Tipo de meta", type_id)
        period = await self.repository.get_period(actor.tenant_id, period_id)
        if period is None or not period["ativo"]:
            raise ResourceNotFoundError("Periodo de meta", period_id)
        if coordinator_id and not await self.repository.coordinator_exists(
            actor.tenant_id, coordinator_id
        ):
            raise ResourceNotFoundError("Coordenador ativo", coordinator_id)

        required_target = {
            "territorial": "territorio",
            "lider": "lideranca",
            "equipe": "equipe",
            "comunidade": "comunidade",
            "nucleo_familiar": "nucleo_familiar",
        }.get(goal_type["codigo"])
        if goal_type["codigo"] != "global" and not targets:
            raise BusinessRuleError(
                "A meta deve possuir ao menos um alvo.",
                code="goal_target_required",
            )
        if required_target and not any(
            target.tipo_alvo == required_target for target in targets
        ):
            raise BusinessRuleError(
                f"Meta do tipo {goal_type['nome']} exige alvo {required_target}.",
                code="invalid_goal_target",
            )
        unique_targets = {(target.tipo_alvo, target.alvo_id) for target in targets}
        if len(unique_targets) != len(targets):
            raise BusinessRuleError("A meta possui alvos duplicados.")
        for target in targets:
            if not await self.repository.target_exists(
                actor.tenant_id, target.tipo_alvo, target.alvo_id
            ):
                raise ResourceNotFoundError(
                    f"Alvo {target.tipo_alvo}", target.alvo_id
                )
            if not await self.repository.target_is_accessible(
                actor.tenant_id,
                target.tipo_alvo,
                target.alvo_id,
                accessible_ids,
            ):
                raise AuthorizationError("Alvo fora do escopo territorial permitido.")
        return goal_type

    async def create_goal(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        payload: GoalCreate,
    ) -> GoalDetailResponse:
        accessible_ids = await self.accessible_territories(actor, access)
        await self.validate_goal(
            actor,
            type_id=payload.tipo_meta_voto_id,
            period_id=payload.periodo_meta_id,
            targets=payload.alvos,
            accessible_ids=accessible_ids,
            coordinator_id=payload.coordenador_id,
        )
        goal_id = await self.repository.create_goal(actor.tenant_id, actor.user_id, payload)
        created = await self.repository.get_goal(actor.tenant_id, goal_id)
        assert created is not None
        person_ids = await self.goal_person_ids(actor.tenant_id, created)
        base = len(person_ids)
        engagement = await self.repository.average_person_engagement(
            actor.tenant_id, person_ids
        )
        percentage = self.percentage(base, payload.quantidade_meta)
        threshold = await self.repository.risk_threshold(actor.tenant_id)
        risk_status = self.risk_status(percentage, threshold)
        initial_tracking = GoalTrackingCreate(
            data_referencia=date.today(),
            quantidade_projetada=base,
            observacao="Calculo inicial automatico",
        )
        await self.repository.upsert_tracking(
            actor.tenant_id,
            actor.user_id,
            goal_id,
            initial_tracking,
            base_count=base,
            percentage=percentage,
            risk_status=risk_status,
        )
        alert_change = await self.repository.sync_risk_alert(
            actor.tenant_id, goal_id, percentage, threshold, risk_status
        )
        await self._audit_alert_change(actor, alert_change)
        score, factors = self.predictive_risk_score(
            percentage=percentage,
            threshold=threshold,
            tracking=[],
            base_count=base,
            target=payload.quantidade_meta,
            average_engagement=engagement,
        )
        await self.repository.update_predictive_risk(
            actor.tenant_id, goal_id, score, factors, risk_status
        )
        await self._audit(
            actor,
            "criar",
            "meta_voto",
            goal_id,
            None,
            payload.model_dump(mode="json"),
        )
        await self.repository.commit()
        return await self.get_goal(actor, access, goal_id)

    async def update_goal(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        goal_id: int,
        payload: GoalUpdate,
    ) -> GoalDetailResponse:
        current = await self.ensure_goal_access(actor, access, goal_id)
        current_targets = await self.repository.list_targets(actor.tenant_id, goal_id)
        targets = (
            payload.alvos
            if payload.alvos is not None
            else [
                GoalTargetInput.model_validate(
                    {
                        "tipo_alvo": target["tipo_alvo"],
                        "alvo_id": target["alvo_id"],
                        "quantidade_atribuida": target["quantidade_atribuida"],
                    }
                )
                for target in current_targets
            ]
        )
        await self.validate_goal(
            actor,
            type_id=payload.tipo_meta_voto_id or current["tipo_meta_voto_id"],
            period_id=payload.periodo_meta_id or current["periodo_meta_id"],
            targets=targets,
            accessible_ids=await self.accessible_territories(actor, access),
            coordinator_id=(
                payload.coordenador_id
                if "coordenador_id" in payload.model_fields_set
                else current["coordenador_id"]
            ),
        )
        await self.repository.update_goal(actor.tenant_id, goal_id, payload)
        updated = await self.repository.get_goal(actor.tenant_id, goal_id)
        assert updated is not None
        await self.persist_goal_state(actor, updated)
        await self._audit(
            actor,
            "editar",
            "meta_voto",
            goal_id,
            current,
            payload.model_dump(exclude_unset=True, mode="json"),
        )
        await self.repository.commit()
        return await self.get_goal(actor, access, goal_id)

    async def cancel_goal(
        self, actor: RequestActor, access: TerritorialAccess, goal_id: int
    ) -> None:
        current = await self.ensure_goal_access(actor, access, goal_id)
        if not await self.repository.cancel_goal(actor.tenant_id, goal_id):
            raise BusinessRuleError("A meta ja esta cancelada.")
        threshold = await self.repository.risk_threshold(actor.tenant_id)
        alert_change = await self.repository.sync_risk_alert(
            actor.tenant_id, goal_id, threshold, threshold, "normal"
        )
        await self._audit_alert_change(actor, alert_change)
        await self._audit(
            actor,
            "editar",
            "meta_voto",
            goal_id,
            current,
            {**current, "status": "cancelada"},
        )
        await self.repository.commit()

    async def ensure_goal_access(
        self, actor: RequestActor, access: TerritorialAccess, goal_id: int
    ) -> dict[str, Any]:
        goal = await self.repository.get_goal(actor.tenant_id, goal_id)
        if goal is None:
            raise ResourceNotFoundError("Meta", goal_id)
        if access.unrestricted:
            return goal
        accessible_ids = await self.accessible_territories(actor, access)
        visible = await self.repository.list_goals(
            actor.tenant_id,
            actor.user_id,
            territory_id=None,
            leader_id=None,
            period_id=None,
            status=None,
            accessible_ids=accessible_ids,
        )
        if not any(item["id"] == goal_id for item in visible):
            raise AuthorizationError("Meta fora do escopo permitido.")
        return goal

    async def list_goals(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        *,
        territory_id: int | None,
        leader_id: int | None,
        period_id: int | None,
        status: str | None,
    ) -> list[GoalResponse]:
        accessible_ids = await self.accessible_territories(actor, access)
        if territory_id and accessible_ids is not None and territory_id not in accessible_ids:
            raise AuthorizationError("Territorio fora do escopo permitido.")
        goals = await self.repository.list_goals(
            actor.tenant_id,
            actor.user_id,
            territory_id=territory_id,
            leader_id=leader_id,
            period_id=period_id,
            status=status,
            accessible_ids=accessible_ids,
        )
        return [await self.enrich_goal(actor.tenant_id, goal) for goal in goals]

    async def get_goal(
        self, actor: RequestActor, access: TerritorialAccess, goal_id: int
    ) -> GoalDetailResponse:
        goal = await self.ensure_goal_access(actor, access, goal_id)
        enriched = await self.enrich_goal(actor.tenant_id, goal)
        return GoalDetailResponse(
            **enriched.model_dump(),
            alvos=await self.repository.list_targets(actor.tenant_id, goal_id),
            acompanhamentos=await self.repository.list_tracking(actor.tenant_id, goal_id),
            alertas=await self.repository.list_alerts(actor.tenant_id, goal_id),
        )

    async def goal_person_ids(
        self, tenant_id: int, goal: dict[str, Any]
    ) -> set[int]:
        targets = await self.repository.list_targets(tenant_id, goal["id"])
        if not targets and goal["tipo_codigo"] == "global":
            return await self.repository.global_person_ids(tenant_id)
        person_ids: set[int] = set()
        for target in targets:
            person_ids.update(
                await self.repository.target_person_ids(
                    tenant_id, target["tipo_alvo"], target["alvo_id"]
                )
            )
        return person_ids

    async def base_count(self, tenant_id: int, goal: dict[str, Any]) -> int:
        return len(await self.goal_person_ids(tenant_id, goal))

    async def enrich_goal(
        self, tenant_id: int, goal: dict[str, Any]
    ) -> GoalResponse:
        tracking = await self.repository.list_tracking(tenant_id, goal["id"])
        person_ids = await self.goal_person_ids(tenant_id, goal)
        base = len(person_ids)
        engagement = await self.repository.average_person_engagement(
            tenant_id, person_ids
        )
        latest = tracking[0] if tracking else None
        current = (
            latest["quantidade_confirmada"]
            if latest and latest["quantidade_confirmada"] is not None
            else (
                latest["quantidade_projetada"]
                if latest and latest["quantidade_projetada"] is not None
                else base
            )
        )
        percentage = self.percentage(current, goal["quantidade_meta"])
        threshold = await self.repository.risk_threshold(tenant_id)
        risk_status = self.risk_status(percentage, threshold)
        score, factors = self.predictive_risk_score(
            percentage=percentage,
            threshold=threshold,
            tracking=tracking,
            base_count=base,
            target=goal["quantidade_meta"],
            average_engagement=engagement,
        )
        goal["score_risco"] = score
        goal["fatores_risco"] = factors
        goal["quantidade_atual"] = current
        goal["quantidade_eleitores_vinculados"] = base
        goal["percentual"] = percentage
        goal["situacao_risco"] = risk_status
        goal["em_risco"] = percentage < threshold
        return GoalResponse.model_validate(goal)

    async def persist_goal_state(
        self, actor: RequestActor, goal: dict[str, Any]
    ) -> None:
        if goal["status"] not in ACTIVE_GOAL_STATUSES:
            threshold = await self.repository.risk_threshold(actor.tenant_id)
            alert_change = await self.repository.sync_risk_alert(
                actor.tenant_id, goal["id"], threshold, threshold, "normal"
            )
            await self._audit_alert_change(actor, alert_change)
            return
        tracking = await self.repository.list_tracking(actor.tenant_id, goal["id"])
        person_ids = await self.goal_person_ids(actor.tenant_id, goal)
        base = len(person_ids)
        latest = tracking[0] if tracking else None
        current = (
            latest["quantidade_confirmada"]
            if latest and latest["quantidade_confirmada"] is not None
            else (
                latest["quantidade_projetada"]
                if latest and latest["quantidade_projetada"] is not None
                else base
            )
        )
        percentage = self.percentage(current, goal["quantidade_meta"])
        threshold = await self.repository.risk_threshold(actor.tenant_id)
        status = self.risk_status(percentage, threshold)
        alert_change = await self.repository.sync_risk_alert(
            actor.tenant_id, goal["id"], percentage, threshold, status
        )
        await self._audit_alert_change(actor, alert_change)
        engagement = await self.repository.average_person_engagement(
            actor.tenant_id, person_ids
        )
        score, factors = self.predictive_risk_score(
            percentage=percentage,
            threshold=threshold,
            tracking=tracking,
            base_count=base,
            target=goal["quantidade_meta"],
            average_engagement=engagement,
        )
        await self.repository.update_predictive_risk(
            actor.tenant_id, goal["id"], score, factors, status
        )

    async def create_tracking(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        goal_id: int,
        payload: GoalTrackingCreate,
    ) -> GoalTrackingResponse:
        goal = await self.ensure_goal_access(actor, access, goal_id)
        if goal["status"] in {"cancelada", "concluida"}:
            raise BusinessRuleError("Meta encerrada nao aceita novo acompanhamento.")
        person_ids = await self.goal_person_ids(actor.tenant_id, goal)
        base = len(person_ids)
        engagement = await self.repository.average_person_engagement(
            actor.tenant_id, person_ids
        )
        current = (
            payload.quantidade_confirmada
            if payload.quantidade_confirmada is not None
            else payload.quantidade_projetada or 0
        )
        percentage = self.percentage(current, goal["quantidade_meta"])
        threshold = await self.repository.risk_threshold(actor.tenant_id)
        risk_status = self.risk_status(percentage, threshold)
        tracking = await self.repository.upsert_tracking(
            actor.tenant_id,
            actor.user_id,
            goal_id,
            payload,
            base_count=base,
            percentage=percentage,
            risk_status=risk_status,
        )
        alert_change = await self.repository.sync_risk_alert(
            actor.tenant_id, goal_id, percentage, threshold, risk_status
        )
        await self._audit_alert_change(actor, alert_change)
        complete_tracking = await self.repository.list_tracking(
            actor.tenant_id, goal_id
        )
        score, factors = self.predictive_risk_score(
            percentage=percentage,
            threshold=threshold,
            tracking=complete_tracking,
            base_count=base,
            target=goal["quantidade_meta"],
            average_engagement=engagement,
        )
        await self.repository.update_predictive_risk(
            actor.tenant_id, goal_id, score, factors, risk_status
        )
        await self._audit(
            actor,
            "editar",
            "acompanhamento_meta",
            tracking["id"],
            None,
            tracking,
        )
        await self.repository.commit()
        return GoalTrackingResponse.model_validate(tracking)

    async def summary(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        *,
        territory_id: int | None = None,
        leader_id: int | None = None,
        period_id: int | None = None,
        status: str | None = None,
    ) -> GoalSummaryResponse:
        goals = await self.list_goals(
            actor,
            access,
            territory_id=territory_id,
            leader_id=leader_id,
            period_id=period_id,
            status=status,
        )
        active = [goal for goal in goals if goal.status in ACTIVE_GOAL_STATUSES]
        target = sum(goal.quantidade_meta for goal in active)
        current = sum(goal.quantidade_atual for goal in active)
        threshold = await self.repository.risk_threshold(actor.tenant_id)
        return GoalSummaryResponse(
            total_metas=len(goals),
            metas_ativas=len(active),
            metas_atingidas=sum(goal.percentual >= 100 for goal in goals),
            metas_em_risco=sum(goal.em_risco for goal in active),
            quantidade_meta_total=target,
            quantidade_atual_total=current,
            percentual_geral=self.percentage(current, target),
            limiar_risco=threshold,
        )

    async def recalculate_ranking(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        ranking_date: date | None = None,
    ) -> list[LeadershipRankingResponse]:
        reference = ranking_date or date.today()
        accessible_ids = await self.accessible_territories(actor, access)
        visible_leader_ids = await self.repository.visible_leader_ids(
            actor.tenant_id, actor.user_id, accessible_ids
        )
        metrics = await self.repository.ranking_metrics(actor.tenant_id)
        raw_goals = await self.repository.list_goals(
            actor.tenant_id,
            actor.user_id,
            territory_id=None,
            leader_id=None,
            period_id=None,
            status=None,
            accessible_ids=None,
        )
        active_goals = [
            goal for goal in raw_goals if goal["status"] in ACTIVE_GOAL_STATUSES
        ]
        goals = [
            await self.enrich_goal(actor.tenant_id, goal) for goal in active_goals
        ]
        targets_by_goal = {
            goal.id: await self.repository.list_targets(actor.tenant_id, goal.id)
            for goal in goals
        }
        ranking_rows: list[dict[str, Any]] = []
        for metric in metrics:
            leader_goals = [
                goal
                for goal in goals
                if any(
                    target["tipo_alvo"] == "lideranca"
                    and target["alvo_id"] == metric["lideranca_id"]
                    for target in targets_by_goal[goal.id]
                )
            ]
            target = sum(goal.quantidade_meta for goal in leader_goals)
            current = sum(goal.quantidade_atual for goal in leader_goals)
            percentage = self.percentage(current, target)
            confirmations = 0
            for goal in leader_goals:
                tracking = await self.repository.list_tracking(
                    actor.tenant_id, goal.id
                )
                if tracking:
                    confirmations += tracking[0]["quantidade_confirmada"] or 0
            points = ranking_score(
                percentage,
                metric["total_cadastros"],
                Decimal(metric["engajamento"]),
            )
            ranking_rows.append(
                {
                    **metric,
                    "total_confirmacoes": confirmations,
                    "quantidade_meta": target,
                    "quantidade_atual": current,
                    "percentual_meta": percentage,
                    "pontuacao": points,
                }
            )
        ranking_rows.sort(
            key=lambda row: (
                row["pontuacao"],
                row["percentual_meta"],
                row["total_cadastros"],
            ),
            reverse=True,
        )
        for position, row in enumerate(ranking_rows, 1):
            row["posicao"] = position
        await self.repository.replace_ranking(actor.tenant_id, reference, ranking_rows)
        await self.repository.commit()
        results = [
            LeadershipRankingResponse(
                id=position,
                lideranca_id=row["lideranca_id"],
                nome_lideranca=row["nome_lideranca"],
                data_referencia=reference,
                posicao=row["posicao"],
                total_cadastros=row["total_cadastros"],
                total_confirmacoes=row["total_confirmacoes"],
                total_eventos=row["total_eventos"],
                total_demandas=row["total_demandas"],
                quantidade_meta=row["quantidade_meta"],
                quantidade_atual=row["quantidade_atual"],
                percentual_meta=row["percentual_meta"],
                pontuacao=row["pontuacao"],
                em_risco=row["percentual_meta"]
                < await self.repository.risk_threshold(actor.tenant_id),
            )
            for position, row in enumerate(ranking_rows, 1)
        ]
        if visible_leader_ids is None:
            return results
        return [row for row in results if row.lideranca_id in visible_leader_ids]

    async def list_ranking(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        ranking_date: date | None = None,
    ) -> list[LeadershipRankingResponse]:
        accessible_ids = await self.accessible_territories(actor, access)
        visible_leader_ids = await self.repository.visible_leader_ids(
            actor.tenant_id, actor.user_id, accessible_ids
        )
        rows = await self.repository.list_ranking(actor.tenant_id, ranking_date)
        if not rows:
            return await self.recalculate_ranking(actor, access, ranking_date)
        threshold = await self.repository.risk_threshold(actor.tenant_id)
        results: list[LeadershipRankingResponse] = []
        for row in rows:
            if (
                visible_leader_ids is not None
                and row["lideranca_id"] not in visible_leader_ids
            ):
                continue
            goals = await self.repository.list_goals(
                actor.tenant_id,
                actor.user_id,
                territory_id=None,
                leader_id=row["lideranca_id"],
                period_id=None,
                status=None,
                accessible_ids=None,
            )
            enriched = [
                await self.enrich_goal(actor.tenant_id, goal)
                for goal in goals
                if goal["status"] in ACTIVE_GOAL_STATUSES
            ]
            target = sum(goal.quantidade_meta for goal in enriched)
            current = sum(goal.quantidade_atual for goal in enriched)
            results.append(
                LeadershipRankingResponse(
                    **row,
                    quantidade_meta=target,
                    quantidade_atual=current,
                    em_risco=Decimal(row["percentual_meta"]) < threshold,
                )
            )
        return results

    async def target_options(
        self,
        actor: RequestActor,
        access: TerritorialAccess,
        target_type: TargetType,
        query: str | None,
    ) -> list[TargetOption]:
        accessible_ids = await self.accessible_territories(actor, access)
        return [
            TargetOption.model_validate(item)
            for item in await self.repository.target_options(
                actor.tenant_id, target_type, query, accessible_ids
            )
        ]

    @staticmethod
    def percentage(current: int, target: int) -> Decimal:
        return calculate_percentage(current, target)

    @staticmethod
    def risk_status(percentage: Decimal, threshold: Decimal) -> RiskStatus:
        return calculate_risk_status(percentage, threshold)  # type: ignore[return-value]

    @staticmethod
    def predictive_risk_score(
        *,
        percentage: Decimal,
        threshold: Decimal,
        tracking: list[dict[str, Any]],
        base_count: int,
        target: int,
        average_engagement: Decimal = Decimal("0"),
    ) -> tuple[Decimal, dict[str, Any]]:
        score, factors = calculate_predictive_risk_score(
            current_percentage=percentage,
            threshold=threshold,
            tracking_percentages=[
                Decimal(str(item["percentual_atingido"] or 0))
                for item in tracking
            ],
            base_count=base_count,
            target=target,
            average_engagement=average_engagement,
        )
        factors["calculado_em"] = datetime.now(UTC).isoformat()
        return score, factors

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
            schema_name="meta",
            table_name=table,
            record_id=record_id,
            before=jsonable_encoder(before) if before is not None else None,
            after=jsonable_encoder(after) if after is not None else None,
        )

    async def _audit_alert_change(
        self, actor: RequestActor, change: dict[str, Any] | None
    ) -> None:
        if change is None:
            return
        await self._audit(
            actor,
            str(change["action"]),
            "alerta_meta",
            int(change["id"]),
            change["before"],
            change["after"],
        )
