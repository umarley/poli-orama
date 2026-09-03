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

    def test_agenda_evolution_migration_contains_google_and_access_tables(self) -> None:
        migration = DEFAULT_MIGRATION.parent / "049 - agendas_classificacao_permissoes_google_calendar.sql"
        expected = parse_expected_structure(migration.read_text(encoding="utf-8"))

        self.assertIn(("agenda", "agenda"), expected.tables)
        self.assertIn(("agenda", "agenda_usuario"), expected.tables)
        self.assertIn(("agenda", "google_integracao_agenda"), expected.tables)
        self.assertIn(("agenda", "google_evento_vinculo"), expected.tables)

    def test_reads_env_without_overwriting_process_environment(self) -> None:
        path = Path(__file__).with_name("fixture.env")
        try:
            path.write_text("# comment\nDATABASE_URL='postgresql://local/db'\n", encoding="utf-8")
            self.assertEqual(read_env_file(path)["DATABASE_URL"], "postgresql://local/db")
        finally:
            path.unlink(missing_ok=True)

    def test_contract_migration_creates_dedicated_schema_and_tables(self) -> None:
        migration = DEFAULT_MIGRATION.parent / "050 - gestao_contratos_campanha.sql"
        expected = parse_expected_structure(migration.read_text(encoding="utf-8"))

        self.assertIn("contrato", expected.schemas)
        self.assertIn(("contrato", "pessoa_juridica"), expected.tables)
        self.assertIn(("contrato", "contrato"), expected.tables)
        sql = migration.read_text(encoding="utf-8")
        self.assertIn("pa.codigo = 'tesoureiro'", sql)
        self.assertNotIn("pa.codigo IN ('gestor'", sql)

    def test_resultados_eleicoes_migration_creates_tse_table(self) -> None:
        migration = DEFAULT_MIGRATION.parent / "053 - tse_resultados_eleicoes.sql"
        expected = parse_expected_structure(migration.read_text(encoding="utf-8"))

        self.assertIn("tse", expected.schemas)
        self.assertIn(("tse", "resultados_eleicoes"), expected.tables)
        sql = migration.read_text(encoding="utf-8")
        self.assertIn("aa_eleicao", sql)
        self.assertIn("nr_votavel", sql)
        self.assertIn("qt_votos", sql)

    def test_gestao_eleitoral_migration_grants_permission_to_campaign_managers(self) -> None:
        migration = DEFAULT_MIGRATION.parent / "054 - gestao_eleitoral_permissoes.sql"
        sql = migration.read_text(encoding="utf-8")
        self.assertIn("gestao_eleitoral.visualizar", sql)
        self.assertIn("coordenador_territorial", sql)
        self.assertIn("ix_resultados_eleicoes_eleicao_turno", sql)


if __name__ == "__main__":
    unittest.main()
