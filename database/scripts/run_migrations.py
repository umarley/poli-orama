"""Aplica as migrations SQL de database/migrations em ordem numerica.

Cada arquivo segue o padrao 'NNN - descricao.sql'. O script conecta uma unica
vez no PostgreSQL, garante uma tabela de controle (public.schema_migrations) e
aplica, em ordem, apenas as migrations ainda nao registradas. Cada arquivo e
enviado ao PostgreSQL como um unico script (protocolo simple query), portanto
blocos $$ ... $$ e BEGIN/COMMIT proprios de cada migration sao respeitados.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
from pathlib import Path

import asyncpg

ROOT_DIR = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = ROOT_DIR / "database" / "migrations"
DEFAULT_ENV_FILE = ROOT_DIR / "backend_core" / ".env"

MIGRATION_FILENAME_PATTERN = re.compile(r"^(\d+)\s*-\s*.+\.sql$", re.IGNORECASE)

CONTROL_SCHEMA = "public"
CONTROL_TABLE = "schema_migrations"


def read_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("\"'")
    return values


def normalize_database_url(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://", 1).replace(
        "postgres+asyncpg://", "postgresql://", 1
    )


def migration_number(path: Path) -> int:
    match = MIGRATION_FILENAME_PATTERN.match(path.name)
    if not match:
        raise SystemExit(
            f"Nome de migration invalido (esperado 'NNN - descricao.sql'): {path.name}"
        )
    return int(match.group(1))


def discover_migrations(migrations_dir: Path) -> list[Path]:
    paths = sorted(migrations_dir.glob("*.sql"), key=migration_number)
    seen: dict[int, Path] = {}
    for path in paths:
        number = migration_number(path)
        if number in seen:
            raise SystemExit(
                f"Numero de sequencia duplicado ({number:03d}): "
                f"{seen[number].name} e {path.name}"
            )
        seen[number] = path
    return paths


async def ensure_control_table(connection: asyncpg.Connection) -> None:
    await connection.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {CONTROL_SCHEMA}.{CONTROL_TABLE} (
            filename text PRIMARY KEY,
            applied_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )


async def fetch_applied(connection: asyncpg.Connection) -> set[str]:
    rows = await connection.fetch(f"SELECT filename FROM {CONTROL_SCHEMA}.{CONTROL_TABLE}")
    return {row["filename"] for row in rows}


async def apply_migration(connection: asyncpg.Connection, path: Path) -> None:
    sql = path.read_text(encoding="utf-8")
    await connection.execute(sql)
    await connection.execute(
        f"""
        INSERT INTO {CONTROL_SCHEMA}.{CONTROL_TABLE} (filename)
        VALUES ($1)
        ON CONFLICT (filename) DO NOTHING
        """,
        path.name,
    )


async def run(
    database_url: str,
    migrations_dir: Path,
    *,
    dry_run: bool,
    force: bool,
    until: int | None,
) -> int:
    migrations = discover_migrations(migrations_dir)
    if until is not None:
        migrations = [path for path in migrations if migration_number(path) <= until]

    connection = await asyncpg.connect(normalize_database_url(database_url))
    try:
        await ensure_control_table(connection)
        applied = set() if force else await fetch_applied(connection)
        pending = [path for path in migrations if path.name not in applied]

        if not pending:
            print("Nenhuma migration pendente.")
            return 0

        print(f"{len(pending)} migration(ns) pendente(s):")
        for path in pending:
            print(f"  - {path.name}")

        if dry_run:
            print("Modo --dry-run: nenhuma alteracao foi aplicada.")
            return 0

        for path in pending:
            print(f"Aplicando {path.name} ...")
            try:
                await apply_migration(connection, path)
            except Exception as exc:
                print(f"ERRO ao aplicar {path.name}: {exc}", file=sys.stderr)
                return 1
            print(f"  OK {path.name}")

        print(f"Concluido: {len(pending)} migration(ns) aplicada(s).")
        return 0
    finally:
        await connection.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Aplica em ordem as migrations SQL de database/migrations."
    )
    parser.add_argument(
        "--database-url", help="URL PostgreSQL administrativa; sobrescreve o ambiente."
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=DEFAULT_ENV_FILE,
        help="Arquivo que contem DATABASE_ADMIN_URL ou DATABASE_URL.",
    )
    parser.add_argument(
        "--migrations-dir",
        type=Path,
        default=MIGRATIONS_DIR,
        help="Diretorio com os arquivos de migration.",
    )
    parser.add_argument(
        "--until",
        type=int,
        metavar="N",
        help="Aplica somente ate a migration de numero N (inclusive).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reaplica migrations ja registradas em schema_migrations (uso cauteloso).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Lista as migrations pendentes sem executa-las.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    env_values = read_env_file(args.env_file)
    database_url = (
        args.database_url
        or os.getenv("DATABASE_ADMIN_URL")
        or os.getenv("DATABASE_URL")
        or env_values.get("DATABASE_ADMIN_URL")
        or env_values.get("DATABASE_URL")
    )
    if not database_url:
        raise SystemExit(
            "Defina DATABASE_ADMIN_URL (ou DATABASE_URL) via argumento, ambiente ou --env-file."
        )
    if not args.migrations_dir.is_dir():
        raise SystemExit(f"Diretorio de migrations nao encontrado: {args.migrations_dir}")

    return asyncio.run(
        run(
            database_url,
            args.migrations_dir,
            dry_run=args.dry_run,
            force=args.force,
            until=args.until,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
