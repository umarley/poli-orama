from typing import Any

from jobs.repository import JobRepositoryProtocol


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
