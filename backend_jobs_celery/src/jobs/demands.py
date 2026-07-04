from datetime import date, timedelta
from typing import Any

import psycopg
from psycopg.rows import dict_row

from jobs.database import normalize_database_url


class DemandDeadlineProcessor:
    def __init__(self, database_url: str) -> None:
        self.database_url = normalize_database_url(database_url)

    def generate_alerts(
        self,
        *,
        tenant_id: int,
        lead_days: int,
        reference_date: date | None = None,
    ) -> dict[str, Any]:
        today = reference_date or date.today()
        limit = today + timedelta(days=lead_days)
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            connection.execute(
                "SELECT set_config('app.current_tenant_id', %s, true)",
                (str(tenant_id),),
            )
            resolved = connection.execute(
                """
                UPDATE demanda.alerta_prazo a
                SET status='resolvido'
                WHERE a.tenant_id=%s AND a.status='aberto'
                  AND NOT EXISTS (
                    SELECT 1
                    FROM demanda.demanda d
                    JOIN demanda.status_demanda s ON s.id=d.status_demanda_id
                    WHERE d.id=a.demanda_id AND d.tenant_id=a.tenant_id
                      AND d.excluido_em IS NULL AND NOT s.final
                      AND d.prazo IS NOT NULL
                      AND (
                        (a.tipo='vencido' AND d.prazo<%s)
                        OR (a.tipo='vencendo' AND d.prazo BETWEEN %s AND %s)
                      )
                  )
                """,
                (tenant_id, today, today, limit),
            ).rowcount
            rows = connection.execute(
                """
                SELECT d.id,d.protocolo,d.prazo,d.responsavel_atendimento_id,
                       CASE WHEN d.prazo<%s THEN 'vencido' ELSE 'vencendo' END tipo
                FROM demanda.demanda d
                JOIN demanda.status_demanda s ON s.id=d.status_demanda_id
                WHERE d.tenant_id=%s AND d.excluido_em IS NULL AND NOT s.final
                  AND d.prazo IS NOT NULL AND d.prazo<=%s
                """,
                (today, tenant_id, limit),
            ).fetchall()
            created = 0
            by_type = {"vencendo": 0, "vencido": 0}
            for row in rows:
                message = (
                    f"Demanda {row['protocolo'] or row['id']} "
                    + (
                        f"venceu em {row['prazo']:%d/%m/%Y}."
                        if row["tipo"] == "vencido"
                        else f"vence em {row['prazo']:%d/%m/%Y}."
                    )
                )
                inserted = connection.execute(
                    """
                    INSERT INTO demanda.alerta_prazo
                        (tenant_id,demanda_id,responsavel_atendimento_id,tipo,
                         mensagem,data_referencia)
                    VALUES (%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (tenant_id,demanda_id,tipo,data_referencia)
                    DO NOTHING
                    """,
                    (
                        tenant_id,
                        row["id"],
                        row["responsavel_atendimento_id"],
                        row["tipo"],
                        message,
                        row["prazo"],
                    ),
                ).rowcount
                created += inserted
                by_type[str(row["tipo"])] += inserted
        return {
            "tenant_id": tenant_id,
            "alertas_criados": created,
            "alertas_vencendo": by_type["vencendo"],
            "alertas_vencidos": by_type["vencido"],
            "alertas_resolvidos": resolved,
        }
