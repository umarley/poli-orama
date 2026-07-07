from celery import Celery
from celery.schedules import crontab

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

beat_schedule = {}
if settings.completeness_job_enabled:
    beat_schedule["cadastro-completude-diaria"] = {
        "task": "jobs.cadastro.enqueue_completeness",
        "schedule": crontab(
            hour=settings.completeness_job_hour,
            minute=settings.completeness_job_minute,
        ),
    }
if settings.goals_job_enabled:
    beat_schedule["metas-recalculo-periodico"] = {
        "task": "jobs.metas.enqueue_recalculation",
        "schedule": settings.goals_job_interval_minutes * 60,
    }
if settings.agenda_reminders_enabled:
    beat_schedule["agenda-lembretes-periodicos"] = {
        "task": "jobs.agenda.enqueue_reminders",
        "schedule": settings.agenda_reminders_interval_minutes * 60,
    }
if settings.agenda_nlp_enabled:
    beat_schedule["agenda-analise-temas-diaria"] = {
        "task": "jobs.agenda.enqueue_topic_analysis",
        "schedule": crontab(hour=settings.agenda_nlp_hour, minute=0),
    }
if settings.demand_deadlines_enabled:
    beat_schedule["demandas-alertas-prazo-diarios"] = {
        "task": "jobs.demandas.enqueue_deadline_alerts",
        "schedule": crontab(hour=settings.demand_deadlines_hour, minute=0),
    }
if settings.dashboard_materialization_enabled:
    beat_schedule["dashboard-materializacao-diaria"] = {
        "task": "jobs.dashboard.enqueue_materialization",
        "schedule": crontab(hour=settings.dashboard_materialization_hour, minute=0),
    }
if settings.scheduled_reports_enabled:
    beat_schedule["relatorios-agendados-diarios"] = {
        "task": "jobs.dashboard.enqueue_scheduled_reports",
        "schedule": crontab(hour=settings.scheduled_reports_hour, minute=0),
    }
if beat_schedule:
    celery_app.conf.beat_schedule = beat_schedule
