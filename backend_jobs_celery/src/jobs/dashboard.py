from datetime import date

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from jobs.database import normalize_database_url


class DashboardProcessor:
    def __init__(self, database_url: str) -> None:
        self.database_url = normalize_database_url(database_url)

    def materialize(self, tenant_id: int, reference_date: date) -> dict[str, int]:
        indicators = {
            "cadastros_total": (
                "SELECT count(*) FROM cadastro.pessoa WHERE tenant_id=%s "
                "AND ativo AND excluido_em IS NULL",
                (),
            ),
            "cadastros_novos": (
                "SELECT count(*) FROM cadastro.pessoa WHERE tenant_id=%s "
                "AND criado_em::date=%s AND excluido_em IS NULL",
                (reference_date,),
            ),
            "lideres_ativos": (
                "SELECT count(*) FROM cadastro.lideranca WHERE tenant_id=%s AND ativo",
                (),
            ),
            "liderados_ativos": (
                "SELECT count(DISTINCT pessoa_subordinada_id) "
                "FROM cadastro.hierarquia_lideranca WHERE tenant_id=%s AND ativo "
                "AND (data_fim IS NULL OR data_fim>=%s)",
                (reference_date,),
            ),
            "demandas_pendentes": (
                "SELECT count(*) FROM demanda.demanda d JOIN demanda.status_demanda s "
                "ON s.id=d.status_demanda_id WHERE d.tenant_id=%s AND d.excluido_em IS NULL "
                "AND NOT COALESCE(s.final,false)",
                (),
            ),
            "eventos_realizados": (
                "SELECT count(*) FROM agenda.evento e JOIN agenda.status_evento s "
                "ON s.id=e.status_evento_id WHERE e.tenant_id=%s "
                "AND e.data_inicio::date=%s AND e.excluido_em IS NULL "
                "AND s.codigo='realizado'",
                (reference_date,),
            ),
            "metas_em_risco": (
                "SELECT count(*) FROM meta.meta_voto WHERE tenant_id=%s AND status='em_risco'",
                (),
            ),
        }
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            connection.execute(
                "SELECT set_config('app.current_tenant_id', %s, true)", (str(tenant_id),)
            )
            written = 0
            for code, (query, extra) in indicators.items():
                value = connection.execute(query, (tenant_id, *extra)).fetchone()
                connection.execute(
                    """
                    INSERT INTO dw.indicador_valor
                      (tenant_id,indicador_id,data_referencia,recorte,valor)
                    SELECT %s,id,%s,'{}'::jsonb,%s FROM dw.indicador WHERE codigo=%s
                    ON CONFLICT (
                      tenant_id,indicador_id,data_referencia,
                      (COALESCE(territorio_id,0)),(COALESCE(lideranca_id,0)),recorte
                    ) DO UPDATE SET valor=EXCLUDED.valor,criado_em=now()
                    """,
                    (tenant_id, reference_date, value["count"], code),
                )
                written += 1
        return {"indicadores_materializados": written}

    def execute_scheduled_reports(self, tenant_id: int) -> dict[str, int]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            connection.execute(
                "SELECT set_config('app.current_tenant_id', %s, true)", (str(tenant_id),)
            )
            reports = connection.execute(
                """
                SELECT id,codigo FROM dw.relatorio
                WHERE (tenant_id IS NULL OR tenant_id=%s) AND automatico
                  AND agendamento_cron IS NOT NULL
                """,
                (tenant_id,),
            ).fetchall()
            for report in reports:
                connection.execute(
                    """
                    INSERT INTO dw.relatorio_execucao
                      (tenant_id,relatorio_id,parametros,status,iniciado_em,concluido_em)
                    VALUES (%s,%s,%s,'concluido',now(),now())
                    """,
                    (
                        tenant_id,
                        report["id"],
                        Jsonb({"origem": "agendamento", "codigo": report["codigo"]}),
                    ),
                )
        return {"relatorios_executados": len(reports)}
