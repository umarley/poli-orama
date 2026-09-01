"""Regras de negocio, calculos e auditoria dos contratos."""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from fastapi.encoders import jsonable_encoder

from app.audit.service import AuditService
from app.auth.access import RequestActor
from app.core.errors import AuthorizationError, BusinessRuleError, ResourceNotFoundError
from app.mod_contrato.repository import ContractRepository
from app.mod_contrato.schemas import (
    ContractCreate,
    ContractResponse,
    ContractTotals,
    ContractUpdate,
    PersonOption,
)


class ContractService:
    def __init__(self, repository: ContractRepository) -> None:
        self.repository = repository

    @staticmethod
    def require_treasurer(actor: RequestActor) -> None:
        if "tesoureiro" not in actor.profiles:
            raise AuthorizationError("Perfil obrigatorio: tesoureiro.")

    @staticmethod
    def calculate(amount: Decimal, installments: int, start: date, end: date) -> ContractTotals:
        if amount <= 0:
            raise BusinessRuleError("O valor do contrato deve ser maior que zero.")
        if installments not in {1, 2, 3}:
            raise BusinessRuleError("A quantidade de parcelas deve ser 1, 2 ou 3.")
        days = (end - start).days
        if days <= 0:
            raise BusinessRuleError("A data final deve ser posterior a data inicial.")
        total = (amount * installments).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        daily = (total / days).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return ContractTotals(valor_total=total, dias_trabalho=days, valor_diaria=daily)

    async def people(self, actor: RequestActor, query: str) -> list[PersonOption]:
        self.require_treasurer(actor)
        return [
            PersonOption.model_validate(item)
            for item in await self.repository.search_people(actor.tenant_id, query)
        ]

    async def list(
        self,
        actor: RequestActor,
        *,
        query: str | None,
        contractor_type: str | None,
        status: str | None,
    ) -> list[ContractResponse]:
        self.require_treasurer(actor)
        return [
            ContractResponse.model_validate(item)
            for item in await self.repository.list_contracts(
                actor.tenant_id,
                query=query,
                contractor_type=contractor_type,
                status=status,
            )
        ]

    async def get(self, actor: RequestActor, contract_id: int) -> ContractResponse:
        self.require_treasurer(actor)
        item = await self.repository.contract(actor.tenant_id, contract_id)
        if item is None:
            raise ResourceNotFoundError("Contrato", contract_id)
        return ContractResponse.model_validate(item)

    async def create(self, actor: RequestActor, payload: ContractCreate) -> ContractResponse:
        self.require_treasurer(actor)
        self.calculate(
            payload.valor_parcela,
            payload.quantidade_parcelas,
            payload.data_inicio,
            payload.data_termino,
        )
        campaign_id = payload.campanha_eleicao_id
        if campaign_id is None:
            campaign_id = await self.repository.active_campaign_id(actor.tenant_id)
        if campaign_id is None or not await self.repository.campaign_exists(
            actor.tenant_id, campaign_id
        ):
            raise BusinessRuleError("Nenhuma campanha eleitoral valida foi selecionada.")

        legal_entity_id: int | None = None
        if payload.tipo_contratado == "pf":
            assert payload.pessoa_id is not None
            person = await self.repository.person(actor.tenant_id, payload.pessoa_id)
            if person is None:
                raise ResourceNotFoundError("Pessoa", payload.pessoa_id)
            if not person["cpf"]:
                raise BusinessRuleError("A pessoa selecionada deve possuir CPF cadastrado.")
        else:
            assert payload.pessoa_juridica is not None
            legal_entity_id = await self.repository.upsert_legal_entity(
                actor.tenant_id, actor.user_id, payload.pessoa_juridica
            )

        contract_id = await self.repository.create_contract(
            actor.tenant_id, actor.user_id, campaign_id, payload, legal_entity_id
        )
        item = await self.repository.contract(actor.tenant_id, contract_id)
        assert item is not None
        await self._audit(actor, "criar", contract_id, None, item)
        await self.repository.commit()
        return ContractResponse.model_validate(item)

    async def update(
        self, actor: RequestActor, contract_id: int, payload: ContractUpdate
    ) -> ContractResponse:
        self.require_treasurer(actor)
        current = await self.repository.contract(actor.tenant_id, contract_id)
        if current is None:
            raise ResourceNotFoundError("Contrato", contract_id)
        start = payload.data_inicio or current["data_inicio"]
        end = payload.data_termino or current["data_termino"]
        amount = payload.valor_parcela or current["valor_parcela"]
        installments = payload.quantidade_parcelas or current["quantidade_parcelas"]
        self.calculate(amount, installments, start, end)
        if payload.pessoa_juridica is not None:
            if current["tipo_contratado"] != "pj" or current["pessoa_juridica_id"] is None:
                raise BusinessRuleError("Dados de empresa so podem ser alterados em contrato PJ.")
            await self.repository.update_legal_entity(
                actor.tenant_id,
                current["pessoa_juridica_id"],
                payload.pessoa_juridica.model_dump(exclude_unset=True),
            )
        await self.repository.update_contract(actor.tenant_id, contract_id, payload)
        updated = await self.repository.contract(actor.tenant_id, contract_id)
        assert updated is not None
        await self._audit(actor, "editar", contract_id, current, updated)
        await self.repository.commit()
        return ContractResponse.model_validate(updated)

    async def delete(self, actor: RequestActor, contract_id: int) -> None:
        self.require_treasurer(actor)
        current = await self.repository.contract(actor.tenant_id, contract_id)
        if current is None:
            raise ResourceNotFoundError("Contrato", contract_id)
        if not await self.repository.delete_contract(actor.tenant_id, contract_id):
            raise ResourceNotFoundError("Contrato", contract_id)
        await self._audit(actor, "excluir", contract_id, current, None)
        await self.repository.commit()

    async def _audit(
        self,
        actor: RequestActor,
        action: str,
        record_id: int,
        before: dict[str, Any] | None,
        after: dict[str, Any] | None,
    ) -> None:
        await AuditService(self.repository.session).record(
            action=action,
            tenant_id=actor.tenant_id,
            user_id=actor.user_id,
            schema_name="contrato",
            table_name="contrato",
            record_id=record_id,
            before=jsonable_encoder(before) if before else None,
            after=jsonable_encoder(after) if after else None,
        )
