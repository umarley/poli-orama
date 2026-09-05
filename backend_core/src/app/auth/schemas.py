import re
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.tenants.schemas import TenantResponse


class LoginRequest(BaseModel):
    tenant_slug: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9-]+$")
    email: str = Field(min_length=3, max_length=254)
    senha: str = Field(min_length=1, max_length=128)
    dispositivo: str | None = Field(default=None, max_length=180)
    codigo_mfa: str | None = Field(default=None, pattern=r"^\d{6}$")
    app_lider: bool = False

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("E-mail invalido.")
        return value


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    codigo: str
    descricao: str | None
    nivel: int
    permissoes: list["PermissionResponse"] = Field(default_factory=list)


class PermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    modulo: str
    acao: str
    descricao: str | None


class UserData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid_publico: UUID
    tenant_id: int
    pessoa_id: int | None
    lideranca_id: int | None = None
    habilitado_app_lider: bool = False
    ultimo_acesso_app_em: datetime | None = None
    nome: str
    email: str
    telefone: str | None
    status: str
    deve_alterar_senha: bool
    mfa_habilitado: bool
    ultimo_login_em: datetime | None
    criado_em: datetime
    atualizado_em: datetime


class UserResponse(UserData):
    tenant: TenantResponse
    perfis: list[ProfileResponse] = Field(default_factory=list)
    permissoes: list[str] = Field(default_factory=list)
    acessos_territoriais: list["TerritorialAccessResponse"] = Field(default_factory=list)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    usuario: UserResponse


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=4096)


class TenantSwitchRequest(BaseModel):
    tenant_id: int = Field(ge=1)
    dispositivo: str | None = Field(default=None, max_length=180)


TerritorialScopeType = Literal[
    "estado",
    "municipio",
    "bairro",
    "zona_eleitoral",
    "secao_eleitoral",
    "territorio",
    "global",
]

_SCOPE_FIELD = {
    "estado": "codigo_uf_ibge",
    "municipio": "codigo_municipio_ibge",
    "bairro": "bairro_id",
    "zona_eleitoral": "zona_eleitoral_id",
    "secao_eleitoral": "secao_eleitoral_id",
    "territorio": "territorio_id",
}


class TerritorialAccessInput(BaseModel):
    tipo_escopo: TerritorialScopeType
    codigo_uf_ibge: int | None = Field(default=None, ge=1)
    codigo_municipio_ibge: int | None = Field(default=None, ge=1)
    bairro_id: int | None = Field(default=None, ge=1)
    zona_eleitoral_id: int | None = Field(default=None, ge=1)
    secao_eleitoral_id: int | None = Field(default=None, ge=1)
    territorio_id: int | None = Field(default=None, ge=1)
    pode_administrar: bool = False

    @model_validator(mode="after")
    def validate_scope_identifier(self) -> "TerritorialAccessInput":
        populated = {field for field in _SCOPE_FIELD.values() if getattr(self, field) is not None}
        expected = _SCOPE_FIELD.get(self.tipo_escopo)
        if expected is None and populated:
            raise ValueError("Escopo global nao aceita identificador territorial.")
        if expected is not None and populated != {expected}:
            raise ValueError(f"Escopo {self.tipo_escopo} exige somente o campo {expected}.")
        return self


class TerritorialAccessResponse(TerritorialAccessInput):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    usuario_id: int
    criado_em: datetime


class TerritorialAccessReplace(BaseModel):
    acessos: list[TerritorialAccessInput] = Field(max_length=500)

    @model_validator(mode="after")
    def validate_unique_scopes(self) -> "TerritorialAccessReplace":
        keys = [
            (
                access.tipo_escopo,
                access.codigo_uf_ibge,
                access.codigo_municipio_ibge,
                access.bairro_id,
                access.zona_eleitoral_id,
                access.secao_eleitoral_id,
                access.territorio_id,
            )
            for access in self.acessos
        ]
        if len(keys) != len(set(keys)):
            raise ValueError("A lista contem escopos territoriais duplicados.")
        return self


class UserCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=180)
    email: str = Field(min_length=3, max_length=254)
    senha: str = Field(min_length=1, max_length=128)
    telefone: str | None = Field(default=None, max_length=20)
    pessoa_id: int | None = Field(default=None, ge=1)
    lideranca_id: int | None = Field(default=None, ge=1)
    habilitado_app_lider: bool = False
    perfil_ids: list[Annotated[int, Field(ge=1)]] = Field(min_length=1)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return LoginRequest.normalize_email(value)

    @model_validator(mode="after")
    def validate_app_lider(self) -> "UserCreate":
        if self.habilitado_app_lider and self.lideranca_id is None:
            raise ValueError(
                "lideranca_id e obrigatorio quando habilitado_app_lider e verdadeiro."
            )
        return self


class UserUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=180)
    email: str | None = Field(default=None, min_length=3, max_length=254)
    telefone: str | None = Field(default=None, max_length=20)
    pessoa_id: int | None = Field(default=None, ge=1)
    lideranca_id: int | None = Field(default=None, ge=1)
    habilitado_app_lider: bool | None = None
    status: str | None = Field(default=None, pattern=r"^(ativo|inativo|bloqueado|pendente)$")
    perfil_ids: list[Annotated[int, Field(ge=1)]] | None = None

    @field_validator("email")
    @classmethod
    def normalize_optional_email(cls, value: str | None) -> str | None:
        return LoginRequest.normalize_email(value) if value is not None else None


class ResetPasswordRequest(BaseModel):
    senha_temporaria: str | None = Field(default=None, min_length=1, max_length=128)


class ResetPasswordResponse(BaseModel):
    usuario_id: int
    senha_temporaria: str
    deve_alterar_senha: bool = True


class SelfProfileUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=180)
    email: str | None = Field(default=None, min_length=3, max_length=254)
    telefone: str | None = Field(default=None, max_length=20)

    @field_validator("email")
    @classmethod
    def normalize_optional_email(cls, value: str | None) -> str | None:
        return LoginRequest.normalize_email(value) if value is not None else None


class ChangePasswordRequest(BaseModel):
    senha_atual: str = Field(min_length=1, max_length=128)
    nova_senha: str = Field(min_length=1, max_length=128)


class MfaSetupRequest(BaseModel):
    senha: str = Field(min_length=1, max_length=128)


class MfaSetupResponse(BaseModel):
    segredo: str
    uri_configuracao: str


class MfaCodeRequest(BaseModel):
    codigo: str = Field(pattern=r"^\d{6}$")


class MfaDisableRequest(MfaCodeRequest):
    senha: str = Field(min_length=1, max_length=128)


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    origem_login: Literal["web", "app_lider"]
    dispositivo: str | None
    user_agent: str | None
    ip_origem: str | None
    criado_em: datetime
    ultimo_uso_em: datetime
    expira_em: datetime
    revogada_em: datetime | None
    atual: bool = False
    status: Literal["ativa", "revogada", "expirada", "expirada_inatividade"]


class ApiKeyCreate(BaseModel):
    tenant_id: int = Field(ge=1)
    nome: str = Field(min_length=2, max_length=120)

    @field_validator("nome")
    @classmethod
    def normalize_nome(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError("Informe um nome com ao menos 2 caracteres.")
        return normalized


class ApiKeyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid_publico: UUID
    tenant_id: int
    tenant_nome: str
    tenant_slug: str
    nome: str
    token_prefix: str
    ativo: bool
    ultimo_uso_em: datetime | None
    revogada_em: datetime | None
    criado_por: int
    criado_em: datetime
    atualizado_em: datetime


class ApiKeyCreatedResponse(ApiKeyResponse):
    token: str
