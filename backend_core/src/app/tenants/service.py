import hashlib
import json
import logging
from typing import Any
from uuid import UUID

from app.core.config import Settings
from app.core.errors import AppError, BusinessRuleError, ResourceNotFoundError
from app.core.pagination import ListParams, Page
from app.tenants.models import Tenant
from app.tenants.repository import CommercialRepository, TenantRepository, TenantRepositoryProtocol
from app.tenants.schemas import (
    CheckoutCreate,
    CheckoutResponse,
    ContratacaoCreate,
    ContratacaoResponse,
    LeadCreate,
    LeadResponse,
    PlanoResponse,
    PlanUsageResponse,
    TenantConfiguracaoResponse,
    TenantConfiguracaoUpdate,
    TenantCreate,
    TenantResponse,
    TenantUpdate,
)

logger = logging.getLogger(__name__)


class TenantService:
    def __init__(self, repository: TenantRepositoryProtocol) -> None:
        self.repository = repository

    async def list(
        self, params: ListParams, status: str | None = None, plano_id: int | None = None
    ) -> Page[TenantResponse]:
        if plano_id is None:
            tenants, total = await self.repository.list(params, status)
        else:
            tenants, total = await self.repository.list(params, status, plano_id)
        items = [TenantResponse.model_validate(tenant) for tenant in tenants]
        return Page[TenantResponse].create(items, total, params)

    async def get_by_id(self, tenant_id: int) -> TenantResponse:
        tenant = await self.repository.get_by_id(tenant_id)
        if tenant is None:
            raise ResourceNotFoundError("Tenant", tenant_id)
        return TenantResponse.model_validate(tenant)


class TenantManagementService(TenantService):
    repository: TenantRepository

    async def create(self, payload: TenantCreate, actor_id: int) -> TenantResponse:
        if await self.repository.get_by_slug(payload.slug):
            raise BusinessRuleError(
                "O slug informado ja esta em uso.", code="tenant_slug_already_exists"
            )
        tenant = await self.repository.create(payload)
        await self.repository.audit(
            tenant_id=tenant.id,
            user_id=actor_id,
            action="criar",
            record_id=tenant.id,
            before=None,
            after=_tenant_snapshot(tenant),
        )
        await self.repository.commit()
        return TenantResponse.model_validate(tenant)

    async def update(self, tenant_id: int, payload: TenantUpdate, actor_id: int) -> TenantResponse:
        tenant = await self.repository.get_by_id(tenant_id)
        if tenant is None:
            raise ResourceNotFoundError("Tenant", tenant_id)
        if payload.slug and payload.slug != tenant.slug:
            existing = await self.repository.get_by_slug(payload.slug)
            if existing is not None:
                raise BusinessRuleError(
                    "O slug informado ja esta em uso.", code="tenant_slug_already_exists"
                )
        before = _tenant_snapshot(tenant)
        await self.repository.update(tenant, payload)
        await self.repository.audit(
            tenant_id=tenant.id,
            user_id=actor_id,
            action="editar",
            record_id=tenant.id,
            before=before,
            after=_tenant_snapshot(tenant),
        )
        await self.repository.commit()
        return TenantResponse.model_validate(tenant)

    async def activate(self, tenant_id: int, actor_id: int) -> TenantResponse:
        tenant = await self.repository.get_by_id(tenant_id)
        if tenant is None:
            raise ResourceNotFoundError("Tenant", tenant_id)
        if tenant.status not in {"pendente", "trial", "suspenso"}:
            raise BusinessRuleError(
                "O tenant nao esta em um status que permita ativacao.",
                code="tenant_cannot_be_activated",
                details={"status": tenant.status},
            )
        return await self.update(tenant_id, TenantUpdate(status="ativo"), actor_id)

    async def get_configuration(self, tenant_id: int) -> TenantConfiguracaoResponse:
        tenant = await self.repository.get_by_id(tenant_id)
        if tenant is None:
            raise ResourceNotFoundError("Tenant", tenant_id)
        if tenant.configuracao is None:
            raise ResourceNotFoundError("Configuracao do tenant", tenant_id)
        return TenantConfiguracaoResponse.model_validate(tenant.configuracao)

    async def update_configuration(
        self, tenant_id: int, payload: TenantConfiguracaoUpdate
    ) -> TenantConfiguracaoResponse:
        tenant = await self.repository.get_by_id(tenant_id)
        if tenant is None or tenant.configuracao is None:
            raise ResourceNotFoundError("Configuracao do tenant", tenant_id)
        configuration = await self.repository.update_configuration(tenant.configuracao, payload)
        await self.repository.commit()
        return TenantConfiguracaoResponse.model_validate(configuration)


