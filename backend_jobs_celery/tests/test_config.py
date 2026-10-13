import pytest
from pydantic import ValidationError

from jobs.config import Settings
from jobs.database import normalize_database_url
from jobs.election_rollups import ElectionKey, ElectionRollupProcessor
from jobs.tasks import (
    enqueue_completeness,
    process_pending_election_rollups,
    recalculate_completeness,
)


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


def test_election_rollup_task_and_lock_key_are_stable() -> None:
    assert process_pending_election_rollups.name == "jobs.election_rollups.process_pending"
    key = ElectionKey(aa_eleicao=2024, cd_eleicao=619, nr_turno=1)
    assert key.lock_name == "tse-rollup:2024:619:1"


def test_election_rollup_settings_and_backfill_filter() -> None:
    settings = Settings(election_rollup_job_batch_size=100)
    assert settings.election_rollup_job_batch_size == 100
    with pytest.raises(ValidationError):
        Settings(election_rollup_job_batch_size=0)

    where, parameters = ElectionRollupProcessor._backfill_filter(2024, 619)
    assert where == "WHERE aa_eleicao = %s AND cd_eleicao = %s"
    assert parameters == (2024, 619)
