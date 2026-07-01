import pytest
from pydantic import ValidationError

from jobs.config import Settings
from jobs.database import normalize_database_url
from jobs.tasks import enqueue_completeness, recalculate_completeness


def test_normalizes_backend_async_database_url() -> None:
    assert (
        normalize_database_url("postgresql+asyncpg://user:pass@db/app")
        == "postgresql://user:pass@db/app"
    )


def test_completeness_tasks_have_stable_queue_names() -> None:
    assert recalculate_completeness.name == "jobs.cadastro.recalculate_completeness"
    assert enqueue_completeness.name == "jobs.cadastro.enqueue_completeness"


def test_completeness_schedule_settings_validate_limits() -> None:
    settings = Settings(
        completeness_job_hour=23,
        completeness_job_minute=59,
        completeness_job_batch_size=10000,
    )
    assert settings.completeness_job_batch_size == 10000

    with pytest.raises(ValidationError):
        Settings(completeness_job_batch_size=0)
