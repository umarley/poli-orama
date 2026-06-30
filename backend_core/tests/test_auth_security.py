from datetime import UTC, datetime, timedelta

import jwt
import pyotp
import pytest

from app.auth.security import (
    create_access_token,
    decode_access_token,
    decrypt_mfa_secret,
    encrypt_mfa_secret,
    generate_mfa_secret,
    hash_password,
    mfa_provisioning_uri,
    session_is_inactive,
    token_digest,
    validate_password_policy,
    verify_mfa_code,
    verify_password,
)
from app.core.config import Settings
from app.core.errors import AuthenticationError, BusinessRuleError


def test_password_is_argon2_hashed_and_verified() -> None:
    password_hash = hash_password("Senha-forte-123!")

    assert password_hash.startswith("$argon2id$")
    assert verify_password("Senha-forte-123!", password_hash)
    assert not verify_password("senha-incorreta", password_hash)


def test_password_policy_rejects_weak_password() -> None:
    with pytest.raises(BusinessRuleError) as error:
        validate_password_policy("curta", Settings())

    assert error.value.code == "weak_password"
    assert error.value.details["requirements"]


def test_jwt_contains_tenant_user_profiles_permissions_and_session() -> None:
    settings = Settings()
    expires_at = datetime.now(UTC) + timedelta(minutes=10)

    token = create_access_token(
        settings=settings,
        user_id=7,
        tenant_id=42,
        session_id=99,
        profiles=["gestor"],
        permissions=["usuarios.administrar"],
        expires_at=expires_at,
    )
    claims = decode_access_token(token, settings)

    assert claims["sub"] == 7
    assert claims["tenant_id"] == 42
    assert claims["sid"] == 99
    assert claims["perfis"] == ["gestor"]
    assert claims["permissoes"] == ["usuarios.administrar"]
    assert len(token_digest(token)) == 64


def test_tenant_claim_cannot_be_tampered_without_invalidating_signature() -> None:
    settings = Settings()
    token = create_access_token(
        settings=settings,
        user_id=7,
        tenant_id=42,
        session_id=99,
        profiles=["gestor"],
        permissions=[],
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
    )
    header, payload, signature = token.split(".")
    decoded = jwt.api_jws.base64url_decode(payload.encode())
    tampered_payload = decoded.replace(b'"tenant_id":42', b'"tenant_id":43')
    tampered = ".".join(
        [header, jwt.api_jws.base64url_encode(tampered_payload).decode(), signature]
    )

    with pytest.raises(AuthenticationError):
        decode_access_token(tampered, settings)


def test_mfa_secret_is_encrypted_and_totp_is_verified() -> None:
    settings = Settings()
    secret = generate_mfa_secret()
    encrypted = encrypt_mfa_secret(secret, settings)
    code = pyotp.TOTP(secret).now()

    assert secret not in encrypted
    assert decrypt_mfa_secret(encrypted, settings) == secret
    assert verify_mfa_code(secret, code)
    assert "otpauth://totp/" in mfa_provisioning_uri(secret, "gestor@example.test", settings)


def test_session_inactivity_policy() -> None:
    settings = Settings(session_idle_minutes=30)
    now = datetime.now(UTC)

    assert session_is_inactive(now - timedelta(minutes=31), now, settings)
    assert not session_is_inactive(now - timedelta(minutes=29), now, settings)
