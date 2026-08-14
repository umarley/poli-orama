import asyncio
from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ResourceNotFoundError
from app.core.pagination import ListParams
from app.tenants.repository import TenantRepository
from app.tenants.schemas import TenantConfiguracaoUpdate, TenantCreate
from app.tenants.service import TenantService


class FakeTenantRepository:
    def __init__(self, tenants: list[SimpleNamespace]) -> None:
        self.tenants = tenants

    async def list(
        self, params: ListParams, status: str | None = None
    ) -> tuple[list[SimpleNamespace], int]:
        items = [tenant for tenant in self.tenants if status is None or tenant.status == status]
        return items, len(items)

    async def get_by_id(self, tenant_id: int) -> SimpleNamespace | None:
        return next((tenant for tenant in self.tenants if tenant.id == tenant_id), None)


def make_tenant() -> SimpleNamespace:
    now = datetime.now(UTC)
    return SimpleNamespace(
        id=1,
        uuid_publico=uuid4(),
        nome="Campanha Exemplo",
        slug="campanha-exemplo",
        documento=None,
        tem_mandato=False,
        plano_assinatura_id=None,
        data_inicio_contrato=date.today(),
        data_fim_contrato=None,
        status="ativo",
        criado_em=now,
        atualizado_em=now,
    )


def test_service_returns_paginated_tenants() -> None:
    service = TenantService(FakeTenantRepository([make_tenant()]))

    result = asyncio.run(service.list(ListParams()))

    assert result.total == 1
    assert result.items[0].slug == "campanha-exemplo"


def test_service_raises_not_found() -> None:
    service = TenantService(FakeTenantRepository([]))

    with pytest.raises(ResourceNotFoundError):
        asyncio.run(service.get_by_id(999))


@pytest.mark.asyncio
async def test_new_tenant_defaults_to_leadership_terminology() -> None:
    session = AsyncMock(spec=AsyncSession)
    repository = TenantRepository(session)

    tenant = await repository.create(
        TenantCreate(nome="Campanha Nova", slug="campanha-nova")
    )

    assert tenant.configuracao.preferencias == {
        "nomenclatura_liderancas": "liderancas"
    }


def test_configuration_update_keeps_full_name_required() -> None:
    payload = TenantConfiguracaoUpdate(
        preferencias={
            "nomenclatura_liderancas": "liderancas",
            "formulario_cadastro": {
                "nome_completo": False,
                "data_nascimento": True,
                "documento": {"CPF": True, "RG": False, "CNH": False},
            },
        }
    )

    assert payload.preferencias is not None
    assert payload.preferencias["formulario_cadastro"]["nome_completo"] is True
    assert payload.preferencias["formulario_cadastro"]["data_nascimento"] is True
    assert payload.preferencias["nomenclatura_liderancas"] == "liderancas"
