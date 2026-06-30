import os
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="TEST_DATABASE_URL nao configurada para teste de integracao RLS.",
)


@pytest.mark.asyncio
async def test_app_role_only_reads_current_tenant() -> None:
    assert TEST_DATABASE_URL is not None
    engine = create_async_engine(TEST_DATABASE_URL)
    suffix = uuid4().hex[:10]
    async with engine.connect() as connection:
        transaction = await connection.begin()
        try:
            tenant_a = await connection.scalar(
                text("INSERT INTO public.tenant (nome, slug) VALUES ('RLS A', :slug) RETURNING id"),
                {"slug": f"rls-a-{suffix}"},
            )
            tenant_b = await connection.scalar(
                text("INSERT INTO public.tenant (nome, slug) VALUES ('RLS B', :slug) RETURNING id"),
                {"slug": f"rls-b-{suffix}"},
            )
            for tenant_id, label in ((tenant_a, "a"), (tenant_b, "b")):
                await connection.execute(
                    text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
                    {"tenant_id": str(tenant_id)},
                )
                await connection.execute(
                    text(
                        "INSERT INTO auth.usuario "
                        "(tenant_id, nome, email, hash_senha) "
                        "VALUES (:tenant_id, :nome, :email, 'test-only')"
                    ),
                    {
                        "tenant_id": tenant_id,
                        "nome": f"Usuario {label}",
                        "email": f"rls-{label}-{suffix}@example.test",
                    },
                )

            await connection.execute(text("SET LOCAL ROLE app_inteligencia"))
            await connection.execute(
                text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
                {"tenant_id": str(tenant_a)},
            )
            visible_tenants = (
                (
                    await connection.execute(
                        text(
                            "SELECT tenant_id FROM auth.usuario "
                            "WHERE email LIKE :email ORDER BY tenant_id"
                        ),
                        {"email": f"rls-%-{suffix}@example.test"},
                    )
                )
                .scalars()
                .all()
            )

            assert visible_tenants == [tenant_a]
        finally:
            await transaction.rollback()
            await engine.dispose()
