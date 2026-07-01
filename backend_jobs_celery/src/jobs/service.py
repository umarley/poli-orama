from collections.abc import Callable
from typing import Any

from jobs.repository import (
    CompletenessRepositoryProtocol,
    CompletenessSchedulerRepositoryProtocol,
    JobRepositoryProtocol,
)


def execute_test_job(
    repository: JobRepositoryProtocol,
    *,
    job_id: int,
    simulate_error: bool = False,
) -> dict[str, Any]:
    repository.mark_started(job_id)
    try:
        if simulate_error:
            raise RuntimeError("Falha simulada solicitada.")
        result = {"job_id": job_id, "status": "concluido", "message": "Job de teste executado."}
        repository.mark_succeeded(job_id, {"resultado": result["message"]})
        return result
    except Exception as exc:
        repository.mark_failed(job_id, {"error_type": type(exc).__name__})
        raise


def execute_completeness_job(
    repository: CompletenessRepositoryProtocol,
    *,
    job_id: int,
    tenant_id: int,
    batch_size: int,
) -> dict[str, Any]:
    repository.mark_started(job_id)
    try:
        metrics = repository.recalculate_person_completeness(
            tenant_id=tenant_id,
            batch_size=batch_size,
        )
        result: dict[str, Any] = {
            "job_id": job_id,
            "status": "concluido",
            **metrics,
        }
        repository.mark_succeeded(job_id, metrics)
        return result
    except Exception as exc:
        repository.mark_failed(
            job_id,
            {
                "tenant_id": tenant_id,
                "error_type": type(exc).__name__,
            },
        )
        raise


def enqueue_scheduled_completeness_jobs(
    repository: CompletenessSchedulerRepositoryProtocol,
    *,
    batch_size: int,
    dispatch: Callable[[int, int, int], str],
) -> dict[str, int]:
    enqueued = 0
    skipped = 0
    failed = 0
    for tenant_id in repository.list_active_tenant_ids():
        job_id = repository.create_if_idle(
            job_type="indicador",
            reference="completude_cadastral",
            parameters={"batch_size": batch_size, "origem": "automatico"},
            tenant_id=tenant_id,
        )
        if job_id is None:
            skipped += 1
            continue
        try:
            dispatch(job_id, tenant_id, batch_size)
            enqueued += 1
        except Exception as exc:
            repository.mark_failed(
                job_id,
                {
                    "tenant_id": tenant_id,
                    "error_type": type(exc).__name__,
                    "fase": "despacho",
                },
            )
            failed += 1
    return {
        "tenants_enfileirados": enqueued,
        "tenants_ignorados": skipped,
        "falhas_despacho": failed,
    }
