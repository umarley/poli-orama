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
    goals_job_enabled: bool = True
    goals_job_interval_minutes: int = Field(default=15, ge=1, le=1440)
    agenda_reminders_enabled: bool = True
    agenda_reminders_interval_minutes: int = Field(default=15, ge=1, le=1440)
    agenda_reminder_lead_hours: int = Field(default=24, ge=1, le=720)
    agenda_nlp_enabled: bool = True
    agenda_nlp_hour: int = Field(default=3, ge=0, le=23)
    agenda_nlp_minimum_frequency: int = Field(default=2, ge=2, le=100)
    demand_deadlines_enabled: bool = True
    demand_deadlines_hour: int = Field(default=7, ge=0, le=23)
    demand_deadlines_lead_days: int = Field(default=3, ge=0, le=30)


@lru_cache
def get_settings() -> Settings:
    return Settings()
