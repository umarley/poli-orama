"""Contratos HTTP do dominio de metas."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MetaSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")


MetaStatus = Literal["ativa", "concluida", "cancelada", "em_risco", "suspensa"]
TargetType = Literal[
    "lideranca", "territorio", "equipe", "comunidade", "nucleo_familiar", "pessoa"
]
RiskStatus = Literal["normal", "atencao", "risco", "critico"]


class GoalTypeCreate(MetaSchema):
    codigo: str = Field(min_length=2, max_length=30, pattern=r"^[a-z0-9_]+$")
    nome: str = Field(min_length=2, max_length=60)
    descricao: str | None = Field(default=None, max_length=255)


class GoalTypeUpdate(MetaSchema):
    nome: str | None = Field(default=None, min_length=2, max_length=60)
    descricao: str | None = Field(default=None, max_length=255)
    ativo: bool | None = None


class GoalTypeResponse(GoalTypeCreate):
    id: int
    tenant_id: int | None
    ativo: bool


class GoalPeriodCreate(MetaSchema):
    nome: str = Field(min_length=2, max_length=120)
    data_inicio: date
    data_fim: date
    ciclo: str | None = Field(default=None, max_length=30)

    @model_validator(mode="after")
    def validate_dates(self) -> GoalPeriodCreate:
        if self.data_fim < self.data_inicio:
            raise ValueError("A data final deve ser igual ou posterior a data inicial.")
        return self


class GoalPeriodUpdate(MetaSchema):
    nome: str | None = Field(default=None, min_length=2, max_length=120)
    data_inicio: date | None = None
    data_fim: date | None = None
    ciclo: str | None = Field(default=None, max_length=30)
    ativo: bool | None = None


class GoalPeriodResponse(GoalPeriodCreate):
    id: int
    tenant_id: int
    ativo: bool
    criado_em: datetime
    atualizado_em: datetime


class GoalTargetInput(MetaSchema):
    tipo_alvo: TargetType
    alvo_id: int = Field(ge=1)
    quantidade_atribuida: int | None = Field(default=None, ge=0)


class GoalTargetResponse(GoalTargetInput):
    id: int
    tenant_id: int
    meta_voto_id: int
    nome_alvo: str | None = None
    criado_em: datetime


class GoalCreate(MetaSchema):
    tipo_meta_voto_id: int = Field(ge=1)
    periodo_meta_id: int = Field(ge=1)
    titulo: str = Field(min_length=2, max_length=150)
    quantidade_meta: int = Field(gt=0)
    coordenador_id: int | None = Field(default=None, ge=1)
    alvos: list[GoalTargetInput] = Field(default_factory=list, max_length=100)


class GoalUpdate(MetaSchema):
    tipo_meta_voto_id: int | None = Field(default=None, ge=1)
    periodo_meta_id: int | None = Field(default=None, ge=1)
    titulo: str | None = Field(default=None, min_length=2, max_length=150)
    quantidade_meta: int | None = Field(default=None, gt=0)
    coordenador_id: int | None = Field(default=None, ge=1)
    status: MetaStatus | None = None
    alvos: list[GoalTargetInput] | None = Field(default=None, max_length=100)


class GoalTrackingCreate(MetaSchema):
    data_referencia: date = Field(default_factory=date.today)
    quantidade_projetada: int | None = Field(default=None, ge=0)
    quantidade_confirmada: int | None = Field(default=None, ge=0)
    observacao: str | None = Field(default=None, max_length=2000)


class GoalTrackingResponse(GoalTrackingCreate):
    id: int
    tenant_id: int
    meta_voto_id: int
    quantidade_eleitores_vinculados: int
    percentual_atingido: Decimal
    situacao_risco: RiskStatus
    criado_por: int | None
    criado_em: datetime


class GoalAlertResponse(MetaSchema):
    id: int
    tenant_id: int
    meta_voto_id: int
    tipo_alerta: str
    percentual_referencia: Decimal | None
    mensagem: str | None
    severidade: str
    resolvido: bool
    gerado_em: datetime
    resolvido_em: datetime | None


class GoalResponse(MetaSchema):
    id: int
    tenant_id: int
    campanha_eleicao_id: int
    campanha_nome: str
    tipo_meta_voto_id: int
    tipo_codigo: str
    tipo_nome: str
    periodo_meta_id: int
    periodo_nome: str
    titulo: str
    quantidade_meta: int
    quantidade_atual: int
    quantidade_eleitores_vinculados: int
    percentual: Decimal
    situacao_risco: RiskStatus
    em_risco: bool
    score_risco: Decimal
    fatores_risco: dict[str, Decimal | int | str | bool]
    coordenador_id: int | None
    territorio_id: int | None
    lideranca_id: int | None
    status: MetaStatus
    criado_por: int | None
    criado_em: datetime
    atualizado_em: datetime


class GoalDetailResponse(GoalResponse):
    alvos: list[GoalTargetResponse]
    acompanhamentos: list[GoalTrackingResponse]
    alertas: list[GoalAlertResponse]


class GoalSummaryResponse(MetaSchema):
    total_metas: int
    metas_ativas: int
    metas_atingidas: int
    metas_em_risco: int
    quantidade_meta_total: int
    quantidade_atual_total: int
    percentual_geral: Decimal
    limiar_risco: Decimal


class LeadershipRankingResponse(MetaSchema):
    id: int
    campanha_eleicao_id: int
    lideranca_id: int
    nome_lideranca: str
    data_referencia: date
    posicao: int
    total_cadastros: int
    total_confirmacoes: int
    total_eventos: int
    total_demandas: int
    quantidade_meta: int
    quantidade_atual: int
    percentual_meta: Decimal
    pontuacao: Decimal
    em_risco: bool


class TargetOption(MetaSchema):
    id: int
    nome: str
    tipo: TargetType
