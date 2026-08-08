import base64
import hashlib
import re
import secrets
import string
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import jwt
import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import Settings
from app.core.errors import AuthenticationError, BusinessRuleError

_password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)
_dummy_password_hash = _password_hasher.hash("Dummy-password-9!never-used")


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def consume_password_verification_time(password: str) -> None:
    verify_password(password, _dummy_password_hash)


def validate_password_policy(password: str, settings: Settings) -> None:
    failures: list[str] = []
    if len(password) < settings.password_min_length:
        failures.append(f"ter ao menos {settings.password_min_length} caracteres")
    if not re.search(r"[a-z]", password):
        failures.append("conter letra minuscula")
    if not re.search(r"[A-Z]", password):
        failures.append("conter letra maiuscula")
    if not re.search(r"\d", password):
        failures.append("conter numero")
    if not re.search(r"[^A-Za-z0-9]", password):
        failures.append("conter caractere especial")
    if failures:
        raise BusinessRuleError(
            "A senha nao atende a politica minima.",
            code="weak_password",
            details={"requirements": failures},
        )


def generate_temporary_password(length: int = 20) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%&*"
    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        if all(
            (
                re.search(r"[a-z]", password),
                re.search(r"[A-Z]", password),
                re.search(r"\d", password),
                re.search(r"[^A-Za-z0-9]", password),
            )
        ):
            return password


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def generate_mfa_secret() -> str:
    return pyotp.random_base32()


def encrypt_mfa_secret(secret: str, settings: Settings) -> str:
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.mfa_encryption_key.encode()).digest())
    return Fernet(key).encrypt(secret.encode()).decode()


def decrypt_mfa_secret(encrypted_secret: str, settings: Settings) -> str:
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.mfa_encryption_key.encode()).digest())
    try:
        return Fernet(key).decrypt(encrypted_secret.encode()).decode()
    except InvalidToken as exc:
        raise AuthenticationError("Configuracao MFA invalida.") from exc


def verify_mfa_code(secret: str, code: str) -> bool:
    return pyotp.TOTP(secret).verify(code, valid_window=1)


def mfa_provisioning_uri(secret: str, email: str, settings: Settings) -> str:
    return pyotp.TOTP(secret).provisioning_uri(
        name=email,
        issuer_name=settings.mfa_issuer,
    )


def create_access_token(
    *,
    settings: Settings,
    user_id: int,
    tenant_id: int,
    session_id: int,
    profiles: list[str],
    permissions: list[str],
    login_origin: str = "web",
    expires_at: datetime,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "tenant_id": tenant_id,
        "sid": session_id,
        "perfis": profiles,
        "permissoes": permissions,
        "origem_login": login_origin,
        "type": "access",
        "jti": str(uuid4()),
        "iat": now,
        "nbf": now,
        "exp": expires_at,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(
    *,
    settings: Settings,
    user_id: int,
    tenant_id: int,
    session_id: int,
    login_origin: str = "web",
    expires_at: datetime,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "tenant_id": tenant_id,
        "sid": session_id,
        "origem_login": login_origin,
        "type": "refresh",
        "jti": str(uuid4()),
        "iat": now,
        "nbf": now,
        "exp": expires_at,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, settings: Settings) -> dict[str, Any]:
    return _decode_token(token, settings, expected_type="access")


def decode_refresh_token(token: str, settings: Settings) -> dict[str, Any]:
    return _decode_token(token, settings, expected_type="refresh")


def _decode_token(token: str, settings: Settings, *, expected_type: str) -> dict[str, Any]:
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={
                "require": [
                    "sub",
                    "tenant_id",
                    "sid",
                    "origem_login",
                    "exp",
                    "iat",
                    "type",
                ]
            },
        )
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Token invalido ou expirado.") from exc
    if payload.get("type") != expected_type:
        raise AuthenticationError("Tipo de token invalido.")
    try:
        payload["sub"] = int(payload["sub"])
        payload["tenant_id"] = int(payload["tenant_id"])
        payload["sid"] = int(payload["sid"])
    except (TypeError, ValueError) as exc:
        raise AuthenticationError("Claims obrigatorias do token sao invalidas.") from exc
    login_origin = payload["origem_login"]
    if login_origin not in {"web", "app_lider"}:
        raise AuthenticationError("Origem da sessao invalida.")
    payload["origem_login"] = login_origin
    return payload


def access_token_expiration(settings: Settings) -> datetime:
    return datetime.now(UTC) + timedelta(minutes=settings.access_token_minutes)


def refresh_token_expiration(settings: Settings) -> datetime:
    return datetime.now(UTC) + timedelta(days=settings.refresh_token_days)


def session_is_inactive(last_activity: datetime, now: datetime, settings: Settings) -> bool:
    return last_activity + timedelta(minutes=settings.session_idle_minutes) <= now
