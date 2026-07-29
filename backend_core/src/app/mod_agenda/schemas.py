"""Contratos HTTP do dominio de agenda."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AgendaSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")


class CatalogCreate(AgendaSchema):
    codigo: str = Field(min_length=2, max_length=40, pattern=r"^[a-z0-9_]+$")
    nome: str = Field(min_length=2, max_length=80)
    descricao: str | None = Field(default=None, max_length=255)


class CatalogUpdate(AgendaSchema):
    nome: str | None = Field(default=None, min_length=2, max_length=80)
    descricao: str | None = Field(default=None, max_length=255)
    ativo: bool | None = None


class CatalogResponse(CatalogCreate):
    id: int
    tenant_id: int | None
    ativo: bool
    criado_em: datetime
    atualizado_em: datetime


class EventInput(AgendaSchema):
    contexto: Literal["campanha", "gabinete", "institucional"] = "institucional"
    campanha_eleicao_id: int | None = Field(default=None, ge=1)
    tipo_evento_id: int | None = Field(default=None, ge=1)
    status_evento_id: int | None = Field(default=None, ge=1)
    titulo: str = Field(min_length=2, max_length=180)
    descricao: str | None = None
    data_inicio: datetime
    data_fim: datetime | None = None
    local_nome: str | None = Field(default=None, max_length=180)
    endereco_id: int | None = Field(default=None, ge=1)
    codigo_municipio_ibge: int | None = Field(default=None, ge=1)
    bairro_id: int | None = Field(default=None, ge=1)
    zona_eleitoral_id: int | None = Field(default=None, ge=1)
    territorio_id: int | None = Field(default=None, ge=1)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)
    responsavel_pessoa_id: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_dates(self) -> "EventInput":
        if self.data_fim is not None and self.data_fim < self.data_inicio:
            raise ValueError("data_fim deve ser posterior ou igual a data_inicio.")
        return self


class EventUpdate(AgendaSchema):
    contexto: Literal["campanha", "gabinete", "institucional"] | None = None
    campanha_eleicao_id: int | None = Field(default=None, ge=1)
    tipo_evento_id: int | None = Field(default=None, ge=1)
    status_evento_id: int | None = Field(default=None, ge=1)
    titulo: str | None = Field(default=None, min_length=2, max_length=180)
    descricao: str | None = None
    data_inicio: datetime | None = None
    data_fim: datetime | None = None
    local_nome: str | None = Field(default=None, max_length=180)
    endereco_id: int | None = Field(default=None, ge=1)
    codigo_municipio_ibge: int | None = Field(default=None, ge=1)
    bairro_id: int | None = Field(default=None, ge=1)
    zona_eleitoral_id: int | None = Field(default=None, ge=1)
    territorio_id: int | None = Field(default=None, ge=1)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)
    responsavel_pessoa_id: int | None = Field(default=None, ge=1)


class EventCancel(AgendaSchema):
    motivo: str = Field(min_length=3, max_length=1000)


class EventResponse(AgendaSchema):
    id: int
    tenant_id: int
    contexto: Literal["campanha", "gabinete", "institucional"]
    campanha_eleicao_id: int | None
    tipo_evento_id: int | None
    tipo_evento_nome: str | None
    status_evento_id: int | None
    status_evento_codigo: str | None
    status_evento_nome: str | None
    titulo: str
    descricao: str | None
    data_inicio: datetime
    data_fim: datetime | None
    local_nome: str | None
    endereco_id: int | None
    codigo_municipio_ibge: int | None
    bairro_id: int | None
    zona_eleitoral_id: int | None
    territorio_id: int | None
    territorio_nome: str | None
    latitude: Decimal | None
    longitude: Decimal | None
    responsavel_pessoa_id: int
    responsavel_nome: str
    motivo_cancelamento: str | None
    cancelado_em: datetime | None
    criado_em: datetime
    atualizado_em: datetime


class ParticipantInput(AgendaSchema):
    pessoa_id: int = Field(ge=1)
    papel: str | None = Field(default=None, max_length=40)
    presente: bool | None = None
    observacao: str | None = Field(default=None, max_length=255)


class ParticipantResponse(ParticipantInput):
    id: int
    nome: str


class LeadershipInput(AgendaSchema):
    lideranca_id: int = Field(ge=1)
    papel: str | None = Field(default=None, max_length=40)


class LeadershipResponse(LeadershipInput):
    pessoa_id: int
    nome: str
    tipo_lideranca: str | None


class InvitationInput(AgendaSchema):
    direcao: Literal["recebido", "emitido"] = "recebido"
    origem: str | None = Field(default=None, max_length=120)
    pessoa_indicou_id: int | None = Field(default=None, ge=1)
    arquivo_id: int | None = Field(default=None, ge=1)
    status: Literal["pendente", "aceito", "recusado", "confirmado"] = "pendente"
    descricao: str | None = None


class InvitationResponse(InvitationInput):
    id: int
    pessoa_indicou_nome: str | None
    arquivo_nome: str | None
    criado_em: datetime


class AgendaItemInput(AgendaSchema):
    titulo: str = Field(min_length=2, max_length=180)
    descricao: str | None = None
    encaminhamento: str | None = None
    ordem: int | None = Field(default=None, ge=0, le=32767)


class AgendaItemResponse(AgendaItemInput):
    id: int
    criado_em: datetime


class AttendanceInput(AgendaSchema):
    presenca_parlamentar: bool = False
    presenca_representante: bool = False
    nome_representante: str | None = Field(default=None, max_length=180)
    numero_lideres_presentes: int | None = Field(default=None, ge=0)
    numero_convidados: int | None = Field(default=None, ge=0)
    numero_estimado_presentes: int | None = Field(default=None, ge=0)
    observacao: str | None = None

    @model_validator(mode="after")
    def validate_representative(self) -> "AttendanceInput":
        if self.presenca_representante and not self.nome_representante:
            raise ValueError("Informe o nome do representante.")
        return self


class AttendanceResponse(AttendanceInput):
    id: int
    registrado_por: int | None
    registrado_em: datetime


class DemandFromEventInput(AgendaSchema):
    titulo: str = Field(min_length=2, max_length=180)
    descricao: str = Field(min_length=2)
    pessoa_solicitante_id: int | None = Field(default=None, ge=1)
    categoria_demanda_id: int | None = Field(default=None, ge=1)
    prioridade_demanda_id: int | None = Field(default=None, ge=1)
    territorio_id: int | None = Field(default=None, ge=1)
    prazo: date | None = None


class DemandResponse(AgendaSchema):
    id: int
    evento_id: int
    titulo: str | None
    descricao: str
    pessoa_solicitante_id: int | None
    territorio_id: int | None
    status: str
    prioridade: str | None
    criado_em: datetime


class ReminderResponse(AgendaSchema):
    id: int
    evento_id: int
    tipo: str
    mensagem: str
    agendado_para: datetime
    status: str


class InsightResponse(AgendaSchema):
    id: int
    evento_id: int | None
    tipo: str
    tema: str
    frequencia: int
    score: Decimal | None
    detalhes: dict[str, Any]
    gerado_em: datetime


class EventDetailResponse(EventResponse):
    participantes: list[ParticipantResponse]
    liderancas: list[LeadershipResponse]
    convites: list[InvitationResponse]
    pautas: list[AgendaItemResponse]
    presenca: AttendanceResponse | None
    demandas: list[DemandResponse]
    lembretes: list[ReminderResponse]
    insights: list[InsightResponse]


class SummaryGroup(AgendaSchema):
    chave: str
    total: int


class AgendaSummary(AgendaSchema):
    total: int
    por_dia: list[SummaryGroup]
    por_status: list[SummaryGroup]
    por_tipo: list[SummaryGroup]
