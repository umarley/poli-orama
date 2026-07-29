from typing import Any

import psycopg
from psycopg.rows import dict_row

from jobs.database import normalize_database_url


class CampaignClosureProcessor:
    """Consolida uma campanha no DW em uma unica transacao idempotente."""

    def __init__(self, database_url: str) -> None:
        self.database_url = normalize_database_url(database_url)

    def consolidate(
        self,
        *,
        tenant_id: int,
        campaign_id: int,
        closure_id: int,
    ) -> dict[str, Any]:
        with psycopg.connect(
            self.database_url, row_factory=dict_row
        ) as connection:
            with connection.transaction():
                connection.execute(
                    "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"
                )
                connection.execute(
                    "SELECT set_config('app.current_tenant_id', %s, true)",
                    (str(tenant_id),),
                )
                connection.execute(
                    "SELECT pg_advisory_xact_lock(%s)", (campaign_id,)
                )
                closure = connection.execute(
                    """
                    SELECT ec.*, ce.eleicao_id, ce.nome AS campanha_nome,
                           ce.cargo_pleiteado, ce.ativa,
                           e.ano, e.tipo AS tipo_eleicao, e.turno,
                           e.data_eleicao
                      FROM eleicao.encerramento_campanha ec
                      JOIN eleicao.campanha_eleicao ce
                        ON ce.id = ec.campanha_eleicao_id
                      JOIN eleicao.eleicao e ON e.id = ce.eleicao_id
                     WHERE ec.id = %s
                       AND ec.tenant_id = %s
                       AND ec.campanha_eleicao_id = %s
                     FOR UPDATE OF ec, ce
                    """,
                    (closure_id, tenant_id, campaign_id),
                ).fetchone()
                if closure is None:
                    raise RuntimeError("Solicitacao de encerramento nao encontrada.")
                if closure["status"] == "concluido":
                    return self._current_metrics(
                        connection, tenant_id, campaign_id
                    )

                connection.execute(
                    """
                    UPDATE eleicao.encerramento_campanha
                       SET status = 'processando', iniciado_em = now(),
                           concluido_em = NULL, erro = NULL
                     WHERE id = %s
                    """,
                    (closure_id,),
                )

                self._clear_snapshot(connection, tenant_id, campaign_id)
                self._bind_active_hierarchy(
                    connection, tenant_id, campaign_id
                )
                self._consolidate_people(connection, tenant_id, campaign_id)
                self._consolidate_leadership_hierarchy(
                    connection, tenant_id, campaign_id
                )
                self._consolidate_goals(connection, tenant_id, campaign_id)
                self._consolidate_leaders(connection, tenant_id, campaign_id)
                self._consolidate_campaign(
                    connection, tenant_id, campaign_id, closure_id
                )

                connection.execute(
                    """
                    UPDATE eleicao.campanha_eleicao
                       SET ativa = FALSE,
                           data_encerramento = now(),
                           atualizado_em = now()
                     WHERE id = %s AND tenant_id = %s
                    """,
                    (campaign_id, tenant_id),
                )
                connection.execute(
                    """
                    UPDATE eleicao.encerramento_campanha
                       SET status = 'concluido', concluido_em = now(), erro = NULL
                     WHERE id = %s
                    """,
                    (closure_id,),
                )
                return self._current_metrics(
                    connection, tenant_id, campaign_id
                )

    def fail(
        self, *, tenant_id: int, closure_id: int, message: str
    ) -> None:
        with psycopg.connect(self.database_url) as connection:
            connection.execute(
                "SELECT set_config('app.current_tenant_id', %s, true)",
                (str(tenant_id),),
            )
            connection.execute(
                """
                UPDATE eleicao.encerramento_campanha
                   SET status = 'falha', erro = left(%s, 4000),
                       concluido_em = now()
                 WHERE id = %s AND tenant_id = %s
                """,
                (message, closure_id, tenant_id),
            )

    @staticmethod
    def _clear_snapshot(
        connection: psycopg.Connection[Any],
        tenant_id: int,
        campaign_id: int,
    ) -> None:
        for table in (
            "hierarquia_lideranca_campanha_consolidada",
            "pessoa_campanha_consolidada",
            "meta_campanha_consolidada",
            "lideranca_campanha_consolidada",
            "campanha_consolidada",
        ):
            connection.execute(
                f"DELETE FROM dw.{table} "
                "WHERE tenant_id = %s AND campanha_eleicao_id = %s",
                (tenant_id, campaign_id),
            )

    @staticmethod
    def _bind_active_hierarchy(
        connection: psycopg.Connection[Any],
        tenant_id: int,
        campaign_id: int,
    ) -> None:
        connection.execute(
            """
            UPDATE cadastro.hierarquia_lideranca
               SET campanha_eleicao_id = %s
             WHERE tenant_id = %s
               AND ativo
               AND campanha_eleicao_id IS DISTINCT FROM %s
            """,
            (campaign_id, tenant_id, campaign_id),
        )

    @staticmethod
    def _consolidate_people(
        connection: psycopg.Connection[Any],
        tenant_id: int,
        campaign_id: int,
    ) -> None:
        connection.execute(
            """
            WITH candidates AS (
                SELECT pessoa_subordinada_id AS pessoa_id,
                       lideranca_superior_id AS lideranca_id,
                       0 AS priority
                  FROM cadastro.hierarquia_lideranca
                 WHERE tenant_id = %s
                   AND campanha_eleicao_id = %s
                   AND ativo
                UNION ALL
                SELECT pessoa_id, lideranca_id, 1 AS priority
                  FROM eleicao.campanha_liderado
                 WHERE tenant_id = %s
                   AND campanha_eleicao_id = %s
                UNION ALL
                SELECT pessoa_id, lideranca_id, 2 AS priority
                  FROM eleicao.status_eleitor_eleicao
                 WHERE tenant_id = %s
                   AND campanha_eleicao_id = %s
            ),
            people AS (
                SELECT pessoa_id,
                       COALESCE(
                           max(lideranca_id) FILTER (WHERE priority = 0),
                           max(lideranca_id) FILTER (WHERE priority = 1),
                           max(lideranca_id)
                       ) AS lideranca_id
                  FROM candidates
                 GROUP BY pessoa_id
            )
            INSERT INTO dw.pessoa_campanha_consolidada
                (tenant_id, campanha_eleicao_id, pessoa_id, lideranca_id,
                 situacao_apoio, status_eleitoral, intencao_confirmada,
                 total_atendimentos, total_interacoes)
            SELECT %s, %s, people.pessoa_id,
                   COALESCE(contexto.lideranca_id, people.lideranca_id),
                   contexto.situacao_apoio, status.status,
                   COALESCE(confirmacao.confirmado, FALSE),
                   COALESCE(atendimento.total, 0)::int,
                   COALESCE(interacao.total, 0)::int
              FROM people
         LEFT JOIN eleicao.pessoa_contexto_campanha contexto
                ON contexto.campanha_eleicao_id = %s
               AND contexto.pessoa_id = people.pessoa_id
         LEFT JOIN eleicao.status_eleitor_eleicao status
                ON status.campanha_eleicao_id = %s
               AND status.pessoa_id = people.pessoa_id
         LEFT JOIN LATERAL (
                   SELECT bool_or(c.confirmado AND c.revogado_em IS NULL)
                          AS confirmado
                     FROM eleicao.confirmacao_operacional_voto c
                    WHERE c.campanha_eleicao_id = %s
                      AND c.pessoa_id = people.pessoa_id
                ) confirmacao ON TRUE
         LEFT JOIN LATERAL (
                   SELECT count(*) AS total
                     FROM comunicacao.atendimento_eleitor a
                    WHERE a.campanha_eleicao_id = %s
                      AND a.pessoa_id = people.pessoa_id
                ) atendimento ON TRUE
         LEFT JOIN LATERAL (
                   SELECT count(*) AS total
                     FROM comunicacao.interacao i
                LEFT JOIN agenda.evento ev ON ev.id = i.evento_id
                LEFT JOIN demanda.demanda d ON d.id = i.demanda_id
                    WHERE i.tenant_id = %s
                      AND i.pessoa_id = people.pessoa_id
                      AND (
                          ev.campanha_eleicao_id = %s
                          OR d.campanha_eleicao_id = %s
                      )
                ) interacao ON TRUE
            """,
            (
                tenant_id,
                campaign_id,
                tenant_id,
                campaign_id,
                tenant_id,
                campaign_id,
                tenant_id,
                campaign_id,
                campaign_id,
                campaign_id,
                campaign_id,
                campaign_id,
                tenant_id,
                campaign_id,
                campaign_id,
            ),
        )

    @staticmethod
    def _consolidate_leadership_hierarchy(
        connection: psycopg.Connection[Any],
        tenant_id: int,
        campaign_id: int,
    ) -> None:
        connection.execute(
            """
            INSERT INTO dw.hierarquia_lideranca_campanha_consolidada
                (tenant_id, campanha_eleicao_id, hierarquia_lideranca_id,
                 lideranca_superior_id, pessoa_subordinada_id,
                 papel_subordinado, data_inicio, data_fim,
                 ativo_no_encerramento, intencao_confirmada,
                 status_eleitoral)
            SELECT h.tenant_id, h.campanha_eleicao_id, h.id,
                   h.lideranca_superior_id, h.pessoa_subordinada_id,
                   h.papel_subordinado, h.data_inicio, h.data_fim,
                   h.ativo, COALESCE(p.intencao_confirmada, FALSE),
                   p.status_eleitoral
              FROM cadastro.hierarquia_lideranca h
         LEFT JOIN dw.pessoa_campanha_consolidada p
                ON p.campanha_eleicao_id = h.campanha_eleicao_id
               AND p.pessoa_id = h.pessoa_subordinada_id
             WHERE h.tenant_id = %s
               AND h.campanha_eleicao_id = %s
            """,
            (tenant_id, campaign_id),
        )

    @staticmethod
    def _consolidate_goals(
        connection: psycopg.Connection[Any],
        tenant_id: int,
        campaign_id: int,
    ) -> None:
        connection.execute(
            """
            INSERT INTO dw.meta_campanha_consolidada
                (tenant_id, campanha_eleicao_id, meta_voto_id, tipo_meta,
                 titulo, quantidade_meta, quantidade_projetada,
                 quantidade_confirmada, percentual_atingido, status_final)
            SELECT m.tenant_id, m.campanha_eleicao_id, m.id, tipo.codigo,
                   m.titulo, m.quantidade_meta,
                   COALESCE(ac.quantidade_eleitores_vinculados,
                            ac.quantidade_projetada, 0),
                   COALESCE(ac.quantidade_confirmada, 0),
                   CASE WHEN m.quantidade_meta > 0
                        THEN round(
                            COALESCE(ac.quantidade_confirmada, 0)
                            * 100.0 / m.quantidade_meta, 4
                        )
                        ELSE 0 END,
                   m.status
              FROM meta.meta_voto m
              JOIN meta.tipo_meta_voto tipo ON tipo.id = m.tipo_meta_voto_id
         LEFT JOIN LATERAL (
                   SELECT a.quantidade_eleitores_vinculados,
                          a.quantidade_projetada, a.quantidade_confirmada
                     FROM meta.acompanhamento_meta a
                    WHERE a.meta_voto_id = m.id
                    ORDER BY a.data_referencia DESC, a.id DESC
                    LIMIT 1
                ) ac ON TRUE
             WHERE m.tenant_id = %s
               AND m.campanha_eleicao_id = %s
            """,
            (tenant_id, campaign_id),
        )

    @staticmethod
    def _consolidate_leaders(
        connection: psycopg.Connection[Any],
        tenant_id: int,
        campaign_id: int,
    ) -> None:
        connection.execute(
            """
            INSERT INTO dw.lideranca_campanha_consolidada
                (tenant_id, campanha_eleicao_id, lideranca_id,
                 tipo_lideranca, total_liderados, total_confirmacoes,
                 total_atendimentos, total_eventos, total_demandas,
                 quantidade_meta, quantidade_confirmada_meta,
                 percentual_meta, pontuacao_final, posicao_final)
            SELECT cl.tenant_id, cl.campanha_eleicao_id, cl.lideranca_id,
                   cl.tipo_lideranca,
                   COALESCE(people.total_liderados, 0)::int,
                   COALESCE(people.total_confirmacoes, 0)::int,
                   COALESCE(contacts.total, 0)::int,
                   COALESCE(events.total, 0)::int,
                   COALESCE(demands.total, 0)::int,
                   COALESCE(goals.quantidade_meta, 0)::int,
                   COALESCE(goals.quantidade_confirmada, 0)::int,
                   CASE WHEN COALESCE(goals.quantidade_meta, 0) > 0
                        THEN round(
                            goals.quantidade_confirmada * 100.0
                            / goals.quantidade_meta, 4
                        )
                        ELSE 0 END,
                   COALESCE(ranking.pontuacao, 0),
                   ranking.posicao
              FROM eleicao.campanha_lideranca cl
         LEFT JOIN LATERAL (
                   SELECT count(*) AS total_liderados,
                          count(*) FILTER (
                              WHERE p.intencao_confirmada
                          ) AS total_confirmacoes
                     FROM dw.pessoa_campanha_consolidada p
                    WHERE p.campanha_eleicao_id = cl.campanha_eleicao_id
                      AND p.lideranca_id = cl.lideranca_id
                ) people ON TRUE
         LEFT JOIN LATERAL (
                   SELECT count(*) AS total
                     FROM comunicacao.atendimento_eleitor a
                    WHERE a.campanha_eleicao_id = cl.campanha_eleicao_id
                      AND a.lideranca_id = cl.lideranca_id
                ) contacts ON TRUE
         LEFT JOIN LATERAL (
                   SELECT count(DISTINCT el.evento_id) AS total
                     FROM agenda.evento_lideranca el
                     JOIN agenda.evento ev ON ev.id = el.evento_id
                    WHERE ev.campanha_eleicao_id = cl.campanha_eleicao_id
                      AND el.lideranca_id = cl.lideranca_id
                ) events ON TRUE
         LEFT JOIN LATERAL (
                   SELECT count(*) AS total
                     FROM demanda.demanda d
                    WHERE d.campanha_eleicao_id = cl.campanha_eleicao_id
                      AND d.lideranca_indicacao_id = cl.lideranca_id
                ) demands ON TRUE
         LEFT JOIN LATERAL (
                   SELECT sum(mc.quantidade_meta) AS quantidade_meta,
                          sum(mc.quantidade_confirmada)
                              AS quantidade_confirmada
                     FROM dw.meta_campanha_consolidada mc
                     JOIN meta.meta_voto_alvo alvo
                       ON alvo.meta_voto_id = mc.meta_voto_id
                      AND alvo.tipo_alvo = 'lideranca'
                    WHERE mc.campanha_eleicao_id = cl.campanha_eleicao_id
                      AND alvo.alvo_id = cl.lideranca_id
                ) goals ON TRUE
         LEFT JOIN LATERAL (
                   SELECT r.pontuacao, r.posicao
                     FROM meta.ranking_lideranca r
                    WHERE r.campanha_eleicao_id = cl.campanha_eleicao_id
                      AND r.lideranca_id = cl.lideranca_id
                    ORDER BY r.data_referencia DESC, r.id DESC
                    LIMIT 1
                ) ranking ON TRUE
             WHERE cl.tenant_id = %s
               AND cl.campanha_eleicao_id = %s
            """,
            (tenant_id, campaign_id),
        )

    @staticmethod
    def _consolidate_campaign(
        connection: psycopg.Connection[Any],
        tenant_id: int,
        campaign_id: int,
        closure_id: int,
    ) -> None:
        connection.execute(
            """
            INSERT INTO dw.campanha_consolidada
                (tenant_id, campanha_eleicao_id, eleicao_id,
                 encerramento_campanha_id, nome_campanha,
                 cargo_pleiteado, ano_eleicao, tipo_eleicao, turno,
                 data_eleicao, votos_obtidos, total_votos_validos,
                 percentual_votos_validos, eleito, colocacao,
                 total_pessoas_vinculadas, total_intencoes_confirmadas,
                 total_liderancas, total_metas, quantidade_meta_total,
                 total_eventos, total_demandas, total_interacoes,
                 indicadores)
            SELECT ce.tenant_id, ce.id, ce.eleicao_id, ec.id,
                   ce.nome, ce.cargo_pleiteado, e.ano, e.tipo, e.turno,
                   e.data_eleicao, ec.votos_obtidos,
                   ec.total_votos_validos,
                   CASE WHEN COALESCE(ec.total_votos_validos, 0) > 0
                        THEN round(
                            ec.votos_obtidos * 100.0
                            / ec.total_votos_validos, 4
                        )
                        ELSE NULL END,
                   ec.eleito, ec.colocacao,
                   (SELECT count(*) FROM dw.pessoa_campanha_consolidada p
                     WHERE p.campanha_eleicao_id = ce.id),
                   (SELECT count(*) FROM dw.pessoa_campanha_consolidada p
                     WHERE p.campanha_eleicao_id = ce.id
                       AND p.intencao_confirmada),
                   (SELECT count(*)
                      FROM dw.lideranca_campanha_consolidada l
                     WHERE l.campanha_eleicao_id = ce.id),
                   (SELECT count(*) FROM dw.meta_campanha_consolidada m
                     WHERE m.campanha_eleicao_id = ce.id),
                   COALESCE((SELECT sum(m.quantidade_meta)
                      FROM dw.meta_campanha_consolidada m
                     WHERE m.campanha_eleicao_id = ce.id), 0),
                   (SELECT count(*) FROM agenda.evento ev
                     WHERE ev.campanha_eleicao_id = ce.id),
                   (SELECT count(*) FROM demanda.demanda d
                     WHERE d.campanha_eleicao_id = ce.id),
                   (SELECT count(*)
                      FROM comunicacao.atendimento_eleitor a
                     WHERE a.campanha_eleicao_id = ce.id),
                   jsonb_build_object(
                       'taxa_conversao_confirmada',
                       CASE WHEN (
                           SELECT count(*)
                           FROM dw.pessoa_campanha_consolidada p
                           WHERE p.campanha_eleicao_id = ce.id
                       ) > 0 THEN round((
                           SELECT count(*)
                           FROM dw.pessoa_campanha_consolidada p
                           WHERE p.campanha_eleicao_id = ce.id
                             AND p.intencao_confirmada
                       ) * 100.0 / (
                           SELECT count(*)
                           FROM dw.pessoa_campanha_consolidada p
                           WHERE p.campanha_eleicao_id = ce.id
                       ), 4) ELSE 0 END,
                       'fonte_resultado', ec.fonte_resultado,
                       'resultado_oficial_em', ec.resultado_oficial_em
                   )
              FROM eleicao.campanha_eleicao ce
              JOIN eleicao.eleicao e ON e.id = ce.eleicao_id
              JOIN eleicao.encerramento_campanha ec
                ON ec.campanha_eleicao_id = ce.id
             WHERE ce.tenant_id = %s
               AND ce.id = %s
               AND ec.id = %s
            """,
            (tenant_id, campaign_id, closure_id),
        )

    @staticmethod
    def _current_metrics(
        connection: psycopg.Connection[Any],
        tenant_id: int,
        campaign_id: int,
    ) -> dict[str, Any]:
        row = connection.execute(
            """
            SELECT votos_obtidos, eleito, total_pessoas_vinculadas,
                   total_intencoes_confirmadas, total_liderancas,
                   total_metas, total_eventos, total_demandas,
                   total_interacoes
              FROM dw.campanha_consolidada
             WHERE tenant_id = %s AND campanha_eleicao_id = %s
            """,
            (tenant_id, campaign_id),
        ).fetchone()
        if row is None:
            raise RuntimeError("Snapshot consolidado nao foi gerado.")
        return dict(row)
