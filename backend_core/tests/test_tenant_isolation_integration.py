import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.auth.security import hash_password
from app.main import app

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="TEST_DATABASE_URL nao configurada para teste HTTP entre tenants.",
)


@pytest.mark.asyncio
async def test_tenant_a_cannot_list_read_or_update_user_from_tenant_b() -> None:
    assert TEST_DATABASE_URL is not None
    admin_engine = create_async_engine(TEST_DATABASE_URL)
    suffix = uuid4().hex[:10]
    tenant_ids: list[int] = []
    users: list[tuple[int, str, str]] = []
    password = "Senha-isolamento-123!"
    try:
        async with admin_engine.begin() as connection:
            profile_id = int(
                await connection.scalar(
                    text(
                        "SELECT id FROM auth.perfil_acesso "
                        "WHERE tenant_id IS NULL AND codigo = 'gestor'"
                    )
                )
            )
            for label in ("a", "b"):
                tenant_id = int(
                    await connection.scalar(
                        text(
                            "INSERT INTO public.tenant (nome, slug) "
                            "VALUES (:nome, :slug) RETURNING id"
                        ),
                        {
                            "nome": f"Tenant {label}",
                            "slug": f"isolation-{label}-{suffix}",
                        },
                    )
                )
                tenant_ids.append(tenant_id)
                await connection.execute(
                    text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
                    {"tenant_id": str(tenant_id)},
                )
                email = f"isolation-{label}-{suffix}@example.test"
                user_id = int(
                    await connection.scalar(
                        text(
                            "INSERT INTO auth.usuario "
                            "(tenant_id, nome, email, hash_senha) "
                            "VALUES (:tenant_id, :nome, :email, :password_hash) "
                            "RETURNING id"
                        ),
                        {
                            "tenant_id": tenant_id,
                            "nome": f"Gestor {label}",
                            "email": email,
                            "password_hash": hash_password(password),
                        },
                    )
                )
                users.append((user_id, email, label))
                await connection.execute(
                    text(
                        "INSERT INTO auth.usuario_perfil "
                        "(usuario_id, perfil_acesso_id, tenant_id) "
                        "VALUES (:user_id, :profile_id, :tenant_id)"
                    ),
                    {
                        "user_id": user_id,
                        "profile_id": profile_id,
                        "tenant_id": tenant_id,
                    },
                )

        with TestClient(app) as client:
            login = client.post(
                "/api/v1/auth/login",
                json={
                    "tenant_slug": f"isolation-a-{suffix}",
                    "email": users[0][1],
                    "senha": password,
                },
            )
            assert login.status_code == 200, login.text
            headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

            listing = client.get("/api/v1/users", headers=headers)
            assert listing.status_code == 200, listing.text
            assert {item["tenant_id"] for item in listing.json()["items"]} == {tenant_ids[0]}
            assert client.get(f"/api/v1/users/{users[1][0]}", headers=headers).status_code == 404
            assert (
                client.patch(
                    f"/api/v1/users/{users[1][0]}",
                    headers=headers,
                    json={"nome": "Tentativa indevida"},
                ).status_code
                == 404
            )
    finally:
        async with admin_engine.begin() as connection:
            await connection.execute(
                text("DELETE FROM public.tenant WHERE id = ANY(:tenant_ids)"),
                {"tenant_ids": tenant_ids},
            )
        await admin_engine.dispose()
