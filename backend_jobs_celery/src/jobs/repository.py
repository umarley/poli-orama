from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from jobs.database import normalize_database_url


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
