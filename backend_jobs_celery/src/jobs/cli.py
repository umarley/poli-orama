import argparse
from typing import Any

from celery.result import AsyncResult

from jobs.config import get_settings
from jobs.repository import JobRecord, JobRepository
from jobs.tasks import recalculate_completeness, test_job


def _print_job(job: JobRecord) -> None:
    print(
        f"id={job.id} status={job.status} tentativas={job.tentativas} "
        f"iniciado_em={job.iniciado_em} concluido_em={job.concluido_em}"
    )


def enqueue_test(*, simulate_error: bool, wait: bool, timeout: float) -> int:
    settings = get_settings()
    repository = JobRepository(settings.jobs_database_url)
    job_id = repository.create(
        job_type="outro",
        reference="job_teste",
        parameters={"simulate_error": simulate_error},
    )
    result: AsyncResult[Any] = test_job.apply_async(
        kwargs={"job_id": job_id, "simulate_error": simulate_error}
    )
    print(f"job_id={job_id} celery_task_id={result.id}")
    if not wait:
        return 0

    try:
        result.get(timeout=timeout)
    except Exception:
        job = repository.get(job_id)
        if job is not None:
            _print_job(job)
        return 0 if simulate_error and job is not None and job.status == "falha" else 1

    job = repository.get(job_id)
    if job is None:
        print("Job nao encontrado depois da execucao.")
        return 1
    _print_job(job)
    return 0 if job.status == "concluido" else 1


def show_status(job_id: int) -> int:
    repository = JobRepository(get_settings().jobs_database_url)
    job = repository.get(job_id)
    if job is None:
        print(f"Job {job_id} nao encontrado.")
        return 1
    _print_job(job)
    return 0


def enqueue_completeness(
    *,
    tenant_id: int,
    batch_size: int | None,
    wait: bool,
    timeout: float,
) -> int:
    settings = get_settings()
    repository = JobRepository(settings.jobs_database_url)
    if not repository.tenant_is_active(tenant_id):
        print(f"Tenant {tenant_id} inexistente ou inativo.")
        return 1

    effective_batch_size = (
        settings.completeness_job_batch_size if batch_size is None else batch_size
    )
    if effective_batch_size < 1 or effective_batch_size > 10000:
        print("batch-size deve estar entre 1 e 10000.")
        return 1
    job_id = repository.create_if_idle(
        job_type="indicador",
        reference="completude_cadastral",
        parameters={"batch_size": effective_batch_size, "origem": "manual"},
        tenant_id=tenant_id,
    )
    if job_id is None:
        print(f"Ja existe recalculo de completude ativo para o tenant {tenant_id}.")
        return 1

    result: AsyncResult[Any] = recalculate_completeness.apply_async(
        kwargs={
            "job_id": job_id,
            "tenant_id": tenant_id,
            "batch_size": effective_batch_size,
        }
    )
    print(f"job_id={job_id} celery_task_id={result.id}")
    if not wait:
        return 0

    try:
        result.get(timeout=timeout)
    except Exception:
        job = repository.get(job_id)
        if job is not None:
            _print_job(job)
        return 1

    job = repository.get(job_id)
    if job is None:
        print("Job nao encontrado depois da execucao.")
        return 1
    _print_job(job)
    return 0 if job.status == "concluido" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Operacoes do worker Celery.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    enqueue = subparsers.add_parser("enqueue-test", help="Enfileira um job de teste.")
    enqueue.add_argument("--simulate-error", action="store_true")
    enqueue.add_argument("--wait", action="store_true")
    enqueue.add_argument("--timeout", type=float, default=30.0)

    completeness = subparsers.add_parser(
        "enqueue-completeness",
        help="Enfileira o recalculo de completude de um tenant.",
    )
    completeness.add_argument("--tenant-id", type=int, required=True)
    completeness.add_argument("--batch-size", type=int)
    completeness.add_argument("--wait", action="store_true")
    completeness.add_argument("--timeout", type=float, default=300.0)

    status = subparsers.add_parser("status", help="Consulta um job persistido.")
    status.add_argument("job_id", type=int)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "enqueue-test":
        return enqueue_test(
            simulate_error=args.simulate_error,
            wait=args.wait,
            timeout=args.timeout,
        )
    if args.command == "status":
        return show_status(args.job_id)
    if args.command == "enqueue-completeness":
        return enqueue_completeness(
            tenant_id=args.tenant_id,
            batch_size=args.batch_size,
            wait=args.wait,
            timeout=args.timeout,
        )
    return 2


def entrypoint() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    entrypoint()
