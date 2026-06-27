from app.core.errors import ResourceNotFoundError
from app.core.pagination import ListParams, Page
from app.tenants.repository import TenantRepositoryProtocol
from app.tenants.schemas import TenantResponse


class TenantService:
    def __init__(self, repository: TenantRepositoryProtocol) -> None:
        self.repository = repository

    async def list(self, params: ListParams, status: str | None = None) -> Page[TenantResponse]:
        tenants, total = await self.repository.list(params, status)
        items = [TenantResponse.model_validate(tenant) for tenant in tenants]
        return Page[TenantResponse].create(items, total, params)

    async def get_by_id(self, tenant_id: int) -> TenantResponse:
        tenant = await self.repository.get_by_id(tenant_id)
        if tenant is None:
            raise ResourceNotFoundError("Tenant", tenant_id)
        return TenantResponse.model_validate(tenant)
