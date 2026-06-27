from typing import Any

import pytest

from jobs.service import execute_test_job


class FakeRepository:
    def __init__(self) -> None:
        self.events: list[tuple[str, int, dict[str, Any] | None]] = []

    def create(
        self,
        *,
        job_type: str,
        reference: str,
        parameters: dict[str, Any],
        tenant_id: int | None = None,
    ) -> int:
        return 1

    def mark_started(self, job_id: int) -> None:
        self.events.append(("started", job_id, None))

    def mark_succeeded(self, job_id: int, context: dict[str, Any] | None = None) -> None:
        self.events.append(("succeeded", job_id, context))

    def mark_failed(self, job_id: int, context: dict[str, Any] | None = None) -> None:
        self.events.append(("failed", job_id, context))

    def get(self, job_id: int) -> None:
        return None


def test_success_records_start_and_completion() -> None:
    repository = FakeRepository()

    result = execute_test_job(repository, job_id=10)

    assert result["status"] == "concluido"
    assert [event[0] for event in repository.events] == ["started", "succeeded"]


def test_simulated_error_records_failure_and_reraises() -> None:
    repository = FakeRepository()

    with pytest.raises(RuntimeError, match="Falha simulada"):
        execute_test_job(repository, job_id=11, simulate_error=True)

    assert [event[0] for event in repository.events] == ["started", "failed"]
    assert repository.events[-1][2] == {"error_type": "RuntimeError"}
