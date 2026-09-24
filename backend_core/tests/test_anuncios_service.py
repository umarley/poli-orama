from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.auth.access import RequestActor
from app.core.errors import AuthorizationError, BusinessRuleError, ResourceNotFoundError
from app.core.pagination import ListParams
from app.mod_anuncios.repository import AnunciosRepository
from app.mod_anuncios.router import _validate_idempotency_header, router
from app.mod_anuncios.schemas import (
    InstallationInput,
    InstallationMaterial,
    PlanningCreate,
    PointMaterialInput,
    RouteCreate,
    RoutePointInput,
    WithdrawalInput,
    WithdrawalMaterial,
)
from app.mod_anuncios.service import AnunciosService


def driver(*, tenant_id: int = 7) -> RequestActor:
    return RequestActor(
        tenant_id=tenant_id,
        user_id=11,
        session_id=3,
        pessoa_id=21,
        profiles=("lider", "motorista_motociclista"),
        permissions=frozenset(
            {
                "anuncios.execucao.registrar",
            }
        ),
        token="test",
        login_origin="app_lider",
    )


class FakeAudit:
    def __init__(self) -> None:
        self.entries: list[dict[str, object]] = []

    async def record(self, **entry: object) -> None:
        self.entries.append(entry)


class FakeFiles:
    def __init__(self) -> None:
        self.repository = SimpleNamespace(list_types=self.list_types)
        self.uploads: list[dict[str, object]] = []

    async def list_types(self, tenant_id: int):
        return [{"id": 9, "codigo": "foto", "ativo": True, "tenant_id": tenant_id}]

    async def upload(self, actor: RequestActor, **kwargs: object) -> None:
        self.uploads.append({"actor": actor, **kwargs})


class FakeRepository:
    def __init__(
        self,
        *,
        accessible: bool = True,
        access_via: str = "direct",
        installed: int = 0,
    ) -> None:
        self.session = SimpleNamespace()
        self.accessible = accessible
        self.access_via = access_via
        self.route_uuid = uuid4()
        self.planning_uuid = uuid4()
        self.point_uuid = uuid4()
        self.material = {
            "id": 31,
            "material_id": 41,
            "material_nome": "Wind Banner",
            "quantidade_planejada": 5,
            "quantidade_instalada": installed,
            "quantidade_recolhida": 0,
            "quantidade_extraviada": 0,
            "quantidade_pendente": 5 - installed,
        }
        self.point = {
            "id": 13,
            "uuid_publico": self.point_uuid,
            "tenant_id": 7,
            "rota_id": 17,
            "rota_uuid": self.route_uuid,
            "planejamento_id": 19,
            "planejamento_uuid": self.planning_uuid,
            "status": "PENDENTE" if installed == 0 else "INSTALADO",
            "materiais": [self.material],
        }
        self.planning = {
            "id": 19,
            "uuid_publico": self.planning_uuid,
            "status": "LIBERADA" if installed == 0 else "EM_EXECUCAO",
        }
        self.route = self.planning
        self.executions: dict[str, dict[str, object]] = {}
        self.movements: list[dict[str, object]] = []
        self.commits = 0

    async def get_execution_by_key(self, tenant_id: int, user_id: int, key: str):
        assert tenant_id == 7 and user_id == 11
        return self.executions.get(key)

    async def get_point(self, tenant_id: int, point_uuid: UUID, *, lock: bool = False):
        if tenant_id != 7 or point_uuid != self.point_uuid:
            return None
        return {**self.point, "materiais": [dict(self.material)]}

    async def get_planning(self, tenant_id: int, planning_uuid: UUID):
        return (
            dict(self.planning) if tenant_id == 7 and planning_uuid == self.planning_uuid else None
        )

    async def planning_is_accessible(
        self, tenant_id: int, planning_id: int, user_id: int, person_id: int | None
    ) -> bool:
        if not self.accessible or (tenant_id, planning_id) != (7, 19):
            return False
        return (self.access_via == "direct" and user_id == 11) or (
            self.access_via == "team" and person_id == 21
        )

    async def reference_exists(self, table: str, tenant_id: int, item_id: int) -> bool:
        return (table, tenant_id, item_id) in {
            ("lideranca", 7, 51),
            ("territorio", 7, 61),
        }

    async def create_execution(self, **values: object) -> int:
        execution_id = len(self.executions) + 1
        self.executions[str(values["idempotency_key"])] = {
            "id": execution_id,
            "uuid_publico": uuid4(),
            "tipo_operacao": values["operation_type"],
            "usuario_id": values["user_id"],
            "ponto_id": values["point_id"],
            "rota_id": values["route_id"],
            "latitude": values["latitude"],
            "longitude": values["longitude"],
            "precisao": values["accuracy"],
            "observacao": values["note"],
            "executado_em": values["captured_at"],
        }
        return execution_id

    async def add_movement(self, **values: object) -> None:
        self.movements.append(
            {
                "_execution_id": values["execution_id"],
                "id": len(self.movements) + 1,
                "uuid_publico": uuid4(),
                "material_id": values["material_id"],
                "material_nome": "Wind Banner",
                "tipo_movimentacao": values["movement_type"],
                "quantidade": values["quantity"],
                "usuario_id": values["user_id"],
                "usuario_nome": "Joao",
                "latitude": values["latitude"],
                "longitude": values["longitude"],
                "observacao": values["note"],
                "registrado_em": values["registered_at"],
            }
        )

    async def update_material_totals(
        self, tenant_id: int, point_material_id: int, *, installed=0, collected=0, lost=0
    ) -> None:
        assert tenant_id == 7 and point_material_id == 31
        self.material["quantidade_instalada"] += installed
        self.material["quantidade_recolhida"] += collected
        self.material["quantidade_extraviada"] += lost
        self.material["quantidade_pendente"] = (
            self.material["quantidade_planejada"] - self.material["quantidade_instalada"]
        )

    async def point_materials(self, tenant_id: int, point_id: int, *, lock=False):
        return [dict(self.material)]

    async def update_operation_statuses(
        self, tenant_id: int, route_id: int, point_id: int, point_status: str
    ) -> str:
        self.point["status"] = point_status
        self.planning["status"] = (
            "CONCLUIDA" if point_status in {"RECOLHIDO", "COM_EXTRAVIO"} else "EM_EXECUCAO"
        )
        return str(self.planning["status"])

    async def point_history(self, tenant_id: int, point_id: int):
        result = []
        for execution in self.executions.values():
            public_execution = {
                key: value for key, value in execution.items() if key not in {"ponto_id", "rota_id"}
            }
            result.append(
                {
                    **public_execution,
                    "usuario_nome": "Joao",
                    "foto": None,
                    "movimentacoes": [
                        {key: value for key, value in movement.items() if key != "_execution_id"}
                        for movement in self.movements
                        if movement["_execution_id"] == execution["id"]
                    ],
                }
            )
        return result

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1


