from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

ElectionType = Literal["municipal", "estadual", "federal", "suplementar", "outra"]


class ElectionSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class ElectionCreate(ElectionSchema):
    ano: int = Field(ge=1900, le=2200)
    tipo: ElectionType
    turno: Literal[1, 2] = 1
    data_eleicao: date
    codigo_uf_ibge: int | None = Field(default=None, ge=1)
    codigo_municipio_ibge: int | None = Field(default=None, ge=1)
    descricao: str | None = Field(default=None, max_length=180)

    @model_validator(mode="after")
    def validate_scope(self) -> "ElectionCreate":
        if self.data_eleicao.year != self.ano:
            raise ValueError("O ano deve corresponder a data da eleicao.")
        return self


class ElectionUpdate(ElectionSchema):
    ano: int | None = Field(default=None, ge=1900, le=2200)
    tipo: ElectionType | None = None
    turno: Literal[1, 2] | None = None
    data_eleicao: date | None = None
    codigo_uf_ibge: int | None = Field(default=None, ge=1)
    codigo_municipio_ibge: int | None = Field(default=None, ge=1)
    descricao: str | None = Field(default=None, max_length=180)
    ativo: bool | None = None


class ElectionResponse(ElectionCreate):
    id: int
    uuid_publico: UUID
    estado_nome: str | None
    estado_uf: str | None
    municipio_nome: str | None
    ativo: bool
    criado_por: int | None
    criado_em: datetime
    atualizado_em: datetime


class ContestedOfficeResponse(ElectionSchema):
    id: int
    codigo: str
    nome: str
    tipo_eleicao: Literal["municipal", "federal"]
    ordem: int


class CampaignCreate(ElectionSchema):
    eleicao_id: int = Field(ge=1)
    nome: str = Field(min_length=2, max_length=180)
    cargo_pleiteado_id: int = Field(ge=1)
    ativa: bool = False


class CampaignUpdate(ElectionSchema):
    nome: str | None = Field(default=None, min_length=2, max_length=180)
    cargo_pleiteado_id: int | None = Field(default=None, ge=1)


class CampaignResponse(ElectionSchema):
    id: int
    uuid_publico: UUID
    tenant_id: int
    eleicao_id: int
    nome: str
    cargo_pleiteado_id: int | None = None
    cargo_pleiteado: str
    ativa: bool
    eleicao_ano: int
    eleicao_tipo: ElectionType
    eleicao_turno: Literal[1, 2]
    eleicao_data: date
    eleicao_descricao: str | None
    data_ativacao: datetime | None
    data_encerramento: datetime | None
    criado_por: int | None
    criado_em: datetime
    atualizado_em: datetime


class CampaignClosureCreate(ElectionSchema):
    votos_obtidos: int = Field(ge=0)
    total_votos_validos: int | None = Field(default=None, ge=0)
    eleito: bool
    colocacao: int | None = Field(default=None, ge=1)
    resultado_oficial_em: datetime | None = None
    fonte_resultado: str | None = Field(default=None, max_length=255)
    observacao: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def validate_votes(self) -> "CampaignClosureCreate":
        if self.total_votos_validos is not None and self.votos_obtidos > self.total_votos_validos:
            raise ValueError("Votos obtidos nao podem superar os votos validos.")
        return self


class CampaignClosureResponse(CampaignClosureCreate):
    id: int
    tenant_id: int
    campanha_eleicao_id: int
    campanha_nome: str
    cargo_pleiteado: str
    eleicao_descricao: str | None
    job_processamento_id: int | None
    status: Literal["enfileirado", "processando", "concluido", "falha"]
    erro: str | None
    solicitado_por: int | None
    solicitado_em: datetime
    iniciado_em: datetime | None
    concluido_em: datetime | None
    atualizado_em: datetime
