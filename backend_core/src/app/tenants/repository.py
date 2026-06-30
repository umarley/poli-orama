from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID, uuid4

from sqlalchemy import Select, func, or_, select, text, update
from sqlalchemy.exc import IntegrityError

from app.core.errors import BusinessRuleError
from app.core.pagination import ListParams, SortDirection
from app.core.repository import BaseRepository
from app.tenants.models import (
    CheckoutSession,
    Contratacao,
    EventoOperacional,
    LeadComercial,
    PlanoAssinatura,
    Tenant,
    TenantConfiguracao,
)
from app.tenants.schemas import (
    ContratacaoCreate,
    LeadCreate,
    TenantConfiguracaoUpdate,
    TenantCreate,
    TenantUpdate,
)


class TenantRepositoryProtocol(Protocol):
    async def list(
        self, params: ListParams, status: str | None = None, plano_id: int | None = None
    ) -> tuple[list[Tenant], int]: ...

    async def get_by_id(self, tenant_id: int) -> Tenant | None: ...


class TenantRepository(BaseRepository[Tenant]):
    sortable_columns = {
        "id": Tenant.id,
        "nome": Tenant.nome,
        "slug": Tenant.slug,
        "status": Tenant.status,
        "criado_em": Tenant.criado_em,
    }

    def _filters(
        self,
        statement: Select[tuple[Tenant]],
        params: ListParams,
        status: str | None,
        plano_id: int | None,
    ) -> Select[tuple[Tenant]]:
        statement = statement.where(Tenant.excluido_em.is_(None))
        if status:
            statement = statement.where(Tenant.status == status)
        if plano_id:
            statement = statement.where(Tenant.plano_assinatura_id == plano_id)
        if params.query:
            term = f"%{params.query}%"
            statement = statement.where(or_(Tenant.nome.ilike(term), Tenant.slug.ilike(term)))
        return statement

    async def list(
        self, params: ListParams, status: str | None = None, plano_id: int | None = None
    ) -> tuple[list[Tenant], int]:
        order_column = self.sortable_columns.get(params.order_by)
        if order_column is None:
            raise BusinessRuleError(
                "Campo de ordenacao nao permitido.",
                code="invalid_order_field",
                details={"allowed": sorted(self.sortable_columns)},
            )

        filtered = self._filters(select(Tenant), params, status, plano_id)
        count_statement = select(func.count()).select_from(filtered.order_by(None).subquery())
        total = int((await self.session.scalar(count_statement)) or 0)

        order_expression = (
            order_column.desc() if params.direction == SortDirection.DESC else order_column.asc()
        )
        result = await self.session.scalars(
            filtered.order_by(order_expression).offset(params.offset).limit(params.page_size)
        )
        return list(result.all()), total

    async def get_by_id(self, tenant_id: int) -> Tenant | None:
        result = await self.session.scalar(
            select(Tenant).where(Tenant.id == tenant_id, Tenant.excluido_em.is_(None))
        )
        return result

    async def get_by_slug(self, slug: str) -> Tenant | None:
        result: Tenant | None = await self.session.scalar(
            select(Tenant).where(Tenant.slug == slug, Tenant.excluido_em.is_(None))
        )
        return result

    async def create(self, payload: TenantCreate) -> Tenant:
        tenant = Tenant(
            uuid_publico=uuid4(),
            **payload.model_dump(),
            criado_em=datetime.now(UTC),
            atualizado_em=datetime.now(UTC),
        )
        tenant.configuracao = TenantConfiguracao(
            nome_publico=payload.nome,
            fuso_horario="America/Sao_Paulo",
            percentual_alerta_meta=Decimal("70"),
            integracoes={},
            preferencias={},
            criado_em=datetime.now(UTC),
            atualizado_em=datetime.now(UTC),
        )
        self.session.add(tenant)
        await self.session.flush()
        return tenant

    async def update(self, tenant: Tenant, payload: TenantUpdate) -> Tenant:
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(tenant, field, value)
        tenant.atualizado_em = datetime.now(UTC)
        await self.session.flush()
        return tenant

    async def update_configuration(
        self, configuration: TenantConfiguracao, payload: TenantConfiguracaoUpdate
    ) -> TenantConfiguracao:
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(configuration, field, value)
        configuration.atualizado_em = datetime.now(UTC)
        await self.session.flush()
        return configuration

    async def audit(
        self,
        *,
        tenant_id: int | None,
        user_id: int | None,
        action: str,
        record_id: int,
        before: dict[str, Any] | None,
        after: dict[str, Any] | None,
    ) -> None:
        await self.session.execute(
            text(
                """
                INSERT INTO auditoria.log_auditoria
                    (tenant_id, usuario_id, acao, schema_nome, tabela, registro_id,
                     dados_anteriores, dados_novos)
                VALUES
                    (:tenant_id,
                     (SELECT id FROM auth.usuario WHERE id = :user_id),
                     :action, 'public', 'tenant', :record_id,
                     CAST(:before AS jsonb), CAST(:after AS jsonb))
                """
            ),
            {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "action": action,
                "record_id": record_id,
                "before": _json_dumps(before),
                "after": _json_dumps(after),
            },
        )

    async def commit(self) -> None:
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            if "slug" in str(exc.orig).lower():
                raise BusinessRuleError(
                    "O slug informado ja esta em uso.", code="tenant_slug_already_exists"
                ) from exc
            raise


