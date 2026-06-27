from typing import Protocol

from sqlalchemy import Select, func, or_, select

from app.core.errors import BusinessRuleError
from app.core.pagination import ListParams, SortDirection
from app.core.repository import BaseRepository
from app.tenants.models import Tenant


class TenantRepositoryProtocol(Protocol):
    async def list(
        self, params: ListParams, status: str | None = None
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
        self, statement: Select[tuple[Tenant]], params: ListParams, status: str | None
    ) -> Select[tuple[Tenant]]:
        statement = statement.where(Tenant.excluido_em.is_(None))
        if status:
            statement = statement.where(Tenant.status == status)
        if params.query:
            term = f"%{params.query}%"
            statement = statement.where(or_(Tenant.nome.ilike(term), Tenant.slug.ilike(term)))
        return statement

    async def list(self, params: ListParams, status: str | None = None) -> tuple[list[Tenant], int]:
        order_column = self.sortable_columns.get(params.order_by)
        if order_column is None:
            raise BusinessRuleError(
                "Campo de ordenacao nao permitido.",
                code="invalid_order_field",
                details={"allowed": sorted(self.sortable_columns)},
            )

        filtered = self._filters(select(Tenant), params, status)
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