def service(repository: FakeRepository):
    files = FakeFiles()
    instance = AnunciosService(repository, files)  # type: ignore[arg-type]
    audit = FakeAudit()
    instance.audit = audit  # type: ignore[assignment]
    return instance, files, audit


def installation(quantity: int = 5) -> InstallationInput:
    return InstallationInput(
        chave_idempotencia="install-key-0001",
        latitude=Decimal("-16.6800000"),
        longitude=Decimal("-49.2500000"),
        precisao=Decimal("4.20"),
        capturado_em=datetime(2026, 9, 21, 12, tzinfo=UTC),
        materiais=[InstallationMaterial(material_id=41, quantidade=quantity)],
    )


def withdrawal(collected: int, lost: int, note: str | None = None) -> WithdrawalInput:
    return WithdrawalInput(
        chave_idempotencia=f"withdraw-{collected}-{lost}",
        latitude=Decimal("-16.6810000"),
        longitude=Decimal("-49.2510000"),
        precisao=Decimal("6.10"),
        capturado_em=datetime(2026, 9, 21, 18, tzinfo=UTC),
        observacao=note,
        materiais=[
            WithdrawalMaterial(
                material_id=41,
                quantidade_recolhida=collected,
                quantidade_extraviada=lost,
            )
        ],
    )


def test_route_template_does_not_accept_operational_fields() -> None:
    with pytest.raises(ValidationError):
        RouteCreate.model_validate(
            {
                "nome": "Centro",
                "data_execucao": "2026-09-22",
                "equipe_id": 10,
                "pontos": [
                    {
                        "ordem": 1,
                        "descricao_local": "Praca",
                        "materiais": [{"material_id": 41, "quantidade_planejada": 2}],
                    }
                ],
            }
        )


