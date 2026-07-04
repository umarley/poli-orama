from typing import Any

from jobs.agenda import AgendaProcessor
from jobs.celery_app import celery_app
from jobs.config import get_settings
from jobs.demands import DemandDeadlineProcessor
from jobs.imports import ImportProcessor
from jobs.repository import JobRepository
from jobs.service import (
    enqueue_scheduled_completeness_jobs,
    enqueue_scheduled_goals_jobs,
    execute_completeness_job,
    execute_goals_job,
    execute_test_job,
)


@celery_app.task(
    bind=True,
    name="jobs.metas.recalculate",
    acks_late=True,
    reject_on_worker_lost=True,
)  # type: ignore[untyped-decorator]
def recalculate_goals(_: Any, job_id: int, tenant_id: int) -> dict[str, Any]:
    settings = get_settings()
    repository = JobRepository(settings.jobs_database_url)
    return execute_goals_job(repository, job_id=job_id, tenant_id=tenant_id)


@celery_app.task(name="jobs.metas.enqueue_recalculation")  # type: ignore[untyped-decorator]
def enqueue_goals_recalculation() -> dict[str, int]:
    settings = get_settings()
    repository = JobRepository(settings.jobs_database_url)

    def dispatch(job_id: int, tenant_id: int) -> str:
        result = recalculate_goals.apply_async(
            kwargs={"job_id": job_id, "tenant_id": tenant_id}
        )
        return str(result.id)

    return enqueue_scheduled_goals_jobs(repository, dispatch=dispatch)


@celery_app.task(
    bind=True,
    name="jobs.etl.process_import",
    acks_late=True,
    reject_on_worker_lost=True,
)  # type: ignore[untyped-decorator]
def process_import(
    _: Any, job_id: int, tenant_id: int, import_id: int
) -> dict[str, Any]:
    settings = get_settings()
    repository = JobRepository(settings.jobs_database_url)
    repository.mark_started(job_id)
    try:
        metrics = ImportProcessor(settings.jobs_database_url).process(
            tenant_id=tenant_id, import_id=import_id
        )
        repository.mark_succeeded(job_id, {"importacao_id": import_id, **metrics})
        return {"job_id": job_id, "status": "concluido", **metrics}
    except Exception as exc:
        ImportProcessor(settings.jobs_database_url).fail(
            tenant_id=tenant_id, import_id=import_id, message=str(exc)
        )
        repository.mark_failed(
            job_id,
            {
                "tenant_id": tenant_id,
                "importacao_id": import_id,
                "error_type": type(exc).__name__,
            },
        )
        raise


@celery_app.task(
    bind=True,
    name="jobs.etl.load_import",
    acks_late=True,
    reject_on_worker_lost=True,
)  # type: ignore[untyped-decorator]
def load_import(
    _: Any, job_id: int, tenant_id: int, import_id: int
) -> dict[str, Any]:
    settings = get_settings()
    repository = JobRepository(settings.jobs_database_url)
    repository.mark_started(job_id)
    try:
        metrics = ImportProcessor(settings.jobs_database_url).load(
            tenant_id=tenant_id, import_id=import_id
        )
        repository.mark_succeeded(job_id, {"importacao_id": import_id, **metrics})
        return {"job_id": job_id, "status": "concluido", **metrics}
    except Exception as exc:
        ImportProcessor(settings.jobs_database_url).fail(
            tenant_id=tenant_id, import_id=import_id, message=str(exc)
        )
        repository.mark_failed(
            job_id,
            {
                "tenant_id": tenant_id,
                "importacao_id": import_id,
                "error_type": type(exc).__name__,
            },
        )
        raise


@celery_app.task(
    bind=True,
    name="jobs.agenda.generate_reminders",
    acks_late=True,
    reject_on_worker_lost=True,
)  # type: ignore[untyped-decorator]
def generate_agenda_reminders(
    _: Any,
    job_id: int,
    tenant_id: int,
    lead_hours: int,
) -> dict[str, Any]:
    settings = get_settings()
    repository = JobRepository(settings.jobs_database_url)
    repository.mark_started(job_id)
    try:
        metrics = AgendaProcessor(settings.jobs_database_url).generate_reminders(
            tenant_id=tenant_id,
            lead_hours=lead_hours,
        )
        repository.mark_succeeded(job_id, metrics)
        return {"job_id": job_id, "status": "concluido", **metrics}
    except Exception as exc:
        repository.mark_failed(
            job_id,
            {"tenant_id": tenant_id, "error_type": type(exc).__name__},
        )
        raise