class CommercialService:
    def __init__(self, repository: CommercialRepository, settings: Settings) -> None:
        self.repository = repository
        self.settings = settings

    async def list_plans(self) -> list[PlanoResponse]:
        return [
            PlanoResponse.model_validate(plan) for plan in await self.repository.list_active_plans()
        ]

    async def create_lead(self, payload: LeadCreate) -> LeadResponse:
        lead = await self.repository.create_lead(payload)
        logger.info("Novo lead comercial registrado id=%s", lead.uuid_publico)
        return LeadResponse(id=lead.uuid_publico)

    async def create_contratacao(
        self, payload: ContratacaoCreate, idempotency_key: str | None
    ) -> ContratacaoResponse:
        key = _idempotency_key(payload.model_dump(mode="json"), idempotency_key)
        existing = await self.repository.find_contratacao_by_key(key)
        if existing is not None:
            return ContratacaoResponse(id=existing.uuid_publico, status=existing.status)
        plan = await self.repository.get_plan_by_slug(payload.plano_slug)
        if plan is None:
            raise ResourceNotFoundError("Plano", payload.plano_slug)
        contratacao = await self.repository.create_contratacao(payload, plan, key)
        logger.info("Nova contratacao pendente id=%s", contratacao.uuid_publico)
        return ContratacaoResponse(id=contratacao.uuid_publico, status=contratacao.status)

    async def create_checkout(
        self, payload: CheckoutCreate, idempotency_key: str | None
    ) -> CheckoutResponse:
        key = _idempotency_key(payload.model_dump(mode="json"), idempotency_key)
        existing = await self.repository.find_checkout_by_key(key)
        if existing is not None:
            return CheckoutResponse(
                session_id=existing.uuid_publico,
                status=existing.status,
                checkout_url=existing.url_checkout,
            )
        contratacao = await self.repository.get_contratacao(payload.contratacao_id)
        if contratacao is None:
            raise ResourceNotFoundError("Contratacao", payload.contratacao_id)
        if contratacao.status != "pendente":
            raise BusinessRuleError("A contratacao nao esta pendente.", code="contract_not_pending")
        if self.settings.checkout_provider == "none":
            raise AppError(
                status_code=503,
                code="checkout_not_configured",
                message="Checkout ainda nao esta configurado. A equipe comercial foi notificada.",
            )
        checkout_url = (
            f"{self.settings.checkout_sandbox_url.rstrip('/')}/{contratacao.uuid_publico}"
        )
        checkout = await self.repository.create_checkout(
            contratacao,
            key=key,
            provider=self.settings.checkout_provider,
            checkout_url=checkout_url,
        )
        return CheckoutResponse(
            session_id=checkout.uuid_publico,
            status=checkout.status,
            checkout_url=checkout.url_checkout,
        )

    async def process_webhook(
        self,
        event_id: str,
        event_type: str,
        contratacao_id: UUID | None,
        tenant_id: int | None,
    ) -> None:
        if not await self.repository.claim_webhook_event(event_id, event_type):
            return
        if event_type == "subscription.overdue":
            if tenant_id is None:
                raise BusinessRuleError("tenant_id obrigatorio para inadimplencia.")
            await self.repository.mark_tenant_overdue(tenant_id)
            return
        if contratacao_id is None:
            raise BusinessRuleError("contratacao_id obrigatorio para evento de pagamento.")
        contratacao = await self.repository.get_contratacao(contratacao_id)
        if contratacao is None:
            raise ResourceNotFoundError("Contratacao", contratacao_id)
        if event_type == "payment.approved":
            await self.repository.process_payment_approved(contratacao)
        else:
            await self.repository.mark_payment_failed(contratacao)

    async def usage(self, tenant: Tenant) -> PlanUsageResponse:
        users, people, storage = await self.repository.get_usage(tenant.id)
        return PlanUsageResponse(
            plano=PlanoResponse.model_validate(tenant.plano) if tenant.plano else None,
            usuarios=users,
            pessoas=people,
            armazenamento_mb=storage,
        )


def _idempotency_key(payload: dict[str, Any], supplied: str | None) -> str:
    if supplied:
        return hashlib.sha256(supplied.encode()).hexdigest()
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _tenant_snapshot(tenant: Tenant) -> dict[str, Any]:
    return {
        "id": tenant.id,
        "nome": tenant.nome,
        "slug": tenant.slug,
        "status": tenant.status,
        "plano_assinatura_id": tenant.plano_assinatura_id,
    }
