import asyncio

import pytest

from app.auth.access import RequestActor, TerritorialAccess, require_permission
from app.core.errors import AuthorizationError

PROFILE_PERMISSIONS = {
    "gestor": {
        "usuarios.administrar",
        "cadastro.excluir",
        "dashboard.exportar",
    },
    "coordenador_territorial": {
        "usuarios.visualizar",
        "cadastro.editar",
        "metas.aprovar",
    },
    "lider": {
        "cadastro.editar",
        "metas.editar",
        "agenda.criar",
    },
    "telefonista": {
        "cadastro.criar",
        "demandas.editar",
        "agenda.visualizar",
    },
}


@pytest.mark.parametrize(
    ("profile", "allowed"),
    [
        ("gestor", True),
        ("coordenador_territorial", False),
        ("lider", False),
        ("telefonista", False),
    ],
)
def test_only_gestor_can_administer_users(profile: str, allowed: bool) -> None:
    actor = RequestActor(
        tenant_id=1,
        user_id=2,
        session_id=3,
        profiles=(profile,),
        permissions=frozenset(PROFILE_PERMISSIONS[profile]),
        token="token",
    )
    dependency = require_permission("usuarios", "administrar")

    if allowed:
        assert asyncio.run(dependency(actor)) == actor
    else:
        with pytest.raises(AuthorizationError):
            asyncio.run(dependency(actor))


def test_territorial_access_restricts_coordinator_to_assigned_scope() -> None:
    access = TerritorialAccess(
        unrestricted=False,
        scopes=frozenset({("municipio", 10, False), ("territorio", 22, True)}),
    )

    assert access.can_access("municipio", 10)
    assert not access.can_access("municipio", 11)
    assert not access.can_access("municipio", 10, administer=True)
    assert access.can_access("territorio", 22, administer=True)


def test_gestor_territorial_access_is_unrestricted() -> None:
    access = TerritorialAccess(unrestricted=True, scopes=frozenset())

    assert access.can_access("municipio", 999, administer=True)
