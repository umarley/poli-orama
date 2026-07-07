from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class CatalogInput(BaseModel):
    codigo: str = Field(min_length=2, max_length=30, pattern=r"^[a-z0-9_]+$")
    nome: str = Field(min_length=2, max_length=60)
    descricao: str | None = Field(default=None, max_length=255)


class CatalogUpdate(BaseModel):
    codigo: str | None = Field(default=None, min_length=2, max_length=30, pattern=r"^[a-z0-9_]+$")
    nome: str | None = Field(default=None, min_length=2, max_length=60)
    descricao: str | None = Field(default=None, max_length=255)
    ativo: bool | None = None


class CatalogResponse(BaseModel):
    id: int
    tenant_id: int | None
    codigo: str
    nome: str
    descricao: str | None = None
    ativo: bool
    criado_em: datetime | None = None
    atualizado_em: datetime | None = None


class InteracaoInput(BaseModel):
    tipo_interacao_id: int | None = Field(default=None, ge=1)
    canal_comunicacao_id: int | None = Field(default=None, ge=1)
    lideranca_id: int | None = Field(default=None, ge=1)
    demanda_id: int | None = Field(default=None, ge=1)
    evento_id: int | None = Field(default=None, ge=1)
    direcao: Literal["entrada", "saida"] = "saida"
    assunto: str | None = Field(default=None, max_length=180)
    conteudo: str | None = Field(default=None, max_length=5000)
    resultado: str | None = Field(default=None, max_length=120)
    data_interacao: datetime | None = None


class InteracaoResponse(BaseModel):
    id: int
    tenant_id: int
    pessoa_id: int
    pessoa_nome: str
    tipo_interacao_id: int | None
    tipo_interacao_nome: str | None
    canal_comunicacao_id: int | None
    canal_comunicacao_nome: str | None
    lideranca_id: int | None
    demanda_id: int | None
    evento_id: int | None
    direcao: str
    assunto: str | None
    conteudo: str | None
    resultado: str | None
    data_interacao: datetime
    registrado_por: int | None
    registrado_por_nome: str | None = None
    criado_em: datetime
