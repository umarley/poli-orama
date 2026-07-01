from typing import Any

from jobs.celery_app import celery_app
from jobs.config import get_settings
from jobs.repository import JobRepository
from jobs.service import (
    enqueue_scheduled_completeness_jobs,
    execute_completeness_job,
    execute_test_job,
)


@celery_app.task(bind=True, name="jobs.test")  # type: ignore[untyped-decorator]
def test_job(_: Any, job_id: int, simulate_error: bool = False) -> dict[str, Any]:
    settings = get_settings()
    repository = JobRepository(settings.jobs_database_url)
    return execute_test_job(repository, job_id=job_id, simulate_error=simulate_error)


@celery_app.task(
    bind=True,
    name="jobs.cadastro.recalculate_completeness",
    acks_late=True,
    reject_on_worker_lost=True,
)  # type: ignore[untyped-decorator]
def recalculate_completeness(
    _: Any,
    job_id: int,
    tenant_id: int,
    batch_size: int | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    repository = JobRepository(settings.jobs_database_url)
    return execute_completeness_job(
        repository,
        job_id=job_id,
        tenant_id=tenant_id,
        batch_size=(settings.completeness_job_batch_size if batch_size is None else batch_size),
    )


@celery_app.task(name="jobs.cadastro.enqueue_completeness")  # type: ignore[untyped-decorator]
def enqueue_completeness() -> dict[str, int]:
    settings = get_settings()
    repository = JobRepository(settings.jobs_database_url)

    def dispatch(job_id: int, tenant_id: int, batch_size: int) -> str:
        result = recalculate_completeness.apply_async(
            kwargs={
                "job_id": job_id,
                "tenant_id": tenant_id,
                "batch_size": batch_size,
            }
        )
        return str(result.id)

    return enqueue_scheduled_completeness_jobs(
        repository,
        batch_size=settings.completeness_job_batch_size,
        dispatch=dispatch,
    )
