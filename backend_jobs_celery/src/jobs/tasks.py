from typing import Any

from jobs.celery_app import celery_app
from jobs.config import get_settings
from jobs.repository import JobRepository
from jobs.service import execute_test_job


@celery_app.task(bind=True, name="jobs.test")  # type: ignore[untyped-decorator]
def test_job(_: Any, job_id: int, simulate_error: bool = False) -> dict[str, Any]:
    settings = get_settings()
    repository = JobRepository(settings.jobs_database_url)
    return execute_test_job(repository, job_id=job_id, simulate_error=simulate_error)
