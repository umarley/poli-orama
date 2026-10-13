from __future__ import annotations

from dataclasses import dataclass

import psycopg
from psycopg.rows import dict_row

from jobs.database import normalize_database_url


@dataclass(frozen=True)
class ElectionKey:
    aa_eleicao: int
    cd_eleicao: int
    nr_turno: int

    @property
    def lock_name(self) -> str:
        return f"tse-rollup:{self.aa_eleicao}:{self.cd_eleicao}:{self.nr_turno}"


class ElectionRollupProcessor:
    def __init__(self, database_url: str) -> None:
        self.database_url = normalize_database_url(database_url)

    def list_pending(self, limit: int) -> list[ElectionKey]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            rows = connection.execute(
                """
                SELECT aa_eleicao, cd_eleicao, nr_turno
                  FROM tse.resultado_rollup_controle
                 WHERE status = 'pending'
                 ORDER BY solicitado_em
                 LIMIT %s
                """,
                (limit,),
            ).fetchall()
        return [ElectionKey(**row) for row in rows]

    def refresh(self, key: ElectionKey) -> int | None:
        try:
            with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
                locked = connection.execute(
                    "SELECT pg_try_advisory_xact_lock(hashtextextended(%s, 0)) AS locked",
                    (key.lock_name,),
                ).fetchone()
                if locked is None or not locked["locked"]:
                    return None

                claimed = connection.execute(
                    """
                    UPDATE tse.resultado_rollup_controle
                       SET status = 'refreshing', iniciado_em = now(), ultima_mensagem = NULL
                     WHERE aa_eleicao = %s AND cd_eleicao = %s AND nr_turno = %s
                       AND status = 'pending'
                    RETURNING aa_eleicao
                    """,
                    (key.aa_eleicao, key.cd_eleicao, key.nr_turno),
                ).fetchone()
                if claimed is None:
                    return None

                row = connection.execute(
                    "SELECT tse.fn_refresh_resultado_rollup(%s, %s, %s) AS generation",
                    (key.aa_eleicao, key.cd_eleicao, key.nr_turno),
                ).fetchone()
                if row is None:
                    raise RuntimeError("funcao de rollup nao retornou uma geracao")
                return int(row["generation"])
        except Exception as exc:
            # A transacao de refresh foi revertida; a chave permanece pending e
            # pode ser tentada novamente pelo beat. Registra apenas erro seguro.
            with psycopg.connect(self.database_url) as connection:
                connection.execute(
                    """
                    UPDATE tse.resultado_rollup_controle
                       SET status = 'pending', ultima_mensagem = %s
                     WHERE aa_eleicao = %s AND cd_eleicao = %s AND nr_turno = %s
                    """,
                    (
                        f"{type(exc).__name__}: {str(exc)[:500]}",
                        key.aa_eleicao,
                        key.cd_eleicao,
                        key.nr_turno,
                    ),
                )
            raise

    def process_pending(self, limit: int) -> dict[str, int]:
        refreshed = skipped = failed = 0
        for key in self.list_pending(limit):
            try:
                generation = self.refresh(key)
            except Exception:
                failed += 1
            else:
                if generation is None:
                    skipped += 1
                else:
                    refreshed += 1
        return {"atualizados": refreshed, "ignorados": skipped, "falhas": failed}

    def count_backfill_candidates(
        self, *, aa_eleicao: int | None = None, cd_eleicao: int | None = None
    ) -> int:
        where, parameters = self._backfill_filter(aa_eleicao, cd_eleicao)
        with psycopg.connect(self.database_url) as connection:
            row = connection.execute(
                f"""
                SELECT COUNT(*) FROM (
                    SELECT DISTINCT aa_eleicao, cd_eleicao, nr_turno
                      FROM tse.resultados_eleicoes
                     {where}
                ) candidates
                """,
                parameters,
            ).fetchone()
        return int(row[0]) if row else 0

    def mark_backfill_pending(
        self, *, aa_eleicao: int | None = None, cd_eleicao: int | None = None
    ) -> int:
        where, parameters = self._backfill_filter(aa_eleicao, cd_eleicao)
        with psycopg.connect(self.database_url) as connection:
            cursor = connection.execute(
                f"""
                INSERT INTO tse.resultado_rollup_controle (
                    aa_eleicao, cd_eleicao, nr_turno, status, solicitado_em
                )
                SELECT DISTINCT aa_eleicao, cd_eleicao, nr_turno, 'pending', now()
                  FROM tse.resultados_eleicoes
                 {where}
                ON CONFLICT (aa_eleicao, cd_eleicao, nr_turno)
                DO UPDATE SET status = 'pending', solicitado_em = EXCLUDED.solicitado_em,
                              ultima_mensagem = NULL
                """,
                parameters,
            )
            return cursor.rowcount

    @staticmethod
    def _backfill_filter(
        aa_eleicao: int | None, cd_eleicao: int | None
    ) -> tuple[str, tuple[int, ...]]:
        clauses: list[str] = []
        parameters: list[int] = []
        if aa_eleicao is not None:
            clauses.append("aa_eleicao = %s")
            parameters.append(aa_eleicao)
        if cd_eleicao is not None:
            clauses.append("cd_eleicao = %s")
            parameters.append(cd_eleicao)
        return (
            ("WHERE " + " AND ".join(clauses)) if clauses else "",
            tuple(parameters),
        )
