"""Lembretes internos e analise deterministica de temas da agenda."""

import re
import unicodedata
from collections import Counter
from datetime import UTC, datetime, timedelta

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from jobs.database import normalize_database_url

STOP_WORDS = {
    "a",
    "ao",
    "aos",
    "as",
    "com",
    "da",
    "das",
    "de",
    "do",
    "dos",
    "e",
    "em",
    "evento",
    "na",
    "nas",
    "no",
    "nos",
    "o",
    "os",
    "para",
    "por",
    "que",
    "reuniao",
    "uma",
    "um",
}


def extract_topics(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKD", text.lower())
    ascii_text = "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )
    return [
        token
        for token in re.findall(r"[a-z]{4,}", ascii_text)
        if token not in STOP_WORDS
    ]


class AgendaProcessor:
    def __init__(self, database_url: str) -> None:
        self.database_url = normalize_database_url(database_url)

    def generate_reminders(
        self,
        *,
        tenant_id: int,
        lead_hours: int = 24,
        now: datetime | None = None,
    ) -> dict[str, int]:
        reference = now or datetime.now(UTC)
        end = reference + timedelta(hours=lead_hours)
        generated = 0
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            connection.execute(
                "SELECT set_config('app.current_tenant_id', %s, true)",
                (str(tenant_id),),
            )
            events = connection.execute(
                """
                SELECT e.id, e.titulo, e.data_inicio
                FROM agenda.evento e
                JOIN agenda.status_evento s ON s.id = e.status_evento_id
                WHERE e.tenant_id = %s AND e.excluido_em IS NULL
                  AND s.codigo IN ('planejado', 'confirmado', 'remarcado')
                  AND e.data_inicio >= %s AND e.data_inicio <= %s
                ORDER BY e.data_inicio
                """,
                (tenant_id, reference, end),
            ).fetchall()
            users = connection.execute(
                """
                SELECT DISTINCT u.id
                FROM auth.usuario u
                JOIN auth.usuario_perfil up
                  ON up.usuario_id = u.id AND up.tenant_id = u.tenant_id
                JOIN auth.perfil_permissao pp ON pp.perfil_acesso_id = up.perfil_acesso_id
                JOIN auth.permissao p ON p.id = pp.permissao_id
                WHERE u.tenant_id = %s AND u.status = 'ativo'
                  AND p.codigo = 'agenda.visualizar'
                """,
                (tenant_id,),
            ).fetchall()
            for event in events:
                scheduled = event["data_inicio"] - timedelta(hours=lead_hours)
                reminder_type = (
                    "evento_hoje"
                    if event["data_inicio"].date() == reference.date()
                    else "evento_proximo"
                )
                for user in users:
                    row = connection.execute(
                        """
                        INSERT INTO agenda.lembrete_evento
                            (tenant_id, evento_id, usuario_id, tipo, mensagem,
                             agendado_para, status, gerado_em)
                        VALUES (%s, %s, %s, %s, %s, %s, 'gerado', now())
                        ON CONFLICT
                            (tenant_id, evento_id, usuario_id, tipo, agendado_para)
                        DO NOTHING
                        RETURNING id
                        """,
                        (
                            tenant_id,
                            event["id"],
                            user["id"],
                            reminder_type,
                            f"Evento proximo: {event['titulo']}"[:255],
                            scheduled,
                        ),
                    ).fetchone()
                    generated += int(row is not None)
        return {
            "tenant_id": tenant_id,
            "eventos_encontrados": len(events),
            "lembretes_gerados": generated,
        }

    def analyze_topics(
        self,
        *,
        tenant_id: int,
        minimum_frequency: int = 2,
    ) -> dict[str, int]:
        counters: dict[str, Counter[str]] = {
            "tema_recorrente": Counter(),
            "demanda_recorrente": Counter(),
        }
        latest_event: dict[tuple[str, str], int] = {}
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            connection.execute(
                "SELECT set_config('app.current_tenant_id', %s, true)",
                (str(tenant_id),),
            )
            agenda_rows = connection.execute(
                """
                SELECT p.evento_id,
                       concat_ws(' ', p.titulo, p.descricao, p.encaminhamento,
                                 c.origem, c.descricao) AS texto
                FROM agenda.pauta_evento p
                LEFT JOIN agenda.convite c
                  ON c.evento_id = p.evento_id AND c.tenant_id = p.tenant_id
                WHERE p.tenant_id = %s
                """,
                (tenant_id,),
            ).fetchall()
            demand_rows = connection.execute(
                """
                SELECT evento_id, concat_ws(' ', titulo, descricao) AS texto
                FROM demanda.demanda
                WHERE tenant_id = %s AND evento_id IS NOT NULL
                  AND excluido_em IS NULL
                """,
                (tenant_id,),
            ).fetchall()
            for category, rows in (
                ("tema_recorrente", agenda_rows),
                ("demanda_recorrente", demand_rows),
            ):
                for row in rows:
                    for topic in set(extract_topics(str(row["texto"] or ""))):
                        counters[category][topic] += 1
                        latest_event[(category, topic)] = int(row["evento_id"])
            connection.execute(
                "DELETE FROM agenda.insight_evento WHERE tenant_id = %s "
                "AND tipo IN ('tema_recorrente', 'demanda_recorrente')",
                (tenant_id,),
            )
            inserted = 0
            for category, counter in counters.items():
                for topic, frequency in counter.items():
                    if frequency < minimum_frequency:
                        continue
                    score = min(100, 40 + frequency * 10)
                    connection.execute(
                        """
                        INSERT INTO agenda.insight_evento
                            (tenant_id, evento_id, tipo, tema, frequencia,
                             score, detalhes)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            tenant_id,
                            latest_event[(category, topic)],
                            category,
                            topic,
                            frequency,
                            score,
                            Jsonb({"algoritmo": "frequencia_lexical_v1"}),
                        ),
                    )
                    inserted += 1
        return {
            "tenant_id": tenant_id,
            "registros_analisados": len(agenda_rows) + len(demand_rows),
            "insights_gerados": inserted,
        }
