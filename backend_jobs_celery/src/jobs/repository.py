from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Protocol

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from jobs.database import normalize_database_url
from jobs.goals_rules import (
    RANKING_ATTAINMENT_WEIGHT,
    RANKING_ENGAGEMENT_WEIGHT,
    RANKING_REGISTRATIONS_WEIGHT,
    alert_severity,
    predictive_risk_score,
)
from jobs.goals_rules import (
    percentage as calculate_percentage,
)
from jobs.goals_rules import (
    risk_status as calculate_risk_status,
)


@dataclass(frozen=True, slots=True)
class JobRecord:
    id: int
    status: str
    tentativas: int
    iniciado_em: datetime | None
    concluido_em: datetime | None


class JobRepositoryProtocol(Protocol):
    def create(
        self,
        *,
        job_type: str,
        reference: str,
        parameters: dict[str, Any],
        tenant_id: int | None = None,
    ) -> int: ...

    def mark_started(self, job_id: int) -> None: ...

    def mark_succeeded(self, job_id: int, context: dict[str, Any] | None = None) -> None: ...

    def mark_failed(self, job_id: int, context: dict[str, Any] | None = None) -> None: ...

    def get(self, job_id: int) -> JobRecord | None: ...


class CompletenessRepositoryProtocol(JobRepositoryProtocol, Protocol):
    def recalculate_person_completeness(
        self, *, tenant_id: int, batch_size: int
    ) -> dict[str, int]: ...


class CompletenessSchedulerRepositoryProtocol(Protocol):
    def list_active_tenant_ids(self) -> list[int]: ...

    def create_if_idle(
        self,
        *,
        job_type: str,
        reference: str,
        parameters: dict[str, Any],
        tenant_id: int,
    ) -> int | None: ...

    def mark_failed(self, job_id: int, context: dict[str, Any] | None = None) -> None: ...


class GoalsRepositoryProtocol(JobRepositoryProtocol, Protocol):
    def recalculate_goals_and_rankings(
        self, *, tenant_id: int, reference_date: date
    ) -> dict[str, int]: ...


