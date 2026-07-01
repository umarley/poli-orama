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
                                        WHEN pessoa.data_nascimento IS NOT NULL THEN 10
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