def test_planning_requires_team_or_individual_assignment() -> None:
    with pytest.raises(ValidationError, match="equipe ou usuario"):
        PlanningCreate(rota_id=17, data_execucao="2026-09-22")  # type: ignore[arg-type]


def test_same_route_template_can_feed_multiple_plannings() -> None:
    route = RouteCreate(
        nome="Centro",
        pontos=[
            RoutePointInput(
                ordem=1,
                descricao_local="Praca",
                materiais=[PointMaterialInput(material_id=41, quantidade_planejada=2)],
            )
        ],
    )
    first = PlanningCreate(rota_id=17, equipe_id=5, data_execucao="2026-09-22")  # type: ignore[arg-type]
    second = PlanningCreate(rota_id=17, usuario_responsavel_id=11, data_execucao="2026-09-23")  # type: ignore[arg-type]
    assert route.nome == "Centro"
    assert first.rota_id == second.rota_id == 17
    assert first.data_execucao != second.data_execucao


class ScalarRows:
    def __init__(self, values: list[int]) -> None:
        self.values = values

    def scalars(self) -> "ScalarRows":
        return self

    def all(self) -> list[int]:
        return self.values


@pytest.mark.asyncio
async def test_planning_sync_ignores_routes_without_unstarted_plannings() -> None:
    session = SimpleNamespace(execute=AsyncMock(return_value=ScalarRows([])))
    repository = AnunciosRepository(session)  # type: ignore[arg-type]

    await repository.synchronize_unstarted_plannings(7, 17, 11, sync_points=True)

    session.execute.assert_awaited_once()
    selection = str(session.execute.await_args.args[0])
    assert "pl.status IN ('PLANEJADA','LIBERADA')" in selection
    assert "NOT EXISTS" in selection
    assert "rota_comunicacao_execucao" in selection


@pytest.mark.asyncio
async def test_planning_sync_updates_snapshot_points_and_materials() -> None:
    session = SimpleNamespace(
        execute=AsyncMock(
            side_effect=[
                ScalarRows([19]),
                None,
                ScalarRows([19]),
                None,
                None,
                None,
                None,
                None,
                None,
            ]
        )
    )
    repository = AnunciosRepository(session)  # type: ignore[arg-type]

    await repository.synchronize_unstarted_plannings(7, 17, 11, sync_points=True)

    statements = [str(call.args[0]) for call in session.execute.await_args_list]
    assert len(statements) == 9
    assert "FOR UPDATE OF pp" in statements[1]
    assert "FOR UPDATE OF pl" in statements[2]
    assert "rota_nome=r.nome" in statements[3]
    assert "DELETE FROM anuncio.rota_comunicacao_planejamento_ponto pp" in statements[4]
    assert "endereco=rp.endereco" in statements[5]
    assert "INSERT INTO anuncio.rota_comunicacao_planejamento_ponto" in statements[6]
    assert "DELETE FROM anuncio.rota_comunicacao_planejamento_ponto_material" in statements[7]
    assert "INSERT INTO anuncio.rota_comunicacao_planejamento_ponto_material" in statements[8]
    for call in session.execute.await_args_list[1:]:
        assert call.args[1]["planning_ids"] == [19]


@pytest.mark.asyncio
async def test_planning_sync_revalidates_execution_after_locking_points() -> None:
    session = SimpleNamespace(
        execute=AsyncMock(side_effect=[ScalarRows([19]), None, ScalarRows([])])
    )
    repository = AnunciosRepository(session)  # type: ignore[arg-type]

    await repository.synchronize_unstarted_plannings(7, 17, 11, sync_points=True)

    assert session.execute.await_count == 3
    revalidation = str(session.execute.await_args_list[2].args[0])
    assert "NOT EXISTS" in revalidation
    assert "FOR UPDATE OF pl" in revalidation


@pytest.mark.asyncio
async def test_planning_header_sync_does_not_rebuild_points_when_points_were_not_edited() -> None:
    session = SimpleNamespace(
        execute=AsyncMock(side_effect=[ScalarRows([19]), None, ScalarRows([19]), None])
    )
    repository = AnunciosRepository(session)  # type: ignore[arg-type]

    await repository.synchronize_unstarted_plannings(7, 17, 11, sync_points=False)

    assert session.execute.await_count == 4
    statement = str(session.execute.await_args_list[3].args[0])
    assert "rota_nome=r.nome" in statement


