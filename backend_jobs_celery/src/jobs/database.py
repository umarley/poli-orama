def normalize_database_url(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://", 1).replace(
        "postgres+asyncpg://", "postgresql://", 1
    )
