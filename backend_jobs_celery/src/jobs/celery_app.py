from celery import Celery

from jobs.config import get_settings

settings = get_settings()

celery_app = Celery(
    "vurix_jobs",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["jobs.tasks"],
)
celery_app.conf.update(
    accept_content=["json"],
    task_serializer="json",
    result_serializer="json",
    timezone="America/Sao_Paulo",
    enable_utc=True,
    task_track_started=True,
    task_always_eager=settings.celery_task_always_eager,
    task_eager_propagates=settings.celery_task_eager_propagates,
    worker_hijack_root_logger=False,
)
