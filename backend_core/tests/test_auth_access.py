import asyncio

import pytest

from app.auth.access import RequestActor, require_permission
from app.core.errors import AuthorizationError


def make_actor(*permissions: str) -> RequestActor:
    return RequestActor(
        tenant_id=1,
        user_id=2,
        session_id=3,
        profiles=("gestor",),
        permissions=frozenset(permissions),
        token="token",
    )


def test_permission_dependency_accepts_effective_permission() -> None:
    dependency = require_permission("usuarios", "editar")

    actor = asyncio.run(dependency(make_actor("usuarios.editar")))

    assert actor.user_id == 2


def test_permission_dependency_rejects_missing_permission() -> None:
    dependency = require_permission("usuarios", "editar")

    with pytest.raises(AuthorizationError):
        asyncio.run(dependency(make_actor("usuarios.visualizar")))