@pytest.mark.asyncio
async def test_driver_cannot_access_route_from_another_team() -> None:
    repository = FakeRepository(accessible=False)
    instance, _, _ = service(repository)
    with pytest.raises(ResourceNotFoundError):
        await instance._ensure_planning_access(driver(), repository.planning)


@pytest.mark.asyncio
@pytest.mark.parametrize("access_via", ["direct", "team"])
async def test_driver_accesses_route_by_direct_assignment_or_team(access_via: str) -> None:
    repository = FakeRepository(access_via=access_via)
    instance, _, _ = service(repository)
    await instance._ensure_planning_access(driver(), repository.planning)


@pytest.mark.asyncio
async def test_team_leadership_must_be_active_and_from_same_tenant() -> None:
    repository = FakeRepository()
    instance, _, _ = service(repository)
    await instance._validate_team(7, [], None, 51, validate_users=False)
    with pytest.raises(ResourceNotFoundError, match="Lideranca"):
        await instance._validate_team(7, [], None, 52, validate_users=False)
    with pytest.raises(ResourceNotFoundError, match="Lideranca"):
        await instance._validate_team(8, [], None, 51, validate_users=False)


@pytest.mark.asyncio
async def test_other_tenant_cannot_obtain_point() -> None:
    repository = FakeRepository()
    assert await repository.get_point(8, repository.point_uuid) is None


@pytest.mark.asyncio
async def test_profile_and_permission_are_required() -> None:
    actor = RequestActor(7, 11, 3, ("lider",), frozenset(), "test", pessoa_id=21)
    repository = FakeRepository()
    instance, _, _ = service(repository)
    with pytest.raises(AuthorizationError):
        await instance.install(
            actor,
            repository.point_uuid,
            installation(),
            photo=("a.jpg", "image/jpeg", b"image"),
        )


@pytest.mark.asyncio
async def test_driver_permission_does_not_grant_administrative_route_listing() -> None:
    repository = FakeRepository()
    instance, _, _ = service(repository)
    with pytest.raises(AuthorizationError):
        await instance.list_routes(driver(), ListParams())


@pytest.mark.asyncio
async def test_installation_records_photo_location_movement_and_audit() -> None:
    repository = FakeRepository()
    instance, files, audit = service(repository)
    response = await instance.install(
        driver(), repository.point_uuid, installation(), photo=("a.jpg", "image/jpeg", b"image")
    )
    assert response.ponto_status == "INSTALADO"
    assert repository.material["quantidade_instalada"] == 5
    assert repository.movements[0]["tipo_movimentacao"] == "INSTALACAO"
    assert repository.movements[0]["latitude"] == Decimal("-16.6800000")
    assert files.uploads[0]["entity_type"] == "anuncio_execucao"
    assert files.uploads[0]["commit"] is False
    assert audit.entries[0]["user_id"] == 11
    assert repository.commits == 1


@pytest.mark.asyncio
async def test_repeated_installation_key_is_idempotent() -> None:
    repository = FakeRepository()
    instance, files, _ = service(repository)
    payload = installation()
    await instance.install(
        driver(), repository.point_uuid, payload, photo=("a.jpg", "image/jpeg", b"image")
    )
    response = await instance.install(
        driver(), repository.point_uuid, payload, photo=("a.jpg", "image/jpeg", b"image")
    )
    assert response.idempotente is True
    assert len(repository.movements) == 1
    assert len(files.uploads) == 1


@pytest.mark.asyncio
async def test_installation_rejects_quantity_above_plan() -> None:
    repository = FakeRepository()
    instance, _, _ = service(repository)
    with pytest.raises(BusinessRuleError, match="saldo planejado"):
        await instance.install(
            driver(),
            repository.point_uuid,
            installation(6),
            photo=("a.jpg", "image/jpeg", b"image"),
        )


