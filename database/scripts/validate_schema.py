from __future__ import annotations

import argparse
import asyncio
import os
import re
from dataclasses import dataclass
from pathlib import Path

import asyncpg

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_MIGRATION = ROOT_DIR / "database" / "migrations" / "001 - ddl_inteligencia_politica.sql"

SCHEMA_PATTERN = re.compile(
    r"^\s*CREATE\s+SCHEMA\s+IF\s+NOT\s+EXISTS\s+([a-z_][a-z0-9_]*)",
    re.IGNORECASE | re.MULTILINE,
)
TABLE_PATTERN = re.compile(
    r"^\s*CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?"
    r"([a-z_][a-z0-9_]*)\.([a-z_][a-z0-9_]*)",
    re.IGNORECASE | re.MULTILINE,
)


@dataclass(frozen=True, slots=True)
class ExpectedStructure:
    schemas: frozenset[str]
    tables: frozenset[tuple[str, str]]


@dataclass(frozen=True, slots=True)
class ValidationResult:
    expected: ExpectedStructure
    existing_schemas: frozenset[str]
    existing_tables: frozenset[tuple[str, str]]

    @property
    def missing_schemas(self) -> frozenset[str]:
        return self.expected.schemas - self.existing_schemas

    @property
    def missing_tables(self) -> frozenset[tuple[str, str]]:
        return self.expected.tables - self.existing_tables

    @property
    def is_valid(self) -> bool:
        return not self.missing_schemas and not self.missing_tables


def parse_expected_structure(sql: str) -> ExpectedStructure:
    tables = frozenset(
        (schema.lower(), table.lower()) for schema, table in TABLE_PATTERN.findall(sql)
    )
    schemas = {schema.lower() for schema in SCHEMA_PATTERN.findall(sql)}
    schemas.update(schema for schema, _ in tables)
    return ExpectedStructure(schemas=frozenset(schemas), tables=tables)


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


async def validate(database_url: str, expected: ExpectedStructure) -> ValidationResult:
    connection = await asyncpg.connect(normalize_database_url(database_url))
    try:
        existing_schemas = frozenset(
            await connection.fetchval(
                """
                SELECT coalesce(array_agg(schema_name::text), ARRAY[]::text[])
                FROM information_schema.schemata
                WHERE schema_name = ANY($1::text[])
                """,
                sorted(expected.schemas),
            )
        )
        rows = await connection.fetch(
            """
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_type = 'BASE TABLE'
              AND table_schema = ANY($1::text[])
            """,
            sorted(expected.schemas),
        )
        existing_tables = frozenset((row["table_schema"], row["table_name"]) for row in rows)
    finally:
        await connection.close()
    return ValidationResult(expected, existing_schemas, existing_tables)


def print_result(result: ValidationResult) -> None:
    print("Schemas esperados:")
    for schema in sorted(result.expected.schemas):
        marker = "OK" if schema in result.existing_schemas else "AUSENTE"
        print(f"  [{marker}] {schema}")

    print("Tabelas esperadas:")
    for schema, table in sorted(result.expected.tables):
        marker = "OK" if (schema, table) in result.existing_tables else "AUSENTE"
        print(f"  [{marker}] {schema}.{table}")

    print(
        f"Resumo: {len(result.expected.schemas) - len(result.missing_schemas)}/"
        f"{len(result.expected.schemas)} schemas, "
        f"{len(result.expected.tables) - len(result.missing_tables)}/"
        f"{len(result.expected.tables)} tabelas."
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compara schemas e tabelas do PostgreSQL com a migration."
    )
    parser.add_argument("--database-url", help="URL PostgreSQL; sobrescreve o ambiente.")
    parser.add_argument(
        "--env-file",
        type=Path,
        default=ROOT_DIR / "backend_core" / ".env",
        help="Arquivo que contem DATABASE_URL.",
    )
    parser.add_argument(
        "--migration",
        type=Path,
        default=DEFAULT_MIGRATION,
        help="Migration usada como fonte da estrutura esperada.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    env_values = read_env_file(args.env_file)
    database_url = args.database_url or os.getenv("DATABASE_URL") or env_values.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL nao definida via argumento, ambiente ou --env-file.")

    expected = parse_expected_structure(args.migration.read_text(encoding="utf-8"))
    result = asyncio.run(validate(database_url, expected))
    print_result(result)
    return 0 if result.is_valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