class CommercialRepository(BaseRepository[PlanoAssinatura]):
    async def list_active_plans(self) -> list[PlanoAssinatura]:
        result = await self.session.scalars(
            select(PlanoAssinatura)
            .where(PlanoAssinatura.ativo.is_(True))
            .order_by(PlanoAssinatura.ordem_comercial, PlanoAssinatura.id)
        )
        return list(result.unique().all())

    async def get_plan_by_slug(self, slug: str) -> PlanoAssinatura | None:
        result: PlanoAssinatura | None = await self.session.scalar(
            select(PlanoAssinatura).where(
                PlanoAssinatura.slug == slug, PlanoAssinatura.ativo.is_(True)
            )
        )
        return result

    async def create_lead(self, payload: LeadCreate) -> LeadComercial:
        now = datetime.now(UTC)
        lead = LeadComercial(
            uuid_publico=uuid4(),
            **payload.model_dump(exclude={"origem"}),
            consentido_em=now,
            origem=payload.origem.model_dump(exclude_none=True),
            criado_em=now,
        )
        self.session.add(lead)
        await self.session.flush()
        await self.notify("lead.criado", "lead_comercial", lead.id, {"email": lead.email})
        await self.session.commit()
        return lead

    async def find_contratacao_by_key(self, key: str) -> Contratacao | None:
        result: Contratacao | None = await self.session.scalar(
            select(Contratacao).where(Contratacao.chave_idempotencia == key)
        )
        return result

    async def get_contratacao(self, public_id: UUID) -> Contratacao | None:
        result: Contratacao | None = await self.session.scalar(
            select(Contratacao).where(Contratacao.uuid_publico == public_id)
        )
        return result

    async def create_contratacao(
        self, payload: ContratacaoCreate, plan: PlanoAssinatura, key: str
    ) -> Contratacao:
        now = datetime.now(UTC)
        data = payload.model_dump(exclude={"origem", "plano_slug"})
        contratacao = Contratacao(
            uuid_publico=uuid4(),
            plano_assinatura_id=plan.id,
            **data,
            origem=payload.origem.model_dump(exclude_none=True),
            status="pendente",
            chave_idempotencia=key,
            criado_em=now,
            atualizado_em=now,
        )
        self.session.add(contratacao)
        await self.session.flush()
        await self.notify(
            "contratacao.criada",
            "contratacao",
            contratacao.id,
            {"email": contratacao.email, "plano": plan.slug},
        )
        await self.session.commit()
        return contratacao

    async def find_checkout_by_key(self, key: str) -> CheckoutSession | None:
        result: CheckoutSession | None = await self.session.scalar(
            select(CheckoutSession).where(CheckoutSession.chave_idempotencia == key)
        )
        return result

    async def create_checkout(
        self,
        contratacao: Contratacao,
        *,
        key: str,
        provider: str,
        checkout_url: str | None,
    ) -> CheckoutSession:
        now = datetime.now(UTC)
        checkout = CheckoutSession(
            uuid_publico=uuid4(),
            contratacao_id=contratacao.id,
            provedor=provider,
            status="pendente" if checkout_url else "indisponivel",
            url_checkout=checkout_url,
            chave_idempotencia=key,
            criado_em=now,
            atualizado_em=now,
        )
        self.session.add(checkout)
        await self.session.commit()
        return checkout

    async def notify(
        self, event_type: str, entity: str, entity_id: int, payload: dict[str, Any]
    ) -> None:
        self.session.add(
            EventoOperacional(
                tipo=event_type,
                entidade=entity,
                entidade_id=entity_id,
                payload=payload,
                status="pendente",
                criado_em=datetime.now(UTC),
            )
        )

    async def process_payment_approved(self, contratacao: Contratacao) -> Tenant:
        existing_tenant = (
            await self.session.get(Tenant, contratacao.tenant_id)
            if contratacao.tenant_id is not None
            else None
        )
        if existing_tenant is not None:
            existing_tenant.status = "ativo"
            existing_tenant.atualizado_em = datetime.now(UTC)
            await self.session.commit()
            return existing_tenant

        slug = contratacao.slug_solicitado
        if await self.session.scalar(select(Tenant.id).where(Tenant.slug == slug)):
            slug = f"{slug}-{str(contratacao.uuid_publico)[:8]}"
        now = datetime.now(UTC)
        tenant = Tenant(
            uuid_publico=uuid4(),
            nome=contratacao.nome_campanha,
            slug=slug,
            documento=contratacao.documento,
            tem_mandato=False,
            plano_assinatura_id=contratacao.plano_assinatura_id,
            data_inicio_contrato=date.today(),
            status="ativo",
            criado_em=now,
            atualizado_em=now,
        )
        tenant.configuracao = TenantConfiguracao(
            nome_publico=contratacao.nome_campanha,
            fuso_horario="America/Sao_Paulo",
            percentual_alerta_meta=Decimal("70"),
            integracoes={},
            preferencias={},
            criado_em=now,
            atualizado_em=now,
        )
        self.session.add(tenant)
        await self.session.flush()
        contratacao.tenant_id = tenant.id
        contratacao.status = "aprovada"
        contratacao.atualizado_em = now
        await self.notify("tenant.ativado", "tenant", tenant.id, {"contratacao_id": contratacao.id})
        await self.session.commit()
        return tenant

    async def mark_payment_failed(self, contratacao: Contratacao) -> None:
        contratacao.status = "pagamento_falhou"
        contratacao.atualizado_em = datetime.now(UTC)
        await self.session.commit()

    async def mark_tenant_overdue(self, tenant_id: int) -> None:
        await self.session.execute(
            update(Tenant)
            .where(Tenant.id == tenant_id, Tenant.status == "ativo")
            .values(status="inadimplente", atualizado_em=datetime.now(UTC))
        )
        await self.session.commit()

    async def claim_webhook_event(self, event_id: str, event_type: str) -> bool:
        claimed = await self.session.scalar(
            text(
                """
                INSERT INTO public.webhook_pagamento_evento (event_id, tipo)
                VALUES (:event_id, :event_type)
                ON CONFLICT (event_id) DO NOTHING
                RETURNING event_id
                """
            ),
            {"event_id": event_id, "event_type": event_type},
        )
        return claimed is not None

    async def suspend_overdue(self) -> int:
        result = await self.session.execute(
            update(Tenant)
            .where(Tenant.status == "inadimplente", Tenant.excluido_em.is_(None))
            .values(status="suspenso", atualizado_em=datetime.now(UTC))
        )
        await self.session.commit()
        return int(result.rowcount or 0)  # type: ignore[attr-defined]

    async def get_usage(self, tenant_id: int) -> tuple[int, int, Decimal]:
        users = int(
            (
                await self.session.scalar(
                    text(
                        "SELECT count(*) FROM auth.usuario "
                        "WHERE tenant_id = :tenant_id AND excluido_em IS NULL"
                    ),
                    {"tenant_id": tenant_id},
                )
            )
            or 0
        )
        people = int(
            (
                await self.session.scalar(
                    text(
                        "SELECT count(*) FROM cadastro.pessoa "
                        "WHERE tenant_id = :tenant_id AND excluido_em IS NULL"
                    ),
                    {"tenant_id": tenant_id},
                )
            )
            or 0
        )
        storage = Decimal(
            str(
                (
                    await self.session.scalar(
                        text(
                            "SELECT COALESCE(sum(tamanho_bytes), 0) / 1048576.0 "
                            "FROM arquivo.arquivo "
                            "WHERE tenant_id = :tenant_id AND excluido_em IS NULL"
                        ),
                        {"tenant_id": tenant_id},
                    )
                )
                or 0
            )
        )
        return users, people, storage


def _json_dumps(value: dict[str, Any] | None) -> str:
    import json

    return json.dumps(value, default=str)
