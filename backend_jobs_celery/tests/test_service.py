from datetime import date
from typing import Any

import pytest

from jobs.service import (
    enqueue_scheduled_goals_jobs,
    enqueue_scheduled_completeness_jobs,
    execute_goals_job,
    execute_completeness_job,
    execute_test_job,
)


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


class FakeCompletenessRepository(FakeRepository):
    def __init__(self, *, error: Exception | None = None) -> None:
        super().__init__()
        self.error = error
        self.recalculation: tuple[int, int] | None = None

    def recalculate_person_completeness(self, *, tenant_id: int, batch_size: int) -> dict[str, int]:
        self.recalculation = (tenant_id, batch_size)
        if self.error is not None:
            raise self.error
        return {
            "tenant_id": tenant_id,
            "processadas": 12,
            "atualizadas": 8,
        }


def test_completeness_job_updates_scores_and_records_metrics() -> None:
    repository = FakeCompletenessRepository()

    result = execute_completeness_job(
        repository,
        job_id=20,
        tenant_id=30,
        batch_size=500,
    )

    assert repository.recalculation == (30, 500)
    assert result["processadas"] == 12
    assert repository.events == [
        ("started", 20, None),
        (
            "succeeded",
            20,
            {"tenant_id": 30, "processadas": 12, "atualizadas": 8},
        ),
    ]


def test_completeness_job_records_failure_and_reraises() -> None:
    repository = FakeCompletenessRepository(error=RuntimeError("database unavailable"))

    with pytest.raises(RuntimeError, match="database unavailable"):
        execute_completeness_job(
            repository,
            job_id=21,
            tenant_id=31,
            batch_size=100,
        )

    assert repository.events[-1] == (
        "failed",
        21,
        {"tenant_id": 31, "error_type": "RuntimeError"},
    )


class FakeSchedulerRepository:
    def __init__(self) -> None:
        self.failed: list[int] = []

    def list_active_tenant_ids(self) -> list[int]:
        return [10, 11, 12]

    def create_if_idle(
        self,
        *,
        job_type: str,
        reference: str,
        parameters: dict[str, Any],
        tenant_id: int,
    ) -> int | None:
        assert job_type == "indicador"
        assert reference == "completude_cadastral"
        assert parameters == {"batch_size": 250, "origem": "automatico"}
        return None if tenant_id == 11 else tenant_id + 100

    def mark_failed(self, job_id: int, context: dict[str, Any] | None = None) -> None:
        self.failed.append(job_id)


def test_scheduler_enqueues_active_tenants_without_overlapping_jobs() -> None:
    repository = FakeSchedulerRepository()
    dispatched: list[tuple[int, int, int]] = []

    def dispatch(job_id: int, tenant_id: int, batch_size: int) -> str:
        dispatched.append((job_id, tenant_id, batch_size))
        if tenant_id == 12:
            raise RuntimeError("broker unavailable")
        return "task-id"

    result = enqueue_scheduled_completeness_jobs(
        repository,
        batch_size=250,
        dispatch=dispatch,
    )

    assert dispatched == [(110, 10, 250), (112, 12, 250)]
    assert repository.failed == [112]
    assert result == {
        "tenants_enfileirados": 1,
        "tenants_ignorados": 1,
        "falhas_despacho": 1,
    }


class FakeGoalsRepository(FakeRepository):
    def recalculate_goals_and_rankings(
        self, *, tenant_id: int, reference_date: date
    ) -> dict[str, int]:
        assert reference_date == date(2026, 7, 3)
        return {
            "tenant_id": tenant_id,
            "metas_atualizadas": 4,
            "alertas_abertos": 2,
            "liderancas_ranqueadas": 3,
        }


def test_goals_job_recalculates_progress_alerts_and_ranking() -> None:
    repository = FakeGoalsRepository()

    result = execute_goals_job(
        repository,
        job_id=40,
        tenant_id=50,
        reference_date=date(2026, 7, 3),
    )

    assert result["metas_atualizadas"] == 4
    assert result["liderancas_ranqueadas"] == 3
    assert [event[0] for event in repository.events] == ["started", "succeeded"]


class FakeGoalsScheduler:
    def __init__(self) -> None:
        self.failed: list[int] = []

    def list_active_tenant_ids(self) -> list[int]:
        return [1, 2]

    def create_if_idle(
        self,
        *,
        job_type: str,
        reference: str,
        parameters: dict[str, Any],
        tenant_id: int,
    ) -> int | None:
        assert job_type == "indicador"
        assert reference == "metas_rankings_alertas"
        assert parameters == {"origem": "mudanca_cadastro_periodica"}
        return None if tenant_id == 2 else 100 + tenant_id

    def mark_failed(self, job_id: int, context: dict[str, Any] | None = None) -> None:
        self.failed.append(job_id)


def test_goals_scheduler_avoids_overlapping_jobs() -> None:
    repository = FakeGoalsScheduler()
    dispatched: list[tuple[int, int]] = []

    result = enqueue_scheduled_goals_jobs(
        repository,
        dispatch=lambda job_id, tenant_id: (
            dispatched.append((job_id, tenant_id)) or "task-id"
        ),
    )

    assert dispatched == [(101, 1)]
    assert result == {
        "tenants_enfileirados": 1,
        "tenants_ignorados": 1,
        "falhas_despacho": 0,
    }
