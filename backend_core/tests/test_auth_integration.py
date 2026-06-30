import os
from uuid import uuid4

import pyotp
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.auth.security import decode_access_token, hash_password
from app.core.config import get_settings
from app.main import app

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="TEST_DATABASE_URL nao configurada para teste de integracao de autenticacao.",
)


@pytest.mark.asyncio
async def test_login_me_logout_with_database_session() -> None:
    assert TEST_DATABASE_URL is not None
    admin_engine = create_async_engine(TEST_DATABASE_URL)
    suffix = uuid4().hex[:10]
    tenant_id: int | None = None
    email = f"auth-{suffix}@example.test"
    password = "Senha-integracao-123!"
    try:
        async with admin_engine.begin() as connection:
            tenant_id = int(
                await connection.scalar(
                    text(
                        "INSERT INTO public.tenant (nome, slug) "
                        "VALUES ('Auth Integration', :slug) RETURNING id"
                    ),
                    {"slug": f"auth-integration-{suffix}"},
                )
            )
            await connection.execute(
                text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
                {"tenant_id": str(tenant_id)},
            )
            user_id = int(
                await connection.scalar(
                    text(
                        "INSERT INTO auth.usuario "
                        "(tenant_id, nome, email, hash_senha) "
                        "VALUES (:tenant_id, 'Gestor Integracao', :email, :password_hash) "
                        "RETURNING id"
                    ),
                    {
                        "tenant_id": tenant_id,
                        "email": email,
                        "password_hash": hash_password(password),
                    },
                )
            )
            await connection.execute(
                text(
                    "INSERT INTO auth.usuario_perfil "
                    "(usuario_id, perfil_acesso_id, tenant_id) "
                    "SELECT :user_id, id, :tenant_id FROM auth.perfil_acesso "
                    "WHERE tenant_id IS NULL AND codigo = 'gestor'"
                ),
                {"user_id": user_id, "tenant_id": tenant_id},
            )

        with TestClient(app) as client:
            login = client.post(
                "/api/v1/auth/login",
                json={
                    "tenant_slug": f"auth-integration-{suffix}",
                    "email": email,
                    "senha": password,
                },
            )
            assert login.status_code == 200, login.text
            body = login.json()
            token = body["access_token"]
            refresh_token = body["refresh_token"]
            assert body["usuario"]["tenant_id"] == tenant_id
            assert body["usuario"]["tenant"]["id"] == tenant_id
            assert body["usuario"]["tenant"]["slug"] == f"auth-integration-{suffix}"
            assert "gestor" in {profile["codigo"] for profile in body["usuario"]["perfis"]}

            headers = {"Authorization": f"Bearer {token}"}
            me = client.get("/api/v1/auth/me", headers=headers)
            assert me.status_code == 200, me.text
            me_body = me.json()
            assert me_body["email"] == email
            assert me_body["tenant_id"] == tenant_id
            assert me_body["tenant"]["id"] == tenant_id
            assert me_body["tenant"]["nome"] == "Auth Integration"
            assert me_body["tenant"]["slug"] == f"auth-integration-{suffix}"

            refreshed = client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": refresh_token},
            )
            assert refreshed.status_code == 200, refreshed.text
            rotated = refreshed.json()
            assert rotated["refresh_token"] != refresh_token
            assert (
                client.post(
                    "/api/v1/auth/refresh",
                    json={"refresh_token": refresh_token},
                ).status_code
                == 401
            )
            token = rotated["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            territorial = client.put(
                f"/api/v1/users/{user_id}/territorial-access",
                headers=headers,
                json={
                    "acessos": [
                        {
                            "tipo_escopo": "global",
                            "pode_administrar": True,
                        }
                    ]
                },
            )
            assert territorial.status_code == 200, territorial.text
            assert territorial.json()[0]["tipo_escopo"] == "global"
            assert (
                client.get(
                    f"/api/v1/users/{user_id}/territorial-access",
                    headers=headers,
                ).json()[0]["pode_administrar"]
                is True
            )
            session_history = client.get("/api/v1/auth/sessions", headers=headers)
            assert session_history.status_code == 200, session_history.text
            assert session_history.json()[0]["atual"] is True
            assert session_history.json()[0]["ultimo_uso_em"]

            mfa_setup = client.post(
                "/api/v1/auth/mfa/setup",
                headers=headers,
                json={"senha": password},
            )
            assert mfa_setup.status_code == 200, mfa_setup.text
            mfa_secret = mfa_setup.json()["segredo"]
            mfa_code = pyotp.TOTP(mfa_secret).now()
            mfa_confirm = client.post(
                "/api/v1/auth/mfa/confirm",
                headers=headers,
                json={"codigo": mfa_code},
            )
            assert mfa_confirm.status_code == 204, mfa_confirm.text

            logout = client.post("/api/v1/auth/logout", headers=headers)
            assert logout.status_code == 204
            assert client.get("/api/v1/auth/me", headers=headers).status_code == 401

            missing_mfa = client.post(
                "/api/v1/auth/login",
                json={
                    "tenant_slug": f"auth-integration-{suffix}",
                    "email": email,
                    "senha": password,
                },
            )
            assert missing_mfa.status_code == 401
            assert missing_mfa.json()["code"] == "mfa_required"

            mfa_login = client.post(
                "/api/v1/auth/login",
                json={
                    "tenant_slug": f"auth-integration-{suffix}",
                    "email": email,
                    "senha": password,
                    "codigo_mfa": pyotp.TOTP(mfa_secret).now(),
                },
            )
            assert mfa_login.status_code == 200, mfa_login.text
            assert mfa_login.json()["usuario"]["mfa_habilitado"] is True
            mfa_access_token = mfa_login.json()["access_token"]
            mfa_session_id = decode_access_token(mfa_access_token, get_settings())["sid"]
            async with admin_engine.begin() as connection:
                await connection.execute(
                    text(
                        "UPDATE auth.sessao_usuario "
                        "SET ultimo_uso_em = now() - interval '3 hours' "
                        "WHERE id = :session_id"
                    ),
                    {"session_id": mfa_session_id},
                )
            expired_by_inactivity = client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {mfa_access_token}"},
            )
            assert expired_by_inactivity.status_code == 401
            assert "inatividade" in expired_by_inactivity.json()["message"].lower()

        async with admin_engine.connect() as connection:
            encrypted_secret = await connection.scalar(
                text("SELECT mfa_segredo FROM auth.usuario WHERE id = :user_id"),
                {"user_id": user_id},
            )
            assert encrypted_secret
            assert encrypted_secret != mfa_secret
    finally:
        if tenant_id is not None:
            async with admin_engine.begin() as connection:
                await connection.execute(
                    text("DELETE FROM public.tenant WHERE id = :tenant_id"),
                    {"tenant_id": tenant_id},
                )
        await admin_engine.dispose()
