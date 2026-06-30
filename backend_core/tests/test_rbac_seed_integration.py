import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="TEST_DATABASE_URL nao configurada para validar os seeds RBAC.",
)

EXPECTED_PROFILE_PERMISSIONS = {
    "coordenador_territorial": {
        "usuarios.visualizar",
        "cadastro.visualizar",
        "cadastro.criar",
        "cadastro.editar",
        "cadastro.exportar",
        "territorio.visualizar",
        "territorio.criar",
        "territorio.editar",
        "metas.visualizar",
        "metas.criar",
        "metas.editar",
        "metas.aprovar",
        "agenda.visualizar",
        "agenda.criar",
        "agenda.editar",
        "demandas.visualizar",
        "demandas.criar",
        "demandas.editar",
        "dashboard.visualizar",
    },
    "lider": {
        "cadastro.visualizar",
        "cadastro.criar",
        "cadastro.editar",
        "territorio.visualizar",
        "metas.visualizar",
        "metas.editar",
        "agenda.visualizar",
        "agenda.criar",
        "agenda.editar",
        "demandas.visualizar",
        "demandas.criar",
        "demandas.editar",
        "dashboard.visualizar",
    },
    "telefonista": {
        "cadastro.visualizar",
        "cadastro.criar",
        "cadastro.editar",
        "agenda.visualizar",
        "demandas.visualizar",
        "demandas.criar",
        "demandas.editar",
    },
}


@pytest.mark.asyncio
async def test_real_rbac_seed_matches_profile_matrix() -> None:
    assert TEST_DATABASE_URL is not None
    engine = create_async_engine(TEST_DATABASE_URL)
    try:
        async with engine.connect() as connection:
            all_permissions = set(
                (
                    await connection.scalars(
                        text("SELECT codigo FROM auth.permissao ORDER BY codigo")
                    )
                ).all()
            )
            rows = (
                await connection.execute(
                    text(
                        "SELECT pa.codigo AS perfil, p.codigo AS permissao "
                        "FROM auth.perfil_acesso pa "
                        "JOIN auth.perfil_permissao pp "
                        "ON pp.perfil_acesso_id = pa.id "
                        "JOIN auth.permissao p ON p.id = pp.permissao_id "
                        "WHERE pa.tenant_id IS NULL "
                        "AND pa.codigo IN "
                        "('gestor', 'coordenador_territorial', 'lider', 'telefonista')"
                    )
                )
            ).all()
    finally:
        await engine.dispose()

    actual = {
        profile: {permission for row_profile, permission in rows if row_profile == profile}
        for profile in ("gestor", *EXPECTED_PROFILE_PERMISSIONS)
    }

    assert actual["gestor"] == all_permissions
    for profile, expected_permissions in EXPECTED_PROFILE_PERMISSIONS.items():
        assert actual[profile] == expected_permissions
