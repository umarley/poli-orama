from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

TenantStatus = Literal["pendente", "ativo", "suspenso", "cancelado", "trial", "inadimplente"]


class PlanoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid_publico: UUID
    slug: str
    nome: str
    descricao: str | None
    preco_mensal: Decimal
    moeda: str
    limite_usuarios: int | None
    limite_pessoas: int | None
    limite_armazenamento_mb: int | None
    recursos: dict[str, Any]
    ordem_comercial: int


class TenantConfiguracaoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    nome_publico: str | None
    cor_primaria: str | None
    logo_url: str | None
    fuso_horario: str
    percentual_alerta_meta: Decimal
    integracoes: dict[str, Any]
    preferencias: dict[str, Any]


class TenantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid_publico: UUID
    nome: str
    slug: str
    documento: str | None
    tem_mandato: bool
    plano_assinatura_id: int | None
    data_inicio_contrato: date | None
    data_fim_contrato: date | None
    status: str
    criado_em: datetime
    atualizado_em: datetime
    plano: PlanoResponse | None = None
    configuracao: TenantConfiguracaoResponse | None = None


class TenantCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=180)
    slug: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    documento: str | None = Field(default=None, max_length=20)
    tem_mandato: bool = False
    plano_assinatura_id: int | None = Field(default=None, ge=1)
    status: TenantStatus = "pendente"


class TenantUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=180)
    slug: str | None = Field(
        default=None, min_length=2, max_length=80, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
    )
    status: TenantStatus | None = None
    plano_assinatura_id: int | None = Field(default=None, ge=1)


class TenantConfiguracaoUpdate(BaseModel):
    nome_publico: str | None = Field(default=None, max_length=180)
    cor_primaria: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}(?:[0-9A-Fa-f]{2})?$")
    logo_url: str | None = Field(default=None, max_length=2048)
    fuso_horario: str | None = Field(default=None, max_length=60)
    percentual_alerta_meta: Decimal | None = Field(default=None, ge=0, le=100)
    preferencias: dict[str, Any] | None = None

    @field_validator("preferencias")
    @classmethod
    def force_nome_completo_obrigatorio(
        cls, value: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        if not isinstance(value, dict):
            return value
        formulario = value.get("formulario_cadastro")
        if not isinstance(formulario, dict):
            return value
        return {
            **value,
            "formulario_cadastro": {**formulario, "nome_completo": True},
        }


class UtmSource(BaseModel):
    utm_source: str | None = Field(default=None, max_length=120)
    utm_medium: str | None = Field(default=None, max_length=120)
    utm_campaign: str | None = Field(default=None, max_length=120)
    utm_content: str | None = Field(default=None, max_length=120)
    utm_term: str | None = Field(default=None, max_length=120)
    pagina_origem: str | None = Field(default=None, max_length=500)


class PublicContactBase(BaseModel):
    nome: str = Field(min_length=2, max_length=180)
    email: str = Field(min_length=5, max_length=254)
    telefone: str | None = Field(default=None, max_length=20)
    consentimento: Literal[True]
    origem: UtmSource = Field(default_factory=UtmSource)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or "." not in normalized.rsplit("@", 1)[-1]:
            raise ValueError("E-mail invalido.")
        return normalized


class LeadCreate(PublicContactBase):
    organizacao: str | None = Field(default=None, max_length=180)
    mensagem: str | None = Field(default=None, max_length=2000)


class LeadResponse(BaseModel):
    id: UUID
    status: Literal["recebido"] = "recebido"


class ContratacaoCreate(PublicContactBase):
    plano_slug: str = Field(min_length=2, max_length=80)
    documento: str | None = Field(default=None, max_length=20)
    nome_campanha: str = Field(min_length=2, max_length=180)
    slug_solicitado: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class ContratacaoResponse(BaseModel):
    id: UUID
    status: str


class CheckoutCreate(BaseModel):
    contratacao_id: UUID
    success_url: str | None = Field(default=None, max_length=2048)
    cancel_url: str | None = Field(default=None, max_length=2048)


class CheckoutResponse(BaseModel):
    session_id: UUID
    status: str
    checkout_url: str | None


class PaymentWebhook(BaseModel):
    event_id: str = Field(min_length=1, max_length=180)
    event_type: Literal["payment.approved", "payment.failed", "subscription.overdue"]
    contratacao_id: UUID | None = None
    tenant_id: int | None = Field(default=None, ge=1)
    external_reference: str | None = Field(default=None, max_length=180)


class PlanUsageResponse(BaseModel):
    plano: PlanoResponse | None
    usuarios: int
    pessoas: int
    armazenamento_mb: Decimal