@celery_app.task(name="jobs.agenda.enqueue_reminders")  # type: ignore[untyped-decorator]
def enqueue_agenda_reminders() -> dict[str, int]:
    settings = get_settings()
    repository = JobRepository(settings.jobs_database_url)
    enqueued = skipped = failures = 0
    for tenant_id in repository.list_active_tenant_ids():
        job_id = repository.create_if_idle(
            job_type="outro",
            reference="agenda_lembretes",
            parameters={"lead_hours": settings.agenda_reminder_lead_hours},
            tenant_id=tenant_id,
        )
        if job_id is None:
            skipped += 1
            continue
        try:
            generate_agenda_reminders.apply_async(
                kwargs={
                    "job_id": job_id,
                    "tenant_id": tenant_id,
                    "lead_hours": settings.agenda_reminder_lead_hours,
                }
            )
            enqueued += 1
        except Exception:
            repository.mark_failed(job_id, {"fase": "despacho"})
            failures += 1
    return {"enfileirados": enqueued, "ignorados": skipped, "falhas": failures}


@celery_app.task(
    bind=True,
    name="jobs.agenda.analyze_topics",
    acks_late=True,
    reject_on_worker_lost=True,
)  # type: ignore[untyped-decorator]
def analyze_agenda_topics(
    _: Any,
    job_id: int,
    tenant_id: int,
    minimum_frequency: int,
) -> dict[str, Any]:
    settings = get_settings()
    repository = JobRepository(settings.jobs_database_url)
    repository.mark_started(job_id)
    try:
        metrics = AgendaProcessor(settings.jobs_database_url).analyze_topics(
            tenant_id=tenant_id,
            minimum_frequency=minimum_frequency,
        )
        repository.mark_succeeded(job_id, metrics)
        return {"job_id": job_id, "status": "concluido", **metrics}
    except Exception as exc:
        repository.mark_failed(
            job_id,
            {"tenant_id": tenant_id, "error_type": type(exc).__name__},
        )
        raise


@celery_app.task(name="jobs.agenda.enqueue_topic_analysis")  # type: ignore[untyped-decorator]
def enqueue_agenda_topic_analysis() -> dict[str, int]:
    settings = get_settings()
    repository = JobRepository(settings.jobs_database_url)
    enqueued = skipped = failures = 0
    for tenant_id in repository.list_active_tenant_ids():
        job_id = repository.create_if_idle(
            job_type="nlp",
            reference="agenda_temas_recorrentes",
            parameters={
                "minimum_frequency": settings.agenda_nlp_minimum_frequency
            },
            tenant_id=tenant_id,
        )
        if job_id is None:
            skipped += 1
            continue
        try:
            analyze_agenda_topics.apply_async(
                kwargs={
                    "job_id": job_id,
                    "tenant_id": tenant_id,
                    "minimum_frequency": settings.agenda_nlp_minimum_frequency,
                }
            )
            enqueued += 1
        except Exception:
            repository.mark_failed(job_id, {"fase": "despacho"})
            failures += 1
    return {"enfileirados": enqueued, "ignorados": skipped, "falhas": failures}


@celery_app.task(
    bind=True,
    name="jobs.demandas.generate_deadline_alerts",
    acks_late=True,
    reject_on_worker_lost=True,
)  # type: ignore[untyped-decorator]
def generate_demand_deadline_alerts(
    _: Any, job_id: int, tenant_id: int, lead_days: int
) -> dict[str, Any]:
    settings = get_settings()
    repository = JobRepository(settings.jobs_database_url)
    repository.mark_started(job_id)
    try:
        metrics = DemandDeadlineProcessor(settings.jobs_database_url).generate_alerts(
            tenant_id=tenant_id, lead_days=lead_days
        )
        repository.mark_succeeded(job_id, metrics)
        return {"job_id": job_id, "status": "concluido", **metrics}
    except Exception as exc:
        repository.mark_failed(
            job_id, {"tenant_id": tenant_id, "error_type": type(exc).__name__}
        )
        raise


@celery_app.task(name="jobs.demandas.enqueue_deadline_alerts")  # type: ignore[untyped-decorator]
def enqueue_demand_deadline_alerts() -> dict[str, int]:
    settings = get_settings()
    repository = JobRepository(settings.jobs_database_url)
    enqueued = skipped = failures = 0
    for tenant_id in repository.list_active_tenant_ids():
        job_id = repository.create_if_idle(
            job_type="alerta",
            reference="demandas_prazos",
            parameters={"lead_days": settings.demand_deadlines_lead_days},
            tenant_id=tenant_id,
        )
        if job_id is None:
            skipped += 1
            continue
        try:
            generate_demand_deadline_alerts.apply_async(
                kwargs={
                    "job_id": job_id,
                    "tenant_id": tenant_id,
                    "lead_days": settings.demand_deadlines_lead_days,
                }
            )
            enqueued += 1
        except Exception:
            repository.mark_failed(job_id, {"fase": "despacho"})
            failures += 1
    return {"enfileirados": enqueued, "ignorados": skipped, "falhas": failures}


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
