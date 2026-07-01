from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    environment: Literal["local", "test", "staging", "production"] = "local"
    log_level: str = "INFO"
    jobs_database_url: str = (
        "postgresql://app_inteligencia:change_me@localhost:5432/inteligencia_politica"
    )
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    celery_task_always_eager: bool = False
    celery_task_eager_propagates: bool = False
    completeness_job_enabled: bool = True
    completeness_job_hour: int = Field(default=2, ge=0, le=23)
    completeness_job_minute: int = Field(default=30, ge=0, le=59)
    completeness_job_batch_size: int = Field(default=1000, ge=1, le=10000)


@lru_cache
def get_settings() -> Settings:
    return Settings()
