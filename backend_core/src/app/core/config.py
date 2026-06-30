from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Vurix Eleitoral API"
    app_version: str = "0.1.0"
    environment: Literal["local", "test", "staging", "production"] = "local"
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"

    database_url: str = (
        "postgresql+asyncpg://app_user:change_me@localhost:5432/inteligencia_politica"
    )
    database_echo: bool = False
    database_pool_size: int = Field(default=5, ge=1)
    database_max_overflow: int = Field(default=10, ge=0)

    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4321,http://127.0.0.1:4321"
    )
    checkout_provider: Literal["none", "sandbox", "external"] = "none"
    checkout_sandbox_url: str = "https://sandbox.checkout.local/session"
    payment_webhook_secret: str = "change-me-in-production"

    jwt_secret: str = Field(
        default="local-development-secret-change-me-32-bytes",
        min_length=32,
    )
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    jwt_issuer: str = "vurix-eleitoral"
    jwt_audience: str = "vurix-eleitoral-api"
    access_token_minutes: int = Field(default=30, ge=5, le=1440)
    refresh_token_days: int = Field(default=7, ge=1, le=30)
    session_idle_minutes: int = Field(default=120, ge=5, le=10080)
    session_touch_interval_seconds: int = Field(default=60, ge=10, le=600)
    password_min_length: int = Field(default=12, ge=10, le=128)
    mfa_issuer: str = "Vurix Eleitoral"
    mfa_encryption_key: str = Field(
        default="local-mfa-encryption-key-change-me-32-bytes",
        min_length=32,
    )

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        if self.environment in {"staging", "production"} and (
            "change-me" in self.jwt_secret
            or "development" in self.jwt_secret
            or "compose" in self.jwt_secret
        ):
            raise ValueError("JWT_SECRET seguro e exclusivo e obrigatorio neste ambiente.")
        if self.environment in {"staging", "production"} and "change-me" in self.mfa_encryption_key:
            raise ValueError("MFA_ENCRYPTION_KEY segura e exclusiva e obrigatoria.")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
