from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class S(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class CatalogIn(S):
    codigo: str = Field(min_length=2, max_length=40, pattern=r"^[a-z0-9_]+$")
    nome: str = Field(min_length=2, max_length=80)
    descricao: str | None = None
    ordem: int | None = None
    final: bool | None = None
    peso: int | None = None


class CatalogPatch(S):
    nome: str | None = None
    descricao: str | None = None
    ativo: bool | None = None
    ordem: int | None = None
    final: bool | None = None
    peso: int | None = None


CatalogKey = Literal["categorias", "status", "prioridades", "origens", "resultados"]


class CatalogOut(S):
    id: int
    tenant_id: int | None
    codigo: str
    nome: str
    descricao: str | None = None
    ativo: bool
    ordem: int | None = None
    final: bool | None = None
    peso: int | None = None


class DemandIn(S):
    titulo: str | None = Field(default=None, max_length=180)
    descricao: str = Field(min_length=2)
    pessoa_solicitante_id: int | None = Field(default=None, ge=1)
    lideranca_indicacao_id: int | None = Field(default=None, ge=1)
    evento_id: int | None = Field(default=None, ge=1)
    territorio_id: int | None = Field(default=None, ge=1)
    categoria_demanda_id: int | None = Field(default=None, ge=1)
    prioridade_demanda_id: int | None = Field(default=None, ge=1)
    origem_demanda_id: int | None = Field(default=None, ge=1)
    prazo: date | None = None

    @model_validator(mode="after")
    def origin(self):
        if (
            not self.pessoa_solicitante_id
            and not self.origem_demanda_id
            and not self.evento_id
            and not self.lideranca_indicacao_id
        ):
            raise ValueError("Informe solicitante ou origem identificada.")
        return self


class DemandPatch(S):
    titulo: str | None = None
    descricao: str | None = None
    categoria_demanda_id: int | None = None
    prioridade_demanda_id: int | None = None
    status_demanda_id: int | None = None
    responsavel_atendimento_id: int | None = None
    resultado_atendimento_id: int | None = None
    territorio_id: int | None = None
    prazo: date | None = None
    observacao: str | None = None


class ResponsibleIn(S):
    nome: str = Field(min_length=2, max_length=150)
    tipo: Literal["usuario", "pessoa", "setor", "area"]
    usuario_id: int | None = None
    pessoa_id: int | None = None
    area: str | None = None


class AttendanceIn(S):
    responsavel_atendimento_id: int | None = None
    resultado_atendimento_id: int | None = None
    descricao: str = Field(min_length=2)
    prazo: date | None = None
    data_execucao: date | None = None
    tempo_atendimento_horas: float | None = Field(default=None, ge=0)


class DemandOut(S):
    id: int
    protocolo: str | None
    titulo: str | None
    descricao: str
    pessoa_solicitante_id: int | None
    solicitante_nome: str | None
    lideranca_indicacao_id: int | None
    evento_id: int | None
    territorio_id: int | None
    territorio_nome: str | None
    categoria_demanda_id: int | None
    categoria_nome: str | None
    prioridade_demanda_id: int | None
    prioridade_nome: str | None
    status_demanda_id: int
    status_codigo: str
    status_nome: str
    origem_demanda_id: int | None
    origem_nome: str | None
    responsavel_atendimento_id: int | None
    responsavel_nome: str | None
    resultado_atendimento_id: int | None
    resultado_nome: str | None
    prazo: date | None
    vencida: bool
    classificacao_automatica: bool
    classificacao_detalhes: dict
    criado_em: datetime
    atualizado_em: datetime


class DemandDetail(DemandOut):
    atendimentos: list[dict]
    movimentacoes: list[dict]
    anexos: list[dict]
    alertas: list[dict]


class Summary(S):
    total: int
    vencidas: int
    por_status: list[dict]
    por_categoria: list[dict]
    por_territorio: list[dict]
    por_responsavel: list[dict]


class StatusChange(S):
    status_demanda_id: int = Field(ge=1)
    resultado_atendimento_id: int | None = None
    observacao: str = Field(min_length=3)


class ClassificationIn(S):
    descricao: str = Field(min_length=2)


class ClassificationOut(S):
    categoria_demanda_id: int | None
    categoria_codigo: str | None
    prioridade_demanda_id: int | None
    prioridade_codigo: str | None
    detalhes: dict
