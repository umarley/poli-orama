import argparse
from typing import Any

from celery.result import AsyncResult

from jobs.config import get_settings
from jobs.repository import JobRecord, JobRepository
from jobs.tasks import test_job


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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Operacoes do worker Celery.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    enqueue = subparsers.add_parser("enqueue-test", help="Enfileira um job de teste.")
    enqueue.add_argument("--simulate-error", action="store_true")
    enqueue.add_argument("--wait", action="store_true")
    enqueue.add_argument("--timeout", type=float, default=30.0)

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
    return 2


def entrypoint() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    entrypoint()