class JobRepository:
    def __init__(self, database_url: str) -> None:
        self.database_url = normalize_database_url(database_url)

    def create(
        self,
        *,
        job_type: str,
        reference: str,
        parameters: dict[str, Any],
        tenant_id: int | None = None,
    ) -> int:
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            row = connection.execute(
                """
                INSERT INTO etl.job_processamento
                    (tenant_id, tipo, referencia, status, parametros)
                VALUES (%s, %s, %s, 'enfileirado', %s)
                RETURNING id
                """,
                (tenant_id, job_type, reference, Jsonb(parameters)),
            ).fetchone()
            if row is None:
                raise RuntimeError("O banco nao retornou o ID do job criado.")
            job_id = int(row["id"])
            self._insert_log(
                connection,
                job_id,
                level="info",
                message="Job enfileirado.",
                context={"referencia": reference},
            )
            return job_id

    def mark_started(self, job_id: int) -> None:
        with psycopg.connect(self.database_url) as connection:
            result = connection.execute(
                """
                UPDATE etl.job_processamento
                SET status = 'executando',
                    tentativas = tentativas + 1,
                    iniciado_em = now(),
                    concluido_em = NULL
                WHERE id = %s
                """,
                (job_id,),
            )
            self._ensure_updated(result.rowcount, job_id)
            self._insert_log(connection, job_id, "info", "Execucao iniciada.")

    def mark_succeeded(self, job_id: int, context: dict[str, Any] | None = None) -> None:
        with psycopg.connect(self.database_url) as connection:
            result = connection.execute(
                """
                UPDATE etl.job_processamento
                SET status = 'concluido', concluido_em = now()
                WHERE id = %s
                """,
                (job_id,),
            )
            self._ensure_updated(result.rowcount, job_id)
            self._insert_log(connection, job_id, "info", "Execucao concluida.", context)

    def mark_failed(self, job_id: int, context: dict[str, Any] | None = None) -> None:
        with psycopg.connect(self.database_url) as connection:
            result = connection.execute(
                """
                UPDATE etl.job_processamento
                SET status = 'falha', concluido_em = now()
                WHERE id = %s
                """,
                (job_id,),
            )
            self._ensure_updated(result.rowcount, job_id)
            self._insert_log(connection, job_id, "error", "Execucao falhou.", context)

    def get(self, job_id: int) -> JobRecord | None:
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            row = connection.execute(
                """
                SELECT id, status, tentativas, iniciado_em, concluido_em
                FROM etl.job_processamento
                WHERE id = %s
                """,
                (job_id,),
            ).fetchone()
        if row is None:
            return None
        return JobRecord(
            id=int(row["id"]),
            status=str(row["status"]),
            tentativas=int(row["tentativas"]),
            iniciado_em=row["iniciado_em"],
            concluido_em=row["concluido_em"],
        )

    def list_active_tenant_ids(self) -> list[int]:
        with psycopg.connect(self.database_url) as connection:
            rows = connection.execute(
                """
                SELECT id
                FROM public.tenant
                WHERE status IN ('ativo', 'trial')
                  AND excluido_em IS NULL
                ORDER BY id
                """
            ).fetchall()
        return [int(row[0]) for row in rows]

    def tenant_is_active(self, tenant_id: int) -> bool:
        with psycopg.connect(self.database_url) as connection:
            row = connection.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM public.tenant
                    WHERE id = %s
                      AND status IN ('ativo', 'trial')
                      AND excluido_em IS NULL
                )
                """,
                (tenant_id,),
            ).fetchone()
        return bool(row and row[0])

    def create_if_idle(
        self,
        *,
        job_type: str,
        reference: str,
        parameters: dict[str, Any],
        tenant_id: int,
    ) -> int | None:
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            connection.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                (f"{tenant_id}:{reference}",),
            )
            row = connection.execute(
                """
                INSERT INTO etl.job_processamento
                    (tenant_id, tipo, referencia, status, parametros)
                SELECT %s, %s, %s, 'enfileirado', %s
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM etl.job_processamento
                    WHERE tenant_id = %s
                      AND tipo = %s
                      AND referencia = %s
                      AND status IN ('enfileirado', 'executando')
                )
                RETURNING id
                """,
                (
                    tenant_id,
                    job_type,
                    reference,
                    Jsonb(parameters),
                    tenant_id,
                    job_type,
                    reference,
                ),
            ).fetchone()
            if row is None:
                return None
            job_id = int(row["id"])
            self._insert_log(
                connection,
                job_id,
                level="info",
                message="Job enfileirado.",
                context={
                    "referencia": reference,
                    "origem": parameters.get("origem", "automatico"),
                },
            )
            return job_id

    def recalculate_person_completeness(self, *, tenant_id: int, batch_size: int) -> dict[str, int]:
        if batch_size < 1:
            raise ValueError("batch_size deve ser maior que zero.")

        processed = 0
        updated = 0
        last_person_id = 0
        with psycopg.connect(self.database_url) as connection:
            while True:
                with connection.transaction():
                    connection.execute(
                        "SELECT set_config('app.current_tenant_id', %s, true)",
                        (str(tenant_id),),
                    )
                    row = connection.execute(
                        """
                        WITH selected AS MATERIALIZED (
                            SELECT id
                            FROM cadastro.pessoa
                            WHERE tenant_id = %s
                              AND id > %s
                              AND ativo = TRUE
                              AND excluido_em IS NULL
                            ORDER BY id
                            LIMIT %s
                        ),
                        scores AS (
                            SELECT
                                pessoa.id,
                                (
                                    CASE WHEN btrim(pessoa.nome_completo) <> '' THEN 10 ELSE 0 END
                                    + CASE
                                        WHEN pessoa.data_nascimento IS NOT NULL THEN 15
                                        ELSE 0
                                    END
                                    + CASE WHEN pessoa.sexo IS NOT NULL THEN 5 ELSE 0 END
                                    + CASE WHEN pessoa.estado_civil IS NOT NULL THEN 5 ELSE 0 END
                                    + CASE WHEN pessoa.escolaridade_id IS NOT NULL THEN 5 ELSE 0 END
                                    + CASE WHEN pessoa.profissao_id IS NOT NULL THEN 5 ELSE 0 END
                                    + CASE WHEN pessoa.religiao_id IS NOT NULL THEN 5 ELSE 0 END
                                    + CASE WHEN EXISTS (
                                        SELECT 1 FROM cadastro.pessoa_documento documento
                                        WHERE documento.tenant_id = %s
                                          AND documento.pessoa_id = pessoa.id
                                    ) THEN 15 ELSE 0 END
                                    + CASE WHEN EXISTS (
                                        SELECT 1 FROM cadastro.pessoa_contato contato
                                        WHERE contato.tenant_id = %s
                                          AND contato.pessoa_id = pessoa.id
                                    ) THEN 15 ELSE 0 END
                                    + CASE WHEN EXISTS (
                                        SELECT 1 FROM cadastro.pessoa_endereco endereco
                                        WHERE endereco.tenant_id = %s
                                          AND endereco.pessoa_id = pessoa.id
                                    ) THEN 15 ELSE 0 END
                                    + CASE WHEN EXISTS (
                                        SELECT 1 FROM cadastro.pessoa_pessoa_tipo tipo
                                        WHERE tipo.tenant_id = %s
                                          AND tipo.pessoa_id = pessoa.id
                                    ) THEN 5 ELSE 0 END
                                )::numeric(5, 2) AS score
                            FROM cadastro.pessoa pessoa
                            JOIN selected ON selected.id = pessoa.id
                        ),
                        changed AS (
                            UPDATE cadastro.pessoa pessoa
                            SET completude_cadastral = scores.score
                            FROM scores
                            WHERE pessoa.id = scores.id
                              AND pessoa.tenant_id = %s
                              AND pessoa.completude_cadastral IS DISTINCT FROM scores.score
                            RETURNING pessoa.id
                        )
                        SELECT
                            (SELECT count(*) FROM selected) AS processed_count,
                            (SELECT count(*) FROM changed) AS updated_count,
                            (SELECT max(id) FROM selected) AS last_id
                        """,
                        (
                            tenant_id,
                            last_person_id,
                            batch_size,
                            tenant_id,
                            tenant_id,
                            tenant_id,
                            tenant_id,
                            tenant_id,
                        ),
                    ).fetchone()

                if row is None or int(row[0]) == 0:
                    break
                processed += int(row[0])
                updated += int(row[1])
                last_person_id = int(row[2])

        return {
            "tenant_id": tenant_id,
            "processadas": processed,
            "atualizadas": updated,
        }

    def recalculate_goals_and_rankings(
        self, *, tenant_id: int, reference_date: date
    ) -> dict[str, int]:
        goals_updated = 0
        alerts_opened = 0
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            with connection.transaction():
                connection.execute(
                    "SELECT set_config('app.current_tenant_id', %s, true)",
                    (str(tenant_id),),
                )
                campaign = connection.execute(
                    """
                    SELECT id FROM eleicao.campanha_eleicao
                    WHERE tenant_id = %s AND ativa
                    ORDER BY data_ativacao DESC NULLS LAST, id DESC
                    LIMIT 1
                    """,
                    (tenant_id,),
                ).fetchone()
                if campaign is None:
                    raise RuntimeError("Tenant nao possui campanha eleitoral ativa.")
                campaign_id = int(campaign["id"])
                threshold_row = connection.execute(
                    """
                    SELECT COALESCE(percentual_alerta_meta, 70) AS threshold
                    FROM public.tenant_configuracao
                    WHERE tenant_id = %s
                    """,
                    (tenant_id,),
                ).fetchone()
                threshold = (
                    Decimal(str(threshold_row["threshold"]))
                    if threshold_row
                    else Decimal("70")
                )
                goals = connection.execute(
                    """
                    SELECT m.id, m.quantidade_meta, tm.codigo AS tipo_codigo
                    FROM meta.meta_voto m
                    JOIN meta.tipo_meta_voto tm ON tm.id = m.tipo_meta_voto_id
                    WHERE m.tenant_id = %s
                      AND m.campanha_eleicao_id = %s
                      AND m.status IN ('ativa', 'em_risco')
                    ORDER BY m.id
                    """,
                    (tenant_id, campaign_id),
                ).fetchall()
                inactive_alerts = connection.execute(
                    """
                    UPDATE meta.alerta_meta a
                    SET resolvido = TRUE, resolvido_em = now()
                    FROM meta.meta_voto m
                    WHERE a.meta_voto_id = m.id
                      AND a.tenant_id = %s
                      AND m.tenant_id = a.tenant_id
                      AND m.status NOT IN ('ativa', 'em_risco')
                      AND a.tipo_alerta = 'meta_abaixo_esperado'
                      AND NOT a.resolvido
                    RETURNING a.id, a.meta_voto_id
                    """,
                    (tenant_id,),
                ).fetchall()
                for alert in inactive_alerts:
                    self._insert_audit(
                        connection,
                        tenant_id=tenant_id,
                        action="editar",
                        table="alerta_meta",
                        record_id=int(alert["id"]),
                        data={
                            "meta_voto_id": int(alert["meta_voto_id"]),
                            "resolvido": True,
                            "origem": "job_recalculo_metas",
                        },
                    )
                for goal in goals:
                    targets = connection.execute(
                        """
                        SELECT tipo_alvo, alvo_id
                        FROM meta.meta_voto_alvo
                        WHERE tenant_id = %s AND meta_voto_id = %s
                        """,
                        (tenant_id, goal["id"]),
                    ).fetchall()
                    person_ids: set[int] = set()
                    if not targets and goal["tipo_codigo"] == "global":
                        rows = connection.execute(
                            """
                            SELECT id FROM cadastro.pessoa
                            WHERE tenant_id = %s AND ativo AND excluido_em IS NULL
                            """,
                            (tenant_id,),
                        ).fetchall()
                        person_ids.update(int(row["id"]) for row in rows)
                    for target in targets:
                        person_ids.update(
                            self._target_person_ids(
                                connection,
                                tenant_id,
                                str(target["tipo_alvo"]),
                                int(target["alvo_id"]),
                            )
                        )
                    base_count = len(person_ids)
                    latest = connection.execute(
                        """
                        SELECT quantidade_confirmada, quantidade_projetada
                        FROM meta.acompanhamento_meta
                        WHERE tenant_id = %s AND meta_voto_id = %s
                        ORDER BY data_referencia DESC, id DESC
                        LIMIT 1
                        """,
                        (tenant_id, goal["id"]),
                    ).fetchone()
                    current = base_count
                    if latest:
                        current = (
                            latest["quantidade_confirmada"]
                            if latest["quantidade_confirmada"] is not None
                            else latest["quantidade_projetada"]
                            if latest["quantidade_projetada"] is not None
                            else base_count
                        )
                    target_quantity = int(goal["quantidade_meta"])
                    percentage = calculate_percentage(int(current), target_quantity)
                    risk_status = calculate_risk_status(percentage, threshold)
                    carried_confirmation = (
                        int(latest["quantidade_confirmada"])
                        if latest and latest["quantidade_confirmada"] is not None
                        else None
                    )
                    carried_projection = (
                        None
                        if carried_confirmation is not None
                        else (
                            int(latest["quantidade_projetada"])
                            if latest and latest["quantidade_projetada"] is not None
                            else base_count
                        )
                    )
                    connection.execute(
                        """
                        INSERT INTO meta.acompanhamento_meta
                            (tenant_id, meta_voto_id, data_referencia,
                             quantidade_projetada, quantidade_confirmada,
                             quantidade_eleitores_vinculados, percentual_atingido,
                             situacao_risco, observacao)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s,
                                'Recalculo automatico')
                        ON CONFLICT (meta_voto_id, data_referencia) DO UPDATE SET
                            quantidade_eleitores_vinculados =
                                EXCLUDED.quantidade_eleitores_vinculados,
                            percentual_atingido = CASE
                                WHEN meta.acompanhamento_meta.quantidade_confirmada IS NOT NULL
                                THEN round(
                                    meta.acompanhamento_meta.quantidade_confirmada * 100.0 / %s, 2
                                )
                                WHEN meta.acompanhamento_meta.quantidade_projetada IS NOT NULL
                                THEN round(
                                    meta.acompanhamento_meta.quantidade_projetada * 100.0 / %s, 2
                                )
                                ELSE EXCLUDED.percentual_atingido
                            END,
                            situacao_risco = EXCLUDED.situacao_risco
                        """,
                        (
                            tenant_id,
                            goal["id"],
                            reference_date,
                            carried_projection,
                            carried_confirmation,
                            base_count,
                            percentage,
                            risk_status,
                            max(target_quantity, 1),
                            max(target_quantity, 1),
                        ),
                    )
                    connection.execute(
                        """
                        UPDATE meta.meta_voto
                        SET status = CASE
                            WHEN status IN ('ativa', 'em_risco') AND %s < %s
                                THEN 'em_risco'
                            WHEN status IN ('ativa', 'em_risco') THEN 'ativa'
                            ELSE status
                        END
                        WHERE tenant_id = %s AND id = %s
                        """,
                        (percentage, threshold, tenant_id, goal["id"]),
                    )
                    engagement_row = connection.execute(
                        """
                        SELECT COALESCE(avg(nivel_engajamento), 0) AS engagement
                        FROM cadastro.pessoa
                        WHERE tenant_id = %s AND id = ANY(%s)
                        """,
                        (tenant_id, list(person_ids)),
                    ).fetchone()
                    average_engagement = Decimal(
                        str(engagement_row["engagement"] if engagement_row else 0)
                    )
                    history_rows = connection.execute(
                        """
                        SELECT percentual_atingido
                        FROM meta.acompanhamento_meta
                        WHERE tenant_id = %s AND meta_voto_id = %s
                        ORDER BY data_referencia DESC, id DESC
                        LIMIT 2
                        """,
                        (tenant_id, goal["id"]),
                    ).fetchall()
                    score, factors = predictive_risk_score(
                        current_percentage=percentage,
                        threshold=threshold,
                        tracking_percentages=[
                            Decimal(str(row["percentual_atingido"] or 0))
                            for row in history_rows
                        ],
                        base_count=base_count,
                        target=target_quantity,
                        average_engagement=average_engagement,
                    )
                    factors["calculado_em"] = datetime.now(UTC).isoformat()
                    serialized_factors = {
                        key: str(value) if isinstance(value, Decimal) else value
                        for key, value in factors.items()
                    }
                    connection.execute(
                        """
                        UPDATE meta.meta_voto
                        SET score_risco = %s, fatores_risco = %s,
                            risco_calculado_em = now()
                        WHERE tenant_id = %s AND id = %s
                        """,
                        (score, Jsonb(serialized_factors), tenant_id, goal["id"]),
                    )
                    if percentage < threshold:
                        result = connection.execute(
                            """
                            INSERT INTO meta.alerta_meta
                                (tenant_id, meta_voto_id, tipo_alerta,
                                 percentual_referencia, mensagem, severidade)
                            VALUES (%s, %s, 'meta_abaixo_esperado', %s, %s, %s)
                            ON CONFLICT (meta_voto_id, tipo_alerta)
                                WHERE resolvido = FALSE
                            DO UPDATE SET
                                percentual_referencia = EXCLUDED.percentual_referencia,
                                mensagem = EXCLUDED.mensagem,
                                severidade = EXCLUDED.severidade,
                                atualizado_em = now()
                            WHERE (
                                alerta_meta.percentual_referencia,
                                alerta_meta.mensagem,
                                alerta_meta.severidade
                            ) IS DISTINCT FROM (
                                EXCLUDED.percentual_referencia,
                                EXCLUDED.mensagem,
                                EXCLUDED.severidade
                            )
                            RETURNING id, (xmax = 0) AS inserted
                            """,
                            (
                                tenant_id,
                                goal["id"],
                                percentage,
                                f"Meta em {percentage:.2f}%, abaixo do limiar de {threshold:.2f}%.",
                                alert_severity(risk_status),
                            ),
                        ).fetchone()
                        alerts_opened += int(bool(result and result["inserted"]))
                        if result:
                            self._insert_audit(
                                connection,
                                tenant_id=tenant_id,
                                action="criar" if result["inserted"] else "editar",
                                table="alerta_meta",
                                record_id=int(result["id"]),
                                data={
                                    "meta_voto_id": int(goal["id"]),
                                    "percentual_referencia": str(percentage),
                                    "situacao_risco": risk_status,
                                    "origem": "job_recalculo_metas",
                                },
                            )
                    else:
                        resolved = connection.execute(
                            """
                            UPDATE meta.alerta_meta
                            SET resolvido = TRUE, resolvido_em = now()
                            WHERE tenant_id = %s AND meta_voto_id = %s
                              AND tipo_alerta = 'meta_abaixo_esperado'
                              AND resolvido = FALSE
                            RETURNING id
                            """,
                            (tenant_id, goal["id"]),
                        ).fetchall()
                        for alert in resolved:
                            self._insert_audit(
                                connection,
                                tenant_id=tenant_id,
                                action="editar",
                                table="alerta_meta",
                                record_id=int(alert["id"]),
                                data={
                                    "meta_voto_id": int(goal["id"]),
                                    "resolvido": True,
                                    "origem": "job_recalculo_metas",
                                },
                            )
                    goals_updated += 1

                connection.execute(
                    """
                    DELETE FROM meta.ranking_lideranca
                    WHERE tenant_id = %s AND campanha_eleicao_id = %s
                      AND data_referencia = %s
                    """,
                    (tenant_id, campaign_id, reference_date),
                )
                connection.execute(
                    """
                    WITH leader_metrics AS (
                        SELECT
                            l.id AS lideranca_id,
                            (SELECT count(DISTINCT hl.pessoa_id)
                             FROM eleicao.campanha_liderado hl
                             WHERE hl.tenant_id = l.tenant_id
                               AND hl.campanha_eleicao_id = %s
                               AND hl.lideranca_id = l.id
                               AND hl.ativo) AS cadastros,
                            (SELECT count(*) FROM agenda.evento_lideranca el
                             JOIN agenda.evento ev ON ev.id = el.evento_id
                             WHERE el.tenant_id = l.tenant_id
                               AND el.lideranca_id = l.id
                               AND ev.campanha_eleicao_id = %s) AS eventos,
                            (SELECT count(*) FROM demanda.demanda d
                             WHERE d.tenant_id = l.tenant_id
                               AND d.lideranca_indicacao_id = l.id
                               AND d.campanha_eleicao_id = %s) AS demandas,
                            COALESCE((
                                SELECT avg(p.nivel_engajamento)
                                FROM eleicao.campanha_liderado hl
                                JOIN cadastro.pessoa p
                                  ON p.id = hl.pessoa_id
                                 AND p.tenant_id = hl.tenant_id
                                WHERE hl.tenant_id = l.tenant_id
                                  AND hl.campanha_eleicao_id = %s
                                  AND hl.lideranca_id = l.id
                                  AND hl.ativo
                            ), 0) AS engajamento,
                            COALESCE((
                                SELECT sum(m.quantidade_meta)
                                FROM meta.meta_voto m
                                JOIN meta.meta_voto_alvo a ON a.meta_voto_id = m.id
                                WHERE m.tenant_id = l.tenant_id
                                  AND a.tipo_alvo = 'lideranca'
                                  AND a.alvo_id = l.id
                                  AND m.campanha_eleicao_id = %s
                                  AND m.status IN ('ativa', 'em_risco')
                            ), 0) AS quantidade_meta,
                            COALESCE((
                                SELECT sum(COALESCE(ac.quantidade_confirmada,
                                                    ac.quantidade_projetada,
                                                    ac.quantidade_eleitores_vinculados, 0))
                                FROM meta.meta_voto m
                                JOIN meta.meta_voto_alvo a ON a.meta_voto_id = m.id
                                LEFT JOIN LATERAL (
                                    SELECT *
                                    FROM meta.acompanhamento_meta x
                                    WHERE x.meta_voto_id = m.id
                                    ORDER BY x.data_referencia DESC, x.id DESC
                                    LIMIT 1
                                ) ac ON TRUE
                                WHERE m.tenant_id = l.tenant_id
                                  AND a.tipo_alvo = 'lideranca'
                                  AND a.alvo_id = l.id
                                  AND m.campanha_eleicao_id = %s
                                  AND m.status IN ('ativa', 'em_risco')
                            ), 0) AS quantidade_atual
                            ,COALESCE((
                                SELECT sum(COALESCE(ac.quantidade_confirmada, 0))
                                FROM meta.meta_voto m
                                JOIN meta.meta_voto_alvo a ON a.meta_voto_id = m.id
                                LEFT JOIN LATERAL (
                                    SELECT quantidade_confirmada
                                    FROM meta.acompanhamento_meta x
                                    WHERE x.meta_voto_id = m.id
                                    ORDER BY x.data_referencia DESC, x.id DESC
                                    LIMIT 1
                                ) ac ON TRUE
                                WHERE m.tenant_id = l.tenant_id
                                  AND a.tipo_alvo = 'lideranca'
                                  AND a.alvo_id = l.id
                                  AND m.campanha_eleicao_id = %s
                                  AND m.status IN ('ativa', 'em_risco')
                            ), 0) AS confirmacoes
                        FROM cadastro.lideranca l
                        JOIN eleicao.campanha_lideranca cl
                          ON cl.lideranca_id = l.id
                         AND cl.campanha_eleicao_id = %s
                         AND cl.ativo
                        WHERE l.tenant_id = %s AND l.ativo
                    ),
                    scored AS (
                        SELECT *,
                            CASE WHEN quantidade_meta > 0
                                THEN round(quantidade_atual * 100.0 / quantidade_meta, 2)
                                ELSE 0 END AS percentual,
                            (
                                LEAST(CASE WHEN quantidade_meta > 0
                                    THEN quantidade_atual * 100.0 / quantidade_meta
                                    ELSE 0 END, 100) * %s
                                + LEAST(cadastros, 100) * %s
                                + LEAST(engajamento * 10, 100) * %s
                            ) AS points
                        FROM leader_metrics
                    ),
                    positioned AS (
                        SELECT *, row_number() OVER (
                            ORDER BY points DESC, percentual DESC, cadastros DESC, lideranca_id
                        ) AS position
                        FROM scored
                    )
                    INSERT INTO meta.ranking_lideranca
                        (tenant_id, campanha_eleicao_id, lideranca_id,
                         data_referencia, posicao,
                         total_cadastros, total_confirmacoes, total_eventos,
                         total_demandas, percentual_meta, pontuacao)
                    SELECT %s, %s, lideranca_id, %s, position, cadastros,
                           confirmacoes, eventos, demandas, percentual, points
                    FROM positioned
                    """,
                    (
                        campaign_id,
                        campaign_id,
                        campaign_id,
                        campaign_id,
                        campaign_id,
                        campaign_id,
                        campaign_id,
                        campaign_id,
                        tenant_id,
                        RANKING_ATTAINMENT_WEIGHT,
                        RANKING_REGISTRATIONS_WEIGHT,
                        RANKING_ENGAGEMENT_WEIGHT,
                        tenant_id,
                        campaign_id,
                        reference_date,
                    ),
                )
                ranking_row = connection.execute(
                    """
                    SELECT count(*) AS total
                    FROM meta.ranking_lideranca
                    WHERE tenant_id = %s AND campanha_eleicao_id = %s
                      AND data_referencia = %s
                    """,
                    (tenant_id, campaign_id, reference_date),
                ).fetchone()
                ranking_count = int(ranking_row["total"]) if ranking_row else 0
        return {
            "tenant_id": tenant_id,
            "metas_atualizadas": goals_updated,
            "alertas_abertos": alerts_opened,
            "liderancas_ranqueadas": ranking_count,
        }

    @staticmethod
    def _target_person_ids(
        connection: psycopg.Connection[Any],
        tenant_id: int,
        target_type: str,
        target_id: int,
    ) -> set[int]:
        queries = {
            "lideranca": """
                SELECT pessoa_subordinada_id AS id
                FROM cadastro.hierarquia_lideranca
                WHERE tenant_id = %s AND lideranca_superior_id = %s AND ativo
            """,
            "territorio": """
                WITH RECURSIVE tree AS (
                    SELECT %s::bigint AS id
                    UNION ALL
                    SELECT h.territorio_filho_id
                    FROM territorio.territorio_hierarquia h
                    JOIN tree t ON t.id = h.territorio_pai_id
                    WHERE h.tenant_id = %s
                )
                SELECT DISTINCT pessoa_id AS id
                FROM territorio.pessoa_territorio
                WHERE tenant_id = %s AND territorio_id IN (SELECT id FROM tree)
            """,
            "equipe": """
                SELECT pessoa_id AS id FROM cadastro.equipe_pessoa
                WHERE tenant_id = %s AND equipe_id = %s
            """,
            "comunidade": """
                SELECT pessoa_id AS id FROM cadastro.pessoa_comunidade
                WHERE tenant_id = %s AND comunidade_id = %s
            """,
            "nucleo_familiar": """
                SELECT pessoa_id AS id FROM cadastro.pessoa_nucleo_familiar
                WHERE tenant_id = %s AND nucleo_familiar_id = %s
            """,
            "pessoa": """
                SELECT id FROM cadastro.pessoa
                WHERE tenant_id = %s AND id = %s AND ativo
            """,
        }
        params: tuple[Any, ...]
        if target_type == "territorio":
            params = (target_id, tenant_id, tenant_id)
        else:
            params = (tenant_id, target_id)
        rows = connection.execute(queries[target_type], params).fetchall()
        return {int(row["id"]) for row in rows}

    @staticmethod
    def _insert_audit(
        connection: psycopg.Connection[Any],
        *,
        tenant_id: int,
        action: str,
        table: str,
        record_id: int,
        data: dict[str, Any],
    ) -> None:
        connection.execute(
            """
            INSERT INTO auditoria.log_auditoria
                (tenant_id, acao, schema_nome, tabela, registro_id, dados_novos)
            VALUES (%s, %s, 'meta', %s, %s, %s)
            """,
            (tenant_id, action, table, record_id, Jsonb(data)),
        )

    @staticmethod
    def _ensure_updated(rowcount: int, job_id: int) -> None:
        if rowcount != 1:
            raise LookupError(f"Job {job_id} nao encontrado.")

    @staticmethod
    def _insert_log(
        connection: psycopg.Connection[Any],
        job_id: int,
        level: str,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> None:
        connection.execute(
            """
            INSERT INTO etl.log_processamento
                (job_processamento_id, nivel, mensagem, contexto)
            VALUES (%s, %s, %s, %s)
            """,
            (job_id, level, message, Jsonb(context) if context is not None else None),
        )
