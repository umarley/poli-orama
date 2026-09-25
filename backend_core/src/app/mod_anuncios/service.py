"""Regras de negocio, seguranca e auditoria do modulo Anuncios."""

from datetime import date
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi.encoders import jsonable_encoder

from app.audit.service import AuditService
from app.auth.access import RequestActor
from app.core.errors import AuthorizationError, BusinessRuleError, ResourceNotFoundError
from app.core.pagination import ListParams, Page
from app.mod_anuncios.repository import AnunciosRepository
from app.mod_anuncios.schemas import (
    DashboardResponse,
    InstallationInput,
    MaterialCreate,
    MaterialResponse,
    MaterialUpdate,
    OperationResponse,
    PlanningCreate,
    PlanningDetail,
    PlanningResponse,
    PlanningUpdate,
    RouteCreate,
    RouteDetail,
    RouteResponse,
    RouteUpdate,
    TeamInput,
    TeamResponse,
    TeamUpdate,
    WithdrawalInput,
)
from app.mod_arquivos.schemas import AttachmentResponse
from app.mod_arquivos.service import FileService

ADMIN_VIEW = "anuncios.visualizar"
ADMIN_MANAGE = "anuncios.gerenciar"
MATERIAL_MANAGE = "anuncios.material.gerenciar"
TEAM_MANAGE = "anuncios.equipe.gerenciar"
ROUTE_MANAGE = "anuncios.rota.gerenciar"
EXECUTION_VIEW = "anuncios.execucao.visualizar"
EXECUTION_REGISTER = "anuncios.execucao.registrar"
EVIDENCE_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "mp4", "mov", "m4v", "webm"}


