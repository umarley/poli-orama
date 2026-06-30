from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session
from app.core.errors import AuthenticationError, AuthorizationError, TenantInactiveError
from app.tenants.repository import TenantRepository


@dataclass(frozen=True, slots=True)
class RequestActor:
    tenant_id: int
    user_id: int
    role: str


async def require_actor(
    session: Annotated[AsyncSession, Depends(get_session)],
    tenant_id: Annotated[int | None, Header(alias="X-Tenant-ID")] = None,
    user_id: Annotated[int | None, Header(alias="X-User-ID")] = None,
    role: Annotated[str | None, Header(alias="X-User-Role")] = None,
) -> RequestActor:
    if tenant_id is None or user_id is None:
        raise AuthenticationError()
    tenant = await TenantRepository(session).get_by_id(tenant_id)
    if tenant is None:
        raise AuthenticationError("Tenant da sessao nao foi encontrado.")
    if tenant.status not in {"ativo", "trial"}:
        raise TenantInactiveError(tenant.status)
    await session.execute(
        text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
        {"tenant_id": str(tenant_id)},
    )
    return RequestActor(tenant_id=tenant_id, user_id=user_id, role=role or "usuario")


async def require_tenant_admin(
    actor: Annotated[RequestActor, Depends(require_actor)],
) -> RequestActor:
    if actor.role not in {"gestor", "gestor_saas", "admin"}:
        raise AuthorizationError()
    return actor


async def require_saas_admin(
    user_id: Annotated[int | None, Header(alias="X-User-ID")] = None,
    role: Annotated[str | None, Header(alias="X-User-Role")] = None,
) -> int:
    if user_id is None:
        if get_settings().environment in {"local", "test"}:
            return 0
        raise AuthenticationError()
    if role not in {"gestor_saas", "admin"}:
        raise AuthorizationError("Apenas gestores SaaS podem administrar tenants.")
    return user_id
