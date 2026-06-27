from jobs.database import normalize_database_url


def test_normalizes_backend_async_database_url() -> None:
    assert (
        normalize_database_url("postgresql+asyncpg://user:pass@db/app")
        == "postgresql://user:pass@db/app"
    )