class AnunciosService:
    def __init__(
        self,
        repository: AnunciosRepository,
        file_service: FileService | None = None,
    ) -> None:
        self.repository = repository
        self.file_service = file_service
        self.audit = AuditService(repository.session)

    async def list_materials(
        self,
        actor: RequestActor,
        params: ListParams,
        *,
        include_inactive: bool = False,
        active_only_for_planning: bool = False,
    ) -> Page[MaterialResponse]:
        self._require_any(actor, ADMIN_VIEW, ADMIN_MANAGE, MATERIAL_MANAGE, ROUTE_MANAGE)
        items, total = await self.repository.list_materials(
            actor.tenant_id,
            params,
            include_inactive and not active_only_for_planning,
        )
        return Page[MaterialResponse].create(
            [MaterialResponse.model_validate(item) for item in items], total, params
        )

    async def create_material(
        self, actor: RequestActor, payload: MaterialCreate
    ) -> MaterialResponse:
        self._require_any(actor, ADMIN_MANAGE, MATERIAL_MANAGE)
        item = await self.repository.create_material(actor.tenant_id, actor.user_id, payload)
        await self._audit(actor, "criar", "material_comunicacao", item["id"], None, item)
        await self.repository.commit()
        return MaterialResponse.model_validate(item)

    async def update_material(
        self, actor: RequestActor, material_id: int, payload: MaterialUpdate
    ) -> MaterialResponse:
        self._require_any(actor, ADMIN_MANAGE, MATERIAL_MANAGE)
        before = await self.repository.get_material(actor.tenant_id, material_id)
        if before is None:
            raise ResourceNotFoundError("Material", material_id)
        item = await self.repository.update_material(actor.tenant_id, material_id, payload)
        assert item is not None
        await self._audit(actor, "editar", "material_comunicacao", material_id, before, item)
        await self.repository.commit()
        return MaterialResponse.model_validate(item)

    async def deactivate_material(self, actor: RequestActor, material_id: int) -> None:
        await self.update_material(actor, material_id, MaterialUpdate(ativo=False))

    async def list_teams(
        self, actor: RequestActor, params: ListParams, *, include_inactive: bool = False
    ) -> Page[TeamResponse]:
        self._require_any(actor, ADMIN_VIEW, ADMIN_MANAGE, TEAM_MANAGE, ROUTE_MANAGE)
        items, total = await self.repository.list_teams(actor.tenant_id, params, include_inactive)
        return Page[TeamResponse].create(
            [TeamResponse.model_validate(item) for item in items], total, params
        )

    async def create_team(self, actor: RequestActor, payload: TeamInput) -> TeamResponse:
        self._require_any(actor, ADMIN_MANAGE, TEAM_MANAGE)
        await self._validate_team(
            actor.tenant_id,
            payload.usuario_ids,
            payload.territorio_id,
            payload.lideranca_id,
        )
        item = await self.repository.create_team(actor.tenant_id, payload)
        await self._audit(actor, "criar", "equipe", item["id"], None, item, schema="cadastro")
        await self.repository.commit()
        return TeamResponse.model_validate(item)

    async def update_team(
        self, actor: RequestActor, team_id: int, payload: TeamUpdate
    ) -> TeamResponse:
        self._require_any(actor, ADMIN_MANAGE, TEAM_MANAGE)
        before = await self.repository.get_team(actor.tenant_id, team_id)
        if before is None:
            raise ResourceNotFoundError("Equipe", team_id)
        if (
            payload.usuario_ids is not None
            or "territorio_id" in payload.model_fields_set
            or "lideranca_id" in payload.model_fields_set
        ):
            await self._validate_team(
                actor.tenant_id,
                payload.usuario_ids if payload.usuario_ids is not None else [],
                payload.territorio_id,
                payload.lideranca_id,
                validate_users=payload.usuario_ids is not None,
                validate_territory="territorio_id" in payload.model_fields_set,
                validate_leadership="lideranca_id" in payload.model_fields_set,
            )
        item = await self.repository.update_team(actor.tenant_id, team_id, payload)
        assert item is not None
        await self._audit(actor, "editar", "equipe", team_id, before, item, schema="cadastro")
        await self.repository.commit()
        return TeamResponse.model_validate(item)

    async def _validate_team(
        self,
        tenant_id: int,
        user_ids: list[int],
        territory_id: int | None,
        leadership_id: int | None,
        *,
        validate_users: bool = True,
        validate_territory: bool = True,
        validate_leadership: bool = True,
    ) -> None:
        if validate_users:
            users = await self.repository.users_for_team_assignment(tenant_id, user_ids)
            if len(users) != len(user_ids):
                raise BusinessRuleError(
                    "A equipe contem usuario inexistente, inativo ou de outro tenant.",
                    code="invalid_team_member",
                )
            if any(user["pessoa_id"] is None for user in users):
                raise BusinessRuleError(
                    "Todos os membros da equipe devem possuir uma pessoa vinculada.",
                    code="team_member_without_person",
                )
            person_ids = [user["pessoa_id"] for user in users]
            if len(person_ids) != len(set(person_ids)):
                raise BusinessRuleError(
                    "Dois usuarios da equipe estao vinculados a mesma pessoa.",
                    code="duplicate_team_person",
                )
        territory_exists = territory_id is not None and await self.repository.reference_exists(
            "territorio", tenant_id, territory_id
        )
        if validate_territory and territory_id is not None and not territory_exists:
            raise ResourceNotFoundError("Territorio", territory_id)
        if (
            validate_leadership
            and leadership_id is not None
            and not await self.repository.reference_exists("lideranca", tenant_id, leadership_id)
        ):
            raise ResourceNotFoundError("Lideranca", leadership_id)

    async def list_routes(
        self,
        actor: RequestActor,
        params: ListParams,
        **filters: Any,
    ) -> Page[RouteResponse]:
        self._require_any(actor, ADMIN_VIEW, ADMIN_MANAGE, ROUTE_MANAGE, EXECUTION_VIEW)
        items, total = await self.repository.list_routes(actor.tenant_id, params, **filters)
        return Page[RouteResponse].create(
            [RouteResponse.model_validate(item) for item in items], total, params
        )

    async def create_route(self, actor: RequestActor, payload: RouteCreate) -> RouteDetail:
        self._require_any(actor, ADMIN_MANAGE, ROUTE_MANAGE)
        await self._validate_route_references(actor.tenant_id, payload)
        item = await self.repository.create_route(actor.tenant_id, actor.user_id, payload)
        await self._audit(actor, "criar", "rota_comunicacao", item["id"], None, item)
        await self.repository.commit()
        return RouteDetail.model_validate(item)

    async def get_admin_route(self, actor: RequestActor, route_uuid: UUID) -> RouteDetail:
        self._require_any(actor, ADMIN_VIEW, ADMIN_MANAGE, ROUTE_MANAGE, EXECUTION_VIEW)
        item = await self.repository.get_route_detail(actor.tenant_id, route_uuid)
        if item is None:
            raise ResourceNotFoundError("Rota", route_uuid)
        return RouteDetail.model_validate(item)

    async def update_route(
        self, actor: RequestActor, route_uuid: UUID, payload: RouteUpdate
    ) -> RouteDetail:
        self._require_any(actor, ADMIN_MANAGE, ROUTE_MANAGE)
        before = await self.repository.get_route_detail(actor.tenant_id, route_uuid)
        if before is None:
            raise ResourceNotFoundError("Rota", route_uuid)
        merged = {
            "nome": payload.nome if payload.nome is not None else before["nome"],
            "descricao": (
                payload.descricao
                if "descricao" in payload.model_fields_set
                else before["descricao"]
            ),
            "territorio_id": (
                payload.territorio_id
                if "territorio_id" in payload.model_fields_set
                else before["territorio_id"]
            ),
            "pontos": (
                payload.pontos
                if payload.pontos is not None
                else [
                    {
                        "ordem": point["ordem"],
                        "descricao_local": point["descricao_local"],
                        "endereco": point["endereco"],
                        "latitude_planejada": point["latitude_planejada"],
                        "longitude_planejada": point["longitude_planejada"],
                        "observacao": point["observacao"],
                        "materiais": [
                            {
                                "material_id": material["material_id"],
                                "quantidade_planejada": material["quantidade_planejada"],
                            }
                            for material in point["materiais"]
                        ],
                    }
                    for point in before["pontos"]
                ]
            ),
            "ativo": payload.ativo if payload.ativo is not None else before["ativo"],
        }
        await self._validate_route_references(actor.tenant_id, RouteCreate.model_validate(merged))
        await self.repository.update_route(actor.tenant_id, before["id"], actor.user_id, payload)
        item = await self.repository.get_route_detail(actor.tenant_id, route_uuid)
        assert item is not None
        await self._audit(actor, "editar", "rota_comunicacao", item["id"], before, item)
        await self.repository.commit()
        return RouteDetail.model_validate(item)

    async def _validate_route_references(self, tenant_id: int, payload: RouteCreate) -> None:
        references = (("territorio", payload.territorio_id, "Territorio"),)
        for table, item_id, label in references:
            if item_id is not None and not await self.repository.reference_exists(
                table, tenant_id, item_id
            ):
                raise ResourceNotFoundError(label, item_id)
        material_ids = {m.material_id for point in payload.pontos for m in point.materiais}
        for material_id in material_ids:
            if not await self.repository.reference_exists("material", tenant_id, material_id):
                raise BusinessRuleError(
                    "A rota contem material inexistente, inativo ou de outro tenant.",
                    code="invalid_route_material",
                    details={"material_id": material_id},
                )

    @staticmethod
    def _validate_status_transition(current: str, target: str) -> None:
        allowed = {
            "PLANEJADA": {"PLANEJADA", "LIBERADA", "CANCELADA"},
            "LIBERADA": {"LIBERADA", "CANCELADA"},
            "EM_EXECUCAO": {"EM_EXECUCAO", "CANCELADA"},
            "CONCLUIDA": {"CONCLUIDA"},
            "CANCELADA": {"CANCELADA"},
        }
        if target not in allowed[current]:
            raise BusinessRuleError(
                f"Transicao de status invalida: {current} para {target}.",
                code="invalid_route_status_transition",
            )

    async def list_plannings(
        self, actor: RequestActor, params: ListParams, **filters: Any
    ) -> Page[PlanningResponse]:
        self._require_any(actor, ADMIN_VIEW, ADMIN_MANAGE, ROUTE_MANAGE, EXECUTION_VIEW)
        items, total = await self.repository.list_plannings(actor.tenant_id, params, **filters)
        return Page[PlanningResponse].create(
            [PlanningResponse.model_validate(item) for item in items], total, params
        )

    async def create_planning(self, actor: RequestActor, payload: PlanningCreate) -> PlanningDetail:
        self._require_any(actor, ADMIN_MANAGE, ROUTE_MANAGE)
        await self._validate_planning_references(actor.tenant_id, payload)
        item = await self.repository.create_planning(actor.tenant_id, actor.user_id, payload)
        await self._audit(actor, "criar", "rota_comunicacao_planejamento", item["id"], None, item)
        await self.repository.commit()
        return PlanningDetail.model_validate(item)

    async def get_admin_planning(self, actor: RequestActor, planning_uuid: UUID) -> PlanningDetail:
        self._require_any(actor, ADMIN_VIEW, ADMIN_MANAGE, ROUTE_MANAGE, EXECUTION_VIEW)
        item = await self.repository.get_planning_detail(actor.tenant_id, planning_uuid)
        if item is None:
            raise ResourceNotFoundError("Planejamento", planning_uuid)
        return PlanningDetail.model_validate(item)

    async def update_planning(
        self, actor: RequestActor, planning_uuid: UUID, payload: PlanningUpdate
    ) -> PlanningDetail:
        self._require_any(actor, ADMIN_MANAGE, ROUTE_MANAGE)
        before = await self.repository.get_planning_detail(actor.tenant_id, planning_uuid)
        if before is None:
            raise ResourceNotFoundError("Planejamento", planning_uuid)
        if await self.repository.planning_has_executions(actor.tenant_id, before["id"]):
            changed = set(payload.model_fields_set) - {"status"}
            if changed:
                raise BusinessRuleError(
                    "A atribuicao e a data nao podem mudar depois do inicio da execucao.",
                    code="planning_already_executed",
                )
        merged = PlanningCreate(
            rota_id=before["rota_id"],
            equipe_id=(
                payload.equipe_id
                if "equipe_id" in payload.model_fields_set
                else before["equipe_id"]
            ),
            usuario_responsavel_id=(
                payload.usuario_responsavel_id
                if "usuario_responsavel_id" in payload.model_fields_set
                else before["usuario_responsavel_id"]
            ),
            data_execucao=payload.data_execucao or before["data_execucao"],
            observacao=(
                payload.observacao
                if "observacao" in payload.model_fields_set
                else before["observacao"]
            ),
        )
        await self._validate_planning_references(
            actor.tenant_id, merged, require_active_route=False
        )
        if payload.status is not None:
            self._validate_status_transition(before["status"], payload.status)
        await self.repository.update_planning(actor.tenant_id, before["id"], actor.user_id, payload)
        item = await self.repository.get_planning_detail(actor.tenant_id, planning_uuid)
        assert item is not None
        await self._audit(
            actor, "editar", "rota_comunicacao_planejamento", item["id"], before, item
        )
        await self.repository.commit()
        return PlanningDetail.model_validate(item)

    async def _validate_planning_references(
        self, tenant_id: int, payload: PlanningCreate, *, require_active_route: bool = True
    ) -> None:
        for table, item_id, label in (
            ("equipe", payload.equipe_id, "Equipe"),
            ("usuario", payload.usuario_responsavel_id, "Usuario"),
        ):
            if item_id is not None and not await self.repository.reference_exists(
                table, tenant_id, item_id
            ):
                raise ResourceNotFoundError(label, item_id)
        route = await self.repository.get_route_by_id(tenant_id, payload.rota_id)
        if route is None or (require_active_route and not route["ativo"]):
            raise ResourceNotFoundError("Rota", payload.rota_id)

    async def app_routes(
        self, actor: RequestActor, params: ListParams, *, selected_date: date | None = None
    ) -> Page[PlanningResponse]:
        self._require_driver(actor)
        items, total = await self.repository.list_plannings(
            actor.tenant_id,
            params,
            start=selected_date,
            end=selected_date,
            accessible_user_id=actor.user_id,
            accessible_person_id=actor.pessoa_id,
        )
        return Page[PlanningResponse].create(
            [PlanningResponse.model_validate(item) for item in items], total, params
        )

    async def app_route(self, actor: RequestActor, route_uuid: UUID) -> PlanningDetail:
        self._require_driver(actor)
        planning = await self.repository.get_planning_detail(actor.tenant_id, route_uuid)
        await self._ensure_planning_access(actor, planning)
        assert planning is not None
        return PlanningDetail.model_validate(planning)

    async def install(
        self,
        actor: RequestActor,
        point_uuid: UUID,
        payload: InstallationInput,
        *,
        photo: tuple[str, str | None, bytes] | None = None,
    ) -> OperationResponse:
        self._require_driver(actor)
        existing = await self.repository.get_execution_by_key(
            actor.tenant_id, actor.user_id, payload.chave_idempotencia
        )
        if existing is not None:
            return await self._idempotent_response(
                actor, point_uuid, existing, expected_type="INSTALACAO"
            )
        point = await self.repository.get_point(actor.tenant_id, point_uuid, lock=True)
        if point is None:
            raise ResourceNotFoundError("Ponto", point_uuid)
        existing = await self.repository.get_execution_by_key(
            actor.tenant_id, actor.user_id, payload.chave_idempotencia
        )
        if existing is not None:
            return await self._idempotent_response(
                actor, point_uuid, existing, expected_type="INSTALACAO"
            )
        planning = await self.repository.get_planning(actor.tenant_id, point["planejamento_uuid"])
        await self._ensure_planning_access(actor, planning)
        assert planning is not None
        if planning["status"] not in {"LIBERADA", "EM_EXECUCAO"}:
            raise BusinessRuleError(
                "A rota nao esta liberada para execucao.", code="route_not_released"
            )
        if point["status"] not in {"PENDENTE", "EM_EXECUCAO"}:
            raise BusinessRuleError(
                "Este ponto nao aceita novas instalacoes.", code="point_installation_closed"
            )
        planned = {item["material_id"]: item for item in point["materiais"]}
        for item in payload.materiais:
            if item.material_id not in planned:
                raise BusinessRuleError(
                    "Somente materiais planejados para o ponto podem ser instalados.",
                    code="material_not_planned",
                    details={"material_id": item.material_id},
                )
            if item.quantidade > planned[item.material_id]["quantidade_pendente"]:
                raise BusinessRuleError(
                    "A quantidade instalada ultrapassa o saldo planejado do material.",
                    code="planned_quantity_exceeded",
                    details={
                        "material_id": item.material_id,
                        "quantidade_planejada": planned[item.material_id]["quantidade_planejada"],
                        "quantidade_instalada": planned[item.material_id]["quantidade_instalada"],
                        "quantidade_pendente": planned[item.material_id]["quantidade_pendente"],
                    },
                )
        execution_id = await self.repository.create_execution(
            tenant_id=actor.tenant_id,
            route_id=point["rota_id"],
            planning_id=point["planejamento_id"],
            point_id=point["id"],
            user_id=actor.user_id,
            operation_type="INSTALACAO",
            idempotency_key=payload.chave_idempotencia,
            latitude=payload.latitude,
            longitude=payload.longitude,
            accuracy=payload.precisao,
            note=payload.observacao,
            captured_at=payload.capturado_em,
        )
        for item in payload.materiais:
            await self.repository.add_movement(
                tenant_id=actor.tenant_id,
                execution_id=execution_id,
                route_id=point["rota_id"],
                planning_id=point["planejamento_id"],
                point_id=point["id"],
                material_id=item.material_id,
                user_id=actor.user_id,
                movement_type="INSTALACAO",
                quantity=item.quantidade,
                latitude=payload.latitude,
                longitude=payload.longitude,
                note=payload.observacao,
                registered_at=payload.capturado_em,
            )
            await self.repository.update_material_totals(
                actor.tenant_id,
                planned[item.material_id]["id"],
                installed=item.quantidade,
            )
        # O envio confirma a instalacao com a quantidade efetivamente realizada.
        # A diferenca para o planejado permanece nos totais para acompanhamento.
        point_status = "INSTALADO"
        route_status = await self.repository.update_operation_statuses(
            actor.tenant_id, point["planejamento_id"], point["id"], point_status
        )
        await self.repository.flush()
        await self._audit(
            actor,
            "criar",
            "rota_comunicacao_execucao",
            execution_id,
            None,
            payload.model_dump(mode="json"),
        )
        if photo is not None:
            await self._upload_photo(actor, execution_id, photo, "Foto da instalacao")
        await self.repository.commit()
        return await self._operation_response(
            actor.tenant_id, point["id"], execution_id, point_status, route_status
        )

    async def withdraw(
        self,
        actor: RequestActor,
        point_uuid: UUID,
        payload: WithdrawalInput,
        *,
        photo: tuple[str, str | None, bytes] | None = None,
    ) -> OperationResponse:
        self._require_driver(actor)
        existing = await self.repository.get_execution_by_key(
            actor.tenant_id, actor.user_id, payload.chave_idempotencia
        )
        if existing is not None:
            return await self._idempotent_response(
                actor, point_uuid, existing, expected_type="RETIRADA"
            )
        point = await self.repository.get_point(actor.tenant_id, point_uuid, lock=True)
        if point is None:
            raise ResourceNotFoundError("Ponto", point_uuid)
        existing = await self.repository.get_execution_by_key(
            actor.tenant_id, actor.user_id, payload.chave_idempotencia
        )
        if existing is not None:
            return await self._idempotent_response(
                actor, point_uuid, existing, expected_type="RETIRADA"
            )
        planning = await self.repository.get_planning(actor.tenant_id, point["planejamento_uuid"])
        await self._ensure_planning_access(actor, planning)
        assert planning is not None
        if planning["status"] != "EM_EXECUCAO":
            raise BusinessRuleError(
                "O planejamento nao esta em execucao para retirada.",
                code="planning_not_in_progress",
            )
        if point["status"] not in {"INSTALADO", "RECOLHIDO_PARCIALMENTE", "COM_EXTRAVIO"}:
            raise BusinessRuleError(
                "O ponto ainda nao possui material instalado para retirada.",
                code="point_not_installed",
            )
        balances = {item["material_id"]: item for item in point["materiais"]}
        for item in payload.materiais:
            balance = balances.get(item.material_id)
            if balance is None:
                raise BusinessRuleError(
                    "O material nao pertence a este ponto.",
                    code="material_not_planned",
                    details={"material_id": item.material_id},
                )
            requested = item.quantidade_recolhida + item.quantidade_extraviada
            outstanding = (
                balance["quantidade_instalada"]
                - balance["quantidade_recolhida"]
                - balance["quantidade_extraviada"]
            )
            if requested > outstanding:
                raise BusinessRuleError(
                    "A soma recolhida e extraviada ultrapassa a quantidade instalada pendente.",
                    code="material_balance_exceeded",
                    details={
                        "material_id": item.material_id,
                        "quantidade_instalada": balance["quantidade_instalada"],
                        "quantidade_recolhida": balance["quantidade_recolhida"],
                        "quantidade_extraviada": balance["quantidade_extraviada"],
                        "quantidade_pendente": outstanding,
                    },
                )
        execution_id = await self.repository.create_execution(
            tenant_id=actor.tenant_id,
            route_id=point["rota_id"],
            planning_id=point["planejamento_id"],
            point_id=point["id"],
            user_id=actor.user_id,
            operation_type="RETIRADA",
            idempotency_key=payload.chave_idempotencia,
            latitude=payload.latitude,
            longitude=payload.longitude,
            accuracy=payload.precisao,
            note=payload.observacao,
            captured_at=payload.capturado_em,
        )
        for item in payload.materiais:
            if item.quantidade_recolhida:
                await self.repository.add_movement(
                    tenant_id=actor.tenant_id,
                    execution_id=execution_id,
                    route_id=point["rota_id"],
                    planning_id=point["planejamento_id"],
                    point_id=point["id"],
                    material_id=item.material_id,
                    user_id=actor.user_id,
                    movement_type="RECOLHIMENTO",
                    quantity=item.quantidade_recolhida,
                    latitude=payload.latitude,
                    longitude=payload.longitude,
                    note=payload.observacao,
                    registered_at=payload.capturado_em,
                )
            if item.quantidade_extraviada:
                await self.repository.add_movement(
                    tenant_id=actor.tenant_id,
                    execution_id=execution_id,
                    route_id=point["rota_id"],
                    planning_id=point["planejamento_id"],
                    point_id=point["id"],
                    material_id=item.material_id,
                    user_id=actor.user_id,
                    movement_type="EXTRAVIO",
                    quantity=item.quantidade_extraviada,
                    latitude=payload.latitude,
                    longitude=payload.longitude,
                    note=payload.observacao,
                    registered_at=payload.capturado_em,
                )
            await self.repository.update_material_totals(
                actor.tenant_id,
                balances[item.material_id]["id"],
                collected=item.quantidade_recolhida,
                lost=item.quantidade_extraviada,
            )
        refreshed = await self.repository.point_materials(actor.tenant_id, point["id"], lock=True)
        any_loss = any(item["quantidade_extraviada"] > 0 for item in refreshed)
        pending = sum(
            item["quantidade_instalada"]
            - item["quantidade_recolhida"]
            - item["quantidade_extraviada"]
            for item in refreshed
        )
        if any_loss:
            point_status = "COM_EXTRAVIO"
        elif pending == 0:
            point_status = "RECOLHIDO"
        else:
            point_status = "RECOLHIDO_PARCIALMENTE"
        route_status = await self.repository.update_operation_statuses(
            actor.tenant_id, point["planejamento_id"], point["id"], point_status
        )
        await self.repository.flush()
        await self._audit(
            actor,
            "criar",
            "rota_comunicacao_execucao",
            execution_id,
            None,
            payload.model_dump(mode="json"),
        )
        if photo is not None:
            await self._upload_photo(actor, execution_id, photo, "Foto da retirada")
        await self.repository.commit()
        return await self._operation_response(
            actor.tenant_id, point["id"], execution_id, point_status, route_status
        )

    async def _upload_photo(
        self,
        actor: RequestActor,
        execution_id: int,
        photo: tuple[str, str | None, bytes],
        description: str,
    ) -> None:
        if self.file_service is None:
            raise RuntimeError("Servico de arquivos nao configurado.")
        types = await self.file_service.repository.list_types(actor.tenant_id)
        photo_type = next((item for item in types if item["codigo"] == "foto"), None)
        if photo_type is None:
            raise BusinessRuleError("Tipo de anexo 'foto' nao configurado.")
        filename, content_type, content = photo
        await self.file_service.upload(
            actor,
            entity_type="anuncio_execucao",
            entity_id=execution_id,
            type_id=photo_type["id"],
            description=description,
            filename=filename,
            content_type=content_type,
            content=content,
            photo_only=True,
            commit=False,
        )

    async def upload_execution_media(
        self,
        actor: RequestActor,
        execution_uuid: UUID,
        media: tuple[str, str | None, bytes],
    ) -> AttachmentResponse:
        self._require_driver(actor)
        execution = await self.repository.get_execution_by_uuid(actor.tenant_id, execution_uuid)
        if execution is None:
            raise ResourceNotFoundError("Execucao", execution_uuid)
        planning = await self.repository.get_planning_by_id(
            actor.tenant_id, execution["planejamento_id"]
        )
        await self._ensure_planning_access(actor, planning)
        if execution["usuario_id"] != actor.user_id:
            raise AuthorizationError("Somente o autor pode enviar evidencias desta execucao.")
        if self.file_service is None:
            raise RuntimeError("Servico de arquivos nao configurado.")
        filename, content_type, content = media
        extension = Path(filename).suffix.lower().removeprefix(".")
        is_video = bool(content_type and content_type.startswith("video/")) or extension in {
            "mp4",
            "mov",
            "m4v",
            "webm",
        }
        is_image = bool(content_type and content_type.startswith("image/")) or extension in {
            "jpg",
            "jpeg",
            "png",
            "webp",
        }
        if not is_video and not is_image:
            raise BusinessRuleError(
                "A evidencia deve ser uma fotografia ou um video.",
                code="unsupported_evidence_type",
            )
        types = await self.file_service.repository.list_types(actor.tenant_id)
        code = "video" if is_video else "foto"
        attachment_type = next((item for item in types if item["codigo"] == code), None)
        if attachment_type is None:
            raise BusinessRuleError(f"Tipo de anexo '{code}' nao configurado.")
        return await self.file_service.upload(
            actor,
            entity_type="anuncio_execucao",
            entity_id=execution["id"],
            type_id=attachment_type["id"],
            description="Video da operacao" if is_video else "Foto da operacao",
            filename=filename,
            content_type=content_type,
            content=content,
            photo_only=False,
            allowed_extensions=EVIDENCE_EXTENSIONS,
        )

    async def _idempotent_response(
        self,
        actor: RequestActor,
        point_uuid: UUID,
        existing: dict[str, Any],
        *,
        expected_type: str,
    ) -> OperationResponse:
        point = await self.repository.get_point(actor.tenant_id, point_uuid)
        if point is None:
            raise ResourceNotFoundError("Ponto", point_uuid)
        planning = await self.repository.get_planning(actor.tenant_id, point["planejamento_uuid"])
        await self._ensure_planning_access(actor, planning)
        if existing["ponto_id"] != point["id"] or existing["tipo_operacao"] != expected_type:
            raise BusinessRuleError(
                "A chave de idempotencia ja foi utilizada em outra operacao.",
                code="idempotency_key_reused",
            )
        assert planning is not None
        response = await self._operation_response(
            actor.tenant_id,
            point["id"],
            existing["id"],
            point["status"],
            planning["status"],
        )
        return response.model_copy(update={"idempotente": True})

    async def _operation_response(
        self,
        tenant_id: int,
        point_id: int,
        execution_id: int,
        point_status: str,
        route_status: str,
    ) -> OperationResponse:
        history = await self.repository.point_history(tenant_id, point_id)
        execution = next(item for item in history if item["id"] == execution_id)
        return OperationResponse.model_validate(
            {
                "execucao": execution,
                "ponto_status": point_status,
                "rota_status": route_status,
                "idempotente": False,
            }
        )

    async def dashboard(
        self,
        actor: RequestActor,
        *,
        start: date,
        end: date,
        **filters: Any,
    ) -> DashboardResponse:
        self._require_any(actor, ADMIN_VIEW, ADMIN_MANAGE, EXECUTION_VIEW)
        if end < start:
            raise BusinessRuleError("A data final deve ser igual ou posterior a inicial.")
        data = await self.repository.dashboard(actor.tenant_id, start=start, end=end, **filters)
        return DashboardResponse.model_validate(data)

    async def _ensure_planning_access(
        self, actor: RequestActor, planning: dict[str, Any] | None
    ) -> None:
        if planning is None or not await self.repository.planning_is_accessible(
            actor.tenant_id,
            planning["id"] if planning else -1,
            actor.user_id,
            actor.pessoa_id,
        ):
            # 404 evita confirmar a existencia de rotas de outro usuario/equipe/tenant.
            raise ResourceNotFoundError(
                "Planejamento", planning["uuid_publico"] if planning else "indisponivel"
            )

    @staticmethod
    def _require_driver(actor: RequestActor) -> None:
        if "motorista_motociclista" not in actor.profiles:
            raise AuthorizationError("Perfil obrigatorio: motorista_motociclista.")
        permission = EXECUTION_REGISTER
        if permission not in actor.permissions:
            raise AuthorizationError(f"Permissao obrigatoria: {permission}.")

    @staticmethod
    def _require_any(actor: RequestActor, *permissions: str) -> None:
        if not set(permissions) & actor.permissions:
            raise AuthorizationError(f"Permissao obrigatoria: {' ou '.join(sorted(permissions))}.")

    async def _audit(
        self,
        actor: RequestActor,
        action: str,
        table: str,
        record_id: int,
        before: dict[str, Any] | None,
        after: dict[str, Any] | None,
        *,
        schema: str = "anuncio",
    ) -> None:
        await self.audit.record(
            action=action,
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            schema_name=schema,
            table_name=table,
            record_id=record_id,
            before=jsonable_encoder(before) if before else None,
            after=jsonable_encoder(after) if after else None,
        )
