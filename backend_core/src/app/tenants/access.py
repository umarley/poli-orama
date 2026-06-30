"""Compatibilidade de imports; autenticacao pertence ao modulo app.auth."""

from app.auth.access import (
    RequestActor,
    get_current_user,
    get_db_session,
    require_permission,
    require_saas_admin,
    require_tenant_admin,
)

require_actor = get_current_user

__all__ = [
    "RequestActor",
    "get_current_user",
    "get_db_session",
    "require_actor",
    "require_permission",
    "require_saas_admin",
    "require_tenant_admin",
]