@pytest.mark.asyncio
async def test_installation_below_plan_is_completed_and_preserves_difference() -> None:
    repository = FakeRepository()
    instance, _, _ = service(repository)
    response = await instance.install(
        driver(),
        repository.point_uuid,
        installation(2),
        photo=("a.jpg", "image/jpeg", b"image"),
    )
    assert response.ponto_status == "INSTALADO"
    assert repository.material["quantidade_instalada"] == 2
    assert repository.material["quantidade_pendente"] == 3


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("collected", "lost", "expected"),
    [(4, 1, "COM_EXTRAVIO"), (0, 5, "COM_EXTRAVIO"), (5, 0, "RECOLHIDO")],
)
async def test_withdrawal_supports_partial_total_loss_and_full_collection(
    collected: int, lost: int, expected: str
) -> None:
    repository = FakeRepository(installed=5)
    instance, _, audit = service(repository)
    response = await instance.withdraw(
        driver(),
        repository.point_uuid,
        withdrawal(collected, lost, "Material nao localizado" if lost else None),
    )
    assert response.ponto_status == expected
    assert repository.material["quantidade_recolhida"] == collected
    assert repository.material["quantidade_extraviada"] == lost
    assert {item["tipo_movimentacao"] for item in repository.movements} == (
        ({"RECOLHIMENTO"} if collected else set()) | ({"EXTRAVIO"} if lost else set())
    )
    assert audit.entries[0]["after"]["observacao"] == ("Material nao localizado" if lost else None)  # type: ignore[index]
    if lost:
        loss = next(
            item for item in repository.movements if item["tipo_movimentacao"] == "EXTRAVIO"
        )
        assert loss["usuario_id"] == 11
        assert loss["latitude"] == Decimal("-16.6810000")
        assert loss["longitude"] == Decimal("-49.2510000")
        assert loss["registrado_em"] == datetime(2026, 9, 21, 18, tzinfo=UTC)
        assert loss["observacao"] == "Material nao localizado"


@pytest.mark.asyncio
async def test_withdrawal_preserves_installation_in_chronological_history() -> None:
    repository = FakeRepository()
    instance, _, _ = service(repository)
    await instance.install(
        driver(),
        repository.point_uuid,
        installation(),
        photo=("a.jpg", "image/jpeg", b"image"),
    )
    await instance.withdraw(driver(), repository.point_uuid, withdrawal(5, 0))
    history = await repository.point_history(7, 13)
    assert [item["tipo_operacao"] for item in history] == ["INSTALACAO", "RETIRADA"]
    assert history[0]["movimentacoes"][0]["tipo_movimentacao"] == "INSTALACAO"
    assert history[1]["movimentacoes"][0]["tipo_movimentacao"] == "RECOLHIMENTO"


@pytest.mark.asyncio
async def test_partial_withdrawal_with_loss_is_immediately_flagged_as_loss() -> None:
    repository = FakeRepository(installed=5)
    instance, _, _ = service(repository)
    response = await instance.withdraw(
        driver(), repository.point_uuid, withdrawal(2, 1, "Duas unidades ainda no local")
    )
    assert response.ponto_status == "COM_EXTRAVIO"
    assert (
        repository.material["quantidade_instalada"]
        - repository.material["quantidade_recolhida"]
        - repository.material["quantidade_extraviada"]
        == 2
    )


@pytest.mark.asyncio
async def test_withdrawal_rejects_sum_above_installed_balance() -> None:
    repository = FakeRepository(installed=5)
    instance, _, _ = service(repository)
    with pytest.raises(BusinessRuleError, match="ultrapassa"):
        await instance.withdraw(
            driver(), repository.point_uuid, withdrawal(5, 1, "Uma unidade nao localizada")
        )


def test_loss_requires_observation() -> None:
    with pytest.raises(ValidationError, match="observacao"):
        withdrawal(4, 1)


def test_main_administrative_and_app_endpoints_are_registered() -> None:
    registered = {
        (method, route.path) for route in router.routes for method in (route.methods or set())
    }
    assert {
        ("GET", "/anuncios/materiais"),
        ("POST", "/anuncios/equipes"),
        ("POST", "/anuncios/rotas"),
        ("GET", "/anuncios/planejamentos"),
        ("POST", "/anuncios/planejamentos"),
        ("PATCH", "/anuncios/planejamentos/{planning_uuid}"),
        ("GET", "/anuncios/dashboard"),
        ("GET", "/anuncios/app/rotas"),
        ("POST", "/anuncios/app/pontos/{point_uuid}/instalar"),
        ("POST", "/anuncios/app/pontos/{point_uuid}/retirar"),
    } <= registered


def test_idempotency_header_must_match_form_payload() -> None:
    with pytest.raises(BusinessRuleError, match="Idempotency-Key"):
        _validate_idempotency_header("payload-key", "another-key")
