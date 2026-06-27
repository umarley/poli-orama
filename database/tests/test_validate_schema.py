import unittest
from pathlib import Path

from database.scripts.validate_schema import (
    DEFAULT_MIGRATION,
    normalize_database_url,
    parse_expected_structure,
    read_env_file,
)


class ValidateSchemaTests(unittest.TestCase):
    def test_extracts_schemas_and_tables_from_migration(self) -> None:
        expected = parse_expected_structure(DEFAULT_MIGRATION.read_text(encoding="utf-8"))

        self.assertIn("etl", expected.schemas)
        self.assertIn(("public", "tenant"), expected.tables)
        self.assertIn(("etl", "job_processamento"), expected.tables)
        self.assertIn(("etl", "log_processamento"), expected.tables)
        self.assertGreater(len(expected.tables), 50)

    def test_normalizes_sqlalchemy_async_url(self) -> None:
        self.assertEqual(
            normalize_database_url("postgresql+asyncpg://user:pass@db/app"),
            "postgresql://user:pass@db/app",
        )

    def test_reads_env_without_overwriting_process_environment(self) -> None:
        path = Path(__file__).with_name("fixture.env")
        try:
            path.write_text("# comment\nDATABASE_URL='postgresql://local/db'\n", encoding="utf-8")
            self.assertEqual(read_env_file(path)["DATABASE_URL"], "postgresql://local/db")
        finally:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
